"""
RAG系统性能优化器
提供完整的性能优化解决方案
"""

import time
import asyncio
import logging
import functools
from typing import Dict, Any, Callable, Optional, Union, List
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib
import inspect

logger = logging.getLogger(__name__)

# ============================================
# 1. 时间性能监控
# ============================================

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, enable_logging: bool = True):
        self.enable_logging = enable_logging
        self.metrics: Dict[str, List[float]] = {}
        
    def timed(self, func: Callable = None, *, name: str = None, log_level: str = "info"):
        """性能计时装饰器"""
        if func is None:
            return lambda f: self.timed(f, name=name, log_level=log_level)
            
        func_name = name or func.__name__
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.perf_counter() - start_time
                self._record_metric(func_name, elapsed)
                if self.enable_logging:
                    level = getattr(logger, log_level, logger.info)
                    level(f"[性能监控] {func_name} 执行时间: {elapsed:.4f}秒")
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = time.perf_counter() - start_time
                self._record_metric(func_name, elapsed)
                if self.enable_logging:
                    level = getattr(logger, log_level, logger.info)
                    level(f"[性能监控] {func_name} 执行时间: {elapsed:.4f}秒")
        
        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
    
    def _record_metric(self, func_name: str, elapsed: float):
        if func_name not in self.metrics:
            self.metrics[func_name] = []
        self.metrics[func_name].append(elapsed)
        
    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """获取性能统计信息"""
        stats = {}
        for func_name, times in self.metrics.items():
            if times:
                stats[func_name] = {
                    'count': len(times),
                    'total': sum(times),
                    'avg': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times),
                    'p95': sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0]
                }
        return stats
    
    def print_report(self):
        """打印性能报告"""
        stats = self.get_statistics()
        if not stats:
            print("无性能数据")
            return
            
        print("=" * 60)
        print("性能分析报告")
        print("=" * 60)
        for func_name, data in stats.items():
            print(f"{func_name}:")
            print(f"  - 调用次数: {data['count']}")
            print(f"  - 总耗时: {data['total']:.4f}s")
            print(f"  - 平均耗时: {data['avg']:.4f}s")
            print(f"  - 最快: {data['min']:.4f}s, 最慢: {data['max']:.4f}s")
            print(f"  - P95: {data['p95']:.4f}s")
        print("=" * 60)

# 全局性能监控器实例
monitor = PerformanceMonitor(enable_logging=True)

# 快捷装饰器
timed = monitor.timed

# ============================================
# 2. 智能缓存系统
# ============================================

class SmartCache:
    """智能缓存系统"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        
    def _generate_key(self, func_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [func_name]
        
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                try:
                    key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
                except:
                    key_parts.append(str(type(arg).__name__))
        
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
            
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self.cache:
            return None
            
        entry = self.cache[key]
        if 'expires_at' in entry and datetime.now() > entry['expires_at']:
            del self.cache[key]
            return None
            
        return entry.get('value')
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存值"""
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].get('access_time', datetime.min))
            del self.cache[oldest_key]
            
        entry = {
            'value': value,
            'access_time': datetime.now()
        }
        
        if ttl is not None:
            entry['expires_at'] = datetime.now() + timedelta(seconds=ttl)
            
        self.cache[key] = entry
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        
    def cached(self, func: Callable = None, *, ttl: Optional[int] = None, key_prefix: str = None):
        """缓存装饰器"""
        if func is None:
            return lambda f: self.cached(f, ttl=ttl, key_prefix=key_prefix)
            
        func_name = key_prefix or func.__name__
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = self._generate_key(func_name, *args, **kwargs)
            cached_value = self.get(cache_key)
            if cached_value is not None:
                logger.debug(f"[缓存命中] {func_name}")
                return cached_value
                
            result = func(*args, **kwargs)
            self.set(cache_key, result, ttl=ttl or self.default_ttl)
            return result
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_key = self._generate_key(func_name, *args, **kwargs)
            cached_value = self.get(cache_key)
            if cached_value is not None:
                logger.debug(f"[缓存命中] {func_name}")
                return cached_value
                
            result = await func(*args, **kwargs)
            self.set(cache_key, result, ttl=ttl or self.default_ttl)
            return result
        
        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

# 全局缓存实例
cache = SmartCache(max_size=500, default_ttl=600)

# 快捷装饰器
cached = cache.cached

# ============================================
# 3. Web框架集成
# ============================================

def integrate_performance_optimizations(app):
    """集成性能优化到Flask/FastAPI应用"""
    
    if hasattr(app, 'add_url_rule'):  # Flask
        @app.route('/performance/stats', methods=['GET'])
        def performance_stats():
            return {
                'status': 'success',
                'metrics': monitor.get_statistics(),
                'cache_size': len(cache.cache)
            }
        
        @app.route('/performance/clear_cache', methods=['POST'])
        def clear_cache():
            cache.clear()
            return {'status': 'success', 'message': '缓存已清空'}
            
    elif hasattr(app, 'add_api_route'):  # FastAPI
        from fastapi import APIRouter
        router = APIRouter()
        
        @router.get("/performance/stats")
        async def performance_stats():
            return {
                'status': 'success',
                'metrics': monitor.get_statistics(),
                'cache_size': len(cache.cache)
            }
        
        @router.post("/performance/clear_cache")
        async def clear_cache():
            cache.clear()
            return {'status': 'success', 'message': '缓存已清空'}
            
        app.include_router(router, prefix="/api")
    
    logger.info("性能优化集成完成")
    return app

# ============================================
# 4. 主函数
# ============================================

def create_optimization_package():
    """创建性能优化包并测试"""
    
    print("性能优化模块加载成功！")
    print("可用功能：")
    print("1. @timed - 性能计时装饰器")
    print("2. @cached - 智能缓存装饰器")
    print("3. monitor - 全局性能监控器")
    print("4. cache - 全局缓存系统")
    print("5. integrate_performance_optimizations(app) - 集成到Web框架")
    
    return monitor, cache

if __name__ == "__main__":
    create_optimization_package()