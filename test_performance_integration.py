#!/usr/bin/env python3
"""
测试性能优化集成
验证性能优化是否成功集成到RAG系统中
"""

import re
from pathlib import Path

def check_performance_imports():
    """检查性能优化导入"""
    print("=== 检查性能优化导入 ===")
    
    with open("app.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查导入
    has_simple_performance = "from simple_performance" in content
    has_timed_decorator = "def timed(func=None" in content or "@timed" in content
    has_cached_decorator = "def cached(func=None" in content or "@cached" in content
    has_gzip_middleware = "GZipMiddleware" in content
    
    results = []
    if has_simple_performance:
        results.append("✓ simple_performance 模块导入")
    else:
        results.append("✗ simple_performance 模块未导入")
    
    if has_timed_decorator:
        results.append("✓ timed 装饰器定义")
    else:
        results.append("✗ timed 装饰器未定义")
    
    if has_cached_decorator:
        results.append("✓ cached 装饰器定义")
    else:
        results.append("✗ cached 装饰器未定义")
    
    if has_gzip_middleware:
        results.append("✓ GZIP压缩中间件")
    else:
        results.append("✗ GZIP压缩中间件未添加")
    
    return results, content

def check_decorated_routes(content):
    """检查添加了性能优化装饰器的路由"""
    print("\n=== 检查优化路由 ===")
    
    # 查找带有装饰器的路由
    routes = []
    
    # 聊天接口
    if "@timed.*聊天接口" in content:
        routes.append("聊天接口 (/chat) - 已添加性能监控和缓存")
    else:
        routes.append("聊天接口 (/chat) - 未添加性能优化")
    
    # 文件上传接口
    if "@timed.*文件上传接口" in content:
        routes.append("文件上传接口 (/api/upload/file) - 已添加性能监控")
    else:
        routes.append("文件上传接口 (/api/upload/file) - 未添加性能优化")
    
    # 知识库上传接口
    if "@timed.*知识库上传接口" in content:
        routes.append("知识库上传接口 (/api/kb/upload) - 已添加性能监控")
    else:
        routes.append("知识库上传接口 (/api/kb/upload) - 未添加性能优化")
    
    return routes

def check_performance_files():
    """检查性能优化文件"""
    print("\n=== 检查性能优化文件 ===")
    
    files = []
    
    # 检查文件是否存在
    if Path("performance_optimizer.py").exists():
        files.append("✓ performance_optimizer.py - 存在")
    else:
        files.append("✗ performance_optimizer.py - 缺失")
    
    if Path("simple_performance.py").exists():
        files.append("✓ simple_performance.py - 存在")
    else:
        files.append("✗ simple_performance.py - 缺失")
    
    if Path("PERFORMANCE_OPTIMIZATION_GUIDE.md").exists():
        files.append("✓ PERFORMANCE_OPTIMIZATION_GUIDE.md - 存在")
    else:
        files.append("✗ PERFORMANCE_OPTIMIZATION_GUIDE.md - 缺失")
    
    return files

def test_simple_performance_module():
    """测试simple_performance模块"""
    print("\n=== 测试性能优化模块 ===")
    
    try:
        # 尝试导入
        from simple_performance import timed, cached, cache
        imports_success = True
        msg = "✓ simple_performance 模块导入成功"
    except ImportError as e:
        imports_success = False
        msg = f"✗ simple_performance 模块导入失败: {e}"
    
    print(msg)
    
    if imports_success:
        # 测试装饰器功能
        print("测试装饰器功能：")
        
        @timed
        def test_function():
            return "测试成功"
        
        result = test_function()
        if result == "测试成功":
            print("✓ timed 装饰器工作正常")
        else:
            print("✗ timed 装饰器工作异常")
    
    return imports_success

def main():
    """主函数"""
    print("开始检查性能优化集成情况...\n")
    
    # 检查导入和中间件
    import_results, content = check_performance_imports()
    for result in import_results:
        print(result)
    
    # 检查优化路由
    route_results = check_decorated_routes(content)
    for result in route_results:
        print(result)
    
    # 检查文件
    file_results = check_performance_files()
    for result in file_results:
        print(result)
    
    # 测试模块
    test_simple_performance_module()
    
    print("\n=== 总结 ===")
    
    # 计算成功比例
    total_checks = len(import_results) + len(route_results) + len(file_results) + 1  # +1 for module test
    success_checks = sum(1 for r in import_results if r.startswith("✓")) + \
                    sum(1 for r in route_results if "已添加" in r) + \
                    sum(1 for r in file_results if r.startswith("✓"))
    
    print(f"总检查项: {total_checks}")
    print(f"成功项: {success_checks}")
    print(f"失败项: {total_checks - success_checks}")
    
    if success_checks >= total_checks - 1:  # 允许一个失败
        print("\n✅ 性能优化集成状态: 优秀")
    elif success_checks >= total_checks - 3:  # 允许三个失败
        print("\n⚠️ 性能优化集成状态: 一般")
    else:
        print("\n❌ 性能优化集成状态: 需要改进")
    
    print("\n建议：")
    print("1. 运行 app.py，查看控制台输出，确认性能优化已初始化")
    print("2. 测试聊天、文件上传等功能，观察性能监控日志")
    print("3. 访问 /api/performance/cache_info 查看缓存信息")

if __name__ == "__main__":
    main()