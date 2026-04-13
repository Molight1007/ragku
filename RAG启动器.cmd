@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

:: ========================================
::  本地知识库 RAG 系统 - 一键启动器
:: ========================================

:menu
cls
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║      本地知识库 RAG 系统 - 启动器         ║
echo  ╚══════════════════════════════════════════╝
echo.

:: 检测环境状态
set "key_ok=未配置"
set "idx_ok=未构建"
set "srv_ok=未启动"
set "venv_ok=未检测"

if exist ".venv\Scripts\python.exe" set "venv_ok=已就绪"
if exist ".env" (
    findstr /C:"DASHSCOPE_API_KEY=" ".env" >nul 2>&1
    if !errorlevel! equ 0 set "key_ok=已配置"
)
if exist "index_store.npy" (
    if exist "index_meta.npy" set "idx_ok=已就绪"
)
netstat -ano | findstr ":8000 " >nul 2>&1
if !errorlevel! equ 0 set "srv_ok=运行中"

echo  当前状态：
echo  ├─ Python虚拟环境：%venv_ok%
echo  ├─ API密钥：%key_ok%
echo  ├─ 知识库索引：%idx_ok%
echo  └─ 网页服务：%srv_ok%
echo.
echo  ═══════════════════════════════════════════
echo  请选择操作：
echo  ═══════════════════════════════════════════
echo.
echo   [1] 配置/修改 API 密钥
echo   [2] 选择知识库目录
echo   [3] 重建索引（向量数据库）
echo   [4] 启动网页服务
echo   [5] 打开聊天界面（浏览器）
echo   [6] 停止网页服务
echo   [7] 一键启动（配置密钥^>重建索引^>启动服务）
echo.
echo   [G] 启动图形界面（GUI）
echo   [C] 命令行问答模式
echo   [D] 打开数据目录
echo.
echo   [0] 退出
echo.
echo  ═══════════════════════════════════════════
echo.

set /p choice=请输入选项 [0-7, G/C/D]: 

if "%choice%"=="" goto menu
if "%choice%"=="1" goto config_key
if "%choice%"=="2" goto choose_dir
if "%choice%"=="3" goto build_index
if "%choice%"=="4" goto start_server
if "%choice%"=="5" goto open_browser
if "%choice%"=="6" goto stop_server
if "%choice%"=="7" goto quick_start
if /i "%choice%"=="G" goto launch_gui
if /i "%choice%"=="C" goto launch_cli
if /i "%choice%"=="D" goto open_data
echo.
echo  无效选项，请重试。
timeout /t 1 >nul
goto menu

:: ========================================
:: 配置密钥
:: ========================================
:config_key
cls
echo.
echo  ═══════════════════════════════════════════
echo  配置 API 密钥
echo  ═══════════════════════════════════════════
echo.
echo  请到阿里云百炼平台获取 API Key:
echo  https://bailian.console.aliyun.com/
echo.
set /p api_key=请输入 DASHSCOPE_API_KEY（直接回车取消）: 

if "%api_key%"=="" (
    echo.
    echo  已取消。
    timeout /t 1 >nul
    goto menu
)

echo DASHSCOPE_API_KEY=%api_key% > ".env"
echo.
echo  ✓ 密钥已保存到 .env
echo.
pause
goto menu

:: ========================================
:: 选择知识库目录
:: ========================================
:choose_dir
cls
echo.
echo  ═══════════════════════════════════════════
echo  选择知识库目录
echo  ═══════════════════════════════════════════
echo.
echo  当前知识库目录保存在 config.py 中
echo.
echo  请确保目录包含要索引的文档（docx/txt/pdf）
echo.
powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $f = New-Object System.Windows.Forms.FolderBrowserDialog; $f.Description = '选择知识库目录'; $f.ShowNewFolderButton = $false; if($f.ShowDialog() -eq 'OK') { Write-Host \"SELECTED:$($f.SelectedPath)\" }"
echo.
pause
goto menu

:: ========================================
:: 重建索引
:: ========================================
:build_index
cls
echo.
echo  ═══════════════════════════════════════════
echo  重建知识库索引
echo  ═══════════════════════════════════════════
echo.

if not exist ".venv\Scripts\python.exe" (
    echo  未检测到虚拟环境，正在创建...
    python -m venv .venv
    if errorlevel 1 (
        echo  创建虚拟环境失败，请确认已安装 Python。
        pause
        goto menu
    )
    echo  安装依赖...
    .venv\Scripts\python -m pip install -r requirements.txt -q
)

if not exist ".env" (
    echo  错误：请先配置 API 密钥！
    echo.
    pause
    goto config_key
)

echo  开始构建索引（这可能需要几分钟到几十分钟）...
echo  请耐心等待，不要关闭此窗口...
echo.

.venv\Scripts\python ingest.py

echo.
if exist "index_store.npy" (
    echo  ✓ 索引构建完成！
) else (
    echo  ✗ 索引构建失败，请检查错误信息。
)
echo.
pause
goto menu

:: ========================================
:: 启动网页服务
:: ========================================
:start_server
cls
echo.
echo  ═══════════════════════════════════════════
echo  启动网页服务
echo  ═══════════════════════════════════════════
echo.

if not exist ".venv\Scripts\python.exe" (
    echo  未检测到虚拟环境，正在创建...
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt -q
)

if not exist ".env" (
    echo  错误：请先配置 API 密钥！
    pause
    goto config_key
)

if not exist "index_store.npy" (
    echo  错误：请先重建索引！
    pause
    goto build_index
)

netstat -ano | findstr ":8000 " >nul 2>&1
if !errorlevel! equ 0 (
    echo  端口 8000 已被占用！
    echo  如果服务已在运行，请直接打开浏览器访问。
    echo.
    echo  聊天界面: http://127.0.0.1:8000/chat-ui
    echo  API文档:  http://127.0.0.1:8000/docs
    pause
    goto menu
)

echo  正在启动服务...
echo.
echo  服务启动后请访问:
echo  ┌─────────────────────────────────────────┐
echo  │  聊天界面: http://127.0.0.1:8000/chat-ui│
echo  │  API文档:  http://127.0.0.1:8000/docs  │
echo  └─────────────────────────────────────────┘
echo.
echo  按 Ctrl+C 可停止服务
echo.
echo  启动中...

.venv\Scripts\uvicorn app:app --host 0.0.0.0 --port 8000 --limit-max-bytes 107374182400 --timeout-keep-alive 300

echo.
echo  服务已停止。
pause
goto menu

:: ========================================
:: 打开浏览器
:: ========================================
:open_browser
start http://127.0.0.1:8000/chat-ui
echo  已打开聊天界面
timeout /t 1 >nul
goto menu

:: ========================================
:: 停止服务
:: ========================================
:stop_server
cls
echo.
echo  ═══════════════════════════════════════════
echo  停止网页服务
echo  ═══════════════════════════════════════════
echo.

netstat -ano | findstr ":8000 " >nul 2>&1
if not !errorlevel! equ 0 (
    echo  服务未在运行。
    pause
    goto menu
)

echo  正在停止服务...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo  ✓ 服务已停止
pause
goto menu

:: ========================================
:: 一键启动（完整流程）
:: ========================================
:quick_start
cls
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║       一键启动（配置密钥^>索引^>服务）      ║
echo  ╚══════════════════════════════════════════╝
echo.

:: 步骤1：检查/配置密钥
if not exist ".env" (
    echo  [步骤 1/3] 配置 API 密钥
    echo  请到阿里云百炼平台获取 API Key:
    echo  https://bailian.console.aliyun.com/
    echo.
    set /p api_key=请输入 DASHSCOPE_API_KEY: 
    if "%api_key%"=="" (
        echo  已取消。
        pause
        goto menu
    )
    echo DASHSCOPE_API_KEY=%api_key% > ".env"
)

:: 步骤2：检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo  [步骤 2/3] 创建虚拟环境...
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt -q
)

:: 步骤3：检查索引
if not exist "index_store.npy" (
    echo  [步骤 3/3] 重建索引（首次可能需要较长时间）...
    echo.
    .venv\Scripts\python ingest.py
    echo.
) else (
    echo  [步骤 3/3] 索引已存在，跳过构建
)

:: 启动服务
echo.
echo  ═══════════════════════════════════════════
echo  启动网页服务...
echo  ═══════════════════════════════════════════
echo.
echo  请访问: http://127.0.0.1:8000/chat-ui
echo.
echo  按 Ctrl+C 可停止服务
echo.

.venv\Scripts\uvicorn app:app --host 0.0.0.0 --port 8000 --limit-max-bytes 107374182400 --timeout-keep-alive 300

pause
goto menu

:: ========================================
:: 启动 GUI 界面
:: ========================================
:launch_gui
cls
echo  启动图形界面...
echo.

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt -q
)

.venv\Scripts\python launcher.py

goto menu

:: ========================================
:: 命令行问答模式
:: ========================================
:launch_cli
cls
echo.
echo  ═══════════════════════════════════════════
echo  命令行问答模式
echo  ═══════════════════════════════════════════
echo.
echo  输入问题后按回车，空格回车退出
echo.

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt -q
)

.venv\Scripts\python main.py

echo.
pause
goto menu

:: ========================================
:: 打开数据目录
:: ========================================
:open_data
start explorer "%~dp0"
goto menu

:: ========================================
:: 退出
:: ========================================
:exit
endlocal
exit /b 0
