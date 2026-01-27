@echo off
REM StockInsight 服务停止脚本 (Windows)

setlocal enabledelayedexpansion

REM 项目根目录
set "PROJECT_ROOT=%~dp0"
set "COMPOSE_FILE=%PROJECT_ROOT%sapas\docker-compose.yml"

echo.
echo ============================================================
echo    StockInsight - 停止服务
echo ============================================================
echo.

REM ========================================
REM 步骤 1: 停止数据网关
REM ========================================
if exist "%PROJECT_ROOT%logs\gateway.pid" (
    echo [1/3] 停止数据网关...
    set /p GATEWAY_PID=<"%PROJECT_ROOT%logs\gateway.pid"
    taskkill /PID !GATEWAY_PID! /F >nul 2>&1
    if %errorlevel% equ 0 (
        echo [√] 数据网关已停止 (PID: !GATEWAY_PID!)
    ) else (
        echo [!] 数据网关进程已不存在
    )
    del /f "%PROJECT_ROOT%logs\gateway.pid" >nul 2>&1
) else (
    echo [1/3] 跳过数据网关（未找到 PID 文件）
)

REM 检查并停止其他可能的进程
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /fo csv ^| findstr /i "uvicorn"') do (
    taskkill /PID %%~i /F >nul 2>&1
    echo [√] 已终止遗留的数据网关进程
)

echo.

REM ========================================
REM 步骤 2: 停止平台前后端
REM ========================================
echo [2/3] 停止平台前后端...
cd /d "%PROJECT_ROOT%sapas"

where docker-compose >nul 2>&1
if %errorlevel% neq 0 (
    docker compose version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [X] 未找到 Docker Compose
        exit /b 1
    )
    set "DOCKER_COMPOSE=docker compose"
) else (
    set "DOCKER_COMPOSE=docker-compose"
)

%DOCKER_COMPOSE% stop backend frontend
echo [√] 平台前后端已停止
echo.

REM ========================================
REM 步骤 3: 停止中间件（可选）
REM ========================================
set /p STOP_MIDDLEWARE="[3/3] 是否停止中间件 (PostgreSQL, Redis)? [y/N]: "
if /i "%STOP_MIDDLEWARE%"=="y" (
    echo 停止中间件...
    %DOCKER_COMPOSE% stop postgres redis
    echo [√] 中间件已停止
) else (
    echo [!] 保留中间件运行
)

cd /d "%PROJECT_ROOT%"

echo.
echo ============================================================
echo    服务已停止！
echo ============================================================
echo.

pause
