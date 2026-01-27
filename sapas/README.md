# SAPAS 股票分析平台

一个完整的股票分析平台，包含用户管理、自选股、选股器、预警、回测等核心功能。

## 技术架构

### 后端
- **框架**: FastAPI (Python 3.11+)
- **数据库**: PostgreSQL 15
- **缓存**: Redis 7
- **认证**: JWT (JSON Web Tokens)
- **数据来源**: 数据网关 API (独立服务)

### 前端
- **框架**: Vue 3.4
- **语言**: TypeScript
- **构建工具**: Vite
- **UI 组件**: Element Plus
- **图表**: ECharts
- **状态管理**: Pinia
- **路由**: Vue Router

## 目录结构

```
sapas/
├── backend/                 # 后端代码
│   ├── models/             # 数据库模型
│   ├── schemas/            # Pydantic 验证模型
│   ├── core/               # 核心服务
│   ├── api/                # API 路由
│   ├── scripts/            # 数据库脚本
│   ├── main.py             # 应用入口
│   ├── pyproject.toml      # Python 依赖配置
│   ├── .env.example        # 环境变量示例
│   └── Dockerfile         # Docker 镜像构建
├── frontend/              # 前端代码
│   ├── src/
│   │   ├── api/          # API 客户端
│   │   ├── components/   # 公共组件
│   │   ├── layouts/      # 布局组件
│   │   ├── router/       # 路由配置
│   │   ├── stores/       # Pinia 状态
│   │   ├── types/        # TypeScript 类型
│   │   ├── utils/        # 工具函数
│   │   ├── views/        # 页面组件
│   │   └── styles/       # 全局样式
│   ├── package.json       # Node.js 依赖
│   ├── vite.config.ts     # Vite 配置
│   ├── nginx.conf         # Nginx 配置
│   └── Dockerfile        # Docker 镜像构建
├── scripts/              # 部署脚本
│   ├── init.sh          # Linux/Mac 初始化
│   ├── start.sh         # Linux/Mac 启动
│   ├── stop.sh          # Linux/Mac 停止
│   ├── docker-start.sh  # Linux/Mac Docker 启动
│   ├── docker-stop.sh   # Linux/Mac Docker 停止
│   ├── db-migrate.sh   # 数据库迁移
│   ├── deploy.sh       # 生产部署
│   ├── init.bat       # Windows 初始化
│   ├── start.bat      # Windows 启动
│   ├── docker-start.bat # Windows Docker 启动
│   └── docker-stop.bat  # Windows Docker 停止
├── docker-compose.yml   # Docker Compose 配置
└── README.md          # 项目说明
```

## 快速开始

### 方式一：本地开发

#### 1. 初始化项目

**Windows:**
```cmd
cd sapas
scripts\init.bat
```

**Linux/Mac:**
```bash
cd sapas
chmod +x scripts/*.sh
./scripts/init.sh
```

初始化脚本会：
- 创建 Python 虚拟环境并安装依赖
- 创建 Node.js 环境并安装依赖
- 复制 `.env.example` 到 `.env`
- 初始化数据库

#### 2. 配置环境变量

编辑 `backend/.env` 文件，配置数据库连接等信息：

```env
# 数据库配置
DATABASE_URL=postgresql+asyncpg://sapas:sapas_password@localhost:5432/sapas

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# 数据网关地址
DATA_GATEWAY_URL=http://localhost:8001

# JWT 密钥 (生产环境请修改)
JWT_SECRET_KEY=your-secret-key-change-in-production

# CORS 配置
CORS_ORIGINS=http://localhost:5173,http://localhost:80
```

#### 3. 启动服务

**Windows:**
```cmd
scripts\start.bat
```

**Linux/Mac:**
```bash
./scripts/start.sh
```

服务启动后访问：
- 前端: http://localhost:5173
- 后端 API: http://localhost:8082
- API 文档: http://localhost:8082/docs

### 方式二：Docker 部署

#### 1. 启动服务

**Windows:**
```cmd
cd sapas
scripts\docker-start.bat
```

**Linux/Mac:**
```bash
cd sapas
./scripts/docker-start.sh
```

#### 2. 访问服务

- 前端: http://localhost
- 后端 API: http://localhost:8082
- API 文档: http://localhost:8082/docs

#### 3. 停止服务

**Windows:**
```cmd
scripts\docker-stop.bat
```

**Linux/Mac:**
```bash
./scripts/docker-stop.sh
```

### 方式三：生产部署

```bash
# 配置环境变量
export DEPLOY_ENV=production

# 执行部署脚本
./scripts/deploy.sh
```

## 数据库迁移

```bash
# Linux/Mac
./scripts/db-migrate.sh

# Windows (手动执行)
cd backend
venv\Scripts\activate
python scripts\init_db.py
```

## 功能模块

| 模块 | 功能 |
|------|------|
| **用户管理** | 注册、登录、权限控制、个人中心 |
| **行情中心** | 实时行情、指数、板块、个股详情 |
| **自选股** | 分组管理、添加删除、实时报价 |
| **选股器** | 多条件筛选、保存条件、导出结果 |
| **预警管理** | 价格/涨跌幅/成交量/资金流向预警 |
| **策略回测** | 策略模板、参数配置、回测结果 |
| **集合竞价** | 竞价数据、筛选分析 |

## 开发指南

### 后端开发

```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装新依赖
uv pip install package-name

# 运行开发服务器
uvicorn main:app --reload --host 0.0.0.0 --port 8082

# 运行测试
pytest
```

### 前端开发

```bash
cd frontend

# 安装新依赖
npm install package-name

# 运行开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 环境要求

- **Python**: 3.10+
- **Node.js**: 18+
- **PostgreSQL**: 15+
- **Redis**: 7+
- **Docker** (可选): 20.10+
- **Docker Compose** (可选): 2.0+

## 注意事项

1. **数据网关**: 确保数据网关服务正常运行（默认端口 8001）
2. **数据库**: 首次运行需要初始化数据库
3. **环境变量**: 生产环境务必修改 `JWT_SECRET_KEY` 等敏感配置
4. **防火墙**: 确保端口 80、8082、5433、6380 可访问

## 常见问题

### 1. 数据库连接失败
检查 `backend/.env` 中的 `DATABASE_URL` 是否正确，确保数据库服务已启动。

### 2. 跨域错误
检查 `CORS_ORIGINS` 配置是否包含前端访问地址。

### 3. WebSocket 连接失败
确保 nginx 配置正确代理了 `/ws` 路径。

## 许可证

Copyright © 2024 SAPAS Team
