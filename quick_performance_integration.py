#!/usr/bin/env python3
"""
快速性能优化集成
直接修改app.py文件，添加性能优化功能
"""

def main():
    # 读取app.py
    with open("app.py", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # 1. 添加性能优化导入（在第14行后）
    for i, line in enumerate(lines):
        if "from fastapi import FastAPI" in line and i < 20:
            # 扩展FastAPI导入
            lines[i] = "from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request\n"
            
            # 添加性能优化导入
            performance_imports = """# 性能优化模块 - 添加性能监控和缓存
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

# FastAPI增强组件
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

"""
            lines.insert(i + 1, performance_imports)
            break
    
    # 转换为完整文本
    content = "".join(lines)
    
    # 2. 添加性能优化中间件（在CORS中间件后）
    if "app.add_middleware(CORSMiddleware" in content:
        # 找到CORS中间件的位置
        cors_start = content.find("app.add_middleware(CORSMiddleware")
        cors_end = content.find(")", cors_start) + 1
        
        # 在CORS之后添加性能优化
        performance_middleware = """\n)
# 添加GZIP压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 集成性能优化到FastAPI应用
try:
    app = integrate_with_fastapi(app)
    print("性能优化集成到FastAPI应用完成")
except Exception as e:
    print(f"性能优化集成失败: {e}")
"""
        content = content[:cors_end] + performance_middleware + content[cors_end:]
    
    # 3. 为关键路由添加装饰器
    
    # a) 聊天接口
    if '@app.post("/chat", response_model=ChatResponse)' in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '@app.post("/chat", response_model=ChatResponse)' in line:
                decorated_line = '@app.post("/chat", response_model=ChatResponse)\n@timed(name="聊天接口")\n@cached(ttl=60)  # 缓存1分钟，相同的查询可以快速返回\nasync def chat'
                # 找到函数定义
                for j in range(i, min(i+10, len(lines))):
                    if 'async def chat' in lines[j]:
                        # 替换
                        lines[i] = decorated_line
                        # 更新函数定义行
                        lines[j] = lines[j].replace('async def chat', 'async def chat')
                        break
                break
        content = '\n'.join(lines)
    
    # b) 文件上传接口
    if '@app.post("/api/upload/file"' in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '@app.post("/api/upload/file"' in line:
                for j in range(i, min(i+20, len(lines))):
                    if 'async def api_upload_file' in lines[j]:
                        # 在函数定义前添加装饰器
                        lines.insert(j, '    @timed(name="文件上传接口")')
                        break
                break
        content = '\n'.join(lines)
    
    # c) 知识库上传接口
    if '@app.post("/api/kb/upload"' in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '@app.post("/api/kb/upload"' in line:
                for j in range(i, min(i+20, len(lines))):
                    if 'async def api_kb_upload' in lines[j]:
                        # 在函数定义前添加装饰器
                        lines.insert(j, '    @timed(name="知识库上传接口")')
                        break
                break
        content = '\n'.join(lines)
    
    # 保存修改后的文件
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("性能优化集成完成！")
    print("检查修改：")
    print("1. 性能优化导入已添加")
    print("2. GZIP压缩中间件已添加")
    print("3. 关键路由已添加性能监控装饰器")
    
    # 验证修改
    with open("app.py", "r", encoding="utf-8") as f:
        final_content = f.read()
    
    checks = [
        ("simple_performance 导入", "from simple_performance" in final_content),
        ("timed 装饰器", "@timed" in final_content),
        ("cached 装饰器", "@cached" in final_content),
        ("GZIP 中间件", "GZipMiddleware" in final_content),
        ("聊天接口优化", '@timed(name="聊天接口")' in final_content),
        ("文件上传接口优化", '@timed(name="文件上传接口")' in final_content),
        ("知识库上传接口优化", '@timed(name="知识库上传接口")' in final_content),
    ]
    
    print("\n验证结果：")
    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"{status} {check_name}")

if __name__ == "__main__":
    main()