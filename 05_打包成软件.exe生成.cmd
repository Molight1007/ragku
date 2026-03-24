@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo ================================
echo  本地RAG系统 - 打包生成 EXE
echo ================================
echo.
echo 说明：
echo - 会在 dist\ 下生成：RAG启动器.exe
echo - 首次打包可能需要安装依赖/耗时较长
echo - 打包后会在 dist\ 下生成可直接运行的 EXE
echo - 建议将 .env 与索引文件放在 EXE 同目录（软件会自动读取）
echo.

if not exist ".venv\Scripts\python.exe" (
  echo 未检测到虚拟环境 .venv，正在创建并安装依赖...
  python -m venv .venv
  if errorlevel 1 (
    echo 创建虚拟环境失败，请确认已安装 Python。
    pause
    exit /b 1
  )
  .venv\Scripts\python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo 安装依赖失败，请检查网络或 pip 输出。
    pause
    exit /b 1
  )
)

echo 正在检查打包工具 PyInstaller...
.venv\Scripts\python -m pip show pyinstaller >nul 2>nul
if errorlevel 1 (
  echo 未检测到 PyInstaller，正在安装...
  .venv\Scripts\python -m pip install pyinstaller
  if errorlevel 1 (
    echo 安装 PyInstaller 失败，请检查网络或 pip 输出。
    pause
    exit /b 1
  )
)

echo 开始打包...
.venv\Scripts\python -m PyInstaller --noconfirm --clean --name "RAG启动器" --onefile --windowed launcher.py
if errorlevel 1 (
  echo.
  echo 打包失败，请滚动查看上方报错信息。
  echo.
  pause
  exit /b 1
)

echo.
echo 正在把 .env（若存在）复制到 dist\ 目录...
if exist "dist\" (
  if exist ".env" (
    copy /Y ".env" "dist\.env" >nul
  )
)

echo.
echo 打包完成后，请到 dist\RAG启动器.exe 运行。
echo.
pause

