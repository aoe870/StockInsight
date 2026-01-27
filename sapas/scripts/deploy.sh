#!/bin/bash
# SAPAS 生产部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================="
echo "  SAPAS 生产部署"
echo "=========================================="

# 环境检查
if [ -z "$DEPLOY_ENV" ]; then
    echo -e "${YELLOW}提示: 设置 DEPLOY_ENV=production 使用生产配置${NC}"
fi

# 进入项目目录
cd "$PROJECT_ROOT"

# 1. 拉取最新代码
echo ""
echo -e "${YELLOW}[1/5] 拉取最新代码...${NC}"
git pull origin main

# 2. 更新后端依赖
echo ""
echo -e "${YELLOW}[2/5] 更新后端依赖...${NC}"
cd backend
source venv/bin/activate
pip install --upgrade pip
uv pip install -e .

# 3. 数据库迁移
echo ""
echo -e "${YELLOW}[3/5] 执行数据库迁移...${NC}"
python scripts/init_db.py

deactivate
cd "$PROJECT_ROOT"

# 4. 构建前端
echo ""
echo -e "${YELLOW}[4/5] 构建前端...${NC}"
cd frontend
npm ci
npm run build
cd "$PROJECT_ROOT"

# 5. 重启服务
echo ""
echo -e "${YELLOW}[5/5] 重启服务...${NC}"

if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    echo "使用 Docker 部署..."
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d --build
    else
        docker compose up -d --build
    fi
else
    echo "使用 systemd 服务部署..."
    sudo systemctl restart sapas-backend
    sudo systemctl restart sapas-frontend
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✓ 部署完成${NC}"
echo "=========================================="
echo ""
echo "服务地址："
echo "  前端: http://$(hostname -I | awk '{print $1}')"
echo "  后端: http://$(hostname -I | awk '{print $1}'):8082"
echo ""
