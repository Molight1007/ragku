from __future__ import annotations

import math
from typing import List, Tuple

import numpy as np
from dashscope import Generation

from config import settings


def load_index(
    index_file: "str | None" = None,
    meta_file: "str | None" = None,
) -> Tuple[np.ndarray, List[dict]]:
    """从本地加载向量索引与元信息。"""
    from pathlib import Path

    idx_path = Path(index_file) if index_file else settings.index_file
    meta_path = Path(meta_file) if meta_file else settings.meta_file

    if not idx_path.exists() or not meta_path.exists():
        raise FileNotFoundError("未找到索引文件，请先运行 ingest.py 构建索引。")

    embeddings = np.load(idx_path)
    metadatas = np.load(meta_path, allow_pickle=True).tolist()
    return embeddings, metadatas


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """计算两个向量的余弦相似度。"""
    dot = float(np.dot(a, b))
    norm_a = math.sqrt(float(np.dot(a, a)))
    norm_b = math.sqrt(float(np.dot(b, b)))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search_similar_chunks(
    query_embedding: np.ndarray,
    embeddings: np.ndarray,
    metadatas: List[dict],
    top_k: int,
) -> List[dict]:
    """在所有向量中检索与查询最相似的若干文本片段。"""
    sims: List[Tuple[int, float]] = []
    for idx in range(embeddings.shape[0]):
        sim = cosine_similarity(query_embedding, embeddings[idx])
        sims.append((idx, sim))

    sims.sort(key=lambda x: x[1], reverse=True)
    top = sims[:top_k]

    results: List[dict] = []
    for idx, score in top:
        meta = dict(metadatas[idx])
        meta["score"] = float(score)
        results.append(meta)
    return results


def embed_query(query: str) -> np.ndarray:
    """为用户问题生成向量表示。"""
    if not settings.dashscope_api_key:
        raise RuntimeError("未检测到 DASHSCOPE_API_KEY，请先在环境变量或 .env 中配置。")

    from dashscope import TextEmbedding  # 延迟导入，避免不必要依赖

    resp = TextEmbedding.call(
        model=settings.embedding_model,
        input=query,
    )
    vector = resp["output"]["embeddings"][0]["embedding"]
    return np.array(vector, dtype="float32")


def build_prompt(query: str, contexts: List[dict]) -> str:
    """根据检索到的文本片段构造给通义千问的提示词。"""
    context_strs = []
    for idx, c in enumerate(contexts, start=1):
        context_strs.append(
            f"[片段{idx} 来源: {c.get('source', '')}]\n{c.get('text', '')}\n"
        )
    joined_context = "\n\n".join(context_strs)

    prompt = f"""你是一名严谨的中文助教，请仅根据下方“知识库片段”来回答用户问题。
如果知识库中没有足够信息，请明确说明“根据当前知识库无法确定”，不要编造。

【用户问题】
{query}

【知识库片段】
{joined_context}

【回答要求】
1. 使用简体中文回答。
2. 尽量引用关键信息的原文表述，并进行适当概括。
3. 在回答末尾用简短文字提示主要参考了哪些来源文件路径。
"""
    return prompt


def generate_answer(prompt: str) -> str:
    """调用通义千问生成回答。"""
    if not settings.dashscope_api_key:
        raise RuntimeError("未检测到 DASHSCOPE_API_KEY，请先在环境变量或 .env 中配置。")

    resp = Generation.call(
        model=settings.llm_model,
        prompt=prompt,
        temperature=0.3,
        top_p=0.8,
        max_tokens=1024,
    )

    output = resp["output"]["text"]
    return output


def rag_answer(
    query: str,
    index_file: "str | None" = None,
    meta_file: "str | None" = None,
) -> Tuple[str, List[dict]]:
    """对外暴露的 RAG 主流程。

    返回 (answer, contexts)，方便上层（CLI 或 Web）展示检索到的证据。
    """
    embeddings, metadatas = load_index(index_file=index_file, meta_file=meta_file)
    q_embed = embed_query(query)
    contexts = search_similar_chunks(
        q_embed,
        embeddings,
        metadatas,
        settings.top_k,
    )
    prompt = build_prompt(query, contexts)
    answer = generate_answer(prompt)
    return answer, contexts

