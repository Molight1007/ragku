@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
cd /d "%~dp0"
REM 使用 %%CD%% 避免 %%~dp0 尾部的 \ 与引号形成 \" 破坏 start /D 等命令
set "ROOT=%CD%"
set "PYEXE="
if exist "%ROOT%\.venv\Scripts\python.exe" set "PYEXE=%ROOT%\.venv\Scripts\python.exe"
if not defined PYEXE (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未找到 Python，且不存在 .venv\Scripts\python.exe
        pause
        exit /b 1
    )
    set "PYEXE=python"
)

if not exist "%ROOT%\.env" (
    echo [错误] 缺少 .env，请先配置密钥（01_一键配置密钥.cmd 或 启动.cmd 菜单）。
    pause
    exit /b 1
)
if not exist "%ROOT%\index_store.npy" (
    echo [错误] 缺少 index_store.npy，请先重建索引（02_重建索引.cmd 或启动器菜单）。
    pause
    exit /b 1
)
if not exist "%ROOT%\index_meta.npy" (
    echo [错误] 缺少 index_meta.npy，请先重建索引。
    pause
    exit /b 1
)

REM 若 8000 已在监听，不再起第二份服务，只打开网页
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo 检测到本机 8000 端口已有服务，直接打开聊天页…
    start "" "http://127.0.0.1:8000/chat-ui"
    exit /b 0
)

echo 正在后台启动网页服务（新窗口）…
start "RAG-Web" /D "%ROOT%" "%PYEXE%" -m uvicorn app:app --host 0.0.0.0 --port 8000

echo 等待服务就绪（约 3 秒）…
ping -n 4 127.0.0.1 >nul

start "" "http://127.0.0.1:8000/chat-ui"
echo.
echo 已在浏览器打开聊天页。停止服务请关闭标题为「RAG-Web」的命令行窗口。
echo.
pause

endlocal
exit /b 0
