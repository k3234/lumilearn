# LumiLearn 安全审计报告

> **审计日期**: 2026-08-16
> **审计范围**: 全项目 Python/Flask/HTML 代码（排除 venv/、archive/、docs/、测试数据目录）
> **审计方法**: 基于 Flask 3.1 安全规范系统性扫描 + 关键路径人工核实
> **结论**: 发现 **3 个严重（Critical）**、**4 个高危（High）**、**6 个中危（Medium）**、若干低危问题。核心风险集中在**无认证的远程代码执行端点**。

---

## 一、执行摘要

LumiLearn 是一个功能丰富的教育智能体系统，后端能力扎实（费曼教学、多 Agent、RAG、安全网关组件齐全），但在 **API 暴露面治理** 上存在系统性缺口：多个可执行任意代码/命令的端点**未挂任何认证**，安全网关组件（IP 白名单、限流、防火墙）**未接入实际请求链**，形成"安全组件存在但未生效"的局面。

**最优先修复**：3 个 Critical（沙箱 RCE、训练端点 RCE、默认管理员口令）。

---

## 二、修复进度

| 编号 | 问题 | 严重性 | 状态 | 修复要点 |
|:---|:---|:---|:---|:---|
| C-1 | 代码沙箱任意代码执行 | Critical | ✅ 已修复 | AST 拦截裸调用+属性链逃逸；`allowed_builtins` 仅保留纯计算函数；移除二次 exec 通道；`threading.Thread` 真超时；`execute_code` 加 `@require_admin`；`user_id` 改服务端生成 |
| C-2 | 模型训练端点命令注入 | Critical | ✅ 已修复 | `trigger_training`/`switch_model`/`compare_models` 加 `@require_admin`；API 层 `_validate_training_params` 正则白名单；`train_lumilearn.sh` 纵深校验（名称/学科/整数） |
| C-3 | 默认超级管理员账号使用弱口令 | Critical | ✅ 已修复 | 初始密码改环境变量或随机生成；`must_change_password` 强制改密；存量账号登录自动触发强制改密；改密最小 6 位；全部运维脚本硬编码口令/IP 清除并改环境变量 |
| H-1 | SECRET_KEY 硬编码默认值 | High | ✅ 已修复 | 新增 `get_app_secret_key`（fail-closed）：生产缺失环境变量拒绝启动，非生产随机生成；三入口 + `.env.example` 更新 |
| H-2 | 前端 XSS | High | ✅ 已修复 | 6 个模板统一 `esc()`（含单引号转义）；innerHTML 动态插值全部包裹；animation_learn 的 onclick 字符串注入改 data-* + addEventListener；修复遗漏的 err.message 反射路径 |
| H-3 | CORS 全通配 | High | ✅ 已修复 | `Access-Control-Allow-Origin` 由 `*` 改为白名单回显（环境变量 `CORS_ALLOWED_ORIGINS`）；server.py/lesson_engine/配置默认值同步 |
| H-4 | Manim 动画代码注入 | High | ✅ 已修复 | 新增 `sanitize_for_code` 字符白名单；formula/geometry 默认动画的 topic 拼入源码前清洗 |
| M-1 | 无 CSRF 防护 | Medium | ✅ 已修复 | 新增 `register_csrf_guard`（Origin/Referer 校验），注册到 goai_web/teacher/student 三入口 |
| M-2 | Cookie 安全属性未配置 | Medium | ✅ 已修复 | 三入口设置 `SESSION_COOKIE_HTTPONLY/SAMESITE=Lax`，SECURE 由环境变量控制 |
| M-3 | 请求体/Host/ProxyFix 缺失 | Medium | ✅ 已修复 | 全入口 `MAX_CONTENT_LENGTH=10MB`；server.py `TRUSTED_HOSTS` + 可选 ProxyFix（`LUMILEARN_PROXY_ENABLED`） |
| M-4 | X-API-Key 只校验存在性 | Medium | ✅ 已修复 | 安全写操作端点已全部改为 `@require_admin`（C-1 连带），无仅查非空的 X-API-Key 路径 |
| M-5 | CSP `'unsafe-inline'` 弱化 | Medium | ⏳ 设计取舍 | 单文件 HTML + 内联 JS 架构依赖 inline 脚本；已配合 H-2 全量转义降低风险，彻底收紧需拆分静态资源 |
| M-6 | 管理员登录无暴力破解防护 | Medium | ✅ 已修复 | 同 IP+用户名 5 次失败锁定 15 分钟（内存态），成功登录清零 |
| M-7 | 文件上传链路缺校验 | Medium | ✅ 已修复（防御代码已落地，路由仍为桩） | 新增 [framework/security/uploads.py](file:///e:/学习LLM/lumilearn/framework/security/uploads.py)：secure_filename 清洗、扩展名白名单、大小上限（图 5MB/音 10MB）、魔数真实性校验；`recognize_file`/`transcribe_file` 接入全部校验；路由接线上传端点时直接复用 |
| M-8 | 主题进入文件名未过滤 `..` | Medium | ✅ 已修复 | goai_agent/langgraph_engine 文件名清洗追加 `..` 过滤 |
| L-1 | SSTI 反模式 | Low | ⏳ 待处理 | `render_template_string` 渲染原型 HTML，当前无载荷；低危 |
| L-6 | torch.load 未用 weights_only | Low | ✅ 已修复 | 新增 `torch_load_safe`（weights_only=True + 旧版兼容）；model/trainer 均切换 |
| L-7 | 安全网关未接入请求链 | Low | ⏳ 设计取舍 | IP 白名单/限流组件存在但未挂接；后续如需可接入 before_request |

**验证**：`pytest tests/test_security_sandbox.py tests/test_admin_auth.py tests/test_admin_api.py tests/test_learning_dashboard.py tests/test_upload_security.py` → 76 passed（2026-08-16）。登录限流行为手动验证通过（5 次失败后锁定）；CORS 局域网 IP 场景手动验证通过。

---

## 三、严重（Critical）

### C-1 代码沙箱任意代码执行（未认证 RCE）

| 项目 | 内容 |
|:---|:---|
| **位置** | [security.py](file:///e:/学习LLM/lumilearn/framework/api/routes/security.py#L167-L186) `execute_code()` → [sandbox.py](file:///e:/学习LLM/lumilearn/framework/security/sandbox.py) |
| **严重性** | Critical |

**证据**：
- 端点 `POST /api/security/sandbox/execute` **无任何认证**，接收客户端提交的任意 Python 代码
- AST 检查器 [sandbox.py:69-77](file:///e:/学习LLM/lumilearn/framework/security/sandbox.py#L69-L77) `visit_Call` 只拦截 `ast.Attribute` 形式调用（如 `os.system(...)`），**裸调用 `exec(...)`/`eval(...)`/`open(...)` 完全不检查**
- 实际生效的 `allowed_builtins` [sandbox.py:250-271](file:///e:/学习LLM/lumilearn/framework/security/sandbox.py#L250-L271) **直接包含** `eval`、`exec`、`compile`、`open`、`getattr`、`globals`、`setattr`、`input`、`vars` 等全部逃逸原语
- [sandbox.py:216-247](file:///e:/学习LLM/lumilearn/framework/security/sandbox.py#L216-L247) 的安全版 `safe_builtins` 是**死代码**，从未使用
- `user_id` 由客户端传入（security.py:172），限流可被伪造绕过

**利用示例**：`POST /api/security/sandbox/execute`，body `{"code": "exec(\"import os; os.system('id')\")"}` → 直接执行系统命令。

**影响**：未认证攻击者可执行任意系统命令、读写任意文件。配合 CORS `*`（见 H-3），公网可达时即完全接管服务器。

**修复**：① 端点加认证（`@require_admin`）或直接**移除**该端点；② 废弃自研 AST 沙箱，改用系统级隔离（容器/firejail/受限子进程+资源限制）；③ 删除 `allowed_builtins` 中的逃逸原语。

---

### C-2 模型训练端点命令注入（未认证 RCE）

| 项目 | 内容 |
|:---|:---|
| **位置** | [models.py](file:///e:/学习LLM/lumilearn/framework/api/routes/models.py#L243-L294) `trigger_training()` → [train_lumilearn.sh](file:///e:/学习LLM/lumilearn/train_lumilearn.sh) |
| **严重性** | Critical |

**证据**：
- `POST /api/models/train` **无认证**（models_bp 全程无装饰器），`request.get_json(force=True)` 强制解析任意 Content-Type
- 用户可控参数 `model_name` / `base_model` / `subjects` 直接传入 `subprocess.Popen(["bash", script, "--model-name", model_name, ...])`（models.py:61-66）
- 虽然 Popen 用列表参数（无 shell），但 `train_lumilearn.sh` 内部把变量**无转义拼接进 `python3 -c "..."` 源码字符串**（如 `model='$BASE_MODEL'`、`subjects = '$SUBJECTS'.split(',')`、`output_path = 'outputs/$MODEL_NAME/...'`），单引号闭合即可注入任意 Python 代码

**影响**：未认证攻击者可注入任意 Python 代码以服务器权限执行；同时该端点可被滥用触发大量训练任务（资源耗尽 DoS）。

**修复**：① 端点加认证；② `model_name`/`base_model`/`subjects` 白名单校验（如 `^[A-Za-z0-9_\-:.]+$`）；③ 训练脚本改为单引号 heredoc 传参，禁止用户变量嵌入 `python3 -c` 源码串。

---

### C-3 默认超级管理员账号弱口令问题

| 项目 | 内容 |
|:---|:---|
| **位置** | [auth.py](file:///e:/学习LLM/lumilearn/framework/admin/auth.py#L33-L43) `_ensure_default_admin()` |
| **严重性** | Critical |

**证据**：首次运行自动创建密码为 `[REDACTED]` 的超级管理员（公开弱口令）。[admin.py:27-37](file:///e:/学习LLM/lumilearn/framework/api/routes/admin.py#L27-L37) 登录端点**无速率限制/锁定**，可被在线暴力破解。超级管理员可访问全部 60+ 管理端点（用户管理、API Key、模型/Agent 管理、数据导出）。

**影响**：部署后未改密即被接管整个系统。

**修复**：① 改为首次登录强制改密；② 登录端点加失败次数限制/延迟；③ 部署脚本移除硬编码口令（见 L-4）。

---

## 四、高危（High）

### H-1 SECRET_KEY 硬编码默认值（session 伪造）

| 项目 | 内容 |
|:---|:---|
| **位置** | [goai_web.py:46](file:///e:/学习LLM/lumilearn/goai_web.py#L46)、[teacher_portal.py:41](file:///e:/学习LLM/lumilearn/teacher_portal.py#L41)、[student_portal.py:42](file:///e:/学习LLM/lumilearn/student_portal.py#L42) |
| **严重性** | High |

**证据**：三处入口使用公开硬编码密钥作为 fallback（`lumilearn-goai-web-secret` 等），`.env.example` 未列出这三个变量，实际部署大概率使用默认值。三个端口共享同一数据库，session 只存 `user_id`。

**影响**：知晓密钥者可离线伪造任意 `user_id` 的 session cookie，直接以任意用户（含教师）身份登录。

**修复**：生产环境强制从环境变量/密钥管理器读取，无环境变量则启动失败（fail-closed）；`.env.example` 补充变量说明。

---

### H-2 前端存储型/反射型 XSS（innerHTML 拼接未转义）

| 项目 | 内容 |
|:---|:---|
| **位置** | 多个前端模板 |
| **严重性** | High |

**命中清单**（数据来自用户输入/AI 生成内容，未转义即拼入 HTML）：

| 文件 | 行号 | 风险点 |
|:---|:---|:---|
| [goai_learn.html](file:///e:/学习LLM/lumilearn/remote/templates/goai_learn.html#L517-L565) | 517-565 | 学习历史/报告/薄弱点/建议 `innerHTML` 拼接 |
| [lumiterm.html](file:///e:/学习LLM/lumilearn/remote/templates/lumiterm.html#L1543-L1546) | 1543-1546 | 图表块 `title` 未转义 |
| [classroom.html](file:///e:/学习LLM/lumilearn/remote/templates/classroom.html#L2683-L2692) | 2683/2692/3363/3380 | 题目解释/幻灯片标题未转义 |
| [animation_learn.html](file:///e:/学习LLM/lumilearn/remote/templates/animation_learn.html#L1077-L1088) | 1077-1088 | 属性/JS 字符串注入（`onclick="selectNode('${node.name}')"`） |
| [admin.html](file:///e:/学习LLM/lumilearn/remote/templates/admin.html#L664) | 664/256-261/364-365/707-710/1349 | 模型名/agent_id 注入，且 `esc()` 不转义单引号 |
| [student-learning-platform](file:///e:/学习LLM/lumilearn/prototypes/student-learning-platform) | 多个 | `learn.html:213`、`history.html:125` 等 |

**影响**：恶意用户提交含 `<script>` 的内容（如 topic），或 AI 输出被提示注入污染，可执行任意 JS（窃取 session、钓鱼）。

**修复**：所有 `innerHTML` 拼接前统一走转义函数（含单引号）；`onclick` 内插值改用 `data-*` 属性 + `addEventListener`；优先 `textContent`。

---

### H-3 CORS 全通配 `*` + 无认证 API

| 项目 | 内容 |
|:---|:---|
| **位置** | [server.py:84-96](file:///e:/学习LLM/lumilearn/framework/api/server.py#L84-L96)、[config.py:38](file:///e:/学习LLM/lumilearn/framework/core/config.py#L38)、[security/config.py:55](file:///e:/学习LLM/lumilearn/framework/security/config.py#L55)、[lesson_engine.py:636](file:///e:/学习LLM/lumilearn/lesson_engine.py#L636) |
| **严重性** | High |

**证据**：`after_request` 对所有响应（含 HTML 页面）加 `Access-Control-Allow-Origin: *`，允许任意来源调用 18081 的**无认证 API**（见 C-1、C-2 及 chat.py/ocr.py/speech.py 等全部无认证端点）。

**影响**：任何恶意网站可跨域调用并读取所有无认证 API 响应，放大 C-1/C-2 的攻击面。

**修复**：CORS 改为显式白名单来源；无认证端点必须加认证（从根本上解决）。

---

### H-4 Manim 动画生成代码注入

| 项目 | 内容 |
|:---|:---|
| **位置** | [formula_gen.py:118-128](file:///e:/学习LLM/lumilearn/animation/generators/formula_gen.py#L118-L128)、[geometry_gen.py:185-194](file:///e:/学习LLM/lumilearn/animation/generators/geometry_gen.py#L185-L194) → [manim_service.py:55-82](file:///e:/学习LLM/lumilearn/framework/services/manim_service.py#L55-L82) |
| **严重性** | High |

**证据**：用户主题直接 f-string 拼入待执行 Python 源码（`title = Text("{topic}", ...)`），`topic` 含 `"`/换行即可注入任意 Python 语句；manim CLI 会真正执行该 `.py` 文件。此链路**完全绕过沙箱**。

**影响**：触发动画生成的学生可执行任意 Python 代码。

**修复**：`topic` 进入源码前做字符转义/白名单（仅允许中英文数字与常见符号），或 manim 执行也走隔离环境。

---

## 五、中危（Medium）

### M-1 无 CSRF 防护

**位置**: 全项目 cookie 认证的 POST/PUT/DELETE 路由（goai_web.py、teacher_portal.py、student_learn.py）
**证据**: 未发现 CSRFProtect/Flask-WTF/Origin 校验；`request.get_json(force=True)` 使 `text/plain` 跨站请求也能携带合法 JSON。**影响**: 跨站可触发 logout 等操作。**修复**: 加 CSRFProtect 或要求自定义 header + SameSite。

### M-2 会话 Cookie 安全属性未配置

**位置**: 全项目
**证据**: `SESSION_COOKIE_SECURE` / `HTTPONLY` / `SAMESITE` 均未设置。**修复**: 生产环境设 `SESSION_COOKIE_HTTPONLY=True`、`SAMESITE='Lax'`，HTTPS 部署时设 `SECURE=True`（本地 HTTP 调试勿开 Secure，避免 cookie 失效）。

### M-3 请求体大小 / Host 校验 / ProxyFix 未设置

**位置**: 全项目
**证据**: `MAX_CONTENT_LENGTH`、`TRUSTED_HOSTS`、`ProxyFix` 均缺失。OCR/语音等上传端点无体积上限。**修复**: 设置 `MAX_CONTENT_LENGTH`、`TRUSTED_HOSTS`，反代部署时配置 ProxyFix。

### M-4 `X-API-Key` 只校验存在性

**位置**: [security.py:195-197](file:///e:/学习LLM/lumilearn/framework/api/routes/security.py#L195-L197)
**证据**: `if not api_key` 仅检查非空，任意值即可通过并触发系统级防火墙修改。**修复**: 校验密钥值或改用 `@require_admin`。

### M-5 CSP `'unsafe-inline'` 弱化

**位置**: [server.py:107-119](file:///e:/学习LLM/lumilearn/framework/api/server.py#L107-L119)
**证据**: `script-src 'self' 'unsafe-inline'` 使 CSP 无法兜底 H-2 的 XSS。**修复**: 逐步移除 inline 脚本，收紧 CSP（`X-Frame-Options: DENY`、nosniff 已正确设置）。

### M-6 管理员登录无暴力破解防护

**位置**: [admin.py:27-37](file:///e:/学习LLM/lumilearn/framework/api/routes/admin.py#L27-L37)、[auth.py:66-88](file:///e:/学习LLM/lumilearn/framework/api/routes/auth.py#L66-L88)
**证据**: 登录端点无速率限制/锁定，叠加 C-3 默认口令构成组合风险。**修复**: 失败次数限制 + 延迟 + 锁定。

### M-7 文件上传链路缺校验（暂未接线）

**位置**: [ocr_service.py:122-151](file:///e:/学习LLM/lumilearn/framework/services/ocr_service.py#L122-L151)、[speech_service.py:86-110](file:///e:/学习LLM/lumilearn/framework/services/speech_service.py#L86-L110)
**证据**: `is_allowed_extension` 定义但从未被路由调用；无大小限制；全项目 `secure_filename` 零命中。缓解因素：当前路由均为 base64 JSON TODO 桩，`request.files` 零命中。**修复**: 未来接线时补齐 `secure_filename` + 白名单 + 大小限制。

### M-8 主题进入文件名未过滤 `..`

**位置**: [goai_agent.py:645-648](file:///e:/学习LLM/lumilearn/goai_agent.py#L645-L648)、[langgraph_engine.py:616-619](file:///e:/学习LLM/lumilearn/langgraph_engine.py#L616-L619)
**证据**: `re.sub(r'[\\/:*?"<>|]', '_', topic)` 已拦截路径分隔符，`../` 无法构成，但 `..` 未单独拦截。**修复**: 追加 `..` 过滤或直接用 `secure_filename`。

---

## 五、低危 / 信息级

### L-1 SSTI 反模式（无实际载荷）
[student_portal.py:67](file:///e:/学习LLM/lumilearn/student_portal.py#L67) 用 `render_template_string` 渲染原型 HTML。当前模板不含 Jinja2 语法（无利用载荷），但属反模式——模板一旦被注入 `{{ }}` 即执行任意表达式。**建议**：改用普通文件读取 + 字符串替换。

### L-2 开放重定向 — **未发现**
`redirect()` 仅一处固定路径 `redirect("/admin")`（server.py:160），无用户输入。

### L-3 SQL 注入 — **未发现可利用点**
全部 SQL 使用参数化 `?` 占位符；f-string 动态列名均来自硬编码白名单（database.py 多处），值全走参数化。审计确认**安全**。

### L-4 硬编码管理员口令的运维脚本
[scripts/_deploy_feynman_flow.py:91](file:///e:/学习LLM/lumilearn/scripts/_deploy_feynman_flow.py) 硬编码 `[REDACTED_CREDS]` 走 SSH。本地运维脚本，建议改为环境变量。

### L-5 敏感信息泄漏 — **基本未发现**
`.env` 未被 git 追踪；`.gitignore` 已覆盖 `.env`/`*.db`/`*.key` 等；密码使用 `generate_password_hash` 存储；`session[...]` 仅存 `user_id`。测试脚本打印 API Key 前 8 位（已截断）。**符合预期**。

### L-6 torch.load 未启用 weights_only（2 处）
[model.py:391-392](file:///e:/学习LLM/lumilearn/framework/model.py#L391-L392)、[trainer.py:263](file:///e:/学习LLM/lumilearn/framework/trainer.py#L263)。建议 `torch.load(..., weights_only=True)`（checkpoint 路径来自用户可控 model_name，组合存在 pickle RCE 风险）。

### L-7 安全网关未接入实际请求链
`SecurityGateway.check_request`（[gateway.py:43](file:///e:/学习LLM/lumilearn/framework/security/gateway.py#L43)）、`NetworkFirewall.check_access` 未挂接任何 Flask `before_request`（唯一 before_request 是 server.py:79 的 OPTIONS 处理），IP 白名单/限流实际**不拦截任何请求**。**建议**：将网关接入请求链，或移除未使用的安全组件。

---

## 七、已确认的安全实践（正面清单）

- ✅ 密码使用 `werkzeug.security.generate_password_hash` 存储
- ✅ SQL 全部参数化，无字符串拼接注入
- ✅ `.gitignore` 覆盖敏感文件（.env/密钥/数据库）
- ✅ 已设置 `X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`、基础 CSP
- ✅ 路径穿越防护（`_send_proto` 等使用 normpath + `..` 检测 + isfile 三重校验）
- ✅ 无 open redirect、无 pickle/yaml.load 不安全反序列化（除 torch.load）

---

## 七、修复优先级建议

### P0（立即，阻止 RCE）
1. **C-1**：`/api/security/sandbox/execute` 加认证或移除；沙箱逃逸原语删除
2. **C-2**：`/api/models/train` 加认证 + 参数白名单校验
3. **C-3**：默认管理员首次登录强制改密

### P1（短期，阻止越权/伪造）
4. **H-1**：SECRET_KEY 强制环境变量
5. **H-2**：前端 innerHTML 统一转义
6. **H-3**：CORS 白名单化
7. **H-4**：Manim topic 白名单
8. **M-1/M-2**：CSRF + cookie 安全属性
9. **M-4**：X-API-Key 真正校验

### P2（中期加固）
10. **M-3**：MAX_CONTENT_LENGTH / TRUSTED_HOSTS / ProxyFix
11. **M-6**：登录限流
12. **L-6**：torch.load weights_only
13. **M-8**：文件名 `..` 过滤

---

*本报告基于静态代码审计，建议修复后重新扫描验证。部分配置类问题（TLS、反代）需结合实际部署环境确认。*
