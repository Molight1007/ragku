from __future__ import annotations

import asyncio
import secrets
import shutil
import threading
import time
import uuid
from http import HTTPStatus
from pathlib import Path
from typing import List, Optional, Tuple

import dashscope

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

# 新上传系统导入
from upload_api import router as upload_router, init_upload_system
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from pydantic import BaseModel

from config import settings
from rag_service import load_index, rag_answer, rag_answer_filtered

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
    if base == LEGACY_KB_ID:
        return LEGACY_KB_ID
    if base.isdigit():
        return base
    return ""


def _new_kb_id() -> str:
    return str(secrets.randbelow(10**12 - 10**11) + 10**11)


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
    selected_files: Optional[List[str]] = None


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


class VisionChatRequest(BaseModel):
    """看图分析聊天请求模型。"""

    question: str = ""
    kb_id: Optional[str] = None
    selected_files: Optional[List[str]] = None


class VisionChatResponse(BaseModel):
    """看图分析聊天返回数据结构。"""

    answer: str
    contexts: List[ContextSnippet]
    image_analysis: str  # 图片分析结果


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
    estimated_remaining_seconds: int = -1


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
KB_CANCEL_REBUILD: set[str] = set()


def _build_embeddings_for_kb_with_progress(docs: List[tuple[str, str]], kb_id: str):
    if not settings.dashscope_api_key:
        raise RuntimeError("未检测到 DASHSCOPE_API_KEY，请先在环境变量或 .env 中配置。")

    if not docs:
        raise RuntimeError("没有可向量化的文本分片。")

    import concurrent.futures
    from dashscope import TextEmbedding

    dashscope.api_key = settings.dashscope_api_key

    # 并发数设置（DashScope QPS 限制约为 10，并发 8 留有余量）
    MAX_CONCURRENCY = 8
    total = len(docs)

    with KB_UPLOAD_LOCK:
        KB_UPLOAD_PROGRESS[kb_id] = {
            "total": total,
            "processed": 0,
            "done": False,
            "message": "开始分片向量化（并发模式）",
            "start_time": time.time(),
        }

    results: List[Tuple[int, List[float], dict]] = []
    results_lock = threading.Lock()

    def _process_single(idx: int, source: str, text: str) -> Tuple[int, List[float], dict] | None:
        """处理单个分片，返回 (索引, 向量, 元数据) 或 None（失败时）"""
        with KB_UPLOAD_LOCK:
            if kb_id in KB_CANCEL_REBUILD:
                raise RuntimeError("重建已取消")

        try:
            resp = TextEmbedding.call(model=settings.embedding_model, input=text)
            status = getattr(resp, "status_code", None)
            if status != HTTPStatus.OK:
                code = getattr(resp, "code", "")
                msg = getattr(resp, "message", "") or str(resp)
                with KB_UPLOAD_LOCK:
                    p = KB_UPLOAD_PROGRESS[kb_id]
                    p["processed"] = max(p["processed"], idx)
                    p["message"] = f"第 {idx}/{total} 分片失败: {code} {msg}".strip()
                return None

            output = resp.output if hasattr(resp, "output") else resp["output"]
            emb_list = output["embeddings"] if isinstance(output, dict) else output.embeddings
            vector = emb_list[0]["embedding"] if isinstance(emb_list[0], dict) else emb_list[0].embedding
            return (idx, list(vector), {"source": source, "text": text})
        except Exception as e:
            with KB_UPLOAD_LOCK:
                p = KB_UPLOAD_PROGRESS[kb_id]
                p["processed"] = max(p["processed"], idx)
                p["message"] = f"第 {idx}/{total} 分片异常: {e}"
            return None

    # 使用线程池并发处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as executor:
        futures = {
            executor.submit(_process_single, i + 1, src, txt): (i + 1, src)
            for i, (src, txt) in enumerate(docs)
        }

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result is not None:
                    idx, vector, meta = result
                    with results_lock:
                        results.append((idx, vector, meta))
                    with KB_UPLOAD_LOCK:
                        KB_UPLOAD_PROGRESS[kb_id]["processed"] = len(results)
                        KB_UPLOAD_PROGRESS[kb_id]["message"] = f"分片向量化进度 {len(results)}/{total}"
            except Exception:
                pass

    # 按原始顺序排列结果
    results.sort(key=lambda x: x[0])
    embeddings = [r[1] for r in results]
    metadatas = [r[2] for r in results]

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

    # 使用随机数字 ID，避免中文名称经 _safe_kb_id 过滤后变空导致死循环
    kb_id = _new_kb_id()
    while _kb_dir(kb_id).exists():
        kb_id = _new_kb_id()

    _kb_files_dir(kb_id).mkdir(parents=True, exist_ok=True)
    _kb_name_file(kb_id).write_text(kb_name, encoding="utf-8")
    return KnowledgeBaseInfo(id=kb_id, name=kb_name, file_count=0)



@app.post("/api/kb/upload", response_model=KnowledgeBaseInfo)
async def api_kb_upload(
    kb_id: str = Form(...), 
    file: UploadFile = File(..., max_length=MAX_FILE_SIZE)
) -> KnowledgeBaseInfo:
    """上传文件到知识库（新版，使用分块上传系统）"""
    from upload_api import upload_file_complete
    
    try:
        # 使用新上传系统的完整API
        result = await upload_file_complete(
            kb_id=kb_id,
            file=file,
            priority="normal"
        )
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.message)
        
        # 转换为旧API格式
        base = _kb_dir(kb_id)
        files_dir = _kb_files_dir(kb_id)
        file_count = len([x for x in files_dir.rglob("*") if x.is_file()]) if files_dir.exists() else 0
        total_size = sum(p.stat().st_size for p in files_dir.glob("*") if p.is_file())
        
        # 获取知识库名称
        kb_name = "未知"
        name_file = _kb_name_file(kb_id)
        if name_file.exists():
            try:
                kb_name = name_file.read_text(encoding="utf-8").strip()
            except:
                pass
        
        return KnowledgeBaseInfo(
            id=kb_id,
            name=kb_name,
            file_count=file_count,
            total_size=total_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

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

    # 计算预估剩余时间
    estimated_remaining = -1
    total = int(p.get("total", 0))
    processed = int(p.get("processed", 0))
    start_time = p.get("start_time")
    done = bool(p.get("done", False))

    if not done and start_time and processed > 0 and total > processed:
        elapsed = time.time() - start_time
        avg_time_per_chunk = elapsed / processed
        remaining_chunks = total - processed
        estimated_remaining = int(avg_time_per_chunk * remaining_chunks)

    return KnowledgeBaseUploadProgress(
        total_chunks=total,
        processed_chunks=processed,
        done=done,
        message=str(p.get("message", "")),
        estimated_remaining_seconds=estimated_remaining,
    )


@app.get("/api/kb/{kb_id}/files", response_model=KnowledgeBaseFileListResponse)
async def api_kb_files(kb_id: str) -> KnowledgeBaseFileListResponse:
    safe_id = _safe_kb_id(kb_id)
    if safe_id == LEGACY_KB_ID:
        if not _legacy_index_exists():
            return KnowledgeBaseFileListResponse(kb_id=safe_id, items=[])
        try:
            _, metas = load_index(None)
        except Exception:
            return KnowledgeBaseFileListResponse(kb_id=safe_id, items=[])
        names = sorted({Path(str(m.get("source", "") or "")).name for m in metas if str(m.get("source", "") or "")})
        items = [KnowledgeBaseFileItem(name=n, rel_path=n, size=0) for n in names]
        return KnowledgeBaseFileListResponse(kb_id=safe_id, items=items)

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

    with KB_UPLOAD_LOCK:
        KB_CANCEL_REBUILD.add(safe_id)
        KB_REBUILD_RUNNING.discard(safe_id)
        KB_UPLOAD_PROGRESS.pop(safe_id, None)

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

    for fp in (_kb_index_file(safe_id), _kb_meta_file(safe_id)):
        if fp.exists():
            fp.unlink()
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
            padding: 12px 20px 10px 12px;
            border-bottom: 1px solid #eef0f5;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }
        .kb-linked-title {
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
            background: linear-gradient(90deg, rgba(74,111,212,0.18) var(--fill, 0%), #ffffff var(--fill, 0%));
            padding: 8px;
            margin-bottom: 8px;
            transition: background 0.18s ease, border-color 0.18s ease;
        }
        .kb-file-row.selected {
            background: linear-gradient(90deg, rgba(74,111,212,0.22) var(--fill, 0%), #f6f9ff var(--fill, 0%));
            border-color: #c9d5fb;
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
            color: #1f2330;
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
        .kb-file-pick {
            width: 28px;
            height: 28px;
            padding: 0;
            border: 1px solid #c7cbd6;
            border-radius: 8px;
            background: #fff;
            color: #111827;
            font-size: 15px;
            font-weight: 500;
            line-height: 1;
            cursor: pointer;
            transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
        }
        .kb-file-pick:hover {
            border-color: #8eaefb;
        }
        .kb-file-pick.selected {
            background: #4a6fd4;
            border-color: #4a6fd4;
            color: #fff;
            transform: scale(1.08);
        }
        .kb-file-actions {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin-left: 8px;
            flex-shrink: 0;
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
            color: #1f2330;
            transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
        }
        .kb-delete-x:hover {
            background: #fee2e2;
            color: #dc2626;
            border-color: #fecaca;
        }
        .kb-delete-x:disabled {
            cursor: not-allowed;
            color: #9ca3af;
            background: #fff;
            border-color: #d9dbe2;
            opacity: 1;
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
            color: #1f2330;
            font-size: 20px;
            line-height: 1;
            cursor: pointer;
            padding: 0;
            font-family: inherit;
            display: inline-flex;
            align-items: center;
            justify-content: center;
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
        <div class="welcome" id="welcomeText">你好，欢迎使用你的个人知识库</div>
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
                            <button class="plus-item" id="plusBtnAnalyze" type="button"><span class="plus-icon">🔍</span>看图分析</button>
                            <button class="plus-item" id="plusBtnVideo" type="button"><span class="plus-icon">🎬</span>视频分析</button>
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
        <div id="kbLinkedHead" class="kb-linked-head">
            <span id="kbLinkedTitle" class="kb-linked-title">知识库文件</span>
            <button id="kbPickAllBtn" type="button" class="kb-file-pick" title="全选文件">✓</button>
        </div>
        <div id="kbLinkedList" class="kb-linked-list"></div>
    </aside>
    <input type="file" id="kbFileInput" accept=".txt,.md,.pdf,.docx,.jpg,.jpeg,.png,.bmp,.webp,.gif" multiple style="display:none" />
    <input type="file" id="fileCamera" accept="image/*" capture="environment" style="display:none" />
    <input type="file" id="fileImage" accept="image/*" multiple style="display:none" />
    <input type="file" id="fileAnalyze" accept="image/*" style="display:none" />
    <input type="file" id="fileVideo" accept="video/*" style="display:none" />
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
        const plusBtnAnalyze = document.getElementById('plusBtnAnalyze');
        const plusBtnVideo = document.getElementById('plusBtnVideo');
        const plusBtnFile = document.getElementById('plusBtnFile');
        const fileCamera = document.getElementById('fileCamera');
        const fileImage = document.getElementById('fileImage');
        const fileAnalyze = document.getElementById('fileAnalyze');
        const fileVideo = document.getElementById('fileVideo');
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
        const kbLinkedTitle = document.getElementById('kbLinkedTitle');
        const kbPickAllBtn = document.getElementById('kbPickAllBtn');
        const kbLinkedList = document.getElementById('kbLinkedList');

        const STORAGE_KEY = 'ragku_chat_sessions_v1';
        const KB_SELECTED_KEY = 'ragku_selected_kb_id_v1';
        const KB_FILE_SELECTED_KEY = 'ragku_kb_file_selected_v1';
        const KB_UPLOAD_TRACK_KEY = 'ragku_upload_tracking_kb_v1';
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

        function cleanDisplayFileName(name) {
            return String(name || '').replace(/^[0-9a-f]{12}_/i, '');
        }

        function loadKbFileSelectionMap() {
            try {
                var raw = localStorage.getItem(KB_FILE_SELECTED_KEY);
                var obj = raw ? JSON.parse(raw) : {};
                return (obj && typeof obj === 'object') ? obj : {};
            } catch (e) {
                return {};
            }
        }

        function saveKbFileSelectionMap(mapObj) {
            try { localStorage.setItem(KB_FILE_SELECTED_KEY, JSON.stringify(mapObj || {})); } catch (e) {}
        }

        function getSelectedFilesForKb(kbId) {
            var m = loadKbFileSelectionMap();
            var arr = m[kbId];
            return Array.isArray(arr) ? arr : [];
        }

        function setSelectedFilesForKb(kbId, arr) {
            var m = loadKbFileSelectionMap();
            m[kbId] = Array.isArray(arr) ? arr : [];
            saveKbFileSelectionMap(m);
        }

        function setKbFileRowProgress(kbId, percent, message) {
            if (!kbLinkedPanel || !kbLinkedPanel.classList.contains('open')) return;
            if (!kbDetailOpenForId || kbDetailOpenForId !== kbId) return;
            var rows = kbLinkedList ? kbLinkedList.querySelectorAll('.kb-file-row[data-kb-id="' + kbId + '"]') : [];
            var p = Math.max(0, Math.min(100, Number(percent || 0)));
            for (var i = 0; i < rows.length; i++) {
                rows[i].style.setProperty('--fill', p + '%');
                rows[i].setAttribute('title', message || ('分片进度 ' + p + '%'));
            }
        }

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
                    deleteBtn.title = kb.id === 'legacy_fire' ? '默认知识库不可删除' : '删除知识库';
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
            if (!kbLinkedPanel || !kbLinkedList) return;
            if (kbLinkedTitle) kbLinkedTitle.textContent = (kb.name || kb.id) + ' · 文件';
            kbLinkedList.innerHTML = '<div class="history-empty">加载中…</div>';
            kbLinkedPanel.classList.add('open');
            kbLinkedPanel.setAttribute('aria-hidden', 'false');

            try {
                const files = await fetchKbFiles(kb.id);
                kbLinkedList.innerHTML = '';

                var selectedAllNow = getSelectedFilesForKb(kb.id);
                var allKeys = files.map(function (f) {
                    return cleanDisplayFileName(f.name || '');
                });
                var allPicked = allKeys.length > 0 && allKeys.every(function (k) { return selectedAllNow.indexOf(k) >= 0; });

                if (kbPickAllBtn) {
                    kbPickAllBtn.classList.toggle('selected', allPicked);
                    kbPickAllBtn.textContent = '✓';
                    kbPickAllBtn.onclick = function () {
                        var cur = getSelectedFilesForKb(kb.id);
                        var curAll = allKeys.length > 0 && allKeys.every(function (k) { return cur.indexOf(k) >= 0; });
                        if (curAll) {
                            setSelectedFilesForKb(kb.id, []);
                        } else {
                            setSelectedFilesForKb(kb.id, allKeys.slice());
                        }
                        openKbLinkedPanel(kb);
                    };
                }

                if (!files.length) {
                    var empty = document.createElement('div');
                    empty.className = 'history-empty';
                    empty.textContent = '该知识库暂无文件';
                    kbLinkedList.appendChild(empty);
                    return;
                }
                for (var i = 0; i < files.length; i++) {
                    (function (f) {
                        var row = document.createElement('div');
                        row.className = 'kb-file-row';
                        row.dataset.kbId = kb.id;

                        var top = document.createElement('div');
                        top.className = 'kb-file-row-top';

                        var left = document.createElement('div');
                        var n = document.createElement('div');
                        n.className = 'kb-file-name';
                        var rawName = f.name || f.rel_path || '未命名文件';
                        n.textContent = cleanDisplayFileName(rawName);
                        var m = document.createElement('div');
                        m.className = 'kb-file-meta';
                        m.textContent = '大小：' + _fmtSize(f.size || 0);
                        left.appendChild(n);
                        left.appendChild(m);

                        var pick = document.createElement('button');
                        pick.type = 'button';
                        pick.className = 'kb-file-pick';
                        pick.title = '选择文件';
                        pick.textContent = '✓';

                        var fileKey = cleanDisplayFileName(f.name || '');
                        var selectedFiles = getSelectedFilesForKb(kb.id);
                        var isPicked = selectedFiles.indexOf(fileKey) >= 0;
                        pick.classList.toggle('selected', isPicked);
                        row.classList.toggle('selected', isPicked);

                        pick.addEventListener('click', function () {
                            var cur = getSelectedFilesForKb(kb.id);
                            var idx = cur.indexOf(fileKey);
                            if (idx >= 0) {
                                cur.splice(idx, 1);
                            } else {
                                cur.push(fileKey);
                            }
                            setSelectedFilesForKb(kb.id, cur);
                            var nowPicked = cur.indexOf(fileKey) >= 0;
                            pick.classList.toggle('selected', nowPicked);
                            row.classList.toggle('selected', nowPicked);
                            var allNow = allKeys.length > 0 && allKeys.every(function (k) { return cur.indexOf(k) >= 0; });
                            if (kbPickAllBtn) kbPickAllBtn.classList.toggle('selected', allNow);
                            setStatus('已更新检索文件选择：' + cur.length + ' 个');
                        });

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
                                var cur = getSelectedFilesForKb(kb.id).filter(function (x) { return x !== fileKey; });
                                setSelectedFilesForKb(kb.id, cur);
                                await refreshKbListAndRender();
                                await openKbLinkedPanel(kb);
                                setStatus('删除完成并已重建索引');
                            } catch (err) {
                                setStatus('删除失败：' + (err.message || err));
                            }
                        });

                        var actions = document.createElement('div');
                        actions.className = 'kb-file-actions';
                        actions.appendChild(del);
                        actions.appendChild(pick);

                        top.appendChild(left);
                        top.appendChild(actions);
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
            if (text === '未选择知识库文件' || text === '当前并未选择文件' || text === '当前并未选择知识库文件') {
                bubble.classList.add('no-wrap');
            }

            if (bubble.classList.contains('no-wrap')) {
                bubble.style.maxWidth = 'none';
            }

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

        function resetChat(skipStatusReset) {
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
            if (!skipStatusReset) {
                setStatus('就绪');
            }
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
                        body: JSON.stringify({
                            question: q,
                            attachment_text: attachPayload,
                            kb_id: selectedKbId,
                            selected_files: selectedKbId ? getSelectedFilesForKb(selectedKbId) : []
                        })
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
                    const data = await resp.json().catch(function () { return null; });
                    if (!resp.ok) {
                        if (data && data.detail) throw new Error(data.detail);
                        throw new Error('创建失败（HTTP ' + resp.status + '），请查看后端日志');
                    }
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

        function saveUploadTracking(kbId) {
            try { localStorage.setItem(KB_UPLOAD_TRACK_KEY, JSON.stringify({ kb_id: kbId, ts: Date.now() })); } catch (e) {}
        }

        function clearUploadTracking() {
            try { localStorage.removeItem(KB_UPLOAD_TRACK_KEY); } catch (e) {}
        }

        function loadUploadTracking() {
            try {
                var raw = localStorage.getItem(KB_UPLOAD_TRACK_KEY);
                if (!raw) return null;
                var o = JSON.parse(raw);
                if (!o || !o.kb_id) return null;
                return o;
            } catch (e) {
                return null;
            }
        }

        function _fmtRemainingTime(seconds) {
            if (!seconds || seconds < 0) return '';
            if (seconds < 60) return '约 ' + seconds + '秒';
            if (seconds < 3600) {
                var m = Math.floor(seconds / 60);
                var s = seconds % 60;
                return '约 ' + m + '分' + (s > 0 ? s + '秒' : '');
            }
            var h = Math.floor(seconds / 3600);
            var m = Math.floor((seconds % 3600) / 60);
            return '约 ' + h + '小时' + (m > 0 ? m + '分' : '');
        }

        async function waitKbRebuildProgress(kbId, persistTracking) {
            if (persistTracking) saveUploadTracking(kbId);
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
                var remaining = data.estimated_remaining_seconds;
                var remainingText = _fmtRemainingTime(remaining);
                if (total > 0) {
                    var p = Math.max(0, Math.min(100, Math.round(done * 100 / total)));
                    var statusText = '分片处理中：' + done + '/' + total + '（' + p + '%）';
                    if (remainingText) statusText += '，剩余 ' + remainingText;
                    if (msg) statusText += ' - ' + msg;
                    setStatus(statusText);
                    setKbFileRowProgress(kbId, p, statusText);
                } else {
                    setStatus(msg || '分片处理中…');
                    setKbFileRowProgress(kbId, 0, msg);
                }

                if (data.done) {
                    if (msg && msg.indexOf('失败') >= 0) {
                        setKbFileRowProgress(kbId, 0, msg);
                        clearUploadTracking();
                        throw new Error(msg);
                    }
                    setKbFileRowProgress(kbId, 100, msg || '完成');
                    clearUploadTracking();
                    return;
                }
                await new Promise(function (r) { setTimeout(r, 700); });
            }
            clearUploadTracking();
            throw new Error('等待分片进度超时');
        }

        async function resumeUploadProgressIfNeeded() {
            var t = loadUploadTracking();
            if (!t || !t.kb_id) return;
            setStatus('检测到上次有进行中的索引任务，正在恢复进度…');
            try {
                await waitKbRebuildProgress(t.kb_id, false);
                setStatus('索引任务已完成');
                setTimeout(function () { setStatus('就绪'); }, 900);
            } catch (err) {
                setStatus('恢复进度失败：' + (err.message || err));
            }
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
                        await waitKbRebuildProgress(kbUploadTargetId, true);
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
        if (plusBtnAnalyze && fileAnalyze) {
            plusBtnAnalyze.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                hidePlusMenu();
                fileAnalyze.click();
            });
        }
        if (plusBtnVideo && fileVideo) {
            plusBtnVideo.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                hidePlusMenu();
                fileVideo.click();
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

        // 看图分析：上传图片并输入问题，调用多模态RAG
        if (fileAnalyze) fileAnalyze.addEventListener('change', async function (e) {
            const f = e.target.files && e.target.files[0];
            e.target.value = '';
            if (!f) return;

            // 弹出问题输入框
            var question = window.prompt('请输入您的问题（可选，不填则自动分析图片）：\n\n例如：\n- 我的乒乓球姿势哪里不对？\n- 这张图片里有什么？\n- 这个动作规范吗？', '');
            if (question === null) {
                setStatus('已取消');
                return;
            }
            question = (question || '').trim();

            setStatus('分析图片中…');

            // 创建预览
            const previewUrl = URL.createObjectURL(f);

            // 添加用户消息
            var userShow = question || '（请分析这张图片）';
            appendMessage('user', userShow + '\n\n[图片]', []);

            // 显示图片预览
            if (welcomeText) welcomeText.style.display = 'none';

            // 调用多模态聊天API
            chatAbortController = new AbortController();
            chatInFlight = true;
            setSendBtnBusy(true);

            try {
                const fd = new FormData();
                fd.append('file', f, f.name);
                fd.append('question', question || '请详细描述这张图片的内容');
                fd.append('kb_id', selectedKbId || '');
                fd.append('selected_files', selectedKbId ? (getSelectedFilesForKb(selectedKbId) || []).join(',') : '');

                const resp = await fetch(apiUrl('/chat/vision'), {
                    method: 'POST',
                    body: fd,
                    signal: chatAbortController.signal,
                });

                if (!resp.ok) {
                    const data = await resp.json().catch(() => ({}));
                    const msg = (data && data.detail) ? data.detail : ('HTTP ' + resp.status);
                    throw new Error(msg);
                }

                const data = await resp.json();

                // 显示AI回答
                var botContexts = [];
                if (data.contexts && data.contexts.length > 0) {
                    botContexts = data.contexts;
                }
                appendMessage('assistant', data.answer, botContexts);

                // 显示图片分析详情（如果有知识库）
                if (data.image_analysis && data.contexts && data.contexts.length > 0) {
                    setStatus('分析完成，已结合知识库给出回答');
                } else {
                    setStatus('分析完成');
                }

            } catch (err) {
                if (err && err.name === 'AbortError') {
                    appendMessage('assistant', '（已停止）', []);
                    setStatus('已停止');
                } else {
                    console.error(err);
                    appendMessage('assistant', '图片分析失败：' + (err.message || err), []);
                    setStatus('分析失败：' + (err.message || err));
                }
            } finally {
                chatInFlight = false;
                chatAbortController = null;
                setSendBtnBusy(false);
                if (previewUrl) URL.revokeObjectURL(previewUrl);
            }
        });

        // 视频分析：上传视频并输入问题，提取帧后调用多模态RAG
        if (fileVideo) fileVideo.addEventListener('change', async function (e) {
            const f = e.target.files && e.target.files[0];
            e.target.value = '';
            if (!f) return;

            // 弹出问题输入框
            var question = window.prompt('请输入您关于视频的问题（可选）：\n\n例如：\n- 我的发球动作规范吗？\n- 这个动作哪里需要改进？\n- 请分析视频中的人物动作', '');
            if (question === null) {
                setStatus('已取消');
                return;
            }
            question = (question || '').trim();

            setStatus('正在提取视频帧…');

            // 添加用户消息
            var userShow = question || '（请分析这个视频）';
            appendMessage('user', userShow + '\n\n[视频文件: ' + f.name + ']', []);

            if (welcomeText) welcomeText.style.display = 'none';

            chatAbortController = new AbortController();
            chatInFlight = true;
            setSendBtnBusy(true);

            try {
                const fd = new FormData();
                fd.append('file', f, f.name);
                fd.append('question', question || '请详细描述视频中的动作和事件');
                fd.append('kb_id', selectedKbId || '');
                fd.append('selected_files', selectedKbId ? (getSelectedFilesForKb(selectedKbId) || []).join(',') : '');
                fd.append('num_frames', '4');

                setStatus('分析视频中（这可能需要一些时间）…');

                const resp = await fetch(apiUrl('/chat/video'), {
                    method: 'POST',
                    body: fd,
                    signal: chatAbortController.signal,
                });

                if (!resp.ok) {
                    const data = await resp.json().catch(() => ({}));
                    const msg = (data && data.detail) ? data.detail : ('HTTP ' + resp.status);
                    throw new Error(msg);
                }

                const data = await resp.json();

                var botContexts = [];
                if (data.contexts && data.contexts.length > 0) {
                    botContexts = data.contexts;
                }
                appendMessage('assistant', data.answer, botContexts);

                if (data.contexts && data.contexts.length > 0) {
                    setStatus('视频分析完成，已结合知识库给出回答');
                } else {
                    setStatus('视频分析完成');
                }

            } catch (err) {
                if (err && err.name === 'AbortError') {
                    appendMessage('assistant', '（已停止）', []);
                    setStatus('已停止');
                } else {
                    console.error(err);
                    var errMsg = err.message || String(err);
                    if (errMsg.includes('OpenCV')) {
                        errMsg = '视频分析需要安装 OpenCV。请在命令行运行: pip install opencv-python';
                    }
                    appendMessage('assistant', '视频分析失败：' + errMsg, []);
                    setStatus('分析失败：' + errMsg);
                }
            } finally {
                chatInFlight = false;
                chatAbortController = null;
                setSendBtnBusy(false);
            }
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

        resetChat(!!loadUploadTracking());
        autoResizeInput();
        resumeUploadProgressIfNeeded();
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
        selected_files = [str(x) for x in (body.selected_files or []) if str(x).strip()]
        resolved_kb = _resolve_rag_kb_id(body.kb_id)

        if (body.kb_id or "").strip() and not selected_files:
            return ChatResponse(answer="未选择知识库文件", contexts=[])

        if selected_files:
            answer, contexts_raw = rag_answer_filtered(
                _effective_rag_query(q, a),
                kb_id=resolved_kb,
                selected_files=selected_files,
            )
        else:
            answer, contexts_raw = rag_answer(
                _effective_rag_query(q, a),
                kb_id=resolved_kb,
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


@app.post("/chat/vision", response_model=VisionChatResponse)
async def chat_vision(
    file: UploadFile = File(...),
    question: str = Form(""),
    kb_id: Optional[str] = Form(None),
    selected_files: Optional[str] = Form(None),
) -> VisionChatResponse:
    """看图分析聊天接口：上传图片，结合问题分析图片并从知识库获取相关信息。
    
    使用方法：
    - 上传图片文件
    - 填写问题（如"我的乒乓球姿势哪里不对？"）
    - 可选关联知识库ID进行RAG增强
    """
    from rag_service import multimodal_rag_answer

    # 验证文件
    if not file.filename:
        raise HTTPException(status_code=400, detail="请上传图片文件")
    
    # 读取图片数据
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="图片文件为空")
    
    # 限制图片大小（20MB）
    MAX_IMAGE_SIZE = 20 * 1024 * 1024
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="图片过大，请压缩后重试（最大20MB）")

    q = (question or "").strip()
    if not q:
        q = "请详细描述这张图片的内容"

    try:
        # 解析选定的文件列表
        sel_files = []
        if selected_files:
            try:
                sel_files = [f.strip() for f in selected_files.split(",") if f.strip()]
            except Exception:
                pass

        resolved_kb = _resolve_rag_kb_id(kb_id)

        # 调用多模态RAG
        answer, contexts_raw, image_analysis = multimodal_rag_answer(
            query=q,
            image_bytes=image_bytes,
            filename=file.filename,
            kb_id=resolved_kb,
            selected_files=sel_files,
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

    return VisionChatResponse(
        answer=answer,
        contexts=contexts,
        image_analysis=image_analysis,
    )


@app.post("/api/analyze/image", response_model=OCRImageResponse)
async def api_analyze_image(file: UploadFile = File(...)) -> OCRImageResponse:
    """看图分析接口：上传图片，使用多模态模型分析图片内容（不结合知识库）。
    
    返回图片的详细描述，适合用户想了解图片中有什么的场景。
    """
    from rag_service import analyze_image

    if not file.filename:
        raise HTTPException(status_code=400, detail="请上传图片文件")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="图片文件为空")

    MAX_IMAGE_SIZE = 20 * 1024 * 1024
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="图片过大，请压缩后重试（最大20MB）")

    try:
        analysis = analyze_image(
            image_bytes,
            file.filename,
            question="请详细描述这张图片的所有内容，包括：\n1. 主体是什么（人物/物品/场景）\n2. 主要特征和细节\n3. 如果是人物动作，请描述姿势、表情、动作要领\n4. 任何值得注意的点"
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"图片分析失败: {e}") from e

    return OCRImageResponse(text=analysis, filename=file.filename)


@app.post("/chat/video", response_model=VisionChatResponse)
async def chat_video(
    file: UploadFile = File(...),
    question: str = Form(""),
    kb_id: Optional[str] = Form(None),
    selected_files: Optional[str] = Form(None),
    num_frames: int = Form(4),
) -> VisionChatResponse:
    """视频分析聊天接口：上传视频，提取关键帧分析并结合知识库回答。

    使用方法：
    - 上传视频文件（mp4, avi, mov等）
    - 填写问题（如"我的发球动作规范吗？"）
    - 可选关联知识库ID进行RAG增强
    """
    from rag_service import multimodal_video_rag_answer

    if not file.filename:
        raise HTTPException(status_code=400, detail="请上传视频文件")

    # 读取视频数据
    video_bytes = await file.read()
    if len(video_bytes) == 0:
        raise HTTPException(status_code=400, detail="视频文件为空")

    # 限制视频大小（100MB）
    MAX_VIDEO_SIZE = 100 * 1024 * 1024
    if len(video_bytes) > MAX_VIDEO_SIZE:
        raise HTTPException(status_code=413, detail="视频过大，请压缩后重试（最大100MB）")

    q = (question or "").strip()
    if not q:
        q = "请描述视频中发生了什么，动作是否规范"

    # 限制帧数
    num_frames = min(max(1, num_frames), 8)

    try:
        sel_files = []
        if selected_files:
            try:
                sel_files = [f.strip() for f in selected_files.split(",") if f.strip()]
            except Exception:
                pass

        resolved_kb = _resolve_rag_kb_id(kb_id)

        answer, contexts_raw, video_analysis = multimodal_video_rag_answer(
            query=q,
            video_bytes=video_bytes,
            filename=file.filename,
            kb_id=resolved_kb,
            selected_files=sel_files,
            num_frames=num_frames,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

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

    return VisionChatResponse(
        answer=answer,
        contexts=contexts,
        image_analysis=video_analysis,
    )


@app.post("/api/analyze/video", response_model=OCRImageResponse)
async def api_analyze_video(
    file: UploadFile = File(...),
    num_frames: int = Form(4),
) -> OCRImageResponse:
    """视频分析接口：上传视频，提取关键帧分析内容（不结合知识库）。

    返回视频的详细描述和动作分析。
    """
    from rag_service import extract_video_frames, analyze_video_frames

    if not file.filename:
        raise HTTPException(status_code=400, detail="请上传视频文件")

    video_bytes = await file.read()
    if len(video_bytes) == 0:
        raise HTTPException(status_code=400, detail="视频文件为空")

    MAX_VIDEO_SIZE = 100 * 1024 * 1024
    if len(video_bytes) > MAX_VIDEO_SIZE:
        raise HTTPException(status_code=413, detail="视频过大，请压缩后重试（最大100MB）")

    # 限制帧数
    num_frames = min(max(1, num_frames), 8)

    try:
        frames = extract_video_frames(video_bytes, file.filename, num_frames)
        analysis = analyze_video_frames(
            frames,
            question="请详细描述视频中的内容：\n1. 主要动作或事件\n2. 动作的连贯性和节奏\n3. 如果是体育动作，请分析姿势是否规范\n4. 任何值得注意的细节"
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"视频分析失败: {e}") from e

    return OCRImageResponse(text=analysis, filename=file.filename)






