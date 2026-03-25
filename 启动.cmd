@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
cd /d "%~dp0"
set "ROOT=%CD%"
set "LAUNCH=%ROOT%\launcher.py"

if not exist "%LAUNCH%" (
    echo [错误] 未找到 launcher.py，请将此脚本放在项目根目录。
    pause
    exit /b 1
)

set "PYEXE="
set "PYWEXE="
if exist "%ROOT%\.venv\Scripts\python.exe" set "PYEXE=%ROOT%\.venv\Scripts\python.exe"
if exist "%ROOT%\.venv\Scripts\pythonw.exe" set "PYWEXE=%ROOT%\.venv\Scripts\pythonw.exe"
if not defined PYEXE (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未找到 Python，且不存在 .venv\Scripts\python.exe
        echo 请先安装 Python，或在本目录执行: python -m venv .venv
        pause
        exit /b 1
    )
    set "PYEXE=python"
)

:menu
cls
echo ========================================
echo   本地知识库 RAG - 启动器
echo ========================================
if defined PYWEXE (
    echo   当前 Python: .venv ^(推荐^)
) else (
    echo   当前 Python: %PYEXE%
)
echo   工作目录: %ROOT%
echo ----------------------------------------
echo   [1] 图形界面启动器 ^(Tk^)
echo   [2] 控制台菜单 ^(配置密钥 / 索引 / 启停服务^)
echo   [3] 启动网页服务 ^(本窗口运行 uvicorn，Ctrl+C 停止^)
echo   [4] 浏览器打开聊天页 ^(需服务已在运行^)
echo   [0] 退出
echo ========================================
set "CHOICE="
set /p "CHOICE=请选择 [0-4]: "

if "%CHOICE%"=="1" goto opt_gui
if "%CHOICE%"=="2" goto opt_console
if "%CHOICE%"=="3" goto opt_web
if "%CHOICE%"=="4" goto opt_browser
if "%CHOICE%"=="0" goto opt_exit

echo.
echo 无效选择，请重新输入。
timeout /t 2 >nul
goto menu

:opt_gui
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "RAG图形启动器" /D "%ROOT%" py -3w "%LAUNCH%"
    goto menu_end
)
if defined PYWEXE (
    start "RAG图形启动器" /D "%ROOT%" "%PYWEXE%" "%LAUNCH%"
    goto menu_end
)
echo 未找到 py / pythonw，将用 python 打开（可能短暂出现黑框）。
start "RAG图形启动器" /D "%ROOT%" "%PYEXE%" "%LAUNCH%"
goto menu_end

:opt_console
echo.
"%PYEXE%" "%LAUNCH%" --console
goto menu_end

:opt_web
if not exist "%ROOT%\.env" (
    echo.
    echo [提示] 缺少 .env。请先选 [2] 配置密钥，或运行 01_一键配置密钥.cmd
    pause
    goto menu
)
if not exist "%ROOT%\index_store.npy" goto opt_web_noindex
if not exist "%ROOT%\index_meta.npy" goto opt_web_noindex
goto opt_web_run

:opt_web_noindex
echo.
echo [提示] 缺少索引文件。请先选 [2] 重建索引，或运行 02_重建索引.cmd
echo 也可运行 03_启动网页.cmd，会自动创建 .venv 并安装依赖（若尚未创建）。
pause
goto menu

:opt_web_run
echo.
echo 聊天界面: http://127.0.0.1:8000/chat-ui
echo 按 Ctrl+C 停止服务。
echo.
cd /d "%ROOT%"
"%PYEXE%" -m uvicorn app:app --host 0.0.0.0 --port 8000
echo.
pause
goto menu

:opt_browser
start "" "http://127.0.0.1:8000/chat-ui"
goto menu_end

:menu_end
goto menu

:opt_exit
echo.
echo 已退出。
endlocal
exit /b 0
