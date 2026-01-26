-- ============================================================
-- 数据网关服务数据库完整初始化脚本
-- Database: data_gateway
-- 创建日期: 2026-01-26
-- ============================================================

-- 连接到 postgres 数据库执行此脚本

-- ============================================================
-- 1. 创建数据库
-- ============================================================
-- 删除已存在的数据库（谨慎使用！）
-- DROP DATABASE IF EXISTS data_gateway;

-- 创建数据库
CREATE DATABASE data_gateway
    ENCODING 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE template0;

-- 切换到 data_gateway 数据库执行后续命令
-- \c data_gateway

-- ============================================================
-- 以下命令需要在 data_gateway 数据库中执行
-- ============================================================

-- ============================================================
-- 2. 数据表
-- ============================================================

-- 2.1 数据源配置表
CREATE TABLE IF NOT EXISTS dg_sources (
    source_id SERIAL PRIMARY KEY,
    source_code VARCHAR(50) NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    market_code VARCHAR(20) NOT NULL,
    data_type VARCHAR(20) NOT NULL,
    is_enabled BOOLEAN DEFAULT true,
    priority_rank INTEGER DEFAULT 0,
    api_config JSONB,
    rate_limit_per_minute INTEGER DEFAULT 120,
    rate_limit_per_hour INTEGER DEFAULT 1000,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_source_market_type UNIQUE (market_code, source_code, data_type)
);

CREATE INDEX IF NOT EXISTS idx_dg_sources_market ON dg_sources(market_code);
CREATE INDEX IF NOT EXISTS idx_dg_sources_enabled ON dg_sources(is_enabled) WHERE is_enabled = true;

-- 2.2 数据源状态监控表
CREATE TABLE IF NOT EXISTS dg_source_monitor (
    monitor_id BIGSERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES dg_sources(source_id) ON DELETE CASCADE,
    health_status VARCHAR(20) NOT NULL,
    success_req_count INTEGER DEFAULT 0,
    fail_req_count INTEGER DEFAULT 0,
    total_req_count INTEGER DEFAULT 0,
    avg_resp_time_ms FLOAT DEFAULT 0,
    last_succ_ts TIMESTAMP,
    last_fail_ts TIMESTAMP,
    last_err_msg TEXT,
    error_rate_pct FLOAT DEFAULT 0,
    check_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dg_source_monitor_source ON dg_source_monitor(source_id);
CREATE INDEX IF NOT EXISTS idx_dg_source_monitor_check_ts ON dg_source_monitor(check_ts DESC);
CREATE INDEX IF NOT EXISTS idx_dg_source_monitor_status ON dg_source_monitor(health_status);

-- 2.3 API请求日志表
CREATE TABLE IF NOT EXISTS dg_api_logs (
    log_id BIGSERIAL PRIMARY KEY,
    req_uuid VARCHAR(50) UNIQUE NOT NULL,
    market_code VARCHAR(20) NOT NULL,
    api_path VARCHAR(200) NOT NULL,
    http_method VARCHAR(10) NOT NULL,
    req_params JSONB,
    client_ip VARCHAR(50),
    user_agent TEXT,
    source_code VARCHAR(50),
    resp_time_ms INTEGER,
    http_status SMALLINT,
    resp_size_bytes INTEGER,
    is_cache_hit BOOLEAN DEFAULT false,
    err_msg TEXT,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dg_api_logs_market ON dg_api_logs(market_code);
CREATE INDEX IF NOT EXISTS idx_dg_api_logs_path ON dg_api_logs(api_path);
CREATE INDEX IF NOT EXISTS idx_dg_api_logs_ts ON dg_api_logs(created_at_ts DESC);
CREATE INDEX IF NOT EXISTS idx_dg_api_logs_status ON dg_api_logs(http_status);
CREATE INDEX IF NOT EXISTS idx_dg_api_logs_cache ON dg_api_logs(is_cache_hit);
CREATE INDEX IF NOT EXISTS idx_dg_api_logs_uuid ON dg_api_logs(req_uuid);

-- 2.4 实时行情缓存表
CREATE TABLE IF NOT EXISTS dg_cache_quote (
    cache_id BIGSERIAL PRIMARY KEY,
    symbol_code VARCHAR(20) NOT NULL,
    market_code VARCHAR(20) NOT NULL,
    quote_data JSONB NOT NULL,
    source_code VARCHAR(50),
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expire_at_ts TIMESTAMP NOT NULL,
    CONSTRAINT uk_cache_quote_symbol_market UNIQUE (symbol_code, market_code)
);

CREATE INDEX IF NOT EXISTS idx_dg_cache_quote_symbol ON dg_cache_quote(symbol_code, market_code);
CREATE INDEX IF NOT EXISTS idx_dg_cache_quote_expire ON dg_cache_quote(expire_at_ts);

-- 2.5 K线缓存表（聚合存储 - 已废弃，保留用于兼容）
CREATE TABLE IF NOT EXISTS dg_cache_kline (
    cache_id BIGSERIAL PRIMARY KEY,
    symbol_code VARCHAR(20) NOT NULL,
    market_code VARCHAR(20) NOT NULL,
    period_type VARCHAR(20) NOT NULL,
    kline_data JSONB NOT NULL,
    source_code VARCHAR(50),
    date_range JSONB,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expire_at_ts TIMESTAMP NOT NULL,
    CONSTRAINT uk_cache_kline_symbol_period UNIQUE (symbol_code, market_code, period_type, date_range)
);

CREATE INDEX IF NOT EXISTS idx_dg_cache_kline_symbol ON dg_cache_kline(symbol_code, market_code, period_type);
CREATE INDEX IF NOT EXISTS idx_dg_cache_kline_expire ON dg_cache_kline(expire_at_ts);

-- 2.5.1 股票日K线数据表（每日一条记录 - 当前使用）
CREATE TABLE IF NOT EXISTS dg_stock_daily_k (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open_price FLOAT,
    close_price FLOAT,
    high_price FLOAT,
    low_price FLOAT,
    volume BIGINT,
    amount FLOAT,
    change_pct FLOAT,
    turnover FLOAT,
    market_code VARCHAR(20) NOT NULL DEFAULT 'cn_a',
    source_code VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_stock_daily_k_code_date UNIQUE (code, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_stock_daily_k_code ON dg_stock_daily_k(code);
CREATE INDEX IF NOT EXISTS idx_stock_daily_k_date ON dg_stock_daily_k(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_stock_daily_k_market ON dg_stock_daily_k(market_code);
CREATE INDEX IF NOT EXISTS idx_stock_daily_k_code_date ON dg_stock_daily_k(code, trade_date DESC);

-- 2.6 基本面数据缓存表
CREATE TABLE IF NOT EXISTS dg_cache_fundamental (
    cache_id BIGSERIAL PRIMARY KEY,
    symbol_code VARCHAR(20) NOT NULL,
    market_code VARCHAR(20) NOT NULL,
    fund_data JSONB NOT NULL,
    source_code VARCHAR(50),
    report_date DATE,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expire_at_ts TIMESTAMP NOT NULL,
    CONSTRAINT uk_cache_fundamental_symbol_report UNIQUE (symbol_code, market_code, report_date)
);

CREATE INDEX IF NOT EXISTS idx_dg_cache_fundamental_symbol ON dg_cache_fundamental(symbol_code, market_code);
CREATE INDEX IF NOT EXISTS idx_dg_cache_fundamental_expire ON dg_cache_fundamental(expire_at_ts);

-- 2.7 限流记录表
CREATE TABLE IF NOT EXISTS dg_rate_limits (
    limit_id BIGSERIAL PRIMARY KEY,
    client_key VARCHAR(100) NOT NULL,
    api_path VARCHAR(200) NOT NULL,
    window_start_ts TIMESTAMP NOT NULL,
    req_count INTEGER DEFAULT 0,
    is_blocked BOOLEAN DEFAULT false,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_rate_limit_client_path_window UNIQUE (client_key, api_path, window_start_ts)
);

CREATE INDEX IF NOT EXISTS idx_dg_rate_limits_client ON dg_rate_limits(client_key, api_path);
CREATE INDEX IF NOT EXISTS idx_dg_rate_limits_window ON dg_rate_limits(window_start_ts);

-- 2.8 统计汇总表
CREATE TABLE IF NOT EXISTS dg_statistics (
    stat_id BIGSERIAL PRIMARY KEY,
    stat_date DATE NOT NULL,
    market_code VARCHAR(20),
    source_code VARCHAR(50),
    total_req_count BIGINT DEFAULT 0,
    succ_req_count BIGINT DEFAULT 0,
    fail_req_count BIGINT DEFAULT 0,
    avg_resp_time_ms FLOAT DEFAULT 0,
    cache_hit_count BIGINT DEFAULT 0,
    cache_miss_count BIGINT DEFAULT 0,
    unique_symbol_count INTEGER DEFAULT 0,
    unique_client_count INTEGER DEFAULT 0,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_stats_date_market_source UNIQUE (stat_date, market_code, source_code)
);

CREATE INDEX IF NOT EXISTS idx_dg_statistics_date ON dg_statistics(stat_date DESC);
CREATE INDEX IF NOT EXISTS idx_dg_statistics_market ON dg_statistics(market_code);

-- 2.9 数据质量报告表
CREATE TABLE IF NOT EXISTS dg_data_quality (
    quality_id BIGSERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES dg_sources(source_id) ON DELETE CASCADE,
    market_code VARCHAR(20) NOT NULL,
    report_date DATE NOT NULL,
    total_rec_count INTEGER DEFAULT 0,
    valid_rec_count INTEGER DEFAULT 0,
    invalid_rec_count INTEGER DEFAULT 0,
    missing_fields JSONB,
    quality_score FLOAT DEFAULT 0,
    issues_list JSONB,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_quality_source_market_date UNIQUE (source_id, market_code, report_date)
);

CREATE INDEX IF NOT EXISTS idx_dg_quality_source_date ON dg_data_quality(source_id, report_date DESC);
CREATE INDEX IF NOT EXISTS idx_dg_quality_market_date ON dg_data_quality(market_code, report_date DESC);

-- 2.10 API密钥管理表
CREATE TABLE IF NOT EXISTS dg_api_keys (
    key_id SERIAL PRIMARY KEY,
    key_code VARCHAR(50) UNIQUE NOT NULL,
    key_secret VARCHAR(100) NOT NULL,
    key_name VARCHAR(100) NOT NULL,
    key_desc TEXT,
    is_enabled BOOLEAN DEFAULT true,
    rate_limit_per_min INTEGER DEFAULT 60,
    rate_limit_per_hr INTEGER DEFAULT 1000,
    allowed_markets JSONB,
    allowed_paths JSONB,
    ip_whitelist JSONB,
    expire_at_ts TIMESTAMP,
    last_used_at_ts TIMESTAMP,
    total_req_count BIGINT DEFAULT 0,
    created_by VARCHAR(100) DEFAULT 'system',
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dg_api_keys_code ON dg_api_keys(key_code);
CREATE INDEX IF NOT EXISTS idx_dg_api_keys_enabled ON dg_api_keys(is_enabled) WHERE is_enabled = true;

-- 2.11 Webhook订阅表
CREATE TABLE IF NOT EXISTS dg_webhook_subs (
    sub_id SERIAL PRIMARY KEY,
    sub_code VARCHAR(50) UNIQUE NOT NULL,
    webhook_url VARCHAR(500) NOT NULL,
    secret_key VARCHAR(100),
    is_enabled BOOLEAN DEFAULT true,
    market_code VARCHAR(20) NOT NULL,
    symbol_list JSONB,
    event_types JSONB,
    filter_rules JSONB,
    retry_policy JSONB,
    last_trig_ts TIMESTAMP,
    total_trig_count INTEGER DEFAULT 0,
    fail_trig_count INTEGER DEFAULT 0,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dg_webhook_subs_code ON dg_webhook_subs(sub_code);
CREATE INDEX IF NOT EXISTS idx_dg_webhook_subs_market ON dg_webhook_subs(market_code);
CREATE INDEX IF NOT EXISTS idx_dg_webhook_subs_enabled ON dg_webhook_subs(is_enabled) WHERE is_enabled = true;

-- 2.12 Webhook事件日志表
CREATE TABLE IF NOT EXISTS dg_webhook_events (
    event_id BIGSERIAL PRIMARY KEY,
    sub_code VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB,
    resp_code INTEGER,
    resp_body TEXT,
    attempt_num INTEGER DEFAULT 1,
    status VARCHAR(20) NOT NULL,
    err_msg TEXT,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dg_webhook_events_sub ON dg_webhook_events(sub_code);
CREATE INDEX IF NOT EXISTS idx_dg_webhook_events_status ON dg_webhook_events(status);
CREATE INDEX IF NOT EXISTS idx_dg_webhook_events_ts ON dg_webhook_events(created_at_ts DESC);

-- 2.13 同步任务主表
CREATE TABLE IF NOT EXISTS dg_sync_tasks (
    task_id VARCHAR(50) PRIMARY KEY,
    sync_type VARCHAR(20) NOT NULL,
    market_code VARCHAR(20) NOT NULL,
    period_type VARCHAR(20) DEFAULT 'daily',
    start_date DATE,
    end_date DATE,
    symbols JSONB,
    total_symbols INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL,
    progress INTEGER DEFAULT 0,
    current_symbol VARCHAR(20),
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    total_records INTEGER DEFAULT 0,
    error_message TEXT,
    result JSONB,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at_ts TIMESTAMP,
    completed_at_ts TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dg_sync_tasks_status ON dg_sync_tasks(status);
CREATE INDEX IF NOT EXISTS idx_dg_sync_tasks_market ON dg_sync_tasks(market_code);
CREATE INDEX IF NOT EXISTS idx_dg_sync_tasks_created ON dg_sync_tasks(created_at_ts DESC);

-- 2.14 同步任务明细表
CREATE TABLE IF NOT EXISTS dg_sync_task_items (
    item_id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(50) REFERENCES dg_sync_tasks(task_id) ON DELETE CASCADE,
    symbol_code VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    records_count INTEGER DEFAULT 0,
    date_range VARCHAR(50),
    error_message TEXT,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dg_sync_task_items_task ON dg_sync_task_items(task_id);
CREATE INDEX IF NOT EXISTS idx_dg_sync_task_items_symbol ON dg_sync_task_items(symbol_code);

-- 2.15 同步配置表
CREATE TABLE IF NOT EXISTS dg_sync_config (
    config_id SERIAL PRIMARY KEY,
    market_code VARCHAR(20) NOT NULL UNIQUE,
    auto_sync_enabled BOOLEAN DEFAULT false,
    sync_frequency VARCHAR(20) DEFAULT 'daily',
    sync_hour INTEGER DEFAULT 0,
    sync_minute INTEGER DEFAULT 0,
    default_period VARCHAR(20) DEFAULT 'daily',
    retention_days INTEGER DEFAULT 365,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2.16 同步日志表
CREATE TABLE IF NOT EXISTS dg_sync_logs (
    log_id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(50),
    market_code VARCHAR(20) NOT NULL,
    log_level VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    details JSONB,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dg_sync_logs_task ON dg_sync_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_dg_sync_logs_created ON dg_sync_logs(created_at_ts DESC);

-- ============================================================
-- 3. 函数
-- ============================================================

-- 3.1 自动更新 updated_at_ts 的函数
CREATE OR REPLACE FUNCTION dg_update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at_ts = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3.2 清理过期数据的函数
CREATE OR REPLACE FUNCTION dg_cleanup_expired()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    DELETE FROM dg_cache_quote WHERE expire_at_ts < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    DELETE FROM dg_cache_kline WHERE expire_at_ts < CURRENT_TIMESTAMP;
    DELETE FROM dg_cache_fundamental WHERE expire_at_ts < CURRENT_TIMESTAMP;
    DELETE FROM dg_api_logs WHERE created_at_ts < CURRENT_TIMESTAMP - INTERVAL '30 days';
    DELETE FROM dg_rate_limits WHERE window_start_ts < CURRENT_TIMESTAMP - INTERVAL '1 day';
    DELETE FROM dg_webhook_events WHERE created_at_ts < CURRENT_TIMESTAMP - INTERVAL '7 days';

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 3.3 记录API请求日志
CREATE OR REPLACE FUNCTION dg_log_request(
    p_req_uuid VARCHAR,
    p_market_code VARCHAR,
    p_api_path VARCHAR,
    p_http_method VARCHAR,
    p_req_params JSONB,
    p_client_ip VARCHAR,
    p_user_agent TEXT,
    p_source_code VARCHAR,
    p_resp_time_ms INTEGER,
    p_http_status SMALLINT,
    p_resp_size_bytes INTEGER,
    p_is_cache_hit BOOLEAN,
    p_err_msg TEXT
) RETURNS BIGINT AS $$
DECLARE
    v_log_id BIGINT;
BEGIN
    INSERT INTO dg_api_logs (
        req_uuid, market_code, api_path, http_method, req_params,
        client_ip, user_agent, source_code, resp_time_ms,
        http_status, resp_size_bytes, is_cache_hit, err_msg
    ) VALUES (
        p_req_uuid, p_market_code, p_api_path, p_http_method, p_req_params,
        p_client_ip, p_user_agent, p_source_code, p_resp_time_ms,
        p_http_status, p_resp_size_bytes, p_is_cache_hit, p_err_msg
    ) RETURNING log_id INTO v_log_id;

    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- 3.4 更新数据源状态
CREATE OR REPLACE FUNCTION dg_update_source_status(
    p_source_id INTEGER,
    p_health_status VARCHAR,
    p_is_success BOOLEAN,
    p_resp_time_ms FLOAT,
    p_err_msg TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO dg_source_monitor (
        source_id, health_status, success_req_count, fail_req_count,
        total_req_count, avg_resp_time_ms, last_err_msg
    ) VALUES (
        p_source_id, p_health_status,
        CASE WHEN p_is_success THEN 1 ELSE 0 END,
        CASE WHEN p_is_success THEN 0 ELSE 1 END,
        1, p_resp_time_ms, p_err_msg
    )
    ON CONFLICT (source_id) DO UPDATE SET
        health_status = EXCLUDED.health_status,
        success_req_count = dg_source_monitor.success_req_count +
            CASE WHEN p_is_success THEN 1 ELSE 0 END,
        fail_req_count = dg_source_monitor.fail_req_count +
            CASE WHEN p_is_success THEN 0 ELSE 1 END,
        total_req_count = dg_source_monitor.total_req_count + 1,
        avg_resp_time_ms = (
            (dg_source_monitor.avg_resp_time_ms * dg_source_monitor.total_req_count) + p_resp_time_ms
        ) / (dg_source_monitor.total_req_count + 1),
        last_succ_ts = CASE WHEN p_is_success THEN CURRENT_TIMESTAMP ELSE dg_source_monitor.last_succ_ts END,
        last_fail_ts = CASE WHEN NOT p_is_success THEN CURRENT_TIMESTAMP ELSE dg_source_monitor.last_fail_ts END,
        last_err_msg = CASE WHEN NOT p_is_success THEN p_err_msg ELSE dg_source_monitor.last_err_msg END,
        error_rate_pct = (
            (dg_source_monitor.fail_req_count + CASE WHEN p_is_success THEN 0 ELSE 1 END) * 100.0 /
            (dg_source_monitor.total_req_count + 1)
        ),
        check_ts = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- 3.5 保存行情缓存
CREATE OR REPLACE FUNCTION dg_save_quote_cache(
    p_symbol_code VARCHAR,
    p_market_code VARCHAR,
    p_quote_data JSONB,
    p_source_code VARCHAR DEFAULT NULL,
    p_ttl_sec INTEGER DEFAULT 5
) RETURNS VOID AS $$
BEGIN
    INSERT INTO dg_cache_quote (symbol_code, market_code, quote_data, source_code, expire_at_ts)
    VALUES (
        p_symbol_code, p_market_code, p_quote_data, p_source_code,
        CURRENT_TIMESTAMP + (p_ttl_sec || ' seconds')::INTERVAL
    )
    ON CONFLICT (symbol_code, market_code) DO UPDATE SET
        quote_data = EXCLUDED.quote_data,
        source_code = EXCLUDED.source_code,
        created_at_ts = CURRENT_TIMESTAMP,
        expire_at_ts = CURRENT_TIMESTAMP + (p_ttl_sec || ' seconds')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- 3.6 获取行情缓存
CREATE OR REPLACE FUNCTION dg_get_quote_cache(
    p_symbol_code VARCHAR,
    p_market_code VARCHAR
) RETURNS JSONB AS $$
DECLARE
    v_data JSONB;
BEGIN
    SELECT quote_data INTO v_data
    FROM dg_cache_quote
    WHERE symbol_code = p_symbol_code
      AND market_code = p_market_code
      AND expire_at_ts > CURRENT_TIMESTAMP
    LIMIT 1;

    RETURN v_data;
END;
$$ LANGUAGE plpgsql;

-- 3.7 保存K线缓存
CREATE OR REPLACE FUNCTION dg_save_kline_cache(
    p_symbol_code VARCHAR,
    p_market_code VARCHAR,
    p_period_type VARCHAR,
    p_kline_data JSONB,
    p_source_code VARCHAR DEFAULT NULL,
    p_start_date VARCHAR DEFAULT NULL,
    p_end_date VARCHAR DEFAULT NULL,
    p_ttl_sec INTEGER DEFAULT 60
) RETURNS VOID AS $$
DECLARE
    v_date_range JSONB;
BEGIN
    IF p_start_date IS NOT NULL AND p_end_date IS NOT NULL THEN
        v_date_range = jsonb_build_object(
            'start', p_start_date,
            'end', p_end_date
        );
    ELSE
        v_date_range = NULL;
    END IF;

    INSERT INTO dg_cache_kline (symbol_code, market_code, period_type, kline_data, source_code, date_range, expire_at_ts)
    VALUES (
        p_symbol_code, p_market_code, p_period_type, p_kline_data, p_source_code, v_date_range,
        CURRENT_TIMESTAMP + (p_ttl_sec || ' seconds')::INTERVAL
    )
    ON CONFLICT (symbol_code, market_code, period_type, date_range) DO UPDATE SET
        kline_data = EXCLUDED.kline_data,
        source_code = EXCLUDED.source_code,
        created_at_ts = CURRENT_TIMESTAMP,
        expire_at_ts = CURRENT_TIMESTAMP + (p_ttl_sec || ' seconds')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- 3.8 检查限流
CREATE OR REPLACE FUNCTION dg_check_rate_limit(
    p_client_key VARCHAR,
    p_api_path VARCHAR,
    p_limit_per_min INTEGER DEFAULT 60,
    p_limit_per_hr INTEGER DEFAULT 1000
) RETURNS JSONB AS $$
DECLARE
    v_is_blocked BOOLEAN;
    v_remaining INTEGER;
    v_window_start TIMESTAMP;
    v_req_count INTEGER;
    v_result JSONB;
BEGIN
    v_window_start := date_trunc('minute', CURRENT_TIMESTAMP);

    SELECT COALESCE(req_count, 0), COALESCE(is_blocked, false)
    INTO v_req_count, v_is_blocked
    FROM dg_rate_limits
    WHERE client_key = p_client_key
      AND api_path = p_api_path
      AND window_start_ts = v_window_start
    FOR UPDATE;

    IF v_is_blocked THEN
        v_result := jsonb_build_object(
            'allowed', false,
            'reason', 'rate_limit_exceeded',
            'retry_after_sec', 60 - EXTRACT(SECOND FROM CURRENT_TIMESTAMP)
        );
        RETURN v_result;
    END IF;

    v_remaining := p_limit_per_min - v_req_count;

    IF v_req_count >= p_limit_per_min THEN
        INSERT INTO dg_rate_limits (client_key, api_path, window_start_ts, req_count, is_blocked)
        VALUES (p_client_key, p_api_path, v_window_start, v_req_count, true)
        ON CONFLICT (client_key, api_path, window_start_ts) DO UPDATE SET
            req_count = dg_rate_limits.req_count + 1,
            is_blocked = true;

        v_result := jsonb_build_object(
            'allowed', false,
            'reason', 'rate_limit_exceeded',
            'limit', p_limit_per_min,
            'retry_after_sec', 60 - EXTRACT(SECOND FROM CURRENT_TIMESTAMP)
        );
    ELSE
        INSERT INTO dg_rate_limits (client_key, api_path, window_start_ts, req_count, is_blocked)
        VALUES (p_client_key, p_api_path, v_window_start, 1, false)
        ON CONFLICT (client_key, api_path, window_start_ts) DO UPDATE SET
            req_count = dg_rate_limits.req_count + 1;

        v_result := jsonb_build_object(
            'allowed', true,
            'limit', p_limit_per_min,
            'remaining', v_remaining - 1,
            'reset_at', v_window_start + INTERVAL '1 minute'
        );
    END IF;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- 3.9 更新每日统计
CREATE OR REPLACE FUNCTION dg_update_daily_stats(
    p_stat_date DATE DEFAULT CURRENT_DATE,
    p_market_code VARCHAR DEFAULT NULL,
    p_source_code VARCHAR DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO dg_statistics (
        stat_date, market_code, source_code,
        total_req_count, succ_req_count, fail_req_count,
        avg_resp_time_ms, cache_hit_count, cache_miss_count,
        unique_symbol_count, unique_client_count
    )
    SELECT
        p_stat_date,
        p_market_code,
        p_source_code,
        COUNT(*) as total_req,
        COUNT(*) FILTER (WHERE http_status = 200) as succ_req,
        COUNT(*) FILTER (WHERE http_status != 200) as fail_req,
        AVG(resp_time_ms) as avg_resp,
        COUNT(*) FILTER (WHERE is_cache_hit = true) as cache_hit,
        COUNT(*) FILTER (WHERE is_cache_hit = false) as cache_miss,
        COUNT(DISTINCT (req_params->>'symbols')) as unique_symbols,
        COUNT(DISTINCT client_ip) as unique_clients
    FROM dg_api_logs
    WHERE DATE(created_at_ts) = p_stat_date
      AND (p_market_code IS NULL OR market_code = p_market_code)
      AND (p_source_code IS NULL OR source_code = p_source_code)
    ON CONFLICT (stat_date, market_code, source_code) DO UPDATE SET
        total_req_count = dg_statistics.total_req_count + EXCLUDED.total_req_count,
        succ_req_count = dg_statistics.succ_req_count + EXCLUDED.succ_req_count,
        fail_req_count = dg_statistics.fail_req_count + EXCLUDED.fail_req_count,
        avg_resp_time_ms = (dg_statistics.avg_resp_time_ms + EXCLUDED.avg_resp_time_ms) / 2,
        cache_hit_count = dg_statistics.cache_hit_count + EXCLUDED.cache_hit_count,
        cache_miss_count = dg_statistics.cache_miss_count + EXCLUDED.cache_miss_count,
        unique_symbol_count = GREATEST(dg_statistics.unique_symbol_count, EXCLUDED.unique_symbol_count),
        unique_client_count = GREATEST(dg_statistics.unique_client_count, EXCLUDED.unique_client_count),
        updated_at_ts = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- 3.10 验证API密钥
CREATE OR REPLACE FUNCTION dg_validate_api_key(
    p_key_code VARCHAR,
    p_key_secret VARCHAR,
    p_market_code VARCHAR,
    p_api_path VARCHAR
) RETURNS JSONB AS $$
DECLARE
    v_key_record RECORD;
    v_result JSONB;
BEGIN
    SELECT * INTO v_key_record
    FROM dg_api_keys
    WHERE key_code = p_key_code
      AND key_secret = p_key_secret
      AND is_enabled = true
      AND (expire_at_ts IS NULL OR expire_at_ts > CURRENT_TIMESTAMP);

    IF NOT FOUND THEN
        v_result := jsonb_build_object('valid', false, 'reason', 'invalid_key');
        RETURN v_result;
    END IF;

    IF v_key_record.allowed_markets IS NOT NULL THEN
        IF NOT (v_key_record.allowed_markets ? p_market_code) THEN
            v_result := jsonb_build_object('valid', false, 'reason', 'market_not_allowed');
            RETURN v_result;
        END IF;
    END IF;

    IF v_key_record.allowed_paths IS NOT NULL THEN
        IF NOT (v_key_record.allowed_paths ? p_api_path) THEN
            v_result := jsonb_build_object('valid', false, 'reason', 'path_not_allowed');
            RETURN v_result;
        END IF;
    END IF;

    UPDATE dg_api_keys
    SET last_used_at_ts = CURRENT_TIMESTAMP,
        total_req_count = total_req_count + 1
    WHERE key_id = v_key_record.key_id;

    v_result := jsonb_build_object(
        'valid', true,
        'key_name', v_key_record.key_name,
        'rate_limit_per_min', v_key_record.rate_limit_per_min,
        'rate_limit_per_hr', v_key_record.rate_limit_per_hr
    );

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- 3.11 获取数据源健康状态
CREATE OR REPLACE FUNCTION dg_get_source_health()
RETURNS TABLE (
    source_code VARCHAR,
    market_code VARCHAR,
    data_type VARCHAR,
    health_status VARCHAR,
    error_rate_pct FLOAT,
    avg_resp_time_ms FLOAT,
    last_check_ts TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.source_code,
        s.market_code,
        s.data_type,
        COALESCE(m.health_status, 'unknown') as health_status,
        COALESCE(m.error_rate_pct, 0) as error_rate_pct,
        COALESCE(m.avg_resp_time_ms, 0) as avg_resp_time_ms,
        m.check_ts as last_check_ts
    FROM dg_sources s
    LEFT JOIN LATERAL (
        SELECT *
        FROM dg_source_monitor
        WHERE source_id = s.source_id
        ORDER BY check_ts DESC
        LIMIT 1
    ) m ON true
    WHERE s.is_enabled = true
    ORDER BY s.market_code, s.priority_rank;
END;
$$ LANGUAGE plpgsql;

-- 3.12 清理过期数据
CREATE OR REPLACE FUNCTION dg_cleanup_old_data(
    p_keep_days INTEGER DEFAULT 30
) RETURNS JSONB AS $$
DECLARE
    v_deleted_count INTEGER;
    v_result JSONB;
BEGIN
    DELETE FROM dg_api_logs
    WHERE created_at_ts < CURRENT_TIMESTAMP - (p_keep_days || ' days')::INTERVAL;
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

    DELETE FROM dg_rate_limits
    WHERE window_start_ts < CURRENT_TIMESTAMP - INTERVAL '1 day';

    DELETE FROM dg_cache_quote WHERE expire_at_ts < CURRENT_TIMESTAMP;
    DELETE FROM dg_cache_kline WHERE expire_at_ts < CURRENT_TIMESTAMP;
    DELETE FROM dg_cache_fundamental WHERE expire_at_ts < CURRENT_TIMESTAMP;

    DELETE FROM dg_webhook_events
    WHERE created_at_ts < CURRENT_TIMESTAMP - (7 || ' days')::INTERVAL;

    v_result := jsonb_build_object(
        'deleted_api_logs', v_deleted_count,
        'cleanup_ts', CURRENT_TIMESTAMP
    );

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- 3.13 生成请求UUID
CREATE OR REPLACE FUNCTION dg_gen_req_uuid()
RETURNS VARCHAR AS $$
BEGIN
    RETURN 'REQ_' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDDHH24MISS') || '_' || UPPER(SUBSTRING(MD5(RANDOM()::TEXT), 1, 8));
END;
$$ LANGUAGE plpgsql;

-- 3.14 获取当前活跃的Webhook订阅
CREATE OR REPLACE FUNCTION dg_get_active_subs(
    p_market_code VARCHAR DEFAULT NULL
) RETURNS TABLE (
    sub_code VARCHAR,
    webhook_url VARCHAR,
    symbol_list JSONB,
    event_types JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.sub_code,
        s.webhook_url,
        s.symbol_list,
        s.event_types
    FROM dg_webhook_subs s
    WHERE s.is_enabled = true
      AND (p_market_code IS NULL OR s.market_code = p_market_code)
      AND (s.expire_at_ts IS NULL OR s.expire_at_ts > CURRENT_TIMESTAMP);
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 4. 触发器
-- ============================================================

-- 为需要的表添加触发器 (先删除再创建，避免重复)
DROP TRIGGER IF EXISTS trg_dg_sources_updated_at ON dg_sources;
CREATE TRIGGER trg_dg_sources_updated_at BEFORE UPDATE ON dg_sources
    FOR EACH ROW EXECUTE FUNCTION dg_update_updated_at();

DROP TRIGGER IF EXISTS trg_dg_source_monitor_updated_at ON dg_source_monitor;
CREATE TRIGGER trg_dg_source_monitor_updated_at BEFORE UPDATE ON dg_source_monitor
    FOR EACH ROW EXECUTE FUNCTION dg_update_updated_at();

DROP TRIGGER IF EXISTS trg_dg_statistics_updated_at ON dg_statistics;
CREATE TRIGGER trg_dg_statistics_updated_at BEFORE UPDATE ON dg_statistics
    FOR EACH ROW EXECUTE FUNCTION dg_update_updated_at();

DROP TRIGGER IF EXISTS trg_dg_api_keys_updated_at ON dg_api_keys;
CREATE TRIGGER trg_dg_api_keys_updated_at BEFORE UPDATE ON dg_api_keys
    FOR EACH ROW EXECUTE FUNCTION dg_update_updated_at();

DROP TRIGGER IF EXISTS trg_dg_webhook_subs_updated_at ON dg_webhook_subs;
CREATE TRIGGER trg_dg_webhook_subs_updated_at BEFORE UPDATE ON dg_webhook_subs
    FOR EACH ROW EXECUTE FUNCTION dg_update_updated_at();

DROP TRIGGER IF EXISTS trg_dg_sync_config_updated_at ON dg_sync_config;
CREATE TRIGGER trg_dg_sync_config_updated_at BEFORE UPDATE ON dg_sync_config
    FOR EACH ROW EXECUTE FUNCTION dg_update_updated_at();

-- ============================================================
-- 5. 视图
-- ============================================================

-- 5.1 数据源状态汇总视图
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

-- 5.2 每日API请求统计视图
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

-- 5.3 缓存效果统计视图
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
-- 6. 初始化数据
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
