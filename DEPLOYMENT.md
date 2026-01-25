

# SAPAS 部署检查清单

## 开发环境部署检查清单

### 1. 环境准备

- [ ] **Python 3.11+** 已安装
  ```bash
  python --version
  ```

- [ ] **Node.js 18+** 已安装
  ```bash
  node --version
  npm --version
  ```

- [ ] **Docker** 已安装并运行
  ```bash
  docker --version
  docker-compose --version
  ```

### 2. 配置文件

- [ ] **.env 文件** 已配置
  ```bash
  cp .env.example .env
  # 编辑 .env 文件，确认数据库连接信息正确
  ```

- [ ] **数据库配置** 已检查
  - DATABASE_URL 正确配置
  - DATABASE_SYNC_URL 正确配置
  - REDIS_URL 正确配置

### 3. 依赖安装

- [ ] **Python 依赖** 已安装
  ```bash
  python -m venv .venv
  source .venv/bin/activate  # Linux/Mac
  # 或 .venv\Scripts\activate  # Windows
  pip install -r requirements.txt
  ```

- [ ] **前端依赖** 已安装
  ```bash
  cd web
  npm install
  cd ..
  ```

### 4. 数据库初始化

- [ ] **PostgreSQL 容器** 已启动
  ```bash
  docker-compose up -d postgres redis
  docker-compose ps
  ```

- [ ] **数据库表** 已创建
  ```bash
  # 检查表是否创建
  docker-compose exec postgres psql -U root -d sapas_db -c "\dt"
  ```

- [ ] **数据库函数** 已创建
  ```bash
  # 检查函数
  docker-compose exec postgres psql -U root -d sapas_db -c "\df"
  ```

- [ ] **初始数据** 已导入
  ```bash
  # 检查用户
  docker-compose exec postgres psql -U root -d sapas_db -c "SELECT * FROM users;"
  ```

### 5. 服务启动

- [ ] **后端服务** 已启动
  ```bash
  python -m uvicorn src.main:app --host 0.0.0.0 --port 8081 --reload
  # 验证: curl http://localhost:8081/health
  ```

- [ ] **前端服务** 已启动
  ```bash
  cd web
  npm run dev
  # 验证: 浏览器访问 http://localhost:5173
  ```

### 6. 功能验证

- [ ] **API 文档** 可访问
  - 访问: http://localhost:8081/docs
  - 检查是否有 API 端点列表

- [ ] **数据库连接** 正常
  ```bash
  # 运行健康检查
  bash start.sh health
  # 或 Windows:
  python scripts\health_check.py
  ```

- [ ] **Redis 连接** 正常（WebSocket 功能需要）

- [ ] **登录功能** 正常
  - 用户名: admin
  - 密码: admin123

- [ ] **K线图** 显示正常
  - MA 均线可见
  - 成交量显示正常
  - 技术指标正常

- [ ] **数据同步** 功能正常
  - 检查是否有股票数据
  - 尝试同步单只股票数据

## 生产环境部署检查清单

### 1. 服务器准备

- [ ] **操作系统** Ubuntu 20.04+ / CentOS 8+ / Windows Server
- [ ] **Python 3.11+** 已安装
- [ ] **Node.js 18+** 已安装
- [ ] **Docker & Docker Compose** 已安装
- [ ] **Nginx** 已安装（用于反向代理）

### 2. 数据库配置

- [ ] **PostgreSQL** 生产实例已配置
  - 设置强密码
  - 配置持久化存储
  - 配置远程访问（如需要）

- [ ] **Redis** 生产实例已配置
  - 设置密码
  - 配置持久化存储
  - 配置最大内存策略

### 3. 环境变量

- [ ] **.env 文件** 已配置生产环境值
  ```bash
  APP_ENV=production
  DEBUG=false
  SECRET_KEY=[强密钥]
  DATABASE_URL=[生产数据库连接]
  REDIS_URL=[生产 Redis 连接]
  CORS_ORIGINS=["https://your-domain.com"]
  ```

### 4. 依赖安装

- [ ] **Python 依赖** 已安装
  ```bash
  pip install -r requirements.txt
  ```

- [ ] **前端构建** 已完成
  ```bash
  cd web
  npm run build
  ```

### 5. 服务部署

- [ ] **数据库服务** 使用 Docker Compose 部署
  ```bash
  docker-compose -f docker-compose.prod.yml up -d
  ```

- [ ] **后端服务** 使用进程管理器部署
  - 推荐使用 systemd / supervisord / gunicorn
  - 示例配置见下方

- [ ] **前端** 使用 Nginx 托管静态文件
  - 配置反向代理到后端 API
  - 配置 WebSocket 支持

### 6. 反向代理配置

- [ ] **Nginx** 已配置
  - 静态文件托管
  - API 反向代理
  - WebSocket 代理

### 7. 安全配置

- [ ] **防火墙** 已配置
  - 开放必要端口（80, 443, 22）
  - 关闭不必要端口

- [ ] **HTTPS** 已配置
  - SSL 证书已安装
  - HTTP 重定向到 HTTPS

- [ ] **密钥管理**
  - 生产环境密钥已更新
  - 密钥不在版本控制中

### 8. 监控配置

- [ ] **日志监控** 已配置
  - 应用日志路径
  - 日志轮转策略

- [ ] **进程监控** 已配置
  - 使用 systemd / supervisord 自动重启

- [ ] **健康检查** 已配置
  - 定期运行健康检查脚本
  - 配置告警通知

### 9. 备份策略

- [ ] **数据库备份** 已配置
  - 定期备份脚本
  - 异地备份存储

- [ ] **应用备份** 已配置
  - 代码备份
  - 配置文件备份

## 常见问题排查

### 问题 1: 后端启动失败

**症状**: 运行 `python -m uvicorn src.main:app` 报错

**排查步骤**:
1. 检查虚拟环境是否激活
2. 检查依赖是否安装完整: `pip list`
3. 检查 .env 配置是否正确
4. 检查数据库服务是否运行

### 问题 2: 数据库连接失败

**症状**: "connection refused" 或 "authentication failed"

**排查步骤**:
1. 检查 Docker 容器是否运行: `docker-compose ps`
2. 检查数据库连接字符串
3. 检查数据库用户权限
4. 测试数据库连接:
   ```bash
   docker-compose exec postgres psql -U root -d sapas_db
   ```

### 问题 3: 前端无法访问后端 API

**症状**: CORS 错误或网络错误

**排查步骤**:
1. 检查后端服务是否运行
2. 检查 .env 中 CORS_ORIGINS 配置
3. 检查浏览器控制台网络请求
4. 确认 API 地址正确

### 问题 4: MA 均线不显示

**症状**: K线图上看不到均线

**排查步骤**:
1. 打开浏览器控制台查看错误
2. 检查网络请求返回的数据格式
3. 确认 close/open/high/low 是数字不是字符串
4. 检查后端日志

### 问题 5: Docker 容器无法启动

**症状**: docker-compose up 失败

**排查步骤**:
1. 检查 Docker 服务是否运行
2. 检查端口是否被占用
3. 查看容器日志: `docker-compose logs postgres`
4. 清理并重新创建: `docker-compose down -v`

## 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                         用户                              │
└────────────────┬────────────────────────────────────────┘
                 │
        ┌────────┴─────────┐
        │                    │
    ┌───▼────┐          ┌────▼──────┐
    │ Nginx  │          │  后端 API  │
    └───┬────┘          └────┬───┬────┘
        │                     │   │
    ┌───▼────┐            │   │
    │ 前端   │            │   │
    │ 静态  │            │   │
    └────────┘            │   │
                          │   │
              ┌───────────┘   │
              │               │
       ┌────▼────┐      ┌────▼───────┐
       │PostgreSQL│      │   Redis    │
       └─────────┘      └────────────┘
```

## 支持与帮助

### 获取帮助

1. 查看日志文件
   - 后端日志: `logs/sapas.log`
   - 告警日志: `logs/alert_history.log`

2. 运行健康检查
   ```bash
   bash start.sh health       # Linux/Mac
   python scripts\health_check.py  # Windows
   ```

3. 查看文档
   - README.md: 项目概述和快速开始
   - API 文档: http://localhost:8081/docs

### 联系方式

- 问题反馈: [GitHub Issues]
- 技术支持: [Email]

## 更新日志

- 2026-01-22: 添加集合竞价功能、资金流向分析
- 2026-01-20: 添加回测系统、选股器
- 2026-01-15: 初始版本发布
