@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo ================================
echo  本地RAG系统 - 一键配置密钥
echo ================================
echo.
echo 说明：
echo - 本操作会在当前目录生成 .env 文件
echo - .env 仅用于本机运行，请勿分享/上传/提交
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$key = Read-Host '请输入阿里云 DASHSCOPE_API_KEY（以 sk- 开头）';" ^
  "if ([string]::IsNullOrWhiteSpace($key)) { Write-Host '密钥为空，已取消。'; exit 1 };" ^
  "$content = \"DASHSCOPE_API_KEY=$key`n\";" ^
  "[System.IO.File]::WriteAllText((Join-Path (Get-Location) '.env'), $content, (New-Object System.Text.UTF8Encoding($false)));" ^
  "Write-Host '已写入 .env（UTF-8）。';"

echo.
echo 完成。你可以继续双击：02_重建索引.cmd 或 03_启动网页.cmd
echo.
pause

