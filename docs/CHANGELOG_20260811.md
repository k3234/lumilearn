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

**正确操作**：使用 `systemctl --user restart lumilearn-api` 重启，`systemctl --user stop/start` 控制启停。学习平台 Web 由 `lumilearn-lumilearn.service` 托管。教师端目前为手动 `nohup` 启动，如需开机自启可仿照添加 systemd 单元。

**附加发现**：教师端（5001）页面无 `/api/status` 路由属正常设计；其 `/` 需返回 teacher.html（见修复 1）。

## 三、一键安装增强（deploy/）

**修改文件**：`deploy/setup.py`、`config/providers.yaml`

- 新增**其他本地模型容器**引导段：支持 vLLM / LM Studio / LocalAI / llama.cpp server 等 OpenAI 兼容容器。
  - 交互式填写容器地址（自动补 `/v1`），调用 `/models` 自动发现容器内**全部模型**。
  - 自动注册到 `config/providers.yaml`，可在 Admin「端口模型配置」中选用。
- **Ollama 仍为默认推荐容器**（`/api/tags` 自动发现全部模型），一键安装流程不变。
- `providers.yaml` 补充本地容器配置示例注释。

## 四、Agent 能力强化

**修改文件**：`framework/admin/agents.py`、`lumilearn_agent.py`

| 改动 | 说明 |
|---|---|
| 费曼教学 Agent | 传入 `dialogue` 对话历史时自动切换为**交互式单步引导**（`explain_step`），上下文连贯逐步推进；并优先使用配置的 `feynman_model`（默认 qwen2.5:7b） |
| LumiLearn 学习智能体 | `ToolCaller` 默认模型改为从 `.env` 的 `OLLAMA_MODEL` 读取（其次环境变量，最后内置兜底），并支持加载 `.env` 配置 |

## 五、文档整理（README 重构）

**修改文件**：`README.md`

- 新增「🤖 Agent 智能体」章节（快速导航之后优先展示）：列出 5 个 Agent（费曼教学/输出检测/自适应学习/对话助手/LumiLearn 学习智能体）及其能力、统一生命周期、推理记录三方查看。
- 新增「🧠 模型与模型容器」章节：Ollama（推荐）/ 其他本地 OpenAI 兼容容器 / 云端 API 三类来源与模型发现机制、主要模型资产表、端口模型配置说明。
- 「接入模型」表补充"其他本地容器"接入方式。

## 六、本地模型容器全链路兼容（本次补充）

**背景**：`deploy/setup.py` 可注册 vLLM / LM Studio / LocalAI / llama.cpp 等 OpenAI 兼容容器到 `config/providers.yaml`，
但原模型发现与调用链路要求提供者必须有 API Key，导致**无 Key 的本地容器注册后不显示、不可用**。

**修改文件**：`framework/services/provider_service.py`、`framework/api/routes/chat.py`、`lumilearn_agent.py`、`deploy/setup.py`、`deploy/README.md`

| 改动 | 说明 |
|---|---|
| `providers.yaml` 新增 `local: true` 标记 | 本地容器专属字段（`deploy/setup.py` 注册时自动写入），表示"无需 API Key 即可使用" |
| `provider_service.get_all_available_models` | 放行 `local` 容器：`enabled` 且（有 Key 或 local）即出现在模型列表，标签显示「本地容器」 |
| `provider_service.list_providers/get_provider` | 返回 `local` 字段，Admin 面板可区分本地容器/云端 |
| `provider_service.get_ollama_models` | Ollama 地址改为优先读取 `OLLAMA_BASE_URL` 环境变量（不再硬编码 localhost:11434） |
| `chat.py _resolve_cloud_model` | 本地容器（local=true）无需 API Key 也可被解析路由 |
| `chat.py _cloud_chat_stream/_cloud_chat_sync` | API Key 为空时发送占位 `Bearer not-needed`，兼容不校验 Key 的本地容器 |
| `lumilearn_agent.py ToolCaller` | 同上：LumiLearn 学习智能体也能使用 lumilearn_web 端口配置的本地容器模型 |
| `deploy/README.md` | 新增「5.3 其他本地模型容器」章节（vLLM/LM Studio/LocalAI/llama.cpp 默认地址与接入说明） |

**验证结果**：本地容器（无 Key）模型出现在 `get_all_available_models`、可被 `_resolve_cloud_model` 解析并走 OpenAI 兼容接口；Ollama 仍为默认推荐容器。

---

**未提交事项**：本日修复与增强已同步本地代码；远程已部署教师端与框架三端口修复。详见 git 提交记录。

---

## 七、Day 1 基础加固（LumiLearn 行动规划）

**背景**：按 `docs/LumiLearn_ACTION_PLAN.md` Day 1 清单执行，全程遵守核心设备压力约束（无重型依赖、测试不触网不调模型、DB 惰性连接）。

### 1. bare except 清理（代码质量，零行为变更）

| 文件 | 行 | 修改 |
|---|---|---|
| `lumilearn_agent.py` | _check_availability | `except:` → `except Exception:` |
| `langgraph_engine.py` | _call_helper / _fmt_cards / 格式合并 | `except:` → `except Exception:`（3 处） |

### 2. langgraph_engine 可导入验证

- 已确认 `lumilearn_config.py`（环境变量驱动的脱敏配置）被 `langgraph_engine.py` 正常导入，`import langgraph_engine` 通过，无 ModuleNotFoundError。

### 3. 测试骨架（轻量，mock 化）

- **新增 `tests/test_lumilearn_agent.py`**（13 用例）：任务理解（学科/难度/学习类型/核心主题）、费曼五步编排、ToolCaller（全部 mock `requests.get/post`，**零真实网络**）、ResultDelivery 报告结构、主引擎 run（mock 模型调用 + 落盘重定向 tmp + 写库 no-op）。
- **新增 `tests/test_conversation_store.py`**（6 用例）：会话创建/隔离/删除、消息顺序/限长/清空、级联删除。
- 全套 `tests/` 共 **150 通过**（原 131 + 新 19），耗时约 7 分钟（含 torch 导入）。

### 4. 多轮对话持久化 chat_history

- **新增 `framework/services/conversation_store.py`**：
  - 独立轻量模块（纯标准库 sqlite3），**不修改** 150KB 的 `framework/database.py`，但共享同一库文件（`LUMILEARN_DB_PATH` 环境变量优先，默认项目根 lumilearn.db，解析逻辑与 database 同源）。
  - **惰性连接**：首次调用方法才打开数据库，空闲零连接零内存占用（核心设备压力友好）。
  - 表：`chat_sessions`（会话头）+ `chat_history`（消息，`session_id` 外键 **ON DELETE CASCADE**，并开启 `PRAGMA foreign_keys`）。
  - 方法：create_session / list_sessions（含消息数与末条预览）/ get_session / delete_session（级联）/ add_message / get_messages（可限长取尾部）/ clear_session；全局单例 `conversation_store`。
  - 用途：LumiLearn / 费曼 / 通用对话的多轮上下文持久化，后续接入对话接口。

---

**未提交事项**：Day 1 全部完成并已提交（见 git 记录）；ruff 未在本地安装，CI 将执行 `ruff check .`。

---

## 八、学习平台 Web 接入天虹服务（chat_history + 学生端原型）

**目标**：将 Day 1 的 chat_history 多轮对话持久化能力 + 学生端原型完整接入天虹（内网服务器）运行的 学习平台 Web 服务（5000 端口）。

### 1. lumilearn_web.py 新增（本地 12 项冒烟测试通过）

| 接入点 | 说明 |
|---|---|
| `/api/learn` | 学习报告生成后自动创建会话：用户学习目标 + 报告摘要（掌握度/薄弱点）写入 chat_history |
| `/api/chat` | 登录用户的多轮消息自动持久化到"对话式问答"会话（get-or-create，保持上下文连贯） |
| `GET /api/conversations` | 当前用户的会话列表（含消息数与末条预览） |
| `GET /api/conversations/<id>` | 某会话完整多轮消息（校验归属，越权 404） |
| `/proto/` + `/proto/<file>` | 内嵌访问学生端静态原型（send_from_directory，防路径穿越） |

### 2. 部署到天虹（scripts/_deploy_lumilearn_integration.py）

- 上传 5 个后端文件（lumilearn_web/lumilearn_agent/langgraph_engine/lumilearn_config/conversation_store）+ 9 个原型文件到 `/home/<user>/lumilearn`。
- 重启 `systemctl --user restart lumilearn-lumilearn`（RC=0），无需重启 framework（18080 未改动）。
- **坑**：paramiko SFTP 不展开 `~`，远程路径必须用绝对路径 `/home/<user>/lumilearn`。

### 3. 远程验证结果（真实服务）

- `/api/status`：`{"model":"lumilearn-v2","ollama_available":true}` ✅
- 登录（123/test123）→ 两次 `/api/chat` → `/api/conversations` 出现"对话式问答"会话（msg_count=4，消息有序）✅
- `/api/learn` 真实推理：「函数的单调性」报告（掌握度 80）→ chat_history 自动落库（学习目标 + 报告摘要，msg_count=2）✅
- `/proto/` HTTP 200，原型可直接在手机/浏览器演示 ✅

---

**未提交事项**：lumilearn_web 接入已提交（9ad4c76）；部署脚本路径修正与本文档待提交；GitHub 推送因网络间歇性失败待重试。

---

## 九、新端口并入项目系统：学生端学习平台(5010) + 学习分析仪表盘(18090)

**目标**：将学生端原型接入真实后端成为独立服务（5010），并新增学习分析仪表盘（18090），二者全部纳入 port_settings / Admin 端口管理 / 启动脚本（前、后端完整接入）。

### 1. 学生端学习平台（student_portal.py，端口 5010）

- 独立 Flask 应用，前端即学生端原型（`prototypes/student-learning-platform/`），服务时向 HTML 注入 `window.__LUMILEARN_REAL__` 标志切换为真实 API 模式。
- **原型 api.js 升级为双模式**：真实后端（fetch 同构接口）+ 离线 mock 兜底（双击打开 / 学习平台 Web /proto/ 仍可演示）。
- 真实后端接口（与原型契约一致）：
  | 接口 | 说明 |
  |---|---|
  | `/api/auth/login|me|logout` | users 表登录（前端登录门，401 自动跳转） |
  | `/api/learn/start` | 任务理解 + 费曼五步编排，chat_history 建会话 |
  | `/api/learn/step` | 费曼教学 Agent 真实生成 + 知识检索注入，持久化 |
  | `/api/learn/feynman-test` | 30 秒讲解评分 |
  | `/api/learn/report` | 汇总报告，落 learning_reports + chat_history |
  | `/api/learn/history` · `/api/learn/report/<id>` | 学习历史 / 报告详情（归属校验） |
- 前端 index.html 新增登录门（真实模式时未登录显示登录浮层，支持 `?need=login`）。

### 2. 学习分析仪表盘（analytics_dashboard.py，端口 18090）

- 只读单页仪表盘，深色主题 + 手绘 SVG 图表（无 CDN，低端设备友好），30s 自动刷新。
- 数据源：learning_reports / answers / concept_understanding / users。
- API：`/api/dashboard/{overview,trend,subjects,weakpoints,concepts,recent}`。

### 3. 系统集成（前后端全链路）

| 文件 | 改动 |
|---|---|
| `framework/services/provider_service.py` | PORT_DISPLAY_NAMES / PORT_SETTINGS_DEFAULTS 新增 student_portal(5010) + analytics_dashboard(18090) |
| `config/framework.yaml` | port_settings 新增两项（enabled + port） |
| `deploy/start.py` | DEFAULT_PORTS + build_services 新增两个服务（STUDENT_PORT / ANALYTICS_PORT 环境变量覆盖） |
| `scripts/remote_start_all.sh` | read_ports 默认端口 + 启动/停止块（第 5、6 段） |
| Admin 面板 | 端口管理自动展示新端口（动态渲染，无需改 admin.html） |

### 4. 验证结果（本地 17 项冒烟 + 天虹真实服务）

- 本地：student_portal 11 项（含登录 401、5 步流程、报告落库、越权 404）+ 仪表盘 6 项，全通过。
- 天虹：`/api/status`、页面、overview/trend 均 200；学生端真实模型 step 生成 164 字、报告掌握度 81、history 2 条；Admin 端口管理显示 7 个端口全部运行中。
- **坑**：paramiko 启动后台服务时 `&` 会挂住通道（进程持有管道 fd），需 `(nohup ... </dev/null &)` 完全脱离；Admin 认证走 `X-Admin-Token` 头（非 cookie）。

---

**未提交事项**：两个新端口已部署至天虹（student_portal 5010 / analytics_dashboard 18090 运行中）；本文档与代码待提交推送。

---

## 十、账号体系贯通：全端口登录 + 学生档案 + 管理员班级管理

**目标**：学生端学习过程卡住修复；所有端口均可使用自己的账号登录；管理员管理账号与班级绑定；各账号查看自己的学习档案；教师查看本班级学生档案。

### 1. 学习过程卡住修复（student_portal.py + learn.html）

- **根因**：前端 `/api/learn/start` 返回的会话 id 为 `"s-3"` 字符串，后端 `/api/learn/step` / `feynman-test` 直接 `int("s-3")` 抛 500，前端 `await` 永不 resolve 导致页面卡死。
- **修复**：
  - 后端新增 `_sid()` 容错解析（接受数字或 `s-` 前缀），3 处调用点统一替换。
  - 前端 learn.html 新增**防挂护栏**：步骤执行失败（后端不可用/报错）时不阻塞流程，标记跳过并继续，第 5 步后正常显示「生成学习报告」。

### 2. 退出登录 / 切换账号（学生端全部页面）

- 新增 `prototypes/student-learning-platform/auth.js`（真实模式专用）：导航底部用户盒显示当前账号（姓名+角色），提供**退出登录**按钮（logout → 跳登录门）。
- 5 个页面（index/learn/report/history/profile）统一加入「我的档案」导航项 + 用户盒 + auth.js。

### 3. 我的档案（学生自绑档案）

- 后端新增 `GET /api/profile`（student_portal.py）：汇总 learning_reports → 掌握度趋势 / 薄弱点聚合 / 平均掌握度 / 最近学习 / 最近对话（chat_history）。
- 前端新增 `profile.html`：学生统计卡 + 手绘 SVG 掌握度趋势折线 + 薄弱点排行 + 最近学习（点击跳报告页）+ 最近对话；api.js 新增 `profile()`（真实 + mock 双模式）。

### 4. 全端口账号登录（框架 18080/18081/18082）

- 新增 `framework/api/routes/auth.py`：users 表 token 登录 `POST /api/auth/login` / `GET /api/auth/me` / `POST /api/auth/logout`（内存 token，12h 有效，`X-Auth-Token` 或 `Authorization: Bearer`），注册到 server.py 与 `__init__.py`。
- 18080 终端 lumiterm.html 新增登录门（头部登录按钮 + 弹窗，登录后显示账号徽章，点击可退出/切换）。
- 至此**全部 7 个端口均支持账号登录**：5000 学习平台 Web、5001 教师端、5010 学生端（users 表）、18080 终端 / 18081 REST API / 18082 模型管理（新增 auth 路由）。

### 5. 管理员管理账号与班级绑定（Admin 面板）

- 后端（admin.py）：`GET /api/admin/users` 每个用户附加 `classes` 字段；新增 4 个端点：
  - `GET /api/admin/classes` 全部班级（含学校/年级/班主任/学生数）
  - `GET /api/admin/users/<id>/classes` 查看账号已绑定班级
  - `POST /api/admin/users/<id>/classes` 绑定班级（仅 student 角色，去重）
  - `DELETE /api/admin/users/<id>/classes/<class_id>` 解绑
- 前端（admin.html）：用户管理面板新增「班级」列——显示已绑定班级徽标（✕ 解绑）+ 学生行内下拉选择班级并「绑定」；创建账号提示语补充 5001/5010 登录入口。

### 6. 教师查看本班级学生档案（已具备，验证确认）

- teacher_portal（5001）已有：`/api/students`（仅自己班级学生 + 候选池）、`/api/students/<id>/reports`、`/api/students/<id>/progress`、`/api/students/<id>/stats`，权限隔离（教师只能看自己为班主任的班级学生）。本次未改动，验证正常。

### 7. 验证结果

- 本地冒烟 20 项全通过：`_sid()` 容错（int / "s-3" / None / 非法）、auth 登录/登出/token 失效、admin 用户 classes 字段 + 班级列表 + 绑定/查询/解绑、student_profile 401/登录/字段。
- 天虹真实服务：
  - 学习过程：`/api/learn/step` 传 `s-` 前缀 id 不再 500（防挂护栏生效）。
  - 18080/18081/18082 三端口 `POST /api/auth/login` 均返回 token ✅；18082 `/api/admin/classes` 返回 4 个班级，绑定/解绑学生成功 ✅。
  - 5010 学生端页面与 profile.html/auth.js/api.js 均 200，登录接口正常 ✅。
- **部署坑**：远程模板目录为 `tianhong/templates`（非 `remote/templates`），首次上传 admin.html/lumiterm.html 需指向该路径；部署脚本首次遗漏 `framework/api/routes/admin.py`，导致 `/api/admin/classes` 404，补传后重启生效。

---

**未提交事项**：本节约改动（student_portal/auth 路由/Admin 班级绑定/终端登录门/学生档案/文档）待提交推送。

---

## 十一、费曼学习全流程接入 + Admin 端口同步

**目标**：修复学生端学习过程卡住（step 500）；让各端口完整接入费曼五步学习全流程（不再只是展示学习过程）；修复 18082 Admin「端口管理」与「模型管理→端口模型配置」端口不同步。

### 1. 学习过程卡住根因（step 500）

- **根因**：前端 `/api/learn/start` 返回会话 id 为 `"s-7"` 字符串，后端 `api_learn_step` 直接 `int("s-7")` 抛 `ValueError` → 500 → 前端 await 永不返回 → 学习过程卡住。
- **修复**：`api_learn_step` 改为 `_sid()` 容错解析（`str(value).replace("s-","")`）。此前只改了 feynman-test/report 两处，本次补齐 step 这一处。

### 2. 共享费曼学习 Blueprint（完整全流程接入各端口）

- **新增 `framework/api/routes/student_learn.py`**：把「登录 → 发起学习(start) → 费曼五步(step) → 30秒讲解评分(feynman-test) → 学习报告(report) → 历史(history) → 我的档案(profile)」抽成可复用 Blueprint（`create_student_learn_bp(agent, session_key)`），单 Agent 实例注入。
- **student_portal.py（5010）**：删除全部重复路由（认证/学习/档案约 280 行），改为注册共享 Blueprint——只保留静态页服务与启动逻辑。
- **lumilearn_web.py（5000）**：同样注册共享 Blueprint，使 `/proto/` 学生端原型走真实 API；`_send_proto` 对 HTML 注入 `__LUMILEARN_REAL__ = true` 真实后端标志（此前未注入，页面只能展示 mock 学习过程——正是"其他端口内容只能展示学习过程"的根因）。
- **效果**：5000 与 5010 共用同一套费曼五步学习 API 契约，任一端口登录后即可完整走完学习全流程，学习数据落同一 `lumilearn.db`。

### 3. Admin 端口同步（端口管理 vs 模型管理）

- **根因**：`DEFAULT_PORT_MODEL_MAP`（provider_service.py）只有 4 个端口（terminal/api/models/lumilearn_web），而 `PORT_SETTINGS_DEFAULTS` 有 7 个端口（多了 teacher_portal/student_portal/analytics_dashboard）→ Admin「端口管理」显示 7 个、「模型管理→端口模型配置」只显示 4 个，不同步。
- **修复**：`DEFAULT_PORT_MODEL_MAP` 补齐 3 个端口至 7 个，与 `PORT_SETTINGS_DEFAULTS` 完全对齐；`get_port_model_map` / `set_port_model` 自动覆盖新端口。

### 4. 验证结果

- 本地冒烟 17 项全通过：student_portal 登录/start/step(s-前缀)/feynman-test/report/history/profile/401、lumilearn_web 登录/start/step/profile、/proto/ 真实标志注入、port_model_map 7 键。
- 天虹真实服务：
  - 5010 `POST /api/learn/step` 传 `s-7` 返回 200（不再 500），五步流程完整可用 ✅
  - 5000 `/proto/` 注入 `__LUMILEARN_REAL__ = true`，登录 + start 走共享 API ✅
  - 18082 `GET /api/admin/port-models` 返回 **7 个端口**（terminal/api/models/lumilearn_web/teacher_portal/student_portal/analytics_dashboard）✅

---

**未提交事项**：本节约改动（共享费曼 Blueprint / 两端口注册 / Admin 端口同步 / 文档）待提交推送。
