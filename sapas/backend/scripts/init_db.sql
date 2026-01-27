-- ================================================================
-- SAPAS 数据库初始化脚本
-- ================================================================

-- 1. 用户表 (users)
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    avatar VARCHAR(255),
    nickname VARCHAR(50),
    phone VARCHAR(20),
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 用户表索引
CREATE INDEX IF NOT EXISTS idx_user_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_user_role ON users(role);

-- 2. 自选股分组表 (watchlist_groups)
CREATE TABLE IF NOT EXISTS watchlist_groups (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_watchlist_group_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 自选股分组表索引
CREATE INDEX IF NOT EXISTS idx_watchlist_group_user ON watchlist_groups(user_id);

-- 3. 自选股项目表 (watchlist_items)
CREATE TABLE IF NOT EXISTS watchlist_items (
    id BIGSERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    sort_order INTEGER NOT NULL DEFAULT 0,
    note TEXT,
    alert_config TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_watchlist_item_group FOREIGN KEY (group_id) REFERENCES watchlist_groups(id) ON DELETE CASCADE
);

-- 自选股项目表索引
CREATE INDEX IF NOT EXISTS idx_watchlist_item_group ON watchlist_items(group_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_item_code ON watchlist_items(stock_code);
CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_item_unique ON watchlist_items(group_id, stock_code);

-- 4. 预警规则表 (alerts)
CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    stock_code VARCHAR(20),
    alert_type VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    condition_config TEXT NOT NULL,
    frequency VARCHAR(20) NOT NULL DEFAULT 'once',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    trigger_count INTEGER NOT NULL DEFAULT 0,
    last_triggered_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_alert_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 预警规则表索引
CREATE INDEX IF NOT EXISTS idx_alert_user ON alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alert_type ON alerts(alert_type);

-- 5. 预警历史表 (alert_history)
CREATE TABLE IF NOT EXISTS alert_history (
    id BIGSERIAL PRIMARY KEY,
    alert_id BIGINT NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    trigger_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    trigger_value TEXT,
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'unread',
    sent_email BOOLEAN NOT NULL DEFAULT FALSE,
    sent_sms BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_alert_history_alert FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE CASCADE
);

-- 预警历史表索引
CREATE INDEX IF NOT EXISTS idx_alert_history_alert ON alert_history(alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_time ON alert_history(trigger_time);
CREATE INDEX IF NOT EXISTS idx_alert_history_status ON alert_history(status);

-- 6. 回测运行表 (backtest_runs)
CREATE TABLE IF NOT EXISTS backtest_runs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    strategy_name VARCHAR(50) NOT NULL,
    strategy_config TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(15,2) NOT NULL,
    commission_rate DECIMAL(5,4) NOT NULL DEFAULT 0.0003,
    slippage DECIMAL(5,4) NOT NULL DEFAULT 0.001,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    final_capital DECIMAL(15,2),
    total_return DECIMAL(10,4),
    total_return_pct DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    max_drawdown_pct DECIMAL(10,4),
    sharpe_ratio DECIMAL(8,4),
    win_rate DECIMAL(5,4),
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    avg_profit DECIMAL(15,4),
    avg_loss DECIMAL(15,4),
    profit_factor DECIMAL(8,4),
    result_summary TEXT,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    CONSTRAINT fk_backtest_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 回测运行表索引
CREATE INDEX IF NOT EXISTS idx_backtest_user ON backtest_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_backtest_status ON backtest_runs(status);
CREATE INDEX IF NOT EXISTS idx_backtest_date ON backtest_runs(start_date);

-- 7. 回测交易记录表 (backtest_trades)
CREATE TABLE IF NOT EXISTS backtest_trades (
    id BIGSERIAL PRIMARY KEY,
    backtest_id BIGINT NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    trade_type VARCHAR(10) NOT NULL,
    trade_time TIMESTAMP NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    quantity INTEGER NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    commission DECIMAL(10,2) NOT NULL DEFAULT 0,
    profit DECIMAL(15,4),
    profit_pct DECIMAL(10,4),
    exit_reason VARCHAR(100),
    CONSTRAINT fk_backtest_trade_backtest FOREIGN KEY (backtest_id) REFERENCES backtest_runs(id) ON DELETE CASCADE
);

-- 回测交易记录表索引
CREATE INDEX IF NOT EXISTS idx_backtest_trade_backtest ON backtest_trades(backtest_id);
CREATE INDEX IF NOT EXISTS idx_backtest_trade_time ON backtest_trades(trade_time);

-- 8. 选股条件表 (screener_conditions)
CREATE TABLE IF NOT EXISTS screener_conditions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    condition_config TEXT NOT NULL,
    is_public INTEGER NOT NULL DEFAULT 0,
    use_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_screener_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 选股条件表索引
CREATE INDEX IF NOT EXISTS idx_screener_user ON screener_conditions(user_id);
CREATE INDEX IF NOT EXISTS idx_screener_public ON screener_conditions(is_public);

-- ================================================================
-- 自动更新 updated_at 触发器
-- ================================================================

-- 用户表 updated_at 触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_watchlist_groups_updated_at
    BEFORE UPDATE ON watchlist_groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_watchlist_items_updated_at
    BEFORE UPDATE ON watchlist_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_alerts_updated_at
    BEFORE UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_screener_conditions_updated_at
    BEFORE UPDATE ON screener_conditions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================================
-- 初始化完成提示
-- ================================================================

DO $$
BEGIN
    RAISE NOTICE 'SAPAS 数据库表初始化完成！';
    RAISE NOTICE '已创建的表：';
    RAISE NOTICE '  - users';
    RAISE NOTICE '  - watchlist_groups';
    RAISE NOTICE '  - watchlist_items';
    RAISE NOTICE '  - alerts';
    RAISE NOTICE '  - alert_history';
    RAISE NOTICE '  - backtest_runs';
    RAISE NOTICE '  - backtest_trades';
    RAISE NOTICE '  - screener_conditions';
END $$;
