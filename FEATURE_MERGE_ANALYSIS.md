# SAPAS vs InStock 功能对比与合并建议

## 📊 执行摘要

本文档对比分析了 SAPAS（StockInsight）与 [InStock](https://github.com/myhhub/stock) 两个股票分析平台的功能，识别可借鉴的功能，并制定详细的合并实施计划。

**分析日期**: 2026-01-23
**InStock 仓库**: https://github.com/myhhub/stock

---

## 📈 项目功能对比

### SAPAS (StockInsight) 现有功能

| 模块 | 功能 | 状态 | 技术栈 |
|------|------|------|--------|
| **数据获取** | AKShare API 集成 | ✅ 已实现 | Python + AKShare |
| **基础数据** | 股票列表、日K线、分时 | ✅ 已实现 | FastAPI + PostgreSQL |
| **技术指标** | MA, MACD, KDJ, RSI, BOLL 等 | ✅ 已实现 | Pandas-TA |
| **回测系统** | 基于 Backtrader 的策略回测 | ✅ 已实现 | Backtrader + Matplotlib |
| **选股器** | 技术指标选股 | ✅ 已实现 | Pandas + NumPy |
| **告警系统** | 价格和技术指标告警 | ✅ 已实现 | APScheduler |
| **自选股** | 自选股管理和监控 | ✅ 已实现 | PostgreSQL |
| **资金流向** | 个股资金流向分析 | ✅ 已实现 | AKShare API |
| **集合竞价** | 集合竞价数据分析 | ✅ 已实现 | 东方财富网 API |
| **WebSocket** | 实时行情推送 | ✅ 已实现 | WebSocket + Redis |
| **用户系统** | 登录、权限管理 | ✅ 已实现 | JWT + Pydantic |
| **前端界面** | Vue 3 + Element Plus | ✅ 已实现 | Vue 3 + TypeScript |

### InStock (myhhub/stock) 核心功能

| 模块 | 功能 | 价值 | 优先级 |
|------|------|------|--------|
| **综合选股** | 200+ 信息维度的多维度选股 | ⭐⭐⭐⭐⭐ | 🔴 高 |
| **K线形态识别** | 61种 K线形态自动识别 | ⭐⭐⭐⭐⭐ | 🔴 高 |
| **筹码分析** | CYQ 筹码分布分析 | ⭐⭐⭐⭐⭐ | 🔴 高 |
| **龙虎榜** | 每日龙虎榜数据 | ⭐⭐⭐⭐ | 🟡 中 |
| **资金流向** | 大单资金流向分析（更细致） | ⭐⭐⭐⭐ | 🟡 中 |
| **跌停分析** | 跌停原因分析 | ⭐⭐⭐⭐ | 🟡 中 |
| **量化策略** | 10+ 内置交易策略 | ⭐⭐⭐⭐⭐ | 🟢 低 |
| **自动化交易** | IPO 申购、策略自动执行 | ⭐⭐⭐⭐⭐ | 🟢 低 |
| **大单分析** | 细分大单类型分析 | ⭐⭐⭐⭐ | 🟢 低 |
| **ETF 数据** | ETF 行情、持仓、净值 | ⭐⭐⭐⭐ | 🟢 低 |

---

## 🎯 推荐合并的功能（按优先级）

### 🔴 高优先级（立即实施）

#### 1. K线形态识别 (61种)

**功能描述**：自动识别 K 线图中的技术形态，如三只乌鸦、早晨之星、锤子线等，提供买卖信号

**商业价值**：
- 辅助交易决策，提供形态买入/卖出信号
- 结合现有技术指标，提升信号准确率
- 提供更直观的技术分析

**技术实现复杂度**：中高

**关键形态列表**（优先实现前10个）：

| 序号 | 形态名称 | 类型 | 信号 |
|------|---------|------|------|
| 1 | 三只乌鸦 | 看跌 | sell |
| 2 | 早晨之星 | 看涨 | buy |
| 3 | 黄昏之星 | 看跌 | sell |
| 4 | 射击之星 | 反转 | 中性 |
| 5 | 锤子线 | 反转 | 中性 |
| 6 | 流星线 | 反转 | 中性 |
| 7 | 孕婴 | 反转 | 中性 |
| 8 | 吞孕 | 看涨 | buy |
| 9 | 红三兵 | 看涨 | buy |
| 10 | 三白兵 | 看涨 | buy |

**数据模型设计**：

```python
# src/models/pattern.py
from sqlalchemy import Column, BigInteger, String, Date, Integer, Text, JSON
from sqlalchemy.orm import Mapped

class StockPattern(Base, TimestampMixin):
    """K线形态数据表"""
    __tablename__ = "stock_patterns"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    trade_date: Mapped[date] = Column(Date, nullable=False, index=True)
    pattern_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 形态类型
    pattern_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 形态名称
    signal: Mapped[str] = mapped_column(String(20), nullable=False)  # buy/sell/neutral
    reliability: Mapped[int] = mapped_column(Integer, nullable=False, default=50)  # 可靠性评分 0-100
    pattern_data: Mapped[dict] = mapped_column(JSON, nullable=True)  # 形态详细数据
    detected_at: Mapped[datetime] = Column(DateTime, nullable=False, default=datetime.now)

    # 复合索引
    __table_args__ = (
        Index("idx_pattern_code_date", "code", "trade_date"),
        Index("idx_pattern_signal", "pattern_type", "signal"),
    )
```

**API 端点设计**：

```python
# src/api/patterns.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/patterns", tags=["patterns"])

@router.get("/stock/{code}/patterns", response_model=List[PatternResponse])
async def get_stock_patterns(
    code: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    signal: Optional[str] = Query(None, description="过滤信号类型: buy/sell/neutral"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定股票的K线形态数据

    参数:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        signal: 信号类型过滤
    """
    query = select(StockPattern).where(StockPattern.code == code)

    if start_date:
        query = query.where(StockPattern.trade_date >= start_date)
    if end_date:
        query = query.where(StockPattern.trade_date <= end_date)
    if signal:
        query = query.where(StockPattern.signal == signal)

    query = query.order_by(StockPattern.trade_date.desc())

    result = await db.execute(query)
    return result.scalars().all()

@router.get("/patterns/latest", response_model=PatternSummary)
async def get_latest_patterns(
    signal: Optional[str] = Query(None, description="过滤信号类型"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取最新的形态信号"""
    query = select(StockPattern, StockBasics.name).join(
        StockBasics, StockPattern.code == StockBasics.code
    ).order_by(StockPattern.trade_date.desc(), StockPattern.detected_at.desc())

    if signal:
        query = query.where(StockPattern.signal == signal)

    query = query.limit(limit)

    result = await db.execute(query)
    return result.all()
```

**前端展示组件**：

```vue
<!-- web/src/components/PatternIndicator.vue -->
<template>
  <div class="pattern-indicator">
    <el-tag
      v-if="pattern"
      :type="getTagType(pattern.signal)"
      size="small"
      effect="dark"
    >
      {{ pattern.pattern_name }}
    </el-tag>
    <span class="reliability">{{ pattern.reliability }}%</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PatternData } from '@/api/patterns'

const props = defineProps<{
  pattern: PatternData | null
}>()

const getTagType = (signal: string) => {
  if (signal === 'buy') return 'success'
  if (signal === 'sell') return 'danger'
  return 'info'
}
</script>
```

**形态识别核心逻辑**：

```python
# src/services/pattern_recognizer.py
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable

class PatternRecognizer:
    """K线形态识别器"""

    # 形态识别函数映射
    PATTERNS: Dict[str, Callable] = {}

    def __init__(self):
        self._init_patterns()

    def _init_patterns(self):
        """初始化所有形态识别函数"""
        self.PATTERNS = {
            'two_crows': self.check_two_crows,
            'three_crows': self.check_three_crows,
            'three_white_soldiers': self.check_three_white_soldiers,
            'morning_star': self.check_morning_star,
            'evening_star': self.check_evening_star,
            'doji': self.check_doji,
            'hammer': self.check_hammer,
            'inverted_hammer': self.check_inverted_hammer,
            'engulfing': self.check_engulfing,
            'harami': self.check_harami,
            'piercing': self.check_piercing,
            # ... 更多形态
        }

    def recognize(
        self,
        df: pd.DataFrame,
        patterns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        识别K线数据中的形态

        参数:
            df: K线数据，需包含 open, close, high, low, volume
            patterns: 要识别的形态列表，None表示识别所有
        """
        if patterns is None:
            patterns = list(self.PATTERNS.keys())

        results = []

        for pattern_name in patterns:
            if pattern_name in self.PATTERNS:
                pattern_func = self.PATTERNS[pattern_name]
                signals = pattern_func(df)
                results.append(signals)

        # 合并所有信号
        all_signals = pd.concat(results, axis=1)
        return all_signals

    def check_two_crows(self, df: pd.DataFrame) -> pd.Series:
        """
        三只乌鸦形态
        条件:
        1. 连续三根阴线
        2. 每日收盘价低于前一日
        3. 每日收盘价接近当日最低价
        4. 实体部分较小
        """
        # 实现逻辑
        pass

    def check_morning_star(self, df: pd.DataFrame) -> pd.Series:
        """
        早晨之星形态
        条件:
        1. 第一天阴线，第二天小实体（十字星），第三天阳线
        2. 第三天收盘价高于第一天实体中部
        3. 成交量萎缩后放大
        """
        # 实现逻辑
        pass
```

**数据同步方案**：

```python
# src/services/sync_patterns.py
from src.services.data_sync import data_sync_service

class PatternSyncService:
    """形态数据同步服务"""

    async def sync_patterns_for_stock(
        self,
        session: AsyncSession,
        code: str,
        start_date: date,
        end_date: date
    ):
        """
        同步指定股票的K线形态数据
        """
        # 1. 获取K线数据
        kline_data = await self._get_kline_data(session, code, start_date, end_date)

        # 2. 转换为DataFrame
        df = pd.DataFrame([{
            'trade_date': k.trade_date,
            'open': float(k.open_price) if k.open_price else None,
            'close': float(k.close_price) if k.close_price else None,
            'high': float(k.high_price) if k.high_price else None,
            'low': float(k.low_price) if k.low_price else None,
            'volume': k.volume,
        } for k in kline_data])

        # 3. 识别形态
        recognizer = PatternRecognizer()
        patterns = recognizer.recognize(df)

        # 4. 保存到数据库
        for trade_date, pattern_signals in patterns.items():
            for pattern_name, signal in pattern_signals.items():
                if signal != 'neutral':
                    # 检查是否已存在
                    existing = await session.execute(
                        select(StockPattern).where(
                            and_(
                                StockPattern.code == code,
                                StockPattern.trade_date == trade_date,
                                StockPattern.pattern_name == pattern_name
                            )
                        ).exists()
                    )

                    if not existing.scalars():
                        pattern = StockPattern(
                            code=code,
                            trade_date=trade_date,
                            pattern_type=pattern_name,
                            pattern_name=pattern_name,
                            signal=signal,
                            reliability=70
                        )
                        session.add(pattern)

        await session.commit()
```

#### 2. 筹码分布分析 (CYQ)

**功能描述**：基于成交量和价格计算筹码分布，识别主力成本区和支撑/阻力位

**商业价值**：
- 识别主力成本区
- 预测股价支撑位和压力位
- 辅助判断买卖时机
- 可视化筹码分布图

**技术实现复杂度**：中

**数据模型设计**：

```python
# src/models/cyq.py
from sqlalchemy import Column, BigInteger, String, Date, Decimal, Integer, JSON

class StockCYQ(Base, TimestampMixin):
    """筹码分布数据表"""
    __tablename__ = "stock_cyq"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    trade_date: Mapped[date] = Column(Date, nullable=False, index=True)
    price_level: Mapped[Decimal] = Column(Decimal(12, 4), nullable=False)  # 价格区间
    volume: Mapped[bigint] = Column(BigInteger, nullable=False)  # 成交量
    amount: Mapped[Decimal] = Column(Decimal(18, 4))  # 成交额
    percentage: Mapped[Decimal] = Column(Decimal(10, 4))  # 占比
    avg_cost: Mapped[Decimal] = Column(Decimal(12, 4))  # 平均成本

    # 复合索引
    __table_args__ = (
        Index("idx_cyq_code_date", "code", "trade_date"),
        Index("idx_cyq_date", "trade_date"),
    )
```

**核心计算逻辑**：

```python
# src/services/cyq_analyzer.py
import pandas as pd
import numpy as np
from typing import List, Tuple, Dict

class CYQAnalyzer:
    """筹码分布分析器"""

    def __init__(self, price_bins: int = 100):
        """
        初始化

        参数:
            price_bins: 价格区间数量
        """
        self.price_bins = price_bins

    def calculate_distribution(
        self,
        kline_data: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        计算筹码分布

        参数:
            kline_data: K线数据，需包含 close, volume, amount

        返回:
            (分布DataFrame, 统计信息Dict)
        """
        # 1. 创建价格区间
        min_price = kline_data['close'].min()
        max_price = kline_data['close'].max()
        bin_size = (max_price - min_price) / self.price_bins

        # 2. 统计每个区间的成交量
        distribution = {}
        total_volume = 0
        total_amount = 0

        for _, row in kline_data.iterrows():
            close_price = row['close']
            volume = row['volume']
            amount = row.get('amount', 0)

            # 确定价格区间
            bin_key = int((close_price - min_price) / bin_size) * bin_size + min_price

            if bin_key not in distribution:
                distribution[bin_key] = {
                    'volume': 0,
                    'amount': 0,
                    'count': 0
                }

            distribution[bin_key]['volume'] += volume
            distribution[bin_key]['amount'] += amount
            distribution[bin_key]['count'] += 1
            total_volume += volume
            total_amount += amount

        # 3. 计算占比
        cyq_data = []
        for price_level in sorted(distribution.keys()):
            item = distribution[price_level]
            cyq_data.append({
                'price_level': price_level,
                'volume': item['volume'],
                'amount': item['amount'],
                'count': item['count'],
                'volume_ratio': (item['volume'] / total_volume * 100) if total_volume > 0 else 0,
                'amount_ratio': (item['amount'] / total_amount * 100) if total_amount > 0 else 0,
                'avg_cost': item['amount'] / item['volume'] if item['volume'] > 0 else 0
            })

        return pd.DataFrame(cyq_data), {
            'total_volume': total_volume,
            'total_amount': total_amount,
            'price_range': (min_price, max_price),
            'support_level': self._find_support_level(cyq_data),
            'resistance_level': self._find_resistance_level(cyq_data)
        }

    def _find_support_level(self, cyq_data: pd.DataFrame) -> float:
        """找到支撑位（筹码密集区）"""
        if cyq_data.empty:
            return 0
        # 找到成交量最大的区间
        max_vol_idx = cyq_data['volume'].idxmax()
        return cyq_data.loc[max_vol_idx, 'price_level']

    def _find_resistance_level(self, cyq_data: pd.DataFrame) -> float:
        """找到阻力位（上方筹码密集区）"""
        # 找到上方筹码集中的区域
        if cyq_data.empty:
            return 0

        mid_index = len(cyq_data) // 2
        upper_half = cyq_data.iloc[:mid_index]
        if upper_half.empty:
            return 0

        max_vol_idx = upper_half['volume'].idxmax()
        return upper_half.loc[max_vol_idx, 'price_level']

    def get_profit_ratio(
        self,
        code: str,
        current_price: float,
        session: AsyncSession
    ) -> Dict[str, float]:
        """
        计算盈利比例

        参数:
            code: 股票代码
            current_price: 当前价格
            session: 数据库会话

        返回:
            盈利比例和亏损比例
        """
        # 获取最近的筹码分布
        # 计算有多少筹码盈利/亏损
        # 返回统计信息
        pass
```

#### 3. 龙虎榜数据

**功能描述**：每日龙虎榜数据获取、分析和历史统计

**商业价值**：
- 了解市场热点
- 跟踪游资动向
- 发现潜在龙头股
- 分析营业部席位动向

**数据来源**：
- 东方财富网龙虎榜（已有 API）
- 同花顺龙虎榜

**数据模型设计**：

```python
# src/models/dragon_tiger.py
from sqlalchemy import Column, BigInteger, String, Date, Decimal, Text, Boolean

class DragonTigerList(Base, TimestampMixin):
    """龙虎榜数据表"""
    __tablename__ = "dragon_tiger_lists"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = Column(Date, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str] = Column(Text)  # 上榜理由
    net_buy: Mapped[Decimal] = Column(Decimal(18, 4))  # 净买入(元)
    net_buy_ratio: Mapped[Decimal] = Column(Decimal(10, 4))  # 净买入率
    total_buy: Mapped[Decimal] = Column(Decimal(18, 4))  # 总买入(元)
    total_sell: Mapped[Decimal] = Column(Decimal(18, 4))  # 总卖出(元)
    institution_buy: Mapped[Decimal] = Column(Decimal(18, 4))  # 机构买入(元)
    institution_sell: Mapped[Decimal] = Column(Decimal(18, 4))  # 机构卖出(元)
    retail_buy: Mapped[Decimal] = Column(Decimal(18, 4))  # 散户买入(元)
    retail_sell: Mapped[Decimal] = Column(Decimal(18, 4))  # 散户卖出(元)
    institution_buy_ratio: Mapped[Decimal] = Column(Decimal(10, 4))  # 机构买入比例
   席位号: Mapped[str] = mapped_column(String(20))  # 营业部席位
    席位名: Mapped[str] = mapped_column(String(50))  # 营业部名称
   上榜次数: Mapped[int] = Column(Integer)  # 近期上榜次数

    # 复合索引
    __table_args__ = (
        Index("idx_dragon_date_code", "trade_date", "code"),
        Index("idx_dragon_date_net_buy", "trade_date", "net_buy", order_by="net_buy", op="DESC"),
        Index("idx_dragon_rank", "trade_date", "net_buy"),
    )
```

**API 端点设计**：

```python
# src/api/dragon_tiger.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/dragon-tiger", tags=["dragon-tiger"])

@router.get("/lists", response_model=DragonTigerResponse)
async def get_dragon_tiger_lists(
    trade_date: Optional[str] = Query(None, description="交易日期 YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    获取龙虎榜数据

    参数:
        trade_date: 交易日期，默认为最近一天
        limit: 返回条数
    """
    if not trade_date:
        # 查询最近日期的数据
        result = await db.execute(
            select(DragonTigerList.trade_date)
            .order_by(desc(DragonTigerList.trade_date))
            .limit(1)
        )
        trade_date = result.scalar()
        if not trade_date:
            return DragonTigerResponse(
                trade_date="",
                total_count=0,
                data=[]
            )

    # 查询指定日期的龙虎榜
    query = select(DragonTigerList, StockBasics.name).join(
        StockBasics, DragonTigerList.code == StockBasics.code
    ).where(DragonTigerList.trade_date == trade_date)

    query = query.order_by(desc(DragonTigerList.net_buy))

    if limit:
        query = query.limit(limit)

    result = await db.execute(query)
    rows = result.all()

    # 返回数据
    total_count = len(rows)
    data = [
        DragonTigerItem(
            code=item[0].code,
            name=item[1],
            reason=item[0].reason,
            net_buy=float(item[0].net_buy) if item[0].net_buy else None,
            net_buy_ratio=float(item[0].net_buy_ratio) if item[0].net_buy_ratio else None,
            total_buy=float(item[0].total_buy) if item[0].total_buy else None,
            institution_buy=float(item[0].institution_buy) if item[0].institution_buy else None,
            institution_buy_ratio=float(item[0].institution_buy_ratio) if item[0].institution_buy_ratio else None,
            trading_volume=int(item[0].retail_buy + item[0].retail_sell),
            ranking=row[2] + 1 if row[2] else None  # 排名
        )
        for row in rows
    ]

    return DragonTigerResponse(
        trade_date=trade_date,
        total_count=total_count,
        data=data
    )

@router.get("/stats/{trade_date_str}")
async def get_dragon_tiger_stats(
    trade_date_str: str,
    db: AsyncSession = Depends(get_db)
):
    """获取龙虎榜统计数据"""
    # 实现统计数据
    pass
```

---

### 🟡 中优先级（近期实施）

#### 4. 跌停分析

**功能描述**：分析跌停股票的原因，提供分类和历史统计

**分类维度**：
- 技术性跌停（高位、放量、破位）
- 消息面跌停（利空）
- 市场性跌停（系统性风险）
- 连续跌停

**数据模型设计**：

```python
# src/models/limit_down.py
class LimitDown(Base, TimestampMixin):
    """跌停分析表"""
    __tablename__ = "limit_downs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(50))
    trade_date: Mapped[date] = Column(Date)
    limit_time: Mapped[str] = Column(String(10))  # 跌停时间
    reason: Mapped[str] = Column(String(200))  # 跌停原因
    reason_type: Mapped[str] = Column(String(50))  # 原因类型
    open_price: Mapped[Optional[Decimal]] = Column(Decimal(12, 4))
    close_price: Mapped[Optional[Decimal]] = Column(Decimal(12, 4))
    fall_pct: Mapped[Optional[Decimal]] = Column(Decimal(10, 4))
    volume: Mapped[Optional[BigInteger]] = Column(BigInteger)
    amount: Mapped[Optional[Decimal]] = Column(Decimal(18, 4))
```

#### 5. 大单资金流向（细化）

**已有基础**：已有个股资金流向功能

**改进点**：
- 大单类型细分：超大单(>500万)、大单(100-500万)、中单(20-100万)、小单(<20万)
- 大单净流入排名
- 实时大单监控
- 大单成交明细

**数据模型扩展**：

```sql
-- 在现有资金流向表基础上，添加大单明细表
CREATE TABLE trade_details (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(10),
    trade_date DATE,
    trade_time TIME,
    direction VARCHAR(10),  -- buy/sell
    order_type VARCHAR(20),  -- large_order/super_large_order/medium_order/small_order
    price DECIMAL(12, 4),
    volume BIGINT,
    amount DECIMAL(18, 4),
    trade_id VARCHAR(50)
);
```

#### 6. ETF 数据

**功能描述**：ETF 行情、持仓、净值等数据

**价值**：
- ETF 选股
- 行业配置参考
- 套利策略

**数据来源**：东方财富网 ETF 数据

**数据模型设计**：

```python
class ETF(Base, TimestampMixin):
    """ETF数据表"""
    __tablename__ = "etf_info"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(100))
    fund_type: Mapped[str] = mapped_column(String(50))  # 基金类型
    tracking_index: Mapped[Optional[str]] = mapped_column(String(50))  # 跟踪指数
    fund_manager: Mapped[Optional[str]] = mapped_column(String(100))  # 基金经理
    establish_date: Mapped[Optional[date]] = mapped_column(Date)
    list_date: Mapped[Optional[date]] = mapped_column(Date)
    delisting_date: Mapped[Optional[date]] = mapped_column(Date)

    # 规模数据
    fund_size: Mapped[Optional[float]] = mapped_column(Float)
    units: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)

    # 实时数据
    nav: Mapped[Optional[float]] = mapped_column(Float)  # 单位净值
    discount_premium: Mapped[Optional[float]] = mapped_column(Float)  # 折溢价率
    yield_1y: Mapped[Optional[float]] = mapped_column(Float)  # 近一年收益率
    yield_3y: Mapped[Optional[float]] = mapped_column(Float)  # 近三年收益率
```

---

### 🟢 低优先级（可选）

#### 7. 自动化交易接口

**功能描述**：
- 自动 IPO 申购
- 策略自动执行
- 模拟盘/实盘切换

**注意事项**：
- 需要券商接口对接
- 风险控制要求高
- 建议仅做模拟盘

#### 8. 更多技术指标

**已有指标**：32个

**可添加指标**：
- Supertrend（超级趋势）
- VHF（垂直水平过滤）
- PPO（价格震荡率）
- DPO（去震荡）

---

## 🛠️ 具体实现方案

### 实施路线图

#### 第一阶段（1-2周）- 高优先级功能

**目标**：
1. 实现K线形态识别（10个基础形态）
2. 添加龙虎榜数据同步

**任务清单**：
- [ ] 创建数据库表结构
- [ ] 实现形态识别算法
- [ ] 添加数据同步服务
- [ ] 创建API端点
- [ ] 前端展示组件

#### 第二阶段（2-3周）- 中优先级功能

**目标**：
3. 实现筹码分布分析
4. 跌停分析功能

**任务清单**：
- [ ] 创建CYQ数据表
- [ ] 实现筹码计算逻辑
- [ ] 创建CYQ可视化组件
- [ ] 跌停数据获取
- [ ] 原因分类系统

#### 第三阶段（3-4周）- 低优先级功能

**目标**：
5. ETF 数据支持
6. 大单资金流向细化

---

## 📊 价值评估矩阵

| 功能 | 技术难度 | 开发时间 | 用户价值 | 商业价值 | ROI | 推荐度 |
|------|---------|---------|---------|---------|-----|--------|
| K线形态识别 | 中高 | 1-2周 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 高 | ⭐⭐⭐⭐⭐ |
| 筹码分布分析 | 中 | 1-2周 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 高 | ⭐⭐⭐⭐⭐ |
| 龙虎榜数据 | 低 | 1周 | ⭐⭐⭐ | ⭐⭐⭐⭐ | 高 | ⭐⭐⭐⭐ |
| 跌停分析 | 中 | 1-2周 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 中 | ⭐⭐⭐ |
| 大单资金流向细化 | 低 | 3-5天 | ⭐⭐⭐⭐ | ⭐⭐⭐ | 中 | ⭐⭐⭐ |
| ETF 数据 | 低 | 3-5天 | ⭐⭐⭐⭐ | ⭐⭐⭐ | 中 | ⭐⭐⭐ |
| 自动化交易接口 | 高 | 4-6周 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 高 | ⭐⭐ |
| 更多技术指标 | 低 | 1周 | ⭐⭐⭐ | ⭐⭐⭐ | 中 | ⭐⭐ |

---

## 💡 技术亮点借鉴

### 1. 性能优化

**InStock 的优化**：
- 使用 TA-Lib C 库提升计算性能
- 多线程并发数据获取
- 批量数据库操作
- 数据预计算和缓存

**SAPAS 可借鉴**：
```python
# 将关键计算改为C扩展
import talib

# 批量操作优化
from sqlalchemy.dialects.postgresql import insert
batch_insert(stmt).returning(*stmt)
```

### 2. 数据质量保证

**InStock 的做法**：
- 多数据源交叉验证
- 异常值检测
- 数据完整性校验
- 自动重试机制

### 3. 用户体验设计

**InStock 的亮点**：
- 热力图展示板块表现
- 一键选股功能
- 策略对比展示
- 移动端适配

---

## 📝 实施检查清单

### K线形态识别实施检查清单

- [ ] 需求分析完成
- [ ] 数据模型设计完成
- [ ] API 接口设计完成
- [ ] 前端组件设计完成
- [ ] 数据同步逻辑实现
- [ ] 单元测试完成
- [ ] 集成测试完成
- [ ] 文档更新完成

### 龙虎榜数据实施检查清单

- [ ] 需求分析完成
- [ ] 数据模型设计完成
- [ ] API 接口设计完成
- [ ] 数据同步逻辑实现
- [ ] 数据展示页面设计
- [ ] 测试完成

### 筹码分布分析实施检查清单

- [ ] 需求分析完成
- [ ] 算法逻辑验证
- [ ] 数据模型设计完成
- [ ] 可视化组件选择
- [ ] 测试完成

---

## 🔗 参考资料

- **InStock 仓库**: https://github.com/myhhub/stock
- **技术文档**: https://github.com/myhhub/stock/wiki
- **API 文档**: https://github.com/myhhubstock/wiki/API
- **功能演示**: https://github.com/myhhubstock#功能演示

---

## 📌 后记

本文档基于 2026-01-23 的分析结果。代码仓库可能持续更新，建议定期查看最新的功能实现。

**下一步行动**：
1. 选择1-2个高优先级功能开始实施
2. 确认技术方案和设计文档
3. 创建开发任务并分配
4. 按路线图推进实施

---

**文档版本**: v1.0
**创建日期**: 2026-01-23
**作者**: SAPAS 团队
**审核人**: [待定]

---

*本文档为 SAPAS 项目的功能规划提供参考，具体实施时需根据实际情况调整*