"""
简易性能优化工具
针对RAG系统的简单、直接性能优化解决方案
"""

import time
import functools
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)

# ============================================
# 基本性能装饰器
# ============================================

def timed(func: Callable = None, *, name: str = None, log_level: str = "info"):
    """
    性能计时装饰器
    """
    if func is None:
        return lambda f: timed(f, name=name, log_level=log_level)
    
    func_name = name or func.__name__
    
    def sync_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start_time
            log_func = getattr(logger, log_level, logger.info)
            log_func(f"[性能监控] {func_name} 执行时间: {elapsed:.4f}秒")
    
    async def async_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start_time
            log_func = getattr(logger, log_level, logger.info)
            log_func(f"[性能监控] {func_name} 执行时间: {elapsed:.4f}秒")
    
    import inspect
    return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

# ============================================
# 简易缓存系统
# ============================================

class SimpleCache:
    """简易缓存系统"""
    
    def __init__(self, max_size: int = 100):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        
    def _generate_key(self, func_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [func_name]
        
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
        
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
            
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self.cache:
            return None
            
        entry = self.cache[key]
        if datetime.now() > entry['expires_at']:
            del self.cache[key]
            return None
            
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """设置缓存值"""
        if len(self.cache) >= self.max_size:
            del self.cache[next(iter(self.cache))]
            
        self.cache[key] = {
            'value': value,
            'expires_at': datetime.now() + timedelta(seconds=ttl)
        }
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()

# 全局缓存实例
cache = SimpleCache(max_size=200)

def cached(func: Callable = None, *, ttl: int = 300, key_prefix: str = None):
    """
    缓存装饰器
    """
    if func is None:
        return lambda f: cached(f, ttl=ttl, key_prefix=key_prefix)
    
    func_name = key_prefix or func.__name__
    
    def sync_wrapper(*args, **kwargs):
        cache_key = cache._generate_key(func_name, *args, **kwargs)
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            logger.debug(f"[缓存命中] {func_name}")
            return cached_value
            
        result = func(*args, **kwargs)
        cache.set(cache_key, result, ttl=ttl)
        return result
    
    async def async_wrapper(*args, **kwargs):
        cache_key = cache._generate_key(func_name, *args, **kwargs)
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            logger.debug(f"[缓存命中] {func_name}")
            return cached_value
            
        result = await func(*args, **kwargs)
        cache.set(cache_key, result, ttl=ttl)
        return result
    
    import inspect
    return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

# ============================================
# FastAPI集成
# ============================================

def integrate_with_fastapi(app):
    """
    集成到FastAPI应用
    """
    try:
        from fastapi import APIRouter
        
        router = APIRouter()
        
        @router.get("/performance/cache_info")
        async def cache_info():
            return {
                'cache_size': len(cache.cache),
                'max_size': cache.max_size,
                'message': '性能优化系统已启用'
            }
        
        @router.post("/performance/clear_cache")
        async def clear_cache():
            cache.clear()
            return {'message': '缓存已清空'}
        
        app.include_router(router, prefix="/api")
        logger.info("性能优化工具已集成到FastAPI应用")
        
    except ImportError:
        logger.warning("FastAPI未安装，跳过FastAPI集成")
    
    return app

# ============================================
# 使用示例
# ============================================

if __name__ == "__main__":
    print("简易性能优化工具测试...")
    
    @timed
    def test_function():
        print("测试函数执行...")
        return "成功"
    
    result = test_function()
    print(f"结果: {result}")