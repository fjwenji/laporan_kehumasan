@echo off
REM ===========================================
REM Mayz Monitoring - Run All Script
REM ===========================================

echo.
echo ============================================
echo   MAYZ MONITORING - Starting Services
echo ============================================
echo.

REM Check if we're in the correct directory
if not exist "backend" (
    echo ERROR: Please run this script from the project root directory
    pause
    exit /b 1
)

REM Check if MySQL is accessible
echo [1/3] Checking database connection...
python -c "import mysql.connector; c = mysql.connector.connect(host='localhost', user='root', password=''); print('Database OK')" 2>nul
if errorlevel 1 (
    echo WARNING: Could not connect to MySQL. Make sure XAMPP/MySQL is running.
    echo.
)

REM Start Backend
echo.
echo [2/3] Starting Backend API (FastAPI)...
echo    Backend will run at: http://localhost:8000
echo.
start "Mayz Backend" cmd /k "cd backend && python run.py"

timeout /t 3 /nobreak >nul

REM Start Frontend
echo.
echo [3/3] Starting Frontend (React)...
echo    Frontend will run at: http://localhost:5173
echo.
start "Mayz Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================
echo   All services starting...
echo ============================================
echo.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo.
echo   Login: admin / admin123
echo.
echo   Press any key to open browser...
pause >nul

start http://localhost:5173
