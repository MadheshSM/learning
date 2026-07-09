@echo off
setlocal

:: ============================================================================
:: ACC Dashboard - Install Auto-Start Service
:: ============================================================================
:: Run this script AS ADMINISTRATOR to create a Windows Task Scheduler task
:: that automatically starts the ACC Dashboard when the machine boots.
:: ============================================================================

title ACC Dashboard - Install Auto-Start

:: Set working directory to script location
cd /d "%~dp0"

echo ============================================
echo   ACC Dashboard - Install Auto-Start
echo ============================================
echo.

:: Check for Administrator privileges
net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: This script must be run as Administrator.
    echo.
    echo Right-click this file and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

set "TASK_NAME=ACC-Dashboard"
set "PROJECT_DIR=%~dp0"
set "VBS_PATH=%~dp0service.vbs"

echo Task Name:    %TASK_NAME%
echo Project Dir:  %PROJECT_DIR%
echo VBS Path:     %VBS_PATH%
echo.

:: Check that service.vbs exists
if not exist "%VBS_PATH%" (
    echo ERROR: service.vbs not found at %VBS_PATH%
    echo Make sure service.vbs is in the same directory as this script.
    pause
    exit /b 1
)

:: Remove existing task if present
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if not errorlevel 1 (
    echo Removing existing task "%TASK_NAME%"...
    schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
)

:: Create the scheduled task
:: - Triggers on system startup (ONSTART)
:: - 30-second delay to allow network to initialize
:: - Runs as the current user
echo Creating scheduled task "%TASK_NAME%"...

schtasks /Create ^
    /TN "%TASK_NAME%" ^
    /TR "wscript.exe \"%VBS_PATH%\"" ^
    /SC ONSTART ^
    /DELAY 0000:30 ^
    /RL HIGHEST ^
    /F

if errorlevel 1 (
    echo.
    echo ERROR: Failed to create scheduled task.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Auto-start installed successfully!
echo ============================================
echo.
echo The ACC Dashboard will now start automatically
echo when this machine boots up (with a 30-second delay).
echo.
echo To test: restart your machine and check
echo   http://localhost:8080/api/health
echo.
echo To remove: run uninstall-service.bat as Administrator
echo.
pause
