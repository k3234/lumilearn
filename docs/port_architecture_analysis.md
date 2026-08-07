# 端口架构分析与部署建议

> **日期**: 2026-08-07  
> **问题**: 学校环境中多端口部署的可行性

---

## 1. 当前架构分析

### 1.1 支持的部署模式

```
┌─────────────────────────────────────────────────────────────────────┐
│                       LumiLearn 部署模式                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  模式一：单端口（推荐）                                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Port 18080                                                 │   │
│  │  ├─ / (首页 - lumiterm.html)                                │   │
│  │  ├─ /learn (课堂 - classroom.html)                          │   │
│  │  ├─ /chat (聊天 - lumiterm.html)                            │   │
│  │  ├─ /api/chat  (对话 API)                                   │   │
│  │  ├─ /api/feynman/* (费曼教学 API)                           │   │
│  │  ├─ /api/animation/* (动画 API)                             │   │
│  │  ├─ /api/models/* (模型管理 API)                            │   │
│  │  └─ ... (其他所有 API)                                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  模式二：三端口（开发/调试用）                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │  18080      │  │  18081      │  │  18082      │                 │
│  │  Terminal   │  │    API      │  │   Models    │                 │
│  │  (HTML)     │  │  (纯API)    │  │  (纯API)    │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 前端 API 调用情况

所有前端页面均使用**相对路径**调用 API：

```javascript
// lumiterm.html, classroom.html, animation_learn.html
fetch('/api/chat', ...)           // ✓ 相对路径
fetch('/api/feynman/explain', ...) // ✓ 相对路径
fetch('/api/animation/generate', ...) // ✓ 相对路径
fetch('/api/models', ...)         // ✓ 相对路径
```

**结论**: 前端代码天然支持单端口部署，无需修改。

---

## 2. 学校部署场景分析

### 2.1 网络环境限制

| 限制类型 | 单端口模式 | 三端口模式 | 影响 |
|----------|-----------|-----------|------|
| 防火墙规则 | ✅ 只需开放1个端口 | ❌ 需开放3个端口 | 高 |
| 路由器配置 | ✅ 简单映射 | ❌ 复杂映射 | 中 |
| ISP 限制 | ✅ 无影响 | ⚠️ 可能拦截 | 低 |
| 安全审计 | ✅ 单一入口 | ❌ 多点暴露 | 高 |
| 学生访问 | ✅ 统一入口 | ⚠️ 需记多个地址 | 低 |

### 2.2 典型学校网络架构

```
互联网
    │
    ▼
┌─────────────────────┐
│   学校防火墙/网关    │  ← 只开放少数端口（如 80, 443）
└─────────┬───────────┘
          │
    ┌─────┴─────┐
    │           │
┌───▼───┐   ┌───▼───┐
│ 内网   │   │ 办公网 │
│ 10.0.0.0│  │ 172.16.0.0│
└───┬───┘   └───┬───┘
    │           │
    ▼           ▼
┌─────────────────────┐
│   LumiLearn 服务器   │
│   内网 IP: 10.0.1.100│
└─────────────────────┘
```

**现实情况**:
- 学校防火墙通常只允许开放 80 (HTTP) 和 443 (HTTPS)
- 或使用反向代理（如 nginx）统一入口
- 开放多个端口需要特殊审批流程

### 2.3 多端口部署的实际问题

```
❌ 问题 1: 防火墙配置复杂
   - 需要为每个端口单独配置规则
   - 学校 IT 部门可能拒绝

❌ 问题 2: 学生访问困难
   - 学生需要记住多个地址
   - 不同功能在不同端口，体验割裂

❌ 问题 3: 运维成本高
   - 3 个服务进程需要分别监控
   - 3 个端口需要分别检查状态

❌ 问题 4: 安全隐患
   - 暴露更多攻击面
   - 需要管理更多端口防火墙规则

✅ 解决方案: 单端口部署
   - 只开放 1 个端口（推荐 80 或 443）
   - 所有功能统一入口
   - 运维简单，安全可控
```

---

## 3. 推荐部署方案

### 3.1 生产环境：单端口模式（推荐）

```bash
# 启动命令（单端口）
python -m framework.api.server --port 80

# 或指定内网端口
python -m framework.api.server --port 18080 --host 10.0.1.100
```

**访问方式**:
- 学生访问: `http://10.0.1.100/` 或 `http://lumilearn.school.edu.cn/`
- 教师访问: `http://10.0.1.100/learn`
- API 调用: `http://10.0.1.100/api/...` (自动跟随)

**优势**:
1. ✅ 防火墙只需开放 1 个端口
2. ✅ 学生只需记住一个地址
3. ✅ 运维简单，单进程管理
4. ✅ 安全性高，单一入口易审计

### 3.2 反向代理方案（Nginx）

```nginx
# /etc/nginx/sites-available/lumilearn
server {
    listen 80;
    server_name lumilearn.school.edu.cn;

    # 前端静态文件
    location / {
        proxy_pass http://127.0.0.1:18080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API 请求（代理到同一服务）
    location /api/ {
        proxy_pass http://127.0.0.1:18080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket 支持（如需实时功能）
    location /ws {
        proxy_pass http://127.0.0.1:18080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**部署命令**:
```bash
# 启动 LumiLearn（内网端口）
python -m framework.api.server --port 18080 --host 127.0.0.1

# 配置 Nginx（外部 80 端口）
sudo nginx -t && sudo systemctl reload nginx
```

**优势**:
1. ✅ 外部只暴露 80/443 端口
2. ✅ 支持 HTTPS（Let's Encrypt）
3. ✅ 负载均衡（多实例）
4. ✅ 缓存静态文件

### 3.3 Docker 容器化部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

# 单端口模式
EXPOSE 18080

CMD ["python", "-m", "framework.api.server", "--port", "18080", "--host", "0.0.0.0"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  lumilearn:
    build: .
    ports:
      - "80:18080"  # 映射到 80 端口
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"  # 模型服务
    volumes:
      - ollama_model:/root/.ollama

volumes:
  ollama_model:
```

**启动命令**:
```bash
docker-compose up -d
```

---

## 4. 配置建议

### 4.1 生产环境 config/framework.yaml

```yaml
# 生产环境配置
version: "1.0.0"
debug: false

server:
  terminal_port: 18080  # 内网端口（反代转发到此）
  host: "127.0.0.1"    # 只监听本地，由反代暴露

ollama:
  base_url: "http://localhost:11434"
  default_model: "qwen2.5:7b"
  timeout: 300

security:
  api_key_required: true
  allowed_origins:
    - "https://lumilearn.school.edu.cn"
```

### 4.2 开发环境配置

```bash
# 开发时可启用三端口模式（仅本地）
python -m framework.api.server --multi-port

# 访问不同服务：
# - http://localhost:18080  (终端界面)
# - http://localhost:18081  (API 测试)
# - http://localhost:18082  (模型管理)
```

---

## 5. 总结与建议

### 5.1 核心结论

| 问题 | 答案 |
|------|------|
| 多端口会影响项目初衷吗？ | ❌ 不会，单端口模式完全支持 |
| 学校能部署吗？ | ✅ 可以，单端口 + 反代方案成熟 |
| 需要改代码吗？ | ❌ 不需要，前端已支持相对路径 |
| 推荐端口？ | 80 (HTTP) 或 443 (HTTPS) |

### 5.2 部署检查清单

```
□ 服务器配置
  □ 安装 Python 3.10+
  □ 安装 Ollama 及模型
  □ 配置防火墙（只开放 80/443）

□ 应用部署
  □ 克隆代码仓库
  □ 安装依赖: pip install -r requirements.txt
  □ 初始化数据库
  □ 配置 config/framework.yaml

□ 生产部署
  □ 使用单端口模式启动
  □ 配置 Nginx 反代（可选但推荐）
  □ 配置 HTTPS（Let's Encrypt）
  □ 配置日志轮转

□ 测试验证
  □ 访问 http://school.edu.cn/
  □ 测试 API: /api/status
  □ 测试费曼教学: /api/feynman/explain
  □ 测试多用户并发
```

### 5.3 最终建议

**学校部署请使用单端口模式**：

```bash
# 生产环境启动命令
python -m framework.api.server --port 80 --host 0.0.0.0
```

或配合 Nginx 反代：

```bash
# 内部端口
python -m framework.api.server --port 18080 --host 127.0.0.1

# 外部通过 Nginx 暴露 80/443
```

**三端口模式仅用于本地开发和调试，不建议在学校生产环境使用。**

---

**文档生成**: 2026-08-07  
**维护**: LumiLearn 开发团队
