@echo off
REM Data Gateway Service Startup Script (Windows)

setlocal enabledelayedexpansion

REM Default configuration
if "%DG_HOST%"=="" set HOST=0.0.0.0
if "%DG_PORT%"=="" set PORT=8002

echo ============================================================
echo    Data Gateway Service
echo ============================================================
echo.

REM Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo [X] Python not found, please install Python 3.11+
    exit /b 1
)
echo [OK] Python:
python --version

REM Change to data_gateway directory
cd /d %~dp0..
set PROJECT_DIR=%CD%

REM Create logs directory
if not exist "%PROJECT_DIR%\logs" mkdir "%PROJECT_DIR%\logs"

echo.
echo =============================================================
echo   Starting service...
echo =============================================================
echo.
echo [i] Service URL: http://%HOST%:%PORT%
echo [i] API Docs: http://%HOST%:%PORT%/docs
echo.

REM Start service
cd /d "%PROJECT_DIR%"
python -m uvicorn src.main:app --host %HOST% --port %PORT% --reload

endlocal
