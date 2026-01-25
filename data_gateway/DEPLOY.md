# 数据网关服务部署指南

## 目录

- [环境变量配置](#环境变量配置)
- [Docker 部署](#docker-部署)
- [本地运行](#本地运行)
- [配置说明](#配置说明)
- [故障排查](#故障排查)

---

## 环境变量配置

### 必需配置

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `DG_DATABASE_URL` | 异步数据库连接 URL | `postgresql+asyncpg://user:pass@host:5432/data_gateway` |

### 可选配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DG_HOST` | 服务监听地址 | `0.0.0.0` |
| `DG_PORT` | 服务端口 | `8001` |
| `DG_DEBUG` | 调试模式 | `false` |
| `DG_LOG_LEVEL` | 日志级别 | `INFO` |
| `DG_REDIS_URL` | Redis 连接 URL | `redis://localhost:6379/0` |
| `DG_MIANA_TOKEN` | Miana 平台 Token | - |
| `DG_AKSHARE_ENABLED` | 启用 AKShare | `true` |
| `DG_BAOSTOCK_ENABLED` | 启用 BaoStock | `true` |

---

## Docker 部署

### 1. 使用 docker-compose（推荐）

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: postgres15
    environment:
      POSTGRES_USER: your_user
      POSTGRES_PASSWORD: your_password
      POSTGRES_DB: data_gateway
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: redis7
    ports:
      - "6379:6379"

  data-gateway:
    image: 1172749335/lion:latest
    container_name: data-gateway
    ports:
      - "8001:8001"
    environment:
      # 必需配置
      - DG_DATABASE_URL=postgresql+asyncpg://your_user:your_password@postgres:5432/data_gateway
      # 可选配置
      - DG_HOST=0.0.0.0
      - DG_PORT=8001
      - DG_DEBUG=false
      - DG_REDIS_URL=redis://redis:6379/0
      - DG_MIANA_TOKEN=your_miana_token_here
      - DG_LOG_LEVEL=INFO
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
```

启动服务：

```bash
docker-compose up -d
```

### 2. 使用 docker run 命令

#### 基础启动

```bash
docker run -d \
  --name data-gateway \
  -p 8001:8001 \
  -e DG_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/data_gateway \
  1172749335/lion:latest
```

#### 完整启动（含所有配置）

```bash
docker run -d \
  --name data-gateway \
  --network your-network \
  -p 8001:8001 \
  -v /path/to/logs:/app/logs \
  -e DG_HOST=0.0.0.0 \
  -e DG_PORT=8001 \
  -e DG_DEBUG=false \
  -e DG_LOG_LEVEL=INFO \
  -e DG_DATABASE_URL=postgresql+asyncpg://root:password@postgres:5432/data_gateway \
  -e DG_REDIS_URL=redis://redis:6379/0 \
  -e DG_MIANA_TOKEN=your_token_here \
  -e DG_AKSHARE_ENABLED=true \
  -e DG_BAOSTOCK_ENABLED=true \
  -e DG_CACHE_TTL_REALTIME=5 \
  -e DG_CACHE_TTL_KLINE=60 \
  1172749335/lion:latest
```

#### 使用 .env 文件启动

```bash
# 创建配置文件
cat > dg.env <<EOF
DG_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/data_gateway
DG_REDIS_URL=redis://host:6379/0
DG_MIANA_TOKEN=your_token_here
EOF

# 使用 --env-file 加载配置
docker run -d \
  --name data-gateway \
  -p 8001:8001 \
  --env-file dg.env \
  1172749335/lion:latest
```

### 3. 使用 docker secrets（生产环境推荐）

对于生产环境，建议使用 Docker Secrets 来管理敏感信息：

```yaml
version: '3.8'

services:
  data-gateway:
    image: 1172749335/lion:latest
    secrets:
      - db_password
      - miana_token
    environment:
      - DG_DATABASE_URL=postgresql+asyncpg://user:file:/run/secrets/db_password@postgres:5432/data_gateway
      - DG_MIANA_TOKEN=file:/run/secrets/miana_token

secrets:
  db_password:
    file: ./secrets/db_password.txt
  miana_token:
    file: ./secrets/miana_token.txt
```

---

## 本地运行

启动脚本位于项目根目录，从根目录执行即可。

### Linux/Mac

```bash
# 1. 进入项目根目录
cd /path/to/StockInsight

# 2. 复制配置模板
cp data_gateway/.env.example .env

# 3. 编辑配置文件
vim .env  # 或使用其他编辑器

# 4. 使用启动脚本（从根目录执行）
chmod +x start_data_gateway.sh
./start_data_gateway.sh
```

### Windows

```cmd
REM 1. 进入项目根目录
cd D:\Develop\StockInsight

REM 2. 复制配置模板
copy data_gateway\.env.example .env

REM 3. 编辑配置文件
notepad .env

REM 4. 使用启动脚本（从根目录执行）
start_data_gateway.bat
```

---

## 配置说明

### Miana Token 配置

Miana 是商业数据平台，需要获取 Token 才能使用其高级功能：

1. 访问 https://miana.com.cn 注册账号
2. 登录后获取 API Token
3. 在环境变量中设置 `DG_MIANA_TOKEN`

**Miana 提供的数据**：
- 实时五档盘口数据
- 详细资金流向（大单、中单、小单分类）
- 行业板块、概念板块实时行情

### 数据源优先级

数据网关会按以下优先级获取数据：

1. **Miana** - 如果配置了 Token，优先使用 Miana 获取实时数据
2. **AKShare** - 备用实时数据源
3. **BaoStock** - 主要用于历史数据

---

## 故障排查

### 服务启动失败

**问题**: 容器启动后立即退出

```bash
# 查看容器日志
docker logs data-gateway

# 进入容器调试
docker exec -it data-gateway sh
```

**常见原因**：
1. `DG_DATABASE_URL` 未设置或格式错误
2. 数据库连接失败
3. 端口被占用

### 数据库连接失败

**问题**: 数据库连接超时

```bash
# 测试数据库连接
docker exec -it data-gateway sh
psql $DG_DATABASE_SYNC_URL
```

**解决方案**：
1. 检查数据库是否运行
2. 检查网络连接
3. 确认用户名密码正确

### 数据获取失败

**问题**: API 返回空数据

```bash
# 检查服务健康状态
curl http://localhost:8001/health

# 检查日志
docker logs data-gateway --tail 50
```

**可能原因**：
1. 数据源网络不可达
2. Token 配置错误（Miana）
3. 请求被限流

---

## API 测试

服务启动后，可以访问：

- **API 文档**: http://localhost:8001/docs
- **健康检查**: http://localhost:8001/health

快速测试：

```bash
# 获取实时行情
curl -X POST http://localhost:8001/api/v1/quote \
  -H "Content-Type: application/json" \
  -d '{"market": "cn_a", "symbols": ["600519"]}'

# 获取 K 线数据
curl "http://localhost:8001/api/v1/kline?market=cn_a&symbol=600519&period=daily&start_date=2026-01-01&end_date=2026-01-26"
```
