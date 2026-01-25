@echo off
REM ============================================================
REM 数据网关服务启动脚本 (Windows)
REM 从项目根目录启动 data_gateway 服务
REM ============================================================

echo =====================================================
echo   Data Gateway Service
echo =====================================================
echo.

REM 获取脚本所在目录（项目根目录）
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%

REM 切换到 data_gateway 目录
cd /d "%PROJECT_ROOT%data_gateway"

echo 项目根目录: %PROJECT_ROOT%
echo 工作目录: %CD%
echo.

REM 设置默认环境变量
if "%DG_HOST%"=="" set DG_HOST=0.0.0.0
if "%DG_PORT%"=="" set DG_PORT=8001
if "%DG_DEBUG%"=="" set DG_DEBUG=false
if "%DG_LOG_LEVEL%"=="" set DG_LOG_LEVEL=INFO

REM 检查必需的环境变量
if "%DG_DATABASE_URL%"=="" (
    echo 错误: 必须设置 DG_DATABASE_URL 环境变量
    echo 示例: DG_DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
    exit /b 1
)

if "%DG_DATABASE_SYNC_URL%"=="" set DG_DATABASE_SYNC_URL=%DG_DATABASE_URL%
if "%DG_REDIS_URL%"=="" set DG_REDIS_URL=redis://localhost:6379/0
if "%DG_REDIS_MESSAGE_QUEUE%"=="" set DG_REDIS_MESSAGE_QUEUE=data-gateway:queue
if "%DG_REDIS_QUOTE_CHANNEL_PREFIX%"=="" set DG_REDIS_QUOTE_CHANNEL_PREFIX=quote
if "%DG_CACHE_TTL_REALTIME%"=="" set DG_CACHE_TTL_REALTIME=5
if "%DG_CACHE_TTL_KLINE%"=="" set DG_CACHE_TTL_KLINE=60
if "%DG_AKSHARE_ENABLED%"=="" set DG_AKSHARE_ENABLED=true
if "%DG_BAOSTOCK_ENABLED%"=="" set DG_BAOSTOCK_ENABLED=true
if "%DG_RATE_LIMIT_PER_MINUTE%"=="" set DG_RATE_LIMIT_PER_MINUTE=120
if "%DG_RATE_LIMIT_PER_HOUR%"=="" set DG_RATE_LIMIT_PER_HOUR=1000
if "%DG_LOG_FILE%"=="" set DG_LOG_FILE=logs\data_gateway.log

echo 服务配置:
echo   - HOST: %DG_HOST%
echo   - PORT: %DG_PORT%
echo   - DEBUG: %DG_DEBUG%
echo   - LOG_LEVEL: %DG_LOG_LEVEL%
echo.
echo 数据源配置:
echo   - AKShare: %DG_AKSHARE_ENABLED%
echo   - BaoStock: %DG_BAOSTOCK_ENABLED%
if "%DG_MIANA_TOKEN%"=="" (
    echo   - Miana Token: 未配置
) else (
    echo   - Miana Token: 已配置
)
echo.
echo =====================================================
echo.

REM 启动服务
python -m uvicorn src.main:app --host %DG_HOST% --port %DG_PORT% --log-level %DG_LOG_LEVEL%
