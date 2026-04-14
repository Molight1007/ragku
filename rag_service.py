from __future__ import annotations

import base64
import math
import mimetypes
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
from dashscope import Generation
from openai import OpenAI

from config import settings


KB_ROOT = Path(__file__).resolve().parent / "uploads" / "knowledge_bases"

# 多模态模型配置（使用阿里云百炼的Qwen-VL模型）
MULTIMODAL_MODEL = "qwen-vl-ocr-latest"  # 也支持视觉理解，可用 qwen-vl-max 或 qwen-vl-plus


def _guess_image_mime(data: bytes, filename: str) -> str:
    """猜测图片的MIME类型。"""
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


def analyze_image(image_bytes: bytes, filename: str = "image.png", 
                  question: str = "请详细描述这张图片的内容") -> str:
    """使用多模态模型分析图片内容并回答问题。
    
    Args:
        image_bytes: 图片二进制数据
        filename: 文件名（用于确定MIME类型）
        question: 用户的问题
    
    Returns:
        模型对图片的分析结果
    """
    if not settings.dashscope_api_key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY，无法调用多模态分析")

    mime = _guess_image_mime(image_bytes, filename)
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"

    client = OpenAI(
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_compatible_base_url,
    )
    
    try:
        completion = client.chat.completions.create(
            model=MULTIMODAL_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text", "text": question},
                    ],
                }
            ],
            max_tokens=1024,
        )
    except Exception as e:
        raise RuntimeError(f"图片分析调用失败：{e}") from e

    if not completion.choices:
        raise RuntimeError("图片分析返回结果为空")
    
    return (completion.choices[0].message.content or "").strip()


def multimodal_rag_answer(
    query: str,
    image_bytes: bytes,
    filename: str = "image.png",
    kb_id: str | None = None,
    selected_files: List[str] | None = None,
) -> Tuple[str, List[dict], str]:
    """多模态RAG主流程：分析图片 + 检索知识库 + 生成回答。
    
    Args:
        query: 用户的问题
        image_bytes: 图片二进制数据
        filename: 文件名
        kb_id: 知识库ID
        selected_files: 选定的文件列表
    
    Returns:
        (回答文本, 知识库上下文片段, 图片分析结果)
    """
    # 1. 先用多模态模型分析图片
    image_analysis = analyze_image(
        image_bytes, 
        filename,
        question=f"请详细描述这张图片的所有内容，包括：物体、场景、动作、状态等细节。"
    )
    
    # 2. 检索知识库相关内容
    try:
        embeddings, metadatas = load_index(kb_id=kb_id)
        
        # 如果指定了文件，先过滤
        if selected_files:
            f_embeddings, f_meta = _filter_index_by_files(embeddings, metadatas, selected_files)
            if f_embeddings.shape[0] > 0:
                q_embed = embed_query(query)
                contexts = search_similar_chunks(q_embed, f_embeddings, f_meta, settings.top_k)
            else:
                contexts = []
        else:
            q_embed = embed_query(query)
            contexts = search_similar_chunks(q_embed, embeddings, metadatas, settings.top_k)
    except FileNotFoundError:
        # 没有知识库时，只用图片分析
        contexts = []
    
    # 3. 构建多模态提示词
    prompt = build_multimodal_prompt(query, image_analysis, contexts)
    
    # 4. 生成回答
    answer = generate_multimodal_answer(prompt)
    
    return answer, contexts, image_analysis


def build_multimodal_prompt(query: str, image_analysis: str, contexts: List[dict]) -> str:
    """构造多模态RAG的提示词。"""
    context_strs = []
    for idx, c in enumerate(contexts, start=1):
        context_strs.append(
            f"[片段{idx} 来源: {c.get('source', '')}]\n{c.get('text', '')}\n"
        )
    joined_context = "\n\n".join(context_strs)
    
    prompt = f"""你是一名专业的中文助手，可以结合图片分析和知识库来回答用户问题。

【用户问题】
{query}

【图片分析结果】
{image_analysis}

【知识库片段】
{joined_context if joined_context else "（无相关知识库内容）"}

【回答要求】
1. 使用简体中文回答。
2. 结合图片内容和知识库信息进行综合分析。
3. 如果图片中有问题（如姿势错误、物品摆放不当等），请具体指出。
4. 尽量引用知识库中的关键信息。
5. 如果知识库没有相关信息，以图片分析为主。
"""
    return prompt


def generate_multimodal_answer(prompt: str) -> str:
    """使用通义千问生成多模态回答。"""
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


def rag_answer_filtered(query: str, kb_id: str | None, selected_files: List[str]) -> Tuple[str, List[dict]]:
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


def extract_video_frames(video_bytes: bytes, filename: str = "video.mp4",
                          num_frames: int = 4) -> List[Tuple[bytes, float]]:
    """从视频中提取关键帧。

    Args:
        video_bytes: 视频二进制数据
        filename: 文件名
        num_frames: 提取的帧数（默认4帧）

    Returns:
        List of (frame_bytes, timestamp_seconds)
    """
    try:
        import cv2
        import numpy as np
        from pathlib import Path
        import tempfile

        # 保存临时视频文件
        suffix = Path(filename).suffix or ".mp4"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        try:
            cap = cv2.VideoCapture(tmp_path)
            if not cap.isOpened():
                raise RuntimeError("无法打开视频文件")

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30  # 默认帧率

            duration = total_frames / fps if total_frames > 0 else 0
            frames = []

            # 均匀采样帧
            for i in range(num_frames):
                frame_idx = int((i / num_frames) * total_frames) if total_frames > 0 else 0
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()

                if ret:
                    # 编码为JPEG
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_bytes = buffer.tobytes()
                    timestamp = frame_idx / fps if fps > 0 else 0
                    frames.append((frame_bytes, timestamp))

            cap.release()

            if not frames:
                raise RuntimeError("未能提取到视频帧")

            return frames

        finally:
            # 清理临时文件
            Path(tmp_path).unlink(missing_ok=True)

    except ImportError:
        raise RuntimeError("视频分析需要安装 OpenCV：pip install opencv-python")
    except Exception as e:
        raise RuntimeError(f"视频帧提取失败：{e}")


def analyze_video_frames(frames: List[Tuple[bytes, float]],
                         question: str = "请描述视频中发生了什么") -> str:
    """分析多个视频帧并回答问题。

    Args:
        frames: List of (frame_bytes, timestamp_seconds)
        question: 用户的问题

    Returns:
        基于视频帧的分析结果
    """
    if not settings.dashscope_api_key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY，无法调用视频分析")

    client = OpenAI(
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_compatible_base_url,
    )

    # 构建多图消息
    content = []
    for idx, (frame_bytes, timestamp) in enumerate(frames):
        b64 = base64.standard_b64encode(frame_bytes).decode("ascii")
        time_str = f"{int(timestamp//60)}:{timestamp%60:.1f}" if timestamp >= 1 else f"{timestamp:.1f}s"
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64}"
            }
        })
        content.append({
            "type": "text",
            "text": f"【第{idx+1}帧 @ {time_str}】"
        })

    # 添加问题
    content.append({
        "type": "text",
        "text": f"\n请根据以上视频帧回答：{question}\n请注意描述动作顺序、连贯性和关键细节。"
    })

    try:
        completion = client.chat.completions.create(
            model=MULTIMODAL_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            max_tokens=1024,
        )
    except Exception as e:
        raise RuntimeError(f"视频分析调用失败：{e}") from e

    if not completion.choices:
        raise RuntimeError("视频分析返回结果为空")

    return (completion.choices[0].message.content or "").strip()


def multimodal_video_rag_answer(
    query: str,
    video_bytes: bytes,
    filename: str = "video.mp4",
    kb_id: str | None = None,
    selected_files: List[str] | None = None,
    num_frames: int = 4,
) -> Tuple[str, List[dict], str]:
    """多模态视频RAG主流程：提取帧 + 分析视频 + 检索知识库 + 生成回答。

    Args:
        query: 用户的问题
        video_bytes: 视频二进制数据
        filename: 文件名
        kb_id: 知识库ID
        selected_files: 选定的文件列表
        num_frames: 提取的帧数

    Returns:
        (回答文本, 知识库上下文片段, 视频分析结果)
    """
    # 1. 提取视频帧
    frames = extract_video_frames(video_bytes, filename, num_frames)

    # 2. 分析视频帧
    video_analysis = analyze_video_frames(frames, question=query)

    # 3. 检索知识库相关内容
    try:
        embeddings, metadatas = load_index(kb_id=kb_id)

        if selected_files:
            f_embeddings, f_meta = _filter_index_by_files(embeddings, metadatas, selected_files)
            if f_embeddings.shape[0] > 0:
                q_embed = embed_query(query)
                contexts = search_similar_chunks(q_embed, f_embeddings, f_meta, settings.top_k)
            else:
                contexts = []
        else:
            q_embed = embed_query(query)
            contexts = search_similar_chunks(q_embed, embeddings, metadatas, settings.top_k)
    except FileNotFoundError:
        contexts = []

    # 4. 构建提示词
    prompt = build_multimodal_prompt(query, video_analysis, contexts)

    # 5. 生成回答
    answer = generate_multimodal_answer(prompt)

    return answer, contexts, video_analysis
