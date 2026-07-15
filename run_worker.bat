@echo off
setlocal
cd /d "%~dp0"

echo.
echo ============================================
echo   MAYZ SCRAPER WORKER
echo ============================================
echo.

if not exist "worker\main.py" (
    echo ERROR: worker\main.py tidak ditemukan. Jalankan dari root project Mayz.
    pause
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [1/2] Checking Python...
"%PYTHON_EXE%" --version
if errorlevel 1 (
    echo ERROR: Python tidak ditemukan.
    pause
    exit /b 1
)

echo.
echo [2/2] Starting worker...
echo Worker berjalan terus dan membaca job dari database.
echo Tekan Ctrl+C untuk menghentikan.
echo.

"%PYTHON_EXE%" "%CD%\worker\main.py" %*

if errorlevel 1 (
    echo.
    echo WORKER STOPPED WITH ERROR.
    pause
)
endlocal
