-- ============================================================
-- SAPAS 数据库索引创建脚本
-- 数据库: PostgreSQL 14+
-- 创建日期: 2026-01-13
-- ============================================================

-- ============================================================
-- stock_basics 表索引
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_stock_basics_market 
    ON stock_basics(market);

CREATE INDEX IF NOT EXISTS idx_stock_basics_industry 
    ON stock_basics(industry);

CREATE INDEX IF NOT EXISTS idx_stock_basics_active 
    ON stock_basics(is_active) WHERE is_active = TRUE;

-- ============================================================
-- stock_daily_k 表索引 (核心表，索引优化关键)
-- ============================================================
-- 联合唯一索引：确保数据幂等性
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_k_unique 
    ON stock_daily_k(code, trade_date, adjust_type);

-- 按股票代码查询（最常用）
CREATE INDEX IF NOT EXISTS idx_daily_k_code 
    ON stock_daily_k(code);

-- 按日期查询（用于批量分析）
CREATE INDEX IF NOT EXISTS idx_daily_k_date 
    ON stock_daily_k(trade_date);

-- 复合索引：按代码+日期范围查询
CREATE INDEX IF NOT EXISTS idx_daily_k_code_date 
    ON stock_daily_k(code, trade_date DESC);

-- 部分索引：仅前复权数据（最常用的复权类型）
CREATE INDEX IF NOT EXISTS idx_daily_k_qfq 
    ON stock_daily_k(code, trade_date) 
    WHERE adjust_type = 'qfq';

-- ============================================================
-- watchlist_items 表索引
-- ============================================================
-- 联合唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_unique 
    ON watchlist_items(user_id, stock_code);

-- 按用户查询自选股
CREATE INDEX IF NOT EXISTS idx_watchlist_user 
    ON watchlist_items(user_id, sort_order);

-- ============================================================
-- alert_rules 表索引
-- ============================================================
-- 按股票代码查询规则
CREATE INDEX IF NOT EXISTS idx_alert_rules_stock 
    ON alert_rules(stock_code) WHERE stock_code IS NOT NULL;

-- 按规则类型查询
CREATE INDEX IF NOT EXISTS idx_alert_rules_type 
    ON alert_rules(rule_type);

-- 仅查询启用的规则
CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled 
    ON alert_rules(is_enabled) WHERE is_enabled = TRUE;

-- ============================================================
-- subscriptions 表索引
-- ============================================================
-- 联合唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_unique 
    ON subscriptions(user_id, rule_id, channel);

-- 按用户查询订阅
CREATE INDEX IF NOT EXISTS idx_subscriptions_user 
    ON subscriptions(user_id);

-- 按规则查询订阅者（用于发送通知）
CREATE INDEX IF NOT EXISTS idx_subscriptions_rule 
    ON subscriptions(rule_id) WHERE is_active = TRUE;

-- ============================================================
-- alert_history 表索引
-- ============================================================
-- 按规则查询历史
CREATE INDEX IF NOT EXISTS idx_alert_history_rule 
    ON alert_history(rule_id);

-- 按股票查询历史
CREATE INDEX IF NOT EXISTS idx_alert_history_stock 
    ON alert_history(stock_code);

-- 按时间查询（最近告警）
CREATE INDEX IF NOT EXISTS idx_alert_history_time 
    ON alert_history(triggered_at DESC);

-- 复合索引：按规则+时间（用于冷却时间检查）
CREATE INDEX IF NOT EXISTS idx_alert_history_rule_time 
    ON alert_history(rule_id, triggered_at DESC);

-- ============================================================
-- sync_logs 表索引
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_sync_logs_type 
    ON sync_logs(sync_type);

CREATE INDEX IF NOT EXISTS idx_sync_logs_status 
    ON sync_logs(status);

CREATE INDEX IF NOT EXISTS idx_sync_logs_time 
    ON sync_logs(started_at DESC);

-- ============================================================
-- stock_indicators 表索引
-- ============================================================
CREATE UNIQUE INDEX IF NOT EXISTS idx_indicators_unique 
    ON stock_indicators(code, trade_date, indicator_type);

CREATE INDEX IF NOT EXISTS idx_indicators_code_date 
    ON stock_indicators(code, trade_date DESC);

