#!/usr/bin/env python
"""
资金流向数据获取脚本

用法:
    python scripts/fetch_fund_flow.py <股票代码> [选项]

示例:
    python scripts/fetch_fund_flow.py 000001
    python scripts/fetch_fund_flow.py 000001 --days 60
    python scripts/fetch_fund_flow.py 000001 --start 2024-01-01 --end 2024-12-31
"""

import argparse
import sys
from datetime import date, timedelta

# 添加项目路径
sys.path.insert(0, ".")

import akshare as ak
import pandas as pd


def fetch_fund_flow(code: str, market: str = None, days: int = 30,
                     start_date: str = None, end_date: str = None):
    """
    获取个股资金流向数据

    参数:
        code: 股票代码
        market: 市场 (sh/sz)，如果为None则自动判断
        days: 查询天数
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    返回:
        DataFrame: 资金流向数据
    """
    print(f"正在获取 {code} 的资金流向数据...")

    try:
        df = ak.stock_individual_fund_flow(stock=code, market=market)
        if df.empty:
            print(f"未获取到 {code} 的资金流向数据")
            return None

        # 过滤日期范围
        if start_date or end_date:
            df['日期'] = pd.to_datetime(df['日期'])
            if start_date:
                df = df[df['日期'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['日期'] <= pd.to_datetime(end_date)]
        else:
            # 取最近 days 天数据
            df = df.head(days)

        print(f"成功获取 {len(df)} 条数据")
        return df

    except Exception as e:
        print(f"获取资金流向数据失败: {e}")
        return None


def print_summary(df: pd.DataFrame, code: str):
    """打印资金流向汇总信息"""
    if df is None or df.empty:
        return

    print(f"\n{'='*60}")
    print(f"股票代码: {code}")
    print(f"数据日期范围: {df['日期'].min()} 至 {df['日期'].max()}")
    print(f"数据条数: {len(df)}")
    print(f"{'='*60}")

    # 计算汇总
    total_main = df['主力净流入-净额'].sum()
    total_super_large = df['超大单净流入-净额'].sum()
    total_large = df['大单净流入-净额'].sum()
    total_medium = df['中单净流入-净额'].sum()
    total_small = df['小单净流入-净额'].sum()

    print(f"\n资金流向汇总:")
    print(f"  主力净流入: {total_main/10000:.2f} 万元")
    print(f"  超大单净流入: {total_super_large/10000:.2f} 万元")
    print(f"  大单净流入: {total_large/10000:.2f} 万元")
    print(f"  中单净流入: {total_medium/10000:.2f} 万元")
    print(f"  小单净流入: {total_small/10000:.2f} 万元")

    # 最新一天的数据
    latest = df.iloc[0]
    print(f"\n最新交易日 ({latest['日期']}):")
    print(f"  收盘价: {latest['收盘价']}")
    print(f"  涨跌幅: {latest['涨跌幅']:.2f}%")
    print(f"  主力净流入: {latest['主力净流入-净额']/10000:.2f} 万元 ({latest['主力净流入-净占比']:.2f}%)")
    print(f"  超大单: {latest['超大单净流入-净额']/10000:.2f} 万元 ({latest['超大单净流入-净占比']:.2f}%)")
    print(f"  大单: {latest['大单净流入-净额']/10000:.2f} 万元 ({latest['大单净流入-净占比']:.2f}%)")
    print(f"  中单: {latest['中单净流入-净额']/10000:.2f} 万元 ({latest['中单净流入-净占比']:.2f}%)")
    print(f"  小单: {latest['小单净流入-净额']/10000:.2f} 万元 ({latest['小单净流入-净占比']:.2f}%)")
    print(f"{'='*60}\n")


def determine_market(code: str) -> str:
    """根据股票代码判断市场"""
    if code.startswith('6'):
        return 'sh'
    elif code.startswith(('0', '3')):
        return 'sz'
    elif code.startswith('8'):
        return 'bj'
    else:
        raise ValueError(f"无法判断股票代码 {code} 的市场")


def main():
    parser = argparse.ArgumentParser(description='获取个股资金流向数据')
    parser.add_argument('code', help='股票代码，如 000001')
    parser.add_argument('--market', choices=['sh', 'sz'], help='市场代码 (可选，默认自动判断)')
    parser.add_argument('--days', type=int, default=30, help='查询天数 (默认30)')
    parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--output', help='输出文件路径 (可选，保存为CSV)')

    args = parser.parse_args()

    # 判断市场
    market = args.market
    if not market:
        try:
            market = determine_market(args.code)
        except ValueError as e:
            print(f"错误: {e}")
            return

    # 获取数据
    df = fetch_fund_flow(args.code, market, args.days, args.start, args.end)

    if df is not None:
        # 打印汇总信息
        print_summary(df, args.code)

        # 保存到文件
        if args.output:
            df.to_csv(args.output, index=False, encoding='utf-8-sig')
            print(f"数据已保存到: {args.output}")
        else:
            # 打印前几行数据
            print("\n详细数据 (前5条):")
            print(df.head().to_string(index=False))


if __name__ == '__main__':
    main()
