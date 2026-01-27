#!/bin/bash
# StockInsight 停止脚本

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
    echo -e "${CYAN}   StockInsight - 停止服务${NC}"
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
    echo "  all            停止所有服务 - 默认"
    echo "  gateway       仅停止数据网关"
    echo "  sapas         仅停止 SAPAS（前端+后端）"
    echo "  backend       仅停止 SAPAS 后端"
    echo "  frontend      仅停止 SAPAS 前端"
    echo "  middleware    仅停止中间件（PostgreSQL + Redis）"
    echo ""
    echo "示例:"
    echo "  $0                    # 停止所有服务"
    echo "  $0 gateway        # 仅停止数据网关"
    echo "  $0 sapas           # 仅停止 SAPAS"
    echo ""
    echo "其他命令:"
    echo "  ./start.sh             # 启动所有服务"
    echo "  ./init-deploy.sh      # 初始化部署"
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
STOP_GATEWAY=false
STOP_SAPAS=false
STOP_MIDDLEWARE=false

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

# 默认停止所有服务
if [ -z "$SERVICE" ] || [ "$SERVICE" = "all" ]; then
    STOP_GATEWAY=false
    STOP_SAPAS=false
    STOP_MIDDLEWARE=false
elif [ "$SERVICE" = "gateway" ]; then
    STOP_SAPAS=true
    STOP_MIDDLEWARE=true
elif [ "$SERVICE" = "sapas" ]; then
    STOP_GATEWAY=true
elif [ "$SERVICE" = "backend" ]; then
    STOP_GATEWAY=true
    STOP_MIDDLEWARE=true
    BACKEND_ONLY=true
elif [ "$SERVICE" = "frontend" ]; then
    STOP_GATEWAY=true
    STOP_MIDDLEWARE=true
elif [ "$SERVICE" = "middleware" ]; then
    STOP_GATEWAY=true
    STOP_SAPAS=true
fi

print_banner

# ========================================
# 步骤 1: 停止数据网关（如果需要）
# ========================================
if [ "$STOP_GATEWAY" != true ]; then
    echo -e "${YELLOW}[1/3] 停止数据网关...${NC}"

    # 读取 PID 文件
    if [ -f "$PROJECT_ROOT/logs/gateway.pid" ]; then
        GATEWAY_PID=$(cat "$PROJECT_ROOT/logs/gateway.pid")

        # 检查并终止进程
        if ps -p $GATEWAY_PID > /dev/null 2>&1; then
            kill $GATEWAY_PID 2>/dev/null
            echo -e "${GREEN}[√] 数据网关已停止 (PID: $GATEWAY_PID)${NC}"
        else
            echo -e "${YELLOW}[!] 数据网关进程不存在${NC}"
        fi

        # 删除 PID 文件
        rm -f "$PROJECT_ROOT/logs/gateway.pid"
    else
        echo -e "${YELLOW}[!] 找不到数据网关 PID 文件${NC}"
    fi

    # 检查并停止其他可能的 uvicorn 进程
    if pgrep -f "uvicorn src.main:app" > /dev/null; then
        pkill -f "uvicorn src.main:app"
        echo -e "${GREEN}[√] 已终止遗留的数据网关进程${NC}"
    fi

    echo ""
fi

# ========================================
# 步骤 2: 停止 SAPAS 平台（如果需要）
# ========================================
if [ "$STOP_SAPAS" != true ]; then
    echo -e "${YELLOW}[2/3] 停止 SAPAS 平台...${NC}"

    if [ -n "$BACKEND_ONLY" ]; then
        $DOCKER_COMPOSE -f $COMPOSE_FILE stop backend frontend
    else
        $DOCKER_COMPOSE -f $COMPOSE_FILE stop backend
    fi

    echo -e "${GREEN}[√] SAPAS 平台已停止${NC}"
    echo ""
fi

# ========================================
# 步骤 3: 停止中间件（如果需要）
# ========================================
if [ "$STOP_MIDDLEWARE" != true ]; then
    echo -e "${YELLOW}[3/3] 停止中间件 (PostgreSQL, Redis)...${NC}"

    $DOCKER_COMPOSE -f $COMPOSE_FILE stop postgres redis

    echo -e "${GREEN}[√] 中间件已停止${NC}"
    echo ""
fi

# ========================================
# 完成提示
# ========================================
echo -e "${CYAN}============================================================${NC}"
echo -e "${GREEN}  停止完成！${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""
echo "所有服务已停止。"
echo ""
echo "常用命令："
echo "  查看服务状态: $DOCKER_COMPOSE -f $COMPOSE_FILE ps"
echo "  启动所有服务: ./start.sh"
echo "  启动特定服务: ./start.sh [gateway|sapas|backend|frontend|middleware]"
echo "  初始化部署: ./init-deploy.sh"
echo ""
