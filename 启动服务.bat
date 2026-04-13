@echo off
chcp 65001 >nul
cd /d "%~dp0"
title RAG知识库服务

echo 正在读取配置...
for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
    if "%%a"=="DASHSCOPE_API_KEY" set DASHSCOPE_API_KEY=%%b
)

if not defined DASHSCOPE_API_KEY (
    echo 错误：未找到 DASHSCOPE_API_KEY，请先配置密钥
    pause
    exit /b 1
)

echo 正在启动服务...
start "" "http://127.0.0.1:8000/chat-ui"
python -m uvicorn app:app --host 0.0.0.0 --port 8000
