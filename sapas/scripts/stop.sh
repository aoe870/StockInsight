#!/bin/bash
# SAPAS 停止脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================="
echo "  SAPAS 停止服务"
echo "=========================================="

# 停止后端
if [ -f "$PROJECT_ROOT/logs/backend.pid" ]; then
    BACKEND_PID=$(cat "$PROJECT_ROOT/logs/backend.pid")
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        kill $BACKEND_PID
        echo -e "${GREEN}✓ 后端已停止 (PID: $BACKEND_PID)${NC}"
    else
        echo -e "${YELLOW}后端进程不存在${NC}"
    fi
    rm -f "$PROJECT_ROOT/logs/backend.pid"
else
    # 尝试查找并停止 uvicorn 进程
    UVICORN_PID=$(pgrep -f "uvicorn main:app" || true)
    if [ -n "$UVICORN_PID" ]; then
        kill $UVICORN_PID
        echo -e "${GREEN}✓ 后端已停止 (PID: $UVICORN_PID)${NC}"
    else
        echo -e "${YELLOW}未找到后端进程${NC}"
    fi
fi

# 停止前端
if [ -f "$PROJECT_ROOT/logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat "$PROJECT_ROOT/logs/frontend.pid")
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        kill $FRONTEND_PID
        echo -e "${GREEN}✓ 前端已停止 (PID: $FRONTEND_PID)${NC}"
    else
        echo -e "${YELLOW}前端进程不存在${NC}"
    fi
    rm -f "$PROJECT_ROOT/logs/frontend.pid"
else
    # 尝试查找并停止 Vite 进程
    VITE_PID=$(pgrep -f "vite.*5173" || true)
    if [ -n "$VITE_PID" ]; then
        kill $VITE_PID
        echo -e "${GREEN}✓ 前端已停止 (PID: $VITE_PID)${NC}"
    else
        echo -e "${YELLOW}未找到前端进程${NC}"
    fi
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✓ 所有服务已停止${NC}"
echo "=========================================="
echo ""
