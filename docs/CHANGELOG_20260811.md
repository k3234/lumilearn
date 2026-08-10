# LumiLearn 更新记录（2026-08-11）

> 本文档整理 2026-08-11 前后所有新增与修改内容，供维护与发布参考。
> 说明：不包含测试脚本、本地验收过程与任何敏感凭据；服务器地址一律使用占位符。

---

## 一、问题修复

### 1. 教师端首页 404（template not found）⭐

**问题**：远程教师端（5001）首页返回 `teacher.html not found`，教师资源模块不可用。

**根因**：`teacher_portal.py` 中 `TEMPLATE_DIR` 硬编码指向 `BASE_DIR / "remote" / "templates"`，该目录在远程部署结构（`tianhong/templates/`）中不存在。

**修复**（`teacher_portal.py`）：改为兼容两种部署目录——本地优先 `remote/templates`，不存在时回退 `tianhong/templates`。

### 2. 框架三端口首页均为终端页面 ⭐

**问题**：18080 / 18081 / 18082 三个端口访问首页都返回终端（lumiterm.html），与设计意图（18081 纯 API、18082 模型管理）不符。

**根因**：三个端口共用 `create_app()` 创建的同一 Flask 应用，且首页路由固定渲染终端模板。

**修复**（`framework/api/server.py`）：

- `create_app()` 新增 `homepage` 参数（`terminal` / `api` / `models`），首页路由按类型返回不同内容：
  - `terminal`：渲染 lumiterm.html（终端）
  - `api`：返回 REST API 端点概览 JSON
  - `models`：重定向到 `/admin`（模型管理面板）
- 新增 `_template_path()` 统一解析模板路径，兼容本地 `remote/templates` 与远程 `tianhong/templates`（应用到所有页面路由）。
- `_start_multi_port` 为三个端口分别创建不同 `homepage` 的应用实例。

**修复后效果**：

| 端口 | 首页 |
|---|---|
| 18080 | 终端（lumiterm.html） |
| 18081 | REST API JSON 概览（含全部 `/api/*` 端点列表） |
| 18082 | 模型管理（302 → `/admin`） |

### 3. 教学资源为空

**问题**：教师端「教学资源」显示"暂无教学内容"。

**根因**：远程 `training_data` 表为空（0 条记录）。

**修复**：从本地教学语料（`data/training_corpus.jsonl`，1152 条）生成教学内容导入远程数据库，全部标记 `status=published`（数学/物理/化学/生物各 288 条），教师端资源、知识点、任务生成功能即可用。

## 二、部署方式修正（重要）

**发现**：远程 `server` 由 **systemd user 服务**（`~/.config/systemd/user/lumilearn-api.service`，`Restart=always`）托管，手动 `pkill` 后会被自动拉起，导致旧代码长时间无法替换、端口冲突。

**正确操作**：使用 `systemctl --user restart lumilearn-api` 重启，`systemctl --user stop/start` 控制启停。GOAI Web 由 `lumilearn-goai.service` 托管。教师端目前为手动 `nohup` 启动，如需开机自启可仿照添加 systemd 单元。

**附加发现**：教师端（5001）页面无 `/api/status` 路由属正常设计；其 `/` 需返回 teacher.html（见修复 1）。

## 三、一键安装增强（deploy/）

**修改文件**：`deploy/setup.py`、`config/providers.yaml`

- 新增**其他本地模型容器**引导段：支持 vLLM / LM Studio / LocalAI / llama.cpp server 等 OpenAI 兼容容器。
  - 交互式填写容器地址（自动补 `/v1`），调用 `/models` 自动发现容器内**全部模型**。
  - 自动注册到 `config/providers.yaml`，可在 Admin「端口模型配置」中选用。
- **Ollama 仍为默认推荐容器**（`/api/tags` 自动发现全部模型），一键安装流程不变。
- `providers.yaml` 补充本地容器配置示例注释。

## 四、Agent 能力强化

**修改文件**：`framework/admin/agents.py`、`goai_agent.py`

| 改动 | 说明 |
|---|---|
| 费曼教学 Agent | 传入 `dialogue` 对话历史时自动切换为**交互式单步引导**（`explain_step`），上下文连贯逐步推进；并优先使用配置的 `feynman_model`（默认 qwen2.5:7b） |
| GOAI 教育智能体 | `ToolCaller` 默认模型改为从 `.env` 的 `OLLAMA_MODEL` 读取（其次环境变量，最后内置兜底），并支持加载 `.env` 配置 |

## 五、文档整理（README 重构）

**修改文件**：`README.md`

- 新增「🤖 Agent 智能体」章节（快速导航之后优先展示）：列出 5 个 Agent（费曼教学/输出检测/自适应学习/对话助手/GOAI 教育智能体）及其能力、统一生命周期、推理记录三方查看。
- 新增「🧠 模型与模型容器」章节：Ollama（推荐）/ 其他本地 OpenAI 兼容容器 / 云端 API 三类来源与模型发现机制、主要模型资产表、端口模型配置说明。
- 「接入模型」表补充"其他本地容器"接入方式。

## 六、本地模型容器全链路兼容（本次补充）

**背景**：`deploy/setup.py` 可注册 vLLM / LM Studio / LocalAI / llama.cpp 等 OpenAI 兼容容器到 `config/providers.yaml`，
但原模型发现与调用链路要求提供者必须有 API Key，导致**无 Key 的本地容器注册后不显示、不可用**。

**修改文件**：`framework/services/provider_service.py`、`framework/api/routes/chat.py`、`goai_agent.py`、`deploy/setup.py`、`deploy/README.md`

| 改动 | 说明 |
|---|---|
| `providers.yaml` 新增 `local: true` 标记 | 本地容器专属字段（`deploy/setup.py` 注册时自动写入），表示"无需 API Key 即可使用" |
| `provider_service.get_all_available_models` | 放行 `local` 容器：`enabled` 且（有 Key 或 local）即出现在模型列表，标签显示「本地容器」 |
| `provider_service.list_providers/get_provider` | 返回 `local` 字段，Admin 面板可区分本地容器/云端 |
| `provider_service.get_ollama_models` | Ollama 地址改为优先读取 `OLLAMA_BASE_URL` 环境变量（不再硬编码 localhost:11434） |
| `chat.py _resolve_cloud_model` | 本地容器（local=true）无需 API Key 也可被解析路由 |
| `chat.py _cloud_chat_stream/_cloud_chat_sync` | API Key 为空时发送占位 `Bearer not-needed`，兼容不校验 Key 的本地容器 |
| `goai_agent.py ToolCaller` | 同上：GOAI 教育智能体也能使用 goai_web 端口配置的本地容器模型 |
| `deploy/README.md` | 新增「5.3 其他本地模型容器」章节（vLLM/LM Studio/LocalAI/llama.cpp 默认地址与接入说明） |

**验证结果**：本地容器（无 Key）模型出现在 `get_all_available_models`、可被 `_resolve_cloud_model` 解析并走 OpenAI 兼容接口；Ollama 仍为默认推荐容器。

---

**未提交事项**：本日修复与增强已同步本地代码；远程已部署教师端与框架三端口修复。详见 git 提交记录。
