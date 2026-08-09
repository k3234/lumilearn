@echo off
chcp 65001 >nul
title LumiLearn 服务管理器

echo ============================================================
echo   🚀 LumiLearn 服务启动中...
echo ============================================================
echo.

cd /d "%~dp0"

:: 清理旧进程
echo [1/4] 清理旧进程...
for /f "tokens=2 delims=," %%i in ('tasklist /fi "imagename eq python.exe" /fo csv /nh 2^>nul ^| findstr /i "goai_web framework.api.server"') do (
    taskkill /f /pid %%i >nul 2>&1
)
timeout /t 2 /nobreak >nul
echo   ✓ 旧进程已清理
echo.

:: 检查Python
echo [2/4] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ❌ Python 未安装或不在 PATH 中
    pause
    exit /b 1
)
echo   ✓ Python 就绪
echo.

:: 启动 GOAI Web (端口5000)
echo [3/4] 启动 GOAI Web 服务 (端口 5000)...
start "LumiLearn GOAI Web" /min cmd /c "python goai_web.py"
timeout /t 3 /nobreak >nul
echo   ✓ GOAI Web 已启动
echo.

:: 启动 Framework API (端口18080/18081/18082)
echo [4/4] 启动 Framework API 服务 (端口 18080-18082)...
start "LumiLearn Framework API" /min cmd /c "python -m framework.api.server --multi-port"
timeout /t 5 /nobreak >nul
echo   ✓ Framework API 已启动
echo.

:: 显示服务信息
echo ============================================================
echo   ✅ 所有服务已启动！
echo ============================================================
echo.
echo   📌 服务访问地址
echo   ─────────────────────────────────────────
echo   🎓 GOAI 学习 Web     http://localhost:5000
echo   🖥️ 框架终端          http://localhost:18080
echo   🔌 REST API          http://localhost:18081
echo   🤖 模型管理          http://localhost:18082
echo   ─────────────────────────────────────────
echo.
echo   🌐 局域网访问 (本机IP: 192.168.2.xx)
echo      http://192.168.2.xx:5000
echo      http://192.168.2.xx:18080
echo.
echo   📋 状态检查
echo      curl http://localhost:5000/api/status
echo      curl http://localhost:18080/api/status
echo.
echo   ⏹  停止服务请运行: stop_services.bat
echo.
echo ============================================================

:: 打开浏览器
timeout /t 2 /nobreak >nul
start http://localhost:5000