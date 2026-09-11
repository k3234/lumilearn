@echo off
chcp 65001 >nul
REM ============================================================
REM LumiLearn 一键启动（统一入口）
REM 启动全部服务，浏览器自动打开统一门户 http://localhost:18080
REM
REM 用法：
REM   start.bat              启动全部服务并打开浏览器
REM   start.bat --dry-run    仅打印服务列表，不启动
REM   start.bat --no-open    启动但不打开浏览器
REM ============================================================

title LumiLearn 服务管理器

echo.
echo ============================================================
echo   🚀 LumiLearn 一键启动
echo ============================================================
echo.
echo   🏠 统一门户:  http://localhost:18080
echo   👨‍🏫 教师门户:  http://localhost:5001
echo   📚 学生门户:  http://localhost:5010
echo   📊 分析仪表盘: http://localhost:18090
echo   🔧 管理面板:   http://localhost:18080/admin
echo.
echo   ⏹  停止服务:   double-click stop_services.bat
echo ============================================================
echo.

cd /d "%~dp0"

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo   ❌ Python 未安装或不在 PATH 中
    pause
    exit /b 1
)

:: 启动全部服务（端口与 Ollama 地址从 config/framework.yaml 读取）
python deploy/start.py %*
if errorlevel 1 (
    echo.
    echo   ❌ 服务启动失败，请查看上方错误信息
    pause
    exit /b 1
)

echo.
pause