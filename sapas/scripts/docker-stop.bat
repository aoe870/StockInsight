@echo off
chcp 65001 >nul

echo ==========================================
echo   SAPAS Docker 停止
echo ==========================================

cd /d %~dp0..

echo.
echo 停止 Docker 容器...
docker-compose down

echo.
echo ==========================================
echo   Docker 服务已停止
echo ==========================================
echo.
echo 提示：使用 'docker-compose down -v' 可同时删除数据卷
echo.

pause
