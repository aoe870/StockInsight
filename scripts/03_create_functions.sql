-- ============================================================
-- SAPAS 数据库函数与触发器脚本
-- 数据库: PostgreSQL 14+
-- 创建日期: 2026-01-13
-- ============================================================

-- ============================================================
-- 通用函数：自动更新 updated_at 字段
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为需要的表添加触发器
CREATE TRIGGER trg_stock_basics_updated_at
    BEFORE UPDATE ON stock_basics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_alert_rules_updated_at
    BEFORE UPDATE ON alert_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 函数：获取股票最新行情日期
-- 用于增量更新时确定起始日期
-- ============================================================
CREATE OR REPLACE FUNCTION get_latest_trade_date(
    p_code VARCHAR(10),
    p_adjust_type VARCHAR(10) DEFAULT 'qfq'
)
RETURNS DATE AS $$
DECLARE
    v_date DATE;
BEGIN
    SELECT MAX(trade_date) INTO v_date
    FROM stock_daily_k
    WHERE code = p_code AND adjust_type = p_adjust_type;
    
    RETURN v_date;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 函数：批量获取多只股票的最新行情日期
-- ============================================================
CREATE OR REPLACE FUNCTION get_latest_trade_dates(
    p_codes VARCHAR(10)[],
    p_adjust_type VARCHAR(10) DEFAULT 'qfq'
)
RETURNS TABLE(code VARCHAR(10), latest_date DATE) AS $$
BEGIN
    RETURN QUERY
    SELECT dk.code, MAX(dk.trade_date) as latest_date
    FROM stock_daily_k dk
    WHERE dk.code = ANY(p_codes) AND dk.adjust_type = p_adjust_type
    GROUP BY dk.code;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 函数：检查告警冷却时间
-- 返回 TRUE 表示可以触发告警，FALSE 表示在冷却中
-- ============================================================
CREATE OR REPLACE FUNCTION check_alert_cooldown(
    p_rule_id BIGINT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_cooldown INTEGER;
    v_last_trigger TIMESTAMP WITH TIME ZONE;
BEGIN
    -- 获取规则的冷却时间
    SELECT cooldown_minutes INTO v_cooldown
    FROM alert_rules
    WHERE id = p_rule_id;
    
    IF v_cooldown IS NULL OR v_cooldown = 0 THEN
        RETURN TRUE;
    END IF;
    
    -- 获取最后一次触发时间
    SELECT MAX(triggered_at) INTO v_last_trigger
    FROM alert_history
    WHERE rule_id = p_rule_id;
    
    IF v_last_trigger IS NULL THEN
        RETURN TRUE;
    END IF;
    
    -- 检查是否超过冷却时间
    RETURN (NOW() - v_last_trigger) > (v_cooldown || ' minutes')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 函数：获取用户的订阅规则列表（带股票信息）
-- ============================================================
CREATE OR REPLACE FUNCTION get_user_subscriptions(
    p_user_id UUID
)
RETURNS TABLE(
    subscription_id BIGINT,
    rule_id BIGINT,
    rule_name VARCHAR(100),
    rule_type VARCHAR(30),
    stock_code VARCHAR(10),
    stock_name VARCHAR(50),
    channel VARCHAR(20),
    is_active BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id as subscription_id,
        r.id as rule_id,
        r.rule_name,
        r.rule_type,
        r.stock_code,
        sb.name as stock_name,
        s.channel,
        s.is_active
    FROM subscriptions s
    JOIN alert_rules r ON s.rule_id = r.id
    LEFT JOIN stock_basics sb ON r.stock_code = sb.code
    WHERE s.user_id = p_user_id
    ORDER BY s.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 函数：记录同步日志并返回ID
-- ============================================================
CREATE OR REPLACE FUNCTION start_sync_log(
    p_sync_type VARCHAR(30),
    p_stock_code VARCHAR(10) DEFAULT NULL,
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_log_id BIGINT;
BEGIN
    INSERT INTO sync_logs (sync_type, stock_code, start_date, end_date, status)
    VALUES (p_sync_type, p_stock_code, p_start_date, p_end_date, 'RUNNING')
    RETURNING id INTO v_log_id;
    
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 函数：完成同步日志
-- ============================================================
CREATE OR REPLACE FUNCTION finish_sync_log(
    p_log_id BIGINT,
    p_records_count INTEGER,
    p_status VARCHAR(20),
    p_error_message TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    UPDATE sync_logs
    SET records_count = p_records_count,
        status = p_status,
        error_message = p_error_message,
        finished_at = NOW()
    WHERE id = p_log_id;
END;
$$ LANGUAGE plpgsql;

