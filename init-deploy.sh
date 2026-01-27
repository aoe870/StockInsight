#!/bin/bash
# StockInsight 初始化部署脚本
# 首次部署时使用，执行完整的初始化流程

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/sapas/docker-compose.yml"
SQL_FILE="$PROJECT_ROOT/sapas/backend/scripts/init_db.sql"

print_banner() {
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}   StockInsight - 初始化部署${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo ""
}

print_banner

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[X] 未找到 Docker${NC}"
    exit 1
fi
echo -e "${GREEN}[√] Docker: $(docker --version)${NC}"

# 检查 docker-compose
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo -e "${RED}[X] 未找到 Docker Compose${NC}"
    exit 1
fi
echo -e "${GREEN}[√] Docker Compose: 已找到${NC}"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}[!] 未找到 Python3，数据网关将无法启动${NC}"
    SKIP_GATEWAY=true
else
    echo -e "${GREEN}[√] Python: $(python3 --version)${NC}"
    SKIP_GATEWAY=false
fi
echo ""

# ========================================
# 步骤 1: 启动中间件
# ========================================
echo -e "${YELLOW}[1/4] 启动中间件 (PostgreSQL, Redis)...${NC}"
$DOCKER_COMPOSE -f $COMPOSE_FILE up -d postgres redis

# 等待数据库就绪
echo -e "${YELLOW}[i] 等待数据库就绪...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if $DOCKER_COMPOSE -f $COMPOSE_FILE exec -T postgres pg_isready -U root &> /dev/null; then
        echo -e "${GREEN}[√] 数据库已就绪${NC}"
        break
    fi
    sleep 1
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}[X] 数据库启动超时${NC}"
    exit 1
fi

echo -e "${GREEN}[√] 中间件启动完成${NC}"
echo ""

# ========================================
# 步骤 2: 初始化数据库
# ========================================
echo -e "${YELLOW}[2/4] 初始化数据库...${NC}"

# 检查表是否已存在
TABLE_EXISTS=$($DOCKER_COMPOSE -f $COMPOSE_FILE exec -T postgres psql -U root -d sapas_db -tAc "SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name = 'users')" 2>/dev/null || true)

if [ "$TABLE_EXISTS" = "t" ]; then
    echo -e "${YELLOW}[!] 数据库表已存在，跳过初始化${NC}"
else
    # 执行 SQL 初始化脚本
    if [ -f "$SQL_FILE" ]; then
        $DOCKER_COMPOSE -f $COMPOSE_FILE exec -T postgres psql -U root -d sapas_db < "$SQL_FILE"
        echo -e "${GREEN}[√] 数据库初始化完成${NC}"
    else
        echo -e "${YELLOW}[!] SQL 初始化文件不存在，跳过数据库初始化${NC}"
    fi
fi
echo ""

# ========================================
# 步骤 3: 启动数据网关
# ========================================
if [ "$SKIP_GATEWAY" != true ]; then
    echo -e "${YELLOW}[3/4] 启动数据网关...${NC}"
    cd "$PROJECT_ROOT/data_gateway"

    # 检查并创建虚拟环境
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}[i] 创建虚拟环境...${NC}"
        python3 -m venv venv
    fi

    # 根据平台选择激活脚本
    if [ -f "venv/Scripts/activate" ]; then
        ACTIVATE_SCRIPT="venv/Scripts/activate"
    elif [ -f "venv/bin/activate" ]; then
        ACTIVATE_SCRIPT="venv/bin/activate"
    else
        echo -e "${YELLOW}[!] 找不到虚拟环境激活脚本，跳过数据网关启动${NC}"
        cd "$PROJECT_ROOT"
        SKIP_GATEWAY=true
    fi

    if [ "$SKIP_GATEWAY" != true ]; then
        # 激活虚拟环境
        source "$ACTIVATE_SCRIPT"

        # 安装依赖
        if [ ! -f ".installed" ]; then
            echo -e "${YELLOW}[i] 安装依赖...${NC}"
            python -m pip install --upgrade pip -q 2>/dev/null || true
            python -m pip install -q -r requirements.txt
            touch .installed
        fi

        # 启动数据网关（后台运行）
        echo -e "${YELLOW}[i] 启动数据网关服务...${NC}"
        mkdir -p "$PROJECT_ROOT/logs"
        nohup python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 > "$PROJECT_ROOT/logs/gateway.log" 2>&1 &
        GATEWAY_PID=$!
        echo $GATEWAY_PID > "$PROJECT_ROOT/logs/gateway.pid"

        deactivate
        cd "$PROJECT_ROOT"

        # 等待数据网关启动
        echo -e "${YELLOW}[i] 等待数据网关启动...${NC}"
        sleep 3

        echo -e "${GREEN}[√] 数据网关启动完成 (PID: $GATEWAY_PID)${NC}"
    fi
else
    echo -e "${YELLOW}[3/4] 跳过数据网关（未找到 Python3）${NC}"
fi
echo ""

# ========================================
# 步骤 4: 启动 SAPAS 平台（前端+后端）
# ========================================
echo -e "${YELLOW}[4/4] 启动 SAPAS 平台（前端+后端）...${NC}"
$DOCKER_COMPOSE -f $COMPOSE_FILE start backend frontend

# 等待服务就绪
echo -e "${YELLOW}[i] 等待服务启动...${NC}"
sleep 5

# 检查服务状态
echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "${GREEN}  初始化部署完成！${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""
echo "服务地址："
echo "  数据库:   localhost:5433"
echo "  Redis:    localhost:6380"
echo "  数据网关: http://localhost:8001"
echo "  后端 API: http://localhost:8082"
echo "  API 文档: http://localhost:8082/docs"
echo "  前端页面: http://localhost"
echo ""
echo "常用命令："
echo "  查看所有服务状态: $DOCKER_COMPOSE -f $COMPOSE_FILE ps"
echo "  查看后端日志: $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f backend"
echo "  查看前端日志: $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f frontend"
echo "  查看网关日志: tail -f logs/gateway.log"
echo "  停止所有服务: ./stop.sh"
echo ""
