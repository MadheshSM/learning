@echo off
setlocal

:: ============================================================================
:: ACC Dashboard - Uninstall Auto-Start Service
:: ============================================================================
:: Run this script AS ADMINISTRATOR to remove the auto-start scheduled task.
:: ============================================================================

title ACC Dashboard - Uninstall Auto-Start

:: Set working directory to script location
cd /d "%~dp0"

echo ============================================
echo   ACC Dashboard - Uninstall Auto-Start
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

:: Stop the server if running
echo Stopping server if running...
call "%~dp0stop.bat" <nul >nul 2>&1

:: Check if task exists
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Task "%TASK_NAME%" does not exist.
    echo Nothing to uninstall.
    echo.
    pause
    exit /b 0
)

:: Delete the scheduled task
echo Removing scheduled task "%TASK_NAME%"...
schtasks /Delete /TN "%TASK_NAME%" /F

if errorlevel 1 (
    echo.
    echo ERROR: Failed to remove scheduled task.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Auto-start removed successfully!
echo ============================================
echo.
echo The ACC Dashboard will no longer start on boot.
echo You can still start it manually with start.bat
echo.
pause
