@echo off
REM ===========================================
REM Mayz Scheduler - Cron Job Sync Script
REM ===========================================
REM
REM This script syncs the scheduler settings from database to Windows Task Scheduler.
REM Run this periodically or manually to sync schedules.
REM
REM Usage:
REM   run_scheduler.bat           - Check and sync scheduler
REM   run_scheduler.bat --force  - Force sync all schedules
REM

echo.
echo ============================================
echo   MAYZ SCHEDULER SYNC
echo ============================================
echo.

REM Check if we're in the correct directory
if not exist "backend" (
    echo ERROR: Please run this script from the project root directory
    pause
    exit /b 1
)

REM Check if virtualenv exists
if not exist ".venv\Scripts\python.exe" (
    echo WARNING: Virtual environment not found at .venv\Scripts\python.exe
    echo Using system Python...
    set PYTHON_EXE=python
) else (
    set PYTHON_EXE=.venv\Scripts\python.exe
)

REM Check MySQL connection
echo [1/2] Checking database connection...
"%PYTHON_EXE%" -c "import mysql.connector; c = mysql.connector.connect(host='localhost', user='root', password=''); print('Database OK')" 2>nul
if errorlevel 1 (
    echo ERROR: Could not connect to MySQL.
    pause
    exit /b 1
)

echo [OK] Database connected
echo.

REM Check Python path
set PYTHONPATH=%CD%
cd /d "%~dp0"

REM Run scheduler sync
echo [2/2] Running scheduler sync...
echo.
"%PYTHON_EXE%" -c "
import sys
sys.path.insert(0, '.')
from src.scheduler_service import sync_scheduler_to_windows, check_sync_status

print('=== Checking Scheduler Status ===')
status = check_sync_status()
print(f'Status: {status[\"status\"]}')
print(f'Message: {status[\"message\"]}')
print(f'Database Enabled: {status[\"database_enabled\"]}')
print(f'Schedule Mode: {status[\"scheduler_mode\"]}')
print(f'Database Times: {status[\"database_times\"]}')
print(f'OS Tasks: {status[\"os_tasks\"]}')
print()

if status['database_enabled']:
    print('=== Syncing to Windows Task Scheduler ===')
    success, message, results = sync_scheduler_to_windows()
    print(f'Result: {message}')
    for r in results:
        print(f'  - {r[\"task\"]}: {r[\"action\"]} - {\"OK\" if r[\"success\"] else \"FAILED\"}')
        if not r['success']:
            print(f'    Message: {r[\"message\"]}')
else:
    print('Scheduler is disabled in database.')
    print('Enable it from Admin Dashboard > Pengaturan > Scheduler')
"

echo.
echo ============================================
echo   DONE
echo ============================================
echo.
pause
