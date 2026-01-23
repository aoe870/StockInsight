@echo off
REM ============================================================
REM SAPAS 启动脚本 (Windows)
REM 股票数据分析与处理自动化服务
REM ============================================================

setlocal enabledelayedexpansion

REM 默认配置
set BACKEND_PORT=8081
set FRONTEND_PORT=5173
set HOST=0.0.0.0
set VENV_DIR=.venv
set WEB_DIR=web

echo ============================================================
echo    SAPAS - Stock Analysis Processing Automated Service
echo    股票数据分析与处理自动化服务
echo ============================================================
echo.

REM 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo [X] 未找到 Python，请先安装 Python 3.11+
    exit /b 1
)
echo [√] 系统 Python:
python --version

REM 创建虚拟环境
if not exist "%VENV_DIR%" (
    echo [i] 创建虚拟环境: %VENV_DIR%
    python -m venv %VENV_DIR%
    echo [√] 虚拟环境已创建
)

REM 激活虚拟环境
echo [i] 激活虚拟环境...
call %VENV_DIR%\Scripts\activate.bat
echo [√] 虚拟环境已激活

REM 检查 .env 文件
if not exist ".env" (
    echo [!] 未找到 .env 配置文件
    if exist ".env.example" (
        copy .env.example .env
        echo [√] 已从 .env.example 复制配置文件
        echo [!] 请编辑 .env 文件配置数据库连接
    )
)

REM 创建日志目录
if not exist "logs" mkdir logs

REM 根据命令执行操作
if "%1"=="server" goto :server
if "%1"=="web" goto :web
if "%1"=="dev" goto :dev
if "%1"=="install" goto :install
if "%1"=="init-db" goto :init_db
if "%1"=="health" goto :health
if "%1"=="help" goto :help
if "%1"=="--help" goto :help
if "%1"=="-h" goto :help

goto :help

:server
echo.
echo [>] 启动后端 API 服务器...
echo [i] 地址: http://%HOST%:%BACKEND_PORT%
echo [i] API 文档: http://%HOST%:%BACKEND_PORT%/docs
echo [i] 健康检查: http://%HOST%:%BACKEND_PORT%/health
echo [i] 按 Ctrl+C 停止服务
echo.
python -m uvicorn src.main:app --host %HOST% --port %BACKEND_PORT% --reload
goto :end

:web
echo.
echo [>] 启动前端服务器...
if not exist "%WEB_DIR%" (
    echo [X] 前端目录不存在
    exit /b 1
)
cd %WEB_DIR%

REM 检查 node_modules
if not exist "node_modules" (
    echo [i] 安装前端依赖...
    npm install
)

echo [i] 地址: http://localhost:%FRONTEND_PORT%
echo [i] 按 Ctrl+C 停止服务
echo.
npm run dev -- --port %FRONTEND_PORT%
goto :end

:dev
echo.
echo [>] 开发模式: 同时启动前后端
echo.

REM 启动后端（使用 start /B 在后台运行）
echo [>] 启动后端...
start /B python -m uvicorn src.main:app --host %HOST% --port %BACKEND_PORT% --reload

REM 等待后端启动
timeout /t 3 /nobreak >nul

REM 启动前端
echo [>] 启动前端...
cd %WEB_DIR%

if not exist "node_modules" (
    npm install
)

echo.
echo =============================================================
echo   后端运行中: http://%HOST%:%BACKEND_PORT%
echo   前端运行中: http://localhost:%FRONTEND_PORT%
echo   按 Ctrl+C 停止当前窗口的服务
echo =============================================================
echo.
npm run dev -- --port %FRONTEND_PORT%
goto :end

:install
echo.
echo [>] 安装依赖...
echo.
echo [>] 升级 pip...
python -m pip install --upgrade pip
echo [>] 安装 Python 依赖...
pip install -r requirements.txt
echo [√] 后端依赖安装完成
echo.

if exist "%WEB_DIR%" (
    echo [>] 安装前端依赖...
    cd %WEB_DIR%
    call npm install
    cd ..
    echo [√] 前端依赖安装完成
)
echo.
echo [√] 所有依赖安装完成
goto :end

:init_db
echo.
echo [>] 初始化数据库...
echo.

REM 检查 Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [X] 未找到 Docker，请先安装 Docker Desktop
    goto :end
)

REM 启动 PostgreSQL
echo [>] 启动 PostgreSQL...
docker-compose up -d postgres

REM 等待 PostgreSQL 就绪
echo [i] 等待 PostgreSQL 就绪...
timeout /t 5 /nobreak >nul

REM 执行 SQL 脚本
echo [>] 执行数据库脚本...
docker-compose exec -T postgres psql -U root -d sapas_db -f /docker-entrypoint-initdb.d/01_create_tables.sql
docker-compose exec -T postgres psql -U root -d sapas_db -f /docker-entrypoint-initdb.d/02_create_indexes.sql
docker-compose exec -T postgres psql -U root -d sapas_db -f /docker-entrypoint-initdb.d/03_create_functions.sql
docker-compose exec -T postgres psql -U root -d sapas_db -f /docker-entrypoint-initdb.d/04_seed_data.sql

echo [√] 数据库初始化完成
goto :end

:health
echo.
echo [>] 运行健康检查...
echo.
python scripts\health_check.py
goto :end

:help
echo.
echo ============================================================
echo 用法: start.bat [command]
echo.
echo 命令:
echo   server       启动后端 API 服务器 (默认端口: 8081)
echo   web          启动前端开发服务器 (默认端口: 5173)
echo   dev          同时启动前后端 (推荐)
echo   install      安装依赖 (Python + Node.js)
echo   init-db      初始化数据库 (执行 SQL 脚本)
echo   health       健康检查 (检查所有服务状态)
echo   help         显示此帮助信息
echo.
echo 数据同步说明:
echo   服务启动时自动执行:
echo     - 检查并同步股票列表（如果为空）
echo     - 同步自选股的K线数据（如果有缺失）
echo.
echo   定时任务（服务运行期间自动执行）:
echo     - 盘后同步: 每个交易日 15:30
echo     - 股票列表更新: 每周一 9:00
echo     - 盘中更新: 交易时段每 30 分钟
echo.
echo 环境变量:
echo   BACKEND_PORT   后端端口 (默认: 8081)
echo   FRONTEND_PORT  前端端口 (默认: 5173)
echo   HOST           服务器地址 (默认: 0.0.0.0)
echo.
echo 快速开始:
echo   1. start.bat install       # 安装依赖
echo   2. start.bat init-db       # 初始化数据库
echo   3. start.bat dev           # 启动服务
echo   4. 打开浏览器访问 http://localhost:5173
echo ============================================================
echo.

:end
endlocal
