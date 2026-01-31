@echo off
REM Windows Batch Script for Test Results Collation Automation
REM Run this script monthly to automate result processing

setlocal enabledelayedexpansion

REM Configuration
set SCRIPT_DIR=%~dp0
set PYTHON_EXE=python
set MONTH_YEAR=%1
set INPUT_DIR=%2
set OUTPUT_DIR=%3

REM Default values
if "%MONTH_YEAR%"=="" (
    REM Auto-generate month/year (JAN, FEB, etc.)
    for /f "tokens=1-2" %%a in ('powershell -Command "Get-Date -Format 'MMMM,yyyy'"') do (
        set MONTH=%%a
        set YEAR=%%b
    )
    set MONTH_YEAR=!MONTH:~0,3!_!YEAR!
)

if "%INPUT_DIR%"=="" (
    set INPUT_DIR=.\input
)

if "%OUTPUT_DIR%"=="" (
    set OUTPUT_DIR=.\output
)

echo.
echo ====================================================================
echo Test Results Collation Automation - Windows Batch Runner
echo ====================================================================
echo.
echo Configuration:
echo   Script Directory: %SCRIPT_DIR%
echo   Input Directory: %INPUT_DIR%
echo   Output Directory: %OUTPUT_DIR%
echo   Month/Year: %MONTH_YEAR%
echo.

REM Check if Python is installed
%PYTHON_EXE% --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://www.python.org
    pause
    exit /b 1
)

REM Check if required directories exist
if not exist "%INPUT_DIR%" (
    echo ERROR: Input directory not found: %INPUT_DIR%
    echo Please create the directory and add test Excel files.
    pause
    exit /b 1
)

REM Check Python packages
echo Checking required Python packages...
%PYTHON_EXE% -c "import pandas, openpyxl" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Installing required packages...
    %PYTHON_EXE% -m pip install --upgrade pandas openpyxl --break-system-packages
    if errorlevel 1 (
        echo ERROR: Failed to install packages
        pause
        exit /b 1
    )
)

REM Create output directory if needed
if not exist "%OUTPUT_DIR%" (
    mkdir "%OUTPUT_DIR%"
)

REM Run the master automation script
echo.
echo Starting collation process...
echo.

%PYTHON_EXE% "%SCRIPT_DIR%master_automation.py" "%INPUT_DIR%" "%OUTPUT_DIR%" "%MONTH_YEAR%"

if errorlevel 1 (
    echo.
    echo ERROR: Process failed. Check the log files in %OUTPUT_DIR%
    pause
    exit /b 1
) else (
    echo.
    echo SUCCESS: Collation process completed!
    echo Results saved to: %OUTPUT_DIR%
    echo.
    pause
)

endlocal
