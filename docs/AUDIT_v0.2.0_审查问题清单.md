# LumiLearn v0.2.0-beta 深度审查问题清单

> **审查对象**：本地工作副本（`e:\学习LLM\lumilearn`）
> **审查日期**：2026-09-12
> **方法**：对照《v0.2.0-beta 测评档案》逐项静态核验 + 新增审计项
> **说明**：本清单不含任何真实凭据/内网 IP，全部用占位符或代码路径指代，可安全进入公开仓库。

---

## 0. 一句话结论

测评档案中"学生端仪表盘加载中"等 P0 问题在当前工作副本**已修复**。本轮深度审查确认了 10 项问题，其中**已修复 6 项**（S1 安全接口鉴权、S5 错误串脱敏、F3 管理员登录死锁、S3 登录防护+Token 过期、S4 强制改密拦截），剩余 4 项为工程/基建类（S2 支付桩、S6 依赖锁、S7 集成测试、S8 端点统一），已给出方案。

**2026-09-12 更新**：本轮已落地 F3/S1/S3/S4/S5 五项修复，并新增回归测试 `tests/test_security_fixes.py`（8 用例）锁定修复效果。

---

## 1. 前端问题

### F1（已修复）学生端仪表盘"加载中…"
- **级别**：P0（测评存档），当前已修复
- **证据**：[index.html](framework/../prototypes/student-learning-platform/index.html#L135-L203) `render()` 期望字段与真实后端 `profile`/`status`/`resources` 返回契约对齐，三请求均有 `.catch` 兜底，不会 Promise 挂死。
- **状态**：无法复现，判定为已修复。

### F2（低）学生端问候语缺失用户名
- **级别**：P2
- **证据**：[index.html](framework/../prototypes/student-learning-platform/index.html#L138) 用 `u.name || "同学"`。仅当用户无 `name` 字段才退化为"同学"。
- **建议**：可忽略；若需兜底，在用户创建时强制补 `display_name`。

### F3（确认真实）管理员首次浏览器登录死锁
- **级别**：P1（功能阻塞）
- **根因链**：
  1. 页面门禁 [_page_role](framework/api/server.py#L290-L300) 只校验 `users` 表/session 角色，**不认 `admins` 表，也不认 X-Admin-Token**；
  2. 主页登录 `/api/auth/login`（[auth.py](framework/api/routes/auth.py)）**只查 `users` 表**，admin 不在其中 → 401；
  3. `/admin*` 各页在无 session 时一律 `redirect("/")`（[server.py:302-340](framework/api/server.py#L302-L340)）。
- **结果**：管理员既无法从主页登入，也无法到达带登录表单的 `/admin/console`（同样被门禁弹回），**无任何浏览器路径进后台**。
- **建议修复方向**（需认证整合，非一行小改）：
  - 方案 A（推荐）：统一会话——在 `/api/auth/login` 中对 `users` 与 `admins` 两张表都做校验，命中 admin 时同时写入 `session["role"]="admin"` 与会话身份，使 `_page_role` 放行，且 admin 前端能拿到可用令牌。
  - 方案 B：`/admin` 未登录时不 302，改为渲染页面并由 admin.js 内联登录门接管（需确保 admin.js 令牌与页面门禁两套体系打通）。
  - 方案 C：主页角色卡片把"管理端"直链到独立登录页，登录页用 `admins` 表认证并建立 session。

### F4（部分缓解）未登录可打开 /learn、/classroom、/student 静态壳
- **级别**：P2
- **证据**：[server.py:383-410](framework/api/server.py#L383-L410) 无鉴权直出页面壳；[app.js](prototypes/student-learning-platform/app.js#L115-L122) 未登录已弹登录门而非纯转圈。
- **判定**：SPA 壳公开属常见做法，数据 API 均需认证，安全边界成立，可接受。

---

## 2. 后端 / 安全问题

### S1（确认真实，高危）安全管理读接口裸奔
- **级别**：P0（信息泄露）
- **证据**：[security.py](framework/api/routes/security.py) 以下端点**无任何鉴权装饰器**，且返回 `local_ip`/`internal_ip`/防火墙规则/网关日志等内网敏感信息：
  - `GET /api/security/status`（L24）
  - `GET /api/security/gateway/stats`（L40）
  - `GET /api/security/gateway/logs`（L89）
  - `GET /api/security/firewall/rules`（L100）
  - `GET /api/security/recommendations`（L227）
  - `POST /api/security/firewall/check`（L156）
- **额外发现（违反测评结论）**：`DELETE /api/security/firewall/rules/<rule_id>`（L144）**也是无鉴权写操作**，可在未登录时删除防火墙规则。测评报告称"写操作已 401"，与当前代码矛盾。
- **修复**：对这些端点统一加 `@require_admin`。

### S2（确认真实，桩）支付端点全为 TODO 空桩且无鉴权
- **级别**：P0（接真实支付前必修）/ 当前因空桩无真实资金风险
- **证据**：[payment.py](framework/api/routes/payment.py)：`/api/payment/notify` 无验签直接 `return "success"`；`/api/payment/create`、`/api/payment/status/<id>` 无用户鉴权。
- **建议**：接真实支付宝前补 RSA2 验签 + 用户鉴权；空桩阶段至少在 create/status 加用户登录校验。

### S3（确认真实，中危）普通用户登录无暴力破解防护 + 用户 Token 不过期
- **级别**：P1
- **证据**：
  - 管理员登录有锁定（[admin/auth.py:28-64](framework/admin/auth.py#L28-L64)），但用户 `/api/auth/login` 无此防护；
  - 用户 Token TTL 定义 12h（[auth.py:31](framework/api/routes/auth.py#L31)），但 `get_user_by_token` 不校验 `created_at`，永不过期。
- **修复**：为用户登录加失败计数+锁定；在 get_user_by_token 增加过期判断（`created_at` 距今 > 12h 视为无效）。

### S4（确认真实，低）管理员强制改密只标记不阻断
- **级别**：P1（策略）
- **证据**：[admin/auth.py:103-141](framework/admin/auth.py#L103-L141) `login()` 返回 `must_change_password` 字段，但 [require_admin](framework/admin/auth.py#L196-L208) 不检查该标志，改密前仍可调用全部管理接口。
- **修复**：在 `require_admin` 中当 `admin["must_change_password"]` 为真时，仅放行改密/登出端点，其余返回 403。

### S5（确认真实，低）LLM 错误串外泄
- **级别**：P2
- **证据**：[feynman.py:329](framework/api/routes/feynman.py#L329) `f"费曼测试失败: {str(e)}"`、[feynman.py:428](framework/api/routes/feynman.py#L428) 直接回吐异常原文；Ollama 离线时会把 `Connection refused <addr>:<port>` 泄露给客户端。
- **修复**：对外返回通用错误文案，完整异常仅写日志。

### S6（确认真实，工程）依赖版本全浮动、无锁文件
- **级别**：P1（可复现性/供应链）
- **证据**：[requirements.txt](requirements.txt) 31 个包全 `>=` 浮动，无 pip-tools/poetry lock。
- **建议**：用 `pip-compile` 生成锁定版本文件，CI 用锁文件安装。

### S7（确认真实，测试基建）8 个核心集成测试被排除
- **级别**：P2
- **证据**：[conftest.py:14-23](tests/conftest.py#L14-L23) `collect_ignore` 排除 8 个依赖本地 Web/Ollama 的脚本式测试。
- **建议**：改用 `flask test_client` 在 CI 内起应用，纳入回归。

### S8（确认真实，低）双套登录端点不一致
- **级别**：P2
- **证据**：`/api/auth/login`（用户）与 `/api/admin/login`（管理员）两套体系并存，前端/文档易混乱。见 F3 修复方案 A/B 的统一建议。

---

## 3. 做得对的部分（无需改动）

- CORS 白名单机制（[server.py:105-125](framework/api/server.py#L105-L125)），无 `*` 通配，符合硬约束。
- 密码哈希 `werkzeug.security`；默认管理员高熵随机密码 + 强制改密标记。
- 管理员 token 12h 过期已生效（[admin/auth.py:153](framework/admin/auth.py#L153)）。
- CSRF 防护已注册（[config.py:135-176](framework/core/config.py#L135-L176)）：Origin/Referer 校验 + 会话 Token。
- SQL 全参数化；CSP / X-Frame-Options / X-Content-Type-Options 头齐全。
- 可信 Host 仅在显式配置时启用，无仓库内硬编码真实地址。

---

## 4. 优先级汇总

| 编号 | 问题 | 级别 | 状态 | 建议动作 |
|---|---|---|---|---|
| S1 | 安全管理读接口裸奔 + 无鉴权删除规则 | P0 | ✅ 已修复 | 7 端点统一加 `@require_admin` |
| S5 | LLM 错误串外泄 | P2 | ✅ 已修复 | 对外通用文案，异常仅写日志 |
| F3 | 管理员浏览器登录死锁 | P1 | ✅ 已修复 | `/api/auth/login` 兼容 admins 表 + 写 session role |
| S3 | 用户登录无防护 + Token 不过期 | P1 | ✅ 已修复 | 加锁定（5 次/15 分钟）+ TTL 过期校验 |
| S4 | 强制改密不阻断接口 | P1 | ✅ 已修复 | `require_admin` 拦截 + admin.js 改密弹窗 |
| S2 | 支付空桩无验签/无鉴权 | P0* | ⬜ 待办 | 接真实支付前必修 RSA2 验签 + 鉴权 |
| S6 | 依赖浮动无锁 | P1 | ⬜ 待办 | 生成锁文件（pip-compile） |
| S7 | 8 集成测试被排除 | P2 | ⬜ 待办 | 改用 test_client 纳入 CI |
| S8/F2/F4 | 端到端一致性/边缘项 | P2 | ⬜ 待办 | 统一登录端点 / 兜底字段 |

> *S2 当前为空桩无真实资金风险，标 P0 表示"接真实支付前必须修"。

---

## 5. 本轮修复与验证记录（2026-09-12）

### 5.1 代码改动
| 文件 | 改动 |
|---|---|
| [security.py](../framework/api/routes/security.py) | 7 个敏感端点补 `@require_admin`（status/gateway stats/gateway logs/firewall rules GET/firewall check/firewall DELETE/recommendations） |
| [feynman.py](../framework/api/routes/feynman.py) | 2 处异常响应脱敏，完整异常仅留服务端日志 |
| [auth.py](../framework/api/routes/auth.py) | 新增登录锁定 + Token `expires_at` 过期校验；登录兼容 admins 表（F3）；`/api/auth/me` 识别管理员会话 |
| [admin/auth.py](../framework/admin/auth.py) | `require_admin` 增加强制改密拦截（放行改密/登出/身份查询） |
| [admin.py](../framework/api/routes/admin.py) | `/api/admin/me` 返回 `must_change_password` |
| [admin.js](../static/ui/admin.js) | 新增强制改密弹窗；403 且带标志时弹改密窗而非登录门 |
| [index.html](../remote/templates/index.html) | 管理员登录后把令牌写入 `localStorage['admin_token']`，跳转管理端无缝衔接 |
| [conftest.py](../tests/conftest.py) | 测试夹具管理员口令由弱口令 `admin123` 改为 `TestAdmin2026`（弱口令会被产品标记强制改密，导致业务测试 403） |
| [test_security_fixes.py](../tests/test_security_fixes.py) | 新增 8 条回归用例，锁定 S1/S3/F3/S4 |

### 5.2 测试结果
- 全量基线（修复前）：**784 passed / 3 skipped / 0 failed**
- 端到端验证脚本（一次性）：**21/21 通过**（S1 7 项 + S3 3 项 + F3 4 项 + S4 5 项 + S3b 2 项）
- 新增回归测试：**8 passed**
- 全量回归（修复后）：**792 passed / 3 skipped / 0 failed**（40:43 时长；新增 8 条回归用例全部通过，无既有用例回归失败）

### 5.3 需要部署方知悉的行为变更
1. **管理员改经统一入口登录**：`POST /api/auth/login` 现同时接受 admins 表账号，返回 `admin_token`；管理端页面 `/admin*` 登录后不再被弹回首页。
2. **首次登录强制改密生效**：`must_change_password=1` 的管理员，在改密前调用业务接口会收到 `403 {must_change_password: true}`；改密/登出/身份查询仍放行，管理端会自动弹出改密窗。
3. **用户 Token 12 小时过期**：此前 token 永不过期，现在超时需重新登录。
4. **登录连续失败 5 次锁定 15 分钟**（按 IP+用户名）。