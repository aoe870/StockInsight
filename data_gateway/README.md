# Data Gateway Service

独立数据网关服务，为外部平台提供统一的数据接口。

## 功能特性

- 🌍 **多市场支持**: A股、港股、美股、期货、经济指标
- 🔄 **多数据源自动切换**: AKShare (实时) + BaoStock (历史)
- 📡 **多种接口**: HTTP API + Redis 消息队列
- 🐳 **Docker 部署**: 开箱即用
- 📊 **统一数据格式**: 标准化返回

## 快速开始

### 方式一: Docker 部署 (推荐)

```bash
# 1. 克隆项目
cd data_gateway

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f data-gateway

# 4. 访问文档
open http://localhost:8001/docs
```

### 方式二: 本地运行

#### Linux/Mac

```bash
# 1. 安装依赖
bash scripts/start.sh

# 2. 初始化数据库
python scripts/init_db.py

# 3. 启动服务
bash scripts/start.sh
```

#### Windows

```cmd
# 1. 安装依赖
scripts\start.bat

# 2. 初始化数据库
python scripts\init_db.py

# 3. 启动服务
scripts\start.bat
```

## API 使用示例

### 1. 获取A股实时行情

```bash
curl -X POST "http://localhost:8001/api/v1/quote" \
  -H "Content-Type: application/json" \
  -d '{
    "market": "cn_a",
    "symbols": ["000001", "600000"]
  }'
```

响应:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "000001": {
      "symbol": "000001",
      "name": "平安银行",
      "price": 11.23,
      "open": 11.20,
      "high": 11.30,
      "low": 11.15,
      "volume": 12345678,
      "change": 0.05,
      "change_pct": 0.45,
      "timestamp": "2026-01-23 14:35:28",
      "market": "cn_a"
    }
  }
}
```

### 2. 获取K线数据

```bash
curl "http://localhost:8001/api/v1/kline?market=cn_a&symbol=000001&period=daily&start_date=2025-01-01&end_date=2026-01-23"
```

### 3. 健康检查

```bash
curl http://localhost:8001/health
```

## 支持的市场

| 市场 | 代码 | 实时行情 | K线 | 基本面 |
|------|------|---------|-----|--------|
| A股 | `cn_a` | ✅ | ✅ | ✅ |
| 港股 | `hk` | ✅ | ✅ | ❌ |
| 美股 | `us` | ✅ | ✅ | ❌ |
| 期货 | `futures` | ✅ | ✅ | ❌ |
| 经济指标 | `economic` | ❌ | ✅ | ❌ |

## 配置说明

复制 `.env.example` 为 `.env` 并修改配置：

```bash
# 服务配置
DG_HOST=0.0.0.0
DG_PORT=8001

# 数据库
DG_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/data_gateway

# Redis
DG_REDIS_URL=redis://localhost:6379/0
```

## 目录结构

```
data_gateway/
├── src/                    # 源代码
│   ├── main.py            # FastAPI 应用入口
│   ├── config.py          # 配置管理
│   ├── gateway/           # 数据网关
│   │   ├── base.py        # 基类
│   │   ├── manager.py     # 网关管理器
│   │   └── markets/       # 市场实现
│   ├── api/              # API 路由
│   └── utils/            # 工具
├── scripts/              # 脚本
│   ├── start.sh         # Linux/Mac 启动
│   ├── start.bat        # Windows 启动
│   └── init_db.py       # 数据库初始化
├── docker/              # Docker 配置
│   └── Dockerfile
├── docker-compose.yml   # Docker Compose
├── requirements.txt     # Python 依赖
└── README.md           # 本文件
```

## 服务端口

| 服务 | 端口 |
|------|------|
| 数据网关 API | 8001 |
| PostgreSQL | 5432 |
| Redis | 6379 |

## 开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行测试
pytest

# 代码格式化
black src/
```

## Docker 命令

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f data-gateway

# 停止服务
docker-compose down

# 重启服务
docker-compose restart data-gateway

# 进入容器
docker-compose exec data-gateway bash
```

## 扩展开发

### 添加新市场

1. 在 `src/gateway/markets/` 创建新文件
2. 继承 `MarketGateway` 类
3. 实现数据源 `DataSource`
4. 在 `manager.py` 注册新市场

### 添加新数据源

1. 继承 `DataSource` 基类
2. 实现三个方法:
   - `get_quote()`
   - `get_kline()`
   - `get_fundamentals()`
3. 在对应市场网关注册

## 故障排查

### 服务启动失败

```bash
# 检查端口占用
netstat -tulpn | grep 8001

# 查看日志
tail -f logs/data_gateway.log
```

### 数据库连接失败

```bash
# 检查 PostgreSQL
docker-compose ps postgres

# 测试连接
psql -h localhost -U postgres -d data_gateway
```

### 数据获取失败

```bash
# 检查数据源健康
curl http://localhost:8001/health
```

## 许可证

MIT License
