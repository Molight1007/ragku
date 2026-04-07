@echo off
setlocal EnableExtensions

rem Use UTF-8 code page for readable output
chcp 65001 >nul 2>&1

cd /d "%~dp0"
set "ROOT=%CD%"
set "SPEC=%ROOT%\RAG启动器.spec"
set "EXE=%ROOT%\dist\RAG启动器.exe"

echo ========================================
echo RAG launcher build script
echo ROOT: %ROOT%
echo ========================================

if not exist "%SPEC%" (
  echo [ERROR] spec file not found: %SPEC%
  pause
  exit /b 1
)

echo [1/4] kill old process if exists...
taskkill /F /IM "RAG启动器.exe" >nul 2>&1

echo [2/4] check pyinstaller...
where pyinstaller >nul 2>&1
if errorlevel 1 (
  echo pyinstaller not found, installing...
  where py >nul 2>&1
  if errorlevel 1 (
    python -m pip install -U pyinstaller
  ) else (
    py -m pip install -U pyinstaller
  )
)

echo [3/4] build exe (keep build/dist, no clean)...
where py >nul 2>&1
if errorlevel 1 (
  python -m PyInstaller "%SPEC%"
) else (
  py -m PyInstaller "%SPEC%"
)
if errorlevel 1 (
  echo [FAIL] build failed, see logs above.
  pause
  exit /b 1
)

echo [4/4] verify output...
if exist "%EXE%" (
  echo [OK] EXE created: %EXE%
  echo You can double-click it now.
) else (
  echo [FAIL] EXE not found: %EXE%
  pause
  exit /b 1
)

echo done.
pause
exit /b 0
