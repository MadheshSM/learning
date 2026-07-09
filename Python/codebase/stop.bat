@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: ACC Dashboard - Stop Script
:: ============================================================================
:: Double-click this file to stop the server.
:: ============================================================================

title ACC Dashboard Server - Stopping

:: Set working directory to script location
cd /d "%~dp0"

echo ============================================
echo   ACC Dashboard Server - Stopping
echo ============================================
echo.

set "STOPPED=0"

:: Try to stop using PID file first
if exist "server.pid" (
    set /p PID=<server.pid
    echo Found PID file: server.pid ^(PID: !PID!^)

    :: Check if process exists
    tasklist /FI "PID eq !PID!" 2>nul | find /i "python" >nul
    if not errorlevel 1 (
        echo Stopping process !PID!...
        taskkill /PID !PID! /F >nul 2>&1
        if not errorlevel 1 (
            echo Process !PID! stopped successfully.
            set "STOPPED=1"
        ) else (
            echo WARNING: Failed to stop process !PID!
        )
    ) else (
        echo Process !PID! is not running ^(stale PID file^)
    )

    del server.pid
    echo PID file removed.
) else (
    echo No server.pid file found.
)

:: Fallback: find and kill any Python process on port 8080
echo.
echo Checking for processes on port 8080...

for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":8080" ^| findstr "LISTENING"') do (
    set "PORT_PID=%%p"
    if not "!PORT_PID!"=="" (
        echo Found process !PORT_PID! listening on port 8080
        taskkill /PID !PORT_PID! /F >nul 2>&1
        if not errorlevel 1 (
            echo Process !PORT_PID! stopped.
            set "STOPPED=1"
        ) else (
            echo WARNING: Could not stop process !PORT_PID! ^(may need Administrator^)
        )
    )
)

echo.
if "!STOPPED!"=="1" (
    echo ============================================
    echo   Server stopped successfully.
    echo ============================================
) else (
    echo ============================================
    echo   No running server was found.
    echo ============================================
)

echo.
echo Press any key to close...
pause >nul
