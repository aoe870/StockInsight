#!/bin/bash
# SAPAS Docker 启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================="
echo "  SAPAS Docker 启动"
echo "=========================================="

cd "$PROJECT_ROOT"

# 检查 docker-compose
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo -e "${RED}错误: 未安装 Docker Compose${NC}"
    exit 1
fi

# 构建并启动
echo -e "${YELLOW}构建并启动 Docker 容器...${NC}"
$DOCKER_COMPOSE up -d --build

# 等待服务就绪
echo ""
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 5

# 检查服务状态
echo ""
echo "服务状态："
$DOCKER_COMPOSE ps

echo ""
echo "=========================================="
echo -e "${GREEN}✓ Docker 服务已启动${NC}"
echo "=========================================="
echo ""
echo "服务地址："
echo "  前端页面: http://localhost"
echo "  后端 API: http://localhost:8082"
echo "  API 文档: http://localhost:8082/docs"
echo "  数据网关: http://localhost:8001"
echo ""
echo "查看日志: $DOCKER_COMPOSE logs -f"
echo "停止服务: ./scripts/docker-stop.sh"
echo ""
