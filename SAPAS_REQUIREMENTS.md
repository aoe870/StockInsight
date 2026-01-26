# SAPAS 股票分析平台 - 需求文档

> 文档版本: 1.0
> 创建日期: 2026-01-26
> 项目名称: SAPAS (Stock Analysis Platform & Algo-trading System)

---

## 目录

- [项目概述](#项目概述)
- [技术架构](#技术架构)
- [功能模块](#功能模块)
- [前端需求](#前端需求)
- [后端API需求](#后端api需求)
- [数据库设计](#数据库设计)
- [实时数据推送](#实时数据推送)
- [技术指标需求](#技术指标需求)
- [功能实现状态](#功能实现状态)
- [开发建议](#开发建议)

---

## 项目概述

### 系统定位

SAPAS 是一个专业的股票分析与自动化交易系统平台，集成了行情数据、技术分析、策略回测、预警监控等功能模块。

### 核心特性

- **多市场支持**: A股、港股、美股
- **多数据源集成**: AKShare (实时) + BaoStock (历史) + Miana (商业数据)
- **实时行情推送**: WebSocket 实时推送
- **专业图表**: K线图、分时图、技术指标图表
- **策略回测**: 支持多种策略回测和结果分析
- **智能预警**: 支持价格、技术指标、事件等多种预警
- **自选股管理**: 自定义自选股分组和监控

### 目标用户

- 个人投资者
- 量化交易研究员
- 证券从业人员
- 金融分析师

---

## 技术架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         客户端层                               │
│                    (Vue 3 + TypeScript)                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │行情中心 │ │指标选股 │ │自选股   │ │预警中心 │ │策略回测 │  │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘  │
└───────┼─────────┼─────────┼─────────┼─────────┼──────────────┘
        │         │         │         │         │
        └─────────┴─────────┴─────────┴─────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                     │
        ▼                                     ▼
┌──────────────────┐              ┌──────────────────┐
│   HTTP API       │              │   WebSocket       │
│  (Restful API)   │              │  实时行情推送      │
└────────┬─────────┘              └────────┬─────────┘
         │                                 │
         └───────────┬─────────────────────┘
                     │
        ┌────────────▼────────────┐
        │  数据网关服务 (FastAPI)  │
        │  - 多数据源自动切换      │
        │  - 缓存与限流           │
        │  - 数据标准化          │
        └────────────┬────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ AKShare  │  │ BaoStock │  │  Miana   │
│ (实时)   │  │ (历史)   │  │ (商业)   │
└──────────┘  └──────────┘  └──────────┘
                     │
                     ▼
        ┌──────────────────────┐
        │   PostgreSQL 数据库  │
        └──────────────────────┘
```

### 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3.4+ | 渐进式框架 |
| 前端 | TypeScript | 类型安全 |
| 前端 | Vite | 构建工具 |
| 前端 | Vue Router | 路由管理 |
| 前端 | Pinia | 状态管理 |
| 前端 | Element Plus | UI组件库 |
| 前端 | ECharts | 图表库 |
| 后端 | FastAPI | Web框架 |
| 后端 | Python 3.10+ | 开发语言 |
| 后端 | SQLAlchemy | ORM |
| 后端 | asyncio | 异步处理 |
| 数据库 | PostgreSQL 15+ | 关系型数据库 |
| 缓存 | Redis | 数据缓存 |
| 实时通信 | WebSocket | 实时推送 |

---

## 功能模块

### 1. 行情中心 (MarketView)

#### 1.1 实时行情展示
- 支持多市场切换（A股、港股、美股）
- 实时价格、涨跌幅、成交量展示
- 五档盘口展示（买一~买五、卖一~卖五）
- 市场深度图表
- 热门股票列表（涨跌幅榜、成交额榜）

#### 1.2 市场概览
- 大盘指数实时展示
- 板块涨跌排行
- 涨停/跌停股票列表
- 涨跌幅分布统计

#### 1.3 股票搜索
- 按代码/名称搜索
- 搜索历史记录
- 搜索结果快速预览

### 2. 股票详情 (StockDetailView)

#### 2.1 基础信息展示
- 股票基本信息（代码、名称、所属行业）
- 实时行情数据（价格、涨跌幅、成交量等）
- 估值指标（市盈率、市净率、总市值等）
- 股本数据（总股本、流通股本）

#### 2.2 K线图表
- 多周期K线（1分、5分、15分、30分、60分、日、周、月）
- 技术指标叠加（MA、MACD、KDJ、RSI、BOLL等）
- 缩放与平移
- 十字光标与数据提示
- 复权选项（前复权、后复权、不复权）

#### 2.3 分时图表
- 分时价格走势
- 均价线
- 分时成交量
- 集合竞价数据

#### 2.4 资金流向
- 当日资金流向（超大单、大单、中单、小单）
- 资金流向趋势图
- 净流入/净流出统计

#### 2.5 相关信息
- 同行业股票对比
- 持股基金列表
- 重大新闻资讯

### 3. 指标选股 (ScreenerView)

#### 3.1 选股条件配置
- 基本面指标（PE、PB、ROE、市值等）
- 技术面指标（MA、MACD、KDJ、RSI等）
- 资金面指标（净流入、大单占比等）
- 自定义公式选股

#### 3.2 选股结果展示
- 符合条件的股票列表
- 按各项指标排序
- 数据导出功能
- 保存选股条件

#### 3.3 历史回测选股
- 历史日期选股回测
- 收益率统计
- 胜率分析

### 4. 自选股 (WatchlistView)

#### 4.1 自选股分组
- 多分组管理
- 分组拖拽排序
- 自定义分组名称

#### 4.2 自选股列表
- 实时行情更新
- 一键移除
- 拖拽排序
- 批量操作

#### 4.3 分组视图
- 切换不同分组
- 快速添加到分组
- 跨分组移动

### 5. 预警中心 (AlertsView)

#### 5.1 预警类型
- 价格预警（突破指定价格）
- 涨跌幅预警（达到指定涨跌幅）
- 技术指标预警（金叉/死叉、超买/超卖等）
- 资金流向预警（净流入/流出突破）
- 自定义公式预警

#### 5.2 预警规则管理
- 添加/编辑/删除预警规则
- 预警条件组合（AND/OR）
- 预警频率设置（单次、每日）

#### 5.3 预警历史
- 预警触发记录
- 预警统计
- 预警消息推送（站内信、邮件、短信）

### 6. 策略回测 (BacktestView)

#### 6.1 策略配置
- 内置策略库（双均线、MACD、KDJ等）
- 自定义策略编写
- 策略参数调整

#### 6.2 回测设置
- 回测周期选择
- 初始资金设置
- 交易手续费设置
- 滑点设置

#### 6.3 回测结果展示
- 收益曲线
- 回撤曲线
- 交易明细
- 统计指标（收益率、胜率、最大回撤、夏普比率等）

#### 6.4 结果分析
- 月度/年度收益分析
- 交易次数统计
- 盈亏分布
- 策略优化建议

### 7. 集合竞价 (CallAuctionView)

#### 7.1 竞价数据展示
- 集合竞价时间轴
- 竞价价格区间
- 委托量变化
- 竞价结束价格预测

#### 7.2 竞价分析
- 竞价强度分析
- 竞价情绪指标
- 竞价与开盘价关系

### 8. 用户认证 (LoginView)

#### 8.1 用户登录
- 用户名/密码登录
- 验证码验证
- 记住登录状态
- 自动登录

#### 8.2 权限管理
- 角色权限控制
- 功能模块访问控制

---

## 前端需求

### 页面路由结构

```typescript
const routes = [
  { path: '/login', name: 'Login', component: LoginView },
  { path: '/', redirect: '/market' },
  { path: '/market', name: 'Market', component: MarketView },
  { path: '/screener', name: 'Screener', component: ScreenerView },
  { path: '/watchlist', name: 'Watchlist', component: WatchlistView },
  { path: '/alerts', name: 'Alerts', component: AlertsView },
  { path: '/backtest', name: 'Backtest', component: BacktestView },
  { path: '/call-auction', name: 'CallAuction', component: CallAuctionView },
  { path: '/stock/:code', name: 'StockDetail', component: StockDetailView }
]
```

### 组件结构

```
web/src/
├── api/                    # API 接口
│   ├── index.ts           # 通用API
│   ├── backtest.ts        # 回测API
│   └── callAuction.ts     # 集合竞价API
├── components/            # 公共组件
│   ├── KLineChart.vue    # K线图表组件
│   ├── BacktestConfig.vue # 回测配置组件
│   ├── BacktestKLine.vue # 回测K线组件
│   └── BacktestResult.vue # 回测结果组件
├── layouts/              # 布局组件
├── router/               # 路由配置
├── stores/               # 状态管理
│   └── auth.ts          # 认证状态
├── styles/               # 样式文件
├── views/                # 页面组件
│   ├── LoginView.vue
│   ├── MarketView.vue
│   ├── ScreenerView.vue
│   ├── WatchlistView.vue
│   ├── AlertsView.vue
│   ├── BacktestView.vue
│   ├── CallAuctionView.vue
│   └── StockDetailView.vue
├── App.vue
└── main.ts
```

### 状态管理需求

#### auth store
- 用户信息
- 登录状态
- 权限信息

#### market store
- 当前市场选择
- 实时行情数据缓存
- WebSocket 连接状态

#### watchlist store
- 自选股分组
- 自选股列表

---

## 后端API需求

### 1. 认证相关 API

```
POST   /api/v1/auth/login          # 用户登录
POST   /api/v1/auth/logout         # 用户登出
GET    /api/v1/auth/profile        # 获取用户信息
POST   /api/v1/auth/refresh        # 刷新Token
```

### 2. 股票数据 API

```
POST   /api/v1/quote              # 获取实时行情
GET    /api/v1/kline              # 获取K线数据
GET    /api/v1/stock/:code/info   # 获取股票基本信息
GET    /api/v1/stock/:code/fundamentals  # 获取基本面数据
```

### 3. 选股相关 API

```
POST   /api/v1/screener/query     # 执行选股查询
GET    /api/v1/screener/conditions # 获取选股条件列表
POST   /api/v1/screener/condition  # 保存选股条件
DELETE /api/v1/screener/condition/:id  # 删除选股条件
```

### 4. 自选股 API

```
GET    /api/v1/watchlist/groups   # 获取分组列表
POST   /api/v1/watchlist/group    # 创建分组
PUT    /api/v1/watchlist/group/:id # 更新分组
DELETE /api/v1/watchlist/group/:id # 删除分组
GET    /api/v1/watchlist          # 获取自选股列表
POST   /api/v1/watchlist          # 添加自选股
DELETE /api/v1/watchlist/:id      # 删除自选股
PUT    /api/v1/watchlist/:id      # 更新自选股
```

### 5. 预警相关 API

```
GET    /api/v1/alerts             # 获取预警列表
POST   /api/v1/alerts             # 创建预警规则
PUT    /api/v1/alerts/:id         # 更新预警规则
DELETE /api/v1/alerts/:id         # 删除预警规则
GET    /api/v1/alerts/history     # 获取预警历史
POST   /api/v1/alerts/:id/enable   # 启用预警
POST   /api/v1/alerts/:id/disable  # 禁用预警
```

### 6. 回测相关 API

```
POST   /api/v1/backtest/run       # 执行回测
GET    /api/v1/backtest/:id       # 获取回测结果
GET    /api/v1/backtest/strategies # 获取策略列表
GET    /api/v1/backtest/parameters # 获取策略参数模板
```

### 7. 集合竞价 API

```
GET    /api/v1/call-auction/:code # 获取集合竞价数据
GET    /api/v1/call-auction/:code/history  # 获取历史竞价数据
```

### 8. 资金流向 API

```
GET    /api/v1/money-flow/:code   # 获取资金流向数据
GET    /api/v1/money-flow/ranking # 获取资金流向排名
```

### 9. 板块数据 API

```
GET    /api/v1/sectors/industry   # 获取行业板块
GET    /api/v1/sectors/concept    # 获取概念板块
GET    /api/v1/sectors/:name/stocks # 获取板块成分股
```

---

## 数据库设计

### 核心数据表

#### users - 用户表
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### watchlist_groups - 自选股分组表
```sql
CREATE TABLE watchlist_groups (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(50) NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### watchlist_items - 自选股项目表
```sql
CREATE TABLE watchlist_items (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES watchlist_groups(id),
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(50),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### alerts - 预警规则表
```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    stock_code VARCHAR(20),
    alert_type VARCHAR(20) NOT NULL,  -- price, pct_change, indicator, money_flow, custom
    condition_config JSONB NOT NULL,  -- 预警条件配置
    frequency VARCHAR(20) DEFAULT 'once',  -- once, daily
    status VARCHAR(20) DEFAULT 'active',  -- active, disabled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### alert_history - 预警历史表
```sql
CREATE TABLE alert_history (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER REFERENCES alerts(id),
    stock_code VARCHAR(20),
    trigger_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trigger_value JSONB,
    message TEXT,
    status VARCHAR(20) DEFAULT 'unread'
);
```

#### backtest_runs - 回测运行表
```sql
CREATE TABLE backtest_runs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    strategy_name VARCHAR(50) NOT NULL,
    strategy_config JSONB NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(15,2) DEFAULT 100000,
    commission_rate DECIMAL(5,4) DEFAULT 0.0003,
    slippage DECIMAL(5,4) DEFAULT 0.001,
    status VARCHAR(20) DEFAULT 'running',  -- running, completed, failed
    result_summary JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

#### backtest_trades - 回测交易记录表
```sql
CREATE TABLE backtest_trades (
    id SERIAL PRIMARY KEY,
    backtest_id INTEGER REFERENCES backtest_runs(id),
    stock_code VARCHAR(20) NOT NULL,
    trade_type VARCHAR(10) NOT NULL,  -- buy, sell
    trade_time TIMESTAMP NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    quantity INTEGER NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    commission DECIMAL(10,2) DEFAULT 0,
    profit DECIMAL(15,2)
);
```

#### screener_conditions - 选股条件表
```sql
CREATE TABLE screener_conditions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    condition_config JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 实时数据推送

### WebSocket 连接

#### 连接地址
```
ws://localhost:8001/ws/quote
```

#### 订阅消息格式
```json
{
  "action": "subscribe",
  "symbols": ["000001", "600000", "600519"],
  "market": "cn_a"
}
```

#### 推送消息格式
```json
{
  "type": "quote",
  "symbol": "600519",
  "name": "贵州茅台",
  "price": 1678.00,
  "open": 1675.00,
  "high": 1680.00,
  "low": 1670.00,
  "volume": 123456,
  "amount": 207654321.00,
  "change": 3.00,
  "change_pct": 0.18,
  "pre_close": 1675.00,
  "high_limit": 1842.50,
  "low_limit": 1507.50,
  "turnover": 0.35,
  "pe_ttm": 30.5,
  "pe_dyn": 31.2,
  "pe_static": 32.0,
  "pb": 9.8,
  "amplitude": 0.60,
  "committee": 45.5,
  "market_value": 2100000000000,
  "circulation_value": 2100000000000,
  "buys": [
    [1677.00, 100],
    [1676.00, 200],
    [1675.00, 300],
    [1674.00, 400],
    [1673.00, 500]
  ],
  "sells": [
    [1678.00, 100],
    [1679.00, 200],
    [1680.00, 300],
    [1681.00, 400],
    [1682.00, 500]
  ],
  "timestamp": "2026-01-26 10:30:00",
  "market": "cn_a"
}
```

#### 心跳消息
```json
{
  "action": "ping"
}
```

#### 客户端实现示例
```typescript
class QuoteWebSocket {
  private ws: WebSocket | null = null;
  private heartbeatInterval: number | null = null;
  private subscribers: Map<string, Set<Function>> = new Map();

  connect(url: string) {
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.stopHeartbeat();
      // 重连逻辑
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  subscribe(symbols: string[], market: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: 'subscribe',
        symbols,
        market
      }));
    }
  }

  onQuote(callback: Function) {
    if (!this.subscribers.has('quote')) {
      this.subscribers.set('quote', new Set());
    }
    this.subscribers.get('quote')?.add(callback);
  }

  private handleMessage(data: any) {
    if (data.type === 'quote') {
      this.subscribers.get('quote')?.forEach(cb => cb(data));
    }
  }

  private startHeartbeat() {
    this.heartbeatInterval = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ action: 'ping' }));
      }
    }, 30000);
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
}
```

---

## 技术指标需求

### 趋势指标

| 指标 | 全称 | 参数 | 说明 |
|------|------|------|------|
| MA | 移动平均线 | N日周期 | 5日、10日、20日、60日等 |
| EMA | 指数移动平均 | N日周期 | 近期权重更高 |
| MACD | 指数平滑异同移动平均线 | 12, 26, 9 | 快线、慢线、柱状图 |
| BOLL | 布林带 | 20, 2 | 上轨、中轨、下轨 |

### 动量指标

| 指标 | 全称 | 参数 | 说明 |
|------|------|------|------|
| KDJ | 随机指标 | 9, 3, 3 | K线、D线、J线 |
| RSI | 相对强弱指标 | 14日 | 0-100范围 |
| CCI | 顺势指标 | 14日 | 超买超卖 |
| WR | 威廉指标 | 14日 | 超买超卖 |

### 成交量指标

| 指标 | 全称 | 参数 | 说明 |
|------|------|------|------|
| VOL | 成交量 | N日周期 | 成交量柱状图 |
| OBV | 能量潮 | - | 累计成交量 |
| VR | 成交量变异率 | 24日 | 成交量强弱 |

### 资金流向指标

| 指标 | 全称 | 参数 | 说明 |
|------|------|------|------|
| MF | 资金流向 | - | 净流入/净流出 |
| MF-L | 大单资金流向 | - | 大单净流入/净流出 |

### 指标计算需求

```typescript
// MA 计算示例
function calculateMA(data: number[], period: number): number[] {
  const result: number[] = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null);
    } else {
      const sum = data.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
      result.push(sum / period);
    }
  }
  return result;
}

// MACD 计算示例
interface MACDData {
  dif: number | null;
  dea: number | null;
  macd: number | null;
}

function calculateMACD(
  data: number[],
  fastPeriod: number = 12,
  slowPeriod: number = 26,
  signalPeriod: number = 9
): MACDData[] {
  const emaFast = calculateEMA(data, fastPeriod);
  const emaSlow = calculateEMA(data, slowPeriod);

  const dif = emaFast.map((v, i) => {
    if (v === null || emaSlow[i] === null) return null;
    return v - emaSlow[i]!;
  });

  const dea = calculateEMA(dif.filter(v => v !== null) as number[], signalPeriod);

  const macd = dif.map((v, i) => {
    if (v === null) return null;
    const deaIndex = i - fastPeriod + 1;
    if (deaIndex < 0) return null;
    return (v - dea[deaIndex]) * 2;
  });

  return { dif, dea, macd };
}

function calculateEMA(data: number[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  const multiplier = 2 / (period + 1);

  for (let i = 0; i < data.length; i++) {
    if (i === 0) {
      result.push(data[i]);
    } else if (result[i - 1] !== null) {
      result.push((data[i] - result[i - 1]!) * multiplier + result[i - 1]!);
    } else {
      result.push(null);
    }
  }

  return result;
}
```

---

## 功能实现状态

### 前端模块实现状态

| 模块 | 文件 | 状态 | 完成度 | 说明 |
|------|------|------|--------|------|
| 行情中心 | MarketView.vue | ✅ 已实现 | 80% | 基本行情展示，需增强功能 |
| 指标选股 | ScreenerView.vue | ✅ 已实现 | 70% | 基础选股功能，需添加更多条件 |
| 自选股 | WatchlistView.vue | ✅ 已实现 | 90% | 功能完整，需优化UI |
| 预警中心 | AlertsView.vue | ✅ 已实现 | 60% | 基础预警，需扩展预警类型 |
| 策略回测 | BacktestView.vue | 🟡 部分实现 | 50% | 基础框架，需完善回测逻辑 |
| 集合竞价 | CallAuctionView.vue | ✅ 已实现 | 85% | 功能较完整 |
| 股票详情 | StockDetailView.vue | ✅ 已实现 | 85% | K线图表完整，需添加更多数据 |
| 登录 | LoginView.vue | ✅ 已实现 | 100% | 功能完整 |

### 组件实现状态

| 组件 | 文件 | 状态 | 完成度 | 说明 |
|------|------|------|--------|------|
| K线图表 | KLineChart.vue | ✅ 已实现 | 90% | 基于ECharts，支持多周期 |
| 回测配置 | BacktestConfig.vue | ✅ 已实现 | 70% | 基础配置，需扩展 |
| 回测K线 | BacktestKLine.vue | ✅ 已实现 | 85% | 支持回测数据展示 |
| 回测结果 | BacktestResult.vue | ✅ 已实现 | 75% | 基础结果展示 |

### API实现状态

| API分组 | 端点 | 状态 | 说明 |
|---------|------|------|------|
| 认证API | /api/v1/auth/* | ❌ 缺失 | 需要实现用户认证 |
| 股票数据API | /api/v1/quote, /api/v1/kline | ✅ 已实现 | 由数据网关提供 |
| 选股API | /api/v1/screener/* | 🟡 部分实现 | 需要完善条件保存 |
| 自选股API | /api/v1/watchlist/* | ❌ 缺失 | 需要实现 |
| 预警API | /api/v1/alerts/* | ❌ 缺失 | 需要实现 |
| 回测API | /api/v1/backtest/* | 🟡 部分实现 | 需要完善 |
| 资金流向API | /api/v1/money-flow/* | ✅ 已实现 | 由数据网关提供 |
| 板块数据API | /api/v1/sectors/* | ✅ 已实现 | 由数据网关提供 |

### 数据库表实现状态

| 表名 | 状态 | 说明 |
|------|------|------|
| users | ❌ 缺失 | 需要创建 |
| watchlist_groups | ❌ 缺失 | 需要创建 |
| watchlist_items | ❌ 缺失 | 需要创建 |
| alerts | ❌ 缺失 | 需要创建 |
| alert_history | ❌ 缺失 | 需要创建 |
| backtest_runs | ❌ 缺失 | 需要创建 |
| backtest_trades | ❌ 缺失 | 需要创建 |
| screener_conditions | ❌ 缺失 | 需要创建 |

---

## 开发建议

### 短期任务（1-2周）

1. **用户认证系统**
   - 实现用户登录/登出功能
   - 添加JWT Token认证
   - 完善权限控制

2. **自选股后端API**
   - 创建自选股分组和项目表
   - 实现自选股CRUD API
   - 添加自选股导入/导出功能

3. **预警系统基础**
   - 创建预警规则表
   - 实现价格预警功能
   - 添加预警触发检测逻辑

### 中期任务（1个月）

1. **选股功能完善**
   - 添加更多选股条件
   - 实现选股条件保存
   - 添加历史回测选股

2. **回测系统完善**
   - 完善回测引擎
   - 添加更多内置策略
   - 优化回测结果展示

3. **实时推送优化**
   - 优化WebSocket连接稳定性
   - 添加断线重连机制
   - 优化推送频率控制

### 长期任务（2-3个月）

1. **预警系统扩展**
   - 实现技术指标预警
   - 添加自定义公式预警
   - 实现预警消息推送（邮件、短信）

2. **策略系统完善**
   - 实现策略编写编辑器
   - 添加策略分享功能
   - 实现策略绩效对比

3. **性能优化**
   - 前端性能优化
   - API响应速度优化
   - 数据库查询优化

4. **数据分析增强**
   - 添加更多技术指标
   - 实现自定义指标编写
   - 添加数据分析工具

---

## 附录

### 数据网关API文档参考

详细的API文档请参考：
- 数据网关文档: `data_gateway/docs/README.md`
- API Swagger文档: `http://localhost:8001/docs`

### Miana数据平台API文档

Miana平台相关文档：
- Miana API文档: `miana_api_doc.md`
- 官网: https://miana.com.cn

### 技术参考

- Vue 3文档: https://cn.vuejs.org/
- FastAPI文档: https://fastapi.tiangolo.com/zh/
- PostgreSQL文档: https://www.postgresql.org/docs/
- ECharts文档: https://echarts.apache.org/zh/
