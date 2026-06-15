@echo off
chcp 65001 >nul
REM ============================================================
REM LumiLearn Framework - Windows 启动脚本（华硕主机）
REM 启动三端口服务：终端HTML / REST API / 模型管理
REM
REM 用法：
REM   start.bat             以三端口模式启动
REM   start.bat --debug      调试模式启动
REM   start.bat --port 8080  单端口模式启动
REM
REM 作者：lumilearn AI自动化专家
REM 版本：1.0.0
REM 日期：2026-06-02
REM ============================================================

title LumiLearn Framework Server

echo.
echo ============================================================
echo   🚀 LumiLearn Framework 启动中...
echo ============================================================
echo.
echo   📡 终端HTML:   http://192.168.2.xx:18080
echo   🔌 REST API:   http://192.168.2.xx:18081
echo   🤖 模型管理:   http://192.168.2.xx:18082
echo.
echo   💻 健康检查:   http://192.168.2.xx:18080/health
echo   📊 API状态:    http://192.168.2.xx:18080/api/status
echo.
echo   本机访问:      http://localhost:18080
echo ============================================================
echo.

REM 切换到项目根目录
cd /d "%~dp0"

REM 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Python 未安装或未添加到 PATH
    echo 请安装 Python 3.9+ 后重试
    pause
    exit /b 1
)

REM 检查必要的依赖
python -c "import flask, requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 缺少依赖，正在安装...
    pip install flask requests -q
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败，请手动运行: pip install -r requirements.txt
        pause
        exit /b 1
    )
)

echo [启动] LumiLearn Framework Server
echo.

REM 解析命令行参数
set ARGS=%*
if "%ARGS%"=="" (
    set ARGS=--multi-port
)

python -m framework.api.server %ARGS%

REM 如果Python进程退出
echo.
echo ============================================================
echo   LumiLearn Framework 已停止
echo ============================================================
pause