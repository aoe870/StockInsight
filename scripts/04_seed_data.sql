-- ============================================================
-- SAPAS 初始化数据脚本
-- 数据库: PostgreSQL 14+
-- 创建日期: 2026-01-13
-- 更新日期: 2026-01-15
-- ============================================================

-- ============================================================
-- 创建默认管理员用户
-- 密码为 'admin123' 的 bcrypt 哈希 (使用 bcrypt 库直接生成)
-- ============================================================
INSERT INTO users (id, username, email, password_hash, nickname, role, notify_channel, is_active)
VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'admin',
    'admin@example.com',
    '$2b$12$Sz/Z7r/o5mJSSRqDY7BJOOrDPtsiujRV.kPt8hQMMLqJPhrB5sdVm',
    '管理员',
    'admin',
    'console',
    TRUE
) ON CONFLICT (username) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    nickname = EXCLUDED.nickname,
    role = EXCLUDED.role;

-- ============================================================
-- 创建默认全局告警规则
-- ============================================================

-- 规则1：成交量异动（放量2倍以上）
INSERT INTO alert_rules (stock_code, rule_type, rule_name, conditions, is_enabled, cooldown_minutes)
VALUES (
    NULL,  -- 全局规则
    'VOLUME_SURGE',
    '成交量异动告警',
    '{
        "volume_ratio": 2.0,
        "compare_days": 5,
        "description": "成交量较前5日均值放大2倍以上"
    }'::JSONB,
    TRUE,
    60
) ON CONFLICT DO NOTHING;

-- 规则2：RSI超买
INSERT INTO alert_rules (stock_code, rule_type, rule_name, conditions, is_enabled, cooldown_minutes)
VALUES (
    NULL,
    'RSI_EXTREME',
    'RSI超买告警',
    '{
        "rsi_period": 14,
        "overbought_threshold": 80,
        "description": "RSI(14)超过80进入超买区"
    }'::JSONB,
    TRUE,
    120
) ON CONFLICT DO NOTHING;

-- 规则3：RSI超卖
INSERT INTO alert_rules (stock_code, rule_type, rule_name, conditions, is_enabled, cooldown_minutes)
VALUES (
    NULL,
    'RSI_EXTREME',
    'RSI超卖告警',
    '{
        "rsi_period": 14,
        "oversold_threshold": 20,
        "description": "RSI(14)低于20进入超卖区"
    }'::JSONB,
    TRUE,
    120
) ON CONFLICT DO NOTHING;

-- 规则4：MACD金叉
INSERT INTO alert_rules (stock_code, rule_type, rule_name, conditions, is_enabled, cooldown_minutes)
VALUES (
    NULL,
    'MACD_SIGNAL',
    'MACD金叉告警',
    '{
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
        "cross_type": "golden",
        "description": "MACD线上穿信号线，低位金叉"
    }'::JSONB,
    TRUE,
    240
) ON CONFLICT DO NOTHING;

-- 规则5：布林带突破上轨
INSERT INTO alert_rules (stock_code, rule_type, rule_name, conditions, is_enabled, cooldown_minutes)
VALUES (
    NULL,
    'BOLLINGER_BREAK',
    '布林带突破上轨',
    '{
        "period": 20,
        "std_dev": 2,
        "break_direction": "upper",
        "description": "股价突破布林带上轨"
    }'::JSONB,
    TRUE,
    60
) ON CONFLICT DO NOTHING;

-- 规则6：均线金叉（MA5上穿MA20）
INSERT INTO alert_rules (stock_code, rule_type, rule_name, conditions, is_enabled, cooldown_minutes)
VALUES (
    NULL,
    'MA_CROSS',
    'MA5/MA20金叉告警',
    '{
        "short_period": 5,
        "long_period": 20,
        "cross_type": "golden",
        "description": "5日均线上穿20日均线"
    }'::JSONB,
    TRUE,
    240
) ON CONFLICT DO NOTHING;

-- ============================================================
-- 让默认用户订阅所有全局规则（控制台通知）
-- ============================================================
INSERT INTO subscriptions (user_id, rule_id, channel, is_active)
SELECT 
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'::UUID,
    r.id,
    'console',
    TRUE
FROM alert_rules r
WHERE r.stock_code IS NULL
ON CONFLICT DO NOTHING;

-- ============================================================
-- 显示初始化完成信息
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '初始化数据完成！';
    RAISE NOTICE '默认用户: admin / admin123';
    RAISE NOTICE '已创建 % 条全局告警规则', (SELECT COUNT(*) FROM alert_rules WHERE stock_code IS NULL);
END $$;

