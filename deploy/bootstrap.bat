@echo off
rem ============================================================
rem LumiLearn One-Click Deploy Bootstrap (Windows entry)
rem Delegates all logic to bootstrap.ps1 (UTF-8, Chinese UI).
rem
rem Usage:
rem   bootstrap.bat                Full deploy (clone/update -> configure -> start)
rem   bootstrap.bat --quick        Non-interactive, all defaults
rem   bootstrap.bat --skip-deps    Skip dependency installation
rem   bootstrap.bat --no-start     Only clone+configure, do not start services
rem   bootstrap.bat --dir D:\proj  Clone into a specific directory
rem   bootstrap.bat --branch dev   Use a specific branch (default master)
rem ============================================================
setlocal
set "PS1=%~dp0bootstrap.ps1"
if not exist "%PS1%" (
    echo [ERROR] bootstrap.ps1 not found next to this script.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" (
    echo.
    echo [ERROR] LumiLearn bootstrap failed with code %CODE%.
    pause
    exit /b %CODE%
)
