from __future__ import annotations

import io
import re
from pathlib import Path

from PyPDF2 import PdfReader
from docx import Document

_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}
_TEXT_EXT = {".txt", ".md"}
_DOC_EXT = {".pdf", ".docx"}
_UPLOAD_EXT = _IMAGE_EXT | _TEXT_EXT | _DOC_EXT


def normalize_suffix(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def is_image_filename(filename: str) -> bool:
    return normalize_suffix(filename) in _IMAGE_EXT


def is_allowed_upload(filename: str) -> bool:
    return normalize_suffix(filename) in _UPLOAD_EXT


def ocr_image_bytes(data: bytes, filename: str = "image.png") -> str:
    """使用阿里云百炼 Qwen-OCR 识别图片中的文字。"""
    from bailian_ocr import ocr_image_with_bailian

    return ocr_image_with_bailian(data, filename)


def extract_text_from_bytes(filename: str, data: bytes) -> str:
    """按扩展名从二进制内容中提取纯文本（含图片 OCR）。"""
    suf = normalize_suffix(filename)
    if suf in _TEXT_EXT:
        return data.decode("utf-8", errors="ignore")
    if suf == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        parts: list[str] = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
    if suf == ".docx":
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    if suf in _IMAGE_EXT:
        return ocr_image_bytes(data, filename)
    raise ValueError(f"不支持的文件类型: {suf or '(无扩展名)'}")


def safe_upload_name(original: str) -> str:
    base = Path(original or "file").name
    base = re.sub(r"[^\w.\-()\u4e00-\u9fff]+", "_", base).strip("._") or "file"
    return base[:180]
