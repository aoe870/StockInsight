@echo off
REM StockInsight 完整服务启动脚本 (Windows)

setlocal enabledelayedexpansion

REM 颜色定义
set "RED=[31m"
set "GREEN=[32m"
set "YELLOW=[33m"
set "CYAN=[36m"
set "NC=[0m"

REM 项目根目录
set "PROJECT_ROOT=%~dp0"
set "COMPOSE_FILE=%PROJECT_ROOT%sapas\docker-compose.yml"

echo.
echo ============================================================
echo    StockInsight - 股票分析平台
echo ============================================================
echo.

REM 检查 Docker
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[X] 未找到 Docker，请先安装%NC%
    exit /b 1
)
for /f "tokens=*" %%i in ('docker --version') do set DOCKER_VERSION=%%i
echo %GREEN%[√] Docker: %DOCKER_VERSION%%NC%

REM 检查 docker-compose
where docker-compose >nul 2>&1
if %errorlevel% neq 0 (
    docker compose version >nul 2>&1
    if %errorlevel% neq 0 (
        echo %RED%[X] 未找到 Docker Compose%NC%
        exit /b 1
    )
    set "DOCKER_COMPOSE=docker compose"
) else (
    set "DOCKER_COMPOSE=docker-compose"
)
echo %GREEN%[√] Docker Compose: 已找到%NC%

REM 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%[!] 未找到 Python，数据网关将无法启动%NC%
    set "SKIP_GATEWAY=1"
) else (
    for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
    echo %GREEN%[√] Python: %PYTHON_VERSION%%NC%
    set "SKIP_GATEWAY=0"
)

echo.

REM ========================================
REM 步骤 1: 启动中间件
REM ========================================
echo %YELLOW%[1/4] 启动中间件 (PostgreSQL, Redis)...%NC%
cd /d "%PROJECT_ROOT%sapas"
%DOCKER_COMPOSE% -f docker-compose.yml up -d postgres redis

echo %YELLOW%[i] 等待数据库就绪...%NC%
set /a RETRY_COUNT=0
:wait_db
%DOCKER_COMPOSE% exec -T postgres pg_isready -U sapas >nul 2>&1
if %errorlevel% equ 0 (
    echo %GREEN%[√] 数据库已就绪%NC%
    goto db_ready
)
set /a RETRY_COUNT+=1
if %RETRY_COUNT% geq 30 (
    echo %RED%[X] 数据库启动超时%NC%
    exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait_db
:db_ready

echo %GREEN%[√] 中间件启动完成%NC%
echo.

REM ========================================
REM 步骤 2: 初始化数据库
REM ========================================
echo %YELLOW%[2/4] 初始化数据库...%NC%
cd /d "%PROJECT_ROOT%sapas\backend"

REM 检查并创建虚拟环境
if not exist "venv" (
    echo %YELLOW%[i] 创建虚拟环境...%NC%
    python -m venv venv
)

REM 激活虚拟环境并安装依赖
call venv\Scripts\activate.bat

if not exist ".installed" (
    echo %YELLOW%[i] 安装依赖...%NC%
    python -m pip install --upgrade pip -q
    if exist "requirements.txt" (
        pip install -q -r requirements.txt
    ) else (
        pip install -q -e .
    )
    type nul > .installed
)

REM 初始化数据库
python scripts\init_db.py
echo %GREEN%[√] 数据库初始化完成%NC%

deactivate
cd /d "%PROJECT_ROOT%"
echo.

REM ========================================
REM 步骤 3: 启动数据网关
REM ========================================
if "%SKIP_GATEWAY%"=="0" (
    echo %YELLOW%[3/4] 启动数据网关...%NC%
    cd /d "%PROJECT_ROOT%data_gateway"

    REM 检查并创建虚拟环境
    if not exist "venv" (
        echo %YELLOW%[i] 创建虚拟环境...%NC%
        python -m venv venv
    )

    REM 激活虚拟环境
    call venv\Scripts\activate.bat

    REM 安装依赖
    if not exist ".installed" (
        echo %YELLOW%[i] 安装依赖...%NC%
        python -m pip install --upgrade pip -q
        pip install -q -r requirements.txt
        type nul > .installed
    )

    REM 创建日志目录
    if not exist "..\logs" mkdir "..\logs"

    REM 启动数据网关（后台运行）
    echo %YELLOW%[i] 启动数据网关服务...%NC%
    start /B python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 > ..\logs\gateway.log 2>&1

    REM 保存进程信息
    wmic process where "commandline like '%%uvicorn src.main:app%%'" get processid > ..\logs\gateway.tmp 2>&1
    for /f "skip=1" %%i in (..\logs\gateway.tmp) do (
        if not "%%i"=="" (
            set /p GATEWAY_PID=%%i <nul
            echo !GATEWAY_PID! > ..\logs\gateway.pid
        )
    )
    del ..\logs\gateway.tmp

    deactivate
    cd /d "%PROJECT_ROOT%"

    echo %YELLOW%[i] 等待数据网关启动...%NC%
    timeout /t 3 /nobreak >nul

    echo %GREEN%[√] 数据网关启动完成%NC%
) else (
    echo %YELLOW%[3/4] 跳过数据网关（未找到 Python）%NC%
)
echo.

REM ========================================
REM 步骤 4: 启动平台前后端
REM ========================================
echo %YELLOW%[4/4] 启动平台前后端...%NC%
cd /d "%PROJECT_ROOT%sapas"
%DOCKER_COMPOSE% -f docker-compose.yml up -d backend frontend

echo %YELLOW%[i] 等待服务启动...%NC%
timeout /t 5 /nobreak >nul

cd /d "%PROJECT_ROOT%"

REM 检查服务状态
echo.
echo ============================================================
echo %GREEN%  服务启动完成！%NC%
echo ============================================================
echo.
echo 服务地址：
echo   前端页面: http://localhost
echo   后端 API: http://localhost:8082
echo   API 文档: http://localhost:8082/docs
echo   数据网关: http://localhost:8001
echo   数据库:   localhost:5433
echo   Redis:    localhost:6380
echo.
echo 常用命令：
echo   查看日志: docker-compose -f sapas\docker-compose.yml logs -f
echo   查看状态: docker-compose -f sapas\docker-compose.yml ps
echo   停止服务: stop.bat
echo   查看网关日志: type logs\gateway.log
echo.

pause
