#!/usr/bin/env python3
"""
分块上传和断点续传模块

功能：
1. 支持大文件分块上传
2. 支持断点续传
3. 支持并行上传
4. 实时上传进度跟踪
5. 文件完整性校验
"""

import hashlib
import json
import os
import shutil
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, BinaryIO
from fastapi import HTTPException, UploadFile

# 配置常量
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB分块
MAX_CHUNKS_PER_FILE = 10000   # 最大分块数（5MB*10000≈50GB）
RESUME_EXPIRY_HOURS = 24      # 断点续传有效期24小时
# 临时上传目录（使用绝对路径，与app.py保持一致）
UPLOAD_TEMP_DIR = Path(__file__).resolve().parent / "uploads" / "temp" / "chunks"

# 确保目录存在
UPLOAD_TEMP_DIR.mkdir(parents=True, exist_ok=True)

# 内存中存储上传会话状态
UPLOAD_SESSIONS: Dict[str, dict] = {}


class ChunkedUploadSession:
    """分块上传会话管理"""
    
    def __init__(self, 
                 kb_id: str,
                 filename: str,
                 file_size: int,
                 total_chunks: int,
                 md5_hash: str = ""):
        self.session_id = str(uuid.uuid4())
        self.kb_id = kb_id
        self.filename = filename
        self.file_size = file_size
        self.total_chunks = total_chunks
        self.md5_hash = md5_hash
        
        # 上传状态
        self.uploaded_chunks: Dict[int, bool] = {i: False for i in range(total_chunks)}
        self.chunk_hashes: Dict[int, str] = {}
        self.chunk_files: Dict[int, Path] = {}
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        
        # 创建临时目录
        self.temp_dir = UPLOAD_TEMP_DIR / self.session_id
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 会话元数据文件
        self.meta_file = self.temp_dir / "session.json"
        self._save_metadata()
        
        # 注册会话
        UPLOAD_SESSIONS[self.session_id] = self
        
    def _save_metadata(self):
        """保存会话元数据到文件"""
        metadata = {
            "session_id": self.session_id,
            "kb_id": self.kb_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "total_chunks": self.total_chunks,
            "md5_hash": self.md5_hash,
            "uploaded_chunks": self.uploaded_chunks,
            "chunk_hashes": self.chunk_hashes,
            "chunk_files": {},
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
        }
        
        # 转换Path对象为字符串
        for chunk_id, chunk_path in self.chunk_files.items():
            metadata["chunk_files"][chunk_id] = str(chunk_path)
        
        with open(self.meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_metadata(cls, session_id: str) -> Optional['ChunkedUploadSession']:
        """从元数据文件加载会话"""
        meta_file = UPLOAD_TEMP_DIR / session_id / "session.json"
        if not meta_file.exists():
            return None
        
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            session = cls(
                kb_id=metadata["kb_id"],
                filename=metadata["filename"],
                file_size=metadata["file_size"],
                total_chunks=metadata["total_chunks"],
                md5_hash=metadata.get("md5_hash", "")
            )
            session.session_id = metadata["session_id"]
            session.uploaded_chunks = metadata["uploaded_chunks"]
            session.chunk_hashes = metadata.get("chunk_hashes", {})
            session.created_at = datetime.fromisoformat(metadata["created_at"])
            session.last_activity = datetime.fromisoformat(metadata["last_activity"])
            
            # 恢复chunk_files
            for chunk_id, chunk_path_str in metadata.get("chunk_files", {}).items():
                session.chunk_files[int(chunk_id)] = Path(chunk_path_str)
            
            # 验证分块文件是否存在
            for chunk_id in session.uploaded_chunks.keys():
                if session.uploaded_chunks.get(chunk_id):
                    chunk_path = session.chunk_files.get(chunk_id)
                    if not chunk_path or not chunk_path.exists():
                        # 如果文件丢失，标记为未上传
                        session.uploaded_chunks[chunk_id] = False
            
            return session
        except Exception as e:
            print(f"加载会话失败 {session_id}: {e}")
            return None
    
    def update_chunk(self, chunk_id: int, chunk_data: bytes, chunk_hash: str) -> Path:
        """更新一个分块数据"""
        if chunk_id < 0 or chunk_id >= self.total_chunks:
            raise ValueError(f"分块ID超出范围: {chunk_id}")
        
        # 计算接收到的数据哈希
        received_hash = hashlib.md5(chunk_data).hexdigest()
        if chunk_hash and received_hash != chunk_hash:
            raise ValueError(f"分块哈希不匹配: 期望{chunk_hash}, 实际{received_hash}")
        
        # 保存分块到临时文件
        chunk_filename = f"chunk_{chunk_id:06d}.bin"
        chunk_path = self.temp_dir / chunk_filename
        
        # 写入文件
        with open(chunk_path, 'wb') as f:
            f.write(chunk_data)
        
        # 更新状态
        self.uploaded_chunks[chunk_id] = True
        self.chunk_hashes[chunk_id] = received_hash
        self.chunk_files[chunk_id] = chunk_path
        self.last_activity = datetime.now()
        
        # 保存元数据
        self._save_metadata()
        
        return chunk_path
    
    def get_missing_chunks(self) -> List[int]:
        """获取缺失的分块列表"""
        return [chunk_id for chunk_id, uploaded in self.uploaded_chunks.items() 
                if not uploaded]
    
    def get_progress(self) -> Dict:
        """获取上传进度信息"""
        uploaded_count = sum(1 for uploaded in self.uploaded_chunks.values() if uploaded)
        progress_percent = (uploaded_count / self.total_chunks * 100) if self.total_chunks > 0 else 0
        
        return {
            "session_id": self.session_id,
            "uploaded": uploaded_count,
            "total": self.total_chunks,
            "progress": round(progress_percent, 2),
            "missing_chunks": self.get_missing_chunks(),
            "is_complete": uploaded_count == self.total_chunks,
        }
    
    def assemble_file(self, target_path: Path) -> Tuple[bool, str]:
        """组装分块为完整文件"""
        # 检查是否所有分块都已上传
        if not self.is_complete():
            return False, "文件上传未完成"
        
        try:
            # 按照分块ID顺序组装文件
            with open(target_path, 'wb') as output_file:
                for chunk_id in sorted(self.chunk_files.keys()):
                    chunk_path = self.chunk_files[chunk_id]
                    if not chunk_path.exists():
                        return False, f"分块文件丢失: {chunk_id}"
                    
                    # 验证文件哈希
                    with open(chunk_path, 'rb') as chunk_file:
                        chunk_data = chunk_file.read()
                        chunk_hash = hashlib.md5(chunk_data).hexdigest()
                        
                        if self.chunk_hashes.get(chunk_id) != chunk_hash:
                            return False, f"分块哈希验证失败: {chunk_id}"
                    
                    # 写入完整文件
                    output_file.write(chunk_data)
            
            # 验证完整文件大小
            file_size = target_path.stat().st_size
            if file_size != self.file_size:
                return False, f"文件大小不匹配: 期望{self.file_size}, 实际{file_size}"
            
            # 可选的MD5验证
            if self.md5_hash:
                with open(target_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                if file_hash != self.md5_hash:
                    return False, f"文件哈希不匹配: 期望{self.md5_hash}, 实际{file_hash}"
            
            return True, "文件组装成功"
        except Exception as e:
            return False, f"文件组装失败: {str(e)}"
    
    def is_complete(self) -> bool:
        """检查文件是否已完整上传"""
        return all(self.uploaded_chunks.values())
    
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        expiry_time = self.last_activity.replace(tzinfo=None) if self.last_activity.tzinfo else self.last_activity
        expiry_time = expiry_time + datetime.timedelta(hours=RESUME_EXPIRY_HOURS)
        return datetime.now() > expiry_time
    
    def cleanup(self):
        """清理会话临时文件"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"清理会话失败 {self.session_id}: {e}")
        
        # 从内存中移除
        if self.session_id in UPLOAD_SESSIONS:
            del UPLOAD_SESSIONS[self.session_id]
    
    def to_dict(self) -> Dict:
        """转换为字典，用于API响应"""
        progress = self.get_progress()
        return {
            "session_id": self.session_id,
            "kb_id": self.kb_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "progress": progress,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_expired": self.is_expired(),
        }


class ChunkedUploadManager:
    """分块上传管理器"""
    
    @staticmethod
    def create_session(kb_id: str, filename: str, file_size: int, 
                      md5_hash: str = "") -> ChunkedUploadSession:
        """创建新的上传会话"""
        # 验证文件大小
        if file_size <= 0:
            raise HTTPException(status_code=400, detail="无效的文件大小")
        
        # 计算分块数量
        total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
        if total_chunks > MAX_CHUNKS_PER_FILE:
            raise HTTPException(
                status_code=400, 
                detail=f"文件过大，最多支持{MAX_CHUNKS_PER_FILE}个分块"
            )
        
        # 创建新会话
        session = ChunkedUploadSession(
            kb_id=kb_id,
            filename=filename,
            file_size=file_size,
            total_chunks=total_chunks,
            md5_hash=md5_hash
        )
        
        return session
    
    @staticmethod
    def get_session(session_id: str) -> Optional[ChunkedUploadSession]:
        """获取上传会话"""
        # 首先检查内存
        if session_id in UPLOAD_SESSIONS:
            session = UPLOAD_SESSIONS[session_id]
            if session.is_expired():
                session.cleanup()
                return None
            return session
        
        # 尝试从文件加载
        session = ChunkedUploadSession.load_from_metadata(session_id)
        if session:
            if session.is_expired():
                session.cleanup()
                return None
            UPLOAD_SESSIONS[session_id] = session
            return session
        
        return None
    
    @staticmethod
    def upload_chunk(session_id: str, chunk_id: int, 
                     chunk_data: bytes, chunk_hash: str = "") -> Dict:
        """上传分块数据"""
        session = ChunkedUploadManager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="上传会话不存在或已过期")
        
        # 验证分块ID
        if chunk_id < 0 or chunk_id >= session.total_chunks:
            raise HTTPException(status_code=400, detail="无效的分块ID")
        
        # 检查分块是否已上传
        if session.uploaded_chunks.get(chunk_id, False):
            return {
                "session_id": session_id,
                "chunk_id": chunk_id,
                "status": "already_uploaded",
                "progress": session.get_progress()
            }
        
        try:
            # 更新分块
            session.update_chunk(chunk_id, chunk_data, chunk_hash)
            
            return {
                "session_id": session_id,
                "chunk_id": chunk_id,
                "status": "uploaded",
                "progress": session.get_progress()
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"上传分块失败: {str(e)}")
    
    @staticmethod
    def get_progress(session_id: str) -> Dict:
        """获取上传进度"""
        session = ChunkedUploadManager.get_session(session_id)
        if not session:
            # 尝试加载已完成的会话
            session_dir = UPLOAD_TEMP_DIR / session_id
            if session_dir.exists():
                # 可能是已完成的会话，但已从内存中移除
                return {
                    "session_id": session_id,
                    "status": "completed_or_expired",
                    "message": "会话可能已完成或已过期"
                }
            raise HTTPException(status_code=404, detail="上传会话不存在")
        
        return session.get_progress()
    
    @staticmethod
    def cleanup_expired_sessions():
        """清理过期的上传会话"""
        expired_sessions = []
        
        for session_id in list(UPLOAD_SESSIONS.keys()):
            session = UPLOAD_SESSIONS[session_id]
            if session.is_expired():
                expired_sessions.append(session_id)
                session.cleanup()
        
        # 也检查磁盘上的过期会话
        if UPLOAD_TEMP_DIR.exists():
            for session_dir in UPLOAD_TEMP_DIR.iterdir():
                if session_dir.is_dir():
                    session_id = session_dir.name
                    if session_id not in UPLOAD_SESSIONS:
                        # 尝试加载并检查是否过期
                        session = ChunkedUploadSession.load_from_metadata(session_id)
                        if session and session.is_expired():
                            session.cleanup()
        
        return expired_sessions
    
    @staticmethod
    def list_sessions() -> List[Dict]:
        """列出所有活跃的上传会话"""
        sessions = []
        
        # 从内存中获取
        for session_id, session in UPLOAD_SESSIONS.items():
            if not session.is_expired():
                sessions.append(session.to_dict())
        
        return sessions


# 后台任务：定期清理过期会话
import threading
import asyncio

_cleanup_running = False

def start_cleanup_task():
    """启动后台清理任务"""
    global _cleanup_running
    if _cleanup_running:
        return
    
    _cleanup_running = True
    
    async def cleanup_loop():
        while _cleanup_running:
            try:
                expired = ChunkedUploadManager.cleanup_expired_sessions()
                if expired:
                    print(f"清理了 {len(expired)} 个过期上传会话")
            except Exception as e:
                print(f"清理上传会话失败: {e}")
            
            # 每小时清理一次
            await asyncio.sleep(3600)
    
    # 启动后台任务
    asyncio.create_task(cleanup_loop())

if __name__ == "__main__":
    # 模块测试
    print("Chunked Upload Module v1.0")
    print(f"分块大小: {CHUNK_SIZE / 1024 / 1024:.1f}MB")
    print(f"最大分块数: {MAX_CHUNKS_PER_FILE}")
    print(f"临时目录: {UPLOAD_TEMP_DIR.absolute()}")
    
    # 清理临时目录
    import sys
    if "--cleanup" in sys.argv:
        if UPLOAD_TEMP_DIR.exists():
            shutil.rmtree(UPLOAD_TEMP_DIR)
            print("清理了临时目录")
    
    print("模块加载完成")