#!/usr/bin/env python3
"""
向量化任务队列管理器

功能：
1. 支持向量化任务的队列管理
2. 支持任务暂停、恢复、取消
3. 支持任务优先级管理
4. 支持断点续传（从中断处继续）
5. 持久化任务状态，支持进程重启后恢复
6. 实时任务进度跟踪
"""

import asyncio
import datetime
import hashlib
import json
import os
import pickle
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from threading import Lock
import numpy as np

from ingest import build_embeddings, read_txt, read_pdf, read_docx, read_image_with_ocr, collect_documents


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待处理
    PROCESSING = "processing"  # 正在处理
    PAUSED = "paused"        # 已暂停
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 已失败
    CANCELLED = "cancelled"  # 已取消
    RESUMABLE = "resumable"  # 可恢复（部分完成）


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class VectorizationTask:
    """向量化任务定义"""
    task_id: str
    kb_id: str
    file_path: Path
    file_hash: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    error_message: Optional[str] = None
    
    # 进度跟踪
    total_chunks: int = 0
    processed_chunks: int = 0
    failed_chunks: int = 0
    
    # 断点续传状态
    current_chunk_index: int = 0
    chunk_progress: Dict[int, bool] = field(default_factory=dict)
    chunk_errors: Dict[int, str] = field(default_factory=dict)
    
    # 结果存储
    embeddings: Optional[np.ndarray] = None
    metadatas: Optional[List[dict]] = None
    index_path: Optional[Path] = None
    meta_path: Optional[Path] = None
    
    # 重试设置
    max_retries: int = 3
    retry_count: int = 0
    last_retry_at: Optional[datetime.datetime] = None
    
    def __post_init__(self):
        # 确保路径是Path对象
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)
        if self.index_path and isinstance(self.index_path, str):
            self.index_path = Path(self.index_path)
        if self.meta_path and isinstance(self.meta_path, str):
            self.meta_path = Path(self.meta_path)
    
    def start(self):
        """开始处理任务"""
        self.status = TaskStatus.PROCESSING
        self.started_at = datetime.datetime.now()
    
    def pause(self):
        """暂停任务"""
        if self.status == TaskStatus.PROCESSING:
            self.status = TaskStatus.PAUSED
    
    def resume(self):
        """恢复任务"""
        if self.status == TaskStatus.PAUSED:
            self.status = TaskStatus.PROCESSING
    
    def cancel(self):
        """取消任务"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.datetime.now()
    
    def complete(self):
        """完成任务"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.datetime.now()
        self.processed_chunks = self.total_chunks
    
    def fail(self, error_message: str):
        """标记任务为失败"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.datetime.now()
        self.error_message = error_message
    
    def can_resume(self) -> bool:
        """检查任务是否可以恢复"""
        return (
            self.status in [TaskStatus.PAUSED, TaskStatus.FAILED, TaskStatus.RESUMABLE] 
            and self.processed_chunks > 0
            and self.processed_chunks < self.total_chunks
        )
    
    def get_progress(self) -> Dict[str, Any]:
        """获取任务进度信息"""
        if self.total_chunks == 0:
            progress_percent = 0
        else:
            progress_percent = (self.processed_chunks / self.total_chunks) * 100
        
        return {
            "task_id": self.task_id,
            "kb_id": self.kb_id,
            "filename": self.file_path.name,
            "status": self.status.value,
            "progress": round(progress_percent, 2),
            "processed": self.processed_chunks,
            "total": self.total_chunks,
            "failed": self.failed_chunks,
            "eta": self._calculate_eta(),
            "can_resume": self.can_resume(),
            "error": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
        }
    
    def _calculate_eta(self) -> Optional[float]:
        """计算预计完成时间（秒）"""
        if (not self.started_at or 
            self.total_chunks == 0 or 
            self.processed_chunks == 0):
            return None
        
        if self.status != TaskStatus.PROCESSING:
            return None
        
        elapsed = (datetime.datetime.now() - self.started_at).total_seconds()
        chunks_per_second = self.processed_chunks / elapsed if elapsed > 0 else 0
        
        if chunks_per_second <= 0:
            return None
        
        remaining_chunks = self.total_chunks - self.processed_chunks
        return remaining_chunks / chunks_per_second
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典"""
        data = asdict(self)
        
        # 转换特殊类型
        data["status"] = self.status.value
        data["priority"] = self.priority.value
        
        # 转换路径为字符串
        data["file_path"] = str(self.file_path)
        if self.index_path:
            data["index_path"] = str(self.index_path)
        if self.meta_path:
            data["meta_path"] = str(self.meta_path)
        
        # 转换枚举类型
        if isinstance(data.get("embeddings"), np.ndarray):
            # 对于numpy数组，只存储元数据
            data["embeddings"] = {
                "shape": data["embeddings"].shape,
                "dtype": str(data["embeddings"].dtype),
                "stored": True if self.index_path and self.index_path.exists() else False
            }
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorizationTask":
        """从字典恢复任务"""
        # 恢复枚举类型
        data["status"] = TaskStatus(data["status"])
        data["priority"] = TaskPriority(data["priority"])
        
        # 恢复路径
        data["file_path"] = Path(data["file_path"])
        if data.get("index_path"):
            data["index_path"] = Path(data["index_path"])
        if data.get("meta_path"):
            data["meta_path"] = Path(data["meta_path"])
        
        # 处理embeddings
        if isinstance(data.get("embeddings"), dict) and "stored" in data["embeddings"]:
            data["embeddings"] = None
        
        return cls(**data)


class VectorizationQueue:
    """向量化队列管理器"""
    
    def __init__(self, 
                 db_path: Path = Path("data/vectorization_queue.db"),
                 max_workers: int = 2,
                 chunk_size: int = 512,
                 task_timeout: int = 3600):
        """
        初始化队列
        
        Args:
            db_path: SQLite数据库路径
            max_workers: 最大并行工作线程数
            chunk_size: 文本分块大小（字符数）
            task_timeout: 任务超时时间（秒）
        """
        self.db_path = db_path
        self.data_dir = db_path.parent
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.task_timeout = task_timeout
        
        # 内存中的任务列表
        self.tasks: Dict[str, VectorizationTask] = {}
        self.queue: List[str] = []  # 任务ID队列，按优先级排序
        
        # 工作线程池
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_futures: Dict[str, asyncio.Future] = {}
        
        # 同步锁
        self.lock = Lock()
        self.db_lock = Lock()
        
        # 初始化数据库
        self._init_database()
        
        # 加载未完成的任务
        self._load_pending_tasks()
        
        # 启动任务处理器
        self._running = True
        self._processor_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._processor_thread.start()
        
        # 启动状态检查器
        self._checker_thread = threading.Thread(target=self._check_status_loop, daemon=True)
        self._checker_thread.start()
    
    def _init_database(self):
        """初始化数据库表"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建任务表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    kb_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    total_chunks INTEGER DEFAULT 0,
                    processed_chunks INTEGER DEFAULT 0,
                    failed_chunks INTEGER DEFAULT 0,
                    current_chunk_index INTEGER DEFAULT 0,
                    chunk_progress TEXT,
                    chunk_errors TEXT,
                    embeddings_path TEXT,
                    metadatas_path TEXT,
                    index_path TEXT,
                    meta_path TEXT,
                    max_retries INTEGER DEFAULT 3,
                    retry_count INTEGER DEFAULT 0,
                    last_retry_at TIMESTAMP,
                    task_data TEXT NOT NULL
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_kb_id ON tasks(kb_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_priority ON tasks(priority)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON tasks(created_at)')
            
            conn.commit()
            conn.close()
    
    def _save_task(self, task: VectorizationTask):
        """保存任务到数据库"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 序列化任务数据
            task_dict = task.to_dict()
            task_data = json.dumps(task_dict, default=str)
            
            # 序列化分块进度
            chunk_progress = json.dumps(task.chunk_progress)
            chunk_errors = json.dumps(task.chunk_errors)
            
            cursor.execute('''
                INSERT OR REPLACE INTO tasks 
                (task_id, kb_id, file_path, file_hash, status, priority, 
                 created_at, started_at, completed_at, error_message,
                 total_chunks, processed_chunks, failed_chunks, current_chunk_index,
                 chunk_progress, chunk_errors, index_path, meta_path,
                 max_retries, retry_count, last_retry_at, task_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task.task_id, task.kb_id, str(task.file_path), task.file_hash,
                task.status.value, task.priority.value,
                task.created_at.isoformat() if task.created_at else None,
                task.started_at.isoformat() if task.started_at else None,
                task.completed_at.isoformat() if task.completed_at else None,
                task.error_message,
                task.total_chunks, task.processed_chunks, task.failed_chunks,
                task.current_chunk_index,
                chunk_progress, chunk_errors,
                str(task.index_path) if task.index_path else None,
                str(task.meta_path) if task.meta_path else None,
                task.max_retries, task.retry_count,
                task.last_retry_at.isoformat() if task.last_retry_at else None,
                task_data
            ))
            
            conn.commit()
            conn.close()
    
    def _load_pending_tasks(self):
        """从数据库加载未完成的任务"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT task_data FROM tasks 
                WHERE status IN (?, ?, ?, ?)
                ORDER BY priority DESC, created_at ASC
            ''', (
                TaskStatus.PENDING.value,
                TaskStatus.PROCESSING.value,
                TaskStatus.PAUSED.value,
                TaskStatus.RESUMABLE.value
            ))
            
            rows = cursor.fetchall()
            conn.close()
            
            with self.lock:
                for (task_data,) in rows:
                    try:
                        task_dict = json.loads(task_data)
                        task = VectorizationTask.from_dict(task_dict)
                        
                        # 恢复任务
                        self.tasks[task.task_id] = task
                        self.queue.append(task.task_id)
                        
                        # 如果任务是处理中但未完成，标记为可恢复
                        if (task.status == TaskStatus.PROCESSING and 
                            task.processed_chunks < task.total_chunks):
                            task.status = TaskStatus.RESUMABLE
                            self._save_task(task)
                    except Exception as e:
                        print(f"加载任务失败: {e}")
    
    def _process_loop(self):
        """任务处理循环"""
        while self._running:
            try:
                # 获取下一个任务
                task_id = None
                with self.lock:
                    if self.queue:
                        # 按优先级和创建时间排序
                        ready_tasks = []
                        for tid in self.queue:
                            task = self.tasks.get(tid)
                            if (task and 
                                task.status in [TaskStatus.PENDING, TaskStatus.RESUMABLE]):
                                ready_tasks.append(task)
                        
                        if ready_tasks:
                            # 按优先级（高到低）和创建时间（早到晚）排序
                            ready_tasks.sort(key=lambda t: (
                                -t.priority.value,  # 优先级降序
                                t.created_at        # 创建时间升序
                            ))
                            task = ready_tasks[0]
                            task_id = task.task_id
                
                if task_id:
                    # 处理任务
                    asyncio.run(self._process_task(task_id))
                else:
                    # 无任务时休眠
                    time.sleep(1)
            
            except Exception as e:
                print(f"任务处理循环错误: {e}")
                time.sleep(5)
    
    async def _process_task(self, task_id: str):
        """处理单个任务"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        # 启动任务
        task.start()
        self._save_task(task)
        print(f"开始处理任务: {task_id} - {task.file_path.name}")
        
        try:
            # 如果是可恢复的任务，从中断处继续
            if task.can_resume():
                await self._resume_task(task)
            else:
                await self._process_new_task(task)
            
            # 任务完成
            task.complete()
            self._save_task(task)
            print(f"任务完成: {task_id}")
            
            # 从队列中移除
            with self.lock:
                if task_id in self.queue:
                    self.queue.remove(task_id)
                if task_id in self.tasks:
                    del self.tasks[task_id]
            
            # 清理数据库记录（可选）
            # self._cleanup_completed_task(task_id)
            
        except asyncio.CancelledError:
            # 任务被取消
            task.status = TaskStatus.CANCELLED
            self._save_task(task)
            print(f"任务被取消: {task_id}")
            
        except Exception as e:
            # 任务失败
            error_msg = str(e)
            print(f"任务失败 {task_id}: {error_msg}")
            
            # 重试逻辑
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.last_retry_at = datetime.datetime.now()
                task.status = TaskStatus.RESUMABLE if task.processed_chunks > 0 else TaskStatus.PENDING
                task.error_message = f"重试 {task.retry_count}/{task.max_retries}: {error_msg}"
                self._save_task(task)
                print(f"任务将重试: {task_id} ({task.retry_count}/{task.max_retries})")
            else:
                task.fail(f"达到最大重试次数: {error_msg}")
                self._save_task(task)
                
                with self.lock:
                    if task_id in self.queue:
                        self.queue.remove(task_id)
                    if task_id in self.tasks:
                        del self.tasks[task_id]
    
    async def _process_new_task(self, task: VectorizationTask):
        """处理新任务"""
        # 1. 读取文件内容
        content = await self._read_file_content(task.file_path)
        
        # 2. 分块处理
        from ingest import split_text
        chunks = split_text(content, self.chunk_size, self.chunk_size // 4)
        task.total_chunks = len(chunks)
        task.chunk_progress = {i: False for i in range(len(chunks))}
        
        # 保存任务状态
        self._save_task(task)
        
        # 3. 批量向量化
        batch_size = 10  # 每次处理10个分块
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i+batch_size]
            batch_sources = [str(task.file_path)] * len(batch_chunks)
            
            # 检查任务是否被取消
            if task.status == TaskStatus.CANCELLED:
                break
            
            # 处理一个批次
            success = False
            retry_count = 0
            max_batch_retries = 3
            
            while not success and retry_count < max_batch_retries:
                try:
                    # 调用向量化函数（在单独的线程池中运行）
                    loop = asyncio.get_event_loop()
                    embeddings, metadatas = await loop.run_in_executor(
                        self.executor, build_embeddings, 
                        list(zip(batch_sources, batch_chunks))
                    )
                    
                    # 更新进度
                    with self.lock:
                        for j in range(len(batch_chunks)):
                            chunk_idx = i + j
                            task.chunk_progress[chunk_idx] = True
                        task.processed_chunks = sum(task.chunk_progress.values())
                        self._save_task(task)
                    
                    # 累积结果
                    if task.embeddings is None:
                        task.embeddings = embeddings
                        task.metadatas = metadatas
                    else:
                        task.embeddings = np.vstack([task.embeddings, embeddings])
                        task.metadatas.extend(metadatas)
                    
                    success = True
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_batch_retries:
                        # 记录失败的chunks
                        for j in range(len(batch_chunks)):
                            chunk_idx = i + j
                            task.chunk_errors[chunk_idx] = str(e)
                            task.failed_chunks += 1
                        self._save_task(task)
                        print(f"批次 {i}-{i+len(batch_chunks)} 处理失败: {e}")
                    else:
                        await asyncio.sleep(2 ** retry_count)  # 指数退避
        
        # 4. 保存向量化结果
        if task.embeddings is not None and len(task.embeddings) > 0:
            await self._save_vectorization_result(task)
        else:
            raise RuntimeError("未成功生成任何向量")
    
    async def _resume_task(self, task: VectorizationTask):
        """恢复中断的任务"""
        print(f"恢复任务: {task.task_id}, 已处理 {task.processed_chunks}/{task.total_chunks}")
        
        # 从文件重新读取内容
        content = await self._read_file_content(task.file_path)
        
        # 重新分块
        from ingest import split_text
        chunks = split_text(content, self.chunk_size, self.chunk_size // 4)
        
        # 找出未处理的分块
        unprocessed_indices = [i for i, processed in task.chunk_progress.items() 
                              if not processed and i < len(chunks)]
        
        if not unprocessed_indices:
            # 所有分块都已标记为处理，但可能有些失败了
            failed_indices = list(task.chunk_errors.keys())
            if failed_indices:
                # 重试失败的分块
                await self._retry_failed_chunks(task, chunks, failed_indices)
        else:
            # 继续处理未完成的分块
            await self._process_remaining_chunks(task, chunks, unprocessed_indices)
    
    async def _process_remaining_chunks(self, task: VectorizationTask, 
                                       chunks: List[str], indices: List[int]):
        """处理剩余的分块"""
        batch_size = 10
        
        for batch_start in range(0, len(indices), batch_size):
            batch_indices = indices[batch_start:batch_start+batch_size]
            batch_chunks = [chunks[i] for i in batch_indices]
            batch_sources = [str(task.file_path)] * len(batch_chunks)
            
            # 检查任务状态
            if task.status == TaskStatus.CANCELLED:
                break
            
            # 处理批次
            success = False
            retry_count = 0
            max_retries = 3
            
            while not success and retry_count < max_retries:
                try:
                    loop = asyncio.get_event_loop()
                    embeddings, metadatas = await loop.run_in_executor(
                        self.executor, build_embeddings,
                        list(zip(batch_sources, batch_chunks))
                    )
                    
                    # 更新进度
                    with self.lock:
                        for idx in batch_indices:
                            task.chunk_progress[idx] = True
                        task.processed_chunks = sum(task.chunk_progress.values())
                        self._save_task(task)
                    
                    # 累积结果
                    if task.embeddings is None:
                        # 如果之前没有embeddings，需要加载之前保存的
                        task.embeddings, task.metadatas = await self._load_partial_result(task)
                    
                    task.embeddings = np.vstack([task.embeddings, embeddings])
                    task.metadatas.extend(metadatas)
                    
                    success = True
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        for idx in batch_indices:
                            task.chunk_errors[idx] = str(e)
                            task.failed_chunks += 1
                        self._save_task(task)
                    else:
                        await asyncio.sleep(2 ** retry_count)
        
        # 保存最终结果
        if task.embeddings is not None:
            await self._save_vectorization_result(task)
    
    async def _retry_failed_chunks(self, task: VectorizationTask, 
                                  chunks: List[str], failed_indices: List[int]):
        """重试失败的分块"""
        print(f"重试 {len(failed_indices)} 个失败分块")
        
        # 实现类似_process_remaining_chunks的逻辑
        await self._process_remaining_chunks(task, chunks, failed_indices)
    
    async def _read_file_content(self, file_path: Path) -> str:
        """异步读取文件内容"""
        loop = asyncio.get_event_loop()
        
        ext = file_path.suffix.lower()
        if ext == '.txt':
            return await loop.run_in_executor(self.executor, read_txt, file_path)
        elif ext == '.pdf':
            return await loop.run_in_executor(self.executor, read_pdf, file_path)
        elif ext == '.docx':
            return await loop.run_in_executor(self.executor, read_docx, file_path)
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            return await loop.run_in_executor(self.executor, read_image_with_ocr, file_path)
        else:
            # 尝试作为纯文本读取
            try:
                return await loop.run_in_executor(self.executor, read_txt, file_path)
            except:
                raise ValueError(f"不支持的文件格式: {ext}")
    
    async def _save_vectorization_result(self, task: VectorizationTask):
        """保存向量化结果到知识库"""
        from config import settings
        
        if not task.embeddings or len(task.embeddings) == 0:
            return
        
        # 保存到知识库目录
        kb_dir = Path("knowledge") / task.kb_id
        kb_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建索引路径
        import time
        timestamp = int(time.time())
        task.index_path = kb_dir / f"index_{timestamp}.npy"
        task.meta_path = kb_dir / f"meta_{timestamp}.npy"
        
        # 异步保存
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor, np.save, task.index_path, task.embeddings
        )
        await loop.run_in_executor(
            self.executor, np.save, task.meta_path, np.array(task.metadatas, dtype=object)
        )
        
        # 更新主索引（如果有的话）
        main_index_path = kb_dir / "index.npy"
        main_meta_path = kb_dir / "meta.npy"
        
        if main_index_path.exists() and main_meta_path.exists():
            # 合并现有索引
            loop = asyncio.get_event_loop()
            existing_embeddings = await loop.run_in_executor(
                self.executor, np.load, main_index_path, allow_pickle=True
            )
            existing_metadatas = await loop.run_in_executor(
                self.executor, np.load, main_meta_path, allow_pickle=True
            )
            
            merged_embeddings = np.vstack([existing_embeddings, task.embeddings])
            merged_metadatas = np.concatenate([existing_metadatas, np.array(task.metadatas, dtype=object)])
            
            await loop.run_in_executor(
                self.executor, np.save, main_index_path, merged_embeddings
            )
            await loop.run_in_executor(
                self.executor, np.save, main_meta_path, merged_metadatas
            )
        else:
            # 创建新的主索引
            task.index_path.rename(main_index_path)
            task.meta_path.rename(main_meta_path)
            task.index_path = main_index_path
            task.meta_path = main_meta_path
        
        self._save_task(task)
    
    async def _load_partial_result(self, task: VectorizationTask) -> Tuple[np.ndarray, List[dict]]:
        """加载部分结果（用于恢复任务）"""
        # 这里需要实现从临时文件加载部分结果
        # 由于实现较复杂，这里返回空的数组和列表
        return np.array([]), []
    
    def _check_status_loop(self):
        """检查任务状态的循环"""
        while self._running:
            try:
                # 检查超时任务
                with self.lock:
                    now = datetime.datetime.now()
                    for task_id, task in list(self.tasks.items()):
                        if (task.status == TaskStatus.PROCESSING and
                            task.started_at and
                            (now - task.started_at).total_seconds() > self.task_timeout):
                            
                            print(f"任务超时: {task_id}")
                            task.status = TaskStatus.RESUMABLE
                            task.error_message = "处理超时"
                            self._save_task(task)
                
                time.sleep(30)  # 每30秒检查一次
                
            except Exception as e:
                print(f"状态检查错误: {e}")
                time.sleep(5)
    
    def add_task(self, kb_id: str, file_path: Path, 
                 priority: TaskPriority = TaskPriority.NORMAL) -> str:
        """
        添加向量化任务到队列
        
        Args:
            kb_id: 知识库ID
            file_path: 要处理的文件路径
            priority: 任务优先级
            
        Returns:
            task_id: 任务ID
        """
        # 计算文件哈希
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        # 创建任务
        task_id = str(uuid.uuid4())
        task = VectorizationTask(
            task_id=task_id,
            kb_id=kb_id,
            file_path=file_path,
            file_hash=file_hash,
            priority=priority
        )
        
        with self.lock:
            self.tasks[task_id] = task
            self.queue.append(task_id)
        
        # 保存到数据库
        self._save_task(task)
        
        print(f"已添加向量化任务: {task_id} - {file_path.name}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        task = self.tasks.get(task_id)
        if not task:
            # 尝试从数据库加载已完成的任务
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT task_data FROM tasks WHERE task_id = ?', (task_id,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    try:
                        task_dict = json.loads(row[0])
                        return task_dict
                    except:
                        pass
            return None
        
        return task.get_progress()
    
    def get_kb_tasks(self, kb_id: str) -> List[Dict[str, Any]]:
        """获取指定知识库的所有任务"""
        tasks_info = []
        
        with self.lock:
            for task in self.tasks.values():
                if task.kb_id == kb_id:
                    tasks_info.append(task.get_progress())
        
        # 从数据库加载已完成的任务
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT task_data FROM tasks WHERE kb_id = ?', (kb_id,))
            rows = cursor.fetchall()
            conn.close()
            
            for (task_data,) in rows:
                try:
                    task_dict = json.loads(task_data)
                    tasks_info.append(task_dict)
                except:
                    pass
        
        return tasks_info
    
    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task or task.status != TaskStatus.PROCESSING:
                return False
            
            task.pause()
            self._save_task(task)
            return True
    
    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task or task.status != TaskStatus.PAUSED:
                return False
            
            task.resume()
            self._save_task(task)
            
            # 确保任务在队列中
            if task_id not in self.queue:
                self.queue.append(task_id)
            
            return True
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            task.cancel()
            self._save_task(task)
            
            # 从队列中移除
            if task_id in self.queue:
                self.queue.remove(task_id)
            
            return True
    
    def shutdown(self):
        """关闭队列管理器"""
        self._running = False
        
        # 等待处理线程结束
        if self._processor_thread.is_alive():
            self._processor_thread.join(timeout=5)
        
        if self._checker_thread.is_alive():
            self._checker_thread.join(timeout=5)
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
        
        print("向量化队列已关闭")


# 全局队列实例
_global_queue: Optional[VectorizationQueue] = None

def get_vectorization_queue() -> VectorizationQueue:
    """获取全局向量化队列实例"""
    global _global_queue
    if _global_queue is None:
        _global_queue = VectorizationQueue()
    return _global_queue


if __name__ == "__main__":
    # 测试模块
    print("向量化任务队列管理器 v1.0")
    print(f"最大工作线程: {2}")
    print(f"分块大小: {512}")
    print(f"数据目录: {Path('data').absolute()}")
    
    # 清理测试
    import sys
    if "--cleanup" in sys.argv:
        db_path = Path("data/vectorization_queue.db")
        if db_path.exists():
            db_path.unlink()
            print("清理了数据库")
    
    print("模块加载完成")