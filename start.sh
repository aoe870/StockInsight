#!/bin/bash
# ============================================================
# SAPAS 启动脚本
# 股票数据分析与处理自动化服务
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 默认配置
BACKEND_PORT=${BACKEND_PORT:-8081}
FRONTEND_PORT=${FRONTEND_PORT:-5173}
HOST=${HOST:-0.0.0.0}
VENV_DIR=".venv"
WEB_DIR="web"

print_banner() {
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}   SAPAS - Stock Analysis Processing Automated Service${NC}"
    echo -e "${CYAN}   股票数据分析与处理自动化服务${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo ""
}

print_banner

# 检查系统 Python
check_python() {
    if command -v python3 > /dev/null 2>&1; then
        PYTHON_BIN=python3
    elif command -v python > /dev/null 2>&1; then
        PYTHON_BIN=python
    else
        echo "[×] 未找到 Python，请先安装 Python 3.11+"
        exit 1
    fi
    echo "[√] 系统 Python: $($PYTHON_BIN --version)"
}

# 创建/激活虚拟环境
setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "[i] 创建虚拟环境: $VENV_DIR"
        $PYTHON_BIN -m venv $VENV_DIR
        echo "[√] 虚拟环境已创建"
    fi

    # 激活虚拟环境
    source "$VENV_DIR/bin/activate"
    PYTHON="$VENV_DIR/bin/python"
    PIP="$VENV_DIR/bin/pip"
    echo "[√] 虚拟环境已激活"
    echo "[√] venv Python: $($PYTHON --version)"
}

# 检查并创建 .env
check_env() {
    if [ ! -f ".env" ]; then
        echo "[!] 未找到 .env 配置文件"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo "[√] 已从 .env.example 复制配置文件"
            echo "[!] 请编辑 .env 文件配置数据库连接"
        fi
    fi
}

# 创建目录
create_dirs() {
    mkdir -p logs
}

# 安装依赖
install_deps() {
    echo "[>] 升级 pip..."
    $PIP install --upgrade pip
    echo "[>] 安装 Python 依赖..."
    $PIP install -r requirements.txt
    echo "[√] 依赖安装完成"
}

# 初始化数据库
init_db() {
    echo "[>] 初始化数据库..."

    # 检查 docker-compose
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        echo "[×] 未找到 docker-compose"
        exit 1
    fi

    # 启动 PostgreSQL 容器
    echo "[>] 启动 PostgreSQL..."
    $COMPOSE_CMD up -d postgres

    # 等待 PostgreSQL 就绪
    echo "[i] 等待 PostgreSQL 就绪..."
    sleep 5

    # 执行 SQL 脚本
    for script in 01_create_tables.sql 02_create_indexes.sql 03_create_functions.sql 04_seed_data.sql; do
        if [ -f "scripts/$script" ]; then
            echo "[>] 执行 $script"
            $COMPOSE_CMD exec -T postgres psql -U root -d sapas_db -f /docker-entrypoint-initdb.d/$script
        fi
    done

    echo "[√] 数据库初始化完成"
}

# 启动后端服务器
start_server() {
    echo -e "${CYAN}[>] 启动后端 API 服务器...${NC}"
    echo -e "${YELLOW}[i] 地址: http://${HOST}:${BACKEND_PORT}${NC}"
    echo -e "${YELLOW}[i] API 文档: http://${HOST}:${BACKEND_PORT}/docs${NC}"
    echo -e "${YELLOW}[i] 健康检查: http://${HOST}:${BACKEND_PORT}/health${NC}"
    echo -e "${YELLOW}[i] 按 Ctrl+C 停止服务${NC}"
    echo ""

    if [ "$1" = "--no-reload" ]; then
        $PYTHON -m uvicorn src.main:app --host $HOST --port $BACKEND_PORT
    else
        $PYTHON -m uvicorn src.main:app --host $HOST --port $BACKEND_PORT --reload
    fi
}

# 启动前端服务器
start_web() {
    echo -e "${CYAN}[>] 启动前端服务器...${NC}"

    if [ ! -d "$WEB_DIR" ]; then
        echo -e "${RED}[×] 前端目录不存在${NC}"
        exit 1
    fi

    cd "$WEB_DIR"

    # 检查 node_modules
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}[i] 安装前端依赖...${NC}"
        npm install
    fi

    echo -e "${YELLOW}[i] 地址: http://localhost:${FRONTEND_PORT}${NC}"
    echo -e "${YELLOW}[i] 按 Ctrl+C 停止服务${NC}"
    echo ""

    npm run dev -- --port $FRONTEND_PORT
}

# 同时启动前后端（开发模式）
start_dev() {
    echo -e "${GREEN}[>] 开发模式: 同时启动前后端${NC}"
    echo ""

    # 启动后端（后台运行）
    echo -e "${CYAN}[>] 启动后端...${NC}"
    $PYTHON -m uvicorn src.main:app --host $HOST --port $BACKEND_PORT --reload &
    BACKEND_PID=$!

    sleep 2

    # 启动前端
    echo -e "${CYAN}[>] 启动前端...${NC}"
    cd "$WEB_DIR"

    if [ ! -d "node_modules" ]; then
        npm install
    fi

    npm run dev -- --port $FRONTEND_PORT &
    FRONTEND_PID=$!

    echo ""
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}  后端运行中: http://${HOST}:${BACKEND_PORT}${NC}"
    echo -e "${GREEN}  前端运行中: http://localhost:${FRONTEND_PORT}${NC}"
    echo -e "${GREEN}  按 Ctrl+C 停止所有服务${NC}"
    echo -e "${GREEN}============================================================${NC}"

    # 捕获退出信号
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
    wait
}

# 显示帮助
show_help() {
    echo -e "${CYAN}用法:${NC} bash start.sh [command] [options]"
    echo ""
    echo -e "${CYAN}命令:${NC}"
    echo -e "  ${GREEN}server${NC}       启动后端 API 服务器 (默认端口: 8081)"
    echo -e "  ${GREEN}web${NC}          启动前端开发服务器 (默认端口: 5173)"
    echo -e "  ${GREEN}dev${NC}          同时启动前后端 (推荐)"
    echo -e "  ${GREEN}install${NC}      安装依赖 (Python + Node.js)"
    echo -e "  ${GREEN}init-db${NC}      初始化数据库 (执行 SQL 脚本)"
    echo -e "  ${GREEN}health${NC}       健康检查 (检查所有服务状态)"
    echo -e "  ${GREEN}help${NC}         显示此帮助信息"
    echo ""
    echo -e "${CYAN}数据同步说明:${NC}"
    echo "  服务启动时自动执行："
    echo "    - 检查并同步股票列表（如果为空）"
    echo "    - 同步自选股的K线数据（如果有缺失）"
    echo ""
    echo "  定时任务（服务运行期间自动执行）："
    echo "    - 盘后同步: 每个交易日 15:30"
    echo "    - 股票列表更新: 每周一 9:00"
    echo "    - 盘中更新: 交易时段每 30 分钟"
    echo ""
    echo -e "${CYAN}环境变量:${NC}"
    echo "  BACKEND_PORT   后端端口 (默认: 8081)"
    echo "  FRONTEND_PORT  前端端口 (默认: 5173)"
    echo "  HOST           服务器地址 (默认: 0.0.0.0)"
    echo ""
    echo -e "${CYAN}快速开始:${NC}"
    echo "  1. bash start.sh install    # 安装依赖"
    echo "  2. bash start.sh init-db    # 初始化数据库"
    echo "  3. bash start.sh dev        # 启动服务（自动同步数据）"
    echo "  4. 打开浏览器访问 http://localhost:5173"
}

# 安装前端依赖
install_web_deps() {
    if [ -d "$WEB_DIR" ]; then
        echo -e "${CYAN}[>] 安装前端依赖...${NC}"
        cd "$WEB_DIR"
        npm install
        cd ..
        echo -e "${GREEN}[√] 前端依赖安装完成${NC}"
    fi
}

# 完整安装
install_all() {
    install_deps
    install_web_deps
}

# 主逻辑
check_python
setup_venv
check_env
create_dirs

case "${1:-help}" in
    server)
        start_server "$2"
        ;;
    web)
        start_web
        ;;
    dev)
        start_dev
        ;;
    install)
        install_all
        ;;
    init-db)
        init_db
        ;;
    health)
        python scripts/health_check.py
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}[×] 未知命令: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

