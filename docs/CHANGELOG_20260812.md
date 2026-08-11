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

**待提交**：goai_multi_agent.py、goai_web.py（重构）、两个模板、部署/验证脚本、本文档。

**遗留**：其他端口（teacher_portal / student_portal / framework 三端口）的前端分离重构，待后续积累经验后进行。
