@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo ================================
echo  本地RAG系统 - 启动命令行问答
echo ================================
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

if not exist ".env" (
  echo 未找到 .env（密钥配置）。请先双击运行：01_一键配置密钥.cmd
  echo.
  pause
  exit /b 1
)

if not exist "index_store.npy" (
  echo 未找到 index_store.npy（索引）。请先双击运行：02_重建索引.cmd
  echo.
  pause
  exit /b 1
)

if not exist "index_meta.npy" (
  echo 未找到 index_meta.npy（索引）。请先双击运行：02_重建索引.cmd
  echo.
  pause
  exit /b 1
)

.venv\Scripts\python main.py

echo.
pause

