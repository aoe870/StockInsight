# 数据网关服务 - 数据库设计文档

## 数据库概述

数据网关服务使用独立的 `data_gateway` 数据库，与 SAPAS 主系统的 `sapas_db` 完全分离。

### 数据库对比

| 数据库 | 用途 | 主要表 |
|--------|------|--------|
| **sapas_db** | SAPAS主系统 | stocks, users, backtests, alerts |
| **data_gateway** | 数据网关服务 | data_sources, request_logs, *_cache, api_keys |

---

## 核心表结构

### 1. 数据源管理

**data_sources** - 数据源配置
- 管理AKShare、BaoStock等数据源
- 支持动态启用/禁用
- 优先级配置

**data_source_status** - 数据源状态
- 实时健康监控
- 成功率、响应时间统计
- 错误率追踪

### 2. 请求日志

**request_logs** - API请求日志
- 记录所有API调用
- 性能分析
- 缓存命中率统计

### 3. 缓存表

**quote_cache** - 实时行情缓存
- TTL: 5秒
- 减少外部API调用

**kline_cache** - K线缓存
- TTL: 60秒
- 支持多周期

**fundamental_cache** - 基本面缓存
- TTL: 1小时
- 财务数据缓存

### 4. 管理表

**api_keys** - API密钥管理
- 外部平台调用认证
- 限流配置
- 权限控制

**rate_limits** - 限流记录
- 防止API滥用
- 支持多级限流

**webhook_subscriptions** - Webhook订阅
- 实时数据推送
- 事件订阅管理

**statistics** - 统计汇总
- 每日统计数据
- 性能指标

---

## 数据库初始化

```bash
# 执行初始化脚本
python scripts/init_db.py
```

该脚本会：
1. 创建 `data_gateway` 数据库
2. 执行 `scripts/sql/01_create_tables.sql` (建表)
3. 执行 `scripts/sql/02_create_functions.sql` (创建函数)
4. 验证安装

---

## 核心函数

| 函数 | 功能 |
|------|------|
| `log_request()` | 记录API请求日志 |
| `update_source_status()` | 更新数据源健康状态 |
| `save_quote_cache()` | 保存行情到缓存 |
| `get_quote_cache()` | 从缓存获取行情 |
| `check_rate_limit()` | 检查限流状态 |
| `validate_api_key()` | 验证API密钥 |
| `cleanup_old_data()` | 清理过期数据 |

---

## 视图

| 视图 | 功能 |
|------|------|
| `v_data_source_status` | 数据源状态汇总 |
| `v_daily_request_stats` | 每日请求统计 |
| `v_cache_stats` | 缓存效果统计 |

---

## 维护命令

```sql
-- 查看数据源状态
SELECT * FROM v_data_source_status;

-- 查看今日请求统计
SELECT * FROM v_daily_request_stats
WHERE stat_date = CURRENT_DATE;

-- 清理过期数据
SELECT cleanup_old_data(30);

-- 禁用数据源
UPDATE data_sources SET enabled = false WHERE source_name = 'akshare';
```

---

## 与 SAPAS 系统集成

```
SAPAS 主系统 ──HTTP──▶ 数据网关服务 ──▶ AKShare/BaoStock
                      │
                      ▼
                data_gateway 数据库
                (缓存/日志/监控)
```

数据网关服务不存储完整的股票历史数据，只缓存最近的数据用于提高性能。
