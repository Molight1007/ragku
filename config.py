import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """项目配置。

    说明：
    - 所有路径与模型参数集中在这里，方便在比赛答辩时说明系统可配置性。
    """

    # 阿里云通义千问密钥（请在环境变量或 .env 中设置）
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")

    # 使用的通义千问对话模型名称
    llm_model: str = "qwen-turbo"

    # 文本向量模型（使用 DashScope 文本向量模型名称）
    embedding_model: str = "text-embedding-v1"

    # 默认知识库路径（可在命令行参数中覆盖）
    default_knowledge_dir: Path = Path(r"D:\知识库资料20")

    # 索引文件保存路径
    index_file: Path = Path("index_store.npy")
    meta_file: Path = Path("index_meta.npy")

    # 文本分片参数
    chunk_size: int = 500  # 每个分片的最大字符数
    chunk_overlap: int = 100  # 分片之间的重叠字符数

    # 检索参数
    top_k: int = 5


settings = Settings()

