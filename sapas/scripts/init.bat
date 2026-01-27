@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================
echo   SAPAS 股票分析平台 - 初始化脚本
echo ==========================================
echo.

set PROJECT_ROOT=%~dp0..
set BACKEND_DIR=%PROJECT_ROOT%\backend
set FRONTEND_DIR=%PROJECT_ROOT%\frontend

echo 项目根目录: %PROJECT_ROOT%
echo.

REM 检查 Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python
    echo 请先安装 Python: https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo [OK] Python 检查通过
echo.

REM 检查 Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 Node.js
    echo 请先安装 Node.js: https://nodejs.org/
    pause
    exit /b 1
)

node --version
echo [OK] Node.js 检查通过
echo.

REM 初始化后端
echo ==========================================
echo   初始化后端
echo ==========================================
echo.

cd /d %BACKEND_DIR%

if not exist "venv" (
    echo 创建 Python 虚拟环境...
    python -m venv venv
    echo [OK] 虚拟环境已创建
)

call venv\Scripts\activate.bat

echo 安装 Python 依赖...
pip install --upgrade pip
pip install uv
uv pip install -e .
echo [OK] Python 依赖已安装

if not exist ".env" (
    echo 创建 .env 文件...
    copy .env.example .env
    echo [OK] .env 文件已创建，请修改其中的配置
) else (
    echo [OK] .env 文件已存在
)

echo 初始化数据库...
python scripts\init_db.py
echo [OK] 数据库初始化完成

deactivate
cd /d %PROJECT_ROOT%

REM 初始化前端
echo.
echo ==========================================
echo   初始化前端
echo ==========================================
echo.

cd /d %FRONTEND_DIR%

echo 安装 Node.js 依赖...
call npm install
echo [OK] Node.js 依赖已安装

cd /d %PROJECT_ROOT%

echo.
echo ==========================================
echo   初始化完成！
echo ==========================================
echo.
echo 后续步骤：
echo   1. 编辑 %BACKEND_DIR%\.env 配置数据库连接
echo   2. 运行 scripts\start.bat 启动服务
echo   3. 运行 scripts\docker-start.bat 启动 Docker 环境
echo.

pause
