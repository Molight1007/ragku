#!/usr/bin/env python3
"""
性能优化集成脚本
将性能优化功能集成到新版本的RAG系统中
"""

import os
import re
from pathlib import Path

def add_performance_imports(app_py_content):
    """添加性能优化导入"""
    
    # 找到fastapi导入位置
    lines = app_py_content.split('\n')
    
    # 查找fastapi导入位置
    for i, line in enumerate(lines):
        if 'from fastapi import' in line:
            # 在导入后添加性能优化导入
            performance_imports = """\n# 性能优化模块 - 添加性能监控和缓存
try:
    from simple_performance import timed, cached, integrate_with_fastapi, cache
    print("性能优化模块导入成功")
except ImportError:
    print("警告: simple_performance 模块未找到，跳过性能优化集成")
    # 创建空的装饰器防止导入错误
    def timed(func=None, *args, **kwargs):
        def decorator(f):
            return f
        return decorator if func is None else decorator(func)
    
    def cached(func=None, *args, **kwargs):
        def decorator(f):
            return f
        return decorator if func is None else decorator(func)
    
    cache = None
    
# FastAPI增强导入
from fastapi.middleware.gzip import GZipMiddleware"""
            
            # 更新FastAPI导入行
            if 'UploadFile' not in line:
                lines[i] = line.replace('UploadFile', 'UploadFile, Request')
            
            # 在FastAPI导入后插入性能优化导入
            lines.insert(i + 1, performance_imports)
            break
    
    return '\n'.join(lines)

def add_performance_middleware(app_py_content):
    """添加性能优化中间件"""
    
    # 找到CORS中间件添加位置
    cors_pattern = r'app\.add_middleware\(\s*CORSMiddleware'
    match = re.search(cors_pattern, app_py_content)
    
    if match:
        # 在CORS中间件后添加GZIP和性能优化集成
        gzip_and_integration = """\n# 添加GZIP压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 集成性能优化到FastAPI应用
try:
    app = integrate_with_fastapi(app)
    print("性能优化集成到FastAPI应用完成")
except Exception as e:
    print(f"性能优化集成失败: {e}")
"""
        # 找到CORS中间件结束位置
        end_pos = app_py_content.find(')', match.end()) + 1
        # 在CORS中间件后插入性能优化
        app_py_content = app_py_content[:end_pos] + gzip_and_integration + app_py_content[end_pos:]
    
    return app_py_content

def add_performance_decorators(app_py_content):
    """为关键路由添加性能优化装饰器"""
    
    # 为聊天接口添加装饰器
    chat_pattern = r'(@app\.post\("/chat".*?\)\s*\nasync def chat.*?:)'
    app_py_content = re.sub(chat_pattern, r'@app.post("/chat", response_model=ChatResponse)\n@timed(name="聊天接口")\n@cached(ttl=60)  # 缓存1分钟，相同的查询可以快速返回\nasync def chat(body: ChatRequest) -> ChatResponse:', app_py_content, flags=re.DOTALL)
    
    # 为文件上传接口添加装饰器
    file_upload_pattern = r'(@app\.post\("/api/upload/file".*?\)\s*\nasync def api_upload_file.*?:)'
    app_py_content = re.sub(file_upload_pattern, r'@app.post("/api/upload/file", response_model=UploadExtractResponse)\n@timed(name="文件上传接口")\nasync def api_upload_file(file: UploadFile = File(...)) -> UploadExtractResponse:', app_py_content, flags=re.DOTALL)
    
    # 为知识库上传接口添加装饰器
    kb_upload_pattern = r'(@app\.post\("/api/kb/upload".*?\)\s*\nasync def api_kb_upload.*?:)'
    app_py_content = re.sub(kb_upload_pattern, r'@app.post("/api/kb/upload", response_model=KnowledgeBaseInfo)\n@timed(name="知识库上传接口")\nasync def api_kb_upload(\n    kb_id: str = Form(...), \n    file: UploadFile = File(..., max_length=MAX_FILE_SIZE)\n) -> KnowledgeBaseInfo:', app_py_content, flags=re.DOTALL)
    
    return app_py_content

def main():
    """主函数"""
    
    app_py_path = Path("app.py")
    if not app_py_path.exists():
        print("错误: app.py 不存在")
        return
    
    # 读取app.py内容
    with open(app_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("开始集成性能优化...")
    
    # 添加性能优化导入
    content = add_performance_imports(content)
    print("已添加性能优化导入")
    
    # 添加性能优化中间件
    content = add_performance_middleware(content)
    print("已添加性能优化中间件")
    
    # 为关键函数添加装饰器
    content = add_performance_decorators(content)
    print("已为关键路由添加性能优化装饰器")
    
    # 保存更新后的文件
    with open(app_py_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✅ 性能优化集成完成！")
    print("\n已集成的功能：")
    print("1. 性能监控装饰器 (@timed) - 实时监控函数执行时间")
    print("2. 智能缓存系统 (@cached) - 自动缓存优化，支持LRU淘汰和TTL过期")
    print("3. GZIP压缩中间件 - 减少网络传输大小")
    print("4. Web框架集成 - 新增性能监控端点")
    
    print("\n优化后的接口：")
    print("- 聊天接口 (/chat) - 添加了性能监控和60秒缓存")
    print("- 文件上传接口 (/api/upload/file) - 添加了性能监控")
    print("- 知识库上传接口 (/api/kb/upload) - 添加了性能监控")
    
    # 检查性能优化文件是否存在
    if not Path("simple_performance.py").exists():
        print("\n⚠️ 注意：simple_performance.py 文件不存在")
        print("请确保性能优化模块已创建")

if __name__ == "__main__":
    main()