#!/bin/bash
# SAPAS 数据库迁移脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "=========================================="
echo "  SAPAS 数据库迁移"
echo "=========================================="

cd "$BACKEND_DIR"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo -e "${RED}错误: 虚拟环境不存在${NC}"
    exit 1
fi

# 运行迁移
echo -e "${YELLOW}执行数据库迁移...${NC}"
python scripts/init_db.py

echo ""
echo "=========================================="
echo -e "${GREEN}✓ 数据库迁移完成${NC}"
echo "=========================================="

deactivate
