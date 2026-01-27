@echo off
chcp 65001 >nul

setlocal enabledelayedexpansion

echo ==========================================
echo   SAPAS 本地启动
echo ==========================================

set PROJECT_ROOT=%~dp0..
set BACKEND_DIR=%PROJECT_ROOT%\backend
set FRONTEND_DIR=%PROJECT_ROOT%\frontend

if not exist "%BACKEND_DIR%\venv" (
    echo [错误] 后端虚拟环境不存在
    echo 请先运行 scripts\init.bat 初始化项目
    pause
    exit /b 1
)

if not exist "%FRONTEND_DIR%\node_modules" (
    echo [错误] 前端依赖未安装
    echo 请先运行 scripts\init.bat 初始化项目
    pause
    exit /b 1
)

REM 创建日志目录
if not exist "%PROJECT_ROOT%\logs" mkdir "%PROJECT_ROOT%\logs"

echo.
echo 启动后端服务...
cd /d %BACKEND_DIR%
start "SAPAS Backend" cmd /k "venv\Scripts\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8082 --reload"

echo.
echo 启动前端服务...
cd /d %FRONTEND_DIR%
start "SAPAS Frontend" cmd /k "npm run dev"

cd /d %PROJECT_ROOT%

echo.
echo ==========================================
echo   服务已启动
echo ==========================================
echo.
echo 服务地址：
echo   后端 API: http://localhost:8082
echo   前端页面: http://localhost:5173
echo   API 文档: http://localhost:8082/docs
echo.
echo 关闭命令窗口即可停止服务
echo.

pause
