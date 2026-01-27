# SAPAS Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 先复制所有代码（包括 api, core 等目录）
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir uv && \
    uv pip install --system -e .

# 暴露端口
EXPOSE 8082

# 启动应用 - 使用 Python 模块方式
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8082"]
