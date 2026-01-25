"""
腾讯财经数据源
提供实时行情数据
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

try:
    import aiohttp
    import json
except ImportError:
    aiohttp = None
    json = None
    logging.warning("aiohttp not installed, run: pip install aiohttp")

from ..data_source_base import DataSourceBase, DataSourcePriority

logger = logging.getLogger(__name__)


class TencentFinanceSource(DataSourceBase):
    """
    腾讯财经数据源
    实时行情延迟: ~1-3秒
    免费额度: 无限制
    """

    # 腾讯财经API端点
    REALTIME_URL = "https://qt.gtimg.cn/q="
    MINUTE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

    def __init__(self):
        super().__init__(
            name="TencentFinance",
            priority=DataSourcePriority.REALTIME
        )
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 HTTP 会话"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=5)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        """关闭连接"""
        if self.session and not self.session.closed:
            await self.session.close()

    def _format_code(self, code: str) -> str:
        """格式化股票代码
        腾讯格式: sh600000, sz000001
        """
        code = code.strip().upper()
        if code.startswith("6"):
            return f"sh{code}"
        elif code.startswith("0") or code.startswith("3"):
            return f"sz{code}"
        elif code.startswith("8") or code.startswith("4"):
            return f"bj{code}"
        return code

    async def get_realtime_quote(self, codes: List[str]) -> Dict[str, Any]:
        """
        获取实时行情

        返回格式:
        {
            "000001": {
                "name": "平安银行",
                "price": 11.23,
                "open": 11.20,
                "high": 11.30,
                "low": 11.15,
                "volume": 12345678,
                "amount": 1234567890.12,
                "change": 0.05,
                "change_pct": 0.45,
                "timestamp": "2026-01-23 14:30:00"
            }
        }
        """
        try:
            session = await self._get_session()

            # 格式化代码
            formatted_codes = [self._format_code(c) for c in codes]
            url = self.REALTIME_URL + ",".join(formatted_codes)

            async with session.get(url, headers={"Referer": "https://stockapp.finance.qq.com/"}) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")

                text = await response.text(encoding="gbk")

            return self._parse_realtime_data(text, codes)

        except Exception as e:
            logger.error(f"TencentFinance get_realtime_quote error: {e}")
            raise

    def _parse_realtime_data(self, data: str, original_codes: List[str]) -> Dict[str, Any]:
        """解析实时行情数据
        腾讯数据格式: v_sh600000="1~平安银行~11.23~..."
        """
        result = {}
        lines = data.strip().split('\n')

        for i, line in enumerate(lines):
            if not line or '=' not in line or '~' not in line:
                continue

            try:
                # 解析行
                parts = line.split('=')
                if len(parts) < 2:
                    continue

                code_with_prefix = parts[0].split('_')[-1].strip('"')
                content = parts[1].strip('"')

                if not content:
                    continue

                # 获取原始代码
                original_code = original_codes[i] if i < len(original_codes) else code_with_prefix[2:]

                fields = content.split('~')
                if len(fields) < 30:
                    continue

                # 解析字段
                result[original_code] = {
                    "name": fields[1],
                    "price": float(fields[3]) if fields[3] else None,
                    "close_prev": float(fields[4]) if fields[4] else None,
                    "open": float(fields[5]) if fields[5] else None,
                    "high": float(fields[33]) if fields[33] else None,
                    "low": float(fields[34]) if fields[34] else None,
                    "volume": int(fields[6]) if fields[6] else 0,
                    "amount": float(fields[37]) if fields[37] else 0,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "date": fields[30],
                    "time": fields[31],
                }

                # 计算涨跌幅
                if result[original_code]["price"] and result[original_code]["close_prev"]:
                    price = result[original_code]["price"]
                    close_prev = result[original_code]["close_prev"]
                    result[original_code]["change"] = round(price - close_prev, 2)
                    result[original_code]["change_pct"] = round(
                        (price - close_prev) / close_prev * 100, 2
                    )

            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse line: {line[:50]}, error: {e}")
                continue

        return result

    async def get_minute_kline(self, code: str) -> List[Dict[str, Any]]:
        """
        获取分钟K线

        参数:
            code: 股票代码

        返回:
            分钟K线数据列表
        """
        try:
            session = await self._get_session()

            formatted_code = self._format_code(code)
            url = (
                f"{self.MINUTE_URL}?"
                f"param={formatted_code},m1,,{self._get_current_date()}"
                f"&_var=m1_data"
                f"&callback=m1_data"
            )

            async with session.get(url) as response:
                if response.status != 200:
                    return []

                text = await response.text()

            # 解析JSONP响应
            if 'm1_data=' in text:
                json_str = text.split('m1_data=')[1].rstrip(';')
                data = json.loads(json_str)

                if data.get('code') == 0 and 'data' in data:
                    klines = []
                    for item in data['data'][formatted_code]['m1']:
                        klines.append({
                            'datetime': item[0],
                            'open': float(item[1]),
                            'close': float(item[2]),
                            'high': float(item[3]),
                            'low': float(item[4]),
                            'volume': int(item[5]),
                            'amount': float(item[6]),
                        })
                    return klines

        except Exception as e:
            logger.error(f"TencentFinance get_minute_kline error: {e}")

        return []

    async def get_daily_kline(
        self,
        code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """获取日K线
        腾讯财经日K数据较完整
        """
        try:
            session = await self._get_session()

            formatted_code = self._format_code(code)
            url = (
                f"{self.MINUTE_URL}?"
                f"param={formatted_code},day,{start_date},{end_date}"
                f"&_var=day_data"
            )

            async with session.get(url) as response:
                if response.status != 200:
                    return []

                text = await response.text()

            if 'day_data=' in text:
                json_str = text.split('day_data=')[1].rstrip(';')
                data = json.loads(json_str)

                if data.get('code') == 0 and 'data' in data:
                    klines = []
                    for item in data['data'][formatted_code]['day']:
                        klines.append({
                            'date': item[0],
                            'open': float(item[1]),
                            'close': float(item[2]),
                            'high': float(item[3]),
                            'low': float(item[4]),
                            'volume': int(item[5]),
                            'amount': float(item[6]),
                        })
                    return klines

        except Exception as e:
            logger.error(f"TencentFinance get_daily_kline error: {e}")

        return []

    def _get_current_date(self) -> str:
        """获取当前日期 YYYYMMDD"""
        return datetime.now().strftime("%Y%m%d")
