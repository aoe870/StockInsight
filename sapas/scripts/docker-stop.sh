#!/bin/bash
# SAPAS Docker 停止脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================="
echo "  SAPAS Docker 停止"
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

# 停止容器
echo -e "${YELLOW}停止 Docker 容器...${NC}"
$DOCKER_COMPOSE down

echo ""
echo "=========================================="
echo -e "${GREEN}✓ Docker 服务已停止${NC}"
echo "=========================================="
echo ""
echo "提示：使用 '$DOCKER_COMPOSE down -v' 可同时删除数据卷"
echo ""
