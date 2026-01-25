"""
多数据源测试脚本
测试各个数据源的可用性和性能
"""

import asyncio
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.multi_source import (
    init_data_sources,
    multi_source_manager,
    SinaFinanceSource,
    TencentFinanceSource,
    AKShareSource
)


async def test_individual_source(source, test_codes):
    """测试单个数据源"""
    print(f"\n{'='*60}")
    print(f"测试数据源: {source.name}")
    print(f"{'='*60}")

    # 测试实时行情
    print("\n[1] 测试实时行情...")
    try:
        start = datetime.now()
        quotes = await asyncio.wait_for(
            source.get_realtime_quote(test_codes),
            timeout=10.0
        )
        elapsed = (datetime.now() - start).total_seconds() * 1000

        if quotes:
            print(f"  ✓ 成功获取 {len(quotes)} 只股票数据")
            print(f"  ⏱ 响应时间: {elapsed:.0f}ms")
            for code, data in list(quotes.items())[:2]:
                print(f"    - {code}: {data.get('name')} = {data.get('price')}")
        else:
            print(f"  ✗ 返回空数据")
    except asyncio.TimeoutError:
        print(f"  ✗ 请求超时")
    except Exception as e:
        print(f"  ✗ 错误: {e}")

    # 测试分钟K线
    print("\n[2] 测试分钟K线...")
    try:
        start = datetime.now()
        klines = await asyncio.wait_for(
            source.get_minute_kline(test_codes[0]),
            timeout=15.0
        )
        elapsed = (datetime.now() - start).total_seconds() * 1000

        if klines:
            print(f"  ✓ 成功获取 {len(klines)} 条分钟K线")
            print(f"  ⏱ 响应时间: {elapsed:.0f}ms")
        else:
            print(f"  ⚠ 返回空数据（可能不支持）")
    except asyncio.TimeoutError:
        print(f"  ✗ 请求超时")
    except Exception as e:
        print(f"  ⚠ 错误: {e}")

    # 测试日K线
    print("\n[3] 测试日K线...")
    try:
        start = datetime.now()
        klines = await asyncio.wait_for(
            source.get_daily_kline(
                test_codes[0],
                "2026-01-01",
                "2026-01-23"
            ),
            timeout=20.0
        )
        elapsed = (datetime.now() - start).total_seconds() * 1000

        if klines:
            print(f"  ✓ 成功获取 {len(klines)} 条日K线")
            print(f"  ⏱ 响应时间: {elapsed:.0f}ms")
        else:
            print(f"  ⚠ 返回空数据（可能不支持）")
    except asyncio.TimeoutError:
        print(f"  ✗ 请求超时")
    except Exception as e:
        print(f"  ⚠ 错误: {e}")


async def test_manager():
    """测试多数据源管理器"""
    print(f"\n{'='*60}")
    print("测试多数据源管理器")
    print(f"{'='*60}")

    test_codes = ["000001", "600000", "600036"]

    # 测试实时行情（自动切换）
    print("\n[1] 测试自动切换获取实时行情...")
    start = datetime.now()
    quotes = await multi_source_manager.get_realtime_quote(test_codes)
    elapsed = (datetime.now() - start).total_seconds() * 1000

    if quotes:
        print(f"  ✓ 成功获取 {len(quotes)} 只股票数据")
        print(f"  ⏱ 响应时间: {elapsed:.0f}ms")
        for code, data in quotes.items():
            print(f"    - {code}: {data.get('name')} = {data.get('price')}")
    else:
        print(f"  ✗ 所有数据源均失败")

    # 查看数据源状态
    print("\n[2] 数据源状态:")
    status = multi_source_manager.get_source_status()
    for name, info in status.items():
        status_icon = "✓" if info["available"] else "✗"
        print(f"  {status_icon} {name}:")
        print(f"      优先级: {info['priority']}")
        print(f"      成功率: {info['success_rate']}")
        print(f"      响应时间: {info['avg_response_time']}")
        print(f"      状态: {'可用' if info['available'] else '不可用'}")

    # 健康检查
    print("\n[3] 健康检查...")
    health = await multi_source_manager.health_check_all()
    for name, status_obj in health.items():
        status_icon = "✓" if status_obj.available else "✗"
        print(f"  {status_icon} {name}: {'健康' if status_obj.available else '不健康'}")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("多数据源系统测试")
    print("=" * 60)

    # 初始化数据源
    print("\n初始化数据源...")
    init_data_sources()

    test_codes = ["000001", "600000"]  # 平安银行、浦发银行

    # 测试各个数据源
    sources = multi_source_manager.sources

    for source in sources:
        await test_individual_source(source, test_codes)
        await asyncio.sleep(1)  # 间隔1秒

    # 测试管理器
    await test_manager()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

    # 关闭连接
    for source in sources:
        if hasattr(source, 'close'):
            await source.close()


if __name__ == "__main__":
    asyncio.run(main())
