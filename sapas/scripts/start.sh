#!/bin/bash
# SAPAS 本地启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "=========================================="
echo "  SAPAS 本地启动"
echo "=========================================="

# 检查虚拟环境
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo -e "${RED}错误: 后端虚拟环境不存在${NC}"
    echo "请先运行 'scripts/init.sh' 初始化项目"
    exit 1
fi

# 检查前端依赖
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${RED}错误: 前端依赖未安装${NC}"
    echo "请先运行 'scripts/init.sh' 初始化项目"
    exit 1
fi

# 创建日志目录
mkdir -p "$PROJECT_ROOT/logs"

# 启动后端
echo ""
echo -e "${YELLOW}启动后端服务...${NC}"
cd "$BACKEND_DIR"
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8082 --reload > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ 后端已启动 (PID: $BACKEND_PID)${NC}"
echo $BACKEND_PID > "$PROJECT_ROOT/logs/backend.pid"
deactivate

# 启动前端
echo ""
echo -e "${YELLOW}启动前端服务...${NC}"
cd "$FRONTEND_DIR"
nohup npm run dev > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ 前端已启动 (PID: $FRONTEND_PID)${NC}"
echo $FRONTEND_PID > "$PROJECT_ROOT/logs/frontend.pid"

cd "$PROJECT_ROOT"

echo ""
echo "=========================================="
echo -e "${GREEN}✓ 服务已启动${NC}"
echo "=========================================="
echo ""
echo "服务地址："
echo "  后端 API: http://localhost:8082"
echo "  前端页面: http://localhost:5173"
echo "  API 文档: http://localhost:8082/docs"
echo ""
echo "日志文件："
echo "  后端: $PROJECT_ROOT/logs/backend.log"
echo "  前端: $PROJECT_ROOT/logs/frontend.log"
echo ""
echo "停止服务请运行: scripts/stop.sh"
echo ""
