@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: ACC Dashboard - Start Script
:: ============================================================================
:: Double-click this file to start the server manually.
:: Logs are written to logs\server.log
:: ============================================================================

title ACC Dashboard Server

:: Set working directory to script location
cd /d "%~dp0"

echo ============================================
echo   ACC Dashboard Server - Starting
echo ============================================
echo.

:: Create logs directory if missing
if not exist "logs" mkdir logs

:: Load .env file if it exists
if exist ".env" (
    echo Loading .env configuration...
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        set "line=%%a"
        :: Skip comments and blank lines
        if not "!line:~0,1!"=="#" (
            if not "%%a"=="" (
                set "%%a=%%b"
            )
        )
    )
) else (
    echo WARNING: .env file not found, using defaults
)

:: Set defaults if not defined
if not defined PORT set PORT=8080

echo Working directory: %cd%
echo Port: %PORT%
echo.

:: Check if server is already running
if exist "server.pid" (
    set /p OLD_PID=<server.pid
    tasklist /FI "PID eq !OLD_PID!" 2>nul | find /i "python" >nul
    if not errorlevel 1 (
        echo Server is already running with PID !OLD_PID!
        echo Use stop.bat to stop it first.
        pause
        exit /b 1
    ) else (
        echo Cleaning up stale PID file...
        del server.pid
    )
)

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo Using system Python...
)

:: Verify Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    pause
    exit /b 1
)

echo Starting server...
echo Log file: logs\server.log
echo.

:: Start Python and capture PID using PowerShell
for /f %%p in ('powershell -Command "(Start-Process -FilePath 'python' -ArgumentList 'main.py' -RedirectStandardOutput 'logs\server_stdout.log' -RedirectStandardError 'logs\server_stderr.log' -WindowStyle Hidden -PassThru).Id"') do (
    set "PID=%%p"
)

if defined PID (
    echo %PID%> server.pid
    echo Server started with PID: %PID%
    echo PID saved to server.pid
) else (
    echo ERROR: Failed to start server
    echo Check logs\server_stderr.log for errors
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Server should be running at:
echo   http://localhost:%PORT%
echo   Health: http://localhost:%PORT%/api/health
echo ============================================
echo.
echo Press any key to close this window (server continues running)...
pause >nul
