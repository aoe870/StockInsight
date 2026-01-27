#!/bin/bash
# StockInsight 启动脚本
# 默认启动数据网关和 SAPAS，不执行初始化 SQL 脚本

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

print_banner() {
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}   StockInsight - 启动服务${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo ""
}

print_usage() {
    echo "用法: $0 [选项] [服务名]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo ""
    echo "服务名 (可选):"
    echo "  all            启动所有服务（数据网关 + SAPAS）- 默认"
    echo "  gateway       仅启动数据网关"
    echo "  sapas         仅启动 SAPAS（前端+后端）"
    echo "  backend       仅启动 SAPAS 后端"
    echo "  frontend      仅启动 SAPAS 前端"
    echo "  middleware    仅启动中间件（PostgreSQL + Redis）"
    echo ""
    echo "示例:"
    echo "  $0                    # 启动所有服务"
    echo "  $0 gateway        # 仅启动数据网关"
    echo "  $0 sapas           # 仅启动 SAPAS"
    echo ""
    echo "其他命令:"
    echo "  ./stop.sh              # 停止所有服务"
    echo "  ./init-deploy.sh       # 初始化部署（含数据库初始化）"
}

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[X] 未找到 Docker${NC}"
    exit 1
fi

# 检查 docker-compose
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo -e "${RED}[X] 未找到 Docker Compose${NC}"
    exit 1
fi

# 解析参数
SERVICE=""
SKIP_GATEWAY=false
SKIP_SAPAS=false
SKIP_MIDDLEWARE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_usage
            exit 0
            ;;
        all|gateway|sapas|backend|frontend|middleware)
            SERVICE=$1
            shift
            ;;
        *)
            echo -e "${RED}[X] 未知选项: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

# 默认启动所有服务
if [ -z "$SERVICE" ] || [ "$SERVICE" = "all" ]; then
    SKIP_GATEWAY=false
    SKIP_SAPAS=false
elif [ "$SERVICE" = "gateway" ]; then
    SKIP_SAPAS=true
    SKIP_MIDDLEWARE=true
elif [ "$SERVICE" = "sapas" ]; then
    SKIP_GATEWAY=true
elif [ "$SERVICE" = "backend" ]; then
    SKIP_GATEWAY=true
    SKIP_MIDDLEWARE=true
    FRONTEND_ONLY=true
elif [ "$SERVICE" = "frontend" ]; then
    SKIP_GATEWAY=true
    SKIP_MIDDLEWARE=true
elif [ "$SERVICE" = "middleware" ]; then
    SKIP_GATEWAY=true
    SKIP_SAPAS=true
fi

print_banner
echo -e "${GREEN}[√] Docker: $(docker --version)${NC}"
echo -e "${GREEN}[√] Docker Compose: 已找到${NC}"

# ========================================
# 步骤 1: 启动中间件（如果需要）
# ========================================
if [ "$SKIP_MIDDLEWARE" != true ]; then
    echo -e "${YELLOW}[1/3] 启动中间件 (PostgreSQL, Redis)...${NC}"
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
fi

# ========================================
# 步骤 2: 启动数据网关（如果需要）
# ========================================
if [ "$SKIP_GATEWAY" != true ]; then
    echo -e "${YELLOW}[2/3] 启动数据网关...${NC}"
    cd "$PROJECT_ROOT/data_gateway"

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
    echo ""
fi

# ========================================
# 步骤 3: 启动 SAPAS（如果需要）
# ========================================
if [ "$SKIP_SAPAS" != true ]; then
    echo -e "${YELLOW}[3/3] 启动 SAPAS 平台...${NC}"

    # 直接启动容器（不构建镜像）
    if [ -n "$FRONTEND_ONLY" ]; then
        $DOCKER_COMPOSE -f $COMPOSE_FILE up -d backend frontend
    else
        $DOCKER_COMPOSE -f $COMPOSE_FILE up -d backend
    fi

    # 等待服务启动
    echo -e "${YELLOW}[i] 等待服务启动...${NC}"
    sleep 5

    echo -e "${GREEN}[√] SAPAS 平台启动完成${NC}"
    echo ""
fi

# ========================================
# 完成提示
# ========================================
echo -e "${CYAN}============================================================${NC}"
echo -e "${GREEN}  启动完成！${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""
echo "服务地址："
echo "  数据库:   localhost:5433"
echo "  Redis:    localhost:6380"
if [ "$SKIP_GATEWAY" != true ]; then
    echo "  数据网关: http://localhost:8001"
fi
if [ "$SKIP_SAPAS" != true ]; then
    echo "  后端 API: http://localhost:8082"
    echo "  API 文档: http://localhost:8082/docs"
    if [ -z "$FRONTEND_ONLY" ]; then
        echo "  前端页面: http://localhost"
    fi
fi
echo ""
echo "常用命令："
echo "  查看所有服务状态: $DOCKER_COMPOSE -f $COMPOSE_FILE ps"
echo "  查看所有服务日志: $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f"
echo "  查看后端日志: $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f backend"
echo "  查看前端日志: $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f frontend"
echo "  查看网关日志: tail -f logs/gateway.log"
echo "  停止所有服务: ./stop.sh"
echo "  初始化部署: ./init-deploy.sh"
echo ""
