"""知识库目录：列举、上传、删除与重建索引（路径安全，防止目录穿越）。"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from dotenv import load_dotenv

from config import settings

# 与 ingest.collect_documents 支持的扩展一致
SUPPORTED_EXT = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
    ".gif",
}

MAX_UPLOAD_BYTES = 15 * 1024 * 1024


def knowledge_root() -> Path:
    """每次解析前刷新 .env，便于网页与启动器写入 KNOWLEDGE_DIR 后尽快生效（仍建议重启服务）。"""
    load_dotenv(override=True)
    raw = os.getenv("KNOWLEDGE_DIR", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(settings.default_knowledge_dir).expanduser().resolve()


def _ensure_root_exists() -> Path:
    root = knowledge_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_relative_path(rel: str) -> str:
    rel = rel.replace("\\", "/").strip().lstrip("/")
    if not rel:
        raise ValueError("路径不能为空")
    parts = rel.split("/")
    if any(p == ".." or p == "" for p in parts):
        raise ValueError("非法路径")
    return rel


def resolve_safe(rel: str) -> Path:
    root = _ensure_root_exists()
    rel = safe_relative_path(rel)
    target = (root / rel).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError("路径越界")
    return target


def list_kb_files() -> list[dict[str, int | str]]:
    root = knowledge_root()
    if not root.exists():
        return []
    out: list[dict[str, int | str]] = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix.lower() not in SUPPORTED_EXT:
                continue
            rel = path.relative_to(root).as_posix()
            try:
                size = path.stat().st_size
            except OSError:
                continue
            out.append({"relative_path": rel, "size_bytes": size})
    out.sort(key=lambda x: str(x["relative_path"]))
    return out


def delete_kb_file(relative_path: str) -> None:
    p = resolve_safe(relative_path)
    if not p.is_file():
        raise FileNotFoundError("文件不存在或不是普通文件")
    p.unlink()


def _sanitize_filename(name: str) -> str:
    base = Path(name).name
    if not base or base in {".", ".."}:
        raise ValueError("无效文件名")
    # 保留中文、字母数字、常见标点
    safe = re.sub(r"[^\w\u4e00-\u9fff.\-]", "_", base)
    if len(safe) > 200:
        safe = safe[:200]
    return safe


def save_upload(original_filename: str, data: bytes) -> str:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"文件过大（最大 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB）")
    root = _ensure_root_exists()
    safe = _sanitize_filename(original_filename)
    ext = Path(safe).suffix.lower()
    if ext not in SUPPORTED_EXT:
        raise ValueError(
            "不支持的文件类型。支持：" + ", ".join(sorted(SUPPORTED_EXT))
        )
    unique_name = f"{uuid.uuid4().hex[:10]}_{safe}"
    dest = root / unique_name
    dest.write_bytes(data)
    return unique_name


def rebuild_index_sync() -> dict[str, int]:
    """全量重建向量索引（与 ingest 主流程一致）。"""
    from ingest import build_embeddings, collect_documents, save_index

    root = knowledge_root()
    if not root.exists():
        raise RuntimeError("知识库目录不存在，请先在配置中指定有效目录或创建目录。")

    docs = collect_documents(root)
    if not docs:
        raise RuntimeError("知识库中没有可索引的文档，请先上传支持的文件。")

    embeddings, metadatas = build_embeddings(docs)
    save_index(embeddings, metadatas)
    sources = {m.get("source", "") for m in metadatas}
    return {"chunks": len(metadatas), "unique_sources": len(sources)}
