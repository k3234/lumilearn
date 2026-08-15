#syntax=docker/dockerfile:1

FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY goai_requirements.txt .
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r goai_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建数据目录
RUN mkdir -p /data /logs

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV OLLAMA_HOST=http://ollama:11434

# 暴露端口（主 API 服务）
EXPOSE 5010

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5010/health || exit 1

# 启动命令
CMD ["python", "framework/api/server.py", "--port", "5010"]
