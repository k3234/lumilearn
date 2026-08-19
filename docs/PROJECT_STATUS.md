# LumiLearn 项目现状总结

> 更新日期：2026-08-17

---

## 一、项目概览

LumiLearn 是一款基于 AI Agent 的高中全科学习辅导平台，采用费曼 5 步教学法，支持多模型并行编排。

**技术栈**：Python / Flask / SQLite / Ollama / 云端 LLM（豆包/GLM/Kimi/MiniMax）

---

## 二、已完成功能

### Phase 1：架构统一（2026-08-17 完成）

| 交付物 | 状态 |
|--------|------|
| `agent_core/` 统一模块（models/router/registry/engine/orchestrator） | ✅ |
| Router Agent 任务分流（简单/标准/复杂并行） | ✅ |
| 8 模型跨 4 提供商统一注册表 | ✅ |
| 加权投票聚合引擎 | ✅ |
| 数据库迁移（agent_call_log/weight_config/knowledge_accumulation） | ✅ |
| Agent 权重管理系统 | ✅ |
| 自积累知识库 | ✅ |
| Agent 跨调用机制 | ✅ |

### Phase 2：并行化与反馈回路（2026-08-17 完成）

| 交付物 | 文件 | 状态 |
|--------|------|------|
| Verifier Agent（质量验证） | `agent_core/verifier.py` | ✅ |
| 并行化编排（多模型并行+反馈） | `agent_core/multi_agent.py` | ✅ |
| LangGraph 风格图定义（条件边） | `agent_core/graph.py` | ✅ |
| 编排器接入新流水线 | `agent_core/orchestrator.py` | ✅ |
| 端到端测试（26 用例） | `tests/test_multi_agent_parallel.py` | ✅ |

**架构升级：**

```
旧（串行）：FeynmanTeacher → ScoreAgent → CoachAgent    延迟 = t1+t2+t3
新（并行+反馈）：FeynmanTeacher(多模型并行) ─┐
                                          ├→ ScoreAgent → CoachAgent → Verifier
              (备选模型并行) ──────────────┘              │
                                                         └→ 未通过 → 重新生成（最多3轮）
```

### Phase 3：生产级加固（2026-08-17 完成）

| 交付物 | 文件 | 状态 |
|--------|------|------|
| Agent API 安全控制（频率/预算/白名单/输出过滤） | `agent_core/safety.py` | ✅ |
| 可观测性追踪（Trace ID/成本/审计/人工中断） | `agent_core/observability.py` | ✅ |
| 人工中断机制（interrupt/resume，EU AI Act Art.14） | `agent_core/orchestrator.py` | ✅ |
| 安全集成测试（26 用例，模拟 OWASP Agent Top 10） | `tests/test_agent_safety.py` | ✅ |
| 合规检查清单（EU AI Act Art.9/12/14/15） | `docs/compliance_checklist.md` | ✅ |

**Phase 3 关键修复：**
- `observability.py` 锁嵌套死锁（Lock→RLock，覆盖 get_stats/request_interrupt/resolve_interrupt）
- `get_cost_summary()` 统计口径（排除 audit 与 trace 汇总记录）
- 安全测试 token 估算断言修正

### Phase 4：成本优化与 MCP 协议接入（2026-08-17 完成）

| 交付物 | 文件 | 状态 |
|--------|------|------|
| 成本追踪与优化报告（趋势/占比/异常/建议） | `agent_core/cost_tracker.py` | ✅ |
| MCP 1.0 协议客户端（stdio/HTTP 双传输） | `agent_core/mcp_client.py` | ✅ |
| 内置教育工具集（知识检索/题目生成/图表渲染） | `agent_core/mcp_client.py` | ✅ |
| 本地 MCP Server（HTTP 传输，对外提供工具） | `agent_core/mcp_client.py` | ✅ |
| 成本感知路由（预估成本 + 超支自动降级） | `agent_core/router.py` | ✅ |
| 性能基准测试（成本目标/延迟 smoke/端到端） | `tests/test_performance_benchmark.py` | ✅ |

**Phase 4 关键修复：**
- `cost_tracker.py` 锁嵌套死锁（detect_anomalies → get_daily_trend，Lock→RLock）
- `mcp_client.py` `_HttpTransport` 补 close()（修复 client.close() AttributeError）
- `MCPServer` 支持 port=0 随机端口（测试稳定）
- 成本目标按 roadmap 美元口径校准（简单 < $0.01 / 复杂 < $0.10）

**成本估算基准（按最低价模型 qwen2.5:7b ≈ 0.001 元/千token）：**
| 路由 | token 预算 | 调用次数 | 预估成本 |
|------|-----------|---------|---------|
| simple | 1000 | 1 | 0.002 元 |
| standard | 4000 | 5 | 0.04 元 |
| complex_parallel | 8000 | 15 | 0.24 元 |

### 自积累闭环 + 人工监督接线（2026-08-18 完成）

| 能力 | 实现 | 状态 |
|------|------|------|
| Agent 数据复用（越用越聪明） | `MultiAgentPipeline.run()` 先查知识缓存 → 命中注入上下文（context）/ 直接复用（direct）→ 生成后写回 `knowledge_accumulation` | ✅ |
| 权重自优化 | Pipeline 每次调用后 `update_weight()`；Verifier 验证失败 → feynman 权重惩罚 | ✅ |
| 人工中断接线（合规 14.1） | `orchestrator.run()` Router 检测敏感主题 → `interrupt()` 返回 `awaiting_review` 暂停 → `resume(approved)` 后带 `_interrupt_approved` 放行 | ✅ |
| 测试 | `tests/test_agent_reuse_feedback.py`（10 用例） | ✅ |

**本轮结构优化与修复：**
- `tests/conftest.py` 预置内置 Agent（FK 数据完整性：agents 空表导致 agent_weight_config/knowledge_accumulation 外键失败）
- `save_knowledge` `source_call_id` 默认 0 → None（FK 引用不存在的 agent_call_log.id 报错）
- `cross_caller` 文本 call_id → 整数 FK 的类型不匹配修正
- `knowledge_cache.query_by_agent` 修复（此前忽略 agent_id，按产出 Agent 过滤）

### 安全加固（2026-08-17 完成）

| 修复项 | 状态 |
|--------|------|
| 沙箱 builtin 逃逸（getattr/super/input） | ✅ |
| AST 检查补全（exec/eval/open 直接调用） | ✅ |
| 沙箱无限循环超时（线程执行） | ✅ |
| 安全网关死锁（锁嵌套重构） | ✅ |
| config.py 安全函数（get_app_secret_key/register_csrf_guard） | ✅ |
| 敏感 API 端点 @require_admin | ✅ |

---

## 三、数据库结构（38 张表）

### Agent 核心表
- `agents` — Agent 注册表（6 个，含动态权重）
- `agent_call_log` — 调用日志
- `agent_weight_config` — 权重配置
- `knowledge_accumulation` — 自积累知识库

### 学习核心表
- `reasoning_logs` — 推理日志（34 条）
- `learning_reports` — 学习报告（2 条）
- `concept_understanding` — 概念理解追踪
- `knowledge_nodes` — 知识点树（13 个）
- `subjects` — 学科分类（12 个）

### 用户与权限
- `users` — 用户表（10 个）
- `admins` — 管理员表
- `api_keys` — API 密钥

### 教师功能
- `questions` — 题库
- `task_assignments` — 任务分配
- `submissions` — 作业提交

---

## 四、核心接口

| 模块 | 接口 | 说明 |
|------|------|------|
| 学习 | `POST /api/learn/start` | 发起学习会话 |
| 学习 | `POST /api/learn/step` | 费曼教学步骤 |
| 学习 | `POST /api/learn/guide` | 引导式交互 |
| 学习 | `POST /api/learn/feynman-test` | 费曼测试 |
| 学习 | `POST /api/learn/report` | 学习报告 |
| 教师 | `POST /api/teacher/correct` | AI 批改作业 |
| 教师 | `GET /api/teacher/questions` | 题库管理 |
| 安全 | `POST /api/security/sandbox/execute` | 代码沙箱 |
| 管理 | `GET /api/admin/agents` | Agent 管理 |
| 管理 | `GET /api/admin/weights` | 权重配置 |

---

## 五、测试状态

```
387 tests passed, 0 failed
  - test_agent_core.py:            66 tests ✅
  - test_multi_agent_parallel.py:  26 tests ✅ (Phase 2)
  - test_agent_safety.py:          26 tests ✅ (Phase 3)
  - test_performance_benchmark.py: 23 tests ✅ (Phase 4)
  - test_agent_reuse_feedback.py:  10 tests ✅ (自积累闭环+人工监督)
  - test_learning_dashboard.py:    19 tests ✅
  - test_security_gateway.py:      17 tests ✅
  - test_security_sandbox.py:      19 tests ✅
  - test_upload_security.py:       17 tests ✅
  - test_feynman_engine.py:        34 tests ✅
  - test_config.py:                12 tests ✅
  - test_model.py / test_tokenizer.py: 依赖缺失（torch/tokenizers，已忽略）
```

---

## 六、待完成（Roadmap）

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| Phase 1-4 | 架构统一 / 并行化 / 生产加固 / 成本优化+MCP | ✅ 全部完成 |
| 自积累闭环 | Agent 数据复用 + 权重自优化 + 人工监督接线 | ✅ 已完成 |
| 后续 | 事实核查 Agent、日志归档策略、提示注入加固 | 中 |

---

## 七、启动方式

```bash
# 主应用（含前端）
python goai_web.py          # http://localhost:5000

# 教师端
python teacher_portal.py    # http://localhost:5010

# 学生端
python student_portal.py    # http://localhost:5008

# 测试
python -m pytest tests/ -v
```
