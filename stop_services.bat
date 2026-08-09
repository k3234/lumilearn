@echo off
chcp 65001 >nul
title LumiLearn 服务停止

echo ============================================================
echo   ⏹  LumiLearn 服务停止中...
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/2] 查找并停止 GOAI Web 服务...
for /f "tokens=2 delims=," %%i in ('tasklist /fi "imagename eq python.exe" /fo csv /nh 2^>nul ^| findstr /i "goai_web"') do (
    taskkill /f /pid %%i >nul 2>&1 && echo   ✓ 已停止 GOAI Web (PID: %%i)
)

echo [2/2] 查找并停止 Framework API 服务...
for /f "tokens=2 delims=," %%i in ('tasklist /fi "imagename eq python.exe" /fo csv /nh 2^>nul ^| findstr /i "framework.api.server"') do (
    taskkill /f /pid %%i >nul 2>&1 && echo   ✓ 已停止 Framework API (PID: %%i)
)

echo.
timeout /t 2 /nobreak >nul

:: 确认是否还有残留
set REMAINING=0
for /f "tokens=2 delims=," %%i in ('tasklist /fi "imagename eq python.exe" /fo csv /nh 2^>nul ^| findstr /i "goai_web framework"') do set REMAINING=1
if "%REMAINING%"=="0" (
    echo ✅ 所有 LumiLearn 服务已停止
) else (
    echo ⚠️  部分服务可能未完全停止，请手动检查
)

echo.
pause