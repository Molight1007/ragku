@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo ================================
echo  本地RAG系统 - 重建知识库索引
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

echo 开始构建索引（这一步可能需要较长时间，请耐心等待）...
echo 知识库目录：D:\知识库资料20
echo.

.venv\Scripts\python ingest.py --data_dir "D:\知识库资料20"

echo.
echo 如果看到“索引构建完成。”并且生成 index_store.npy / index_meta.npy，则成功。
echo.
pause

