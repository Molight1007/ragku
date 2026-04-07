@echo off

setlocal EnableExtensions EnableDelayedExpansion

chcp 65001 >nul 2>&1

cd /d "%~dp0"

set "ROOT=%CD%"

set "SPEC=%ROOT%\RAG启动器.spec"

set "EXE=%ROOT%\dist\RAG启动器.exe"



echo ========================================

echo  RAG 启动器打包脚本

echo  目录: %ROOT%

echo ========================================



if not exist "%SPEC%" (

  echo [错误] 未找到 RAG启动器.spec

  pause

  exit /b 1

)



echo [1/5] 检查是否有旧进程占用 EXE...

taskkill /F /IM "RAG启动器.exe" >nul 2>&1



echo [2/5] 保留 build/ 与 dist/（按你的要求不清理）...

echo [3/5] 检查 PyInstaller...

where pyinstaller >nul 2>&1

if %ERRORLEVEL% neq 0 (

  echo 未检测到 pyinstaller，尝试自动安装...

  where py >nul 2>&1

  if %ERRORLEVEL% equ 0 (

    py -m pip install -U pyinstaller

  ) else (

    python -m pip install -U pyinstaller

  )

)



echo [4/5] 开始打包...

where py >nul 2>&1

if %ERRORLEVEL% equ 0 (

  py -m PyInstaller "%SPEC%"

) else (

  python -m PyInstaller "%SPEC%"

)



if %ERRORLEVEL% neq 0 (

  echo.

  echo [失败] 打包命令执行失败，请查看上方日志。

  pause

  exit /b 1

)



echo [5/5] 校验输出...

if exist "%EXE%" (

  echo.

  echo [成功] 已生成: %EXE%

  echo 你可以直接双击运行，或在命令行测试：

  echo   "%EXE%"

) else (

  echo.

  echo [失败] 未找到输出 EXE: %EXE%

  echo 请检查 spec 的 name 配置是否为「RAG启动器」。

  pause

  exit /b 1

)



echo.

echo 完成。

pause

exit /b 0

