@echo off
echo ============================================
echo MLJ Results Compiler - Installation Check
echo ============================================
echo.

:: Check Node.js
echo [1/4] Checking Node.js...
node --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Node.js is installed
    node --version
) else (
    echo [ERROR] Node.js not found!
    echo Please install from: https://nodejs.org/
    goto :end
)
echo.

:: Check npm
echo [2/4] Checking npm...
npm --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] npm is installed
    npm --version
) else (
    echo [ERROR] npm not found!
    goto :end
)
echo.

:: Check Python
echo [3/4] Checking Python...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python is installed
    python --version
) else (
    echo [ERROR] Python not found!
    echo Please ensure Python 3.x is installed
    goto :end
)
echo.

:: Check frontend directory
echo [4/4] Checking project structure...
if exist "frontend" (
    echo [OK] Frontend directory exists
    if exist "frontend\package.json" (
        echo [OK] package.json found
    ) else (
        echo [ERROR] package.json not found
        goto :end
    )
) else (
    echo [ERROR] Frontend directory not found!
    goto :end
)
echo.

:: Check Python scripts
if exist "master_automation.py" (
    echo [OK] Python automation scripts found
) else (
    echo [WARNING] master_automation.py not in current directory
)
echo.

echo ============================================
echo All checks passed! Ready to start.
echo ============================================
echo.
echo Next steps:
echo 1. cd frontend
echo 2. npm install
echo 3. npm run dev
echo 4. Open http://localhost:3000
echo.
echo Or simply run: start_frontend.bat
echo.

:end
pause
