#!/usr/bin/env python3
"""
分块上传和向量化API模块

功能：
1. 分块上传API（创建会话、上传分块、获取进度）
2. 向量化任务管理API（创建任务、获取状态、暂停/恢复/取消）
3. 综合文件上传API（一站式上传和向量化）
4. 断点续传支持
5. 与现有知识库系统集成
"""

import asyncio
import hashlib
import json
import shutil
import time
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from chunked_upload import ChunkedUploadSession, ChunkedUploadManager
from vectorization_queue import VectorizationTask, TaskStatus, TaskPriority, VectorizationQueue, get_vectorization_queue
from upload_persistence import UploadPersistence, get_persistence

# 创建API路由器
router = APIRouter(prefix="/api/v2", tags=["上传和向量化"])

# 全局管理器实例
_upload_manager = None
_vectorization_queue = None
_persistence = None

def get_upload_manager():
    """获取上传管理器实例"""
    global _upload_manager
    if _upload_manager is None:
        _upload_manager = ChunkedUploadManager()
    return _upload_manager

def get_vectorization_queue_instance():
    """获取向量化队列实例"""
    global _vectorization_queue
    if _vectorization_queue is None:
        _vectorization_queue = get_vectorization_queue()
    return _vectorization_queue

def get_persistence_instance():
    """获取持久化实例"""
    global _persistence
    if _persistence is None:
        _persistence = get_persistence()
    return _persistence


# ====== 数据模型 ======

class CreateUploadSessionRequest(BaseModel):
    """创建上传会话请求"""
    kb_id: str = Field(..., description="知识库ID")
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    md5_hash: Optional[str] = Field(None, description="文件MD5哈希值（可选）")
    chunk_size: Optional[int] = Field(5 * 1024 * 1024, description="分块大小（字节），默认5MB")

class UploadSessionResponse(BaseModel):
    """上传会话响应"""
    session_id: str = Field(..., description="会话ID")
    kb_id: str = Field(..., description="知识库ID")
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小")
    total_chunks: int = Field(..., description="总分块数")
    chunk_size: int = Field(..., description="每块大小")
    expires_at: str = Field(..., description="过期时间")
    created_at: str = Field(..., description="创建时间")

class UploadChunkRequest(BaseModel):
    """上传分块请求"""
    chunk_id: int = Field(..., description="分块ID（从0开始）")
    chunk_hash: Optional[str] = Field(None, description="分块哈希值（可选）")
    
    class Config:
        schema_extra = {
            "example": {
                "chunk_id": 0,
                "chunk_hash": "d41d8cd98f00b204e9800998ecf8427e"
            }
        }

class UploadChunkResponse(BaseModel):
    """上传分块响应"""
    session_id: str = Field(..., description="会话ID")
    chunk_id: int = Field(..., description="分块ID")
    status: str = Field(..., description="上传状态")
    progress: Dict[str, Any] = Field(..., description="上传进度")
    missing_chunks: List[int] = Field(..., description="缺失的分块列表")

class UploadProgressResponse(BaseModel):
    """上传进度响应"""
    session_id: str = Field(..., description="会话ID")
    uploaded: int = Field(..., description="已上传分块数")
    total: int = Field(..., description="总分块数")
    progress: float = Field(..., description="进度百分比")
    missing_chunks: List[int] = Field(..., description="缺失的分块列表")
    is_complete: bool = Field(..., description="是否已完成")
    estimated_time: Optional[float] = Field(None, description="预计剩余时间（秒）")

class CompleteUploadResponse(BaseModel):
    """完成上传响应"""
    session_id: str = Field(..., description="会话ID")
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")
    file_path: Optional[str] = Field(None, description="文件保存路径")
    file_id: Optional[str] = Field(None, description="文件ID")
    vectorization_task_id: Optional[str] = Field(None, description="向量化任务ID")

class VectorizationTaskResponse(BaseModel):
    """向量化任务响应"""
    task_id: str = Field(..., description="任务ID")
    kb_id: str = Field(..., description="知识库ID")
    filename: str = Field(..., description="文件名")
    status: str = Field(..., description="任务状态")
    progress: float = Field(..., description="进度百分比")
    processed_chunks: int = Field(..., description="已处理分块数")
    total_chunks: int = Field(..., description="总分块数")
    failed_chunks: int = Field(..., description="失败的分块数")
    eta: Optional[float] = Field(None, description="预计完成时间（秒）")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: str = Field(..., description="创建时间")
    started_at: Optional[str] = Field(None, description="开始时间")
    completed_at: Optional[str] = None

class BatchUploadRequest(BaseModel):
    """批量上传请求"""
    kb_id: str = Field(..., description="知识库ID")
    files: List[Dict[str, Any]] = Field(..., description="文件信息列表")
    priority: Optional[str] = Field("normal", description="优先级（low/normal/high/urgent）")

class BatchUploadResponse(BaseModel):
    """批量上传响应"""
    session_id: str = Field(default="", description="会话ID")
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="消息")
    uploaded_files: int = Field(default=0, description="成功上传的文件数")
    failed_files: List[str] = Field(default_factory=list, description="失败的文件列表")

class ResumeUploadRequest(BaseModel):
    """恢复上传请求"""
    session_id: str = Field(..., description="会话ID")
    missing_chunks_only: Optional[bool] = Field(True, description="是否只上传缺失的分块")

class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="系统状态")
    timestamp: str = Field(..., description="检查时间")
    upload_sessions: int = Field(..., description="活跃上传会话数")
    vectorization_tasks: int = Field(..., description="进行中任务数")
    database: Dict[str, Any] = Field(..., description="数据库状态")
    issues: List[Dict[str, Any]] = Field(..., description="问题列表")

class SystemStatsResponse(BaseModel):
    """系统统计响应"""
    total_files: int = Field(..., description="总文件数")
    total_vectors: int = Field(..., description="总向量数")
    active_sessions: int = Field(..., description="活跃会话数")
    active_tasks: int = Field(..., description="活跃任务数")
    completed_today: int = Field(..., description="今日完成数")
    failed_today: int = Field(..., description="今日失败数")
    average_upload_speed: Optional[float] = Field(None, description="平均上传速度（MB/s）")
    average_vectorization_speed: Optional[float] = Field(None, description="平均向量化速度（chunks/s）")
    uptime: float = Field(..., description="系统运行时间（秒）")


# ====== 分块上传API ======

@router.post("/upload/sessions", response_model=UploadSessionResponse)
async def create_upload_session(
    request: CreateUploadSessionRequest,
    upload_manager: ChunkedUploadManager = Depends(get_upload_manager),
    persistence: UploadPersistence = Depends(get_persistence_instance)
):
    """
    创建分块上传会话
    
    用于上传大文件，支持断点续传和并行上传
    """
    try:
        # 验证知识库目录路径（与app.py保持一致）
        from pathlib import Path as AppPath
        kb_root = AppPath(__file__).resolve().parent / "uploads" / "knowledge_bases"
        kb_dir = kb_root / request.kb_id
        # 确保目录存在
        kb_dir.mkdir(parents=True, exist_ok=True)
        
        # 验证文件大小
        if request.file_size <= 0:
            raise HTTPException(status_code=400, detail="无效的文件大小")
        
        # 创建上传会话
        session = upload_manager.create_session(
            kb_id=request.kb_id,
            filename=request.filename,
            file_size=request.file_size,
            md5_hash=request.md5_hash or ""
        )
        
        # 保存到持久化存储
        persistence.save_upload_session(session)
        
        # 构建响应
        expires_at = datetime.now().timestamp() + (24 * 3600)  # 24小时后过期
        
        return UploadSessionResponse(
            session_id=session.session_id,
            kb_id=session.kb_id,
            filename=session.filename,
            file_size=session.file_size,
            total_chunks=session.total_chunks,
            chunk_size=5 * 1024 * 1024,  # 5MB
            expires_at=datetime.fromtimestamp(expires_at).isoformat(),
            created_at=session.created_at.isoformat() if session.created_at else datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建上传会话失败: {str(e)}")

@router.post("/upload/sessions/{session_id}/chunks/{chunk_id}", response_model=UploadChunkResponse)
async def upload_chunk(
    session_id: str,
    chunk_id: int,
    chunk_data: UploadFile = File(...),
    request_data: Optional[UploadChunkRequest] = None,
    upload_manager: ChunkedUploadManager = Depends(get_upload_manager),
    persistence: UploadPersistence = Depends(get_persistence_instance)
):
    """
    上传文件分块
    
    支持并行上传和断点续传
    """
    try:
        # 读取分块数据
        chunk_bytes = await chunk_data.read()
        
        # 获取请求参数
        chunk_hash = None
        if request_data:
            chunk_hash = request_data.chunk_hash
        
        # 上传分块
        result = upload_manager.upload_chunk(
            session_id=session_id,
            chunk_id=chunk_id,
            chunk_data=chunk_bytes,
            chunk_hash=chunk_hash
        )
        
        # 更新持久化存储
        session = upload_manager.get_session(session_id)
        if session:
            persistence.save_upload_session(session)
        
        return UploadChunkResponse(**result)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传分块失败: {str(e)}")

@router.get("/upload/sessions/{session_id}/progress", response_model=UploadProgressResponse)
async def get_upload_progress(
    session_id: str,
    upload_manager: ChunkedUploadManager = Depends(get_upload_manager)
):
    """
    获取上传进度
    
    用于显示上传进度和断点续传信息
    """
    try:
        progress = upload_manager.get_progress(session_id)
        
        # 估计剩余时间（简化的估算，实际可以有更复杂的算法）
        estimated_time = None
        if progress.get("uploaded", 0) > 0:
            # 假设平均上传速度为1MB/s
            chunk_size = 5 * 1024 * 1024  # 5MB
            remaining_chunks = len(progress.get("missing_chunks", []))
            estimated_time = remaining_chunks * chunk_size / (1024 * 1024)  # 秒
        
        return UploadProgressResponse(
            session_id=session_id,
            uploaded=progress.get("uploaded", 0),
            total=progress.get("total", 0),
            progress=progress.get("progress", 0),
            missing_chunks=progress.get("missing_chunks", []),
            is_complete=progress.get("is_complete", False),
            estimated_time=estimated_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取上传进度失败: {str(e)}")

@router.post("/upload/sessions/{session_id}/complete", response_model=CompleteUploadResponse)
async def complete_upload(
    session_id: str,
    upload_manager: ChunkedUploadManager = Depends(get_upload_manager),
    vectorization_queue: VectorizationQueue = Depends(get_vectorization_queue_instance),
    persistence: UploadPersistence = Depends(get_persistence_instance)
):
    """
    完成上传并触发向量化
    
    组装分块文件，保存到知识库，并创建向量化任务
    """
    try:
        session = upload_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="上传会话不存在或已过期")
        
        if not session.is_complete():
            raise HTTPException(status_code=400, detail="文件上传未完成，无法进行组装")
        
        # 组装文件（与app.py保持一致的路径）
        kb_root = Path(__file__).resolve().parent / "uploads" / "knowledge_bases"
        kb_dir = kb_root / session.kb_id
        kb_dir.mkdir(parents=True, exist_ok=True)
        
        files_dir = kb_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成安全的文件名
        import re
        safe_name = re.sub(r'[^\w\-_.]', '_', session.filename)
        timestamp = int(time.time())
        final_filename = f"{timestamp}_{safe_name}"
        target_path = files_dir / final_filename
        
        # 组装文件
        success, message = session.assemble_file(target_path)
        if not success:
            raise HTTPException(status_code=500, detail=f"文件组装失败: {message}")
        
        # 生成文件ID
        file_hash = hashlib.md5(target_path.read_bytes()).hexdigest()
        file_id = hashlib.md5(f"{session.kb_id}:{session.filename}:{session.file_size}:{file_hash}".encode()).hexdigest()
        
        # 保存文件元数据
        metadata = {
            "file_id": file_id,
            "kb_id": session.kb_id,
            "filename": final_filename,
            "original_name": session.filename,
            "file_size": target_path.stat().st_size,
            "file_hash": file_hash,
            "upload_session_id": session_id,
            "file_path": str(target_path),
            "created_at": datetime.now()
        }
        
        persistence.save_file_metadata(file_id, metadata)
        
        # 创建向量化任务
        # TODO: 暂时跳过，因为需要集成现有知识库系统
        task_id = None
        # task_id = vectorization_queue.add_task(
        #     kb_id=session.kb_id,
        #     file_path=target_path,
        #     priority=TaskPriority.NORMAL
        # )
        
        # 清理会话
        session.cleanup()
        
        return CompleteUploadResponse(
            session_id=session_id,
            success=True,
            message="文件上传和保存成功",
            file_path=str(target_path),
            file_id=file_id,
            vectorization_task_id=task_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"完成上传失败: {str(e)}")

@router.post("/upload/sessions/{session_id}/resume", response_model=UploadProgressResponse)
async def resume_upload(
    session_id: str,
    request: ResumeUploadRequest,
    upload_manager: ChunkedUploadManager = Depends(get_upload_manager)
):
    """
    恢复上传会话
    
    用于断点续传，可以只上传缺失的分块
    """
    try:
        session = upload_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="上传会话不存在或已过期")
        
        if session.is_complete():
            raise HTTPException(status_code=400, detail="文件已上传完成，无需恢复")
        
        # 获取缺失的分块
        missing_chunks = session.get_missing_chunks()
        
        if request.missing_chunks_only and not missing_chunks:
            raise HTTPException(status_code=400, detail="没有缺失的分块需要上传")
        
        # 获取进度
        progress_data = session.get_progress()
        
        return UploadProgressResponse(
            session_id=session_id,
            uploaded=progress_data.get("uploaded", 0),
            total=progress_data.get("total", 0),
            progress=progress_data.get("progress", 0),
            missing_chunks=missing_chunks,
            is_complete=progress_data.get("is_complete", False),
            estimated_time=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复上传失败: {str(e)}")

@router.delete("/upload/sessions/{session_id}")
async def cancel_upload_session(
    session_id: str,
    upload_manager: ChunkedUploadManager = Depends(get_upload_manager)
):
    """
    取消上传会话
    
    清除所有临时文件
    """
    try:
        session = upload_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="上传会话不存在")
        
        session.cleanup()
        
        return {"success": True, "message": "上传会话已取消"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消上传会话失败: {str(e)}")


# ====== 向量化任务API ======

@router.get("/vectorization/tasks/{task_id}", response_model=VectorizationTaskResponse)
async def get_vectorization_task(
    task_id: str,
    vectorization_queue: VectorizationQueue = Depends(get_vectorization_queue_instance)
):
    """
    获取向量化任务状态
    """
    try:
        task_info = vectorization_queue.get_task(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 转换格式
        return VectorizationTaskResponse(
            task_id=task_info.get("task_id", task_id),
            kb_id=task_info.get("kb_id", ""),
            filename=task_info.get("filename", ""),
            status=task_info.get("status", ""),
            progress=task_info.get("progress", 0),
            processed_chunks=task_info.get("processed", 0),
            total_chunks=task_info.get("total", 0),
            failed_chunks=task_info.get("failed", 0),
            eta=task_info.get("eta"),
            error_message=task_info.get("error"),
            created_at=task_info.get("created_at", datetime.now().isoformat()),
            started_at=task_info.get("started_at"),
            completed_at=task_info.get("completed_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务失败: {str(e)}")

@router.get("/kb/{kb_id}/vectorization/tasks", response_model=List[VectorizationTaskResponse])
async def get_kb_vectorization_tasks(
    kb_id: str,
    vectorization_queue: VectorizationQueue = Depends(get_vectorization_queue_instance)
):
    """
    获取知识库的所有向量化任务
    """
    try:
        tasks_info = vectorization_queue.get_kb_tasks(kb_id)
        
        response = []
        for task_info in tasks_info:
            response.append(VectorizationTaskResponse(
                task_id=task_info.get("task_id", ""),
                kb_id=task_info.get("kb_id", kb_id),
                filename=task_info.get("filename", ""),
                status=task_info.get("status", ""),
                progress=task_info.get("progress", 0),
                processed_chunks=task_info.get("processed", 0),
                total_chunks=task_info.get("total", 0),
                failed_chunks=task_info.get("failed", 0),
                eta=task_info.get("eta"),
                error_message=task_info.get("error"),
                created_at=task_info.get("created_at", datetime.now().isoformat()),
                started_at=task_info.get("started_at"),
                completed_at=task_info.get("completed_at")
            ))
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识库任务失败: {str(e)}")

@router.post("/vectorization/tasks/{task_id}/pause")
async def pause_vectorization_task(
    task_id: str,
    vectorization_queue: VectorizationQueue = Depends(get_vectorization_queue_instance)
):
    """
    暂停向量化任务
    """
    try:
        success = vectorization_queue.pause_task(task_id)
        if not success:
            raise HTTPException(status_code=400, detail="无法暂停任务")
        
        return {"success": True, "message": "任务已暂停"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"暂停任务失败: {str(e)}")

@router.post("/vectorization/tasks/{task_id}/resume")
async def resume_vectorization_task(
    task_id: str,
    vectorization_queue: VectorizationQueue = Depends(get_vectorization_queue_instance)
):
    """
    恢复向量化任务
    """
    try:
        success = vectorization_queue.resume_task(task_id)
        if not success:
            raise HTTPException(status_code=400, detail="无法恢复任务")
        
        return {"success": True, "message": "任务已恢复"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复任务失败: {str(e)}")

@router.post("/vectorization/tasks/{task_id}/cancel")
async def cancel_vectorization_task(
    task_id: str,
    vectorization_queue: VectorizationQueue = Depends(get_vectorization_queue_instance)
):
    """
    取消向量化任务
    """
    try:
        success = vectorization_queue.cancel_task(task_id)
        if not success:
            raise HTTPException(status_code=400, detail="无法取消任务")
        
        return {"success": True, "message": "任务已取消"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


# ====== 综合文件上传API ======

async def _save_upload_file(kb_id: str, file: UploadFile) -> Tuple[bool, str, str]:
    """保存单个上传文件，返回 (success, file_path_or_error, file_id)"""
    try:
        # 保存文件到临时位置
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp_file:
            chunk_size = 16 * 1024 * 1024  # 16MB
            file_size = 0
            
            while chunk := await file.read(chunk_size):
                tmp_file.write(chunk)
                file_size += len(chunk)
            
            temp_path = Path(tmp_file.name)
        
        # 保存文件到知识库（与app.py保持一致的路径）
        kb_root = Path(__file__).resolve().parent / "uploads" / "knowledge_bases"
        kb_dir = kb_root / kb_id
        kb_dir.mkdir(parents=True, exist_ok=True)
        
        files_dir = kb_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成安全的文件名
        import re
        safe_name = re.sub(r'[^\w\-_.]', '_', file.filename)
        timestamp = int(time.time())
        final_filename = f"{timestamp}_{safe_name}"
        target_path = files_dir / final_filename
        
        # 移动文件
        shutil.move(temp_path, target_path)
        
        # 生成文件ID
        file_hash = hashlib.md5(target_path.read_bytes()).hexdigest()
        file_id = hashlib.md5(f"{kb_id}:{file.filename}:{file_size}:{file_hash}".encode()).hexdigest()
        
        return True, str(target_path), file_id
    except Exception as e:
        return False, str(e), ""




async def _upload_file_complete_internal(
    kb_id: str,
    file: UploadFile,
    priority: str,
    upload_manager: ChunkedUploadManager,
    vectorization_queue: VectorizationQueue,
    persistence: UploadPersistence
):
    """
    一站式文件上传API内部实现
    
    结合分块上传和向量化，返回完整的结果
    """
    try:
        success, result, file_id = await _save_upload_file(kb_id, file)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"文件上传失败: {result}")
        
        # 创建上传会话
        session = upload_manager.create_session(
            kb_id=kb_id,
            filename=file.filename,
            file_size=file.size if hasattr(file, 'size') else 0,
            md5_hash=""
        )
        
        # 保存文件元数据
        metadata = {
            "file_id": file_id,
            "kb_id": kb_id,
            "filename": Path(result).name,
            "original_name": file.filename,
            "file_size": Path(result).stat().st_size if Path(result).exists() else 0,
            "file_hash": hashlib.md5(Path(result).read_bytes()).hexdigest() if Path(result).exists() else "",
            "upload_session_id": session.session_id,
            "file_path": result,
            "created_at": datetime.now()
        }
        
        persistence.save_file_metadata(file_id, metadata)
        
        return CompleteUploadResponse(
            session_id=session.session_id,
            success=True,
            message="文件上传成功",
            file_path=result,
            file_id=file_id,
            vectorization_task_id=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


async def upload_file_complete(
    kb_id: str = Form(...),
    file: UploadFile = File(...),
    priority: str = Form("normal"),
    upload_manager: ChunkedUploadManager = Depends(get_upload_manager),
    vectorization_queue: VectorizationQueue = Depends(get_vectorization_queue_instance),
    persistence: UploadPersistence = Depends(get_persistence_instance)
):
    """
    一站式文件上传API（FastAPI路由使用）
    
    结合分块上传和向量化，返回完整的结果
    """
    # 处理直接调用时 Depends 对象无法解析的问题
    from fastapi.params import Depends as FastAPIDepends
    
    actual_upload_manager = upload_manager
    actual_vectorization_queue = vectorization_queue
    actual_persistence = persistence
    
    # 如果参数是 Depends 对象，说明是直接调用，需要手动获取依赖
    try:
        if type(actual_upload_manager).__name__ == 'Depends':
            actual_upload_manager = get_upload_manager()
        if type(actual_vectorization_queue).__name__ == 'Depends':
            actual_vectorization_queue = get_vectorization_queue_instance()
        if type(actual_persistence).__name__ == 'Depends':
            actual_persistence = get_persistence_instance()
    except TypeError:
        # 在 FastAPI 路由调用时，这些参数已经被正确解析
        pass
    
    return await _upload_file_complete_internal(
        kb_id=kb_id,
        file=file,
        priority=priority,
        upload_manager=actual_upload_manager,
        vectorization_queue=actual_vectorization_queue,
        persistence=actual_persistence
    )


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_batch_files(
    kb_id: str = Form(...),
    files: List[UploadFile] = File(...),
    priority: str = Form("normal"),
    upload_manager: ChunkedUploadManager = Depends(get_upload_manager),
    persistence: UploadPersistence = Depends(get_persistence_instance)
):
    """
    批量上传多个文件
    
    支持同时上传多个文件，提高效率
    """
    try:
        success_count = 0
        failed_files = []
        file_ids = []
        
        # 并行保存所有文件
        results = await asyncio.gather(
            *[_save_upload_file(kb_id, f) for f in files],
            return_exceptions=True
        )
        
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                failed_files.append(f"{files[i].filename}: {str(r)}")
            else:
                success, result, file_id = r
                if success:
                    success_count += 1
                    file_ids.append(file_id)
                    
                    # 保存元数据
                    metadata = {
                        "file_id": file_id,
                        "kb_id": kb_id,
                        "filename": Path(result).name,
                        "original_name": files[i].filename,
                        "file_size": Path(result).stat().st_size if Path(result).exists() else 0,
                        "file_hash": hashlib.md5(Path(result).read_bytes()).hexdigest() if Path(result).exists() else "",
                        "file_path": result,
                        "created_at": datetime.now()
                    }
                    persistence.save_file_metadata(file_id, metadata)
                else:
                    failed_files.append(f"{files[i].filename}: {result}")
        
        message = f"成功上传 {success_count}/{len(files)} 个文件"
        if failed_files:
            message += f"，{len(failed_files)} 个失败"
        
        return BatchUploadResponse(
            session_id=hashlib.md5(str(datetime.now()).encode()).hexdigest()[:12],
            success=success_count > 0,
            message=message,
            uploaded_files=success_count,
            failed_files=failed_files
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量上传失败: {str(e)}")


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def batch_upload(
    request: BatchUploadRequest,
    upload_manager: ChunkedUploadManager = Depends(get_upload_manager),
    vectorization_queue: VectorizationQueue = Depends(get_vectorization_queue_instance),
    persistence: UploadPersistence = Depends(get_persistence_instance)
):
    """
    批量上传文件
    
    支持多个文件并行上传
    """
    # TODO: 实现批量上传
    return BatchUploadResponse(
        upload_session_ids=[],
        vectorization_task_ids=[],
        failed_files=[]
    )


# ====== 系统管理API ======

@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    persistence: UploadPersistence = Depends(get_persistence_instance)
):
    """
    系统健康检查
    """
    try:
        health = persistence.run_health_check()
        
        return HealthCheckResponse(
            status="healthy" if not health["issues"] else "degraded",
            timestamp=health.get("timestamp", datetime.now().isoformat()),
            upload_sessions=health.get("sessions", 0),
            vectorization_tasks=health.get("tasks", 0),
            database={"status": health.get("database", "unknown")},
            issues=health.get("issues", [])
        )
        
    except Exception as e:
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.now().isoformat(),
            upload_sessions=0,
            vectorization_tasks=0,
            database={"status": "error", "error": str(e)},
            issues=[{"type": "health_check_error", "error": str(e)}]
        )

@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    persistence: UploadPersistence = Depends(get_persistence_instance)
):
    """
    获取系统统计信息
    """
    try:
        health = persistence.run_health_check()
        
        # 计算今日统计数据（简化版）
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_str = today_start.isoformat()
        
        # 从持久化存储获取更多统计数据
        total_files = health.get("files", 0)
        active_sessions = health.get("sessions", 0)
        active_tasks = health.get("tasks", 0)
        
        # 统计总向量数（简化版，实际应从索引文件统计）
        total_vectors = total_files * 100  # 假设每个文件100个向量
        
        return SystemStatsResponse(
            total_files=total_files,
            total_vectors=total_vectors,
            active_sessions=active_sessions,
            active_tasks=active_tasks,
            completed_today=0,  # TODO: 实现实际统计
            failed_today=0,     # TODO: 实现实际统计
            average_upload_speed=None,  # TODO: 实现统计
            average_vectorization_speed=None,  # TODO: 实现统计
            uptime=time.time() - (24 * 3600)  # 假设运行24小时
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统统计失败: {str(e)}")

@router.post("/maintenance/cleanup")
async def cleanup_system():
    """
    清理系统临时文件和过期数据
    """
    try:
        upload_manager = get_upload_manager()
        persistence = get_persistence_instance()
        
        # 清理过期会话
        expired_sessions = upload_manager.cleanup_expired_sessions()
        
        # 清理数据库过期数据
        cleanup_stats = persistence.cleanup_expired_data()
        
        return {
            "success": True,
            "message": "系统清理完成",
            "expired_sessions": len(expired_sessions),
            "cleanup_stats": cleanup_stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系统清理失败: {str(e)}")

@router.post("/maintenance/backup")
async def backup_system():
    """
    备份系统数据
    """
    try:
        persistence = get_persistence_instance()
        backup_path = persistence.backup_database()
        
        if backup_path:
            return {
                "success": True,
                "message": "系统备份完成",
                "backup_path": str(backup_path),
                "size": backup_path.stat().st_size
            }
        else:
            raise HTTPException(status_code=500, detail="备份失败")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系统备份失败: {str(e)}")


# ====== 初始化函数 ======

def init_upload_system():
    """初始化上传系统"""
    print("初始化上传系统...")
    
    # 创建必要的目录（与app.py保持一致的路径）
    base_dir = Path(__file__).resolve().parent
    directories = [
        base_dir / "uploads",
        base_dir / "uploads" / "knowledge_bases",
        base_dir / "uploads" / "temp",
        base_dir / "uploads" / "temp" / "chunks",
        base_dir / "data",
        base_dir / "data" / "backups"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    
    # 启动后台任务
    from chunked_upload import start_cleanup_task
    start_cleanup_task()
    
    print("上传系统初始化完成")


# 导出API路由器
__all__ = ["router", "init_upload_system"]


if __name__ == "__main__":
    # 测试模块
    print("分块上传和向量化API模块 v1.0")
    print("=" * 60)
    
    # 测试初始化
    init_upload_system()
    
    # 列出API路由
    for route in router.routes:
        print(f"{route.methods} {route.path}")
    
    print(f"\n总计 {len(router.routes)} 个API端点")
    print("模块测试完成")