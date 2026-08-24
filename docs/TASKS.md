# LumiLearn 全量开发任务清单

> 更新时间：2026-08-20
> 全量测试：475 passed / 0 failed / 2 skipped（torch/tokenizers 依赖缺失，importorskip 正确跳过）
> 数据库：39 张表，0 FK 违规

---

## P0 — 生产完善 ✅ 全部完成

| # | 任务 | 状态 | 测试 | 新增文件 |
|---|------|------|------|----------|
| 1 | **人工中断全链路**：Router 敏感主题 + Verifier 低置信度/内容异常 + complex_parallel poor 三处中断接线，interrupt/resume 状态机完整 | ✅ | 10 tests | `observability.py` 扩展 |
| 2 | **事实核查 Agent**：FactCheckerAgent 对教学内容与 RAG 来源二次核对（数值矛盾/声明一致性/主题覆盖），已接入 Pipeline 与人工复核协同，注册为内置 Agent | ✅ | 13 tests | `agent_core/fact_checker.py` |
| 3 | **日志归档与保留策略**：LogRetentionManager，三张日志表独立保留期/行数上限，超期/超量归档为 JSONL，agent_call_log FK 保护，`run_policy()` + `get_stats()` | ✅ | 16 tests | `framework/log_retention.py` |

---

## P1 — 运营层 ✅ 全部完成

| # | 任务 | 状态 | 测试 | 新增/修改文件 |
|---|------|------|------|---------------|
| 4 | **管理面板落地**：admin.html 新增待审批队列/成本报告/权重配置 3 个面板，含审批操作、Agent 占比条形图、权重内联编辑；admin API 7 个端点 | ✅ | 全量 475 passed | `framework/api/routes/admin.py`、`agent_core/observability.py`、`remote/templates/admin.html` |
| 5 | **MCP 外部接入**：`ExternalMCPServerConfig`/`ExternalMCPRegistry` CRUD + HTTP/stdio 双传输 + 连接复用池 + 降级；`agent_mcp_configs` 表 + `task_queue` 表（39 张表）；admin API 5 个端点 + admin.html MCP 面板 | ✅ | 6 tests | `agent_core/mcp_external.py`（新建）、`framework/database.py`、`framework/api/routes/admin.py`、`remote/templates/admin.html` |
| 6 | **提示注入加固**：`prompt_guard.py` 中英双语 20+ 条注入正则 + 角色边界声明 + 输入/输出双侧校验；`orchestrator.run()` 入口接线 `sanitize_payload()` | ✅ | 13 tests | `agent_core/prompt_guard.py`（新建）、`agent_core/orchestrator.py` |
| 7 | **权重深度驱动路由**：`get_best_models_by_dynamic_weight()` 综合分 = 静态×动态权重；FeynmanTeacher 并行路由切换至动态权重排序 | ✅ | 1 test（benchmark 追加） | `agent_core/model_registry.py` |

---

## P2 — 技术优化

| # | 任务 | 状态 | 说明 | 依赖 |
|---|------|------|------|------|
| 8 | **模型推理依赖处理** | ✅ 已处理 | `test_model.py`/`test_tokenizer.py` 使用 `pytest.importorskip` 模块级跳过（全量 2 skipped），无需 `--ignore` | — |
| 9 | **单元测试覆盖率** | ⚠️ 持续中 | 核心路径覆盖良好，部分边界条件待补充 | — |
| 10 | **Redis 依赖（学习仪表盘）** | ✅ 已解决 | `test_learning_dashboard.py` 19 tests 全部通过 | — |
| 11 | **集成测试** | ❌ 未实现 | 无端到端集成测试覆盖多 Agent 完整链路（Router → Feynman → Verifier → FactChecker → KnowledgeCache） | — |
| 12 | **分布式任务队列** | ❌ 未实现 | 当前为同步执行，高并发场景需引入 Celery/RQ 队列 | — |

---

## P3 — 规划中（待定义）

当前项目暂无 P3 任务。可选方向：

| 方向 | 说明 | 优先级建议 |
|------|------|-----------|
| 多租户隔离与配额管理 | 多用户/多 Agent 配额、数据隔离、RBAC 权限细化 | 高（商业化前提）|
| Agent 编排可视化 | DAG 编辑器，可视化 Agent 依赖与执行顺序 | 中 |
| 模型灰度发布与 A/B 测试 | 多模型版本灰度、性能对比、自动回滚 | 中 |
| 性能基准自动化 | CI 中自动运行性能基准，阈值告警 | 中 |
| Webhook 事件通知 | Agent 中断/审批完成/成本超限等事件推送到外部系统 | 低 |
| 多语言 i18n | 前端/错误消息/提示词多语言支持 | 低 |

---

## 历史修复记录

| 时间 | 修复内容 |
|------|---------|
| 2026-08-20 | **pytest 收集修复**：新增 `pytest.ini`（`testpaths=tests` + `norecursedirs`），避免 `scripts/_full_e2e_test.py` 等独立脚本被误收集导致 SystemExit（全量 475 passed / 2 skipped，19 分钟）；新增 faulthandler_timeout 防护 |
| 2026-08-20 | **仓库整理与隐私脱敏**：`git rm --cached` 根目录 6 个临时调试脚本 + `output/*.json` + `push_git.ps1`（本地 token 工具）；移除 7 个含远程主机用户名的历史 `_deploy_*`/`_check_remote*` 脚本；`.gitignore` 增加对应规则与 `output/`、`test_migration.py`；`docs/CHANGELOG_*.md` 中 `/home/kai/` 脱敏为 `/home/<user>/` |
| 2026-08-20 | **天虹实操缺陷修复**：`framework/api/routes/admin.py` `_task_to_api` 使用 `Dict` 注解但未导入（Python 3.14 延迟注解掩盖、3.10 启动即崩），已补 `from typing import Dict`；天虹主机导入与 28080-28082 独立实例验证通过 |
| 2026-08-19 | **P2-12 分布式任务队列**：新建 `agent_core/task_queue.py` + `task_queue` 表（39 张表）+ admin API 5 端点 + admin.html 任务面板（15 tests），全量 475 passed |
| 2026-08-19 | **P2-11 集成测试**：新建 `tests/test_integration.py`（8 tests），端到端覆盖 Router → Feynman → Verifier → FactChecker → KnowledgeCache 完整链路 |
| 2026-08-19 | **P1-5 MCP 外部接入**：新建 `agent_core/mcp_external.py` + `agent_mcp_configs` 表（38 张表）；admin API 5 个端点；admin.html MCP 面板；HTTP/stdio 双传输端到端验证通过 |
| 2026-08-19 | **P1-6 编排器接线**：`orchestrator.run()` 入口接线 `sanitize_payload()`；英文注入正则修复（贪婪可选组漏检 bug） |
| 2026-08-19 | **P1-4 管理面板落地**：7 个 admin API 端点 + `get_all_interrupts()`；3 个面板落地 |
| 2026-08-19 | **P1-7 权重深度驱动路由**：动态权重排序函数 + FeynmanTeacher 路由切换 |
| 2026-08-18 | **P0-3 日志归档与保留策略**：新建 `framework/log_retention.py`（16 tests） |
| 2026-08-18 | **P0-2 事实核查 Agent 收尾**：注册为内置 Agent，补齐注册断言 |
| 2026-08-18 | **P0-1 补充 3 个 complex_parallel poor 路径端到端测试** |
| 2026-08-18 | `set_budget()` 从全局修改改为 per-user 存储 |
| 2026-08-18 | `cost_tracker.py` Lock → RLock，解决嵌套死锁 |
| 2026-08-18 | `mcp_client.py` `_HttpTransport` 补 `close()` 方法 |
| 2026-08-18 | `MCPServer` 支持 port=0 随机端口，修复重复实例化 |
| 2026-08-18 | `conftest.py` 测试环境 FK 修复：预注册内置 Agent |
| 2026-08-18 | `database.py save_knowledge` source_call_id 默认值 0→None（FK 约束修复）|
| 2026-08-18 | `agent_core/__init__.py` 补 `AgentSafetyGuard`/`AgentTelemetry` import，导出 62 符号 |

---

## 下一步行动建议

### 立即处理
- [x] **P2-8**：`test_model.py`/`test_tokenizer.py` 已用 `pytest.importorskip` 模块级跳过（无 torch/tokenizers 时整模块跳过，全量 2 skipped），无需 `--ignore` 规避

### P2 收尾
- [ ] **P2-9 单元测试覆盖率**：核心路径覆盖良好，部分边界条件持续补充

### P3 待定
- 根据业务优先级选择 P3 方向，定义具体任务后再启动
