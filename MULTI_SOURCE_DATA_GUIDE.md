# 多数据源架构指南

## 概述

为解决 AKShare 实时数据延迟问题（3-15分钟），本系统采用多数据源架构，支持：

1. **自动切换**：主数据源失败时自动切换到备用数据源
2. **优先级管理**：按数据延迟和稳定性排序
3. **失败重试**：连续失败后暂时禁用，定期恢复
4. **性能监控**：记录响应时间和成功率
5. **数据缓存**：短期缓存减少请求频率

---

## 数据源配置

### 已实现数据源

| 数据源 | 优先级 | 延迟 | 成本 | 状态 |
|--------|--------|------|------|------|
| 新浪财经 | REALTIME (1) | 1-3秒 | 免费 | ✅ 已实现 |
| 腾讯财经 | REALTIME (1) | 1-3秒 | 免费 | ✅ 已实现 |
| AKShare | FALLBACK (4) | 3-15分钟 | 免费 | ✅ 已实现 |

### 可扩展数据源

| 数据源 | 优先级 | 延迟 | 成本 | 实现难度 |
|--------|--------|------|------|----------|
| Tushare Pro | MINUTE (2) | 实时 | 120次/分钟免费 | 低 |
| 网易财经 | REALTIME (1) | 1-3秒 | 免费 | 低 |
| 东方财富 | REALTIME (1) | 1-3秒 | 免费 | 低 |
| 聚宽 | MINUTE (2) | 实时 | 有免费额度 | 中 |
| 米筐 | MINUTE (2) | 实时 | 有免费额度 | 中 |

---

## 快速开始

### 1. 安装依赖

```bash
pip install aiohttp akshare
```

### 2. 初始化数据源

```python
# src/main.py
from src.services.multi_source import init_data_sources, multi_source_manager

@app.on_event("startup")
async def startup_event():
    # 初始化多数据源
    init_data_sources()

    # 健康检查
    status = await multi_source_manager.health_check_all()
    logger.info(f"Data sources health: {status}")
```

### 3. 使用示例

```python
from src.services.multi_source import multi_source_manager

# 获取实时行情（自动选择最优数据源）
@router.get("/api/stocks/realtime")
async def get_realtime_quotes(codes: List[str]):
    quotes = await multi_source_manager.get_realtime_quote(codes)
    return {"data": quotes}

# 获取分钟K线
@router.get("/api/stocks/{code}/minute")
async def get_minute_kline(code: str):
    klines = await multi_source_manager.get_minute_kline(code)
    return {"data": klines}

# 查看数据源状态
@router.get("/api/data-sources/status")
async def get_source_status():
    return multi_source_manager.get_source_status()
```

---

## 数据源状态监控

### 状态字段说明

```json
{
  "SinaFinance": {
    "priority": "REALTIME",
    "available": true,
    "success_rate": "95.5%",
    "success_count": 200,
    "fail_count": 10,
    "avg_response_time": "150ms",
    "last_success": "2026-01-23T14:30:00",
    "last_error": null
  }
}
```

### 监控端点

```bash
# 查看所有数据源状态
curl http://localhost:8081/api/data-sources/status

# 健康检查
curl http://localhost:8081/api/data-sources/health
```

---

## 数据获取策略

### 实时行情策略

```
1. 请求到达
2. 检查缓存 (5秒TTL)
3. 缓存命中 → 返回缓存数据
4. 缓存未命中 → 按优先级尝试数据源
   - 优先级 1: 新浪财经、腾讯财经
   - 优先级 2: (待添加) Tushare
   - 优先级 3: (待添加) 网易财经
   - 优先级 4: AKShare (备用)
5. 成功 → 缓存并返回
6. 失败 → 尝试下一个数据源
7. 全部失败 → 返回错误
```

### 历史数据策略

```
日K线数据:
1. 优先使用 AKShare (数据最完整)
2. 备用: 腾讯财经
3. 最后: 新浪财经 (历史数据有限)

分钟K线数据:
1. 优先使用 腾讯财经
2. 备用: AKShare
```

---

## 配置文件

### .env 配置

```bash
# 数据源配置
DATA_SOURCE_DEFAULT=auto  # auto, sina, tencent, akshare
DATA_SOURCE_CACHE_TTL=5   # 缓存有效期(秒)
DATA_SOURCE_TIMEOUT=5     # 请求超时(秒)

# 数据源开关
DATA_SOURCE_SINA_ENABLED=true
DATA_SOURCE_TENCENT_ENABLED=true
DATA_SOURCE_AKSHARE_ENABLED=true

# Tushare 配置 (可选)
TUSHARE_TOKEN=your_token_here
TUSHARE_ENABLED=false
```

### config.py 配置

```python
# src/config/data_source.py
from pydantic_settings import BaseSettings

class DataSourceSettings(BaseSettings):
    # 默认数据源
    default_source: str = "auto"
    cache_ttl: int = 5
    request_timeout: int = 5

    # 数据源开关
    sina_enabled: bool = True
    tencent_enabled: bool = True
    akshare_enabled: bool = True
    tushare_enabled: bool = False
    tushare_token: str = ""

    class Config:
        env_prefix = "DATA_SOURCE_"

settings = DataSourceSettings()
```

---

## 添加新数据源

### 1. 创建数据源类

```python
# src/services/multi_source/sources/tushare_source.py
from ..data_source_base import DataSourceBase, DataSourcePriority

class TushareSource(DataSourceBase):
    def __init__(self, token: str):
        super().__init__(
            name="Tushare",
            priority=DataSourcePriority.MINUTE
        )
        self.token = token
        self.api = ts.pro_api(token)

    async def get_realtime_quote(self, codes: List[str]) -> Dict[str, Any]:
        # 实现 Tushare 实时行情获取
        pass
```

### 2. 注册数据源

```python
# src/services/multi_source/sources/__init__.py
from .tushare_source import TushareSource

def init_data_sources():
    # ... 现有数据源

    # 添加 Tushare（如果配置了 token）
    if settings.tushare_enabled and settings.tushare_token:
        multi_source_manager.register_source(
            TushareSource(settings.tushare_token)
        )
```

---

## 性能优化建议

### 1. 批量请求优化

```python
# 一次获取多只股票
codes = ["000001", "000002", "600000", "600036"]
quotes = await multi_source_manager.get_realtime_quote(codes)
```

### 2. WebSocket 推送

```python
# 对于需要秒级更新的场景，使用 WebSocket 推送
# 而不是轮询
from src.services.websocket import broadcast_manager

async def push_realtime_quotes():
    while True:
        quotes = await multi_source_manager.get_realtime_quote(watch_list)
        await broadcast_manager.broadcast("quotes", quotes)
        await asyncio.sleep(2)  # 2秒推送一次
```

### 3. Redis 缓存

```python
# 使用 Redis 缓存热点数据
import redis

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

async def get_realtime_with_cache(codes: List[str]):
    cache_key = f"realtime:{','.join(sorted(codes))}"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    data = await multi_source_manager.get_realtime_quote(codes)
    redis_client.setex(cache_key, 5, json.dumps(data))  # 5秒过期
    return data
```

---

## 故障处理

### 数据源不可用

系统会自动：
1. 记录失败次数
2. 连续失败3次后暂时禁用
3. 切换到备用数据源
4. 定期恢复尝试

### 限流处理

```python
# 添加请求速率限制
from asyncio import Semaphore

rate_limiter = Semaphore(10)  # 最多10个并发请求

async def get_with_rate_limit(codes: List[str]):
    async with rate_limiter:
        return await multi_source_manager.get_realtime_quote(codes)
```

---

## 成本对比

| 方案 | 月成本 | 优势 | 劣势 |
|------|--------|------|------|
| 纯免费组合 | ¥0 | 无成本 | 延迟较高 |
| + Tushare 免费版 | ¥0 | 实时数据 | 120次/分钟限制 |
| + Tushare 高级版 | ¥2000/年 | 更快更全 | 有成本 |
| + 聚宽/米筐 | ¥500+/月 | 专业级 | 成本高 |

**推荐方案**：
- 开发/测试：纯免费组合（新浪+腾讯+AKShare）
- 生产环境：免费组合 + Tushare 免费版

---

## 测试

```bash
# 测试所有数据源
pytest tests/test_multi_source.py

# 健康检查
curl http://localhost:8081/api/data-sources/health

# 手动测试
python -m src.services.multi_source.test_sources
```

---

## 常见问题

### Q1: 为什么新浪财经返回空数据？

A: 新浪财经有请求频率限制，建议：
1. 添加请求间隔
2. 使用多个数据源轮换
3. 添加缓存

### Q2: 实时数据还是有延迟？

A: 免费数据源通常有1-5秒延迟，如需更低延迟：
1. 使用 WebSocket 推送
2. 考虑付费数据源（Tushare Pro）

### Q3: 如何提高并发性能？

A:
1. 使用异步请求
2. 添加连接池
3. 使用 Redis 缓存
4. 批量获取数据
