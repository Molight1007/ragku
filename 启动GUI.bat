@echo off
cd /d "%~dp0"

:: 创建虚拟环境（如果不存在）
if not exist ".venv\Scripts\python.exe" (
    echo 首次运行，正在创建虚拟环境...
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt -q
)

:: 启动图形界面
.venv\Scripts\python launcher.py
