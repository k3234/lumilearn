# LumiLearn 多 Agent 架构升级实施路线图

> 基于《全球 AI Agent 行业研究报告》结论制定
> 版本：v1.0 | 日期：2026-08-17

---

## 一、现状诊断

### 1.1 当前架构全景

LumiLearn 当前存在 **5 套并行但孤立的 Agent 系统**，缺乏统一编排：

```
┌─────────────────────────────────────────────────────────────────┐
│                        LumiLearn 当前架构                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐   │
│  │goai_agent.py │   │goai_multi_   │   │langgraph_engine  │   │
│  │单Agent 演示  │   │agent.py      │   │.py 12模型并行    │   │
│  │(关键词路由)  │   │(串行3-Agent) │   │(投票聚合)        │   │
│  └──────────────┘   └──────────────┘   └──────────────────┘   │
│       │                   │                    │               │
│       └───────────────────┴────────────────────┘               │
│                           │                                   │
│                    ┌──────────────┐   ┌──────────────────┐    │
│                    │framework/    │   │framework/        │    │
│                    │admin/agents.py│   │workflow_engine.py │    │
│                    │(Agent注册表) │   │(5步费曼工作流)    │    │
│                    └──────────────┘   └──────────────────┘    │
│                           │                                   │
│                    ┌──────────────┐                           │
│                    │framework/    │                           │
│                    │security/     │                           │
│                    │sandbox.py    │                           │
│                    │(AST代码沙箱) │                           │
│                    └──────────────┘                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 关键问题清单

| # | 问题 | 严重性 | 研究报告对应 |
|---|------|--------|-------------|
| P1 | 3套独立Agent系统未整合，存在重复实现和接口不一致 | 高 | §6.2 架构选择风险 |
| P2 | `goai_multi_agent.py` 为纯串行执行，延迟叠加 | 高 | §5.1 串行→并行趋势 |
| P3 | 缺少反馈回路（Verifier/Critic），无法区分"合理但错误"与"已确认" | 高 | §5.1 反馈回路模式 |
| P4 | 安全沙箱仅覆盖代码执行，未扩展到Agent API调用级 | 中 | §6.3 OWASP Top 10 |
| P5 | 无统一可观测性，无法追踪Agent调用链和成本 | 中 | §5.2 可观测性 |
| P6 | 无Router/Triage，所有任务都用同等级模型，成本失控 | 中 | §6.2 成本失控 |
| P7 | 缺少MCP协议支持，无法接入外部工具生态 | 低 | §5.1 MCP/A2A协议 |
| P8 | 单Agent vs 多Agent选择无依据，存在过度设计风险 | 低 | §4 单Agent vs 多Agent研究 |

### 1.3 技术债务评估

```
当前代码库 Agent 相关模块：

goai_agent.py         ~850行  单Agent串行流水线（关键词路由）
goai_multi_agent.py   ~516行  3-Agent串行链
langgraph_engine.py   ~750行  12模型并行（已有LangGraph基础）
framework/admin/agents.py ~311行 Agent注册表（BaseAgent抽象）
framework/workflow_engine.py ~521行 费曼5步工作流

总计约 3000+ 行 Agent 核心代码，分散在 5 个文件中
```

---

## 二、升级目标架构

### 2.1 目标架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LumiLearn 目标架构（Phase 2+）                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  用户请求                                                                │
│     │                                                                   │
│     ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Router / Triage Agent                         │   │
│  │  · 简单任务 → 单模型（低成本）                                    │   │
│  │  · 复杂任务 → 多Agent并行编排                                     │   │
│  │  · 顺序推理 → 单Agent（高精度）                                   │   │
│  └────────────────────────┬────────────────────────────────────────┘   │
│                           │                                             │
│              ┌────────────┴────────────┐                               │
│              ▼                         ▼                               │
│  ┌───────────────────┐      ┌─────────────────────────────┐           │
│  │ 简单路径           │      │ 复杂路径（LangGraph编排）     │           │
│  │ 单模型调用         │      │                             │           │
│  │ · 单Agent          │      │  ┌─────────────────────┐   │           │
│  │ · 快速响应         │      │  │ FeynmanTeacher     │   │           │
│  └───────────────────┘      │  │ (RAG + 五步教学)    │   │           │
│                             │  └──────────┬──────────┘   │           │
│                             │     ┌───────┴────────┐     │           │
│                             │     ▼                ▼     │           │
│                             │  ┌────────┐      ┌──────────┐ │           │
│                             │  │Score   │      │Coach     │ │           │
│                             │  │Agent   │      │Agent     │ │           │
│                             │  │(评分)  │      │(建议)    │ │           │
│                             │  └────┬───┘      └────┬─────┘ │           │
│                             │       │               │        │           │
│                             │       └───────┬───────┘        │           │
│                             │               ▼                │           │
│                             │  ┌─────────────────────┐       │           │
│                             │  │ Verifier Agent      │       │           │
│                             │  │ (反馈回路/质量检查)  │       │           │
│                             │  └──────────┬──────────┘       │           │
│                             │             │                  │           │
│                             │       ┌─────┴─────┐            │           │
│                             │       ▼           ▼            │           │
│                             │  ┌────────┐  ┌──────────┐     │           │
│                             │  │通过    │  │需改进     │     │           │
│                             │  └────┬───┘  └────┬─────┘     │           │
│                             │       │           │            │           │
│                             │       └─────┬─────┘            │           │
│                             │             ▼                  │           │
│                             │     最终报告输出                │           │
│                             └─────────────────────────────────┘           │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    支撑层                                          │   │
│  │  · MCP 工具集成  · 可观测性/日志  · 成本追踪  · 安全网关         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 架构设计原则

| 原则 | 说明 | 研究报告依据 |
|------|------|-------------|
| **统一编排** | 所有Agent通过LangGraph统一管理，消除3套独立系统 | §3.2 LangGraph企业采用率领先 |
| **按需并行** | 简单任务走单模型，复杂任务走并行+反馈回路 | §4 单Agent vs 多Agent研究 |
| **成本优先** | Router/Triage根据任务复杂度选择模型和路径 | §6.2 成本失控风险 |
| **安全内建** | 沙箱从代码级扩展到API调用级 | §6.3 OWASP Top 10 for Agentic |
| **可观测** | 每次Agent调用可追踪、可审计、可中断 | §6.1 EU AI Act Article 12/14 |
| **协议开放** | 支持MCP/A2A，接入外部工具生态 | §5.1 MCP/A2A协议标准化 |

---

## 三、分阶段实施计划

### Phase 1：架构统一与基础整合（第1-2周）

**目标**：消除重复实现，建立统一Agent编排基础

#### 1.1 创建统一Agent编排层

**新建文件**：`lumilearn/agent_core/orchestrator.py`

```
目标结构：
agent_core/
  ├── __init__.py
  ├── models.py          # AgentState, ToolCall, AgentResult 数据模型
  ├── orchestrator.py    # 统一编排器（LangGraph节点）
  ├── router.py          # Router/Triage Agent
  ├── safety.py          # Agent级安全控制
  └── observability.py   # 可观测性基座
```

**关键变更**：
- 将 `goai_multi_agent.py` 中的 3 个 Agent（FeynmanTeacher, ScoreAgent, CoachAgent）迁移到统一注册表
- 复用 `framework/admin/agents.py` 的 BaseAgent 抽象
- 建立 AgentState TypedDict 统一状态管理

#### 1.2 整合 LangGraph 引擎

**修改**：`langgraph_engine.py` → 拆分为：
- `agent_core/langgraph_engine.py`（核心编排逻辑）
- `agent_core/model_registry.py`（12模型注册表，提取自原文件）

**关键变更**：
- 保留12模型并行能力作为"复杂任务模式"的底层基础设施
- 将投票聚合逻辑抽象为可复用的 `vote_aggregate()` 工具函数
- 为每个模型节点添加调用日志和成本追踪

#### 1.3 统一 Agent 注册表

**修改**：`framework/admin/agents.py`

- 在 AgentRegistry 中新增 `agent_core` 模块的 Agent 注册
- 确保 FeynmanAgent, DetectionAgent, AdaptiveAgent, ChatAgent 与新的多Agent系统共存
- 添加 Agent 生命周期钩子（start/stop/health_check）

#### Phase 1 交付物

| 交付物 | 文件路径 | 验收标准 |
|--------|---------|---------|
| 统一AgentState模型 | `agent_core/models.py` | TypedDict 定义完整状态结构 |
| Router/Triage Agent | `agent_core/router.py` | 能根据任务复杂度选择路径 |
| 整合后的LangGraph引擎 | `agent_core/langgraph_engine.py` | 保留12模型并行能力 |
| 更新后的Agent注册表 | `framework/admin/agents.py` | 新旧Agent共存 |
| 单元测试 | `tests/test_agent_core.py` | 覆盖Router路由逻辑 |

---

### Phase 2：并行化与反馈回路（第3-4周）

**目标**：将串行3-Agent链升级为并行+反馈回路架构

#### 2.1 改造 MultiAgentOrchestrator

**修改**：`goai_multi_agent.py` → 迁移到 `agent_core/multi_agent.py`

**架构升级**：

```
旧架构（串行）：
  FeynmanTeacher → ScoreAgent → CoachAgent
  延迟 = t1 + t2 + t3

新架构（并行+反馈）：
  FeynmanTeacher ──┐
                   ├──→ Vote/merge ──→ ScoreAgent ──→ CoachAgent
  (并行备选模型) ──┘                │
                                   ▼
                            Verifier Agent
                          (反馈回路)
```

**关键变更**：
1. FeynmanTeacher 支持多模型并行调用（复用 langgraph_engine 的并行能力）
2. 添加 Verifier Agent：在 CoachAgent 输出前进行质量检查
3. 反馈回路：如果 Verifier 判定不合格，退回 FeynmanTeacher 重新生成
4. 最大反馈轮次限制（防止无限循环）

#### 2.2 实现 Verifier Agent

**新建文件**：`agent_core/verifier.py`

```python
class VerifierAgent:
    """
    质量验证 Agent — 反馈回路核心
    
    职责：
    1. 检查教学内容的准确性（与RAG知识库对比）
    2. 检查评分的合理性（维度一致性）
    3. 检查建议的可行性（与学习路径匹配）
    
    输出：
    - pass: 通过验证
    - fail + reason: 需要重新生成
    - confidence: 置信度评分
    """
```

**关键设计**：
- Verifier 使用与 FeynmanTeacher 相同的模型（保持一致性）
- 验证失败时返回具体原因，而非简单拒绝
- 置信度 < 阈值时自动触发重试

#### 2.3 LangGraph 图定义

**新建文件**：`agent_core/graph.py`

```python
# LangGraph 节点定义
from langgraph.graph import StateGraph, END

# 节点函数
def router_node(state: AgentState) -> str:
    """Router: 简单→单模型，复杂→多Agent"""
    
def feynman_node(state: AgentState) -> AgentState:
    """FeynmanTeacher: 五步教学"""
    
def score_node(state: AgentState) -> AgentState:
    """ScoreAgent: 五维评分"""
    
def coach_node(state: AgentState) -> AgentState:
    """CoachAgent: 学习建议"""
    
def verifier_node(state: AgentState) -> AgentState:
    """Verifier: 质量验证 + 反馈回路"""

# 图构建
graph = StateGraph(AgentState)
graph.add_node("router", router_node)
graph.add_node("feynman", feynman_node)
graph.add_node("score", score_node)
graph.add_node("coach", coach_node)
graph.add_node("verifier", verifier_node)

# 条件边（反馈回路）
graph.add_conditional_edges(
    "verifier",
    lambda state: "end" if state["verified"] else "feynman",
    {"end": END, "feynman": "feynman"}
)
```

#### Phase 2 交付物

| 交付物 | 文件路径 | 验收标准 |
|--------|---------|---------|
| 并行化MultiAgent编排 | `agent_core/multi_agent.py` | 延迟降低≥40%（对比串行） |
| Verifier Agent | `agent_core/verifier.py` | 能识别明显错误并触发重试 |
| LangGraph 图定义 | `agent_core/graph.py` | 支持条件边和反馈回路 |
| 集成测试 | `tests/test_multi_agent_parallel.py` | 端到端测试通过 |

---

### Phase 3：生产级加固（第5-6周）

**目标**：解决安全、可观测性、合规性三大生产级问题

#### 3.1 扩展安全沙箱到 Agent API 调用级

**修改**：`framework/security/sandbox.py` + 新建 `agent_core/safety.py`

```
安全风险升级路径：

Phase 0（当前）：
  代码沙箱 → AST验证 → 禁止危险模块

Phase 3（目标）：
  代码沙箱 → Agent API调用沙箱 → 结果验证沙箱
      │               │                  │
   AST验证         调用频率限制          输出过滤
   模块黑名单      预算控制             敏感信息检测
   执行超时        模型白名单           幻觉检测
```

**关键变更**：
1. `agent_core/safety.py`：Agent API调用安全控制
   - 调用频率限制（per-agent, per-user）
   - 预算控制（单次请求最大token数）
   - 模型白名单（禁止未授权的模型调用）
2. 结果验证：输出内容过滤（敏感信息、幻觉检测）
3. 与现有 `sandbox.py` 协同：代码执行 + Agent调用双重防护

#### 3.2 可观测性基础设施

**新建文件**：`agent_core/observability.py`

```python
class AgentTelemetry:
    """Agent调用链追踪"""
    
    def record_call(self, ...):
        """记录每次Agent调用"""
        
    def trace_cost(self, ...):
        """追踪成本"""
        
    def measure_latency(self, ...):
        """测量延迟"""
        
    def audit_log(self, ...):
        """审计日志（EU AI Act Article 12合规）"""
```

**关键设计**：
- 每次Agent调用记录：timestamp, agent_id, input_tokens, output_tokens, cost, latency, model
- 支持 LangSmith 集成（可选）
- 审计日志满足 EU AI Act Article 12 全量日志要求
- 支持人工中断（human-in-the-loop）标记

#### 3.3 中断与人工监督机制

**修改**：`agent_core/orchestrator.py`

- 添加 `interrupt()` 方法：在关键节点支持人工干预
- 添加 `resume()` 方法：人工批准/修改后恢复执行
- 符合 EU AI Act Article 14 要求

#### Phase 3 交付物

| 交付物 | 文件路径 | 验收标准 |
|--------|---------|---------|
| Agent API安全控制 | `agent_core/safety.py` | 调用频率/预算/白名单控制 |
| 可观测性追踪 | `agent_core/observability.py` | 每次调用可追踪、可审计 |
| 人工中断机制 | `agent_core/orchestrator.py` | 支持interrupt/resume |
| 安全集成测试 | `tests/test_agent_safety.py` | 模拟OWASP Top 10攻击 |
| 合规检查清单 | `docs/compliance_checklist.md` | EU AI Act Article 9/12/14/15 |

---

### Phase 4：成本优化与生态集成（第7-8周）✅ 已完成（2026-08-17）

**目标**：实现智能路由降本，接入MCP工具生态

#### 4.1 Router/Triage 智能路由

**完善**：`agent_core/router.py`

```python
class RouterAgent:
    """
    任务复杂度评估 + 路径选择
    
    路由规则：
    - 简单任务（定义/概念解释）→ 单模型（低成本）
    - 中等任务（理解/应用）→ FeynmanTeacher单模型
    - 复杂任务（分析/评价/创造）→ 多Agent并行+反馈回路
    - 顺序推理任务 → 单Agent（Google研究：准确率高39-70%）
    """
```

**关键设计**：
- 基于任务关键词和用户历史判断复杂度
- 简单任务成本目标：< $0.01/次
- 复杂任务成本目标：< $0.10/次（并行优化后）
- 成本超支自动降级为单模型

#### 4.2 MCP 协议支持

**新建文件**：`agent_core/mcp_client.py`

```python
class MCPClient:
    """MCP（Model Context Protocol）客户端"""
    
    def list_tools(self):
        """列出可用工具"""
        
    def call_tool(self, tool_name, arguments):
        """调用工具"""
        
    def register_tool(self, tool_schema):
        """注册自定义工具"""
```

**关键设计**：
- 支持 MCP 1.0 协议
- 预置教育工具集（知识库检索、题目生成、图表渲染）
- 允许第三方工具通过MCP接入

#### 4.3 成本追踪与优化报告

**新建文件**：`agent_core/cost_tracker.py`

```python
class CostTracker:
    """
    成本追踪与优化
    
    指标：
    - 单次请求成本
    - 每日/每月成本趋势
    - 各Agent成本占比
    - 成本异常检测
    """
```

#### Phase 4 交付物

| 交付物 | 文件路径 | 验收标准 |
|--------|---------|---------|
| 智能路由Agent | `agent_core/router.py` | 简单任务成本降低≥60% |
| MCP客户端 | `agent_core/mcp_client.py` | 支持MCP 1.0协议 |
| 成本追踪 | `agent_core/cost_tracker.py` | 实时成本监控 + 异常告警 |
| 性能基准测试 | `tests/test_performance_benchmark.py` | 对比Phase 0基线 |

---

## 四、技术栈适配建议

### 4.1 现有代码迁移策略

| 现有文件 | 处理方式 | 说明 |
|---------|---------|------|
| `goai_agent.py` | **废弃** | 单Agent演示，功能已被Phase 1整合 |
| `goai_multi_agent.py` | **迁移** | 3-Agent逻辑迁移到 `agent_core/multi_agent.py` |
| `langgraph_engine.py` | **重构** | 拆分到 `agent_core/langgraph_engine.py` + `model_registry.py` |
| `framework/admin/agents.py` | **扩展** | 新增 `agent_core` 模块的Agent注册 |
| `framework/workflow_engine.py` | **保留** | 费曼5步工作流保持不变，作为上层业务逻辑 |
| `framework/security/sandbox.py` | **扩展** | 新增 `agent_core/safety.py` 补充API级安全 |

### 4.2 新增依赖

```txt
# agent_core/requirements.txt
langgraph>=0.2.0
langchain-core>=0.3.0
mcp>=1.0.0          # MCP协议支持
opentelemetry-api>=1.25.0  # 可观测性
opentelemetry-sdk>=1.25.0
```

### 4.3 兼容性保证

- 所有现有 API 端点保持兼容（`/goai/web`, `/goai/multi-agent`, `/goai/web/langgraph`）
- 新增统一端点 `/agent/v1/run` 作为未来主入口
- 旧端点通过 Router Agent 内部路由到新架构

---

## 五、团队学习路线

基于研究报告 §5.2 的 9 步学习路线图，结合 LumiLearn 实际情况：

### 5.1 团队学习映射

| 步骤 | 学习内容 | LumiLearn 对应实践 | 负责人 |
|------|---------|-------------------|--------|
| 1 | LLM基础 | 已有 FeynmanEngine 理解 | 全员 |
| 2 | RAG入门 | 已有 `knowledge_retrieval.py` | 全员 |
| 3 | 单Agent模式 | `goai_agent.py` 已有基础 | 后端 |
| 4 | 进阶工具使用 | `ToolCaller` 模块 | 后端 |
| 5 | 多Agent基础 | **Phase 1 实施过程** | 架构组 |
| 6 | LangGraph深入 | **Phase 1-2 实施过程** | 架构组 |
| 7 | 多Agent进阶 | **Phase 2 实施过程** | 架构组 |
| 8 | 生产部署 | **Phase 3 实施过程** | 运维组 |
| 9 | 架构优化 | **Phase 4 实施过程** | 架构组 |

### 5.2 学习资源推荐

1. **LangGraph 官方文档**：https://langchain.github.io/langgraph/
2. **Google 单Agent vs 多Agent 研究**：引用 [18] in research report
3. **OWASP Top 10 for Agentic Applications**：https://owasp.org/
4. **MCP 协议规范**：https://modelcontextprotocol.io/
5. **EU AI Act 合规指南**：引用 [21] in research report

---

## 六、风险评估与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| LangGraph 学习曲线陡峭 | 中 | 中 | Phase 1 预留 7-14 天学习期；使用 CrewAI 快速原型验证 |
| 并行化增加系统复杂度 | 高 | 中 | 保持向后兼容；分阶段迁移；充分测试 |
| 反馈回路导致延迟增加 | 中 | 低 | 设置最大轮次限制；Verifier 使用轻量模型 |
| MCP 生态成熟度不足 | 低 | 低 | 先实现核心功能；MCP 作为可选扩展 |
| 成本优化效果不及预期 | 中 | 中 | 建立成本基线；持续监控；预留降级路径 |

---

## 七、里程碑与验收标准

### 7.1 关键里程碑

```
Week 1-2:  [M1] 架构统一完成
           - agent_core 模块建立
           - Router/Triage 基本功能
           - 单元测试覆盖率 ≥ 80%

Week 3-4:  [M2] 并行化与反馈回路完成
           - Verifier Agent 上线
           - LangGraph 图定义完成
           - 端到端测试通过

Week 5-6:  [M3] 生产级加固完成
           - Agent API 安全控制上线
           - 可观测性追踪完成
           - 人工中断机制实现

Week 7-8:  [M4] 成本优化与生态集成完成
           - 智能路由上线
           - MCP 客户端可用
           - 性能基准测试通过
```

### 7.2 验收指标

| 指标 | Phase 0 基线 | Phase 2 目标 | Phase 4 目标 |
|------|-------------|-------------|-------------|
| 单次请求延迟（复杂任务） | 3-5s（串行） | ≤2s（并行） | ≤1.5s（优化后） |
| 单次请求成本（简单任务） | ~$0.05 | ~$0.03 | ≤$0.01 |
| 代码复用率 | 0%（5套独立系统） | ≥60% | ≥80% |
| 安全覆盖率 | 代码级沙箱 | +API调用级 | +结果验证级 |
| 可观测性 | 无 | 基础日志 | 全链路追踪 |
| 测试覆盖率 | ~60% | ≥80% | ≥90% |

---

## 八、附录

### A. 研究报告关键结论引用

- **串行→并行趋势**：§5.1 "多Agent并行架构替代串行"
- **反馈回路价值**：§5.1 "反馈回路模式是区分'合理但错误'与'已确认'的最高杠杆添加"
- **单Agent vs 多Agent**：§4 "顺序任务单Agent准确率高39-70%"
- **成本失控风险**：§6.2 "每任务10-20次LLM调用"
- **安全扩展需求**：§6.3 "sandbox.py需扩展到Agent API调用级安全控制"
- **信任悬崖**：§6.1 "95%试点失败，生产工程是关键"

### B. 代码结构对照

```
当前结构                          目标结构
─────────────────────────────────────────────────────
goai_agent.py          →        (废弃，功能整合)
goai_multi_agent.py    →        agent_core/multi_agent.py
langgraph_engine.py    →        agent_core/langgraph_engine.py
                           →        agent_core/model_registry.py
framework/admin/agents.py →     framework/admin/agents.py (扩展)
framework/workflow_engine.py →  framework/workflow_engine.py (保留)
framework/security/    →        framework/security/ + agent_core/safety.py
                                (新增)
```

### C. Git 分支策略

```
main
 ├── feature/phase1-unified-agent-core    (Week 1-2)
 │    └── feature/phase2-parallel-feedback (Week 3-4, 基于phase1)
 │         └── feature/phase3-production-hardening (Week 5-6)
 │              └── feature/phase4-cost-optimization (Week 7-8)
 └── release/v2.0.0                       (Phase 4 完成后)
```

---

*文档版本：v1.0 | 基于全球 AI Agent 行业研究报告（2026-08-17）*
*编制：LumiLearn 架构组 | 审核状态：待评审*
