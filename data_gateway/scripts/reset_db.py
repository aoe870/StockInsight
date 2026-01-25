#!/usr/bin/env python3
"""
重置数据网关数据库
删除并重建 data_gateway 数据库
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg


async def reset_database():
    """重置数据库"""
    print("[*] 重置数据网关数据库...")
    print()

    # 连接到 postgres 默认数据库
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="root",
        password="J7aXgk2BJUj=",
        database="postgres"
    )

    try:
        # 终止所有连接
        await conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'data_gateway' AND pid <> pg_backend_pid()")

        # 删除数据库
        print("[i] 删除数据库 data_gateway...")
        await conn.execute("DROP DATABASE IF EXISTS data_gateway")
        print("[√] 数据库已删除")

        # 重新创建
        print("[i] 重新创建数据库 data_gateway...")
        await conn.execute("CREATE DATABASE data_gateway")
        print("[√] 数据库已创建")

        # 检查是否成功
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = 'data_gateway')"
        )

        if exists:
            print("\n[√] 数据库重置成功！")
            print("\n下一步:")
            print("  python scripts/init_db.py")
            return True
        else:
            print("\n[X] 数据库创建失败")
            return False

    except Exception as e:
        print(f"\n[X] 重置失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await conn.close()


if __name__ == "__main__":
    success = asyncio.run(reset_database())
    sys.exit(0 if success else 1)
