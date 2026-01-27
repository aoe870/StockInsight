#!/bin/bash
# SAPAS 初始化脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  SAPAS 股票分析平台 - 初始化脚本"
echo "=========================================="

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo ""
echo -e "${GREEN}项目根目录: $PROJECT_ROOT${NC}"

# 检查 Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: 未安装 Docker${NC}"
        echo "请先安装 Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}错误: 未安装 Docker Compose${NC}"
        echo "请先安装 Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi

    echo -e "${GREEN}✓ Docker 检查通过${NC}"
}

# 检查 Python
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}错误: 未安装 Python 3${NC}"
        exit 1
    fi

    local python_version=$(python3 --version | awk '{print $2}')
    local major=$(echo $python_version | cut -d. -f1)
    local minor=$(echo $python_version | cut -d. -f2)

    if [ "$major" -lt 3 ] || [ "$major" -eq 3 -a "$minor" -lt 10 ]; then
        echo -e "${RED}错误: Python 版本需要 3.10 或以上${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Python 检查通过 ($python_version)${NC}"
}

# 检查 Node.js
check_node() {
    if ! command -v node &> /dev/null; then
        echo -e "${RED}错误: 未安装 Node.js${NC}"
        exit 1
    fi

    local node_version=$(node --version)
    echo -e "${GREEN}✓ Node.js 检查通过 ($node_version)${NC}"
}

# 初始化后端
init_backend() {
    echo ""
    echo "=========================================="
    echo "  初始化后端"
    echo "=========================================="

    cd "$BACKEND_DIR"

    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}创建 Python 虚拟环境...${NC}"
        python3 -m venv venv
        echo -e "${GREEN}✓ 虚拟环境已创建${NC}"
    fi

    # 激活虚拟环境
    source venv/bin/activate

    # 安装依赖
    echo -e "${YELLOW}安装 Python 依赖...${NC}"
    pip install --upgrade pip
    pip install uv
    uv pip install -e .
    echo -e "${GREEN}✓ Python 依赖已安装${NC}"

    # 创建 .env 文件
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}创建 .env 文件...${NC}"
        cp .env.example .env
        echo -e "${GREEN}✓ .env 文件已创建，请修改其中的配置${NC}"
    else
        echo -e "${GREEN}✓ .env 文件已存在${NC}"
    fi

    # 初始化数据库
    echo -e "${YELLOW}初始化数据库...${NC}"
    python scripts/init_db.py
    echo -e "${GREEN}✓ 数据库初始化完成${NC}"

    deactivate
}

# 初始化前端
init_frontend() {
    echo ""
    echo "=========================================="
    echo "  初始化前端"
    echo "=========================================="

    cd "$FRONTEND_DIR"

    # 安装依赖
    echo -e "${YELLOW}安装 Node.js 依赖...${NC}"
    npm install
    echo -e "${GREEN}✓ Node.js 依赖已安装${NC}"
}

# 主流程
main() {
    check_docker
    check_python
    check_node

    # 初始化后端
    init_backend

    # 初始化前端
    init_frontend

    echo ""
    echo "=========================================="
    echo -e "${GREEN}✓ 初始化完成！${NC}"
    echo "=========================================="
    echo ""
    echo "后续步骤："
    echo "  1. 编辑 $BACKEND_DIR/.env 配置数据库连接"
    echo "  2. 运行 'scripts/start.sh' 启动服务"
    echo "  3. 运行 'scripts/docker-start.sh' 启动 Docker 环境"
    echo ""
}

main "$@"
