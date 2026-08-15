# LumiLearn Docker 部署

## 快速开始

```bash
# 构建并启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f

# 停止所有服务
docker compose down
```

## 服务架构

```
┌─────────────────────────────────────────────────────┐
│                    Nginx (port 80)                  │
│           反向代理 + SSL 终止                        │
└──────────────────┬──────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┬──────────────┐
    ▼              ▼              ▼              ▼
┌───────┐    ┌─────────┐   ┌─────────┐   ┌──────────┐
│ API   │    │GOAI Web │   │ Teacher │   │   Admin   │
│ 5010  │    │  5000   │   │  5001   │   │  18080   │
└───┬───┘    └────┬────┘   └────┬────┘   └────┬─────┘
    │             │             │             │
    └─────────────┴──────┬──────┴─────────────┘
                          ▼
                   ┌─────────────┐
                   │  SQLite DB  │
                   │   ./data/   │
                   └──────┬──────┘
                          ▼
                   ┌─────────────┐
                   │   Ollama    │
                   │  :11434     │
                   └─────────────┘
```

## 环境变量配置

复制并编辑 `.env` 文件：

```bash
cp .env.example .env
```

关键环境变量：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `OLLAMA_HOST` | Ollama 服务地址 | `http://ollama:11434` |
| `FLASK_ENV` | 运行环境 | `production` |
| `SECRET_KEY` | Flask 密钥 | 自动生成 |
| `DATABASE_URL` | 数据库连接 | `sqlite:///./data/lumilearn.db` |

## 持久化数据

| 路径 | 说明 |
|---|---|
| `./data/` | SQLite 数据库、用户数据 |
| `./ollama_data/` | Ollama 模型数据 |
| `./logs/` | 应用日志 |

## 自定义配置

### 修改端口

编辑 `docker-compose.yml` 中的端口映射：

```yaml
services:
  api:
    ports:
      - "8080:5010"  # 修改为 8080
```

### 添加更多模型

在 `docker-compose.yml` 的 Ollama 服务中添加模型拉取：

```yaml
services:
  ollama:
    volumes:
      - ./ollama_data:/root/.ollama
    command: >
      start
      && ollama pull qwen2.5:7b
      && ollama pull lumilearn-v2:latest
```

### 使用外部数据库

```yaml
services:
  api:
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/lumilearn
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: lumilearn
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 健康检查

```bash
# 检查所有服务
docker compose ps

# 检查 API 健康
curl http://localhost:5010/health

# 检查 Ollama
curl http://localhost:11434/api/tags
```

## 故障排除

### 端口冲突

如果端口被占用，编辑 `docker-compose.yml` 修改映射端口：

```yaml
services:
  api:
    ports:
      - "5020:5010"  # 原 5010 被占用，改为 5020
```

### 模型拉取失败

```bash
# 手动拉取模型
docker exec -it lumilearn-ollama-1 ollama pull qwen2.5:7b
```

### 数据库初始化

```bash
# 重置数据库
docker compose down
rm -rf data/
docker compose up -d
```

## 生产部署建议

1. 使用 HTTPS（Nginx 配置 SSL）
2. 定期备份数据库
3. 配置日志轮转
4. 启用监控告警
5. 使用 secrets 管理敏感信息

```bash
# 备份数据库
docker exec lumilearn-api-1 cp /app/data/lumilearn.db /backup/
```
