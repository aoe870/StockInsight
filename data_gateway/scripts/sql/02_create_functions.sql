-- ============================================================
-- 数据网关服务数据库函数和存储过程 (完全独立设计)
-- Database: data_gateway
-- ============================================================

-- 1. 记录API请求日志
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

-- 2. 更新数据源状态
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

-- 3. 保存行情缓存
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

-- 4. 获取行情缓存
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

-- 5. 保存K线缓存
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

-- 6. 检查限流
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

-- 7. 更新每日统计
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

-- 8. 验证API密钥
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

    -- 检查市场权限
    IF v_key_record.allowed_markets IS NOT NULL THEN
        IF NOT (v_key_record.allowed_markets ? p_market_code) THEN
            v_result := jsonb_build_object('valid', false, 'reason', 'market_not_allowed');
            RETURN v_result;
        END IF;
    END IF;

    -- 检查接口权限
    IF v_key_record.allowed_paths IS NOT NULL THEN
        IF NOT (v_key_record.allowed_paths ? p_api_path) THEN
            v_result := jsonb_build_object('valid', false, 'reason', 'path_not_allowed');
            RETURN v_result;
        END IF;
    END IF;

    -- 更新最后使用时间
    UPDATE dg_api_keys
    SET last_used_at_ts = CURRENT_TIMESTAMP,
        total_req_count = total_req_count + 1
    WHERE id = v_key_record.id;

    v_result := jsonb_build_object(
        'valid', true,
        'key_name', v_key_record.key_name,
        'rate_limit_per_min', v_key_record.rate_limit_per_min,
        'rate_limit_per_hr', v_key_record.rate_limit_per_hr
    );

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- 9. 获取数据源健康状态
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

-- 10. 清理过期数据
CREATE OR REPLACE FUNCTION dg_cleanup_old_data(
    p_keep_days INTEGER DEFAULT 30
) RETURNS JSONB AS $$
DECLARE
    v_deleted_count INTEGER;
    v_result JSONB;
BEGIN
    -- 清理旧的请求日志
    DELETE FROM dg_api_logs
    WHERE created_at_ts < CURRENT_TIMESTAMP - (p_keep_days || ' days')::INTERVAL;
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

    -- 清理旧的限流记录
    DELETE FROM dg_rate_limits
    WHERE window_start_ts < CURRENT_TIMESTAMP - INTERVAL '1 day';

    -- 清理过期的缓存
    DELETE FROM dg_cache_quote WHERE expire_at_ts < CURRENT_TIMESTAMP;
    DELETE FROM dg_cache_kline WHERE expire_at_ts < CURRENT_TIMESTAMP;
    DELETE FROM dg_cache_fundamental WHERE expire_at_ts < CURRENT_TIMESTAMP;

    -- 清理旧的Webhook事件日志
    DELETE FROM dg_webhook_events
    WHERE created_at_ts < CURRENT_TIMESTAMP - (7 || ' days')::INTERVAL;

    v_result := jsonb_build_object(
        'deleted_api_logs', v_deleted_count,
        'cleanup_ts', CURRENT_TIMESTAMP
    );

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 辅助函数
-- ============================================================

-- 生成请求UUID
CREATE OR REPLACE FUNCTION dg_gen_req_uuid()
RETURNS VARCHAR AS $$
BEGIN
    RETURN 'REQ_' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDDHH24MISS') || '_' || UPPER(SUBSTRING(MD5(RANDOM()::TEXT), 1, 8));
END;
$$ LANGUAGE plpgsql;

-- 获取当前活跃的Webhook订阅
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
