@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
set "_ROOT=%~dp0"

call :ensure_venv
if errorlevel 1 exit /b 1

:menu
cls
echo ================================
echo   本地知识库 RAG - 启动菜单
echo ================================
echo.
echo   [1] 图形界面启动器（推荐：配密钥 / 建索引 / 开网页）
echo   [2] 启动网页聊天（需已有 .env 与索引文件）
echo   [3] 启动命令行问答（需已有 .env 与索引文件）
echo   [4] 重建知识库索引
echo   [5] 一键配置密钥（生成或编辑 .env）
echo   [0] 退出
echo.
set "_opt="
set /p "_opt=请选择 [0-5]: "

if "%_opt%"=="1" goto run_gui
if "%_opt%"=="2" goto run_web
if "%_opt%"=="3" goto run_cli
if "%_opt%"=="4" goto run_index
if "%_opt%"=="5" goto run_env
if "%_opt%"=="0" goto end

echo 无效选择，请重新输入。
pause
goto menu

:run_gui
echo.
echo 正在打开图形界面启动器……
".venv\Scripts\python.exe" launcher.py
if errorlevel 1 (
  echo 启动失败，请查看上方报错。
  pause
)
goto menu

:run_web
call "%_ROOT%03_启动网页.cmd"
goto menu

:run_cli
call "%_ROOT%04_启动命令行.cmd"
goto menu

:run_index
call "%_ROOT%02_重建索引.cmd"
goto menu

:run_env
call "%_ROOT%01_一键配置密钥.cmd"
goto menu

:end
echo 已退出。
endlocal
exit /b 0

:ensure_venv
if exist ".venv\Scripts\python.exe" goto :eof

echo 未检测到虚拟环境 .venv，正在创建并安装依赖……
python -m venv .venv
if errorlevel 1 (
  echo 创建虚拟环境失败，请确认已安装 Python 并加入 PATH。
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo 安装依赖失败，请检查网络或 pip 输出。
  pause
  exit /b 1
)
echo 虚拟环境与依赖已就绪。
pause
goto :eof
