# LumiLearn 项目开发情况总结

> 更新时间：2026-08-19（今日）
> 数据库：`lumilearn.db`（SQLite，38 张表，完整性 ok，0 FK 违规，新增 `agent_mcp_configs`）
> 语法编译：200+ .py 文件，100% 通过（`archive/`、`scripts/` 内历史调试脚本的 `SyntaxWarning` 不计入核心代码）

---

## 一、项目概览

LumiLearn 是一个面向学生的 AI 驱动学习平台，支持教师 Portal、学生 Portal、管理分析面板等多端。核心架构围绕 `agent_core/` 的多 Agent 编排引擎构建，已实现 EU AI Act Art.14 人工中断机制。

### 当前架构（已实现）

```
用户请求
    │
    ▼
┌─────────────────────────────────────────────┐
│  UnifiedOrchestrator.run()                  │
│  ├─ Router.route()         路由到合适节点    │
│  │    ├─ sensitive_topic → interrupt()     │  ← EU AI Act Art.14
│  │    └─ 继续路由                              │
│  ├─ _run_complex_parallel() 多模型并行生成   │
│  │    └─ quality=poor → interrupt("verifier")  ← P0-1 已补齐
│  ├─ _run_standard()        标准流程          │
│  ├─ ScoreAgent → CoachAgent → VerifierAgent │
│  │    └─ confidence<50 or content_anomaly   │
│  │           → interrupt("verifier")          ← P0-1 已有
│  ├─ FactCheckerAgent        事实二次核查      │  ← P0-2 新增
│  │    └─ 与 RAG 来源核对，矛盾 → interrupt  │
│  │       (fact_check_failed)                 │
│  ├─ KnowledgeCache.writeback()               │  ← 自积累闭环
│  └─ AgentWeightConfig.dynamic_update()       │  ← 权重自优化
└─────────────────────────────────────────────┘
         │
         ▼
   返回报告 / awaiting_review / 人工审批后放行
```

---

## 二、已完成交付（Phase 1–4 + 自积累闭环）

### Phase 1：多 Agent 并行生成框架 ✅

| 交付物 | 文件 |
|--------|------|
| FeynmanTeacher 多模型并行 + Vote | [multi_agent.py](file:///e:/学习LLM/lumilearn/agent_core/multi_agent.py) |
| ScoreAgent / CoachAgent / VerifierAgent | [multi_agent.py](file:///e:/学习LLM/lumilearn/agent_core/multi_agent.py) |
| Verifier 4 维加权检查（结构/内容/评分/建议） | [verifier.py](file:///e:/学习LLM/lumilearn/agent_core/verifier.py) |
| 反馈回路（feedback_loop） | [multi_agent.py](file:///e:/学习LLM/lumilearn/agent_core/multi_agent.py) |
| StateGraph（LangGraph 风格） | [multi_agent.py](file:///e:/学习LLM/lumilearn/agent_core/multi_agent.py) |
| 测试 | [test_multi_agent_parallel.py](file:///e:/学习LLM/lumilearn/tests/test_multi_agent_parallel.py)（15 tests）|

### Phase 2：Agent 治理框架（安全 + 成本 + 可观测） ✅

| 交付物 | 文件 | 测试 |
|--------|------|------|
| AgentSafetyGuard（预算/频率/模型白名单/输出校验） | [safety.py](file:///e:/学习LLM/lumilearn/agent_core/safety.py) | [test_agent_safety.py](file:///e:/学习LLM/lumilearn/tests/test_agent_safety.py)（18 tests）|
| AgentTelemetry（trace/cost/audit_log） | [observability.py](file:///e:/学习LLM/lumilearn/agent_core/observability.py) | 同上 |
| CostTracker（日限额/异常检测/优化报告） | [cost_tracker.py](file:///e:/学习LLM/lumilearn/agent_core/cost_tracker.py) | 同上 |
| 测试 | [test_agent_safety.py](file:///e:/学习LLM/lumilearn/tests/test_agent_safety.py) | |

### Phase 3：生产级加固 ✅

| 交付物 | 文件 | 测试 |
|--------|------|------|
| 安全沙箱（exec_sandbox） | [sandbox.py](file:///e:/学习LLM/lumilearn/agent_core/sandbox.py) | [test_security_sandbox.py](file:///e:/学习LLM/lumilearn/tests/test_security_sandbox.py)（14 tests）|
| 安全网关（RateLimiter + IPBlocklist） | [gateway.py](file:///e:/学习LLM/lumilearn/agent_core/gateway.py) | [test_security_gateway.py](file:///e:/学习LLM/lumilearn/tests/test_security_gateway.py)（8 tests）|
| 上传安全（校验 + 魔数检测） | [upload_security.py](file:///e:/学习LLM/lumilearn/agent_core/upload_security.py) | [test_upload_security.py](file:///e:/学习LLM/lumilearn/tests/test_upload_security.py)（12 tests）|
| 合规清单（EU AI Act Art.14） | [docs/compliance_checklist.md](file:///e:/学习LLM/lumilearn/docs/compliance_checklist.md) | — |

### Phase 4：成本优化 + MCP 协议接入 ✅

| 交付物 | 文件 | 测试 |
|--------|------|------|
| CostTracker 日趋势/Agent 占比/异常检测 | [cost_tracker.py](file:///e:/学习LLM/lumilearn/agent_core/cost_tracker.py) | [test_performance_benchmark.py](file:///e:/学习LLM/lumilearn/tests/test_performance_benchmark.py)（23 tests）|
| MCP 1.0 Client（stdio/HTTP 双传输） | [mcp_client.py](file:///e:/学习LLM/lumilearn/agent_core/mcp_client.py) | 同上 |
| BuiltinToolRegistry + MCPServer（本地） | [mcp_client.py](file:///e:/学习LLM/lumilearn/agent_core/mcp_client.py) | 同上 |
| route_with_budget() 成本感知路由 | [router.py](file:///e:/学习LLM/lumilearn/agent_core/router.py) | 同上 |

### 自积累闭环（Phase 5 并行期交付） ✅

| 交付物 | 文件 | 测试 |
|--------|------|------|
| LogRetentionManager（日志归档 + 保留期配置） | [log_retention.py](file:///e:/学习LLM/lumilearn/framework/log_retention.py) | [test_log_retention.py](file:///e:/学习LLM/lumilearn/tests/test_log_retention.py)（16 tests）|
| FactCheckerAgent（事实核查，与 RAG 来源核对） | [fact_checker.py](file:///e:/学习LLM/lumilearn/agent_core/fact_checker.py) | [test_agent_fact_checker.py](file:///e:/学习LLM/lumilearn/tests/test_agent_fact_checker.py)（13 tests）|
| Pipeline fact_check 阶段（矛盾→人工复核协同/降级放行） | [multi_agent.py](file:///e:/学习LLM/lumilearn/agent_core/multi_agent.py) | 同上 |
| 内置 Agent 注册（fact_checker） | [framework/admin/agents.py](file:///e:/学习LLM/lumilearn/framework/admin/agents.py) | [test_agent_core.py](file:///e:/学习LLM/lumilearn/tests/test_agent_core.py) |
| KnowledgeCache（写回/查询/复用） | [knowledge.py](file:///e:/学习LLM/lumilearn/agent_core/knowledge.py) | [test_agent_reuse_feedback.py](file:///e:/学习LLM/lumilearn/tests/test_agent_reuse_feedback.py)（10 tests）|
| 动态权重公式（success_rate × latency_factor） | [knowledge.py](file:///e:/学习LLM/lumilearn/agent_core/knowledge.py) | 同上 |
| pipeline 知识复用（context/direct 模式） | [multi_agent.py](file:///e:/学习LLM/lumilearn/agent_core/multi_agent.py) | 同上 |
| 权重自更新（feynman 成功率/verifier 失败惩罚） | [multi_agent.py](file:///e:/学习LLM/lumilearn/agent_core/multi_agent.py) | 同上 |
| Router 敏感主题 → interrupt → awaiting_review | [orchestrator.py](file:///e:/学习LLM/lumilearn/agent_core/orchestrator.py) | [test_agent_human_review.py](file:///e:/学习LLM/lumilearn/tests/test_agent_human_review.py)（10 tests）|
| Verifier 低置信度/内容异常 → interrupt | [orchestrator.py](file:///e:/学习LLM/lumilearn/agent_core/orchestrator.py) | 同上 |
| complex_parallel poor → interrupt（P0-1 扩展） | [orchestrator.py](file:///e:/学习LLM/lumilearn/agent_core/orchestrator.py) | 同上 |
| interrupt/resume 状态机 | [observability.py](file:///e:/学习LLM/lumilearn/agent_core/observability.py) | [test_agent_safety.py](file:///e:/学习LLM/lumilearn/tests/test_agent_safety.py) + [test_agent_reuse_feedback.py](file:///e:/学习LLM/lumilearn/tests/test_agent_reuse_feedback.py) |

---

## 三、测试统计

| 指标 | 数值 |
|------|------|
| 测试文件数 | 26 |
| 可运行用例数 | **452** |
| 通过 | **452** ✅ |
| 失败 | **0** |
| 跳过 | **0** |
| 排除（依赖缺失） | 2 文件：`test_model.py`（需 torch）、`test_tokenizer.py`（需 tokenizers）|
| 数据库表数 | 38 |
| 数据库完整性 | OK |
| FK 违规 | 0 |
| 语法编译 | 100%（核心 agent_core/、framework/、tests/ 全通过）|
| 全量耗时 | ~17 min |

> **说明**：`test_model.py` 和 `test_tokenizer.py` 因 `torch`/`tokenizers` 未安装而跳过，不影响核心功能。

---

## 四、P0 / P1 / P2 任务清单

### P0 — 生产完善（全部完成 ✅）

| # | 任务 | 状态 | 测试覆盖 | 说明 |
|---|------|------|----------|------|
| 1 | **人工中断全链路扩展** | ✅ 已完成 | 10 tests | Router 敏感主题 + Verifier 低置信度/内容异常 + complex_parallel poor 三处中断接线，interrupt/resume 状态机完整 |
| 2 | **事实核查 Agent** | ✅ 已完成 | 13 tests | `agent_core/fact_checker.py` FactCheckerAgent 对教学内容与 RAG 来源二次核对（数值矛盾/声明一致性/主题覆盖），已接入 Pipeline 与人工复核协同，注册为内置 Agent |
| 3 | **日志归档与保留策略** | ✅ 已完成 | 16 tests | `framework/log_retention.py` LogRetentionManager：三张日志表独立保留期/行数上限，超期/超量归档为 JSONL，agent_call_log FK 保护，`run_policy()` 一键执行 + `get_stats()` 存储监控 |

### P1 运营层（全部完成 ✅）

> P1-4 / P1-5 / P1-6 / P1-7 四项任务均已实现并通过全量回归 452 passed。

### P2 技术优化
| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| 8 | **模型推理依赖** | ✅ 已处理 | 已添加 `pytest.importorskip` 优雅跳过，全量测试 452 passed / 2 skipped |
| 9 | **单元测试覆盖率** | ⚠️ 持续中 | 核心路径覆盖良好，部分边界条件待补充 |
| 10 | **Redis 依赖（学习仪表盘）** | ✅ 已解决 | `test_learning_dashboard.py` 19 tests 全部通过（此前跳过项已恢复）|
| 11 | **集成测试** | ❌ 未实现 | 无端到端集成测试覆盖多 Agent 完整链路 |
| 12 | **分布式任务队列** | ❌ 未实现 | 当前为同步执行，高并发场景需引入队列 |

---

## 五、近期关键修复记录

| 时间 | 修复内容 |
|------|---------|
| 2026-08-19 | **P1-5 MCP 外部接入**：新建 `agent_core/mcp_external.py`（`ExternalMCPServerConfig`/`ExternalMCPRegistry` CRUD + HTTP/stdio 双传输 + 连接复用池 + 降级）；`database.py` 新增 `agent_mcp_configs` 表（38 张表）；admin API 5 个端点；admin.html MCP 面板；端到端验证通过 |
| 2026-08-19 | **P1-6 编排器接线**：`orchestrator.run()` 入口接线 `sanitize_payload()`，命中注入返回拦截响应并写审计日志；英文注入正则修复（贪婪可选组漏检 bug） |
| 2026-08-19 | **P1-4 管理面板落地**：新增 7 个 admin API 端点（interrupts/costs/weights）+ `observability.py` 新增 `get_all_interrupts()`；`admin.html` 新增 3 个面板（待审批队列/成本报告/权重配置），含审批操作与权重内联编辑 |
| 2026-08-19 | **P1-7 权重深度驱动路由**：`model_registry.py` 新增 `get_best_models_by_dynamic_weight()` / `get_best_model_by_dynamic_weight()`；`multi_agent.py` 的 FeynmanTeacher 并行路由已切换至动态权重排序 |
| 2026-08-18 | **P0-3 日志归档与保留策略**：新建 `framework/log_retention.py`（16 测试全过）、合规清单 12.6/缺口/矩阵更新 |
| 2026-08-18 | **P0-2 事实核查 Agent 收尾**：注册为内置 Agent（`fact_checker`）、补齐注册断言、更新合规清单 9.4/缺口/矩阵 |
| 2026-08-18 | **P0-1 补充 3 个 complex_parallel poor 路径端到端测试**，全量回归 415 passed |
| 2026-08-18 | 全量测试 452 passed（零失败），`test_learning_dashboard.py` Redis 问题已恢复 |
| 2026-08-18 | `set_budget()` 从全局修改改为 per-user 存储 |
| 2026-08-18 | `cost_tracker.py` Lock → RLock，解决 detect_anomalies/get_daily_trend 嵌套死锁 |
| 2026-08-18 | `mcp_client.py` `_HttpTransport` 补 `close()` 方法 |
| 2026-08-18 | `MCPServer` 支持 port=0 随机端口，修复重复实例化 |
| 2026-08-18 | `conftest.py` 测试环境 FK 修复：预注册内置 Agent |
| 2026-08-18 | `database.py save_knowledge` source_call_id 默认值 0→None（FK 约束修复）|
| 2026-08-18 | `agent_core/__init__.py` 补 `AgentSafetyGuard`/`AgentTelemetry` import，导出 62 符号 |

---

## 六、下一步建议（按优先级排序）

### 立即处理

1. **P2-8 模型依赖**：为 `test_model.py` 和 `test_tokenizer.py` 添加 `@pytest.mark.skip` 装饰器，消除预存 2 个失败（当前已通过 `--ignore` 规避，但应在测试文件中正确处理）

### P2 技术优化

6. **P2-11 集成测试**：端到端覆盖多 Agent 完整链路（Router → Feynman → Verifier → FactChecker → KnowledgeCache）
7. **P2-12 分布式任务队列**：高并发场景引入 Celery/RQ 队列

---

## 七、合规状态速览

> 全量任务清单见 [docs/TASKS.md](file:///e:/学习LLM/lumilearn/docs/TASKS.md)

| 条款 | 要求 | 状态 | 证据 |
|------|------|------|------|
| Art.9 风险管理 | 风险识别/缓解/监控/残余评估 | ✅ | `safety.py` + `fact_checker.py` |
| Art.12 日志记录 | 调用链追踪/持久化审计/保留策略 | ✅ | `observability.py` + `log_retention.py` |
| Art.14 人工监督 | 中断/审批/待审队列/留痕/追溯 | ✅ | `orchestrator.py` + `observability.py` |
| Art.15 准确性与鲁棒性 | 验证/反馈/沙箱/脱敏/降级 | ✅ | `verifier.py` + `sandbox.py` + `safety.py` |

> 全部 EU AI Act 高风险条款（Art.9/12/14/15）均已实现，无开放缺口。

---

## 八、近期变更记录（2026-08-19）

> 本快照文档生成于 2026-08-18，以下为本日增量变更。全量任务清单见 [docs/TASKS.md](file:///e:/学习LLM/lumilearn/docs/TASKS.md)。

| 时间 | 变更内容 |
|------|---------|
| 2026-08-19 | **P2-12 分布式任务队列**：新建 `agent_core/task_queue.py`（SQLite broker + 结果后端 + 线程工作池，无外部依赖，不引入 Celery/RQ/Redis）；`database.py` 新增 `task_queue` 表（39 张表）；优先级/延迟/重试指数退避/超时/取消/宕机恢复；默认注册 `unified_orchestrator` 任务；admin API 5 个端点 + admin.html 任务队列面板；15 tests |
| 2026-08-19 | **P2-11 集成测试**：新建 `tests/test_integration.py`（8 tests），端到端覆盖 Router → Feynman → Verifier → FactChecker → KnowledgeCache 完整链路（知识复用/反馈回路/注入拦截/人工中断/质量闸门） |
| 2026-08-19 | 全量测试 475 passed / 0 failed / 2 skipped（460 + 15 新增），数据库 39 张表 |
