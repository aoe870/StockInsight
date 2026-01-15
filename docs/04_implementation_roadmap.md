# SAPAS 实现路线图

## 总体规划

项目采用**增量式开发**，分为9个主要阶段，预计总工期约 4-6 周。每个阶段完成后可独立验证。

---

## 阶段 1: 基础设施搭建 (1-2天)

### 1.1 数据库初始化
```bash
# 执行数据库脚本
psql -U postgres -c "CREATE DATABASE sapas_db WITH ENCODING='UTF8';"
psql -U postgres -d sapas_db -f scripts/01_create_tables.sql
psql -U postgres -d sapas_db -f scripts/02_create_indexes.sql
psql -U postgres -d sapas_db -f scripts/03_create_functions.sql
psql -U postgres -d sapas_db -f scripts/04_seed_data.sql
```

### 1.2 Python 项目初始化
```bash
# 激活虚拟环境 (用户已创建)
# Windows: .\venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 1.3 配置管理
- 创建 `.env` 配置文件
- 实现 `src/config.py` 配置加载模块

**产出物**: 可连接数据库的基础项目框架

---

## 阶段 2: 数据模型层 (2-3天)

### 2.1 SQLAlchemy 模型定义
- `src/models/stock.py` - 股票基础信息、日K线模型
- `src/models/alert.py` - 告警规则、告警历史模型
- `src/models/subscription.py` - 用户、订阅模型

### 2.2 数据库会话管理
- `src/core/database.py` - 异步数据库连接池
- 实现上下文管理器模式

**产出物**: 完整的 ORM 模型，可进行 CRUD 操作

---

## 阶段 3: 数据同步服务 (4-5天)

### 3.1 AKShare 封装
- `src/services/data_sync.py`
- 实现股票列表获取
- 实现日K线数据获取
- 支持前复权/后复权/不复权

### 3.2 增量更新逻辑
- 查询各股票最新日期
- 仅拉取缺失数据
- 批量入库优化

### 3.3 异常处理
- 重试装饰器 (3次重试，指数退避)
- 请求限流 (每秒不超过5次)
- 接口超时处理

**产出物**: 可稳定运行的数据同步脚本

---

## 阶段 4: 技术分析引擎 (4-5天)

### 4.1 指标计算模块
- `src/core/indicators.py`
- MA 均线系统 (5, 10, 20, 60, 120, 250)
- MACD (12, 26, 9)
- RSI (14)
- KDJ (9, 3, 3)
- 布林带 (20, 2)

### 4.2 信号识别
- 均线金叉/死叉检测
- MACD 低位金叉
- RSI 超买超卖
- 布林带突破

**产出物**: 可对任意股票计算技术指标的分析引擎

---

## 阶段 5: REST API 服务 (5-6天)

### 5.1 FastAPI 框架搭建
- `src/main.py` - 应用入口
- `src/api/router.py` - 路由汇总
- 中间件配置 (CORS, 日志)

### 5.2 API 端点实现

| 模块 | 端点 | 功能 |
|------|------|------|
| 股票 | `GET /api/stocks` | 股票列表 |
| 股票 | `GET /api/stocks/{code}/kline` | K线数据 |
| 自选 | `GET /api/watchlist` | 获取自选股 |
| 自选 | `POST /api/watchlist` | 添加自选股 |
| 自选 | `DELETE /api/watchlist/{id}` | 删除自选股 |
| 分析 | `GET /api/analysis/{code}` | 技术指标 |
| 告警 | `GET /api/alerts/rules` | 告警规则列表 |
| 订阅 | `POST /api/subscriptions` | 创建订阅 |

**产出物**: 完整的后端 API 服务

---

## 阶段 6: 数据可视化 (2-3天)

### 6.1 K线图生成
- `src/core/visualization.py`
- Plotly Candlestick 主图
- MA 均线叠加
- 布林带通道

### 6.2 副图模块
- 成交量柱状图
- MACD 能量柱

### 6.3 交互特性
- 十字光标
- 区域缩放
- HTML 导出

**产出物**: 可生成交互式 K 线图的可视化模块

---

## 阶段 7: 告警订阅系统 (5-6天)

### 7.1 发布订阅核心
- `src/core/publisher.py`
- 观察者模式实现
- 告警事件定义

### 7.2 监控守护进程
- `src/services/monitor.py`
- APScheduler 定时任务
- 交易时段检测 (9:30-11:30, 13:00-15:00)

### 7.3 多渠道通知
- `src/services/notification.py`
- 控制台输出 + 日志文件
- Webhook 通知 (可扩展)
- 邮件通知 (可扩展)

**产出物**: 完整的实时监控与告警通知系统

---

## 阶段 8: Web 前端 (5-7天)

### 8.1 Vue 项目初始化
```bash
cd web
npm create vite@latest . -- --template vue
npm install
```

### 8.2 页面开发
- 自选股管理页面 (添加/删除/排序)
- K线图表页面 (指标选择/时间范围)
- 告警订阅页面 (规则管理/通知设置)

**产出物**: 完整的 Web 管理界面

---

## 阶段 9: 测试与部署 (3-5天)

### 9.1 测试
- 单元测试 (pytest)
- API 集成测试
- 数据同步测试

### 9.2 部署
- Docker 容器化 (可选)
- 部署文档编写

**产出物**: 可部署的完整系统

---

## 依赖关系图

```
阶段1 → 阶段2 → 阶段3 → 阶段4 → 阶段5 → 阶段6
                                    ↓
                               阶段7 ← 阶段8
                                    ↓
                               阶段9
```

## 关键里程碑

| 里程碑 | 预计时间 | 验收标准 |
|--------|----------|----------|
| M1 | 第1周末 | 数据同步正常运行 |
| M2 | 第2周末 | API 服务可用 |
| M3 | 第3周末 | 告警系统上线 |
| M4 | 第4周末 | 前端界面完成 |
| M5 | 第5周末 | 全系统测试通过 |

