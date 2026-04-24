@echo off
chcp 65001 >nul
title RAG启动器 - 正在打包...
cd /d "%~dp0"
echo ==========================================
echo   RAG启动器 打包脚本
echo ==========================================
echo.

REM 检查是否安装了 PyInstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [警告] 未检测到 PyInstaller，正在安装...
    pip install pyinstaller -q
)

REM 清理旧的构建文件
if exist "build" rmdir /s /q "build"
if exist "dist\RAG启动器" rmdir /s /q "dist\RAG启动器"

echo.
echo 开始打包，请稍候...
echo.

REM 执行打包
pyinstaller "RAG启动器.spec" --clean -y

echo.
if exist "dist\RAG启动器\RAG启动器.exe" (
    echo ==========================================
    echo   打包成功！
    echo   输出目录: dist\RAG启动器\
    echo ==========================================
    echo.
    echo 按任意键打开输出目录...
    pause >nul
    explorer "dist\RAG启动器"
) else (
    echo ==========================================
    echo   打包失败，请检查上方错误信息
    echo ==========================================
    echo.
    pause
)
