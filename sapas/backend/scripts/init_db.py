"""
SAPAS 数据库初始化脚本
直接创建表，不使用 SQLAlchemy ORM
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 直接导入
from config import get_settings
from models import User, WatchlistGroup, WatchlistItem, Alert, AlertHistory, BacktestRun, BacktestTrade, ScreenerCondition

# 导入 SQL 执行模块
from sqlalchemy import text

# 创建异步引擎
engine = create_async_engine(get_settings().DATABASE_URL)


async def execute_sql_file():
    """直接执行 SQL 文件"""
    sql_file = Path(__file__).parent.joinpath("init_db.sql")
    if not sql_file.exists():
        print(f"SQL 文件不存在: {sql_file}")
        return

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    # 连接到数据库
    async with engine.begin() as conn:
        await conn.execute(text(sql_script))
        await conn.commit()
        print("Database SQL script executed successfully!")
        print("\nTables created:")
        tables = [
            "users",
            "watchlist_groups",
            "watchlist_items",
            "alerts",
            "alert_history",
            "backtest_runs",
            "backtest_trades",
            "screener_conditions"
        ]
        for table in tables:
            print(f"  - {table}")


async def create_tables():
    """创建所有表"""
    print("Creating database tables...")

    # 执行 SQL 文件
    await execute_sql_file()

    print("Database tables created successfully!")
    print("\nTables created:")
    tables = [
        "users",
        "watchlist_groups",
        "watchlist_items",
        "alerts",
        "alert_history",
        "backtest_runs",
        "backtest_trades",
        "screener_conditions"
    ]
    for table in tables:
        print(f"  - {table}")


async def drop_tables():
    """删除所有表（慎用）"""
    print("Dropping all tables...")

    # 直接执行 SQL DROP
    await engine.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    print("All tables dropped!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        asyncio.run(drop_tables())
    else:
        asyncio.run(create_tables())
