@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo Personal Expense System Launcher
echo ========================================
echo.

set "PYTHON_CMD=python"
where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python 3.8+ was not found.
        pause
        exit /b 1
    )
    set "PYTHON_CMD=py"
)

echo [1/4] Checking Python...
%PYTHON_CMD% --version
if errorlevel 1 (
    echo [ERROR] Failed to run Python.
    pause
    exit /b 1
)

echo [2/4] Checking dependencies...
%PYTHON_CMD% -m pip show starlette >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies from requirements.txt...
    %PYTHON_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed.
        pause
        exit /b 1
    )
)

echo [3/4] Preparing folders...
if not exist "data" mkdir data
if not exist "exports" mkdir exports
if not exist "backups" mkdir backups

echo [4/4] Starting backend service...
start "Expense API" cmd /k "%PYTHON_CMD% -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

echo Waiting for backend to become ready...
set "READY=0"
for /L %%i in (1,1,20) do (
    powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/ -TimeoutSec 1 ^| Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        set "READY=1"
        goto :backend_ready
    )
    timeout /t 1 >nul
)

:backend_ready
echo.
if "%READY%"=="1" (
    echo Backend is ready.
) else (
    echo Warning: backend may still be starting.
)
echo ========================================
echo Frontend: http://127.0.0.1:8000/frontend/index.html
echo Backend : http://127.0.0.1:8000
echo ========================================
echo.
start "" "http://127.0.0.1:8000/frontend/index.html"
echo You can close this window after the browser opens.
pause
