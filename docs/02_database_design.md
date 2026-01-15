# SAPAS 数据库设计文档

## 1. 数据库概述

- **数据库类型**: PostgreSQL 14+
- **字符集**: UTF-8
- **时区**: Asia/Shanghai

## 2. 表结构设计

### 2.1 股票基础信息表 (stock_basics)

存储所有A股股票的基本信息。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| code | VARCHAR(10) | 股票代码 | PRIMARY KEY |
| name | VARCHAR(50) | 股票名称 | NOT NULL |
| industry | VARCHAR(50) | 所属行业板块 | - |
| list_date | DATE | 上市日期 | - |
| market | VARCHAR(10) | 市场 (SH/SZ/BJ) | NOT NULL |
| is_active | BOOLEAN | 是否正常交易 | DEFAULT TRUE |
| created_at | TIMESTAMP | 创建时间 | DEFAULT NOW() |
| updated_at | TIMESTAMP | 更新时间 | DEFAULT NOW() |

### 2.2 日线行情表 (stock_daily_k)

存储股票日K线数据，支持前复权/后复权/不复权。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BIGSERIAL | 自增ID | PRIMARY KEY |
| code | VARCHAR(10) | 股票代码 | NOT NULL, FK |
| trade_date | DATE | 交易日期 | NOT NULL |
| open_price | DECIMAL(12,4) | 开盘价 | - |
| close_price | DECIMAL(12,4) | 收盘价 | - |
| high_price | DECIMAL(12,4) | 最高价 | - |
| low_price | DECIMAL(12,4) | 最低价 | - |
| volume | BIGINT | 成交量(股) | - |
| amount | DECIMAL(18,4) | 成交额(元) | - |
| adjust_type | VARCHAR(10) | 复权类型 | NOT NULL |
| change_pct | DECIMAL(12,4) | 涨跌幅% | - |
| turnover | DECIMAL(12,4) | 换手率% | - |
| created_at | TIMESTAMP | 创建时间 | DEFAULT NOW() |

**联合唯一索引**: (code, trade_date, adjust_type)

### 2.3 用户表 (users)

支持多用户的自选股和订阅管理。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | UUID | 用户ID | PRIMARY KEY |
| username | VARCHAR(50) | 用户名 | UNIQUE, NOT NULL |
| email | VARCHAR(100) | 邮箱地址 | UNIQUE |
| password_hash | VARCHAR(255) | 密码哈希 | NOT NULL |
| notify_channel | VARCHAR(20) | 默认通知渠道 | DEFAULT 'console' |
| is_active | BOOLEAN | 是否激活 | DEFAULT TRUE |
| created_at | TIMESTAMP | 创建时间 | DEFAULT NOW() |
| updated_at | TIMESTAMP | 更新时间 | DEFAULT NOW() |

### 2.4 自选股表 (watchlist_items)

用户的自选股列表。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BIGSERIAL | 自增ID | PRIMARY KEY |
| user_id | UUID | 用户ID | NOT NULL, FK |
| stock_code | VARCHAR(10) | 股票代码 | NOT NULL, FK |
| note | TEXT | 用户备注 | - |
| sort_order | INTEGER | 排序顺序 | DEFAULT 0 |
| added_at | TIMESTAMP | 添加时间 | DEFAULT NOW() |

**联合唯一索引**: (user_id, stock_code)

### 2.5 告警规则表 (alert_rules)

定义各类告警触发条件。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BIGSERIAL | 规则ID | PRIMARY KEY |
| stock_code | VARCHAR(10) | 股票代码 (NULL=全局) | FK |
| rule_type | VARCHAR(30) | 规则类型 | NOT NULL |
| rule_name | VARCHAR(100) | 规则名称 | NOT NULL |
| conditions | JSONB | 触发条件配置 | NOT NULL |
| is_enabled | BOOLEAN | 是否启用 | DEFAULT TRUE |
| cooldown_minutes | INTEGER | 冷却时间(分钟) | DEFAULT 60 |
| created_by | UUID | 创建人 | FK |
| created_at | TIMESTAMP | 创建时间 | DEFAULT NOW() |
| updated_at | TIMESTAMP | 更新时间 | DEFAULT NOW() |

**rule_type 枚举值**:
- `PRICE_BREAKOUT` - 价格突破
- `MA_CROSS` - 均线交叉
- `MACD_SIGNAL` - MACD信号
- `RSI_EXTREME` - RSI极值
- `VOLUME_SURGE` - 成交量异动
- `BOLLINGER_BREAK` - 布林带突破

### 2.6 订阅表 (subscriptions)

用户对告警规则的订阅关系。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BIGSERIAL | 订阅ID | PRIMARY KEY |
| user_id | UUID | 用户ID | NOT NULL, FK |
| rule_id | BIGINT | 规则ID | NOT NULL, FK |
| channel | VARCHAR(20) | 通知渠道 | NOT NULL |
| channel_config | JSONB | 渠道配置 | - |
| is_active | BOOLEAN | 是否激活 | DEFAULT TRUE |
| created_at | TIMESTAMP | 创建时间 | DEFAULT NOW() |

**channel 枚举值**: `console`, `email`, `webhook`, `wechat`
**联合唯一索引**: (user_id, rule_id, channel)

### 2.7 告警历史表 (alert_history)

记录所有触发的告警。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BIGSERIAL | 记录ID | PRIMARY KEY |
| rule_id | BIGINT | 规则ID | NOT NULL, FK |
| stock_code | VARCHAR(10) | 股票代码 | NOT NULL |
| alert_type | VARCHAR(30) | 告警类型 | NOT NULL |
| alert_data | JSONB | 告警详情 | NOT NULL |
| triggered_at | TIMESTAMP | 触发时间 | DEFAULT NOW() |

### 2.8 数据同步日志表 (sync_logs)

记录数据同步状态，支持增量更新。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BIGSERIAL | 日志ID | PRIMARY KEY |
| sync_type | VARCHAR(30) | 同步类型 | NOT NULL |
| stock_code | VARCHAR(10) | 股票代码 (可选) | - |
| start_date | DATE | 同步起始日期 | - |
| end_date | DATE | 同步结束日期 | - |
| records_count | INTEGER | 同步记录数 | - |
| status | VARCHAR(20) | 状态 | NOT NULL |
| error_message | TEXT | 错误信息 | - |
| started_at | TIMESTAMP | 开始时间 | DEFAULT NOW() |
| finished_at | TIMESTAMP | 结束时间 | - |

## 3. 索引策略

详见 `scripts/02_create_indexes.sql`

## 4. 分区策略 (可选)

对于 `stock_daily_k` 表，当数据量超过 1000 万条时，建议按年份进行分区。

