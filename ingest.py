import argparse
import os
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pytesseract
from PIL import Image
from PyPDF2 import PdfReader
from dashscope import TextEmbedding
from docx import Document

from config import settings


def read_txt(path: Path) -> str:
    """读取文本文件内容。"""
    return path.read_text(encoding="utf-8", errors="ignore")


def read_pdf(path: Path) -> str:
    """读取 PDF 文本内容。"""
    text_parts: List[str] = []
    with path.open("rb") as f:
        reader = PdfReader(f)
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def read_docx(path: Path) -> str:
    """读取 Word 文档内容。"""
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def read_image_with_ocr(path: Path) -> str:
    """通过 OCR 提取图片中的文字。

    说明：
    - 比赛中用于展示多模态能力，将图片内容转为文本后统一进入向量索引。
    """
    image = Image.open(str(path))
    text = pytesseract.image_to_string(image, lang="chi_sim+eng")
    return text


def split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """将长文本切分为重叠的短文本块。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    chunks: List[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == length:
            break
        start = end - overlap
    return chunks


def collect_documents(data_dir: Path) -> List[Tuple[str, str]]:
    """遍历文件夹，收集所有可用文档的分片文本。

    返回 [(source, chunk_text)] 列表，source 用于在回答中回溯来源。
    """
    supported_ext = {".txt", ".md", ".pdf", ".docx", ".jpg", ".jpeg", ".png", ".bmp"}
    docs: List[Tuple[str, str]] = []

    for root, _, files in os.walk(data_dir):
        for name in files:
            path = Path(root) / name
            if path.suffix.lower() not in supported_ext:
                continue
            try:
                if path.suffix.lower() in {".txt", ".md"}:
                    full_text = read_txt(path)
                elif path.suffix.lower() == ".pdf":
                    full_text = read_pdf(path)
                elif path.suffix.lower() == ".docx":
                    full_text = read_docx(path)
                else:
                    full_text = read_image_with_ocr(path)
            except Exception as e:  # noqa: BLE001
                print(f"读取文件失败: {path}，错误: {e}")
                continue

            chunks = split_text(full_text, settings.chunk_size, settings.chunk_overlap)
            for chunk in chunks:
                docs.append((str(path), chunk))

    return docs


def build_embeddings(docs: List[Tuple[str, str]]) -> Tuple[np.ndarray, List[dict]]:
    """调用 DashScope 文本向量接口，为每个文档分片生成向量。"""
    if not settings.dashscope_api_key:
        raise RuntimeError("未检测到 DASHSCOPE_API_KEY，请先在环境变量或 .env 中配置。")

    embeddings: List[List[float]] = []
    metadatas: List[dict] = []

    for idx, (source, text) in enumerate(docs, start=1):
        try:
            resp = TextEmbedding.call(
                model=settings.embedding_model,
                input=text,
            )
            vector = resp["output"]["embeddings"][0]["embedding"]
            embeddings.append(vector)
            metadatas.append({"source": source, "text": text})
        except Exception as e:  # noqa: BLE001
            print(f"向量化失败，第 {idx} 条，来源 {source}，错误: {e}")
            continue

        if idx % 20 == 0:
            print(f"已完成向量化 {idx} 条文档分片")

    if not embeddings:
        raise RuntimeError("未成功生成任何向量，请检查数据与 API 配置。")

    return np.array(embeddings, dtype="float32"), metadatas


def save_index(embeddings: np.ndarray, metadatas: List[dict]) -> None:
    """保存向量索引与元数据到本地文件。"""
    np.save(settings.index_file, embeddings)
    np.save(settings.meta_file, np.array(metadatas, dtype=object))
    print(f"索引已保存到: {settings.index_file} 和 {settings.meta_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="构建本地知识库向量索引")
    parser.add_argument(
        "--data_dir",
        type=str,
        default=str(settings.default_knowledge_dir),
        help="知识库根目录路径",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"指定的知识库目录不存在: {data_dir}")

    print(f"开始遍历知识库目录: {data_dir}")
    docs = collect_documents(data_dir)
    print(f"完成收集，共得到文档分片数量: {len(docs)}")

    print("开始生成文本向量……")
    embeddings, metadatas = build_embeddings(docs)

    print("开始保存索引……")
    save_index(embeddings, metadatas)
    print("索引构建完成。")


if __name__ == "__main__":
    main()

