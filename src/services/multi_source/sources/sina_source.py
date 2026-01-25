"""
新浪财经数据源
提供秒级实时行情数据
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

try:
    import aiohttp
except ImportError:
    aiohttp = None
    logging.warning("aiohttp not installed, run: pip install aiohttp")

from ..data_source_base import DataSourceBase, DataSourcePriority

logger = logging.getLogger(__name__)


class SinaFinanceSource(DataSourceBase):
    """
    新浪财经数据源
    实时行情延迟: ~1-3秒
    免费额度: 无限制
    """

    # 新浪财经API端点
    REALTIME_URL = "https://hq.sinajs.cn/list="
    MARKET_URL = "https://hq.sinajs.cn/list=s_sh000001,s_sz399001"

    # 股票代码前缀映射
    MARKET_PREFIX = {
        "sh": "sh",  # 上海
        "sz": "sz",  # 深圳
        "bj": "bj",  # 北京
    }

    def __init__(self):
        super().__init__(
            name="SinaFinance",
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
        """格式化股票代码"""
        # 移除前缀，判断市场
        code = code.strip().upper()
        if code.startswith("6"):
            return f"sh{code}"
        elif code.startswith("0") or code.startswith("3"):
            return f"sz{code}"
        elif code.startswith("8") or code.startswith("4"):
            return f"bj{code}"
        else:
            # 已有前缀
            if code[:2] in self.MARKET_PREFIX.values():
                return code
            return f"sh{code}"

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
                "bid": [11.22, 11.21, 11.20],
                "ask": [11.24, 11.25, 11.26],
                "timestamp": "2026-01-23 14:30:00"
            }
        }
        """
        try:
            session = await self._get_session()

            # 格式化代码
            formatted_codes = [self._format_code(c) for c in codes]
            url = self.REALTIME_URL + ",".join(formatted_codes)

            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")

                text = await response.text(encoding="gbk")

            return self._parse_realtime_data(text, codes)

        except Exception as e:
            logger.error(f"SinaFinance get_realtime_quote error: {e}")
            raise

    def _parse_realtime_data(self, data: str, original_codes: List[str]) -> Dict[str, Any]:
        """解析实时行情数据"""
        result = {}
        lines = data.strip().split('\n')

        for i, line in enumerate(lines):
            if not line or '=' not in line:
                continue

            try:
                # 数据格式: var hq_str_sh600000="平安银行,11.23,11.20,...
                parts = line.split('=')
                if len(parts) < 2:
                    continue

                code_with_prefix = parts[0].split('_')[-1]
                content = parts[1].strip('"')

                if not content:
                    continue

                # 获取原始代码
                original_code = original_codes[i] if i < len(original_codes) else code_with_prefix[2:]

                fields = content.split(',')
                if len(fields) < 32:
                    continue

                # 解析字段
                result[original_code] = {
                    "name": fields[0],
                    "open": float(fields[1]) if fields[1] else None,
                    "close_prev": float(fields[2]) if fields[2] else None,
                    "price": float(fields[3]) if fields[3] else None,
                    "high": float(fields[4]) if fields[4] else None,
                    "low": float(fields[5]) if fields[5] else None,
                    "bid": float(fields[6]) if fields[6] else None,
                    "ask": float(fields[7]) if fields[7] else None,
                    "volume": int(fields[8]) if fields[8] else 0,
                    "amount": float(fields[9]) if fields[9] else 0,
                    "bid_volume": [
                        int(fields[10]) if fields[10] else 0,
                        int(fields[12]) if fields[12] else 0,
                        int(fields[14]) if fields[14] else 0,
                        int(fields[16]) if fields[16] else 0,
                        int(fields[18]) if fields[18] else 0,
                    ],
                    "bid_price": [
                        float(fields[11]) if fields[11] else None,
                        float(fields[13]) if fields[13] else None,
                        float(fields[15]) if fields[15] else None,
                        float(fields[17]) if fields[17] else None,
                        float(fields[19]) if fields[19] else None,
                    ],
                    "ask_volume": [
                        int(fields[20]) if fields[20] else 0,
                        int(fields[22]) if fields[22] else 0,
                        int(fields[24]) if fields[24] else 0,
                        int(fields[26]) if fields[26] else 0,
                        int(fields[28]) if fields[28] else 0,
                    ],
                    "ask_price": [
                        float(fields[21]) if fields[21] else None,
                        float(fields[23]) if fields[23] else None,
                        float(fields[25]) if fields[25] else None,
                        float(fields[27]) if fields[27] else None,
                        float(fields[29]) if fields[29] else None,
                    ],
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
        新浪财经不直接提供分钟K，需要通过其他方式
        返回空列表，让管理器尝试下一个数据源
        """
        logger.debug("SinaFinance does not support minute kline")
        return []

    async def get_daily_kline(
        self,
        code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        获取日K线
        新浪财经历史数据有限，建议使用其他数据源
        """
        logger.debug("SinaFinance daily kline is limited, try other sources")
        return []

    async def get_index_data(self) -> Dict[str, Any]:
        """获取指数数据"""
        try:
            session = await self._get_session()
            async with session.get(self.MARKET_URL) as response:
                text = await response.text(encoding="gbk")
                return self._parse_realtime_data(text, ["sh000001", "sz399001"])
        except Exception as e:
            logger.error(f"Failed to get index data: {e}")
            return {}
