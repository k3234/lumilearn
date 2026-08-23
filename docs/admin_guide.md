# LumiLearn 管理员指南

> 面向系统管理员：默认账号、Web 管理面板、CLI、REST API、Agent 架构与安全注意事项。
> 适用版本：2026-08-07 管理员系统（管理员管理 + Agent 框架）。

---

## 1. 默认账号与首次登录

首次启动服务时，若数据库中不存在任何管理员，系统会自动创建默认超级管理员：

| 项 | 值 |
|:---|:---|
| 用户名 | `admin` |
| 初始密码 | 环境变量 `LUMILEARN_ADMIN_INITIAL_PASSWORD`；未设置时随机生成并打印到日志 |
| 角色 | `super_admin`（超级管理员） |
| 显示名 | 超级管理员 |
| 强制改密 | ✅ 首次登录后强制要求修改密码（`must_change_password`） |

> ⚠️ **安全说明**：系统不再使用公开弱口令。
> - 新部署：初始密码随机生成或由 `LUMILEARN_ADMIN_INITIAL_PASSWORD` 指定，且**首次登录必须改密**，改密前无法执行任何管理操作。
> - 存量库：若旧版曾创建默认弱口令账号，登录成功后会自动标记强制改密，必须修改后才能继续使用。

修改密码的三种方式：

1. **Web 面板**：登录后调用右上角/用户菜单中的"修改密码"（填写原密码 + 新密码，新密码至少 6 位）。
2. **REST API**：

   ```bash
   curl -X POST http://localhost:18080/api/admin/password \
     -H "Content-Type: application/json" \
     -H "X-Admin-Token: <你的Token>" \
     -d '{"old_password": "原密码", "new_password": "你的新密码"}'
   ```

3. **CLI**（忘记密码时由另一管理员重置）：

   ```bash
   python scripts/db_admin.py admin reset-password --username admin --password 新密码
   ```

登录成功后返回 `token`，后续所有管理 API 调用需在请求头携带 `X-Admin-Token: <token>`。
会话有效期 **12 小时**，超时后需重新登录；令牌仅保存在服务内存中，重启服务后所有会话失效。

---

## 2. Web 管理面板

浏览器访问 **http://localhost:18080/admin**，登录后进入管理面板。面板为单页应用，左侧导航分为六个模块：

| 模块 | 说明 | 对应 API |
|:---|:---|:---|
| 📊 **系统概览** | 用户总数（教师/学生）、工作流数、输出检测数、模型健康状态、Agent 总数/运行数、最近 5 条系统日志 | `GET /api/admin/overview` |
| 👥 **用户管理** | 查看全部用户、按角色筛选、创建用户、删除用户 | `GET/POST /api/admin/users`、`DELETE /api/admin/users/<id>` |
| 🤖 **模型管理** | 查看 Ollama 模型列表与健康状态、拉取新模型、删除模型、设置默认模型 | `GET /api/admin/models`、`POST .../pull`、`.../delete`、`.../default` |
| 🧠 **Agent管理** | 查看 Agent 列表（含运行状态/是否内置）、注册自定义 Agent、启动/停止/手动执行/删除 Agent、查看健康状态 | `GET/POST /api/admin/agents`、`.../start`、`.../stop`、`.../run`、`.../health` |
| 📜 **系统日志** | 按级别筛选查看系统日志、清理过期日志 | `GET /api/admin/logs`、`POST /api/admin/logs/clear` |
| 🔑 **API密钥** | 查看/生成（`scope`：read/write）/删除 API 密钥，生成后仅显示一次 | `GET/POST /api/admin/api-keys`、`DELETE /api/admin/api-keys/<key>` |

---

## 3. CLI 命令

管理员相关命令统一挂在 `python scripts/db_admin.py admin` 子命令下：

```bash
# 列出所有管理员
python scripts/db_admin.py admin list

# 创建管理员（--role 可选 super_admin / operator，默认 super_admin）
python scripts/db_admin.py admin create --username zhangsan --password xxx --name 张三 --role operator

# 重置指定管理员密码
python scripts/db_admin.py admin reset-password --username zhangsan --password 新密码

# 停用指定管理员（is_active=0）
python scripts/db_admin.py admin disable --username zhangsan

# 列出全部 Agent（含运行状态）
python scripts/db_admin.py admin agents

# 启动 / 停止 Agent
python scripts/db_admin.py admin agent-start --agent-id feynman_teacher
python scripts/db_admin.py admin agent-stop --agent-id chat_assistant

# 查看系统日志（--level 可选 info/warning/error，--limit 默认 50）
python scripts/db_admin.py admin logs
python scripts/db_admin.py admin logs --level error --limit 100
```

---

## 4. REST API 端点清单

所有端点前缀为 `/api/admin`。**除 `POST /api/admin/login` 外，其余端点均需请求头 `X-Admin-Token`**（由 `require_admin` 装饰器强制校验，未登录返回 401）。

### 4.1 认证

| 方法 | 路径 | 鉴权 | 说明 | 请求体 |
|:---|:---|:---|:---|:---|
| POST | `/api/admin/login` | 无 | 登录，成功返回 `{success, token, admin}` | `{username, password}` |
| POST | `/api/admin/logout` | ✅ | 退出登录，销毁当前会话 | — |
| GET | `/api/admin/me` | ✅ | 获取当前登录管理员信息 | — |
| POST | `/api/admin/password` | ✅ | 修改当前管理员密码 | `{old_password, new_password}` |

### 4.2 系统概览

| 方法 | 路径 | 鉴权 | 说明 |
|:---|:---|:---|:---|
| GET | `/api/admin/overview` | ✅ | 系统总览：用户/教师/学生数、工作流数、检测数、Agent 数与运行数、模型健康、最近日志 |

### 4.3 用户管理

| 方法 | 路径 | 鉴权 | 说明 | 参数 |
|:---|:---|:---|:---|:---|
| GET | `/api/admin/users` | ✅ | 用户列表 | query: `role`（teacher/student） |
| POST | `/api/admin/users` | ✅ | 创建用户 | `{name, role}` |
| DELETE | `/api/admin/users/<user_id>` | ✅ | 删除用户 | — |

### 4.4 模型管理

| 方法 | 路径 | 鉴权 | 说明 | 参数 |
|:---|:---|:---|:---|:---|
| GET | `/api/admin/models` | ✅ | 模型列表 + Ollama 健康状态 | — |
| POST | `/api/admin/models/pull` | ✅ | 拉取新模型到 Ollama | `{model}` |
| POST | `/api/admin/models/delete` | ✅ | 从 Ollama 删除模型 | `{model}` |
| POST | `/api/admin/models/default` | ✅ | 设置全局默认模型（写入配置） | `{model}` |

### 4.5 Agent 管理

| 方法 | 路径 | 鉴权 | 说明 | 参数 |
|:---|:---|:---|:---|:---|
| GET | `/api/admin/agents` | ✅ | Agent 列表（含运行状态、是否内置） | query: `type` |
| POST | `/api/admin/agents` | ✅ | 注册新 Agent（含自定义 Agent） | `{agent_id, name, type, description, config}` |
| POST | `/api/admin/agents/<agent_id>/start` | ✅ | 启动 Agent | — |
| POST | `/api/admin/agents/<agent_id>/stop` | ✅ | 停止 Agent | — |
| POST | `/api/admin/agents/<agent_id>/run` | ✅ | 手动触发 Agent 执行（测试用，自动启动未运行实例） | 任意 payload |
| DELETE | `/api/admin/agents/<agent_id>` | ✅ | 删除 Agent（先停止再删除） | — |
| GET | `/api/admin/agents/health` | ✅ | 全部 Agent 健康检查 | — |

### 4.6 系统日志

| 方法 | 路径 | 鉴权 | 说明 | 参数 |
|:---|:---|:---|:---|:---|
| GET | `/api/admin/logs` | ✅ | 日志列表 | query: `level`、`limit`（默认 100） |
| POST | `/api/admin/logs/clear` | ✅ | 清理过期日志，返回清除条数 | `{older_than_days}`（默认 7） |

### 4.7 API 密钥

| 方法 | 路径 | 鉴权 | 说明 | 参数 |
|:---|:---|:---|:---|:---|
| GET | `/api/admin/api-keys` | ✅ | 密钥列表 | — |
| POST | `/api/admin/api-keys` | ✅ | 生成密钥（`secrets.token_hex(24)`，仅返回一次） | `{key_name, scope}`（scope 默认 read） |
| DELETE | `/api/admin/api-keys/<api_key>` | ✅ | 删除密钥 | — |

**curl 调用示例**：

```bash
# 登录获取 token（口令从环境变量 ADMIN_PASSWORD 传入，禁止硬编码）
TOKEN=$(curl -s -X POST http://localhost:18080/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"'"$ADMIN_PASSWORD"'"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 带鉴权调用
curl -H "X-Admin-Token: $TOKEN" http://localhost:18080/api/admin/overview
curl -H "X-Admin-Token: $TOKEN" http://localhost:18080/api/admin/agents
```

---

## 5. Agent 架构说明

### 5.1 基类 BaseAgent

`framework/admin/agents.py` 定义抽象基类 `BaseAgent`（`ABC`），统一 Agent 生命周期契约：

| 方法 | 说明 |
|:---|:---|
| `run(payload: Dict) -> Dict` | **抽象方法**，Agent 的核心执行入口，接收任意参数、返回结果字典 |
| `health() -> Dict` | 健康检查，默认返回 `{agent_id, status: "healthy", type}`，子类可覆写（如 ChatAgent 检查聊天服务） |
| `to_dict() -> Dict` | 返回 `{agent_id, name, type, description}` 元信息 |

`AgentRegistry` 负责注册、启停、执行与健康检查：
- **注册**：内置 Agent 在注册表初始化时幂等写入数据库（`_ensure_builtins`）；自定义 Agent 通过 API/注册表 `register()` 动态注册（当前执行器为占位实现，预留 `config.runner` 扩展点）。
- **启停**：`start()` / `stop()` 维护内存运行实例表 `_agent_runners`，并把状态（running/stopped）持久化到数据库；重复启动/停止幂等。
- **执行**：`run_agent()` 自动启动未运行实例后调用 `instance.run(payload)`，异常时把状态标记为 `error`。
- **健康检查**：`health()` 支持单 Agent 与全量两种模式；未运行的 Agent 状态为 `stopped`。

### 5.2 内置 Agent（4 个）

| agent_id | 类 | 类型 | 说明 | 底层实现 |
|:---|:---|:---|:---|:---|
| `feynman_teacher` | `FeynmanAgent` | feynman | 基于费曼五步学习法讲解知识点 | `FeynmanEngine.explain(topic, level)`，参数 `topic`（必填）、`level` |
| `output_detector` | `DetectionAgent` | detector | 检测学生学习输出质量并给出改进建议 | `OutputDetector.run_detection(concept, student_output)`，返回总分/是否掌握/反馈 |
| `adaptive_path` | `AdaptiveAgent` | adaptive | 根据学生学习进度推荐学习路径 | `AdaptiveLearningEngine.recommend_next(user_id, count=5)`（经 `get_adaptive_engine()` 获取），参数 `user_id`（必填） |
| `chat_assistant` | `ChatAgent` | chat | 通用多轮对话助手 | `chat_sync([...])`（经 `get_chat_service()` 获取，非流式同步对话），参数 `message`（必填）；覆写 `health()` 检查聊天服务状态 |

> 4 个内置 Agent 在 `BUILTIN_AGENTS` 工厂列表中声明，注册表启动时自动注册，不可删除（`is_builtin=true`）。

### 5.3 手动执行示例

```bash
# 通过 REST API 手动触发
curl -X POST http://localhost:18080/api/admin/agents/feynman_teacher/run \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $TOKEN" \
  -d '{"topic": "牛顿第二定律", "level": "junior"}'

curl -X POST http://localhost:18080/api/admin/agents/adaptive_path/run \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $TOKEN" \
  -d '{"user_id": 1}'
```

---

## 6. 安全注意事项

1. **密码策略**
   - 系统不再内置公开口令：默认管理员初始密码由环境变量 `LUMILEARN_ADMIN_INITIAL_PASSWORD` 指定或随机生成，**首次登录必须强制改密**（Web 面板 / API / CLI 均可）；新密码至少 6 位。
   - 密码使用 `werkzeug.security.generate_password_hash` 加盐哈希存储，数据库不保存明文。
   - 停用离职管理员：`python scripts/db_admin.py admin disable --username <name>`，停用后无法登录。

2. **API 鉴权机制（require_admin）**
   - 除登录外，全部管理端点由 Flask 装饰器 `require_admin` 强制校验请求头 `X-Admin-Token`。
   - 未带 Token 或会话无效/过期均返回 **401**。
   - 会话 TTL 12 小时；令牌仅存内存，服务重启后全部失效，需重新登录。

3. **API 密钥轮换**
   - 密钥由 `secrets.token_hex(24)` 生成（48 位十六进制），生成后只在响应中显示一次，丢失需重建。
   - 定期轮换：新建密钥 → 切换业务使用 → 删除旧密钥。
   - 密钥按 `scope`（read/write）区分权限，最小权限原则分配。

4. **网络暴露面**
   - 管理 API 与面板承载敏感操作，**建议仅限内网/本机访问**：默认监听 `localhost:18080`，如需对外请务必置于防火墙/反向代理之后，并对 `/api/admin/*` 做来源限制。
   - 不要在公网明文传输登录凭据，生产环境应启用 HTTPS。

5. **操作留痕**
   - 创建/删除用户、拉取/删除模型、注册/启停 Agent、生成密钥等敏感操作均自动写入系统日志（`system_logs` 表），可通过 Web 面板"系统日志"或 `admin logs` 审计。
