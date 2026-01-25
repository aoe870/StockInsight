#!/bin/bash
# 数据网关服务启动脚本 (Linux/Mac)

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# 默认配置
HOST=${DG_HOST:-0.0.0.0}
PORT=${DG_PORT:-8001}
WORKERS=${DG_WORKERS:-1}

print_banner() {
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}   Data Gateway Service - 数据网关服务${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo ""
}

print_banner

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[X] 未找到 Python3，请先安装${NC}"
    exit 1
fi
echo -e "${GREEN}[√] Python: $(python3 --version)${NC}"

# 安装依赖
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}[i] 创建虚拟环境...${NC}"
    python3 -m venv venv
fi

echo -e "${YELLOW}[i] 激活虚拟环境...${NC}"
source venv/bin/activate

echo -e "${YELLOW}[i] 安装依赖...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[i] 创建 .env 文件...${NC}"
    cat > .env << EOF
# 服务配置
DG_HOST=0.0.0.0
DG_PORT=8001
DG_DEBUG=true

# 数据库配置
DG_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/data_gateway
DG_DATABASE_SYNC_URL=postgresql://postgres:postgres@localhost:5432/data_gateway

# Redis 配置
DG_REDIS_URL=redis://localhost:6379/0

# 日志配置
DG_LOG_LEVEL=INFO
DG_LOG_FILE=logs/data_gateway.log
EOF
fi

# 创建日志目录
mkdir -p logs

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  服务启动中...${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "${YELLOW}[i] 服务地址: http://${HOST}:${PORT}${NC}"
echo -e "${YELLOW}[i] API 文档: http://${HOST}:${PORT}/docs${NC}"
echo ""

# 启动服务
if [ "$WORKERS" = "1" ]; then
    python -m uvicorn src.main:app --host $HOST --port $PORT --reload
else
    # 多worker模式
    python -m uvicorn src.main:app --host $HOST --port $PORT --workers $WORKERS
fi
