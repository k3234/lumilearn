@echo off
chcp 65001 >nul
title LumiLearn 服务停止

echo ============================================================
echo   ⏹  LumiLearn 服务停止中...
echo ============================================================
echo.

cd /d "%~dp0"

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo   ❌ Python 未安装或不在 PATH 中
    pause
    exit /b 1
)

:: 调用统一停止脚本
python deploy/stop.py %*

echo.
pause
