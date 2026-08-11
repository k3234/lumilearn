# LumiLearn 更新记录（2026-08-12 · Day 2）

> 本文档记录 2026-08-12（GOAI 行动规划 Day 2）的开发内容。
> 说明：不包含测试脚本细节、本地验收过程与任何敏感凭据；服务器地址一律使用占位符。

---

## 一、多 Agent 协作系统（goai_multi_agent.py）⭐

**目标**：从"单 Agent 四模块串行"升级为"多 Agent 协作"，契合 GOAI 评审对 Agent 协作的核心要求。

### 架构

```
用户输入
    │
    ▼
┌──────────────────┐
│ FeynmanTeacher   │  教学 Agent — 费曼五步教学（复用 FeynmanEngine）
└───────┬──────────┘
        ▼
┌──────────────────┐
│ ScoreAgent       │  评分 Agent — 五维评估（复用 OutputDetector）
└───────┬──────────┘
        ▼
┌──────────────────┐
│ CoachAgent       │  建议 Agent — 学习路径推荐（复用 AdaptiveLearningEngine）
└───────┬──────────┘
        ▼
   聚合报告
```

### 关键设计

| 特性 | 说明 |
|---|---|
| **独立模型配置** | 每个 Agent 独立 `model_name`（`MULTI_AGENT_FEYNMAN_MODEL` / `MULTI_AGENT_SCORE_MODEL` 环境变量），优先读取端口模型配置 |
| **串行编排** | `MultiAgentOrchestrator.run(payload)` 依次执行三 Agent，上一步输出注入下一步输入 |
| **失败降级** | 单 Agent 异常不阻塞后续：记录 `agent_trace`（ok / skipped / failed），FeynmanTeacher 失败走模板兜底，无学生解释时评分阶段 skipped |
| **耗时追踪** | 每 Agent 单独计时 + `total_time` 汇总 |
| **难度映射** | 中文难度（初中/高中/大学）→ FeynmanEngine level（junior/senior/college） |
| **交互模式** | 传入 `dialogue` 对话历史时 FeynmanTeacher 自动切交互式单步引导（explain_step） |

### 聚合报告结构

```json
{
  "topic": "...", "subject": "...", "difficulty": "...", "user_id": 0,
  "teaching":  {"steps": [...], "full_content": "..."},
  "assessment":{"score": 90, "dimensions": {...}, "is_mastered": true, "feedback": "..."},
  "coaching":  {"mastery_level": "优秀", "suggestions": [...], "next_topics": [...]},
  "agent_trace": {"feynman": {"status": "ok", ...}, "score": {...}, "coach": {...}},
  "total_time": 47.53, "timestamp": "..."
}
```

---

## 二、GOAI Web 前端分离重构（goai_web.py）⭐

**目标**：解决"前端代码混在 goai_web.py 中"的可维护性问题（GOAI 报告指出的高优先级技术债）。

### 改动

| 项 | 改动前 | 改动后 |
|---|---|---|
| 学习智能体页 | `HTML_TEMPLATE` 常量（700 行内嵌在 .py） | 独立模板 `remote/templates/goai_learn.html` |
| 仪表盘首页 | `dashboard_html` 字符串拼接（100+ 行） | Jinja2 模板 `remote/templates/goai_dashboard.html` |
| 渲染方式 | `render_template_string` | `render_template`（模板化，易维护） |
| 模板目录 | 无 | `remote/templates`（本地）→ `tianhong/templates`（远程）双目录兼容 |
| 文件体积 | goai_web.py 1172 行 | goai_web.py 402 行（减 66%） |

### 新增：`POST /api/multi-agent` 路由

- 登录用户可调用三 Agent 协作完整流程
- 请求：`{topic, subject, difficulty, student_explanation?, weak_topics?, dialogue?}`
- 响应：`{success, data: 聚合报告}`
- 有评分时自动落库 `learning_reports`（Admin / 教师端可见）

---

## 三、修复：GOAI Web 旧进程占用端口导致服务无法更新

**现象**：部署后 `/api/multi-agent` 返回 404（路由未注册），仪表盘/学习页却正常。

**根因**：天虹服务器上存在一个 **8月11日手动 nohup 启动的旧 goai_web 进程**（不归 systemd 管理），持续占用 5000 端口。`systemctl --user restart lumilearn-goai` 启动的新代码进程绑定端口失败 → exit 1 → systemd auto-restart 死循环；实际请求全被旧进程处理。

**修复**：
1. `systemctl --user stop lumilearn-goai`（避免 auto-restart 干扰）
2. `pkill -9 -f goai_web.py` 清理全部旧进程（含 nohup 遗留）
3. `systemctl --user start lumilearn-goai` 重新拉起新代码

**经验**：手动 nohup 启动的进程与 systemd 服务并存时，端口冲突会让 systemd 服务"看起来没生效"。部署后须验证目标端口进程的 PID 是否为 systemd 托管实例（`systemctl --user status` 的 Main PID 应等于 `ss -tlnp` 的 PID）。

---

## 四、验证结果

### 本地（mock 模型，零网络）26 项全通过
- 各 Agent 单元：FeynmanTeacher 五步/交互/缺参、ScoreAgent 评分/缺解释、CoachAgent 建议+推荐
- 编排器：完整流程、5 步教学、评分、建议、状态追踪、耗时
- goai_web：仪表盘/学习页 200、multi-agent 401/200/评分跳过/报告落库

### 天虹真实服务（真实模型推理）
- `POST /api/multi-agent`（牛顿第二定律 + 学生解释）：HTTP 200，5 步教学（真实生成，质量良好）、评分 90（优秀）、五维评分、建议 1 条、推荐 4 个知识点、三 Agent 全 ok、耗时 47.5s ✅
- 无学生解释：评分阶段正确 `skipped` ✅
- 页面：仪表盘含「多 Agent」、学习页完整 JS ✅
- 报告落库 ✅

---

## 五、学习分析仪表盘前端分离重构（analytics_dashboard.py）⭐ 任务二

**目标**：延续 GOAI Web 前端分离经验，消除最后一个内嵌前端的端口服务（18090）。

### 改动

| 项 | 改动前 | 改动后 |
|---|---|---|
| 仪表盘页面 | `DASHBOARD_HTML` 常量（166 行内嵌在 .py） | 独立模板 `remote/templates/analytics_dashboard.html` |
| 渲染方式 | `render_template_string(DASHBOARD_HTML)` | `render_template("analytics_dashboard.html")` |
| 模板目录 | 无 | `remote/templates`（本地）→ `tianhong/templates`（远程）双目录兼容 |
| 文件体积 | analytics_dashboard.py 387 行 | 202 行（减 48%） |

### 验证结果（本地 15 项全通过）
- 模块无 `render_template_string` / 无 `DASHBOARD_HTML` 内嵌 ✅
- 首页 200，含 6 个数据区块（stats/trend/subjects/weak/concepts/recent）与全部 JS 加载逻辑 ✅
- 6 个 API 端点（overview/trend/subjects/weakpoints/concepts/recent）全部正常 ✅
- 与 git HEAD 旧版内容一致性 ✅

---

## 六、任务一 + 任务二 合并完整检测（本地）

### 本地全产品冒烟测试（114 项全通过）
覆盖 Admin（18080）25 项、Student@5010 36 项、Student@5000（含多 Agent 三阶段协作）15 项、Teacher@5001 18 项、前端页面可访问性 12 项、跨端口一致性 3 项、多轮对话 5 项、五步学习详细验证 10 项。

### Day2 多 Agent 专项（26 项全通过）
- Agent 单元：FeynmanTeacher 五步/交互/缺参、ScoreAgent 评分/缺解释、CoachAgent 建议+推荐
- 编排器：完整流程、5 步教学、评分、建议、状态追踪、耗时
- goai_web：仪表盘/学习页 200、multi-agent 401/200/评分跳过/报告落库

---

## 七、数据可视化 + 权限管理 + 数据合规导出（任务三）

**目标**：实现「数据可图形化完全查看管理（管理员/教师）」+「账号权限完全管理」+「数据在管理员管理下合规传输」。

### 7.1 数据可视化（纯 SVG，零 CDN）

| 端口 | 新增面板 | 图表内容 |
|---|---|---|
| **Admin 18080** | 📈 数据可视化 | 总量卡片、掌握度趋势折线图、学科对比条形图、薄弱点排行、知识点掌握度热力、模型推理统计、学生掌握度排行 |
| **Teacher 5001** | 📈 学习分析 | 同上（仅本班学生数据范围，`_visible_student_ids` 权限隔离） |

数据源 API（`framework/database.py` 新增 Z1.6 系列）：`get_analytics_overview/trend/subjects/weakpoints/concepts/reasoning/users`，支持按 `user_ids` 限定范围（教师本班）。

### 7.2 账号权限完全管理

| 能力 | 说明 |
|---|---|
| **管理员分级** | `super_admin`（创建/启停/改角色/删除管理员）+ `operator`（查看）双角色；`admins` 表管理 API：`GET/POST /api/admin/admins`、`POST .../toggle`、`POST .../role`、`DELETE .../<id>` |
| **用户权限** | `users` 表新增 `is_active`（登录拦截），`verify_user_login` 拒绝禁用账号；API：`POST /api/admin/users/<id>/active`（启停）、`POST .../role`（改角色） |
| **数据范围隔离** | 教师 analytics/导出仅限本班学生；非本班学生数据（报告/推理日志）自动隔离 |
| **防锁死保护** | 不能禁用/删除自己；超管账号不可删除（防止系统锁死） |

### 7.3 数据合规导出（管理员审批）

- 新表 `data_exports`：申请人/类型/格式/范围/状态(pending→approved/rejected)/审批人/文件路径/申请时间/审批时间
- **Admin**：直接导出（即时生成文件）+ 审批教师申请 + 下载（JSON/CSV），全部记录审计日志
- **Teacher**：发起导出申请（本班范围）→ 管理员审批 → 批准后可下载；仅本人可下载
- 导出类型：`reports / reasoning / answers / users / concepts`，格式 `json / csv`
- 导出文件写入 `export_data/` 目录

### 7.4 验证结果

| 测试套件 | 结果 |
|---|---|
| 任务三专项（analytics/权限/导出/前端） | **56/56 ✅** |
| 全产品回归（含既有 124 项） | **124/124 ✅** |
| pytest 核心（admin/auth/agent/管道） | **59/59 ✅** |

---

## 八、Day3：RAG 知识库原型 ⭐

**目标**：教学内容"有据可查"，从纯模型生成升级为"知识库检索增强 + 模型生成"。遵循行动规划约束：不引入向量数据库。

### 8.1 关键词倒排索引检索服务（新增）

`framework/services/knowledge_retrieval.py`

- 数据源：`training_data(status=published)` + `knowledge_nodes`
- 轻量中文分词：领域词典（180+ 学科术语）+ 字母数字段 + 中文 2-gram + 停用词过滤
- 简化 BM25 打分（tf + idf + 对数平滑），支持学科过滤，索引惰性构建 + 内存缓存 + `refresh()`
- 检索失败静默降级为空，绝不阻塞教学主流程

### 8.2 集成点

| 位置 | 改动 |
|---|---|
| `goai_multi_agent.py` | FeynmanTeacher.run() 生成前 `retriever.search(topic, top_k=3)` → 聚合报告 `teaching.rag_sources` |
| `feynman_engine.py` | `_build_feynman_prompt` / `explain` / `explain_step` 新增 `extra_context` 注入（默认空，向后兼容） |
| `goai_web.py` | 新增 `GET/POST /api/knowledge/search`、`GET /api/knowledge/status`（需登录） |
| `goai_learn.html` | 报告新增「知识库参考来源（RAG）」+「多 Agent 协作状态」区块 |

### 8.3 验证

- 本地 Day3 专项 18/18 ✅（索引/检索/上下文格式化/FeynmanEngine 注入/编排器/API）
- 天虹真实数据（1166 条 published）：勾股定理/牛顿/光合/共价键/单调性 5/5 命中 ✅

---

## 九、天虹服务器完整部署 + 测评（Day2/3 + 任务三 全量）

### 9.1 部署

- 14 个文件（代码 9 + 模板 5）上传至 `/home/kai/lumilearn`，覆盖前自动备份 `*.bak_时间戳`
- 合并 `port_settings`（补齐 terminal/teacher_portal/student_portal，保留远程其他配置）
- 重启全部服务：`lumilearn-api`(18080/81/82) + `lumilearn-goai`(5000)（systemd）+ `teacher_portal`(5001) + `analytics_dashboard`(18090) + `student_portal`(5010)（nohup）
- 7 端口全部 HTTP 200/302 ✅

### 9.2 在线测评结果

| 模块 | 结果 |
|---|---|
| RAG 知识库（1166 文档） | 5/5 检索命中 ✅ |
| 多 Agent 真实调用（牛顿第二定律 + 学生解释） | 56.9s，教学 5 步 + RAG 来源 2 + 评分 100 + 建议 + 三 Agent 全 ok ✅ |
| Admin 数据可视化（7 API） | 全过 ✅ |
| Admin 权限管理（admins/users/is_active） | 全过 ✅ |
| Admin 直接导出 + 下载 | 全过 ✅ |
| 教师本班数据隔离（analytics 5 项） | 全过 ✅ |
| 教师导出申请 → 管理员审批 → 下载 | 全过 ✅ |
| 前端新面板（多 Agent/数据可视化/学习分析） | 全过 ✅ |
| **合计** | **37/37 ✅** |

### 9.3 修复记录（测评发现并修复）

| 问题 | 根因 | 修复 |
|---|---|---|
| 多 Agent 180s 超时 | 模型发散输出无上限，单步 120s 超时 | `call_ollama` 支持 `num_predict`；费曼引擎调用默认限制 300 token（评分 400）→ 总耗时 284s → **56s** |
| ScoreAgent `'int' object has no attribute 'get'` | 模型返回的维度值是 int 而非 dict | `output_detector._ai_score` 维度归一化为 dict；`thirty_second_test` 校验 JSON 顶层为对象 |
| 「共价键」检索 0 条 | 知识库无共价键数据（非代码问题） | 天虹补充 1 条 published 教学资源 |

### 9.4 真实用户体验场景测试（天虹 CPU）

| 场景 | 结果 |
|---|---|
| 数学-勾股定理 | 5/5 步教学，评分 100，59.2s ✅ |
| 化学-共价键 | 5/5 步教学，评分 100，49.1s ✅ |

---

## 十、AI 使用声明 + 安全审查

- 新增仓库根目录 `AI-DECLARATION.md`：角色、AI 工具（Trae CN / Trae Work CN）、审核方式、责任声明、使用的技能/插件
- 已追踪脚本脱敏：`_remote_e2e_test.py` / `_check_remote_users.py` 中真实内网 IP 改为环境变量读取 + 占位符
- 文档：新增 `docs/rag_design.md`、`docs/privacy_compliance.md`、`docs/open_source_plan.md`；README 补充多 Agent/RAG/数据可视化章节

---

## 十一、classroom 互动教学修复 + 统一活动日志（用户测评反馈）⭐

**背景**：用户测评发现 18080/classroom 等学习展示端口互动教学不可用（CDN 库内网加载失败致前端 JS 出错）；18082 Admin「系统日志」只显示管理操作测试数据，看不到学生真实使用数据。

### 11.1 classroom 互动教学修复

| 问题 | 根因 | 修复 |
|---|---|---|
| 页面可开但互动失效 | KaTeX/Chart.js/highlight.js/reveal.js 走 jsdelivr CDN，内网环境加载失败 | 8 个 vendor 库下载至 `static/vendor/`，页面改本地引用 `/static/vendor/...`，保留 CDN 兜底 |
| 聊天慢 | 前端硬编码 `qwen2.5:7b`（CPU 极慢） | 移除 model 字段，后端按端口配置自动选 `lumilearn-v2` |
| 五步学习动画报 404 | 前端调 `/api/animation/generate/async`、`/progress/<id>` 路由不存在 | `animation.py` 补兼容路由（Manim 未部署返回降级）；前端失败自动切换通用画布动画，互动不中断 |

### 11.2 统一活动日志（解决「只显示测试数据」）

**根因**：Admin「系统日志」只读 `system_logs`（管理操作），而学生真实使用数据在 `reasoning_logs` / `learning_reports`，且课堂/终端普通聊天、五步学习此前不写库。

**修复**：
- 补齐埋点：`/api/feynman/explain`（五步学习）、`/api/chat` 非流式对话 → 写 `reasoning_logs`（mode=feynman/chat）
- 新增 `GET /api/admin/activity-logs`：合并 `system_logs` + `reasoning_logs` + `learning_reports` 按时间倒序，支持 `source=all/system/reasoning/report` 筛选
- Admin「系统日志」面板升级：来源徽标（⚙️系统/🧠推理/📚报告）+ 来源筛选按钮

### 11.3 验证

- 本地（临时 DB + test_client）**19/19 ✅**：合并日志/筛选/动画降级/静态资源 200/classroom 页面/原 /logs 兼容
- 天虹真实服务 **9/9 ✅**：admin 登录、activity-logs 展示真实数据（reasoning 75 + system 49 + report 20）、chat 埋点入库、feynman 5 步 + 埋点入库
- 部署：7 代码/模板 + 8 vendor 文件上传，重启 lumilearn-api，18080/81/82 全端口监听

---

## 十二、引导式学习（苏格拉底式交互）+ Admin 面板缓存修复（用户第二轮反馈）⭐

**背景**：用户反馈 18082 Admin「系统日志」仍看不到正确数据（实为浏览器缓存旧模板）；5010/learn.html 等学习端口仍是"老师提问-AI 学生回答"的自动播放式模拟课堂，学生只是旁观者。

### 12.1 Admin 面板缓存修复

- 根因：部署了新模板，但浏览器缓存旧版 admin.html，前端仍调用旧逻辑
- 修复：`server.py` 全局 `after_request` 对 `text/html` 响应加 `Cache-Control: no-store, no-cache, must-revalidate`，模板每次部署后刷新即生效
- 验证：`curl -sI /admin` 返回 `Cache-Control: no-store...` ✅

### 12.2 引导式学习（5010/learn.html）

**根因**：前端 `runAll()` 自动连续生成 5 步内容并打字机播放，学生只旁观，仅第 5 步需输入；与"学生自主推导"背道而驰。

**改造**（复用 FeynmanEngine.explain_step 交互引导能力）：
- 后端 `student_learn.py` 新增 `POST /api/learn/guide`：
  - 首次无 `answer` → 生成第 1 步引导提问
  - 之后带 `answer` → AI 先具体回应学生回答（肯定/修正），再生成下一步引导
  - 会话历史存 `chat_history`（user/assistant 交替）驱动步骤推进；RAG 检索注入；推理过程写 `reasoning_logs`
- 前端 `learn.html`：改为苏格拉底式交互——每一步展示引导提问 → 学生输入回答（含"答不上来请提示"按钮）→ AI 回应并推进下一步；第 5 步保留费曼 30 秒测试
- `api.js` 新增 `guideStep`；引导服务不可用时自动降级为原自动播放（`runLegacy`）

### 12.3 验证

- 本地（临时 DB + 模板兜底）**12/12 ✅**：登录/建会话/首次引导 step=1/回答推进 step=2→5/推理日志写库
- 天虹真实服务（真实模型 lumilearn-v2）**9/9 ✅**：admin 创建学生 → 5010 登录 → start → guide 首次（4s 生成引导提问）→ 回答后推进「认知冲突」→ 推理日志入库（Admin 可见）
- 部署：4 文件上传 + 重启 lumilearn-api、student_portal(5010)
- **重启经验**：nohup 后台启动必须 `< /dev/null > log 2>&1` 且 exec_command 后不 read stdout，否则 paramiko 阻塞

---

**待提交**：goai_multi_agent.py、goai_web.py、analytics_dashboard.py、admin.py、teacher_portal.py、database.py、feynman_engine.py、output_detector.py、lumilearn_shared.py、knowledge_retrieval.py（新增）、5 个前端模板、README、AI-DECLARATION.md、3 篇 docs、验证/部署/测评脚本、本文档。

**遗留**：演示视频与 PPT（用户指定另行完成）；`qwen2.5:7b` 已从费曼默认路径中规避（端口模型配置 lumilearn-v2，CPU 推理 6s/次）。
