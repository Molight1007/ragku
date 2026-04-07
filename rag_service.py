from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

import numpy as np
from dashscope import Generation

from config import settings


KB_ROOT = Path(__file__).resolve().parent / "uploads" / "knowledge_bases"


def _kb_index_paths(kb_id: str) -> Tuple[Path, Path]:
    safe = "".join(ch for ch in (kb_id or "") if ch.isalnum() or ch in {"_", "-"}).strip()
    if not safe:
        raise ValueError("无效知识库 ID")
    base = KB_ROOT / safe
    return base / "index_store.npy", base / "index_meta.npy"


def load_index(kb_id: str | None = None) -> Tuple[np.ndarray, List[dict]]:
    """从本地加载向量索引与元信息。"""
    if kb_id:
        index_file, meta_file = _kb_index_paths(kb_id)
    else:
        index_file, meta_file = settings.index_file, settings.meta_file

    if not index_file.exists() or not meta_file.exists():
        if kb_id:
            raise FileNotFoundError("未找到该知识库索引，请先上传文件并构建索引。")
        raise FileNotFoundError("未找到索引文件，请先运行 ingest.py 构建索引。")

    embeddings = np.load(index_file)
    metadatas = np.load(meta_file, allow_pickle=True).tolist()
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

    from http import HTTPStatus

    import dashscope
    from dashscope import TextEmbedding  # 延迟导入，避免不必要依赖

    dashscope.api_key = settings.dashscope_api_key
    resp = TextEmbedding.call(
        model=settings.embedding_model,
        input=query,
    )
    if getattr(resp, "status_code", None) != HTTPStatus.OK:
        code = getattr(resp, "code", "")
        msg = getattr(resp, "message", "") or str(resp)
        raise RuntimeError(f"查询向量化失败: status={resp.status_code}, code={code}, message={msg}")

    output = resp.output if hasattr(resp, "output") else resp["output"]
    emb_list = output["embeddings"] if isinstance(output, dict) else output.embeddings
    first = emb_list[0]
    vector = first["embedding"] if isinstance(first, dict) else first.embedding
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

    import dashscope

    dashscope.api_key = settings.dashscope_api_key
    resp = Generation.call(
        model=settings.llm_model,
        prompt=prompt,
        temperature=0.3,
        top_p=0.8,
        max_tokens=1024,
    )

    output = resp["output"]["text"]
    return output


def _filter_index_by_files(
    embeddings: np.ndarray,
    metadatas: List[dict],
    selected_files: List[str],
) -> Tuple[np.ndarray, List[dict]]:
    wanted = {str(x).strip() for x in selected_files if str(x).strip()}
    if not wanted:
        return embeddings, metadatas

    kept_vecs: List[np.ndarray] = []
    kept_meta: List[dict] = []
    for i, m in enumerate(metadatas):
        src = str(m.get("source", "") or "")
        src_name = Path(src).name
        src_clean = src_name
        if len(src_clean) > 13 and src_clean[12] == "_":
            src_clean = src_clean[13:]
        if src_name in wanted or src_clean in wanted:
            kept_vecs.append(embeddings[i])
            kept_meta.append(m)

    if not kept_vecs:
        return np.zeros((0, embeddings.shape[1]), dtype=embeddings.dtype), []
    return np.stack(kept_vecs), kept_meta


def rag_answer_filtered(query: str, kb_id: str, selected_files: List[str]) -> Tuple[str, List[dict]]:
    embeddings, metadatas = load_index(kb_id=kb_id)
    f_embeddings, f_meta = _filter_index_by_files(embeddings, metadatas, selected_files)
    if f_embeddings.shape[0] == 0:
        raise FileNotFoundError("当前所选文件没有可检索内容，请取消筛选或重新选择文件。")
    q_embed = embed_query(query)
    contexts = search_similar_chunks(q_embed, f_embeddings, f_meta, settings.top_k)
    prompt = build_prompt(query, contexts)
    answer = generate_answer(prompt)
    return answer, contexts


def rag_answer(query: str, kb_id: str | None = None) -> Tuple[str, List[dict]]:
    """对外暴露的 RAG 主流程。"""
    embeddings, metadatas = load_index(kb_id=kb_id)
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
