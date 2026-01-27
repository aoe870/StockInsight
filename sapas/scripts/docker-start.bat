@echo off
chcp 65001 >nul

echo ==========================================
echo   SAPAS Docker 启动
echo ==========================================

cd /d %~dp0..

where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 Docker
    echo 请先安装 Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo.
echo 构建并启动 Docker 容器...
docker-compose up -d --build

echo.
echo 等待服务启动...
timeout /t 5 /nobreak >nul

echo.
echo 服务状态：
docker-compose ps

echo.
echo ==========================================
echo   Docker 服务已启动
echo ==========================================
echo.
echo 服务地址：
echo   前端页面: http://localhost
echo   后端 API: http://localhost:8082
echo   API 文档: http://localhost:8082/docs
echo   数据网关: http://localhost:8001
echo.
echo 查看日志: docker-compose logs -f
echo 停止服务: scripts\docker-stop.bat
echo.

pause
