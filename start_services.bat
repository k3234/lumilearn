@echo off
chcp 65001 >nul
title LumiLearn 服务管理器

echo ============================================================
echo   🚀 LumiLearn 服务启动中...
echo ============================================================
echo.
echo   🏠 统一门户:  http://localhost:18080
echo   👨‍🏫 教师门户:  http://localhost:5001
echo   📚 学生门户:  http://localhost:5010
echo   📊 分析仪表盘: http://localhost:18090
echo   🔧 管理面板:   http://localhost:18080/admin
echo.

cd /d "%~dp0"

:: 检查Python
echo [1/2] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ❌ Python 未安装或不在 PATH 中
    pause
    exit /b 1
)
echo   ✓ Python 就绪
echo.

:: 调用统一启动脚本（端口与 Ollama 地址均从 config/framework.yaml 与 .env 读取）
echo [2/2] 启动服务...
python deploy/start.py %*
if errorlevel 1 (
    echo.
    echo   ❌ 服务启动失败，请查看上方错误信息
    pause
    exit /b 1
)

echo.
pause
