@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
cd /d "%~dp0"
set "ROOT=%CD%"
set "LAUNCH=%ROOT%\launcher.py"

if not exist "%LAUNCH%" (
    echo 未找到 launcher.py，请与本 bat 放在同一目录。
    pause
    exit /b 1
)

REM 1) py -3w：官方 Python 启动器的无控制台模式，通常比裸 pythonw 更可靠
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "RAG启动器" /D "%ROOT%" py -3w "%LAUNCH%"
    exit /b 0
)

where python >nul 2>&1
if not %ERRORLEVEL% equ 0 (
    echo 未找到 Python。请从 https://www.python.org 安装，并勾选 Add python.exe to PATH。
    echo 若已安装但仍提示本行，请检查 PATH 或改用「应用和功能」修复 Python。
    pause
    exit /b 1
)

REM 2) 同目录下的 pythonw（当前 PATH）
where pythonw >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "RAG启动器" /D "%ROOT%" pythonw "%LAUNCH%"
    exit /b 0
)

REM 3) 退回 python.exe（会短暂出现控制台窗口，便于看到报错）
start "RAG启动器" /D "%ROOT%" python "%LAUNCH%"
exit /b 0
