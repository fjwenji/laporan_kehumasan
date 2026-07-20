@echo off
REM ===========================================
REM Mayz Sync - Worker Batch Script
REM ===========================================
REM
REM Script ini dijalankan oleh Windows Task Scheduler untuk melakukan
REM scraping Instagram secara terjadwal.
REM
REM Cara pakai:
REM   mayz_sync.bat              - Jalankan worker sekali jalan
REM
REM Biasanya dipanggil oleh Task Scheduler:
REM   schtasks /create /tn "Mayz_HOT_AM" /tr "D:\path\to\mayz_sync.bat" /sc DAILY /st 06:00 /f
REM

setlocal enabledelayedexpansion

REM --- Konfigurasi ---
set "PROJECT_ROOT=%~dp0"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
cd /d "%PROJECT_ROOT%"

REM --- Setup Environment ---
set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

set "PYTHON_PATH=%PROJECT_ROOT%"
set "WORKER_SCRIPT=%PROJECT_ROOT%\worker\main.py"

REM --- Logging ---
set "LOG_DIR=%PROJECT_ROOT%\logs"
set "LOG_FILE=%LOG_DIR%\mayz_sync.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM --- Log Header ---
echo [%date% %time%] ======================================= >> "%LOG_FILE%"
echo [%date% %time%] Mayz Sync Started >> "%LOG_FILE%"
echo [%date% %time%] Project: %PROJECT_ROOT% >> "%LOG_FILE%"
echo [%date% %time%] Python: %PYTHON_EXE% >> "%LOG_FILE%"
echo [%date% %time%] Worker: %WORKER_SCRIPT% >> "%LOG_FILE%"

REM --- Check Prerequisites ---

REM Check Python
if exist "%PYTHON_EXE%" (
    echo Python found: %PYTHON_EXE%
    echo [%date% %time%] Python OK: %PYTHON_EXE% >> "%LOG_FILE%"
) else (
    echo ERROR: Python not found at %PYTHON_EXE%
    echo [%date% %time%] ERROR: Python not found >> "%LOG_FILE%"
    exit /b 1
)

REM Check Worker Script
if exist "%WORKER_SCRIPT%" (
    echo Worker script found: %WORKER_SCRIPT%
    echo [%date% %time%] Worker script OK >> "%LOG_FILE%"
) else (
    echo ERROR: Worker script not found at %WORKER_SCRIPT%
    echo [%date% %time%] ERROR: Worker script not found >> "%LOG_FILE%"
    exit /b 1
)

REM --- Check Database Connection ---
echo.
echo [1/3] Checking database connection...
"%PYTHON_EXE%" -c "import sys; sys.path.insert(0, '%PYTHON_PATH%'); from src.database import test_connection; ok, msg = test_connection(); print('Database:', msg); sys.exit(0 if ok else 1)" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo ERROR: Database connection failed
    echo [%date% %time%] ERROR: Database connection failed >> "%LOG_FILE%"
    exit /b 1
)
echo [OK] Database connected

REM --- Check Scheduler Enabled ---
echo.
echo [2/3] Checking scheduler settings...
"%PYTHON_EXE%" -c "import sys; sys.path.insert(0, '%PYTHON_PATH%'); from src.scheduler_service import get_scheduler_enabled; enabled = get_scheduler_enabled(); print('Scheduler enabled:', enabled); sys.exit(0 if enabled else 1)" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [INFO] Scheduler disabled in database, checking for pending jobs...
    echo [%date% %time%] Scheduler disabled, checking for jobs >> "%LOG_FILE%"
) else (
    echo [OK] Scheduler enabled
    echo [%date% %time%] Scheduler enabled >> "%LOG_FILE%"
)

REM --- Run Worker ---
echo.
echo [3/3] Running worker...
echo [%date% %time%] Starting worker... >> "%LOG_FILE%"

cd /d "%PROJECT_ROOT%"
"%PYTHON_EXE%" "%WORKER_SCRIPT%" --once >> "%LOG_FILE%" 2>&1
set WORKER_EXIT=%errorlevel%

REM --- Log Results ---
if %WORKER_EXIT% equ 0 (
    echo.
    echo [%date% %time%] Worker completed successfully >> "%LOG_FILE%"
    echo [OK] Worker completed successfully
) else (
    echo.
    echo [%date% %time%] Worker exited with code: %WORKER_EXIT% >> "%LOG_FILE%"
    echo [WARN] Worker exited with code: %WORKER_EXIT%
)

echo [%date% %time%] ======================================= >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

REM --- Cleanup ---
endlocal

exit /b %WORKER_EXIT%
