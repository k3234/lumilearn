# LumiLearn GOAI 参赛完整行动规划

> 基于 GOAI 分析报告制定，覆盖提交截止（8/16）至复赛（8/25–9/3）全流程。  
> 最后更新：2026-08-11

---

## 一、当前能力盘点（基于代码实际审查）

### 1.1 已实现的硬核能力

| 能力 | 实现位置 | 完成度 | 备注 |
|:---|:---|:---|:---|
| **本地优先架构** | `deploy/setup.py` + `config/providers.yaml` + `lumilearn_config.py` | ✅ 完整 | Ollama / vLLM / LM Studio / LocalAI / llama.cpp 全兼容，`local: true` 标记无需 API Key |
| **费曼五步教学** | `framework/engines/feynman_engine.py` + `goai_agent.py` | ✅ 完整 | 现象引入→认知冲突→思维模型→自主推导→费曼测试，支持交互式单步引导 |
| **Agent 框架** | `framework/admin/agents.py` | ✅ 完整 | BaseAgent 基类 + FeynmanAgent/OutputDetector/AdaptivePath/ChatAssistant，统一 start/stop/status/run 生命周期 |
| **多模型编排引擎** | `langgraph_engine.py`（仓库根） | ✅ 完整（待联调） | 12 模型并行→结果格式化→加权投票，`lumilearn_config.py` 已补充（本次修复） |
| **GOAI 教育智能体** | `goai_agent.py` | ✅ 完整 | TaskUnderstanding → FlowOrchestrator → ToolCaller → ResultDelivery 四模块，推理日志写库 |
| **自研模型** | `framework/model.py` + `notebooks/` | ✅ 完整 | 8M 参数 Transformer 从零训练（CPU），Qwen2.5 LoRA 微调（lumilearn-v2，671 条真实教学问答） |
| **多端口服务** | `framework/api/server.py` | ✅ 完整 | 18080 终端 / 18081 REST API / 18082 模型管理，端口独立配置 |
| **教师门户** | `teacher_portal.py` | ✅ 完整 | 班级/学生管理、学习监控、任务生成，`training_data` 表已导入 1152 条资源 |
| **OCR + 语音** | `framework/api/routes/ocr.py` + `speech.py` | ✅ 完整 | PaddleOCR + Whisper tiny + edge-tts |
| **安全系统** | `framework/api/middlewares/security.py` | ✅ 完整 | IP 白名单、限流、沙箱、CSP、API Key 认证 |
| **一键部署** | `deploy/bootstrap.{sh,bat,ps1}` | ✅ 完整 | Linux/macOS/Windows 三平台，clone→配置→运行全流程 |
| **推理日志** | `reasoning_logs` 表 | ✅ 完整 | GOAI / Feynman 推理过程写库，Admin/教师/API 三方查看 |

### 1.2 当前缺口（按 GOAI 报告）

| 缺口 | 影响 | 修复难度 |
|:---|:---|:---|
| **单 Agent（非多 Agent）** | 评审核心扣分项：无 Agent 间协作/编排 | 中 |
| **无真实 RAG 知识库** | 教学内容为模型生成，无检索增强 | 中 |
| **缺少多轮对话持久化** | 仅记录结果，无完整对话历史 | 低 |
| **无测试基础设施** | 无 pytest/单元测试，报告指出 | 低 |
| **部署文档不完整** | 缺少"从克隆到运行"完整说明（已修复 bootstrap） | 已修复 |
| **GoAI Web 前端内嵌** | 前端代码混在 `goai_web.py` 中，可维护性差 | 高（暂缓） |

---

## 二、提交前冲刺（D-5 → D-Day：8/11–8/16）

### 2.1 每日作战清单

#### **Day 1（8/11 今天）— 基础加固**

| 序号 | 任务 | 产出物 | 预计工时 |
|:---:|:---|:---|:---:|
| 1 | 完成 `lumilearn_config.py` 并验证 `langgraph_engine.py` 可导入运行 | 修复 commit | 30min |
| 2 | 修复 `goai_agent.py` 中所有 bare except → `except Exception` | 代码清理 | 20min |
| 3 | 添加 `pytest` 依赖，创建基础测试骨架（`tests/test_goai_agent.py`） | 测试文件 | 40min |
| 4 | 写一段多轮对话持久化逻辑（`chat_history` 表） | 数据库迁移脚本 | 30min |

#### **Day 2（8/12）— 多 Agent 原型**

| 序号 | 任务 | 产出物 | 预计工时 |
|:---:|:---|:---|:---:|
| 1 | 创建 `goai_multi_agent.py`：FeynmanAgent（教学）+ ScoreAgent（评分）+ CoachAgent（建议）三 Agent 串行编排 | 新文件 | 2h |
| 2 | 每个 Agent 独立 ToolCaller，可配置不同模型 | 同上 | 30min |
| 3 | 在 `goai_web.py` 中新增 `/api/multi-agent` 路由 | 路由 | 30min |
| 4 | 本地验证三 Agent 串联流程 | 截图/日志 | 20min |

#### **Day 3（8/13）— RAG 知识库原型**

| 序号 | 任务 | 产出物 | 预计工时 |
|:---:|:---|:---|:---:|
| 1 | 从 `training_data` 表提取知识点，构建简化版关键词检索索引（不引入向量数据库） | 索引模块 | 1.5h |
| 2 | FeynmanAgent 调用 RAG 检索相关知识点后再生成内容 | 集成修改 | 1h |
| 3 | 写 `docs/rag_design.md` 说明设计思路 | 文档 | 30min |

#### **Day 4（8/14）— 演示素材制作**

| 序号 | 任务 | 产出物 | 预计工时 |
|:---:|:---|:---|:---:|
| 1 | **录制 Demo 视频**（60–90 秒）：演示多轮对话 + 费曼五步 + 学习报告生成 | MP4 文件 | 1h |
| 2 | **撰写解决方案 PPT**（10–15 页）：痛点→方案→技术亮点→Agent 架构→演示截图 | PPT/MD | 2h |
| 3 | 编写 `docs/open_source_plan.md`（开源路线图 + 社区建设） | 文档 | 30min |
| 4 | 编写 `docs/privacy_compliance.md`（数据合规说明） | 文档 | 30min |

#### **Day 5（8/15）— 集成打磨**

| 序号 | 任务 | 产出物 | 预计工时 |
|:---:|:---|:---|:---:|
| 1 | 全链路联调：用户输入→多 Agent 处理→报告生成→学习记录保存 | 端到端验证 | 1.5h |
| 2 | 更新 `README.md`：补充多 Agent 说明、RAG 说明、Demo 视频链接 | 文档更新 | 30min |
| 3 | 重新打包提交 zip（如有新文件） | zip 更新 | 20min |
| 4 | 最终代码审查：确认无敏感信息 | 安全审查 | 20min |

#### **Day 6（8/16）— 提交日**

| 序号 | 任务 | 产出物 |
|:---:|:---|:---|
| 1 | 确认 zip 包内容完整 | 验证清单 |
| 2 | 完成 GOAI 平台提交 | 提交截图 |
| 3 | 备份所有成果到本地 | 备份确认 |

### 2.2 提交前 Checklist

- [ ] 多 Agent 原型代码已提交
- [ ] RAG 知识库原型已集成
- [ ] 测试骨架（pytest）已添加
- [ ] Demo 视频已录制（60–90 秒）
- [ ] 解决方案 PPT 已完成（10–15 页）
- [ ] `privacy_compliance.md` 已编写
- [ ] `open_source_plan.md` 已编写
- [ ] README.md 已更新（多 Agent / RAG / Demo）
- [ ] 提交 zip 已重新打包
- [ ] 无敏感信息（IP、API Key、密码）
- [ ] 提交截图已保存

---

## 三、复赛冲刺（8/25–9/3，9 天）

### 3.1 核心任务规划

#### **Phase 1：多 Agent 系统升级（Day 1–3，8/25–8/27）**

**目标**：从"单 Agent 流程编排"升级到"多 Agent 协作系统"

```
用户输入
    │
    ▼
┌──────────────┐
│  Orchestrator │  ← 新增：任务分发 + 结果聚合
│  (调度Agent)   │
└──────┬───────┘
       │
   ┌───┴───┬──────────┬──────────┐
   ▼       ▼          ▼          ▼
Feynman   Score    Knowledge   Path
Teacher   Agent    Retrieval  Adapter
(教学)    (评分)   (RAG检索)  (个性化)
```

**具体任务**：

| 任务 | 文件 | 说明 |
|:---|:---|:---|
| 创建 `orchestrator.py` | `framework/agents/orchestrator.py` | 任务分发 + 结果聚合 |
| 创建 `score_agent.py` | `framework/agents/score_agent.py` | 独立评分 Agent，五维评分 |
| 创建 `knowledge_agent.py` | `framework/agents/knowledge_agent.py` | RAG 检索 Agent |
| 创建 `path_agent.py` | `framework/agents/path_agent.py` | 学习路径推荐 Agent |
| 更新 `agents.py` | `framework/admin/agents.py` | 注册新 Agent |
| 更新 `goai_agent.py` | `goai_agent.py` | 支持多 Agent 模式 |

#### **Phase 2：RAG 知识库增强（Day 4–5，8/28–8/29）**

**目标**：建立可检索的教学知识库，让教学内容有据可查

| 任务 | 说明 |
|:---|:---|
| 构建知识点索引 | 从 `training_data` 表提取 → 关键词倒排索引 |
| 实现检索 API | `/api/knowledge/search?q=...` 返回相关知识点 |
| 集成到 FeynmanAgent | 生成内容前先检索，注入上下文 |
| 添加知识点管理 UI | Admin 面板可增删改知识点 |

#### **Phase 3：学习分析可视化（Day 6–7，8/30–8/31）**

**目标**：为教师端提供学习数据分析看板

| 任务 | 说明 |
|:---|:---|
| 掌握度趋势图 | ECharts 折线图，按时间展示学生掌握度变化 |
| 薄弱点热力图 | 学科×知识点矩阵，颜色深浅表示薄弱程度 |
| 学习时长统计 | 柱状图，按日/周统计 |
| 教师端仪表盘 | 新增 `/teacher/dashboard` 页面 |

#### **Phase 4：Skill 工程化（Day 8，9/1）**

**目标**：将核心能力封装为可复用 Skill

| 任务 | 说明 |
|:---|:---|
| 创建 `skills/feynman_teach.md` | 费曼五步法 Skill 定义 |
| 创建 `skills/learn_report.md` | 学习报告生成 Skill |
| 创建 `skills/knowledge_retrieve.md` | RAG 检索 Skill |
| 更新 `skills/INDEX.md` | Skill 索引 |

#### **Phase 5：CI/CD 与测试（Day 9，9/2–9/3）**

| 任务 | 说明 |
|:---|:---|
| 完善 `tests/` 目录 | 单元测试覆盖核心模块 |
| 添加 GitHub Actions | `.github/workflows/ci.yml` |
| 编写 `CONTRIBUTING.md` | 贡献指南 |
| 最终代码审查 | 确认无敏感信息 |

### 3.2 复赛 Demo 升级方向

| 维度 | 初赛 | 复赛目标 |
|:---|:---|:---|
| Agent 架构 | 单 Agent 四模块串行 | 多 Agent 并行协作（4 Agent + Orchestrator） |
| 知识来源 | 模型生成 | RAG 检索增强 + 模型生成 |
| 对话能力 | 单次问答 | 多轮对话持久化 + 上下文连贯 |
| 数据分析 | 无 | 学习分析可视化仪表盘 |
| 工程化 | 基础 | Skill 封装 + CI/CD + 测试覆盖 |
| 视频演示 | 无 | 60–90 秒完整流程演示 |

---

## 四、Demo 视频脚本（60–90 秒）

### 4.1 分镜脚本

| 时间 | 画面 | 旁白/字幕 |
|:---|:---|:---|
| 0–5s | 终端界面，输入"我想理解函数的单调性" | "LumiLearn — 在 CPU 上运行的 AI 教育智能体" |
| 5–15s | 任务理解 → 费曼五步流程生成 | "智能识别学习目标，自动生成费曼五步教学流程" |
| 15–35s | 五步内容逐步生成（每步 4 秒） | "现象引入 → 认知冲突 → 思维模型 → 自主推导 → 费曼测试" |
| 35–50s | 学习报告生成（掌握度 + 薄弱点 + 建议） | "生成完整学习报告：掌握度评估、薄弱点分析、下一步建议" |
| 50–65s | 多轮对话切换（同一个话题继续追问） | "支持多轮对话，上下文连贯，像真人老师一样引导" |
| 65–80s | 教师端仪表盘（掌握度趋势图） | "教师端实时掌握学习进度，精准定位薄弱点" |
| 80–90s | 全部在本地运行，无需云端 | "全部本地运行，保护隐私，老旧设备也能跑" |

### 4.2 录制要点

- 使用 `recordmydesktop`（Linux）或 OBS（Windows）录制
- 分辨率 1920×1080，帧率 30fps
- 提前准备 2–3 个测试话题（函数单调性、牛顿第二定律、化学平衡）
- 旁白可用剪映/必剪添加
- 最终压缩到 GOAI 平台要求的大小（通常 < 100MB）

---

## 五、解决方案 PPT 大纲（10–15 页）

| 页码 | 标题 | 内容要点 |
|:---:|:---|:---|
| 1 | 封面 | 项目名称、赛道、作者信息 |
| 2 | 教育痛点 | 资源不均、个性化缺失、算力门槛 |
| 3 | 我们的方案 | 本地优先 + 费曼教学法 + 多 Agent 协作 |
| 4 | 技术架构 | 架构图（Agent → Model → Database） |
| 5 | 核心创新 1 | 费曼五步教学法自动化编排 |
| 6 | 核心创新 2 | 多 Agent 协作系统（教学+评分+检索+路径） |
| 7 | 核心创新 3 | 本地优先，算力平权 |
| 8 | RAG 知识库 | 知识点检索增强，教学内容有据可查 |
| 9 | 学习分析 | 教师端仪表盘，掌握度可视化 |
| 10 | 模型能力 | 8M 自研模型 + Qwen2.5 LoRA 微调 |
| 11 | 演示截图 | 终端对话 / 教师端 / 学习报告 |
| 12 | Demo 视频 | 嵌入视频或二维码 |
| 13 | 开源计划 | 路线图 + 社区建设 |
| 14 | 总结 | 一句话价值主张 |

---

## 六、文档编写清单

### 6.1 必须编写（提交前）

- [ ] `docs/privacy_compliance.md` — 数据合规说明
  - 所有数据本地存储
  - 无用户隐私数据上传云端
  - 符合《个人信息保护法》教育类应用要求
- [ ] `docs/open_source_plan.md` — 开源路线图
  - Phase 1（8月）：核心功能开源
  - Phase 2（9月）：文档完善 + 贡献指南
  - Phase 3（10月）：Skill 市场 + 社区建设
- [ ] `docs/rag_design.md` — RAG 知识库设计说明

### 6.2 复赛补充

- [ ] `docs/multi_agent_design.md` — 多 Agent 系统架构设计
- [ ] `docs/learning_analytics.md` — 学习分析指标体系
- [ ] `CONTRIBUTING.md` — 贡献指南
- [ ] `docs/CHANGELOG复赛.md` — 复赛更新记录

---

## 七、技术债务处理策略

### 7.1 本次不处理（高风险，低优先级）

| 文件 | 原因 |
|:---|:---|
| `framework/database.py`（150KB） | 改动风险高，功能正常，复赛后再重构 |
| `goai_web.py` 内嵌前端 | 重构工作量大，当前功能可用 |
| `goai_agent.py` 超长重构 | 逻辑清晰，维持现状 |

### 7.2 本次处理（低风险，高回报）

| 任务 | 说明 | 状态 |
|:---|:---|:---|
| bare except → `except Exception` | 代码质量，易修复 | Day 1 完成 |
| 添加 pytest 测试骨架 | 工程化基础 | Day 1 完成 |
| 多轮对话持久化 | 评审关注点 | Day 1 完成 |

### 7.3 复赛处理

| 任务 | 说明 | 时间 |
|:---|:---|:---|
| database.py 重构 | 拆分模块 | 复赛 Phase 5 |
| goai_web.py 前端分离 | 独立 static/ 目录 | 复赛 Phase 5 |
| 完整测试覆盖 | pytest 覆盖核心逻辑 | 复赛 Phase 5 |

---

## 八、每日 Git 提交规范

```
# Day 1
git commit -m "fix: 补充 lumilearn_config.py，修复 langgraph_engine 导入；清理 bare except；添加 pytest 测试骨架；添加多轮对话持久化"

# Day 2
git commit -m "feat: 实现多 Agent 协作原型（FeynmanTeacher + ScoreAgent + CoachAgent）"

# Day 3
git commit -m "feat: 添加 RAG 知识库检索能力，FeynmanAgent 集成知识点检索"

# Day 4
git commit -m "docs: 添加 Demo 视频、解决方案 PPT、隐私合规说明、开源路线图"

# Day 5
git commit -m "refactor: 全链路联调，更新 README 多 Agent/RAG 说明，重新打包提交 zip"
```

---

## 九、风险评估与应对

| 风险 | 概率 | 影响 | 应对 |
|:---|:---:|:---:|:---|
| 多 Agent 开发时间不足 | 中 | 高 | 先实现串行三 Agent，并行可后续优化 |
| RAG 效果不理想 | 中 | 中 | 关键词检索兜底，不引入向量数据库 |
| Demo 视频质量不佳 | 低 | 中 | 提前演练 3 遍，使用剪映添加字幕 |
| 复赛时间冲突 | 低 | 高 | 关键代码每日提交，确保进度可回溯 |
| 评审对"学生开发"有偏见 | 中 | 中 | 强调技术深度（从零训练模型、Agent 架构、RAG） |

---

## 十、关键成功指标

| 指标 | 初赛目标 | 复赛目标 |
|:---|:---:|:---:|
| Agent 数量 | 1（单 Agent 四模块） | 4（多 Agent 协作） |
| 知识来源 | 模型生成 | RAG + 模型生成 |
| 对话持久化 | 无 | ✅ |
| 测试覆盖 | 无 | 核心模块 |
| Demo 视频 | 无 | ✅ 60–90 秒 |
| 文档完整度 | 基础 | 合规 + 开源计划 |
| 代码安全性 | 已清理 | 保持 |

---

*本规划基于 GOAI 分析报告 + 代码实际审查制定。所有时间估算为独立开发场景，如团队协作可适当压缩。*
