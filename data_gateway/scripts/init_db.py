#!/usr/bin/env python3
"""
数据库初始化脚本
用于创建 data_gateway 数据库和表结构
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg


async def create_database():
    """创建数据库"""
    print("[1/4] 检查数据库...")

    # 连接到 postgres 默认数据库
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="root",
        password="J7aXgk2BJUj=",
        database="postgres"
    )

    try:
        # 检查数据库是否存在
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = 'data_gateway')"
        )

        if not exists:
            print("[i] 创建数据库 data_gateway...")
            await conn.execute("CREATE DATABASE data_gateway")
            print("[√] 数据库创建成功")
        else:
            print("[√] 数据库已存在")
    finally:
        await conn.close()


async def execute_sql_file(conn, sql_file: str, description: str):
    """执行SQL文件"""
    print(f"[i] {description}...")

    sql_path = Path(__file__).parent / "sql" / sql_file
    if not sql_path.exists():
        print(f"[!] SQL文件不存在: {sql_path}")
        return

    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    try:
        await conn.execute(sql_content)
        print(f"[√] {description}成功")
    except Exception as e:
        print(f"[X] {description}失败: {e}")
        raise


async def create_tables():
    """创建表结构"""
    print("\n[2/4] 创建数据表...")

    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="root",
        password="J7aXgk2BJUj=",
        database="data_gateway"
    )

    try:
        # 执行建表SQL
        await execute_sql_file(conn, "01_create_tables.sql", "创建表")
    finally:
        await conn.close()


async def create_functions():
    """创建函数和存储过程"""
    print("\n[3/4] 创建函数和存储过程...")

    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="root",
        password="J7aXgk2BJUj=",
        database="data_gateway"
    )

    try:
        # 执行函数SQL
        await execute_sql_file(conn, "02_create_functions.sql", "创建函数")
    finally:
        await conn.close()


async def create_sync_tables():
    """创建同步任务表"""
    print("\n[4/5] 创建同步任务表...")

    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="root",
        password="J7aXgk2BJUj=",
        database="data_gateway"
    )

    try:
        # 执行同步表SQL
        await execute_sql_file(conn, "03_create_sync_tables.sql", "创建同步表")
    finally:
        await conn.close()


async def verify_installation():
    """验证安装"""
    print("\n[5/5] 验证安装...")

    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="root",
        password="J7aXgk2BJUj=",
        database="data_gateway"
    )

    try:
        # 查询版本
        version = await conn.fetchval("SELECT version()")
        print(f"[√] 数据库连接成功")
        print(f"    PostgreSQL 版本: {version.split(',')[0]}")

        # 列出所有表
        tables = await conn.fetch("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)

        print(f"\n[i] 已创建 {len(tables)} 个表:")
        for table in tables:
            print(f"    - {table['tablename']}")

        # 列出所有函数
        functions = await conn.fetch("""
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_schema = 'public'
              AND routine_type = 'FUNCTION'
            ORDER BY routine_name
        """)

        print(f"\n[i] 已创建 {len(functions)} 个函数:")
        for func in functions[:10]:  # 只显示前10个
            print(f"    - {func['routine_name']}")

        if len(functions) > 10:
            print(f"    ... 还有 {len(functions) - 10} 个函数")

        # 检查初始数据
        data_sources = await conn.fetchval("SELECT COUNT(*) FROM dg_sources")
        print(f"\n[i] 数据源配置: {data_sources} 条")

        return True

    except Exception as e:
        print(f"[X] 验证失败: {e}")
        return False

    finally:
        await conn.close()


async def main():
    """主函数"""
    print("=" * 60)
    print("  数据网关服务 - 数据库初始化")
    print("=" * 60)
    print()

    try:
        await create_database()
        await create_tables()
        await create_functions()
        await create_sync_tables()
        success = await verify_installation()

        print()
        print("=" * 60)
        if success:
            print("  [OK] 数据库初始化完成")
            print("")
            print("  数据库信息:")
            print("    - 数据库名: data_gateway")
            print("    - 用户: root")
            print("    - 端口: 5432")
            print("")
            print("  下一步:")
            print("    1. 启动服务: python -m uvicorn src.main:app --reload")
            print("    2. 访问文档: http://localhost:8001/docs")
        else:
            print("  [ERROR] 数据库初始化失败")
        print("=" * 60)

        return 0 if success else 1

    except Exception as e:
        print(f"\n[X] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
