# LumiLearn 竞赛版本（V2.5）开发规划

> **版本**：v2.5 竞赛版本
> **日期**：2026-08-21
> **目标**：在 V2 基础上补齐评测、稳定性、文档，完成 GOAI 复赛参赛版本定型
> **适用**：单人开发，3-6 个月迭代周期

---

## 一、当前能力盘点

### 1.1 已实现核心能力

| 能力模块 | 实现状态 | 代码位置 | 测试覆盖 |
|:---|:---:|:---|:---:|
| **自研 8M Transformer** | ✅ | `framework/model.py` | 需 torch |
| **Qwen2.5 LoRA 微调** | ✅ | `lumilearn-v2`（671 条真实教学问答） | - |
| **费曼五步教学引擎** | ✅ | `framework/engines/feynman_engine.py` | 29 tests |
| **多 Agent 协作系统** | ✅ 三 Agent 串行 | `goai_multi_agent.py` + `framework/admin/agents.py` | 26 tests |
| **知识流水线** | ✅ 新增 | `agent_core/knowledge_pipeline.py` | 6 tests |
| **RAG 知识库检索** | ✅ 关键词倒排索引 | `framework/services/knowledge_retrieval.py` | 18 tests |
| **自适应路由** | ✅ 任务类型路由 | `framework/core/router.py` | 4 tests |
| **双路校验** | ✅ 新增 | `agent_core/verifier.py` | 5 tests |
| **分层记忆** | ✅ 新增 | `framework/storage/layered_memory.py` | 4 tests |
| **错误降级** | ✅ 新增 | `framework/core/fallback.py` | 6 tests |
| **系统评测** | ✅ 新增 | `agent_core/observability.py` | 5 tests |
| **Lite 模式** | ✅ 新增 | `framework/lite_mode.py` | 7 tests |
| **存储兼容** | ✅ 新增 | `framework/storage/file_compat.py` | 7 tests |
| **安全网关** | ✅ | `framework/security/gateway.py` | 19 tests |
| **全端口服务** | ✅ 6 端口 | `framework/api/server.py` | 全量通过 |
| **一键部署** | ✅ | `deploy/bootstrap.{sh,bat,ps1}` | - |
| **安全审计** | ✅ 已完成 | git 历史清理 + 敏感信息脱敏 | - |

### 1.2 当前缺口（按优先级排序）

| 缺口 | 影响程度 | 修复难度 | 竞赛优先级 |
|:---|:---:|:---:|:---:|
| **多 Agent 串行 → 可升级为并行/反馈回路** | 🔴 高 | 高 | P0 |
| **Agent trace 可视化面板** | 🔴 高 | 中 | P0 |
| **RAG 检索仅关键词，无语义理解** | 🟡 中 | 中 | P1 |
| **评测模块薄弱**（缺少自动化评测集与报表） | 🟡 中 | 中 | P0 |
| **Prompt 质量可进一步优化** | 🟡 中 | 低 | P1 |
| **输出引用来源标注缺失** | 🟡 中 | 低 | P1 |
| **CI/CD 流水线缺失** | 🟡 中 | 低 | P1 |
| **多轮对话上下文管理待增强** | 🟢 低 | 低 | P2 |
| **自我批判/self-critique 机制** | 🟢 低 | 中 | P2 |

---

## 二、V2.5 开发任务规划

### Phase 1：Agent 系统升级（P0，最高优先级）

**目标**：从"串行三 Agent"升级为"可反馈、可降级、可追踪"的多 Agent 协作系统

```
当前：用户输入 → FeynmanTeacher → ScoreAgent → CoachAgent → 聚合报告
目标：用户输入 → Orchestrator → FeynmanTeacher → Self-Critique → ScoreAgent → CoachAgent
                          ↑                                        ↓
                    动态路由（可选）                       质量不达标触发重试（最多2次）
```

| 任务 | 文件 | 说明 | 优先级 |
|:---|:---|:---|:---:|
| 创建 Orchestrator Agent | `agent_core/orchestrator.py`（扩展） | 任务分发 + 动态路由 | P0 |
| 创建 Self-Critique Agent | `agent_core/self_critique.py` | 对输出质量评估，不达标触发重试 | P0 |
| 添加 Agent trace 记录 | `agent_core/observability.py`（扩展） | 记录每个 Agent 输入/输出/耗时/token | P0 |
| 升级多 Agent 流水线 | `goai_multi_agent.py` + `orchestrator.py` | 支持反馈回路 + 超时控制 + token 预算限制 | P0 |

**关键设计**：
- 反馈阈值：Self-Critique 评分 < 70 分时，触发 FeynmanTeacher 重试（最多 2 次）
- 超时控制：每个 Agent 独立超时，整体 Orchestrator 总超时 ≤ 180s
- Token 预算：每个 Agent 独立 token 预算，超出后降级输出
- Trace 记录：所有 Agent 交互写入 `agent_traces` 表，Admin 面板可查看

---

### Phase 2：RAG 知识库增强（P1）

**目标**：从"纯关键词匹配"升级到"关键词 + 同义词扩展 + 引用来源标注"

| 任务 | 文件 | 说明 | 优先级 |
|:---|:---|:---|:---:|
| 构建学科同义词词典 | `framework/services/synonym_dict.py` | 数学/物理/化学核心术语同义词 | P1 |
| 查询扩展 | `framework/services/knowledge_retrieval.py` | 自动添加同义词扩展查询 | P1 |
| 文档导入格式校验 | `framework/pipeline/knowledge_parser.py`（扩展） | 支持 Markdown/EPUB，过滤坏文档 | P1 |
| 输出引用来源标注 | `agent_core/orchestrator.py` | 生成内容标注来源片段 | P1 |
| 预留语义检索接口 | `knowledge_retrieval.py` | 占位方法 `search_semantic()` | P2 |

**关键设计**：
- 同义词词典：按学科组织，支持手动扩展
- 引用标注：每个生成内容附带来源文档名称 + 段落片段
- 段落权重：教材类文档优先级高于网络文档

---

### Phase 3：评测模块补强（P0，竞赛说服力核心）

**目标**：构建标准化学科测试集，自动化评测并输出可视化报表

| 任务 | 文件 | 说明 | 优先级 |
|:---|:---|:---|:---:|
| 构建标准化学科测试集 | `tests/test_evaluation_dataset.py` | 数学/物理/化学各 50 题标准题库 | P0 |
| 知识点召回率评测 | `agent_core/observability.py`（扩展） | 统计知识点覆盖度 | P0 |
| 幻觉频次统计 | `agent_core/fact_checker.py`（扩展） | 检测输出与知识库矛盾的内容 | P0 |
| 评测报表可视化 | `remote/templates/goai_dashboard.html`（扩展） | ECharts 图表展示评测结果 | P0 |
| 评测数据持久化 | `framework/database.py`（扩展） | 评测结果写入 `eval_reports` 表 | P0 |

**评测指标**：
- 知识点召回率（Recall@K）
- 习题正确率（Accuracy）
- 幻觉频次（Hallucination Rate）
- 检索命中率（Hit Rate）
- Agent 平均响应时间（Latency）

---

### Phase 4：UI 与工程健壮性（P1）

**目标**：优化用户体验，增强系统稳定性

| 任务 | 说明 | 优先级 |
|:---|:---|:---:|
| Lite/完整模式开关更清晰 | 启动参数 `--mode` 帮助信息完善 | P1 |
| 异常页面优化 | 统一的错误处理页面，友好提示 | P1 |
| 输入边界校验 | 各 API 接口参数校验增强 | P1 |
| Docker Compose 优化 | 配置文件与业务代码分离，密钥全走环境变量 | P1 |
| 安全声明三处呈现 | README、技术报告、演示页面均明确安全边界 | P1 |

---

### Phase 5：文档与开源交付（P1）

| 任务 | 说明 | 优先级 |
|:---|:---|:---:|
| 整理开发笔记与架构图 | `docs/ARCHITECTURE.md`、模块接口说明 | P1 |
| 区分自研模块/第三方依赖 | 清晰披露哪些是自研、哪些是开源基座 | P1 |
| 完善 issue 模板 | `.github/ISSUE_TEMPLATE/` | P2 |
| 贡献指南 | `CONTRIBUTING.md` | P2 |
| 演示视频精简版 | 90 秒精简版（现有 5 分钟版已够用） | P2 |

---

## 三、优先级总览

### P0（必须完成，影响竞赛评分核心维度）
1. Agent 反馈回路 + 降级输出
2. Agent trace 可视化面板
3. 自动化评测集 + 评测报表

### P1（强烈推荐，有明显加分）
4. RAG 同义词扩展 + 引用来源标注
5. UI 异常处理 + 安全声明
6. 文档完善 + 架构图

### P2（锦上添花，有时间再做）
7. 语义检索接口预留
8. 自我批判机制
9. CI/CD 流水线
10. 贡献指南 + issue 模板

---

## 四、技术约束

- **不做基座预训练**：继续基于 Qwen、DeepSeek 等开源基座做 LoRA 微调
- **纯 CPU 部署优先**：不引入 GPU 依赖，保持算力平权定位
- **零外部依赖原则**：RAG 检索不引入向量数据库，纯 Python 实现
- **安全边界**：所有密钥走环境变量，禁止明文硬编码；不做不受限代码执行沙盒

---

## 五、成功指标（V2.5 达成标准）

| 指标 | V2 当前值 | V2.5 目标值 |
|:---|:---:|:---:|
| Agent 数量 | 3（串行） | 5（含 Orchestrator + Self-Critique） |
| Agent 协作模式 | 单向串行 | 串行 + 反馈回路 |
| Trace 记录 | ❌ | ✅ 全部 Agent 交互可追溯 |
| 评测集规模 | ❌ | 150 题（数/物/化各 50） |
| 自动化评测 | ❌ | ✅ 一键运行，生成报表 |
| RAG 检索方式 | 纯关键词 | 关键词 + 同义词 |
| 引用来源标注 | ❌ | ✅ 输出附带来源片段 |
| 测试用例数 | 534 | 600+ |
| 安全声明 | README 一处 | README + 报告 + 演示页三处 |

---

## 六、与中长期规划的关系

| 阶段 | 时间 | 与本规划关系 |
|:---|:---|:---|
| **V2.5（本规划）** | 3-6 个月 | 竞赛版本，完成核心闭环 |
| **V3（中期）** | 6-12 个月 | Agent 内核解耦为 SDK，Skill 插件系统 |
| **V4（长期）** | 1-2 年 | 微服务拆分，多租户支持 |

**本次规划只聚焦 V2.5 竞赛版本**，V3/V4 相关任务（SDK 重构、MCP 插件、微服务）延后处理。
