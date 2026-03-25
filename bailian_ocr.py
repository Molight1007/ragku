from __future__ import annotations

import base64
import mimetypes
import re

from openai import OpenAI

from config import settings


def _guess_image_mime(data: bytes, filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    if mime and mime.startswith("image/"):
        return mime
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    if len(data) > 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _strip_markdown_fences(text: str) -> str:
    s = (text or "").strip()
    m = re.match(r"^```(?:\w*)?\s*\n([\s\S]*?)\n```\s*$", s)
    if m:
        return m.group(1).strip()
    return s


def ocr_image_with_bailian(image_bytes: bytes, filename: str = "image.png") -> str:
    """调用阿里云百炼 OpenAI 兼容接口中的 Qwen-OCR 模型识别图片文字。"""
    if not settings.dashscope_api_key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY，无法调用百炼图片识别")

    mime = _guess_image_mime(image_bytes, filename)
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"

    client = OpenAI(
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_compatible_base_url,
    )
    try:
        completion = client.chat.completions.create(
            model=settings.ocr_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {
                            "type": "text",
                            "text": (
                                "请识别图片中的全部文字，按阅读顺序输出，保留合理换行。"
                                "仅输出识别结果，不要解释或添加其他说明。"
                            ),
                        },
                    ],
                }
            ],
        )
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"百炼图片识别调用失败：{e}") from e

    if not completion.choices:
        raise RuntimeError("百炼返回结果为空")
    raw = (completion.choices[0].message.content or "").strip()
    return _strip_markdown_fences(raw)
