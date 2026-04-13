@echo off
chcp 65001 >nul
title 停止RAG服务

echo 正在停止RAG服务...

:: 查找并终止占用8000端口的进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo 终止进程 PID: %%a
    taskkill /F /PID %%a
)

echo 服务已停止
timeout /t 2
