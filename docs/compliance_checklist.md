# LumiLearn AI Agent 合规检查清单

> 对齐：EU AI Act（欧盟人工智能法案）— Article 9 / 12 / 14 / 15
> 更新日期：2026-08-19
>
> 说明：LumiLearn 面向高中教育辅导场景，本清单按 EU AI Act 高风险 AI 系统的
> 要求逐条核对当前实现，标注实施状态与证据位置。合规评估由本项目自查完成，
> 不构成法律意见。

---

## 一、Article 9 — 风险管理体系（Risk Management）

> 要求：建立并实施风险管理体系，识别、评估已知与可合理预见的风险，
> 采取适当缓解措施，并持续监控。

| # | 检查项 | 要求 | 状态 | 证据/实现位置 |
|---|--------|------|------|--------------|
| 9.1 | 风险识别 | 识别已知/可预见风险（幻觉、敏感信息泄露、错误占位符、调用滥用） | ✅ | `agent_core/safety.py` 敏感信息模式 + 幻觉警示词检测 |
| 9.2 | 风险缓解 | 对识别的风险采取技术缓解措施 | ✅ | `agent_core/safety.py`（频率限制/预算/白名单/输出脱敏）、`framework/security/sandbox.py`（代码沙箱） |
| 9.3 | 风险监控 | 运行中持续监控风险 | ✅ | `agent_core/observability.py`（Trace + 审计日志）、`AgentSafetyGuard.stats` 拒绝统计 |
| 9.4 | 残余风险评估 | 记录无法完全消除的残余风险 | ✅ | 启发式幻觉检测 + `agent_core/fact_checker.py` FactCheckerAgent（P0-2）对教学内容与 RAG 来源做二次事实核对（数值矛盾/声明一致性/主题覆盖），矛盾内容触发人工复核并阻断交付 |
| 9.5 | 测试 | 上线前进行风险相关测试 | ✅ | `tests/test_agent_safety.py`（18 tests）、`tests/test_prompt_guard.py`（13 tests）、`tests/test_mcp_external.py`（6 tests）、全量回归 452 tests |

---

## 二、Article 12 — 日志记录（Record-keeping）

> 要求：自动记录事件日志，覆盖系统运行全程，日志应可追溯、可审计，
> 至少保留：系统启用/禁用、关键决策、输入数据指纹、输出记录、人工审核。

| # | 检查项 | 要求 | 状态 | 证据/实现位置 |
|---|--------|------|------|--------------|
| 12.1 | 调用链追踪 | 每次用户请求可追溯完整 Agent 调用链 | ✅ | `agent_core/observability.py` `start_trace/record_call/end_trace`（Trace ID 贯穿所有 Agent 调用） |
| 12.2 | 调用留痕 | 记录 agent_id / 模型 / 耗时 / token / 成本 / 结果 | ✅ | `record_call()` 生成完整调用记录 |
| 12.3 | 持久化审计 | 审计日志持久化存储 | ✅ | `audit_log()` 落库 `system_logs` 表 |
| 12.4 | 数据库级日志 | Agent 调用明细入库 | ✅ | `framework/database.py` → `agent_call_log` 表（caller/target/topic/耗时/权重/调用链） |
| 12.5 | 日志检索 | 支持按 trace_id / agent_id / user_id 检索 | ✅ | `get_trace()` / `get_calls(agent_id)` / `get_cost_summary()` |
| 12.6 | 日志保留 | 日志长期保留与容量控制 | ✅ | `framework/log_retention.py` LogRetentionManager（P0-3）：system_logs / reasoning_logs / agent_call_log 独立保留期与行数上限，超期/超量日志自动归档为 JSONL 文件后清理，agent_call_log 受 FK 保护，`run_policy()` 一键执行 + `get_stats()` 存储监控 |

---

## 三、Article 14 — 人工监督（Human Oversight）

> 要求：高风险系统应由自然人有效监督，具备"人在回路"机制，
> 包括：理解系统能力与局限、监控运行、必要时人工干预（中断/拒绝/终止）。

| # | 检查项 | 要求 | 状态 | 证据/实现位置 |
|---|--------|------|------|--------------|
| 14.1 | 人工中断 | 关键节点可请求人工介入 | ✅ | `agent_core/orchestrator.py` `interrupt()` 已接线 `run()` 三处：① `node=router` 敏感主题检测 → `awaiting_review` 暂停；② `node=complex_parallel` quality=poor → 请求人工审核（P0-1 扩展）；③ `node=verifier` 生成内容验证未通过（低置信度/内容异常）→ 请求人工审核（P0-1 扩展）。均通过 `resume(approved)` + `_interrupt_approved` 放行 |
| 14.2 | 审批流程 | 支持 approved（放行）/ rejected（终止） | ✅ | `resume(decision, reviewer)` / `resolve_interrupt()` |
| 14.3 | 待审队列 | 管理员可查看待审批中断 | ✅ | `get_pending_interrupts()`（`_interrupts` 状态机 pending→approved/rejected）|
| 14.4 | 审核留痕 | 审批人、审批时间、决策全程记录 | ✅ | `interrupt` 记录 `reviewer/reviewed_at/status`，写审计日志 |
| 14.5 | 中断可追溯 | 中断标记关联调用链 | ✅ | trace 记录 `interrupted` 标记 + 原因；`stats["interrupted"]` 统计 |

---

## 四、Article 15 — 准确性、鲁棒性与网络安全

（Accuracy, Robustness, Cybersecurity）

> 要求：系统在其生命周期内达到可合理预期的准确性与鲁棒性；
> 对操纵/规避企图（对抗性攻击、投毒）具备弹性；抵御未授权第三方利用漏洞。

| # | 检查项 | 要求 | 状态 | 证据/实现位置 |
|---|--------|------|------|--------------|
| 15.1 | 准确性验证 | 输出质量有验证机制 | ✅ | `agent_core/verifier.py`（4 维加权置信度 + 反馈回路）|
| 15.2 | 质量反馈 | 不达标内容触发重新生成 | ✅ | `MultiAgentPipeline` 反馈回路（最多 3 轮）|
| 15.3 | 沙箱隔离 | 用户代码执行隔离，防逃逸 | ✅ | `framework/security/sandbox.py`（AST 验证 + 模块黑名单 + 执行超时）|
| 15.4 | 调用滥用防护 | 频率限制 / 预算 / 模型白名单 | ✅ | `AgentSafetyGuard.check_call()` 三层检查 |
| 15.5 | 输入净化 | 防提示注入 / 恶意输入 | ✅ | `agent_core/prompt_guard.py`（P1-6，2026-08-19）：中英双语注入模式检测（20+ 条正则）+ `ROLE_BOUNDARY_STATEMENT` 角色边界声明 + `validate_input_structure()` 输入长度/行数/注入三重校验 + `validate_model_output()` 输出侧系统提示词泄漏检测；系统提示词通过 `build_safe_system_prompt()` 幂等追加边界声明，`sanitize_payload()` 供编排器便捷调用 |
| 15.6 | 敏感信息防护 | 输出不泄露凭据/内网 IP/手机号/身份证号 | ✅ | `sensitive_patterns` 正则脱敏（API Key/令牌/私钥/IP/手机号/身份证号）|
| 15.7 | 错误降级 | 模型不可用时优雅降级而非崩溃 | ✅ | `MultiAgentPipeline` 多模型投票 + 无模型环境降级路径 |
| 15.8 | 网络安全 | 敏感端点鉴权 | ✅ | `@require_admin` 管理端点、`config.py` 密钥管理、CSRF 防护 |

---

## 五、合规缺口与行动项

| 缺口 | 影响 | 建议行动 | 优先级 |
|------|------|----------|--------|
| 无 | — | 其余 EU AI Act 高风险条款（Art.9/12/14/15）均已实现，无开放缺口 | — |

> 其余 EU AI Act 高风险条款（Art.9/12/14/15）均已实现，无开放缺口。

---

## 六、对照矩阵（EU AI Act 条款 → 实现文件）
|------|----------|----------|
| Art.9 风险管理 | 安全控制三层防护 + 事实核查二次校验 | `agent_core/safety.py`、`agent_core/fact_checker.py` |
| Art.12 日志记录 | Trace 全链路 + 审计落库 + 归档保留 | `agent_core/observability.py`、`framework/database.py`、`framework/log_retention.py` |
| Art.14 人工监督 | interrupt / resume 人审（三处中断节点）| `agent_core/orchestrator.py` |
| Art.15 准确性与鲁棒性 | Verifier 反馈回路 + 沙箱 + 脱敏 + 提示注入加固 + MCP 外部接入 | `agent_core/verifier.py`、`agent_core/multi_agent.py`、`framework/security/sandbox.py`、`agent_core/prompt_guard.py`、`agent_core/mcp_external.py` |

---

## 七、验证方式

```bash
# 安全与合规相关测试
python -m pytest tests/test_agent_safety.py -v
python -m pytest tests/test_agent_fact_checker.py -v
python -m pytest tests/test_log_retention.py -v
python -m pytest tests/test_agent_human_review.py -v
python -m pytest tests/test_prompt_guard.py -v
python -m pytest tests/test_mcp_external.py -v

# 全量回归（排除 torch/tokenizers 依赖缺失的测试文件）
python -m pytest tests/ --ignore=tests/test_model.py --ignore=tests/test_tokenizer.py -q
```

---

## 八、近期变更记录（2026-08-19）

| 变更 | 说明 |
|------|------|
| P1-5 MCP 外部接入 | 新建 `agent_core/mcp_external.py`、`agent_mcp_configs` 表（38 张表）；admin API 5 个端点；admin.html MCP 面板；HTTP/stdio 双传输端到端验证通过 |
| P1-6 提示注入接线 | `orchestrator.run()` 入口接线 `sanitize_payload()`，命中注入返回拦截响应；英文注入正则修复（贪婪可选组 bug） |
| P1-7 权重驱动路由 | `model_registry.py` 新增动态权重排序函数，FeynmanTeacher 并行路由已切换 |
| P1-4 管理面板 | 待审批队列/成本报告/权重配置 3 个面板落地 |
| 全量回归 | 452 passed（+21 新用例），0 failed |
