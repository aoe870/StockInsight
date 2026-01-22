-- ============================================================
-- SAPAS 数据库表结构创建脚本
-- 数据库: PostgreSQL 14+
-- 创建日期: 2026-01-13
-- ============================================================

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. 股票基础信息表
-- ============================================================
CREATE TABLE IF NOT EXISTS stock_basics (
    code            VARCHAR(10) PRIMARY KEY,
    name            VARCHAR(50) NOT NULL,
    industry        VARCHAR(50),
    list_date       DATE,
    market          VARCHAR(10) NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE stock_basics IS '股票基础信息表';
COMMENT ON COLUMN stock_basics.code IS '股票代码，如 000001';
COMMENT ON COLUMN stock_basics.name IS '股票名称';
COMMENT ON COLUMN stock_basics.industry IS '所属行业板块';
COMMENT ON COLUMN stock_basics.list_date IS '上市日期';
COMMENT ON COLUMN stock_basics.market IS '市场: SH-上海, SZ-深圳, BJ-北京';
COMMENT ON COLUMN stock_basics.is_active IS '是否正常交易';

-- ============================================================
-- 2. 日线行情表
-- ============================================================
CREATE TABLE IF NOT EXISTS stock_daily_k (
    id              BIGSERIAL PRIMARY KEY,
    code            VARCHAR(10) NOT NULL,
    trade_date      DATE NOT NULL,
    open_price      DECIMAL(12, 4),
    close_price     DECIMAL(12, 4),
    high_price      DECIMAL(12, 4),
    low_price       DECIMAL(12, 4),
    volume          BIGINT,
    amount          DECIMAL(18, 4),
    adjust_type     VARCHAR(10) NOT NULL DEFAULT 'none',
    change_pct      DECIMAL(12, 4),
    turnover        DECIMAL(12, 4),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT fk_daily_k_stock
        FOREIGN KEY (code) REFERENCES stock_basics(code) ON DELETE CASCADE
);

COMMENT ON TABLE stock_daily_k IS '股票日K线行情表';
COMMENT ON COLUMN stock_daily_k.adjust_type IS '复权类型: none-不复权, qfq-前复权, hfq-后复权';
COMMENT ON COLUMN stock_daily_k.change_pct IS '涨跌幅百分比';
COMMENT ON COLUMN stock_daily_k.turnover IS '换手率百分比';

-- ============================================================
-- 3. 用户表
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(50) NOT NULL UNIQUE,
    email           VARCHAR(100) UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    nickname        VARCHAR(50),
    avatar          VARCHAR(255),
    role            VARCHAR(20) DEFAULT 'user',
    notify_channel  VARCHAR(20) DEFAULT 'console',
    is_active       BOOLEAN DEFAULT TRUE,
    last_login_at   TIMESTAMP WITH TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.role IS '用户角色: user, admin';
COMMENT ON COLUMN users.notify_channel IS '默认通知渠道: console, email, webhook, wechat';

-- ============================================================
-- 4. 自选股表
-- ============================================================
CREATE TABLE IF NOT EXISTS watchlist_items (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL,
    stock_code      VARCHAR(10) NOT NULL,
    note            TEXT,
    sort_order      INTEGER DEFAULT 0,
    added_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT fk_watchlist_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_watchlist_stock
        FOREIGN KEY (stock_code) REFERENCES stock_basics(code) ON DELETE CASCADE
);

COMMENT ON TABLE watchlist_items IS '用户自选股列表';

-- ============================================================
-- 5. 告警规则表
-- ============================================================
CREATE TABLE IF NOT EXISTS alert_rules (
    id                  BIGSERIAL PRIMARY KEY,
    stock_code          VARCHAR(10),
    rule_type           VARCHAR(30) NOT NULL,
    rule_name           VARCHAR(100) NOT NULL,
    conditions          JSONB NOT NULL,
    is_enabled          BOOLEAN DEFAULT TRUE,
    cooldown_minutes    INTEGER DEFAULT 60,
    created_by          UUID,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT fk_rule_stock
        FOREIGN KEY (stock_code) REFERENCES stock_basics(code) ON DELETE CASCADE,
    CONSTRAINT fk_rule_creator
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

COMMENT ON TABLE alert_rules IS '告警规则定义表';
COMMENT ON COLUMN alert_rules.stock_code IS '股票代码，NULL表示全局规则';
COMMENT ON COLUMN alert_rules.rule_type IS '规则类型: PRICE_BREAKOUT, MA_CROSS, MACD_SIGNAL, RSI_EXTREME, VOLUME_SURGE, BOLLINGER_BREAK';
COMMENT ON COLUMN alert_rules.conditions IS 'JSON格式的触发条件配置';
COMMENT ON COLUMN alert_rules.cooldown_minutes IS '告警冷却时间(分钟)，避免频繁触发';

-- ============================================================
-- 6. 订阅表
-- ============================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL,
    rule_id         BIGINT NOT NULL,
    channel         VARCHAR(20) NOT NULL,
    channel_config  JSONB,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT fk_sub_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_sub_rule
        FOREIGN KEY (rule_id) REFERENCES alert_rules(id) ON DELETE CASCADE
);

COMMENT ON TABLE subscriptions IS '用户告警订阅表';
COMMENT ON COLUMN subscriptions.channel IS '通知渠道: console, email, webhook, wechat';
COMMENT ON COLUMN subscriptions.channel_config IS '渠道特定配置，如webhook URL';




-- ============================================================
-- 7. 告警历史表
-- ============================================================
CREATE TABLE IF NOT EXISTS alert_history (
    id              BIGSERIAL PRIMARY KEY,
    rule_id         BIGINT NOT NULL,
    stock_code      VARCHAR(10) NOT NULL,
    alert_type      VARCHAR(30) NOT NULL,
    alert_data      JSONB NOT NULL,
    triggered_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT fk_history_rule
        FOREIGN KEY (rule_id) REFERENCES alert_rules(id) ON DELETE CASCADE
);

COMMENT ON TABLE alert_history IS '告警触发历史记录';
COMMENT ON COLUMN alert_history.alert_data IS 'JSON格式的告警详情，包含触发时的指标值等';

-- ============================================================
-- 8. 数据同步日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS sync_logs (
    id              BIGSERIAL PRIMARY KEY,
    sync_type       VARCHAR(30) NOT NULL,
    stock_code      VARCHAR(10),
    start_date      DATE,
    end_date        DATE,
    records_count   INTEGER,
    status          VARCHAR(20) NOT NULL,
    error_message   TEXT,
    started_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    finished_at     TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE sync_logs IS '数据同步日志表';
COMMENT ON COLUMN sync_logs.sync_type IS '同步类型: STOCK_LIST, DAILY_K, MINUTE_K';
COMMENT ON COLUMN sync_logs.status IS '状态: RUNNING, SUCCESS, FAILED';

-- ============================================================
-- 9. 技术指标缓存表 (可选，用于存储计算好的指标)
-- ============================================================
CREATE TABLE IF NOT EXISTS stock_indicators (
    id              BIGSERIAL PRIMARY KEY,
    code            VARCHAR(10) NOT NULL,
    trade_date      DATE NOT NULL,
    indicator_type  VARCHAR(20) NOT NULL,
    indicator_data  JSONB NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT fk_indicator_stock
        FOREIGN KEY (code) REFERENCES stock_basics(code) ON DELETE CASCADE
);

COMMENT ON TABLE stock_indicators IS '技术指标缓存表';
COMMENT ON COLUMN stock_indicators.indicator_type IS '指标类型: MA, MACD, RSI, KDJ, BOLL';
COMMENT ON COLUMN stock_indicators.indicator_data IS 'JSON格式的指标值';

-- ============================================================
-- 10. 股票基本面数据表
-- ============================================================
CREATE TABLE IF NOT EXISTS stock_fundamentals (
    id                      BIGSERIAL PRIMARY KEY,
    code                    VARCHAR(10) NOT NULL,
    end_date                DATE NOT NULL,

    -- 估值指标
    pe                      DECIMAL(10, 4),
    pe_ttm                  DECIMAL(10, 4),
    pb                      DECIMAL(10, 4),
    ps                      DECIMAL(10, 4),
    total_market_cap        DECIMAL(18, 4),
    circulating_market_cap DECIMAL(18, 4),
    circulating_shares     DECIMAL(18, 4),

    -- 盈利能力
    eps                     DECIMAL(10, 4),
    eps_diluted             DECIMAL(10, 4),
    net_profit_margin       DECIMAL(10, 4),
    gross_profit_margin     DECIMAL(10, 4),
    roe                     DECIMAL(10, 4),
    roa                     DECIMAL(10, 4),

    -- 成长性
    revenue_yoy             DECIMAL(10, 4),
    profit_yoy              DECIMAL(10, 4),
    revenue_qoq             DECIMAL(10, 4),
    profit_qoq              DECIMAL(10, 4),

    -- 财务健康
    reserve_per_share       DECIMAL(10, 4),
    retained_earnings_per_share DECIMAL(10, 4),
    total_assets            DECIMAL(18, 4),
    total_liabilities       DECIMAL(18, 4),

    -- 经营指标
    operating_cash_flow_per_share DECIMAL(10, 4),
    debt_to_asset_ratio     DECIMAL(10, 4),
    current_ratio           DECIMAL(10, 4),
    quick_ratio             DECIMAL(10, 4),

    -- 元数据
    data_source             VARCHAR(50),
    update_time             TIMESTAMP WITHOUT TIME ZONE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT fk_fundamentals_stock
        FOREIGN KEY (code) REFERENCES stock_basics(code) ON DELETE CASCADE,
    CONSTRAINT uq_fundamentals_code_date UNIQUE (code, end_date)
);

COMMENT ON TABLE stock_fundamentals IS '股票基本面数据表';
COMMENT ON COLUMN stock_fundamentals.end_date IS '报告期';
COMMENT ON COLUMN stock_fundamentals.pe IS '市盈率(动态)';
COMMENT ON COLUMN stock_fundamentals.pe_ttm IS '市盈率(TTM)';
COMMENT ON COLUMN stock_fundamentals.pb IS '市净率';
COMMENT ON COLUMN stock_fundamentals.ps IS '市销率';
COMMENT ON COLUMN stock_fundamentals.total_market_cap IS '总市值(元)';
COMMENT ON COLUMN stock_fundamentals.circulating_market_cap IS '流通市值(元)';
COMMENT ON COLUMN stock_fundamentals.circulating_shares IS '流通股本(股)';
COMMENT ON COLUMN stock_fundamentals.eps IS '每股收益(元)';
COMMENT ON COLUMN stock_fundamentals.eps_diluted IS '稀释每股收益(元)';
COMMENT ON COLUMN stock_fundamentals.net_profit_margin IS '销售净利率(%)';
COMMENT ON COLUMN stock_fundamentals.gross_profit_margin IS '毛利率(%)';
COMMENT ON COLUMN stock_fundamentals.roe IS '净资产收益率(%)';
COMMENT ON COLUMN stock_fundamentals.roa IS '总资产收益率(%)';
COMMENT ON COLUMN stock_fundamentals.revenue_yoy IS '营业收入同比增长(%)';
COMMENT ON COLUMN stock_fundamentals.profit_yoy IS '净利润同比增长(%)';
COMMENT ON COLUMN stock_fundamentals.revenue_qoq IS '营业收入环比增长(%)';
COMMENT ON COLUMN stock_fundamentals.profit_qoq IS '净利润环比增长(%)';
COMMENT ON COLUMN stock_fundamentals.reserve_per_share IS '每股公积金(元)';
COMMENT ON COLUMN stock_fundamentals.retained_earnings_per_share IS '每股未分配利润(元)';
COMMENT ON COLUMN stock_fundamentals.total_assets IS '总资产(元)';
COMMENT ON COLUMN stock_fundamentals.total_liabilities IS '总负债(元)';
COMMENT ON COLUMN stock_fundamentals.operating_cash_flow_per_share IS '每股经营现金流(元)';
COMMENT ON COLUMN stock_fundamentals.debt_to_asset_ratio IS '资产负债率(%)';
COMMENT ON COLUMN stock_fundamentals.current_ratio IS '流动比率';
COMMENT ON COLUMN stock_fundamentals.quick_ratio IS '速动比率';
COMMENT ON COLUMN stock_fundamentals.data_source IS '数据来源';
COMMENT ON COLUMN stock_fundamentals.update_time IS '数据更新时间';

-- ============================================================
-- 11. 股票集合竞价数据表
-- ============================================================
CREATE TABLE IF NOT EXISTS stock_call_auction (
    id              BIGSERIAL PRIMARY KEY,
    code            VARCHAR(10) NOT NULL,
    trade_date      DATE NOT NULL,
    auction_time    VARCHAR(8) NOT NULL,

    -- 竞价数据
    price           DECIMAL(12, 4),
    volume          BIGINT,
    amount          DECIMAL(18, 4),
    buy_volume      BIGINT,
    sell_volume     BIGINT,

    -- 涨跌信息
    change_pct      DECIMAL(10, 4),
    change_amount   DECIMAL(12, 4),

    -- 委比和买卖盘
    bid_ratio       DECIMAL(10, 4),

    -- 元数据
    data_source     VARCHAR(50),
    update_time     TIMESTAMP WITHOUT TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT fk_call_auction_stock
        FOREIGN KEY (code) REFERENCES stock_basics(code) ON DELETE CASCADE,
    CONSTRAINT uq_call_auction_unique UNIQUE (code, trade_date, auction_time)
);

COMMENT ON TABLE stock_call_auction IS '股票集合竞价数据表';
COMMENT ON COLUMN stock_call_auction.trade_date IS '交易日期';
COMMENT ON COLUMN stock_call_auction.auction_time IS '竞价时间(HH:MM:SS)';
COMMENT ON COLUMN stock_call_auction.price IS '集合竞价价格';
COMMENT ON COLUMN stock_call_auction.volume IS '集合竞价成交量(股)';
COMMENT ON COLUMN stock_call_auction.amount IS '集合竞价成交额(元)';
COMMENT ON COLUMN stock_call_auction.buy_volume IS '买盘量(股)';
COMMENT ON COLUMN stock_call_auction.sell_volume IS '卖盘量(股)';
COMMENT ON COLUMN stock_call_auction.change_pct IS '涨跌幅(%)';
COMMENT ON COLUMN stock_call_auction.change_amount IS '涨跌额';
COMMENT ON COLUMN stock_call_auction.bid_ratio IS '委比(%)';
COMMENT ON COLUMN stock_call_auction.data_source IS '数据来源';
COMMENT ON COLUMN stock_call_auction.update_time IS '数据更新时间';