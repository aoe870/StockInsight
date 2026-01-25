-- ============================================================
-- 数据同步任务表
-- 用于跟踪和管理数据同步任务
-- ============================================================

-- 同步任务主表
CREATE TABLE IF NOT EXISTS dg_sync_tasks (
    task_id VARCHAR(50) PRIMARY KEY,
    sync_type VARCHAR(20) NOT NULL,              -- 同步类型: full, incremental, symbol
    market_code VARCHAR(20) NOT NULL,             -- 市场代码
    period_type VARCHAR(20) DEFAULT 'daily',      -- 周期类型
    start_date DATE,                              -- 开始日期
    end_date DATE,                                -- 结束日期
    symbols JSONB,                                -- 股票列表
    total_symbols INTEGER DEFAULT 0,              -- 总股票数
    status VARCHAR(20) NOT NULL,                  -- 状态: pending, running, completed, failed, cancelled
    progress INTEGER DEFAULT 0,                   -- 进度 (0-100)
    current_symbol VARCHAR(20),                   -- 当前处理的股票
    success_count INTEGER DEFAULT 0,              -- 成功数量
    failed_count INTEGER DEFAULT 0,               -- 失败数量
    total_records INTEGER DEFAULT 0,              -- 总记录数
    error_message TEXT,                           -- 错误信息
    result JSONB,                                 -- 结果详情
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at_ts TIMESTAMP,
    completed_at_ts TIMESTAMP
);

CREATE INDEX idx_dg_sync_tasks_status ON dg_sync_tasks(status);
CREATE INDEX idx_dg_sync_tasks_market ON dg_sync_tasks(market_code);
CREATE INDEX idx_dg_sync_tasks_created ON dg_sync_tasks(created_at_ts DESC);

-- 同步任务明细表（记录每个股票的同步情况）
CREATE TABLE IF NOT EXISTS dg_sync_task_items (
    item_id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(50) REFERENCES dg_sync_tasks(task_id) ON DELETE CASCADE,
    symbol_code VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,                  -- success, failed, no_data
    records_count INTEGER DEFAULT 0,              -- 获取的记录数
    date_range VARCHAR(50),                       -- 日期范围
    error_message TEXT,                           -- 错误信息
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dg_sync_task_items_task ON dg_sync_task_items(task_id);
CREATE INDEX idx_dg_sync_task_items_symbol ON dg_sync_task_items(symbol_code);

-- 同步配置表
CREATE TABLE IF NOT EXISTS dg_sync_config (
    config_id SERIAL PRIMARY KEY,
    market_code VARCHAR(20) NOT NULL UNIQUE,
    auto_sync_enabled BOOLEAN DEFAULT false,      -- 是否自动同步
    sync_frequency VARCHAR(20) DEFAULT 'daily',   -- 同步频率: daily, weekly, monthly
    sync_hour INTEGER DEFAULT 0,                  -- 同步小时 (0-23) - 每日0点执行
    sync_minute INTEGER DEFAULT 0,                -- 同步分钟 (0-59)
    default_period VARCHAR(20) DEFAULT 'daily',   -- 默认周期
    retention_days INTEGER DEFAULT 365,           -- 数据保留天数
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 同步日志表
CREATE TABLE IF NOT EXISTS dg_sync_logs (
    log_id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(50),
    market_code VARCHAR(20) NOT NULL,
    log_level VARCHAR(10) NOT NULL,               -- INFO, WARNING, ERROR
    message TEXT NOT NULL,
    details JSONB,
    created_at_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dg_sync_logs_task ON dg_sync_logs(task_id);
CREATE INDEX idx_dg_sync_logs_created ON dg_sync_logs(created_at_ts DESC);

-- 触发器: 自动更新 updated_at_ts
CREATE TRIGGER trg_dg_sync_config_updated_at BEFORE UPDATE ON dg_sync_config
    FOR EACH ROW EXECUTE FUNCTION dg_update_updated_at();
