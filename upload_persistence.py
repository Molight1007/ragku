#!/usr/bin/env python3
"""
上传和向量化状态持久化模块

功能：
1. 持久化存储上传会话状态
2. 持久化存储向量化任务状态
3. 支持状态恢复（服务器重启后）
4. 自动清理过期数据
"""

import json
import pickle
import sqlite3
import time
import threading
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import hashlib
import shutil

from chunked_upload import ChunkedUploadSession, ChunkedUploadManager
from vectorization_queue import VectorizationTask, TaskStatus


class PersistenceType(Enum):
    """持久化类型枚举"""
    UPLOAD_SESSION = "upload_session"
    VECTORIZATION_TASK = "vectorization_task"
    FILE_METADATA = "file_metadata"
    SYSTEM_STATE = "system_state"


class UploadPersistence:
    """上传状态持久化管理器"""
    
    def __init__(self, db_path: Path = Path("data/upload_persistence.db")):
        """
        初始化持久化管理器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        self.data_dir = db_path.parent
        
        # 确保目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据库锁
        self.db_lock = threading.Lock()
        
        # 初始化数据库
        self._init_database()
        
        # 启动清理线程
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
        # 启动检查线程
        self._health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_check_thread.start()
    
    def _init_database(self):
        """初始化数据库表结构"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 上传会话表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS upload_sessions (
                    session_id TEXT PRIMARY KEY,
                    kb_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    total_chunks INTEGER NOT NULL,
                    md5_hash TEXT,
                    session_data TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    status TEXT NOT NULL,
                    completed_at TIMESTAMP
                )
            ''')
            
            # 向量化任务表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vectorization_tasks (
                    task_id TEXT PRIMARY KEY,
                    kb_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    session_id TEXT,
                    task_data TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress REAL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    next_retry_at TIMESTAMP
                )
            ''')
            
            # 文件元数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_metadata (
                    file_id TEXT PRIMARY KEY,
                    kb_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    upload_session_id TEXT,
                    vectorization_task_id TEXT,
                    file_path TEXT NOT NULL,
                    index_path TEXT,
                    meta_path TEXT,
                    created_at TIMESTAMP NOT NULL,
                    deleted_at TIMESTAMP,
                    indexed BOOLEAN DEFAULT FALSE,
                    vector_count INTEGER DEFAULT 0,
                    tags TEXT
                )
            ''')
            
            # 系统状态表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_state (
                    state_key TEXT PRIMARY KEY,
                    state_value TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    description TEXT
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_upload_sessions_kb_id 
                ON upload_sessions(kb_id, status)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_upload_sessions_expires 
                ON upload_sessions(expires_at)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_vectorization_tasks_kb_id 
                ON vectorization_tasks(kb_id, status)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_vectorization_tasks_session 
                ON vectorization_tasks(session_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_file_metadata_kb_id 
                ON file_metadata(kb_id, indexed)
            ''')
            
            conn.commit()
            conn.close()
    
    # ====== 上传会话持久化方法 ======
    
    def save_upload_session(self, session: ChunkedUploadSession) -> bool:
        """
        保存上传会话状态
        
        Args:
            session: 上传会话对象
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 序列化会话数据
                session_dict = session.to_dict()
                session_data = json.dumps(session_dict, ensure_ascii=False)
                
                # 计算过期时间
                expires_at = datetime.now() + timedelta(hours=24)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO upload_sessions 
                    (session_id, kb_id, filename, file_size, total_chunks, md5_hash,
                     session_data, created_at, updated_at, expires_at, status, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session.session_id,
                    session.kb_id,
                    session.filename,
                    session.file_size,
                    session.total_chunks,
                    session.md5_hash or "",
                    session_data,
                    session.created_at.isoformat() if session.created_at else datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    expires_at.isoformat(),
                    "active" if not session.is_complete() else "completed",
                    session.created_at.isoformat() if session.is_complete() else None
                ))
                
                conn.commit()
                conn.close()
                
                # 同时保存文件元数据
                if session.is_complete():
                    self._save_file_metadata_from_session(session)
                
                return True
                
        except Exception as e:
            print(f"保存上传会话失败 {session.session_id}: {e}")
            return False
    
    def load_upload_session(self, session_id: str) -> Optional[ChunkedUploadSession]:
        """
        加载上传会话状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[ChunkedUploadSession]: 恢复的会话对象，或None
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT session_data FROM upload_sessions 
                    WHERE session_id = ? AND expires_at > ? AND status != 'expired'
                ''', (session_id, datetime.now().isoformat()))
                
                row = cursor.fetchone()
                conn.close()
                
                if not row:
                    return None
                
                session_data = json.loads(row[0])
                
                # 重建会话对象
                # 注意：这里简化处理，实际使用时需要完整的ChunkedUploadSession.load_from_metadata方法
                return None  # 暂不实现完整恢复
                
        except Exception as e:
            print(f"加载上传会话失败 {session_id}: {e}")
            return None
    
    def update_session_status(self, session_id: str, status: str) -> bool:
        """
        更新上传会话状态
        
        Args:
            session_id: 会话ID
            status: 新状态
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE upload_sessions 
                    SET status = ?, updated_at = ?, expires_at = ?
                    WHERE session_id = ?
                ''', (
                    status,
                    datetime.now().isoformat(),
                    (datetime.now() + timedelta(hours=24)).isoformat(),
                    session_id
                ))
                
                conn.commit()
                conn.close()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"更新会话状态失败 {session_id}: {e}")
            return False
    
    def _save_file_metadata_from_session(self, session: ChunkedUploadSession):
        """
        从会话保存文件元数据
        
        Args:
            session: 上传会话对象
        """
        # 生成文件ID
        file_id = hashlib.md5(f"{session.kb_id}:{session.filename}:{session.file_size}".encode()).hexdigest()
        
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO file_metadata 
                    (file_id, kb_id, filename, original_name, file_size, file_hash,
                     upload_session_id, file_path, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file_id,
                    session.kb_id,
                    session.filename,
                    session.filename,  # 这里可以处理重命名逻辑
                    session.file_size,
                    session.md5_hash or "",
                    session.session_id,
                    "",  # 文件路径，后续更新
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                conn.close()
                
        except Exception as e:
            print(f"保存文件元数据失败 {session.session_id}: {e}")
    
    # ====== 向量化任务持久化方法 ======
    
    def save_vectorization_task(self, task: VectorizationTask) -> bool:
        """
        保存向量化任务状态
        
        Args:
            task: 向量化任务对象
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 序列化任务数据
                task_dict = task.to_dict()
                task_data = json.dumps(task_dict, ensure_ascii=False)
                
                # 计算进度百分比
                progress = 0
                if task.total_chunks > 0:
                    progress = (task.processed_chunks / task.total_chunks) * 100
                
                cursor.execute('''
                    INSERT OR REPLACE INTO vectorization_tasks 
                    (task_id, kb_id, file_path, file_hash, task_data, status,
                     progress, created_at, started_at, completed_at, error_message,
                     retry_count, max_retries, next_retry_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.task_id,
                    task.kb_id,
                    str(task.file_path),
                    task.file_hash,
                    task_data,
                    task.status.value,
                    progress,
                    task.created_at.isoformat() if task.created_at else datetime.now().isoformat(),
                    task.started_at.isoformat() if task.started_at else None,
                    task.completed_at.isoformat() if task.completed_at else None,
                    task.error_message,
                    task.retry_count,
                    task.max_retries,
                    task.last_retry_at.isoformat() if task.last_retry_at else None
                ))
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            print(f"保存向量化任务失败 {task.task_id}: {e}")
            return False
    
    def load_vectorization_tasks(self, kb_id: Optional[str] = None, 
                                status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        加载向量化任务
        
        Args:
            kb_id: 知识库ID，None表示所有
            status: 任务状态，None表示所有
            
        Returns:
            List[Dict]: 任务列表
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                if kb_id and status:
                    cursor.execute('''
                        SELECT task_data FROM vectorization_tasks 
                        WHERE kb_id = ? AND status = ?
                        ORDER BY created_at DESC
                    ''', (kb_id, status))
                elif kb_id:
                    cursor.execute('''
                        SELECT task_data FROM vectorization_tasks 
                        WHERE kb_id = ?
                        ORDER BY created_at DESC
                    ''', (kb_id,))
                elif status:
                    cursor.execute('''
                        SELECT task_data FROM vectorization_tasks 
                        WHERE status = ?
                        ORDER BY created_at DESC
                    ''', (status,))
                else:
                    cursor.execute('''
                        SELECT task_data FROM vectorization_tasks 
                        ORDER BY created_at DESC
                    ''')
                
                rows = cursor.fetchall()
                conn.close()
                
                tasks = []
                for (task_data,) in rows:
                    try:
                        tasks.append(json.loads(task_data))
                    except:
                        pass
                
                return tasks
                
        except Exception as e:
            print(f"加载向量化任务失败: {e}")
            return []
    
    def update_vectorization_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新向量化任务
        
        Args:
            task_id: 任务ID
            updates: 更新字段字典
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 动态构建UPDATE语句
                set_clauses = []
                set_values = []
                
                for key, value in updates.items():
                    if key == "progress" and "total_chunks" in updates and "processed_chunks" in updates:
                        # 自动计算进度
                        if updates["total_chunks"] > 0:
                            progress = (updates["processed_chunks"] / updates["total_chunks"]) * 100
                            set_clauses.append("progress = ?")
                            set_values.append(progress)
                    elif key in ["task_data", "status", "error_message", "retry_count", "next_retry_at"]:
                        set_clauses.append(f"{key} = ?")
                        set_values.append(value)
                    elif key == "started_at" and value:
                        set_clauses.append("started_at = ?")
                        set_values.append(value.isoformat() if isinstance(value, datetime) else value)
                    elif key == "completed_at" and value:
                        set_clauses.append("completed_at = ?")
                        set_values.append(value.isoformat() if isinstance(value, datetime) else value)
                
                if not set_clauses:
                    return False
                
                set_values.append(task_id)
                
                query = f'''
                    UPDATE vectorization_tasks 
                    SET {", ".join(set_clauses)}
                    WHERE task_id = ?
                '''
                
                cursor.execute(query, tuple(set_values))
                conn.commit()
                conn.close()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"更新向量化任务失败 {task_id}: {e}")
            return False
    
    # ====== 文件元数据管理方法 ======
    
    def save_file_metadata(self, file_id: str, metadata: Dict[str, Any]) -> bool:
        """
        保存文件元数据
        
        Args:
            file_id: 文件ID
            metadata: 元数据字典
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 构建插入语句
                columns = ["file_id"]
                placeholders = ["?"]
                values = [file_id]
                
                for key, value in metadata.items():
                    columns.append(key)
                    placeholders.append("?")
                    
                    if isinstance(value, datetime):
                        values.append(value.isoformat())
                    elif isinstance(value, dict) or isinstance(value, list):
                        values.append(json.dumps(value, ensure_ascii=False))
                    else:
                        values.append(value)
                
                cursor.execute(f'''
                    INSERT OR REPLACE INTO file_metadata 
                    ({", ".join(columns)})
                    VALUES ({", ".join(placeholders)})
                ''', tuple(values))
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            print(f"保存文件元数据失败 {file_id}: {e}")
            return False
    
    def get_file_metadata(self, kb_id: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        获取文件元数据
        
        Args:
            kb_id: 知识库ID
            filename: 文件名
            
        Returns:
            Optional[Dict]: 元数据字典，或None
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM file_metadata 
                    WHERE kb_id = ? AND filename = ? AND deleted_at IS NULL
                ''', (kb_id, filename))
                
                row = cursor.fetchone()
                conn.close()
                
                if not row:
                    return None
                
                # 获取列名
                cursor.description
                column_names = [desc[0] for desc in cursor.description]
                
                metadata = {}
                for i, (col_name, value) in enumerate(zip(column_names, row)):
                    if col_name in ["created_at", "deleted_at"] and value:
                        try:
                            metadata[col_name] = datetime.fromisoformat(value)
                        except:
                            metadata[col_name] = value
                    elif col_name in ["tags", "session_data", "task_data"] and value:
                        try:
                            metadata[col_name] = json.loads(value)
                        except:
                            metadata[col_name] = value
                    else:
                        metadata[col_name] = value
                
                return metadata
                
        except Exception as e:
            print(f"获取文件元数据失败 {kb_id}:{filename}: {e}")
            return None
    
    def mark_file_indexed(self, file_id: str, index_path: str, meta_path: str, 
                          vector_count: int) -> bool:
        """
        标记文件已索引
        
        Args:
            file_id: 文件ID
            index_path: 索引文件路径
            meta_path: 元数据文件路径
            vector_count: 向量数量
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE file_metadata 
                    SET indexed = TRUE, index_path = ?, meta_path = ?, vector_count = ?
                    WHERE file_id = ?
                ''', (index_path, meta_path, vector_count, file_id))
                
                conn.commit()
                conn.close()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"标记文件已索引失败 {file_id}: {e}")
            return False
    
    # ====== 系统状态管理方法 ======
    
    def save_system_state(self, key: str, value: Any, description: str = "") -> bool:
        """
        保存系统状态
        
        Args:
            key: 状态键
            value: 状态值
            description: 状态描述
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 序列化值
                if isinstance(value, dict) or isinstance(value, list):
                    value_str = json.dumps(value, ensure_ascii=False)
                else:
                    value_str = str(value)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO system_state 
                    (state_key, state_value, updated_at, description)
                    VALUES (?, ?, ?, ?)
                ''', (key, value_str, datetime.now().isoformat(), description))
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            print(f"保存系统状态失败 {key}: {e}")
            return False
    
    def load_system_state(self, key: str, default: Any = None) -> Any:
        """
        加载系统状态
        
        Args:
            key: 状态键
            default: 默认值
            
        Returns:
            Any: 状态值
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT state_value FROM system_state WHERE state_key = ?
                ''', (key,))
                
                row = cursor.fetchone()
                conn.close()
                
                if not row:
                    return default
                
                value_str = row[0]
                
                # 尝试解析JSON
                try:
                    return json.loads(value_str)
                except:
                    return value_str
                
        except Exception as e:
            print(f"加载系统状态失败 {key}: {e}")
            return default
    
    # ====== 清理和维护方法 ======
    
    def _cleanup_loop(self):
        """清理过期数据的循环"""
        while self._running:
            try:
                self.cleanup_expired_data()
                time.sleep(3600)  # 每小时清理一次
            except Exception as e:
                print(f"清理循环错误: {e}")
                time.sleep(300)
    
    def cleanup_expired_data(self) -> Dict[str, int]:
        """
        清理过期数据
        
        Returns:
            Dict[str, int]: 各项清理数量
        """
        counts = {}
        
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                current_time = datetime.now().isoformat()
                
                # 清理过期的上传会话
                cursor.execute('''
                    UPDATE upload_sessions 
                    SET status = 'expired' 
                    WHERE expires_at <= ? AND status != 'completed'
                ''', (current_time,))
                
                counts["expired_sessions"] = cursor.rowcount
                
                # 清理长期失败的任务（超过7天）
                week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                cursor.execute('''
                    DELETE FROM vectorization_tasks 
                    WHERE status = 'failed' AND completed_at <= ?
                ''', (week_ago,))
                
                counts["old_failed_tasks"] = cursor.rowcount
                
                # 清理已删除的文件元数据（超过30天）
                month_ago = (datetime.now() - timedelta(days=30)).isoformat()
                cursor.execute('''
                    DELETE FROM file_metadata 
                    WHERE deleted_at IS NOT NULL AND deleted_at <= ?
                ''', (month_ago,))
                
                counts["old_deleted_files"] = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                # 清理临时目录
                temp_dir = Path("uploads/temp")
                if temp_dir.exists():
                    cleaned_dirs = 0
                    for session_dir in temp_dir.iterdir():
                        if session_dir.is_dir():
                            # 检查是否过期
                            session_json = session_dir / "session.json"
                            if session_json.exists():
                                try:
                                    with open(session_json, 'r') as f:
                                        session_data = json.load(f)
                                    
                                    expires_at = datetime.fromisoformat(session_data.get("expires_at", "1970-01-01"))
                                    if datetime.now() > expires_at:
                                        shutil.rmtree(session_dir, ignore_errors=True)
                                        cleaned_dirs += 1
                                except:
                                    # 如果无法解析，清理
                                    shutil.rmtree(session_dir, ignore_errors=True)
                                    cleaned_dirs += 1
                    
                    counts["cleaned_temp_dirs"] = cleaned_dirs
                
                return counts
                
        except Exception as e:
            print(f"清理过期数据失败: {e}")
            return {}
    
    def _health_check_loop(self):
        """健康检查循环"""
        while self._running:
            try:
                self.run_health_check()
                time.sleep(300)  # 每5分钟检查一次
            except Exception as e:
                print(f"健康检查循环错误: {e}")
                time.sleep(60)
    
    def run_health_check(self) -> Dict[str, Any]:
        """
        运行健康检查
        
        Returns:
            Dict[str, Any]: 健康检查结果
        """
        health = {
            "timestamp": datetime.now().isoformat(),
            "database": "unknown",
            "sessions": 0,
            "tasks": 0,
            "files": 0,
            "issues": []
        }
        
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 检查数据库连接
                cursor.execute("SELECT 1")
                health["database"] = "healthy"
                
                # 统计活跃会话
                current_time = datetime.now().isoformat()
                cursor.execute('''
                    SELECT COUNT(*) FROM upload_sessions 
                    WHERE expires_at > ? AND status = 'active'
                ''', (current_time,))
                
                health["sessions"] = cursor.fetchone()[0]
                
                # 统计进行中任务
                cursor.execute('''
                    SELECT COUNT(*) FROM vectorization_tasks 
                    WHERE status IN ('pending', 'processing', 'paused', 'resumable')
                ''')
                
                health["tasks"] = cursor.fetchone()[0]
                
                # 统计文件
                cursor.execute('''
                    SELECT COUNT(*) FROM file_metadata WHERE deleted_at IS NULL
                ''')
                
                health["files"] = cursor.fetchone()[0]
                
                # 检查潜在问题
                # 1. 检查有会话但无对应文件的任务
                cursor.execute('''
                    SELECT vt.task_id, vt.kb_id, vt.file_path
                    FROM vectorization_tasks vt
                    LEFT JOIN file_metadata fm ON vt.file_path = fm.file_path
                    WHERE fm.file_id IS NULL AND vt.status NOT IN ('completed', 'failed', 'cancelled')
                ''')
                
                orphaned_tasks = cursor.fetchall()
                if orphaned_tasks:
                    health["issues"].append({
                        "type": "orphaned_tasks",
                        "count": len(orphaned_tasks),
                        "sample": orphaned_tasks[:3]
                    })
                
                # 2. 检查长时间运行的任务
                hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
                cursor.execute('''
                    SELECT task_id, kb_id, file_path, status, started_at
                    FROM vectorization_tasks 
                    WHERE started_at IS NOT NULL AND started_at <= ? 
                    AND status = 'processing'
                ''', (hour_ago,))
                
                long_running = cursor.fetchall()
                if long_running:
                    health["issues"].append({
                        "type": "long_running_tasks",
                        "count": len(long_running),
                        "sample": long_running[:3]
                    })
                
                conn.close()
                
        except Exception as e:
            health["database"] = "unhealthy"
            health["issues"].append({
                "type": "database_error",
                "error": str(e)
            })
        
        # 保存健康状态
        self.save_system_state("health_check", health, "最近一次健康检查")
        
        return health
    
    def backup_database(self, backup_dir: Path = Path("data/backups")) -> Optional[Path]:
        """
        备份数据库
        
        Args:
            backup_dir: 备份目录
            
        Returns:
            Optional[Path]: 备份文件路径，失败返回None
        """
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"upload_db_{timestamp}.db"
            
            # 使用SQLite的备份API
            source_conn = sqlite3.connect(self.db_path)
            backup_conn = sqlite3.connect(backup_path)
            
            source_conn.backup(backup_conn)
            
            backup_conn.close()
            source_conn.close()
            
            # 记录备份
            self.save_system_state(
                "last_backup",
                {
                    "timestamp": timestamp,
                    "path": str(backup_path),
                    "size": backup_path.stat().st_size
                },
                "数据库备份"
            )
            
            return backup_path
            
        except Exception as e:
            print(f"数据库备份失败: {e}")
            return None
    
    def restore_database(self, backup_path: Path) -> bool:
        """
        从备份恢复数据库
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            bool: 恢复是否成功
        """
        if not backup_path.exists():
            print(f"备份文件不存在: {backup_path}")
            return False
        
        try:
            # 关闭所有连接
            self.shutdown()
            time.sleep(2)
            
            # 备份当前数据库
            temp_backup = self.db_path.with_suffix(".db.bak")
            if self.db_path.exists():
                shutil.copy2(self.db_path, temp_backup)
            
            # 恢复备份
            shutil.copy2(backup_path, self.db_path)
            
            # 重新初始化
            self._running = True
            self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self._cleanup_thread.start()
            self._health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
            self._health_check_thread.start()
            
            # 记录恢复
            self.save_system_state(
                "last_restore",
                {
                    "timestamp": datetime.now().isoformat(),
                    "backup_path": str(backup_path),
                    "original_backup": str(temp_backup) if temp_backup.exists() else None
                },
                "数据库恢复"
            )
            
            return True
            
        except Exception as e:
            print(f"数据库恢复失败: {e}")
            
            # 尝试恢复备份
            if temp_backup.exists():
                try:
                    shutil.copy2(temp_backup, self.db_path)
                except:
                    pass
            
            return False
    
    def shutdown(self):
        """关闭持久化管理器"""
        self._running = False
        
        if self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        
        if self._health_check_thread.is_alive():
            self._health_check_thread.join(timeout=5)
        
        print("持久化管理器已关闭")


# 全局持久化实例
_global_persistence: Optional[UploadPersistence] = None

def get_persistence() -> UploadPersistence:
    """获取全局持久化实例"""
    global _global_persistence
    if _global_persistence is None:
        _global_persistence = UploadPersistence()
    return _global_persistence


if __name__ == "__main__":
    # 测试模块
    print("上传和向量化状态持久化模块 v1.0")
    print(f"数据库路径: {Path('data/upload_persistence.db').absolute()}")
    print(f"数据目录: {Path('data').absolute()}")
    
    # 测试功能
    persistence = get_persistence()
    
    # 运行健康检查
    health = persistence.run_health_check()
    print(f"健康检查: {health}")
    
    # 保存系统状态
    persistence.save_system_state("test_key", {"test": "value", "time": datetime.now().isoformat()})
    
    # 加载系统状态
    state = persistence.load_system_state("test_key")
    print(f"加载的系统状态: {state}")
    
    print("模块测试完成")