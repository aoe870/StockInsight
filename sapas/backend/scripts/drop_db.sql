-- ================================================================
-- SAPAS 数据库删除脚本（慎用！）
-- ================================================================

-- 删除触发器
DROP TRIGGER IF EXISTS trigger_users_updated_at ON users;
DROP TRIGGER IF EXISTS trigger_watchlist_groups_updated_at ON watchlist_groups;
DROP TRIGGER IF EXISTS trigger_watchlist_items_updated_at ON watchlist_items;
DROP TRIGGER IF EXISTS trigger_alerts_updated_at ON alerts;
DROP TRIGGER IF EXISTS trigger_screener_conditions_updated_at ON screener_conditions;

-- 删除函数
DROP FUNCTION IF EXISTS update_updated_at_column();

-- 删除表（注意顺序：先删除有外键约束的表）
DROP TABLE IF EXISTS screener_conditions CASCADE;
DROP TABLE IF EXISTS backtest_trades CASCADE;
DROP TABLE IF EXISTS backtest_runs CASCADE;
DROP TABLE IF EXISTS alert_history CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS watchlist_items CASCADE;
DROP TABLE IF EXISTS watchlist_groups CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ================================================================
-- 删除完成提示
-- ================================================================

DO $$
BEGIN
    RAISE NOTICE 'SAPAS 数据库表已全部删除！';
END $$;
