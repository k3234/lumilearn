# LumiLearn v0.2.0-beta 测评报告

> 评测日期：2026-09-11　|　环境：Windows 本机 + 天虹主机 Docker 隔离容器
> 范围：v0.2.0-beta（统一双端口架构：18080 管理门户 / 18081 REST API，lumi 单色极简设计系统）

---

## 一、结论总览

| 维度 | 方法 | 结果 |
| --- | --- | --- |
| 功能回归 | 71 项真实 HTTP 冒烟（16 HTML 路由 + 8 静态资源 + 真实登录 + 13 会话页面字节比对 + 24 管理 API + 8 REST API + 2 鉴权边界） | **71/71 通过** |
| 跨设备可移植性 | 天虹主机 Docker 容器内自测 + 经 SSH 隧道从本机复测 | **两轮均 71/71** |
| 页面正确性 | 会话页面与本地模板**字节级一致** | 13/13 一致 |
| 安全隐患 | 跟踪文件敏感信息扫描 + 全工作树扫描 | 无真实主机 IP / 用户名 / 口令 / API Key 进入待提交内容 |
| 隔离性/不影响他机 | 容器限权（cap-drop / no-new-privileges / 无挂载 / bridge）+ 端口仅绑环回 | 通过，测完即删 |

---

## 二、71 项冒烟测试明细

测试脚本：`_smoke_http.py`（已被 .gitignore 排除，不入仓库；为一次性验证工具）。

### 1) 匿名 HTML 路由（16 项）— 全 200
`/` `/health` `/chat` `/classroom` `/learn` `/student/` `/admin` `/admin/org` `/admin/ops` `/admin/console` `/admin/traces` `/teacher` `/teacher/class` `/teacher/tasks` `/teacher/console` `/analytics`

### 2) 静态资源（8 项）— 全 200
`static/ui/lumi.css`(11915B) `static/ui/icons.css`(6756B) `static/ui/admin.js`(10576B) `static/ui/teacher.js`(7265B) + 本地化 vendor（chart/katex/reveal/highlight）

### 3) 管理端真实登录 + 会话页面字节比对（13 项）— 全一致
- 登录：`must_change_password=True`，返回有效 token
- 页面与模板字节精确一致：`admin_dashboard.html`(12201) `admin_org.html`(13084) `admin_ops.html`(10942) `admin.html`(124306) `admin_traces.html`(11919) `teacher_dashboard.html`(15343) `teacher_class.html`(10185) `teacher_tasks.html`(15777) `teacher.html`(79512) `analytics_dashboard.html`(15421) `lumiterm.html`(97071) `classroom.html`(133605)
  → 证明服务的是正确模板，而非 302 兜底页。

### 4) 管理端 API（24 项，经 `X-Admin-Token`）— 全 200
me / overview / users / classes / agents / agents/health / models / port-models / port-settings / providers / api-keys / costs / tasks / traces / logs / activity-logs / mcp-servers / memories / weights / eval-reports / interrupts / analytics/overview / reasoning-logs/stats / dashboard/overview

### 5) 18081 REST API 与鉴权边界（10 项）
- `/api/status` `/health` `/api/models` `/api/port-config` `/api/providers` `/api/security/status` `/api/animation/health` `/student/` 全 200
- 鉴权隔离：`/api/admin/me`（18081，无 token）→ **401**
- 鉴权边界：匿名 `/api/analytics/overview` → **401**

### 冒烟汇总：`71/71 通过`

---

## 三、天虹主机 Docker 隔离容器验证（不影响主机其他项目）

在主机创建**只读隔离**的临时容器（`--cap-drop=ALL --security-opt=no-new-privileges --memory 2g --cpus 2 --pids-limit 256`，无挂载、bridge、端口仅绑 `127.0.0.1:28080/28081`）：

- 容器内 `pip` 仅装 **flask / requests / pyyaml / python-dotenv** 即可运行（无需 torch/manim 等重依赖）——最简化运行确认。
- 容器内自测 + 本机经 SSH 隧道指向 `127.0.0.1:28080/28081` 复测：**两轮均 71/71**，页面字节与本机模板一致。
- 主机侧：`<部署机内网IP>:28080` 局域网探测不可达（未暴露）；主机原 `18080/18081/11434` 全程 200 未受影响。
- 测试结束已 `docker rm -f` 并清理 `/tmp/ll-cfgtest`，主机容器/镜像/端口与测试前基线一致。

## 四、安全审计

- 跟踪文件扫描（`_audit_sensitive.py`）：仅有防火墙 CIDR、安全测试夹具、注释占位 API Key、测试口令，**无真实凭据**。
- 全工作树扫描：真实主机 IP、用户名、真实口令**只存在于 .gitignore 已排除路径**（`scripts/_archive/`、`models/`、`.env`、`docs/admin-token.txt`），绝不进入提交；唯一被跟踪的 `scripts/_deploy_ollama_remote.py` 只读环境变量。
- 对外仓库 `k3234/lumilearn` 为 **PUBLIC**，已按「仅干净配置包」范围提交，排除 `.bak`、诊断、主机专用散件。

## 五、客观局限（不掩盖）

1. **未做真实模型推理联调**：Ollama / 云端 provider 在测试容器内未连接，相关 API 仅验证「配置读取 / 鉴权」；真实推理需接入后才可评测。
2. `/api/port-config` 会按请求端口查端口-模型映射，端口未命中时回退默认模型（设计行为，非缺陷）。
3. 测评为**功能 / 回归类**，未包含压测与安全性渗透专项（性能基准见 `docs/performance-benchmark.md`）。

---

## 六、复现方式

```bash
# 干净环境实测
python -m framework.api.server --multi-port
# 另开终端（需已设管理员初始密码或首次登录后改密）
LUMILEARN_ADMIN_INITIAL_PASSWORD=你的强密码 python _smoke_http.py
```