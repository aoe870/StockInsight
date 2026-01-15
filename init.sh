#!/bin/bash

# SAPAS 数据库初始化脚本
# 使用 docker-compose 管理 PostgreSQL

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  SAPAS 数据库初始化${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查 docker-compose
if ! command -v docker-compose &> /dev/null; then
    if ! docker compose version &> /dev/null; then
        echo -e "${RED}[×] 未找到 docker-compose，请先安装${NC}"
        exit 1
    fi
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo -e "${YELLOW}[i] 使用: $COMPOSE_CMD${NC}"

# 启动 PostgreSQL
echo -e "${GREEN}[>] 启动 PostgreSQL 容器...${NC}"
$COMPOSE_CMD up -d postgres

# 等待健康检查通过
echo -e "${YELLOW}[i] 等待 PostgreSQL 就绪...${NC}"
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if $COMPOSE_CMD exec -T postgres pg_isready -U root -d sapas_db > /dev/null 2>&1; then
        echo -e "${GREEN}[√] PostgreSQL 已就绪${NC}"
        break
    fi
    echo "  尝试 $attempt/$max_attempts..."
    sleep 2
    ((attempt++))
done

if [ $attempt -gt $max_attempts ]; then
    echo -e "${RED}[×] PostgreSQL 启动超时${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  数据库初始化完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}连接信息:${NC}"
echo "  主机: localhost"
echo "  端口: 5432"
echo "  数据库: sapas_db"
echo "  用户: root"
echo ""
echo -e "${YELLOW}常用命令:${NC}"
echo "  启动: $COMPOSE_CMD up -d"
echo "  停止: $COMPOSE_CMD down"
echo "  日志: $COMPOSE_CMD logs -f postgres"
echo "  连接: $COMPOSE_CMD exec postgres psql -U root -d sapas_db"