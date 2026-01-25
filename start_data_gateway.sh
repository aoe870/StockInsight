#!/bin/bash
set -e

# ============================================================
# 数据网关服务启动脚本
# ============================================================
# 从项目根目录启动 data_gateway 服务
# 敏感信息（如 token、密码）应通过环境变量传递
# ============================================================

# 获取脚本所在目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR" && pwd)"

# 切换到 data_gateway 目录
cd "$PROJECT_ROOT/data_gateway"

echo "====================================================="
echo "  Data Gateway Service"
echo "====================================================="
echo "项目根目录: $PROJECT_ROOT"
echo "工作目录: $(pwd)"
echo ""

# 加载环境变量文件（如果存在）
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "加载 .env 配置文件..."
    # 只加载 DG_ 开头的配置，避免冲突
    export $(grep "^DG_" "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
fi

# ============================================================
# 环境变量配置（可覆盖默认值）
# ============================================================

# 服务配置
export DG_HOST=${DG_HOST:-0.0.0.0}
export DG_PORT=${DG_PORT:-8001}
export DG_DEBUG=${DG_DEBUG:-false}
export DG_LOG_LEVEL=${DG_LOG_LEVEL:-INFO}

# 数据库配置（必需）
if [ -z "$DG_DATABASE_URL" ]; then
    echo "错误: 必须设置 DG_DATABASE_URL 环境变量"
    echo "示例: DG_DATABASE_URL=postgresql+asyncpg://user:password@host:port/database"
    exit 1
fi

export DG_DATABASE_SYNC_URL=${DG_DATABASE_SYNC_URL:-$DG_DATABASE_URL}

# Redis 配置
export DG_REDIS_URL=${DG_REDIS_URL:-redis://localhost:6379/0}
export DG_REDIS_MESSAGE_QUEUE=${DG_REDIS_MESSAGE_QUEUE:-data-gateway:queue}
export DG_REDIS_QUOTE_CHANNEL_PREFIX=${DG_REDIS_QUOTE_CHANNEL_PREFIX:-quote}

# 缓存配置
export DG_CACHE_TTL_REALTIME=${DG_CACHE_TTL_REALTIME:-5}
export DG_CACHE_TTL_KLINE=${DG_CACHE_TTL_KLINE:-60}

# 数据源配置
export DG_AKSHARE_ENABLED=${DG_AKSHARE_ENABLED:-true}
export DG_BAOSTOCK_ENABLED=${DG_BAOSTOCK_ENABLED:-true}
export DG_MIANA_TOKEN=${DG_MIANA_TOKEN:-""}

# 限流配置
export DG_RATE_LIMIT_PER_MINUTE=${DG_RATE_LIMIT_PER_MINUTE:-120}
export DG_RATE_LIMIT_PER_HOUR=${DG_RATE_LIMIT_PER_HOUR:-1000}

# 日志配置
export DG_LOG_FILE=${DG_LOG_FILE:-logs/data_gateway.log}

# ============================================================
# 显示配置信息
# ============================================================
echo ""
echo "服务配置:"
echo "  - HOST: $DG_HOST"
echo "  - PORT: $DG_PORT"
echo "  - DEBUG: $DG_DEBUG"
echo "  - LOG_LEVEL: $DG_LOG_LEVEL"
echo ""
echo "数据源配置:"
echo "  - AKShare: $DG_AKSHARE_ENABLED"
echo "  - BaoStock: $DG_BAOSTOCK_ENABLED"
echo "  - Miana Token: ${DG_MIANA_TOKEN:+已配置}${DG_MIANA_TOKEN:-未配置}"
echo ""
echo "====================================================="
echo ""

# ============================================================
# 启动服务
# ============================================================
# 将日志级别转换为小写 (uvicorn 要求)
LOG_LEVEL=$(echo "$DG_LOG_LEVEL" | tr '[:upper:]' '[:lower:]')
exec python -m uvicorn src.main:app --host "$DG_HOST" --port "$DG_PORT" --log-level "$LOG_LEVEL"
