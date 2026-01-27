# StockInsight
一个完整的股票分析平台项目，包含数据网关和 SAPAS 股票分析平台。

## 项目结构
```
StockInsight/
├── data_gateway/          # 数据网关服务
│   ├── src/
│   ├── models/
│   ├── scripts/
│   ├── main.py
│   ├── Dockerfile
│   └── pyproject.toml
├── sapas/                # SAPAS 股票分析平台
│   ├── backend/             # 后端服务 (FastAPI)
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── core/
│   │   ├── api/
│   │   ├── scripts/
│   │   ├── main.py
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   ├── frontend/            # 前端服务 (Vue 3)
│   │   ├── src/
│   │   ├── Dockerfile
│   │   ├── nginx.conf
│   │   ├── package.json
│   ├── scripts/             # 部署脚本
│   ├── docker-compose.yml
│   └── README.md
├── Makefile               # 项目管理命令
├── init-deploy.sh         # 初始化部署脚本（含数据库初始化）
├── start.sh               # 启动服务脚本
└── README.md              # 项目说明
```

## 快速开始

### 使用根目录脚本（推荐）

```bash
# 初始化部署（首次部署，包含数据库初始化）
./init-deploy.sh

# 启动所有服务（默认，不含数据库初始化）
./start.sh

# 停止所有服务
./stop.sh
```

**脚本选项：**

```bash
# 查看帮助
./start.sh --help

# 启动特定服务
./start.sh gateway      # 仅启动数据网关
./start.sh sapas         # 仅启动 SAPAS（前端+后端）
./start.sh backend       # 仅启动 SAPAS 后端
./start.sh frontend      # 仅启动 SAPAS 前端
./start.sh middleware    # 仅启动中间件（PostgreSQL + Redis）

# 停止特定服务
./stop.sh gateway       # 仅停止数据网关
./stop.sh sapas         # 仅停止 SAPAS
./stop.sh backend       # 仅停止 SAPAS 后端
./stop.sh frontend      # 仅停止 SAPAS 前端
./stop.sh middleware    # 仅停止中间件
```

### 使用 Makefile（项目内管理）

```bash
# 初始化项目
make init

# 启动本地开发服务
make start

# 启动 Docker 环境
make docker-start

# 查看服务状态
make ps

# 查看服务日志
make logs

# 停止服务
make stop
```

## 服务端口

| 服务       | 端口  | 说明           |
|-------------|---------|----------------|
| SAPAS 前端 | 80     | Web 界面       |
| SAPAS 后端 | 8082   | REST API       |
| 数据网关     | 8001   | 数据 API       |
| PostgreSQL  | 5433   | 数据库         |
| Redis      | 6380   | 缓存           |

## 技术栈

### 数据网关
- **框架**: FastAPI (Python)
- **数据库**: MongoDB
- **数据源**: MiNa API

### SAPAS 后端
- **框架**: FastAPI (Python 3.11+)
- **数据库**: PostgreSQL 15
- **缓存**: Redis 7
- **认证**: JWT

### SAPAS 前端
- **框架**: Vue 3
- **语言**: TypeScript
- **构建工具**: Vite
- **UI**: Element Plus
- **图表**: ECharts

## 功能模块

| 模块           | 功能                                      |
|----------------|------------------------------------------|
| 用户管理       | 注册、登录、权限控制                        |
| 行情中心       | 实时行情、指数、板块                        |
| 自选股         | 分组管理、实时报价                        |
| 选股器         | 多条件筛选、导出结果                      |
| 预警管理       | 价格/涨跌幅/成交量预警                      |
| 策略回测       | 策略模板、回测结果                      |
| 集合竞价       | 竞价数据分析                              |

## 环境要求

- **Python**: 3.10+
- **Node.js**: 18+
- **PostgreSQL**: 15+
- **MongoDB**: 6+
- **Redis**: 7+
- **Docker**: 20.10+ (可选)

## 开发指南

### 数据网关开发
```bash
cd data_gateway
pip install -r requirements.txt
python main.py
```

### SAPAS 后端开发
```bash
cd sapas/backend
source venv/bin/activate
uvicorn main:app --reload --port 8082
```

### SAPAS 前端开发
```bash
cd sapas/frontend
npm install
npm run dev
```

## 部署

### Docker 部署
```bash
# 构建镜像
make build

# 启动服务
make docker-start

# 推送镜像
make push DOCKER_USER=yourname
```

### 生产部署
```bash
cd sapas/scripts
./deploy.sh
```

## 许可证

Copyright (c) 2024 StockInsight Team
