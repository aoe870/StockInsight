# SAPAS 项目结构设计

## 目录结构

```
StockInsight/
├── docs/                           # 项目文档
│   ├── 01_project_structure.md     # 项目结构说明
│   ├── 02_database_design.md       # 数据库设计文档
│   ├── 03_api_specification.md     # API 接口规范
│   └── 04_implementation_roadmap.md # 实现路线图
│
├── scripts/                        # 数据库脚本
│   ├── 01_create_tables.sql        # 创建表结构
│   ├── 02_create_indexes.sql       # 创建索引
│   ├── 03_create_functions.sql     # 创建存储过程/函数
│   └── 04_seed_data.sql            # 初始化数据
│
├── src/                            # 源代码目录
│   ├── __init__.py
│   ├── main.py                     # 应用入口
│   ├── config.py                   # 配置管理
│   │
│   ├── models/                     # 数据模型层
│   │   ├── __init__.py
│   │   ├── base.py                 # SQLAlchemy Base
│   │   ├── stock.py                # 股票相关模型
│   │   ├── alert.py                # 告警相关模型
│   │   └── subscription.py         # 订阅相关模型
│   │
│   ├── services/                   # 业务服务层
│   │   ├── __init__.py
│   │   ├── data_sync.py            # 数据同步服务
│   │   ├── analysis.py             # 技术分析服务
│   │   ├── monitor.py              # 实时监控服务
│   │   └── notification.py         # 通知服务
│   │
│   ├── api/                        # API 路由层
│   │   ├── __init__.py
│   │   ├── router.py               # 路由汇总
│   │   ├── stocks.py               # 股票相关 API
│   │   ├── watchlist.py            # 自选股 API
│   │   ├── analysis.py             # 分析 API
│   │   ├── alerts.py               # 告警 API
│   │   └── subscriptions.py        # 订阅 API
│   │
│   ├── schemas/                    # Pydantic 数据校验
│   │   ├── __init__.py
│   │   ├── stock.py
│   │   ├── alert.py
│   │   └── subscription.py
│   │
│   ├── core/                       # 核心模块
│   │   ├── __init__.py
│   │   ├── database.py             # 数据库连接
│   │   ├── indicators.py           # 技术指标计算
│   │   ├── visualization.py        # 可视化生成
│   │   └── publisher.py            # 发布订阅核心
│   │
│   └── utils/                      # 工具模块
│       ├── __init__.py
│       ├── logger.py               # 日志工具
│       ├── retry.py                # 重试机制
│       └── validators.py           # 数据校验
│
├── web/                            # 前端代码 (Vue.js)
│   ├── src/
│   │   ├── components/             # Vue 组件
│   │   ├── views/                  # 页面视图
│   │   ├── stores/                 # Pinia 状态管理
│   │   ├── api/                    # API 调用封装
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.js
│
├── tests/                          # 测试代码
│   ├── __init__.py
│   ├── test_services/
│   ├── test_api/
│   └── conftest.py
│
├── logs/                           # 日志目录
│   └── .gitkeep
│
├── requirements.txt                # Python 依赖
├── .env.example                    # 环境变量示例
├── .gitignore
└── pyproject.toml                  # 项目配置
```

## 技术栈选型

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| Web框架 | FastAPI | 高性能异步框架，自动生成API文档 |
| 前端框架 | Vue 3 + Vite | 现代化前端，快速开发 |
| 数据库 | PostgreSQL | 用户指定，支持复杂查询 |
| ORM | SQLAlchemy 2.0 | 异步支持，类型安全 |
| 数据获取 | AKShare | A股数据源 |
| 技术指标 | pandas-ta | 纯Python实现，无需编译 |
| 可视化 | Plotly | 交互式图表 |
| 任务调度 | APScheduler | 定时任务调度 |
| 缓存/消息 | Redis (可选) | 缓存与发布订阅 |

