@echo off
chcp 65001 >nul 2>&1
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 python，请先安装 Python 并加入 PATH。
    goto :end
)

echo 正在启动控制台菜单……
python launcher.py --console

:end
echo.
pause
endlocal
