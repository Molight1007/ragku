@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
    echo 未找到 python，请先安装并加入 PATH。
    pause
    exit /b 1
)
where pythonw >nul 2>&1
if errorlevel 1 (
    start "RAG启动器" /D "%~dp0." python.exe launcher.py
) else (
    start "RAG启动器" /D "%~dp0." pythonw.exe launcher.py
)
exit /b 0
