# SAPAS - Stock Analysis Processing Automated Service

股票数据分析与处理自动化服务

## 系统概述

SAPAS 是一个全功能的股票分析平台，提供：

- 📊 **实时行情**: 股票实时报价、分时图、K线图
- 📈 **技术指标**: MA、MACD、KDJ、RSI、BOLL 等多种技术指标
- 🔔 **价格告警**: 自定义价格和技术指标告警
- 💰 **回测系统**: 基于Backtrader的策略回测
- 📰 **选股器**: 技术指标选股
- 💹 **集合竞价**: 集合竞价数据分析
- 📱 **资金流向**: 个股资金流向分析

## 技术栈

### 后端
- **框架**: FastAPI (Python 3.11+)
- **数据库**: PostgreSQL 15+
- **缓存**: Redis 7+
- **任务调度**: APScheduler
- **数据源**: AKShare

### 前端
- **框架**: Vue 3 + TypeScript
- **UI**: Element Plus
- **图表**: ECharts 5.6
- **构建**: Vite 6

## 快速开始

### 方式一：使用启动脚本（推荐 Linux/Mac）

```bash
# 1. 安装依赖
bash start.sh install

# 2. 初始化数据库
bash start.sh init-db

# 3. 启动服务（开发模式）
bash start.sh dev
```

### 方式二：手动启动（Windows）

#### 1. 启动数据库服务

```bash
# 使用 Docker Compose
docker-compose up -d postgres redis

# 验证服务状态
docker-compose ps
```

#### 2. 配置环境变量

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env 文件，修改数据库连接信息
# DATABASE_URL=postgresql+asyncpg://root:J7aXgk2BJUj=@localhost:5432/sapas_db
# REDIS_URL=redis://localhost:6379/0
```

#### 3. 安装 Python 依赖

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 4. 初始化数据库

```bash
# 执行数据库脚本
# Windows: 使用 psql 命令或 Docker
docker exec -i postgres15 psql -U root -d sapas_db -f scripts/01_create_tables.sql
docker exec -i postgres15 psql -U root -d sapas_db -f scripts/02_create_indexes.sql
docker exec -i postgres15 psql -U root -d sapas_db -f scripts/03_create_functions.sql
docker exec -i postgres15 psql -U root -d sapas_db -f scripts/04_seed_data.sql

# 或使用 docker-compose（推荐）
docker-compose exec -T postgres psql -U root -d sapas_db -f /docker-entrypoint-initdb.d/01_create_tables.sql
docker-compose exec -T postgres psql -U root -d sapas_db -f /docker-entrypoint-initdb.d/02_create_indexes.sql
docker-compose exec -T postgres psql -U root -d sapas_db -f /docker-entrypoint-initdb.d/03_create_functions.sql
docker-compose exec -T postgres psql -U root -d sapas_db -f /docker-entrypoint-initdb.d/04_seed_data.sql
```

#### 5. 安装前端依赖

```bash
cd web
npm install
cd ..
```

#### 6. 启动后端服务

```bash
# 激活虚拟环境后
python -m uvicorn src.main:app --host 0.0.0.0 --port 8081 --reload
```

#### 7. 启动前端服务

```bash
cd web
npm run dev -- --port 5173
```

#### 8. 访问应用

- 前端: http://localhost:5173
- 后端 API: http://localhost:8081
- API 文档: http://localhost:8081/docs
- 健康检查: http://localhost:8081/health

## 默认账户

- 用户名: `admin`
- 密码: `admin123`

## 目录结构

```
StockInsight/
├── src/                    # 后端源代码
│   ├── api/               # API 路由
│   ├── core/              # 核心功能
│   ├── models/            # 数据模型
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # 业务逻辑
│   └── main.py            # 应用入口
├── web/                   # 前端源代码
│   ├── src/               # Vue 组件
│   ├── public/            # 静态资源
│   └── package.json       # 前端依赖
├── scripts/               # SQL 脚本
│   ├── 01_create_tables.sql
│   ├── 02_create_indexes.sql
│   ├── 03_create_functions.sql
│   └── 04_seed_data.sql
├── docker-compose.yml     # Docker 编排
├── .env.example           # 环境变量示例
├── requirements.txt       # Python 依赖
└── start.sh               # 启动脚本
```

## 数据同步

服务启动时会自动执行：

1. 检查并同步股票列表（如果为空）
2. 同步自选股的K线数据（如果有缺失）

定时任务（服务运行期间自动执行）：

- 盘后数据同步: 每个交易日 15:30
- 股票列表更新: 每周一 9:00
- 盘中数据更新: 交易时段每 30 分钟

手动同步数据：

```bash
# 同步股票列表
curl -X POST http://localhost:8081/api/stocks/sync/list

# 同步指定股票的 K 线数据
curl -X POST http://localhost:8081/api/stocks/000001/sync/kline?adjust=qfq

# 同步自选股 K 线数据
curl -X POST http://localhost:8081/api/watchlist/sync-klines
```

## 常见问题

### 1. 数据库连接失败

检查 PostgreSQL 服务是否运行：

```bash
docker-compose ps
docker-compose logs postgres
```

### 2. Redis 连接失败

检查 Redis 服务是否运行：

```bash
docker-compose ps
docker-compose logs redis
```

### 3. 前端无法访问后端

检查 `.env` 中的 `CORS_ORIGINS` 配置是否包含前端地址。

### 4. MA 均线不显示

确认后端 API 返回的是数字格式而不是字符串。在浏览器控制台检查网络请求的响应。

### 5. 数据同步失败

- 检查网络连接
- 查看后端日志确认错误信息
- AKShare 可能有访问限制，建议在交易时段外同步

## 开发指南

### 添加新的 API 端点

1. 在 `src/api/` 中创建或修改路由文件
2. 在 `src/schemas/` 中定义请求/响应模型
3. 在 `src/services/` 中实现业务逻辑

### 添加新的前端页面

1. 在 `web/src/views/` 中创建 Vue 组件
2. 在 `web/src/router/index.ts` 中添加路由
3. 在 `web/src/api/` 中添加 API 调用

### 运行测试

```bash
# 后端测试
pytest

# 前端测试（如果配置了）
cd web
npm run test
```

## 生产部署

### 构建 Docker 镜像

```bash
# 构建前端
cd web
npm run build
cd ..

# 使用 Docker Compose 部署
docker-compose up -d
```

### 配置 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/web/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://localhost:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://localhost:8081;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 许可证

MIT License

## 联系方式

- 项目地址: [GitHub URL]
- 问题反馈: [Issues URL]
