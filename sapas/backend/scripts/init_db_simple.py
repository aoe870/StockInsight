"""
SAPAS 数据库初始化脚本
简化版 - 直接使用数据库连接
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, os.path.join(str(Path(__file__).parent.parent), "backend"))

# 直接从数据库模块导入
import database

from models import Base


async def init_from_sql():
    """使用 SQL 脚本初始化数据库表"""
    print("Creating database tables from SQL script...")

    # 读取 SQL 脚本
    sql_file = Path(__file__).parent.join("init_db.sql")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    # 执行 SQL
    async with database.engine.begin() as conn:
        await conn.execute(text(sql_script))

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


async def drop_from_sql():
    """使用 SQL 脚本删除所有表（慎用）"""
    print("Dropping all tables from SQL script...")

    # 读取 SQL 脚本
    sql_file = Path(__file__).parent.join("drop_db.sql")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    # 执行 SQL
    async with database.engine.begin() as conn:
        await conn.execute(text(sql_script))

    print("All tables dropped!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        asyncio.run(drop_from_sql())
    else:
        asyncio.run(init_from_sql())
