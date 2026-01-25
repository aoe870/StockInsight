-- ============================================================
-- 数据网关服务数据库表结构 (完全独立设计)
-- Database: data_gateway
-- 创建日期: 2026-01-25
-- ============================================================

-- ============================================================
-- 1. 数据源配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS dg_sources (
    source_id SERIAL PRIMARY KEY,
    source_code VARCHAR(50) NOT NULL,                -- 数据源代码 (akshare, baostock, tushare)
    source_name VARCHAR(100) NOT NULL,               -- 数据源名称
    market_code VARCHAR(20) NOT NULL,                -- 市场代码 (cn_a, hk, us, futures, economic)
    data_type VARCHAR(20) NOT NULL,                  -- 数据类型 (quote, kline, fundamental)
    is_enabled BOOLEAN DEFAULT true,                 -- 是否启用
    priority_rank INTEGER DEFAULT 0,                 -- 优先级 (数字越小优先级越高)
    api_config JSONB,                                -- API配置信息
    rate_limit_per_minute INTEGER DEFAULT 120,       -- 每分钟请求限制
    rate_limit_per_hour INTEGER DEFAULT 1000,         -- 每小时请求限制
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_source_market_type UNIQUE (market_code, source_code, data_type)
);

CREATE INDEX IF NOT EXISTS idx_dg_sources_market ON dg_sources(market_code);
CREATE INDEX IF NOT EXISTS idx_dg_sources_enabled ON dg_sources(is_enabled) WHERE is_enabled = true;

-- ============================================================
-- 2. 数据源状态监控表
-- ============================================================
CREATE TABLE IF NOT EXISTS dg_source_monitor (
    monitor_id BIGSERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES dg_sources(source_id) ON DELETE CASCADE,
    health_status VARCHAR(20) NOT NULL,              -- 健康状态 (healthy, degraded, down, unknown)
    success_req_count INTEGER DEFAULT 0,             -- 成功请求数
    fail_req_count INTEGER DEFAULT 0,                -- 失败请求数
    total_req_count INTEGER DEFAULT 0,               -- 总请求数
    avg_resp_time_ms FLOAT DEFAULT 0,                -- 平均响应时间(毫秒)
    last_succ_ts TIMESTAMP,                          -- 最后成功时间戳
    last_fail_ts TIMESTAMP,                          -- 最后失败时间戳
    last_err_msg TEXT,                               -- 最后错误信息
    error_rate_pct FLOAT DEFAULT 0,                  -- 错误率百分比
    check_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,    -- 检查时间戳
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dg_source_monitor_source ON dg_source_monitor(source_id);
CREATE INDEX IF NOT EXISTS idx_dg_source_monitor_check_ts ON dg_source_monitor(check_ts DESC);
CREATE INDEX IF NOT EXISTS idx_dg_source_monitor_status ON dg_source_monitor(health_status);

-- ============================================================
-- 3. API请求日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS dg_api_logs (
    log_id BIGSERIAL PRIMARY KEY,
    req_uuid VARCHAR(50) UNIQUE NOT NULL,             -- 请求UUID
    market_code VARCHAR(20) NOT NULL,                 -- 市场代码
    api_path VARCHAR(200) NOT NULL,                   -- API路径
    http_method VARCHAR(10) NOT NULL,                 -- HTTP方法
    req_params JSONB,                                -- 请求参数
    client_ip VARCHAR(50),                           -- 客户端IP
    user_agent TEXT,                                 -- User Agent
    source_code VARCHAR(50),                         -- 实际使用的数据源代码
    resp_time_ms INTEGER,                            -- 响应时间(毫秒)
    http_status SMALLINT,                            -- HTTP状态码
    resp_size_bytes INTEGER,                         -- 响应大小(字节)
    is_cache_hit BOOLEAN DEFAULT false,              -- 是否命中缓存
    err_msg TEXT,                                    -- 错误信息
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dg_api_logs_market ON dg_api_logs(market_code);
CREATE INDEX IF NOT EXISTS idx_dg_api_logs_path ON dg_api_logs(api_path);
CREATE INDEX IF NOT EXISTS idx_dg_api_logs_ts ON dg_api_logs(created_at_ts DESC);
CREATE INDEX IF NOT EXISTS idx_dg_api_logs_status ON dg_api_logs(http_status);
CREATE INDEX IF NOT EXISTS idx_dg_api_logs_cache ON dg_api_logs(is_cache_hit);
CREATE INDEX IF NOT EXISTS idx_dg_api_logs_uuid ON dg_api_logs(req_uuid);

-- ============================================================
-- 4. 实时行情缓存表
-- ============================================================
CREATE TABLE IF NOT EXISTS dg_cache_quote (
    cache_id BIGSERIAL PRIMARY KEY,
    symbol_code VARCHAR(20) NOT NULL,               -- 代码
    market_code VARCHAR(20) NOT NULL,                -- 市场代码
    quote_data JSONB NOT NULL,                       -- 行情数据
    source_code VARCHAR(50),                        -- 数据来源
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expire_at_ts TIMESTAMP NOT NULL,                 -- 过期时间戳
    CONSTRAINT uk_cache_quote_symbol_market UNIQUE (symbol_code, market_code)
);

CREATE INDEX IF NOT EXISTS idx_dg_cache_quote_symbol ON dg_cache_quote(symbol_code, market_code);
CREATE INDEX IF NOT EXISTS idx_dg_cache_quote_expire ON dg_cache_quote(expire_at_ts);

-- ============================================================
-- 5. K线缓存表（聚合存储 - 已废弃，保留用于兼容）
-- ============================================================
CREATE TABLE IF NOT EXISTS dg_cache_kline (
    cache_id BIGSERIAL PRIMARY KEY,
    symbol_code VARCHAR(20) NOT NULL,               -- 代码
    market_code VARCHAR(20) NOT NULL,                -- 市场代码
    period_type VARCHAR(20) NOT NULL,                -- 周期类型 (1m, 5m, 15m, 30m, 60m, daily, weekly, monthly)
    kline_data JSONB NOT NULL,                      -- K线数据（JSON格式）
    source_code VARCHAR(50),                        -- 数据来源
    date_range JSONB,                              -- 日期范围 {"start": "2026-01-01", "end": "2026-01-23"}
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expire_at_ts TIMESTAMP NOT NULL,                 -- 过期时间戳
    CONSTRAINT uk_cache_kline_symbol_period UNIQUE (symbol_code, market_code, period_type, date_range)
);

CREATE INDEX IF NOT EXISTS idx_dg_cache_kline_symbol ON dg_cache_kline(symbol_code, market_code, period_type);
CREATE INDEX IF NOT EXISTS idx_dg_cache_kline_expire ON dg_cache_kline(expire_at_ts);

-- ============================================================
-- 5.1. 股票日K线数据表（每日一条记录 - 当前使用）
-- ============================================================
CREATE TABLE IF NOT EXISTS dg_stock_daily_k (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,                      -- 股票代码
    trade_date DATE NOT NULL,                       -- 交易日期
    open_price FLOAT,                               -- 开盘价
    close_price FLOAT,                              -- 收盘价
    high_price FLOAT,                               -- 最高价
    low_price FLOAT,                                -- 最低价
    volume BIGINT,                                  -- 成交量（股）
    amount FLOAT,                                   -- 成交额（元）
    change_pct FLOAT,                               -- 涨跌幅(%)
    turnover FLOAT,                                 -- 换手率(%)
    market_code VARCHAR(20) NOT NULL DEFAULT 'cn_a', -- 市场代码
    source_code VARCHAR(50),                        -- 数据来源
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 创建时间
    CONSTRAINT uk_stock_daily_k_code_date UNIQUE (code, trade_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_stock_daily_k_code ON dg_stock_daily_k(code);
CREATE INDEX IF NOT EXISTS idx_stock_daily_k_date ON dg_stock_daily_k(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_stock_daily_k_market ON dg_stock_daily_k(market_code);
CREATE INDEX IF NOT EXISTS idx_stock_daily_k_code_date ON dg_stock_daily_k(code, trade_date DESC);

-- ============================================================
-- 6. 基本面数据缓存表
-- ============================================================
CREATE TABLE IF NOT EXISTS dg_cache_fundamental (
    cache_id BIGSERIAL PRIMARY KEY,
    symbol_code VARCHAR(20) NOT NULL,               -- 代码
    market_code VARCHAR(20) NOT NULL,                -- 市场代码
    fund_data JSONB NOT NULL,                       -- 基本面数据
    source_code VARCHAR(50),                        -- 数据来源
    report_date DATE,                               -- 报告期
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expire_at_ts TIMESTAMP NOT NULL,                 -- 过期时间戳
    CONSTRAINT uk_cache_fundamental_symbol_report UNIQUE (symbol_code, market_code, report_date)
);

CREATE INDEX IF NOT EXISTS idx_dg_cache_fundamental_symbol ON dg_cache_fundamental(symbol_code, market_code);
CREATE INDEX IF NOT EXISTS idx_dg_cache_fundamental_expire ON dg_cache_fundamental(expire_at_ts);

-- ============================================================
-- 7. 限流记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS dg_rate_limits (
    limit_id BIGSERIAL PRIMARY KEY,
    client_key VARCHAR(100) NOT NULL,                -- 客户端标识 (IP或API Key)
    api_path VARCHAR(200) NOT NULL,                  -- API路径
    window_start_ts TIMESTAMP NOT NULL,              -- 时间窗口开始
    req_count INTEGER DEFAULT 0,                     -- 请求数
    is_blocked BOOLEAN DEFAULT false,                -- 是否被阻止
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_rate_limit_client_path_window UNIQUE (client_key, api_path, window_start_ts)
);

CREATE INDEX IF NOT EXISTS idx_dg_rate_limits_client ON dg_rate_limits(client_key, api_path);
CREATE INDEX IF NOT EXISTS idx_dg_rate_limits_window ON dg_rate_limits(window_start_ts);

-- ============================================================
-- 8. 统计汇总表
-- ============================================================
CREATE TABLE IF NOT EXISTS dg_statistics (
    stat_id BIGSERIAL PRIMARY KEY,
    stat_date DATE NOT NULL,                         -- 统计日期
    market_code VARCHAR(20),                         -- 市场代码 (NULL表示全部)
    source_code VARCHAR(50),                         -- 数据源代码 (NULL表示全部)
    total_req_count BIGINT DEFAULT 0,               -- 总请求数
    succ_req_count BIGINT DEFAULT 0,                -- 成功请求数
    fail_req_count BIGINT DEFAULT 0,                -- 失败请求数
    avg_resp_time_ms FLOAT DEFAULT 0,               -- 平均响应时间
    cache_hit_count BIGINT DEFAULT 0,                -- 缓存命中数
    cache_miss_count BIGINT DEFAULT 0,               -- 缓存未命中数
    unique_symbol_count INTEGER DEFAULT 0,           -- 唯一代码数
    unique_client_count INTEGER DEFAULT 0,           -- 唯一客户端数
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_stats_date_market_source UNIQUE (stat_date, market_code, source_code)
);

CREATE INDEX IF NOT EXISTS idx_dg_statistics_date ON dg_statistics(stat_date DESC);
CREATE INDEX IF NOT EXISTS idx_dg_statistics_market ON dg_statistics(market_code);

-- ============================================================
-- 9. 数据质量报告表
-- ============================================================
CREATE TABLE IF NOT EXISTS dg_data_quality (
    quality_id BIGSERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES dg_sources(source_id) ON DELETE CASCADE,
    market_code VARCHAR(20) NOT NULL,
    report_date DATE NOT NULL,
    total_rec_count INTEGER DEFAULT 0,               -- 总记录数
    valid_rec_count INTEGER DEFAULT 0,               -- 有效记录数
    invalid_rec_count INTEGER DEFAULT 0,             -- 无效记录数
    missing_fields JSONB,                          -- 缺失字段统计
    quality_score FLOAT DEFAULT 0,                   -- 数据质量评分 (0-100)
    issues_list JSONB,                             -- 发现的问题列表
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_quality_source_market_date UNIQUE (source_id, market_code, report_date)
);

CREATE INDEX IF NOT EXISTS idx_dg_quality_source_date ON dg_data_quality(source_id, report_date DESC);
CREATE INDEX IF NOT EXISTS idx_dg_quality_market_date ON dg_data_quality(market_code, report_date DESC);

-- ============================================================
-- 10. API密钥管理表
-- ============================================================
CREATE TABLE IF NOT EXISTS dg_api_keys (
    key_id SERIAL PRIMARY KEY,
    key_code VARCHAR(50) UNIQUE NOT NULL,             -- API Key代码
    key_secret VARCHAR(100) NOT NULL,                 -- API Key密钥
    key_name VARCHAR(100) NOT NULL,                   -- 密钥名称
    key_desc TEXT,                                  -- 密钥描述
    is_enabled BOOLEAN DEFAULT true,                  -- 是否启用
    rate_limit_per_min INTEGER DEFAULT 60,           -- 每分钟限制
    rate_limit_per_hr INTEGER DEFAULT 1000,           -- 每小时限制
    allowed_markets JSONB,                         -- 允许访问的市场
    allowed_paths JSONB,                           -- 允许访问的接口
    ip_whitelist JSONB,                            -- IP白名单
    expire_at_ts TIMESTAMP,                         -- 过期时间
    last_used_at_ts TIMESTAMP,                      -- 最后使用时间
    total_req_count BIGINT DEFAULT 0,               -- 总请求数
    created_by VARCHAR(100) DEFAULT 'system',       -- 创建者
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dg_api_keys_code ON dg_api_keys(key_code);
CREATE INDEX IF NOT EXISTS idx_dg_api_keys_enabled ON dg_api_keys(is_enabled) WHERE is_enabled = true;

-- ============================================================
-- 11. Webhook订阅表
-- ============================================================
CREATE TABLE IF NOT EXISTS dg_webhook_subs (
    sub_id SERIAL PRIMARY KEY,
    sub_code VARCHAR(50) UNIQUE NOT NULL,            -- 订阅代码
    webhook_url VARCHAR(500) NOT NULL,               -- Webhook URL
    secret_key VARCHAR(100),                         -- 签名密钥
    is_enabled BOOLEAN DEFAULT true,                  -- 是否启用
    market_code VARCHAR(20) NOT NULL,                 -- 市场代码
    symbol_list JSONB,                              -- 订阅的代码列表 (NULL表示全部)
    event_types JSONB,                              -- 订阅的事件 (quote, kline, etc)
    filter_rules JSONB,                             -- 过滤条件
    retry_policy JSONB,                             -- 重试策略
    last_trig_ts TIMESTAMP,                         -- 最后触发时间
    total_trig_count INTEGER DEFAULT 0,             -- 总触发次数
    fail_trig_count INTEGER DEFAULT 0,              -- 失败次数
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dg_webhook_subs_code ON dg_webhook_subs(sub_code);
CREATE INDEX IF NOT EXISTS idx_dg_webhook_subs_market ON dg_webhook_subs(market_code);
CREATE INDEX IF NOT EXISTS idx_dg_webhook_subs_enabled ON dg_webhook_subs(is_enabled) WHERE is_enabled = true;

-- ============================================================
-- 12. Webhook事件日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS dg_webhook_events (
    event_id BIGSERIAL PRIMARY KEY,
    sub_code VARCHAR(50) NOT NULL,                  -- 订阅代码
    event_type VARCHAR(50) NOT NULL,                 -- 事件类型
    event_data JSONB,                               -- 事件数据
    resp_code INTEGER,                              -- HTTP响应码
    resp_body TEXT,                                 -- 响应内容
    attempt_num INTEGER DEFAULT 1,                  -- 尝试次数
    status VARCHAR(20) NOT NULL,                    -- 状态 (success, failed, pending)
    err_msg TEXT,                                   -- 错误信息
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dg_webhook_events_sub ON dg_webhook_events(sub_code);
CREATE INDEX IF NOT EXISTS idx_dg_webhook_events_status ON dg_webhook_events(status);
CREATE INDEX IF NOT EXISTS idx_dg_webhook_events_ts ON dg_webhook_events(created_at_ts DESC);

-- ============================================================
-- 触发器：自动更新 updated_at_ts
-- ============================================================
CREATE OR REPLACE FUNCTION dg_update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at_ts = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为需要的表添加触发器
CREATE TRIGGER trg_dg_sources_updated_at BEFORE UPDATE ON dg_sources
    FOR EACH ROW EXECUTE FUNCTION dg_update_updated_at();

CREATE TRIGGER trg_dg_source_monitor_updated_at BEFORE UPDATE ON dg_source_monitor
    FOR EACH ROW EXECUTE FUNCTION dg_update_updated_at();

CREATE TRIGGER trg_dg_statistics_updated_at BEFORE UPDATE ON dg_statistics
    FOR EACH ROW EXECUTE FUNCTION dg_update_updated_at();

CREATE TRIGGER trg_dg_api_keys_updated_at BEFORE UPDATE ON dg_api_keys
    FOR EACH ROW EXECUTE FUNCTION dg_update_updated_at();

CREATE TRIGGER trg_dg_webhook_subs_updated_at BEFORE UPDATE ON dg_webhook_subs
    FOR EACH ROW EXECUTE FUNCTION dg_update_updated_at();

-- ============================================================
-- 视图
-- ============================================================

-- 数据源状态汇总视图
CREATE OR REPLACE VIEW v_dg_source_status AS
SELECT
    s.source_id,
    s.source_code,
    s.source_name,
    s.market_code,
    s.data_type,
    s.is_enabled,
    s.priority_rank,
    m.health_status,
    m.success_req_count,
    m.fail_req_count,
    m.total_req_count,
    m.avg_resp_time_ms,
    m.error_rate_pct,
    m.last_succ_ts,
    m.last_fail_ts,
    m.last_err_msg,
    m.check_ts as last_check_ts
FROM dg_sources s
LEFT JOIN LATERAL (
    SELECT *
    FROM dg_source_monitor
    WHERE source_id = s.source_id
    ORDER BY check_ts DESC
    LIMIT 1
) m ON true;

-- 每日API请求统计视图
CREATE OR REPLACE VIEW v_dg_daily_stats AS
SELECT
    DATE(created_at_ts) as stat_date,
    market_code,
    api_path,
    COUNT(*) as total_req,
    COUNT(*) FILTER (WHERE http_status = 200) as succ_req,
    COUNT(*) FILTER (WHERE http_status != 200) as fail_req,
    AVG(resp_time_ms) as avg_resp_ms,
    COUNT(*) FILTER (WHERE is_cache_hit = true) as cache_hit,
    COUNT(*) FILTER (WHERE is_cache_hit = false) as cache_miss,
    COUNT(DISTINCT client_ip) as unique_clients
FROM dg_api_logs
GROUP BY DATE(created_at_ts), market_code, api_path;

-- 缓存效果统计视图
CREATE OR REPLACE VIEW v_dg_cache_stats AS
SELECT
    DATE(created_at_ts) as stat_date,
    'quote' as cache_type,
    COUNT(*) as item_count,
    AVG(EXTRACT(EPOCH FROM (expire_at_ts - created_at_ts))) as avg_ttl_sec
FROM dg_cache_quote
GROUP BY DATE(created_at_ts)
UNION ALL
SELECT
    DATE(created_at_ts) as stat_date,
    'kline' as cache_type,
    COUNT(*) as item_count,
    AVG(EXTRACT(EPOCH FROM (expire_at_ts - created_at_ts))) as avg_ttl_sec
FROM dg_cache_kline
GROUP BY DATE(created_at_ts);

-- ============================================================
-- 初始化数据
-- ============================================================

-- 插入默认数据源配置
INSERT INTO dg_sources (source_code, source_name, market_code, data_type, priority_rank) VALUES
-- A股数据源
('akshare', 'AKShare数据接口', 'cn_a', 'quote', 1),
('akshare', 'AKShare数据接口', 'cn_a', 'kline', 2),
('baostock', 'BaoStock数据接口', 'cn_a', 'kline', 1),
('baostock', 'BaoStock数据接口', 'cn_a', 'fundamental', 1),

-- 港股数据源
('akshare', 'AKShare数据接口', 'hk', 'quote', 1),
('akshare', 'AKShare数据接口', 'hk', 'kline', 1),

-- 美股数据源
('akshare', 'AKShare数据接口', 'us', 'quote', 1),
('akshare', 'AKShare数据接口', 'us', 'kline', 1),

-- 期货数据源
('akshare', 'AKShare数据接口', 'futures', 'quote', 1),
('akshare', 'AKShare数据接口', 'futures', 'kline', 1),

-- 经济指标数据源
('akshare', 'AKShare数据接口', 'economic', 'kline', 1)

ON CONFLICT (market_code, source_code, data_type) DO NOTHING;

-- ============================================================
-- 清理函数
-- ============================================================

-- 清理过期数据的函数
CREATE OR REPLACE FUNCTION dg_cleanup_expired()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    -- 清理过期的行情缓存
    DELETE FROM dg_cache_quote WHERE expire_at_ts < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- 清理过期的K线缓存
    DELETE FROM dg_cache_kline WHERE expire_at_ts < CURRENT_TIMESTAMP;

    -- 清理过期的基本面缓存
    DELETE FROM dg_cache_fundamental WHERE expire_at_ts < CURRENT_TIMESTAMP;

    -- 清理旧的请求日志 (保留30天)
    DELETE FROM dg_api_logs WHERE created_at_ts < CURRENT_TIMESTAMP - INTERVAL '30 days';

    -- 清理旧的限流记录 (保留1天)
    DELETE FROM dg_rate_limits WHERE window_start_ts < CURRENT_TIMESTAMP - INTERVAL '1 day';

    -- 清理旧的Webhook事件日志 (保留7天)
    DELETE FROM dg_webhook_events WHERE created_at_ts < CURRENT_TIMESTAMP - INTERVAL '7 days';

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
