@echo off
chcp 65001 >nul
title LumiLearn 部署配置引导

:: 切换到仓库根目录（脚本所在目录的上一级）
cd /d "%~dp0.."

:: 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.9+ 并加入 PATH
    pause
    exit /b 1
)

python deploy/setup.py %*
exit /b %errorlevel%
