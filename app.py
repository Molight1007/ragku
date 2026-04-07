from __future__ import annotations

import asyncio
import shutil
import threading
import uuid
from http import HTTPStatus
from pathlib import Path
from typing import List, Optional

import dashscope

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from pydantic import BaseModel

from config import settings
from rag_service import rag_answer

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
LEGACY_KB_ID = "legacy_fire"
LEGACY_KB_NAME = "消防"
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
KB_ROOT_DIR = UPLOAD_DIR / "knowledge_bases"


def _ensure_upload_dir() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_kb_root_dir() -> None:
    KB_ROOT_DIR.mkdir(parents=True, exist_ok=True)


def _safe_kb_id(name: str) -> str:
    base = (name or "").strip()
    safe = "".join(ch for ch in base if ch.isalnum() or ch in {"_", "-"})
    safe = safe.strip("_-")
    if not safe:
        safe = f"kb_{uuid.uuid4().hex[:8]}"
    return safe[:64]


def _kb_dir(kb_id: str) -> Path:
    return KB_ROOT_DIR / kb_id


def _kb_files_dir(kb_id: str) -> Path:
    return _kb_dir(kb_id) / "files"


def _kb_index_file(kb_id: str) -> Path:
    return _kb_dir(kb_id) / "index_store.npy"


def _kb_meta_file(kb_id: str) -> Path:
    return _kb_dir(kb_id) / "index_meta.npy"


def _kb_name_file(kb_id: str) -> Path:
    return _kb_dir(kb_id) / "name.txt"


def _legacy_index_exists() -> bool:
    return settings.index_file.exists() and settings.meta_file.exists()


def _resolve_rag_kb_id(kb_id: Optional[str]) -> Optional[str]:
    safe_id = _safe_kb_id((kb_id or "").strip()) if kb_id else None
    if safe_id == LEGACY_KB_ID:
        return None
    return safe_id


class ChatRequest(BaseModel):
    """前端发送的问题请求模型。"""

    question: str = ""
    attachment_text: str = ""
    kb_id: Optional[str] = None


class ContextSnippet(BaseModel):
    """返回给前端的参考片段数据结构。"""

    source: str
    text_preview: str
    score: float


class ChatResponse(BaseModel):
    """前端收到的回答数据结构。"""

    answer: str
    contexts: List[ContextSnippet]


class OCRImageResponse(BaseModel):
    """图片 OCR 接口返回。"""

    text: str
    filename: str


class UploadExtractResponse(BaseModel):
    """文件上传并解析文本后的返回。"""

    text: str
    filename: str
    saved_path: str


class KnowledgeBaseCreateRequest(BaseModel):
    """创建知识库请求。"""

    name: str = ""


class KnowledgeBaseInfo(BaseModel):
    """知识库信息。"""

    id: str
    name: str
    file_count: int


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表返回。"""

    items: List[KnowledgeBaseInfo]


class KnowledgeBaseUploadProgress(BaseModel):
    """知识库上传后分片向量化进度。"""

    total_chunks: int
    processed_chunks: int
    done: bool
    message: str = ""


class KnowledgeBaseFileItem(BaseModel):
    name: str
    rel_path: str
    size: int


class KnowledgeBaseFileListResponse(BaseModel):
    kb_id: str
    items: List[KnowledgeBaseFileItem]


app = FastAPI(
    title="本地知识库RAG问答系统",
    description="基于阿里云通义千问 + 本地多模态知识库的RAG服务，用于大赛展示。",
    version="1.0.0",
)

# 注意：allow_credentials=True 时不能使用 allow_origins=["*"]，否则浏览器会拦截跨域请求。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def index() -> dict:
    """简单健康检查接口。"""
    return {
        "message": "本地知识库RAG问答系统已启动。",
        "docs": "/docs",
    }


@app.post("/api/ocr/image", response_model=OCRImageResponse)
async def api_ocr_image(file: UploadFile = File(...)) -> OCRImageResponse:
    """上传图片，返回百炼 Qwen-OCR 识别的文字。"""
    from config import settings as app_settings
    from document_extract import is_image_filename, ocr_image_bytes

    if not app_settings.dashscope_api_key:
        raise HTTPException(status_code=400, detail="未配置 DASHSCOPE_API_KEY，无法调用百炼图片识别")
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")
    if not is_image_filename(file.filename):
        raise HTTPException(
            status_code=400,
            detail="请上传图片文件（jpg / png / bmp / webp / gif）",
        )
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="图片过大，请压缩后重试")
    try:
        text = ocr_image_bytes(data, file.filename)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"图片识别失败: {e}") from e
    return OCRImageResponse(text=text.strip(), filename=file.filename)


@app.post("/api/upload/file", response_model=UploadExtractResponse)
async def api_upload_file(file: UploadFile = File(...)) -> UploadExtractResponse:
    """上传文件：保存到本地 uploads/，并尽量提取文本（与知识库支持的类型一致）。"""
    from config import settings as app_settings
    from document_extract import (
        extract_text_from_bytes,
        is_allowed_upload,
        is_image_filename,
        safe_upload_name,
    )

    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")
    if not is_allowed_upload(file.filename):
        raise HTTPException(
            status_code=400,
            detail="仅支持 txt、md、pdf、docx 及常见图片格式",
        )
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件过大")
    if is_image_filename(file.filename) and not app_settings.dashscope_api_key:
        raise HTTPException(status_code=400, detail="未配置 DASHSCOPE_API_KEY，无法对图片调用百炼识别")
    try:
        text = extract_text_from_bytes(file.filename, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"解析文件失败: {e}") from e

    _ensure_upload_dir()
    stored = f"{uuid.uuid4().hex[:12]}_{safe_upload_name(file.filename)}"
    dest = UPLOAD_DIR / stored
    dest.write_bytes(data)
    rel = str(dest.relative_to(Path(__file__).resolve().parent)).replace("\\", "/")
    return UploadExtractResponse(
        text=(text or "").strip(),
        filename=file.filename,
        saved_path=rel,
    )


def _collect_documents_for_kb(data_dir: Path) -> List[tuple[str, str]]:
    from ingest import collect_documents

    return collect_documents(data_dir)


KB_UPLOAD_PROGRESS: dict[str, dict] = {}
KB_UPLOAD_LOCK = threading.Lock()
KB_REBUILD_RUNNING: set[str] = set()


def _build_embeddings_for_kb_with_progress(docs: List[tuple[str, str]], kb_id: str):
    if not settings.dashscope_api_key:
        raise RuntimeError("未检测到 DASHSCOPE_API_KEY，请先在环境变量或 .env 中配置。")

    if not docs:
        raise RuntimeError("没有可向量化的文本分片。")

    from dashscope import TextEmbedding

    dashscope.api_key = settings.dashscope_api_key

    embeddings: List[List[float]] = []
    metadatas: List[dict] = []
    total = len(docs)

    with KB_UPLOAD_LOCK:
        KB_UPLOAD_PROGRESS[kb_id] = {
            "total": total,
            "processed": 0,
            "done": False,
            "message": "开始分片向量化",
        }

    for idx, (source, text) in enumerate(docs, start=1):
        try:
            resp = TextEmbedding.call(model=settings.embedding_model, input=text)
            status = getattr(resp, "status_code", None)
            if status != HTTPStatus.OK:
                code = getattr(resp, "code", "")
                msg = getattr(resp, "message", "") or str(resp)
                with KB_UPLOAD_LOCK:
                    KB_UPLOAD_PROGRESS[kb_id]["processed"] = idx
                    KB_UPLOAD_PROGRESS[kb_id]["message"] = f"第 {idx}/{total} 分片失败: {code} {msg}".strip()
                continue

            output = resp.output if hasattr(resp, "output") else resp["output"]
            emb_list = output["embeddings"] if isinstance(output, dict) else output.embeddings
            vector = emb_list[0]["embedding"] if isinstance(emb_list[0], dict) else emb_list[0].embedding
            embeddings.append(list(vector))
            metadatas.append({"source": source, "text": text})
        except Exception as e:  # noqa: BLE001
            with KB_UPLOAD_LOCK:
                KB_UPLOAD_PROGRESS[kb_id]["processed"] = idx
                KB_UPLOAD_PROGRESS[kb_id]["message"] = f"第 {idx}/{total} 分片异常: {e}"
            continue

        with KB_UPLOAD_LOCK:
            KB_UPLOAD_PROGRESS[kb_id]["processed"] = idx
            KB_UPLOAD_PROGRESS[kb_id]["message"] = f"分片向量化进度 {idx}/{total}"

    if not embeddings:
        with KB_UPLOAD_LOCK:
            KB_UPLOAD_PROGRESS[kb_id]["done"] = True
            KB_UPLOAD_PROGRESS[kb_id]["message"] = "未成功生成任何向量"
        raise RuntimeError("未成功生成任何向量，请检查密钥、模型或网络。")

    with KB_UPLOAD_LOCK:
        KB_UPLOAD_PROGRESS[kb_id]["done"] = True
        KB_UPLOAD_PROGRESS[kb_id]["message"] = "向量化完成"

    return np.array(embeddings, dtype="float32"), metadatas


def _list_kb_items() -> List[KnowledgeBaseInfo]:
    _ensure_kb_root_dir()
    items: List[KnowledgeBaseInfo] = []

    if _legacy_index_exists():
        items.append(KnowledgeBaseInfo(id=LEGACY_KB_ID, name=LEGACY_KB_NAME, file_count=0))

    for p in KB_ROOT_DIR.iterdir():
        if not p.is_dir():
            continue
        kb_id = p.name
        name_file = _kb_name_file(kb_id)
        kb_name = name_file.read_text(encoding="utf-8", errors="ignore").strip() if name_file.exists() else kb_id
        files_dir = _kb_files_dir(kb_id)
        file_count = 0
        if files_dir.exists():
            file_count = len([x for x in files_dir.rglob("*") if x.is_file()])
        items.append(KnowledgeBaseInfo(id=kb_id, name=kb_name or kb_id, file_count=file_count))
    items.sort(key=lambda x: x.name)
    return items


@app.get("/api/kb/list", response_model=KnowledgeBaseListResponse)
async def api_kb_list() -> KnowledgeBaseListResponse:
    return KnowledgeBaseListResponse(items=_list_kb_items())


@app.post("/api/kb/create", response_model=KnowledgeBaseInfo)
async def api_kb_create(body: KnowledgeBaseCreateRequest) -> KnowledgeBaseInfo:
    _ensure_kb_root_dir()
    kb_name = (body.name or "").strip() or f"知识库-{uuid.uuid4().hex[:6]}"
    kb_id = _safe_kb_id(kb_name)
    base = _kb_dir(kb_id)
    i = 2
    while base.exists():
        kb_id = _safe_kb_id(f"{kb_name}_{i}")
        base = _kb_dir(kb_id)
        i += 1
    _kb_files_dir(kb_id).mkdir(parents=True, exist_ok=True)
    _kb_name_file(kb_id).write_text(kb_name, encoding="utf-8")
    return KnowledgeBaseInfo(id=kb_id, name=kb_name, file_count=0)


@app.post("/api/kb/upload", response_model=KnowledgeBaseInfo)
async def api_kb_upload(kb_id: str = Form(...), file: UploadFile = File(...)) -> KnowledgeBaseInfo:
    from config import settings as app_settings
    from document_extract import is_allowed_upload, is_image_filename, safe_upload_name

    safe_id = _safe_kb_id(kb_id)
    base = _kb_dir(safe_id)
    if not base.exists():
        raise HTTPException(status_code=404, detail="知识库不存在，请先创建")

    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")
    if not is_allowed_upload(file.filename):
        raise HTTPException(status_code=400, detail="仅支持 txt、md、pdf、docx 及常见图片格式")

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件过大")
    if is_image_filename(file.filename) and not app_settings.dashscope_api_key:
        raise HTTPException(status_code=400, detail="未配置 DASHSCOPE_API_KEY，无法对图片调用百炼识别")

    files_dir = _kb_files_dir(safe_id)
    files_dir.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex[:12]}_{safe_upload_name(file.filename)}"
    (files_dir / stored).write_bytes(data)

    with KB_UPLOAD_LOCK:
        if safe_id in KB_REBUILD_RUNNING:
            kb_name = _kb_name_file(safe_id).read_text(encoding="utf-8", errors="ignore").strip() or safe_id
            file_count = len([x for x in files_dir.rglob("*") if x.is_file()])
            return KnowledgeBaseInfo(id=safe_id, name=kb_name, file_count=file_count)
        KB_REBUILD_RUNNING.add(safe_id)
        KB_UPLOAD_PROGRESS[safe_id] = {
            "total": 1,
            "processed": 0,
            "done": False,
            "message": "文件已上传，等待重建索引",
        }

    async def _rebuild() -> None:
        try:
            docs = await asyncio.to_thread(_collect_documents_for_kb, files_dir)
            if not docs:
                with KB_UPLOAD_LOCK:
                    KB_UPLOAD_PROGRESS[safe_id] = {
                        "total": 0,
                        "processed": 0,
                        "done": True,
                        "message": "知识库未提取到可向量化文本",
                    }
                return
            embeddings, metadatas = await asyncio.to_thread(_build_embeddings_for_kb_with_progress, docs, safe_id)
            await asyncio.to_thread(np.save, _kb_index_file(safe_id), embeddings)
            await asyncio.to_thread(np.save, _kb_meta_file(safe_id), np.array(metadatas, dtype=object))
            with KB_UPLOAD_LOCK:
                p = KB_UPLOAD_PROGRESS.get(safe_id, {})
                p["done"] = True
                p["message"] = "索引重建完成"
                KB_UPLOAD_PROGRESS[safe_id] = p
        except Exception as e:  # noqa: BLE001
            with KB_UPLOAD_LOCK:
                p = KB_UPLOAD_PROGRESS.get(safe_id, {"total": 0, "processed": 0})
                p["done"] = True
                p["message"] = f"索引重建失败: {e}"
                KB_UPLOAD_PROGRESS[safe_id] = p
        finally:
            with KB_UPLOAD_LOCK:
                KB_REBUILD_RUNNING.discard(safe_id)

    asyncio.create_task(_rebuild())

    kb_name = _kb_name_file(safe_id).read_text(encoding="utf-8", errors="ignore").strip() or safe_id
    file_count = len([x for x in files_dir.rglob("*") if x.is_file()])
    return KnowledgeBaseInfo(id=safe_id, name=kb_name, file_count=file_count)


@app.get("/api/kb/{kb_id}/progress", response_model=KnowledgeBaseUploadProgress)
async def api_kb_progress(kb_id: str) -> KnowledgeBaseUploadProgress:
    safe_id = _safe_kb_id(kb_id)
    with KB_UPLOAD_LOCK:
        p = KB_UPLOAD_PROGRESS.get(safe_id)
    if not p:
        return KnowledgeBaseUploadProgress(total_chunks=0, processed_chunks=0, done=True, message="暂无任务")
    return KnowledgeBaseUploadProgress(
        total_chunks=int(p.get("total", 0)),
        processed_chunks=int(p.get("processed", 0)),
        done=bool(p.get("done", False)),
        message=str(p.get("message", "")),
    )


@app.get("/api/kb/{kb_id}/files", response_model=KnowledgeBaseFileListResponse)
async def api_kb_files(kb_id: str) -> KnowledgeBaseFileListResponse:
    safe_id = _safe_kb_id(kb_id)
    if safe_id == LEGACY_KB_ID:
        return KnowledgeBaseFileListResponse(kb_id=safe_id, items=[])

    base = _kb_dir(safe_id)
    if not base.exists() or not base.is_dir():
        raise HTTPException(status_code=404, detail="知识库不存在")

    files_dir = _kb_files_dir(safe_id)
    items: List[KnowledgeBaseFileItem] = []
    if files_dir.exists():
        for p in files_dir.rglob("*"):
            if not p.is_file():
                continue
            rel = str(p.relative_to(files_dir)).replace("\\", "/")
            items.append(KnowledgeBaseFileItem(name=p.name, rel_path=rel, size=int(p.stat().st_size)))
    items.sort(key=lambda x: x.rel_path)
    return KnowledgeBaseFileListResponse(kb_id=safe_id, items=items)


@app.delete("/api/kb/{kb_id}/file")
async def api_kb_delete_file(kb_id: str, rel_path: str) -> dict:
    safe_id = _safe_kb_id(kb_id)
    if safe_id == LEGACY_KB_ID:
        raise HTTPException(status_code=400, detail="默认“消防”知识库不支持删除文件")

    base = _kb_dir(safe_id)
    if not base.exists() or not base.is_dir():
        raise HTTPException(status_code=404, detail="知识库不存在")

    files_dir = _kb_files_dir(safe_id)
    target = (files_dir / (rel_path or "")).resolve()
    if not str(target).startswith(str(files_dir.resolve())):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    target.unlink()

    async def _rebuild_after_delete() -> None:
        with KB_UPLOAD_LOCK:
            KB_REBUILD_RUNNING.add(safe_id)
            KB_UPLOAD_PROGRESS[safe_id] = {
                "total": 1,
                "processed": 0,
                "done": False,
                "message": "文件删除后重建索引中",
            }
        try:
            docs = await asyncio.to_thread(_collect_documents_for_kb, files_dir)
            if not docs:
                for fp in (_kb_index_file(safe_id), _kb_meta_file(safe_id)):
                    if fp.exists():
                        fp.unlink()
                with KB_UPLOAD_LOCK:
                    KB_UPLOAD_PROGRESS[safe_id] = {
                        "total": 0,
                        "processed": 0,
                        "done": True,
                        "message": "已无可索引文件，索引已清空",
                    }
                return
            embeddings, metadatas = await asyncio.to_thread(_build_embeddings_for_kb_with_progress, docs, safe_id)
            await asyncio.to_thread(np.save, _kb_index_file(safe_id), embeddings)
            await asyncio.to_thread(np.save, _kb_meta_file(safe_id), np.array(metadatas, dtype=object))
            with KB_UPLOAD_LOCK:
                p = KB_UPLOAD_PROGRESS.get(safe_id, {})
                p["done"] = True
                p["message"] = "索引重建完成"
                KB_UPLOAD_PROGRESS[safe_id] = p
        except Exception as e:  # noqa: BLE001
            with KB_UPLOAD_LOCK:
                p = KB_UPLOAD_PROGRESS.get(safe_id, {"total": 0, "processed": 0})
                p["done"] = True
                p["message"] = f"索引重建失败: {e}"
                KB_UPLOAD_PROGRESS[safe_id] = p
        finally:
            with KB_UPLOAD_LOCK:
                KB_REBUILD_RUNNING.discard(safe_id)

    asyncio.create_task(_rebuild_after_delete())
    return {"ok": True}


@app.delete("/api/kb/{kb_id}")
async def api_kb_delete(kb_id: str) -> dict:
    safe_id = _safe_kb_id(kb_id)

    if safe_id == LEGACY_KB_ID:
        removed = False
        if settings.index_file.exists():
            settings.index_file.unlink()
            removed = True
        if settings.meta_file.exists():
            settings.meta_file.unlink()
            removed = True
        if not removed:
            raise HTTPException(status_code=404, detail="知识库不存在")
        return {"ok": True}

    base = _kb_dir(safe_id)
    if not base.exists() or not base.is_dir():
        raise HTTPException(status_code=404, detail="知识库不存在")

    shutil.rmtree(base)
    return {"ok": True}


@app.get("/chat-ui", response_class=HTMLResponse)
async def chat_ui() -> str:
    """千问风格的中文网页聊天界面。"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8" />
    <title>本地知识库问答系统</title>
    <style>
        * {
            box-sizing: border-box;
        }
        body {
            font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            margin: 0;
            background: #f2f2f3;
            color: #1f2330;
        }
        .page {
            min-height: 100vh;
            max-width: 980px;
            margin: 0 auto;
            padding: 24px 20px 36px;
            display: flex;
            flex-direction: column;
        }
        .top-tools {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 28px;
        }
        .menu-btn {
            border: 1px solid #d9dbe2;
            background: #ffffff;
            color: #4a4f5d;
            border-radius: 10px;
            width: 42px;
            height: 42px;
            padding: 0;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(28, 39, 64, 0.06);
            display: inline-flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 5px;
            flex-shrink: 0;
        }
        .menu-btn:hover {
            background: #f8f9fc;
        }
        .menu-btn .bar {
            display: block;
            width: 18px;
            height: 2px;
            background: #4a4f5d;
            border-radius: 1px;
        }
        .history-overlay {
            position: fixed;
            inset: 0;
            background: rgba(55, 60, 72, 0.38);
            z-index: 1000;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.22s ease, visibility 0.22s ease;
        }
        .history-overlay.open {
            opacity: 1;
            visibility: visible;
        }
        .history-drawer {
            position: fixed;
            top: 0;
            left: 0;
            bottom: 0;
            width: min(82vw, 340px);
            max-width: 380px;
            background: #ffffff;
            z-index: 1001;
            box-shadow: 8px 0 32px rgba(28, 39, 64, 0.12);
            transform: translateX(-102%);
            transition: transform 0.26s cubic-bezier(0.22, 1, 0.36, 1);
            display: flex;
            flex-direction: column;
        }
        .history-drawer.open {
            transform: translateX(0);
        }
        .kb-linked-panel {
            position: fixed;
            top: 0;
            left: min(82vw, 340px);
            bottom: 0;
            width: min(42vw, 420px);
            background: #ffffff;
            z-index: 1001;
            box-shadow: 8px 0 32px rgba(28, 39, 64, 0.10);
            border-left: 1px solid #eef0f5;
            display: flex;
            flex-direction: column;
            opacity: 0;
            pointer-events: none;
            transform: translateX(0);
            transition: opacity 0.2s ease;
        }
        .kb-linked-panel.open {
            opacity: 1;
            pointer-events: auto;
        }
        .kb-linked-head {
            padding: 18px 16px 12px;
            border-bottom: 1px solid #eef0f5;
            font-size: 16px;
            font-weight: 700;
        }
        .kb-linked-list {
            flex: 1;
            min-height: 0;
            overflow-y: auto;
            padding: 10px 12px 12px;
        }
        .kb-file-row {
            border: 1px solid #edf0f5;
            border-radius: 10px;
            background: #fafbff;
            padding: 8px;
            margin-bottom: 8px;
        }
        .kb-file-row-top {
            display: flex;
            justify-content: space-between;
            gap: 8px;
            align-items: flex-start;
        }
        .kb-file-del {
            width: 28px;
            height: 28px;
            padding: 0;
            border: 1px solid #d9dbe2;
            border-radius: 8px;
            background: #fff;
            font-size: 18px;
            line-height: 1;
            color: #9ca3af;
            cursor: pointer;
            transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
        }
        .kb-file-del:hover {
            background: #fee2e2;
            color: #dc2626;
            border-color: #fecaca;
        }
        .kb-file-del:disabled {
            cursor: not-allowed;
            color: #c4c7cf;
            background: #f6f7fa;
            border-color: #e5e7eb;
        }
        .kb-file-name {
            font-size: 11px;
            color: #1f2330;
            word-break: break-all;
        }
        .kb-file-meta {
            font-size: 11px;
            color: #6b7280;
            margin-top: 3px;
        }
        .history-drawer-inner {
            flex: 1;
            min-height: 0;
            display: flex;
            flex-direction: column;
            padding: 20px 0 20px;
        }
        .history-drawer-title {
            font-size: 17px;
            font-weight: 700;
            color: #1f2330;
            padding: 0 20px 12px;
            border-bottom: 1px solid #eef0f5;
        }
        .drawer-tabs {
            display: flex;
            gap: 8px;
            padding: 10px 16px 8px;
            border-bottom: 1px solid #eef0f5;
        }
        .drawer-tab {
            border: 1px solid #d9dbe2;
            background: #fff;
            color: #4a4f5d;
            border-radius: 999px;
            font-size: 13px;
            padding: 6px 12px;
            cursor: pointer;
        }
        .drawer-tab.active {
            background: #e8edfb;
            color: #355ddf;
            border-color: #c9d5fb;
        }
        .drawer-panel {
            display: none;
            flex: 1;
            min-height: 0;
            overflow-y: auto;
        }
        .drawer-panel.active {
            display: block;
        }
        .history-list {
            flex: 1;
            overflow-y: auto;
            padding: 12px 0 8px;
        }
        .kb-panel {
            padding: 12px 16px 14px;
        }
        .kb-create {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
        }
        .kb-create input {
            flex: 1;
            min-width: 0;
            border: 1px solid #d9dbe2;
            border-radius: 10px;
            padding: 8px 10px;
            font-size: 14px;
        }
        .kb-create button {
            border: 1px solid #d9dbe2;
            border-radius: 10px;
            background: #fff;
            padding: 8px 10px;
            cursor: pointer;
        }
        .kb-item {
            border: 1px solid #edf0f5;
            border-radius: 10px;
            background: #fff;
            padding: 10px;
            margin-bottom: 10px;
        }
        .kb-item.active {
            border-color: #c9d5fb;
            background: #f6f9ff;
        }
        .kb-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }
        .kb-name {
            font-size: 12px;
            font-weight: 600;
            color: #1f2330;
            word-break: break-all;
        }
        .kb-meta {
            font-size: 11px;
            color: #6b7280;
        }
        .kb-actions {
            display: flex;
            gap: 8px;
        }
        .kb-actions button {
            border: 1px solid #d9dbe2;
            border-radius: 8px;
            background: #fff;
            font-size: 12px;
            padding: 6px 8px;
            cursor: pointer;
        }
        .kb-delete-x {
            width: 28px;
            height: 28px;
            padding: 0;
            border-radius: 8px;
            font-size: 18px;
            line-height: 1;
            color: #9ca3af;
            transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
        }
        .kb-delete-x:hover {
            background: #fee2e2;
            color: #dc2626;
            border-color: #fecaca;
        }
        .kb-delete-x:disabled {
            cursor: not-allowed;
            color: #c4c7cf;
            background: #f6f7fa;
            border-color: #e5e7eb;
        }
        .history-row {
            display: flex;
            align-items: stretch;
            border-bottom: 1px solid #f0f2f7;
        }
        .history-row:last-child {
            border-bottom: none;
        }
        .history-item-main {
            flex: 1;
            min-width: 0;
            border: none;
            background: transparent;
            text-align: left;
            padding: 12px 8px 12px 20px;
            font-size: 15px;
            color: #1f2330;
            cursor: pointer;
            font-family: inherit;
            line-height: 1.45;
            transition: background 0.15s ease;
        }
        .history-row:hover .history-item-main {
            background: #f3f5fa;
        }
        .history-row.active .history-item-main {
            background: #e8edfb;
            color: #355ddf;
        }
        .history-item-delete {
            flex-shrink: 0;
            width: 44px;
            border: none;
            background: transparent;
            color: #9ca3af;
            font-size: 20px;
            line-height: 1;
            cursor: pointer;
            padding: 0;
            font-family: inherit;
            transition: background 0.15s ease, color 0.15s ease;
        }
        .history-item-delete:hover {
            background: #fee2e2;
            color: #dc2626;
        }
        .history-empty {
            padding: 24px 20px;
            font-size: 14px;
            color: #9ca3af;
            text-align: center;
        }
        .clear-btn {
            border: 1px solid #d9dbe2;
            background: #ffffff;
            color: #4a4f5d;
            border-radius: 999px;
            font-size: 13px;
            padding: 8px 14px;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(28, 39, 64, 0.06);
        }
        .welcome {
            text-align: center;
            font-size: 42px;
            font-weight: 600;
            letter-spacing: 1px;
            margin-top: 40px;
            margin-bottom: 26px;
        }
        .chat-box {
            flex: 1;
            min-height: 0;
            display: block;
            overflow-y: auto;
            padding: 0;
            border-radius: 0;
            background: transparent;
            box-shadow: none;
            transition: padding 0.2s ease;
        }
        .chat-box.active {
            padding: 10px 10px 16px;
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.38);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
        }
        .msg {
            margin-bottom: 12px;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }
        .msg-user {
            justify-content: flex-end;
        }
        .msg-bot {
            justify-content: flex-start;
        }
        .avatar {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            flex-shrink: 0;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            font-weight: 700;
        }
        .avatar-bot {
            background: #e8ebf2;
            color: #374151;
        }
        .avatar-user {
            background: #d8e5ff;
            color: #355ddf;
        }
        .bubble {
            max-width: min(82%, 880px);
            padding: 10px 13px;
            border-radius: 12px;
            line-height: 1.6;
            font-size: 14px;
            white-space: pre-wrap;
            word-break: break-word;
        }
        .msg-user .bubble {
            background: #8eaefb;
            color: #fff;
            border-radius: 12px 12px 4px 12px;
            box-shadow: 0 3px 10px rgba(120, 149, 230, 0.20);
        }
        .msg-bot .bubble {
            background: #fcfcfd;
            color: #1f2937;
            border: 1px solid #e4e6eb;
            border-radius: 4px 12px 12px 12px;
            box-shadow: 0 2px 8px rgba(33, 43, 60, 0.06);
        }
        .contexts {
            margin-top: 8px;
            padding: 8px 10px;
            background: #f7f8fb;
            border: 1px solid #eceef3;
            border-radius: 10px;
            font-size: 12px;
            color: #4b5563;
        }
        .composer-wrap {
            margin-top: 12px;
            flex-shrink: 0;
            position: relative;
            z-index: 20;
        }
        .composer {
            display: flex;
            align-items: flex-end;
            gap: 10px;
            background: #f7f7f8;
            border: 1px solid #dcdee4;
            border-radius: 28px;
            box-shadow: 0 10px 24px rgba(50, 59, 81, 0.08), 0 2px 6px rgba(50, 59, 81, 0.05);
            padding: 8px 14px;
            position: relative;
            z-index: 21;
            overflow: visible;
        }
        .composer-main {
            flex: 1;
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 8px;
            align-items: stretch;
        }
        .attachment-strip {
            display: none;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
            padding: 0 2px;
        }
        .attachment-strip.has-items {
            display: flex;
        }
        .attachment-chip {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 4px 6px 4px 4px;
            background: #ffffff;
            border: 1px solid #e5e7ee;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(33, 43, 60, 0.06);
            max-width: 100%;
        }
        .attachment-thumb {
            width: 48px;
            height: 48px;
            border-radius: 8px;
            object-fit: cover;
            background: #eef0f5;
            flex-shrink: 0;
        }
        .attachment-thumb.file-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            width: 48px;
            height: 48px;
        }
        .attachment-meta {
            font-size: 13px;
            color: #4b5563;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .attachment-remove {
            width: 28px;
            height: 28px;
            border: none;
            border-radius: 8px;
            background: transparent;
            color: #9ca3af;
            font-size: 18px;
            line-height: 1;
            cursor: pointer;
            flex-shrink: 0;
        }
        .attachment-remove:hover {
            background: #f3f4f6;
            color: #374151;
        }
        .question-input {
            flex: 1;
            min-width: 0;
            width: 100%;
            border: none;
            outline: none;
            background: transparent;
            font-size: 16px;
            line-height: 1.4;
            min-height: 40px;
            max-height: 220px;
            resize: none;
            overflow-y: auto;
            font-family: inherit;
            font-weight: 400;
            color: #1f2330;
            padding: 8px 0;
        }
        .question-input::placeholder {
            font-size: inherit;
            line-height: inherit;
            font-family: inherit;
            font-weight: 400;
            color: #b6b9c3;
        }
        .composer-bottom {
            margin-top: 0;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 8px;
            position: relative;
            flex-shrink: 0;
            z-index: 22;
        }
        .plus-wrap {
            position: relative;
            display: inline-flex;
            align-items: center;
            flex-shrink: 0;
            z-index: 30;
        }
        .plus-btn {
            width: 40px;
            height: 40px;
            border: 1px solid #d7dbe6;
            border-radius: 999px;
            background: #ffffff;
            color: #5d6473;
            font-size: 24px;
            line-height: 1;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 10px rgba(33, 43, 60, 0.10);
        }
        .plus-menu {
            position: absolute;
            right: 0;
            top: auto;
            bottom: calc(100% + 8px);
            min-width: 210px;
            background: #ffffff;
            border: 1px solid #e5e7ee;
            border-radius: 16px;
            box-shadow: 0 14px 24px rgba(33, 43, 60, 0.12);
            overflow: hidden;
            display: none;
            z-index: 200;
        }
        .plus-menu.show {
            display: block;
        }
        .plus-item {
            width: 100%;
            border: none;
            background: #fff;
            color: #1f2330;
            text-align: left;
            padding: 12px 14px;
            font-size: 15px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 10px;
        }
        .plus-item + .plus-item {
            border-top: 1px solid #edf0f5;
        }
        .plus-item:hover {
            background: #f8f9fc;
        }
        .plus-icon {
            width: 18px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #4b5563;
            font-size: 16px;
        }
        .send-btn {
            width: 40px;
            height: 40px;
            border: none;
            border-radius: 999px;
            background: #4a6fd4;
            color: #fff;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            flex-shrink: 0;
            position: relative;
            z-index: 22;
            box-shadow: 0 4px 10px rgba(71, 111, 216, 0.35);
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }
        .send-btn:disabled {
            background: #bfd0f8;
            color: #bfd0f8;
            cursor: not-allowed;
            box-shadow: 0 4px 10px rgba(106, 138, 220, 0.28);
        }
        .send-btn[aria-busy="true"] {
            background: #3d5eb8;
            cursor: pointer;
            box-shadow: 0 4px 10px rgba(61, 94, 184, 0.45);
        }
        .send-square {
            display: block;
            width: 12px;
            height: 12px;
            border-radius: 2px;
            background: #fff;
        }
        .status {
            margin-top: 8px;
            font-size: 12px;
            color: #7a808f;
            text-align: center;
        }
        @media (max-width: 900px) {
            .page {
                padding: 16px 12px 24px;
            }
            .welcome {
                font-size: 30px;
                margin-top: 26px;
            }
            .question-input {
                font-size: 16px;
            }
        }
    </style>
</head>
<body>
    <div class="page">
        <div class="top-tools">
            <button type="button" id="menuBtn" class="menu-btn" aria-label="打开菜单" title="菜单">
                <span class="bar"></span>
                <span class="bar"></span>
                <span class="bar"></span>
            </button>
            <button type="button" class="clear-btn" onclick="resetChat()">新对话</button>
        </div>
        <div class="welcome" id="welcomeText">你好，欢迎使用知识库问答</div>
        <div class="chat-box" id="chatBox"></div>
        <div class="composer-wrap">
            <div class="composer">
                <div class="composer-main">
                    <div id="attachmentStrip" class="attachment-strip" aria-live="polite"></div>
                    <textarea id="questionInput" class="question-input" rows="1" placeholder="请输入你的问题"></textarea>
                </div>
                <div class="composer-bottom">
                    <div class="plus-wrap">
                        <button id="plusBtn" class="plus-btn" type="button" aria-label="更多功能">+</button>
                        <div id="plusMenu" class="plus-menu">
                            <button class="plus-item" id="plusBtnCamera" type="button"><span class="plus-icon">📷</span>拍照识文字</button>
                            <button class="plus-item" id="plusBtnImage" type="button"><span class="plus-icon">🖼</span>图片识文字</button>
                            <button class="plus-item" id="plusBtnFile" type="button"><span class="plus-icon">📎</span>文件</button>
                        </div>
                    </div>
                    <button id="sendBtn" class="send-btn" type="button" aria-label="发送">↑</button>
                </div>
            </div>
            <div class="status" id="statusText">就绪</div>
        </div>
    </div>
    <div id="historyOverlay" class="history-overlay" aria-hidden="true"></div>
    <aside id="historyDrawer" class="history-drawer" aria-hidden="true" aria-label="菜单">
        <div class="history-drawer-inner">
            <div class="history-drawer-title">菜单</div>
            <div class="drawer-tabs">
                <button type="button" id="tabHistory" class="drawer-tab active">历史记录</button>
                <button type="button" id="tabKb" class="drawer-tab">知识库</button>
            </div>
            <div id="panelHistory" class="drawer-panel active">
                <div id="historyList" class="history-list"></div>
            </div>
            <div id="panelKb" class="drawer-panel">
                <div class="kb-panel">
                    <div class="kb-create">
                        <input id="kbNameInput" type="text" placeholder="输入知识库名称" />
                        <button id="kbCreateBtn" type="button">创建</button>
                    </div>
                    <div id="kbList"></div>
                </div>
            </div>
        </div>
    </aside>
    <aside id="kbLinkedPanel" class="kb-linked-panel" aria-hidden="true">
        <div id="kbLinkedHead" class="kb-linked-head">知识库文件</div>
        <div id="kbLinkedList" class="kb-linked-list"></div>
    </aside>
    <input type="file" id="kbFileInput" accept=".txt,.md,.pdf,.docx,.jpg,.jpeg,.png,.bmp,.webp,.gif" multiple style="display:none" />
    <input type="file" id="fileCamera" accept="image/*" capture="environment" style="display:none" />
    <input type="file" id="fileImage" accept="image/*" multiple style="display:none" />
    <input type="file" id="fileDoc" accept=".txt,.md,.pdf,.docx,.jpg,.jpeg,.png,.bmp,.webp,.gif" multiple style="display:none" />
    <script>
        const chatBox = document.getElementById('chatBox');
        const questionInput = document.getElementById('questionInput');
        const sendBtn = document.getElementById('sendBtn');
        const statusText = document.getElementById('statusText');
        const welcomeText = document.getElementById('welcomeText');
        const plusBtn = document.getElementById('plusBtn');
        const plusMenu = document.getElementById('plusMenu');
        const plusBtnCamera = document.getElementById('plusBtnCamera');
        const plusBtnImage = document.getElementById('plusBtnImage');
        const plusBtnFile = document.getElementById('plusBtnFile');
        const fileCamera = document.getElementById('fileCamera');
        const fileImage = document.getElementById('fileImage');
        const fileDoc = document.getElementById('fileDoc');
        const attachmentStrip = document.getElementById('attachmentStrip');
        const menuBtn = document.getElementById('menuBtn');
        const historyOverlay = document.getElementById('historyOverlay');
        const historyDrawer = document.getElementById('historyDrawer');
        const historyList = document.getElementById('historyList');
        const tabHistory = document.getElementById('tabHistory');
        const tabKb = document.getElementById('tabKb');
        const panelHistory = document.getElementById('panelHistory');
        const panelKb = document.getElementById('panelKb');
        const kbNameInput = document.getElementById('kbNameInput');
        const kbCreateBtn = document.getElementById('kbCreateBtn');
        const kbList = document.getElementById('kbList');
        const kbFileInput = document.getElementById('kbFileInput');
        const kbLinkedPanel = document.getElementById('kbLinkedPanel');
        const kbLinkedHead = document.getElementById('kbLinkedHead');
        const kbLinkedList = document.getElementById('kbLinkedList');

        const STORAGE_KEY = 'ragku_chat_sessions_v1';
        const KB_SELECTED_KEY = 'ragku_selected_kb_id_v1';
        let pendingAttachments = [];
        let chatInFlight = false;
        let chatAbortController = null;
        let chatCancelReason = null;
        let currentSessionId = null;
        let sessionMessages = [];
        let persistTimer = null;
        let kbItems = [];
        let selectedKbId = localStorage.getItem(KB_SELECTED_KEY) || null;
        let kbUploadTargetId = null;
        let kbDetailOpenForId = null;

        function apiUrl(path) {
            var base = (window.location.origin && window.location.origin !== 'null')
                ? window.location.origin
                : 'http://127.0.0.1:8000';
            return new URL(path, base).href;
        }

        function explainFetchError(err) {
            if (err && err.name === 'TypeError') {
                return '无法连接服务器。请用地址栏打开 ' + window.location.origin + '/chat-ui（不要用本地离线网页），并确认本机已启动 uvicorn。';
            }
            return (err && err.message) ? err.message : String(err);
        }

        function setStatus(text) {
            if (statusText) statusText.textContent = text;
        }

        function setSendBtnBusy(busy) {
            if (!sendBtn) return;
            sendBtn.disabled = false;
            sendBtn.setAttribute('aria-busy', busy ? 'true' : 'false');
            if (busy) {
                sendBtn.innerHTML = '<span class="send-square" aria-hidden="true"></span>';
                sendBtn.setAttribute('aria-label', '停止本次回答');
                sendBtn.title = '点击停止本次回答';
            } else {
                sendBtn.textContent = '↑';
                sendBtn.setAttribute('aria-label', '发送');
                sendBtn.title = '';
            }
        }

        function autoResizeInput() {
            if (!questionInput) return;
            questionInput.style.height = 'auto';
            questionInput.style.height = Math.min(questionInput.scrollHeight, 220) + 'px';
        }

        function hidePlusMenu() {
            if (plusMenu) plusMenu.classList.remove('show');
        }

        function loadAllSessionsFromStorage() {
            try {
                var raw = localStorage.getItem(STORAGE_KEY);
                if (!raw) return [];
                var arr = JSON.parse(raw);
                return Array.isArray(arr) ? arr : [];
            } catch (e) {
                return [];
            }
        }

        function saveAllSessionsToStorage(list) {
            try {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
            } catch (e) {}
        }

        function persistCurrentSession() {
            clearTimeout(persistTimer);
            persistTimer = setTimeout(function () {
                if (sessionMessages.length === 0) return;
                if (!currentSessionId) {
                    currentSessionId = 's_' + Date.now() + '_' + Math.random().toString(36).slice(2, 9);
                }
                var title = '新对话';
                for (var i = 0; i < sessionMessages.length; i++) {
                    if (sessionMessages[i].role === 'user') {
                        var t = (sessionMessages[i].text || '').replace(/\\n/g, ' ').trim();
                        title = t.length > 28 ? t.slice(0, 28) + '…' : (t || '新对话');
                        break;
                    }
                }
                var all = loadAllSessionsFromStorage();
                var found = false;
                var snapshot = JSON.parse(JSON.stringify(sessionMessages));
                var now = Date.now();
                for (var j = 0; j < all.length; j++) {
                    if (all[j].id === currentSessionId) {
                        all[j] = { id: currentSessionId, title: title, updatedAt: now, messages: snapshot };
                        found = true;
                        break;
                    }
                }
                if (!found) {
                    all.unshift({ id: currentSessionId, title: title, updatedAt: now, messages: snapshot });
                }
                all.sort(function (a, b) { return (b.updatedAt || 0) - (a.updatedAt || 0); });
                saveAllSessionsToStorage(all);
            }, 80);
        }

        function closeHistoryDrawer() {
            if (historyOverlay) {
                historyOverlay.classList.remove('open');
                historyOverlay.setAttribute('aria-hidden', 'true');
            }
            if (historyDrawer) {
                historyDrawer.classList.remove('open');
                historyDrawer.setAttribute('aria-hidden', 'true');
            }
            if (kbLinkedPanel) {
                kbLinkedPanel.classList.remove('open');
                kbLinkedPanel.setAttribute('aria-hidden', 'true');
            }
        }

        function setDrawerTab(tab) {
            var isHistory = tab !== 'kb';
            if (tabHistory) tabHistory.classList.toggle('active', isHistory);
            if (tabKb) tabKb.classList.toggle('active', !isHistory);
            if (panelHistory) panelHistory.classList.toggle('active', isHistory);
            if (panelKb) panelKb.classList.toggle('active', !isHistory);
            if (isHistory && kbLinkedPanel) {
                kbLinkedPanel.classList.remove('open');
                kbLinkedPanel.setAttribute('aria-hidden', 'true');
                kbDetailOpenForId = null;
            }
        }

        async function fetchKbList() {
            let resp;
            try {
                resp = await fetch(apiUrl('/api/kb/list'));
            } catch (err) {
                throw new Error(explainFetchError(err));
            }
            if (!resp.ok) {
                throw new Error('加载知识库失败：' + resp.status);
            }
            const data = await resp.json();
            kbItems = Array.isArray(data.items) ? data.items : [];
            if (selectedKbId && !kbItems.some(function (x) { return x.id === selectedKbId; })) {
                selectedKbId = null;
                localStorage.removeItem(KB_SELECTED_KEY);
            }
        }

        function renderKbList() {
            if (!kbList) return;
            kbList.innerHTML = '';
            if (!kbItems.length) {
                var empty = document.createElement('div');
                empty.className = 'history-empty';
                empty.textContent = '暂无知识库，请先创建';
                kbList.appendChild(empty);
                return;
            }
            for (var i = 0; i < kbItems.length; i++) {
                (function (kb) {
                    var item = document.createElement('div');
                    item.className = 'kb-item' + (kb.id === kbDetailOpenForId ? ' active' : '');

                    var head = document.createElement('div');
                    head.className = 'kb-head';

                    var nameWrap = document.createElement('div');
                    var nm = document.createElement('div');
                    nm.className = 'kb-name';
                    nm.textContent = kb.name || kb.id;
                    var meta = document.createElement('div');
                    meta.className = 'kb-meta';
                    meta.textContent = '文件数：' + (kb.file_count || 0);
                    nameWrap.appendChild(nm);
                    nameWrap.appendChild(meta);
                    head.appendChild(nameWrap);
                    item.appendChild(head);

                    item.addEventListener('click', async function (evt) {
                        if (evt.target && evt.target.closest('.kb-actions')) return;
                        if (kbDetailOpenForId === kb.id) {
                            kbDetailOpenForId = null;
                            if (kbLinkedPanel) {
                                kbLinkedPanel.classList.remove('open');
                                kbLinkedPanel.setAttribute('aria-hidden', 'true');
                            }
                            renderKbList();
                            return;
                        }
                        kbDetailOpenForId = kb.id;
                        renderKbList();
                        await openKbLinkedPanel(kb);
                    });

                    var actions = document.createElement('div');
                    actions.className = 'kb-actions';

                    var selectBtn = document.createElement('button');
                    selectBtn.type = 'button';
                    selectBtn.textContent = kb.id === selectedKbId ? '当前使用中' : '使用此库';
                    selectBtn.addEventListener('click', function () {
                        selectedKbId = kb.id;
                        localStorage.setItem(KB_SELECTED_KEY, kb.id);
                        renderKbList();
                        setStatus('已切换问答知识库：' + (kb.name || kb.id));
                    });

                    var uploadBtn = document.createElement('button');
                    uploadBtn.type = 'button';
                    uploadBtn.textContent = '上传文件';
                    uploadBtn.disabled = kb.id === 'legacy_fire';
                    uploadBtn.addEventListener('click', function () {
                        if (kb.id === 'legacy_fire') {
                            setStatus('“消防”为默认知识库，不支持上传');
                            return;
                        }
                        kbUploadTargetId = kb.id;
                        if (kbFileInput) kbFileInput.click();
                    });

                    var deleteBtn = document.createElement('button');
                    deleteBtn.type = 'button';
                    deleteBtn.className = 'kb-delete-x';
                    deleteBtn.textContent = '×';
                    deleteBtn.title = '删除知识库';
                    deleteBtn.disabled = kb.id === 'legacy_fire';
                    deleteBtn.addEventListener('click', async function () {
                        var ok = window.confirm('确认删除知识库「' + (kb.name || kb.id) + '」吗？此操作不可恢复。');
                        if (!ok) return;
                        try {
                            const resp = await fetch(apiUrl('/api/kb/' + encodeURIComponent(kb.id)), { method: 'DELETE' });
                            const data = await resp.json().catch(function () { return {}; });
                            if (!resp.ok) throw new Error((data && data.detail) ? data.detail : ('HTTP ' + resp.status));
                            if (selectedKbId === kb.id) {
                                selectedKbId = null;
                                localStorage.removeItem(KB_SELECTED_KEY);
                            }
                            if (kbDetailOpenForId === kb.id) {
                                kbDetailOpenForId = null;
                                if (kbLinkedPanel) {
                                    kbLinkedPanel.classList.remove('open');
                                    kbLinkedPanel.setAttribute('aria-hidden', 'true');
                                }
                            }
                            await refreshKbListAndRender();
                            setStatus('已删除知识库：' + (kb.name || kb.id));
                        } catch (err) {
                            setStatus('删除失败：' + (err.message || err));
                        }
                    });

                    actions.appendChild(selectBtn);
                    actions.appendChild(uploadBtn);
                    actions.appendChild(deleteBtn);
                    item.appendChild(actions);
                    kbList.appendChild(item);
                })(kbItems[i]);
            }
        }

        async function fetchKbFiles(kbId) {
            const resp = await fetch(apiUrl('/api/kb/' + encodeURIComponent(kbId) + '/files'));
            const data = await resp.json().catch(function () { return {}; });
            if (!resp.ok) throw new Error((data && data.detail) ? data.detail : ('HTTP ' + resp.status));
            return Array.isArray(data.items) ? data.items : [];
        }

        function _fmtSize(n) {
            var b = Number(n || 0);
            if (b < 1024) return b + ' B';
            if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB';
            return (b / 1024 / 1024).toFixed(1) + ' MB';
        }

        async function openKbLinkedPanel(kb) {
            if (!kbLinkedPanel || !kbLinkedHead || !kbLinkedList) return;
            kbLinkedHead.textContent = (kb.name || kb.id) + ' · 文件';
            kbLinkedList.innerHTML = '<div class="history-empty">加载中…</div>';
            kbLinkedPanel.classList.add('open');
            kbLinkedPanel.setAttribute('aria-hidden', 'false');

            try {
                const files = await fetchKbFiles(kb.id);
                kbLinkedList.innerHTML = '';
                if (!files.length) {
                    var empty = document.createElement('div');
                    empty.className = 'history-empty';
                    empty.textContent = kb.id === 'legacy_fire' ? '默认“消防”不展示原始文件列表' : '该知识库暂无文件';
                    kbLinkedList.appendChild(empty);
                    return;
                }
                for (var i = 0; i < files.length; i++) {
                    (function (f) {
                        var row = document.createElement('div');
                        row.className = 'kb-file-row';

                        var top = document.createElement('div');
                        top.className = 'kb-file-row-top';

                        var left = document.createElement('div');
                        var n = document.createElement('div');
                        n.className = 'kb-file-name';
                        var rawName = f.name || f.rel_path || '未命名文件';
                        n.textContent = String(rawName).replace(/^[0-9a-f]{12}_/i, '');
                        var m = document.createElement('div');
                        m.className = 'kb-file-meta';
                        m.textContent = '大小：' + _fmtSize(f.size || 0);
                        left.appendChild(n);
                        left.appendChild(m);

                        var del = document.createElement('button');
                        del.type = 'button';
                        del.className = 'kb-file-del';
                        del.textContent = '×';
                        del.title = '删除文件';
                        del.disabled = kb.id === 'legacy_fire';
                        del.addEventListener('click', async function () {
                            var ok = window.confirm('确认删除文件：' + (f.rel_path || f.name) + ' ？');
                            if (!ok) return;
                            try {
                                const resp = await fetch(apiUrl('/api/kb/' + encodeURIComponent(kb.id) + '/file?rel_path=' + encodeURIComponent(f.rel_path || f.name)), { method: 'DELETE' });
                                const data = await resp.json().catch(function () { return {}; });
                                if (!resp.ok) throw new Error((data && data.detail) ? data.detail : ('HTTP ' + resp.status));
                                setStatus('文件已删除，正在重建索引…');
                                await waitKbRebuildProgress(kb.id);
                                await refreshKbListAndRender();
                                await openKbLinkedPanel(kb);
                                setStatus('删除完成并已重建索引');
                            } catch (err) {
                                setStatus('删除失败：' + (err.message || err));
                            }
                        });

                        top.appendChild(left);
                        top.appendChild(del);
                        row.appendChild(top);
                        kbLinkedList.appendChild(row);
                    })(files[i]);
                }
            } catch (err) {
                kbLinkedList.innerHTML = '<div class="history-empty">加载失败：' + (err.message || err) + '</div>';
            }
        }

        async function refreshKbListAndRender() {
            try {
                await fetchKbList();
                renderKbList();
                if (kbDetailOpenForId) {
                    var target = null;
                    for (var i = 0; i < kbItems.length; i++) {
                        if (kbItems[i].id === kbDetailOpenForId) {
                            target = kbItems[i];
                            break;
                        }
                    }
                    if (target) {
                        await openKbLinkedPanel(target);
                    } else if (kbLinkedPanel) {
                        kbLinkedPanel.classList.remove('open');
                        kbLinkedPanel.setAttribute('aria-hidden', 'true');
                        kbDetailOpenForId = null;
                    }
                }
            } catch (err) {
                setStatus(err.message || String(err));
            }
        }

        function openHistoryDrawer() {
            renderHistoryList();
            refreshKbListAndRender();
            setDrawerTab('history');
            kbDetailOpenForId = null;
            if (historyOverlay) {
                historyOverlay.classList.add('open');
                historyOverlay.setAttribute('aria-hidden', 'false');
            }
            if (historyDrawer) {
                historyDrawer.classList.add('open');
                historyDrawer.setAttribute('aria-hidden', 'false');
            }
        }

        function renderHistoryList() {
            if (!historyList) return;
            historyList.innerHTML = '';
            var sessions = loadAllSessionsFromStorage().slice();
            sessions.sort(function (a, b) { return (b.updatedAt || 0) - (a.updatedAt || 0); });
            if (!sessions.length) {
                var empty = document.createElement('div');
                empty.className = 'history-empty';
                empty.textContent = '暂无历史对话';
                historyList.appendChild(empty);
                return;
            }
            for (var si = 0; si < sessions.length; si++) {
                (function (sess) {
                    var row = document.createElement('div');
                    row.className = 'history-row' + (sess.id === currentSessionId ? ' active' : '');
                    var btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'history-item-main';
                    btn.textContent = sess.title || '未命名对话';
                    btn.addEventListener('click', function () {
                        selectHistorySession(sess.id);
                        closeHistoryDrawer();
                    });
                    var delBtn = document.createElement('button');
                    delBtn.type = 'button';
                    delBtn.className = 'history-item-delete';
                    delBtn.setAttribute('aria-label', '删除此对话');
                    delBtn.title = '删除';
                    delBtn.textContent = '×';
                    delBtn.addEventListener('click', function (e) {
                        e.preventDefault();
                        e.stopPropagation();
                        deleteHistorySession(sess.id);
                    });
                    row.appendChild(btn);
                    row.appendChild(delBtn);
                    historyList.appendChild(row);
                })(sessions[si]);
            }
        }

        function deleteHistorySession(id) {
            if (!confirm('确定删除这条历史对话？此操作不可恢复。')) return;
            var all = loadAllSessionsFromStorage();
            var next = [];
            for (var i = 0; i < all.length; i++) {
                if (all[i].id !== id) next.push(all[i]);
            }
            saveAllSessionsToStorage(next);
            if (id === currentSessionId) {
                resetChat();
            }
            renderHistoryList();
            setStatus('已删除历史记录');
            setTimeout(function () { setStatus('就绪'); }, 800);
        }

        function selectHistorySession(id) {
            var all = loadAllSessionsFromStorage();
            var sess = null;
            for (var i = 0; i < all.length; i++) {
                if (all[i].id === id) {
                    sess = all[i];
                    break;
                }
            }
            if (!sess || !Array.isArray(sess.messages)) return;
            if (chatInFlight && chatAbortController) {
                chatCancelReason = 'reset';
                try { chatAbortController.abort(); } catch (e) {}
            }
            chatInFlight = false;
            chatAbortController = null;
            chatCancelReason = null;
            setSendBtnBusy(false);
            clearPendingAttachments();
            hidePlusMenu();
            currentSessionId = sess.id;
            sessionMessages = JSON.parse(JSON.stringify(sess.messages));
            if (chatBox) chatBox.innerHTML = '';
            for (var j = 0; j < sessionMessages.length; j++) {
                var m = sessionMessages[j];
                appendMessage(m.role, m.text, m.contexts || [], false);
            }
            setChatBoxActive(sessionMessages.length > 0);
            if (welcomeText) welcomeText.style.display = sessionMessages.length ? 'none' : 'block';
            setStatus('已载入历史对话');
            setTimeout(function () { setStatus('就绪'); }, 600);
        }

        function revokeAttachmentPreview(item) {
            if (item && item.previewUrl) {
                URL.revokeObjectURL(item.previewUrl);
            }
        }

        function removePendingAttachmentAt(index) {
            if (index < 0 || index >= pendingAttachments.length) return;
            revokeAttachmentPreview(pendingAttachments[index]);
            pendingAttachments.splice(index, 1);
            renderAttachmentStrip();
        }

        function clearPendingAttachments() {
            for (var i = 0; i < pendingAttachments.length; i++) {
                revokeAttachmentPreview(pendingAttachments[i]);
            }
            pendingAttachments = [];
            renderAttachmentStrip();
        }

        function enqueuePendingFile(file, processingText) {
            var isImg = !!(file.type && file.type.indexOf('image/') === 0) ||
                /\\.(jpe?g|png|gif|webp|bmp)$/i.test(file.name || '');
            var previewUrl = isImg ? URL.createObjectURL(file) : null;
            var item = {
                text: '',
                name: file.name || '附件',
                previewUrl: previewUrl,
                kind: isImg ? 'image' : 'file',
                processing: true,
                processingText: processingText || '处理中…'
            };
            pendingAttachments.push(item);
            renderAttachmentStrip();
            return item;
        }

        function finishPendingFile(item, text) {
            if (!item) return;
            item.text = (text || '').trim();
            item.processing = false;
            item.processingText = '';
            renderAttachmentStrip();
        }

        function failPendingFile(item, msg) {
            if (!item) return;
            item.processing = false;
            item.processingText = '';
            item.text = '';
            item.name = (item.name || '附件') + '（失败）';
            renderAttachmentStrip();
            if (msg) setStatus(msg);
        }

        function buildAttachmentPayload() {
            var chunks = [];
            for (var i = 0; i < pendingAttachments.length; i++) {
                var item = pendingAttachments[i];
                var txt = (item.text || '').trim();
                if (!txt) continue;
                chunks.push('【' + (item.name || ('附件' + (i + 1))) + '】\\n' + txt);
            }
            return chunks.join('\\n\\n');
        }

        function buildAttachmentCaption() {
            if (!pendingAttachments.length) return '';
            if (pendingAttachments.length === 1) return pendingAttachments[0].name || '附件';
            return pendingAttachments.length + ' 个附件';
        }

        function renderAttachmentStrip() {
            if (!attachmentStrip) return;
            attachmentStrip.innerHTML = '';
            attachmentStrip.classList.remove('has-items');
            if (!pendingAttachments.length) return;
            attachmentStrip.classList.add('has-items');
            for (var i = 0; i < pendingAttachments.length; i++) {
                (function (idx) {
                    var item = pendingAttachments[idx];
                    var chip = document.createElement('div');
                    chip.className = 'attachment-chip';
                    if (item.kind === 'image' && item.previewUrl) {
                        var img = document.createElement('img');
                        img.className = 'attachment-thumb';
                        img.alt = '';
                        img.src = item.previewUrl;
                        chip.appendChild(img);
                    } else {
                        var ph = document.createElement('div');
                        ph.className = 'attachment-thumb file-icon';
                        ph.textContent = '📄';
                        chip.appendChild(ph);
                    }
                    var meta = document.createElement('span');
                    meta.className = 'attachment-meta';
                    meta.textContent = item.processing ? (item.processingText || '处理中…') : (item.name || '附件');
                    chip.appendChild(meta);
                    var rm = document.createElement('button');
                    rm.type = 'button';
                    rm.className = 'attachment-remove';
                    rm.setAttribute('aria-label', '移除附件');
                    rm.textContent = '×';
                    rm.addEventListener('click', function (e) {
                        e.preventDefault();
                        removePendingAttachmentAt(idx);
                        setStatus('已移除附件');
                    });
                    chip.appendChild(rm);
                    attachmentStrip.appendChild(chip);
                })(i);
            }
        }

        async function postOcrImage(file, pendingItem) {
            setStatus('识别图片中…');
            const fd = new FormData();
            fd.append('file', file, file.name);
            let resp;
            try {
                resp = await fetch(apiUrl('/api/ocr/image'), { method: 'POST', body: fd });
            } catch (err) {
                throw new Error(explainFetchError(err));
            }
            let data = null;
            try {
                data = await resp.json();
            } catch (e) {
                data = null;
            }
            if (!resp.ok) {
                const msg = (data && data.detail) ? (Array.isArray(data.detail) ? data.detail[0].msg : data.detail) : ('HTTP ' + resp.status);
                throw new Error(msg);
            }
            finishPendingFile(pendingItem, data.text);
            if (!(data.text || '').trim()) {
                setStatus('未识别到文字，已关联图片；可输入问题后发送（仅发送您输入的内容）');
            } else {
                setStatus('识别完成，内容将随发送一并提交（未写入输入框）');
            }
        }

        async function postUploadFile(file, pendingItem) {
            setStatus('上传并解析文件…');
            const fd = new FormData();
            fd.append('file', file, file.name);
            let resp;
            try {
                resp = await fetch(apiUrl('/api/upload/file'), { method: 'POST', body: fd });
            } catch (err) {
                throw new Error(explainFetchError(err));
            }
            let data = null;
            try {
                data = await resp.json();
            } catch (e) {
                data = null;
            }
            if (!resp.ok) {
                const msg = (data && data.detail) ? (Array.isArray(data.detail) ? data.detail[0].msg : data.detail) : ('HTTP ' + resp.status);
                throw new Error(msg);
            }
            finishPendingFile(pendingItem, data.text);
            if (!(data.text || '').trim()) {
                setStatus('未提取到文本；文件已关联，可输入问题后发送（仅发送您输入的内容）');
            } else {
                setStatus('已解析「' + (file.name || '文件') + '」，内容将随发送一并提交');
            }
        }

        function setChatBoxActive(active) {
            if (chatBox) chatBox.classList.toggle('active', active);
        }

        function createAvatar(role) {
            const avatar = document.createElement('span');
            if (role === 'user') {
                avatar.className = 'avatar avatar-user';
                avatar.textContent = '我';
            } else {
                avatar.className = 'avatar avatar-bot';
                avatar.textContent = '助';
            }
            return avatar;
        }

        function appendMessage(role, text, contexts, record) {
            if (record !== false) {
                sessionMessages.push({
                    role: role,
                    text: text,
                    contexts: Array.isArray(contexts) ? contexts : []
                });
                persistCurrentSession();
            }
            const wrap = document.createElement('div');
            wrap.className = 'msg ' + (role === 'user' ? 'msg-user' : 'msg-bot');

            const bubble = document.createElement('div');
            bubble.className = 'bubble';
            bubble.textContent = text;

            if (role === 'user') {
                wrap.appendChild(bubble);
                wrap.appendChild(createAvatar(role));
            } else {
                wrap.appendChild(createAvatar(role));
                const contentWrap = document.createElement('div');
                contentWrap.style.maxWidth = 'calc(100% - 40px)';
                contentWrap.appendChild(bubble);

                if (Array.isArray(contexts) && contexts.length > 0) {
                    const ctxDiv = document.createElement('div');
                    ctxDiv.className = 'contexts';
                    ctxDiv.innerHTML = '<strong>参考片段</strong><br>' + contexts.map((c, idx) =>
                        `【${idx + 1}】来源：${c.source}<br/>相关度：${Number(c.score || 0).toFixed(3)}<br/>预览：${c.text_preview}`
                    ).join('<br><br>');
                    contentWrap.appendChild(ctxDiv);
                }
                wrap.appendChild(contentWrap);
            }

            if (chatBox) {
                chatBox.appendChild(wrap);
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        }

        function resetChat() {
            if (chatInFlight && chatAbortController) {
                chatCancelReason = 'reset';
                try { chatAbortController.abort(); } catch (e) {}
            } else {
                chatCancelReason = null;
            }
            chatInFlight = false;
            chatAbortController = null;
            setSendBtnBusy(false);
            currentSessionId = null;
            sessionMessages = [];
            if (chatBox) chatBox.innerHTML = '';
            setChatBoxActive(false);
            hidePlusMenu();
            clearPendingAttachments();
            if (welcomeText) welcomeText.style.display = 'block';
            setStatus('就绪');
        }

        async function sendQuestion() {
            if (!questionInput) {
                setStatus('页面未就绪，请刷新重试');
                return;
            }
            if (chatInFlight) {
                setStatus('回答生成中，可点击蓝色按钮停止');
                return;
            }
            const q = questionInput.value.trim();
            const attachPayload = buildAttachmentPayload();
            if (!q && !attachPayload) {
                setStatus('请输入问题，或先上传并完成识别后再发送');
                try { questionInput.focus(); } catch (e) {}
                return;
            }

            if (welcomeText) welcomeText.style.display = 'none';
            var userShow = q;
            var attachCaption = buildAttachmentCaption();
            if (attachCaption) {
                userShow = q
                    ? (q + '\\n（附件：' + attachCaption + '）')
                    : ('（附件：' + attachCaption + '）');
            }
            appendMessage('user', userShow);
            questionInput.value = '';
            autoResizeInput();

            chatAbortController = new AbortController();
            chatInFlight = true;
            setSendBtnBusy(true);
            setStatus('检索中');

            try {
                let resp;
                try {
                    resp = await fetch(apiUrl('/chat'), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        signal: chatAbortController.signal,
                        body: JSON.stringify({ question: q, attachment_text: attachPayload, kb_id: selectedKbId })
                    });
                } catch (err) {
                    if (err && err.name === 'AbortError') {
                        throw err;
                    }
                    throw new Error(explainFetchError(err));
                }
                if (!resp.ok) {
                    throw new Error('请求失败，状态码：' + resp.status);
                }
                const data = await resp.json();
                appendMessage('bot', data.answer || '后端未返回回答。', data.contexts || []);
                setChatBoxActive(true);
                setStatus('完成');
                clearPendingAttachments();
            } catch (err) {
                if (err && err.name === 'AbortError') {
                    const reason = chatCancelReason;
                    chatCancelReason = null;
                    if (reason === 'user') {
                        appendMessage('bot', '已停止本次回答。', []);
                        setChatBoxActive(true);
                        setStatus('已停止');
                    }
                } else {
                    console.error(err);
                    appendMessage('bot', '请求后端失败，请检查服务是否在运行，或稍后再试。', []);
                    setChatBoxActive(true);
                    setStatus('异常');
                }
            } finally {
                chatInFlight = false;
                chatAbortController = null;
                setSendBtnBusy(false);
                setTimeout(function () { setStatus('就绪'); }, 800);
            }
        }

        if (menuBtn) {
            menuBtn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                hidePlusMenu();
                openHistoryDrawer();
            });
        }
        if (tabHistory) {
            tabHistory.addEventListener('click', function () {
                setDrawerTab('history');
            });
        }
        if (tabKb) {
            tabKb.addEventListener('click', function () {
                setDrawerTab('kb');
                refreshKbListAndRender();
            });
        }
        if (kbCreateBtn) {
            kbCreateBtn.addEventListener('click', async function () {
                var name = (kbNameInput && kbNameInput.value) ? kbNameInput.value.trim() : '';
                if (!name) {
                    setStatus('请输入知识库名称');
                    return;
                }
                setStatus('创建知识库中…');
                try {
                    const resp = await fetch(apiUrl('/api/kb/create'), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: name })
                    });
                    const data = await resp.json();
                    if (!resp.ok) throw new Error((data && data.detail) ? data.detail : ('HTTP ' + resp.status));
                    if (kbNameInput) kbNameInput.value = '';
                    selectedKbId = data.id;
                    localStorage.setItem(KB_SELECTED_KEY, selectedKbId);
                    await refreshKbListAndRender();
                    setStatus('知识库已创建：' + (data.name || data.id));
                } catch (err) {
                    setStatus('创建失败：' + (err.message || err));
                }
            });
        }
        async function uploadKbFileWithProgress(kbId, file, index, total) {
            return await new Promise(function (resolve, reject) {
                var xhr = new XMLHttpRequest();
                xhr.open('POST', apiUrl('/api/kb/upload'));
                xhr.responseType = 'json';

                xhr.upload.onprogress = function (evt) {
                    if (evt.lengthComputable && evt.total > 0) {
                        var p = Math.round((evt.loaded / evt.total) * 100);
                        setStatus('文件传输中（' + index + '/' + total + '）：' + file.name + ' ' + p + '%');
                    } else {
                        setStatus('文件传输中（' + index + '/' + total + '）：' + file.name);
                    }
                };

                xhr.onload = function () {
                    var data = xhr.response;
                    if (!data && xhr.responseText) {
                        try { data = JSON.parse(xhr.responseText); } catch (e) {}
                    }
                    if (xhr.status >= 200 && xhr.status < 300) {
                        resolve(data || {});
                    } else {
                        reject(new Error((data && data.detail) ? data.detail : ('HTTP ' + xhr.status)));
                    }
                };

                xhr.onerror = function () {
                    reject(new Error('网络错误，上传失败'));
                };

                var fd = new FormData();
                fd.append('kb_id', kbId);
                fd.append('file', file, file.name);
                xhr.send(fd);
            });
        }

        async function waitKbRebuildProgress(kbId) {
            var maxLoop = 360;
            for (var i = 0; i < maxLoop; i++) {
                let resp;
                try {
                    resp = await fetch(apiUrl('/api/kb/' + encodeURIComponent(kbId) + '/progress'));
                } catch (err) {
                    setStatus('查询分片进度失败，稍后重试…');
                    await new Promise(function (r) { setTimeout(r, 700); });
                    continue;
                }
                const data = await resp.json().catch(function () { return {}; });
                if (!resp.ok) {
                    setStatus('查询分片进度失败：HTTP ' + resp.status);
                    await new Promise(function (r) { setTimeout(r, 700); });
                    continue;
                }

                var total = Number(data.total_chunks || 0);
                var done = Number(data.processed_chunks || 0);
                var msg = data.message || '';
                if (total > 0) {
                    var p = Math.max(0, Math.min(100, Math.round(done * 100 / total)));
                    setStatus('分片处理中：' + done + '/' + total + '（' + p + '%）' + (msg ? ' - ' + msg : ''));
                } else {
                    setStatus(msg || '分片处理中…');
                }

                if (data.done) {
                    if (msg && msg.indexOf('失败') >= 0) {
                        throw new Error(msg);
                    }
                    return;
                }
                await new Promise(function (r) { setTimeout(r, 700); });
            }
            throw new Error('等待分片进度超时');
        }

        if (kbFileInput) {
            kbFileInput.addEventListener('change', async function (e) {
                var files = Array.from(e.target.files || []);
                e.target.value = '';
                if (!files.length) return;
                if (!kbUploadTargetId) {
                    setStatus('请先选择知识库再上传');
                    return;
                }

                var total = files.length;
                var ok = 0;
                var lastData = null;
                try {
                    for (var i = 0; i < files.length; i++) {
                        var f = files[i];
                        var idx = i + 1;
                        setStatus('准备上传（' + idx + '/' + total + '）：' + f.name);
                        var data = await uploadKbFileWithProgress(kbUploadTargetId, f, idx, total);
                        lastData = data;
                        ok++;
                        await waitKbRebuildProgress(kbUploadTargetId);
                    }

                    if (lastData && lastData.id) {
                        selectedKbId = lastData.id;
                        localStorage.setItem(KB_SELECTED_KEY, selectedKbId);
                    }
                    await refreshKbListAndRender();
                    setStatus('知识库导入完成：成功 ' + ok + ' / ' + total);
                } catch (err) {
                    await refreshKbListAndRender();
                    setStatus('知识库导入中断：已成功 ' + ok + ' / ' + total + '，原因：' + (err.message || err));
                } finally {
                    kbUploadTargetId = null;
                }
            });
        }
        if (historyOverlay) {
            historyOverlay.addEventListener('click', function () {
                closeHistoryDrawer();
            });
        }
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                closeHistoryDrawer();
            }
        });

        if (sendBtn) {
            sendBtn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                if (chatInFlight && chatAbortController) {
                    chatCancelReason = 'user';
                    try { chatAbortController.abort(); } catch (err) {}
                    return;
                }
                sendQuestion();
            });
        }
        if (questionInput) {
            questionInput.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendQuestion();
                }
            });
            questionInput.addEventListener('input', autoResizeInput);
        }
        if (plusBtn && plusMenu) {
            plusBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                plusMenu.classList.toggle('show');
            });
        }
        document.addEventListener('click', function (e) {
            if (!plusMenu || !plusBtn) return;
            var t = e.target;
            if (plusMenu.contains(t) || t === plusBtn || plusBtn.contains(t)) return;
            hidePlusMenu();
        });

        if (plusBtnCamera && fileCamera) {
            plusBtnCamera.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                hidePlusMenu();
                fileCamera.click();
            });
        }
        if (plusBtnImage && fileImage) {
            plusBtnImage.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                hidePlusMenu();
                fileImage.click();
            });
        }
        if (plusBtnFile && fileDoc) {
            plusBtnFile.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                hidePlusMenu();
                fileDoc.click();
            });
        }

        if (fileCamera) fileCamera.addEventListener('change', async function (e) {
            const f = e.target.files && e.target.files[0];
            e.target.value = '';
            if (!f) return;
            var item = enqueuePendingFile(f, '识别中…');
            try {
                await postOcrImage(f, item);
            } catch (err) {
                console.error(err);
                failPendingFile(item, '识别失败：' + (err.message || err));
            }
        });
        if (fileImage) fileImage.addEventListener('change', async function (e) {
            const files = Array.from((e.target.files || []));
            e.target.value = '';
            if (!files.length) return;
            var ok = 0;
            for (var i = 0; i < files.length; i++) {
                var item = enqueuePendingFile(files[i], '识别中…');
                try {
                    await postOcrImage(files[i], item);
                    ok++;
                } catch (err) {
                    console.error(err);
                    failPendingFile(item, '第 ' + (i + 1) + ' 张识别失败：' + (err.message || err));
                }
            }
            if (ok > 0) setStatus('已导入 ' + ok + ' 张图片');
        });
        if (fileDoc) fileDoc.addEventListener('change', async function (e) {
            const files = Array.from((e.target.files || []));
            e.target.value = '';
            if (!files.length) return;
            var ok = 0;
            for (var i = 0; i < files.length; i++) {
                var item = enqueuePendingFile(files[i], '解析中…');
                try {
                    await postUploadFile(files[i], item);
                    ok++;
                } catch (err) {
                    console.error(err);
                    failPendingFile(item, '第 ' + (i + 1) + ' 个文件上传失败：' + (err.message || err));
                }
            }
            if (ok > 0) setStatus('已导入 ' + ok + ' 个文件');
        });

        resetChat();
        autoResizeInput();
    </script>
</body>
</html>
    """


def _effective_rag_query(question: str, attachment_text: str) -> str:
    q = (question or "").strip()
    a = (attachment_text or "").strip()
    if q and a:
        return f"{q}\n\n【用户上传/识别内容】\n{a}"
    if a:
        return f"【用户上传/识别内容】\n{a}"
    return q


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    """核心聊天接口：接收问题，返回回答和参考片段。"""
    q = (body.question or "").strip()
    a = (body.attachment_text or "").strip()
    if not q and not a:
        return ChatResponse(answer="请输入问题，或先上传文件完成识别后再发送。", contexts=[])

    try:
        answer, contexts_raw = rag_answer(
            _effective_rag_query(q, a),
            kb_id=_resolve_rag_kb_id(body.kb_id),
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    contexts: List[ContextSnippet] = []
    for c in contexts_raw:
        text = c.get("text", "") or ""
        if len(text) > 200:
            text = text[:200] + "..."
        contexts.append(
            ContextSnippet(
                source=str(c.get("source", "")),
                text_preview=text,
                score=float(c.get("score", 0.0)),
            )
        )

    return ChatResponse(answer=answer, contexts=contexts)

