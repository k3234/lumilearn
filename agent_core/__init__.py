# -*- coding: utf-8 -*-
"""
agent_core — LumiLearn Agent 核心模块

提供统一的 Agent 数据模型、路由、模型注册、编排引擎和权重管理。

核心能力：
- models.py:    AgentState, ToolCall, AgentResult, TaskProfile
- router.py:    RouterAgent — 按复杂度路由到单/多Agent
- model_registry.py: 8个模型跨4个提供商的统一注册表
- langgraph_engine.py: 5节点LangGraph式编排 + 加权投票
- orchestrator.py: UnifiedOrchestrator — Router → 单/3Agent/12模型
- weight_manager.py: Agent动态权重计算与管理
- knowledge_cache.py: 自积累知识库 — Agent产出可复用
- cross_caller.py: Agent跨调用 — 先查缓存，未命中则调Agent
- verifier.py:    VerifierAgent — 质量验证 + 反馈回路核心（Phase 2）
- multi_agent.py: MultiAgentPipeline — 并行化编排 + 反馈回路（Phase 2）
- graph.py:       StateGraph — 轻量LangGraph图 + 条件边反馈回路（Phase 2）
- cost_tracker.py: CostTracker — 成本追踪与优化报告（Phase 4）
- mcp_client.py:  MCPClient/MCPServer — MCP 1.0 协议与教育工具集（Phase 4）
- mcp_external.py: 外部 MCP 服务器接入 — 配置注册表与连接池（P1-5）

使用方式：
    from agent_core import get_unified_orchestrator, get_weight_manager, get_knowledge_cache
    from agent_core import get_verifier_agent, get_multi_agent_pipeline, get_feedback_graph
    from agent_core import get_cost_tracker, get_mcp_client, get_tool_registry
    from agent_core import ExternalMCPRegistry, get_external_mcp_registry
"""

from agent_core.models import AgentState, ToolCall, AgentResult, TaskProfile
from agent_core.router import RouterAgent, get_router_agent, route_task
from agent_core.model_registry import (
    ModelEntry, build_model_registry, ALL_MODELS, ALL_MODELS_DICT,
    get_model, get_models_by_provider, get_models_by_weight,
    get_best_models, get_model_summary,
)
from agent_core.langgraph_engine import (
    MultiFormatGenerator, WeightedVoter, OrchestrationEngine,
    run_orchestration, run_single_model,
)
from agent_core.orchestrator import (
    UnifiedOrchestrator, get_unified_orchestrator, run_agent,
)
from agent_core.weight_manager import WeightManager, get_weight_manager
from agent_core.knowledge_cache import KnowledgeCache, get_knowledge_cache
from agent_core.cross_caller import CrossCaller, get_cross_caller
from agent_core.verifier import (
    VerifierAgent, get_verifier_agent, verify_teaching,
    evaluate_human_review,
)
from agent_core.fact_checker import (
    FactCheckerAgent, get_fact_checker_agent, fact_check,
)
from agent_core.multi_agent import (
    FeynmanTeacher, ScoreAgent, CoachAgent, MultiAgentPipeline,
    MultiAgentOrchestrator, get_multi_agent_pipeline,
    get_multi_agent_orchestrator, run_multi_agent,
)
from agent_core.graph import (
    StateGraph, CompiledGraph, build_feedback_graph,
    get_feedback_graph, run_graph,
)
from agent_core.cost_tracker import (
    CostTracker, get_cost_tracker, reset_cost_tracker,
)
from agent_core.safety import (
    AgentSafetyGuard, get_safety_guard, reset_safety_guard,
    check_agent_call,
)
from agent_core.observability import (
    AgentTelemetry, get_telemetry, reset_telemetry,
)
from agent_core.mcp_client import (
    MCPClient, BuiltinToolRegistry, MCPServer,
    get_mcp_client, get_tool_registry, reset_mcp_client,
)
from agent_core.mcp_external import (
    ExternalMCPRegistry, ExternalMCPServerConfig,
    get_external_mcp_registry, reset_external_mcp_registry,
)

__all__ = [
    # models
    "AgentState", "ToolCall", "AgentResult", "TaskProfile",
    # router
    "RouterAgent", "get_router_agent", "route_task",
    # model_registry
    "ModelEntry", "build_model_registry", "ALL_MODELS", "ALL_MODELS_DICT",
    "get_model", "get_models_by_provider", "get_models_by_weight",
    "get_best_models", "get_model_summary",
    # langgraph_engine
    "MultiFormatGenerator", "WeightedVoter", "OrchestrationEngine",
    "run_orchestration", "run_single_model",
    # orchestrator
    "UnifiedOrchestrator", "get_unified_orchestrator", "run_agent",
    # weight_manager
    "WeightManager", "get_weight_manager",
    # knowledge_cache
    "KnowledgeCache", "get_knowledge_cache",
    # cross_caller
    "CrossCaller", "get_cross_caller",
    # verifier (Phase 2)
    "VerifierAgent", "get_verifier_agent", "verify_teaching",
    "evaluate_human_review",
    # fact_checker (P0-2)
    "FactCheckerAgent", "get_fact_checker_agent", "fact_check",
    # multi_agent (Phase 2)
    "FeynmanTeacher", "ScoreAgent", "CoachAgent", "MultiAgentPipeline",
    "MultiAgentOrchestrator", "get_multi_agent_pipeline",
    "get_multi_agent_orchestrator", "run_multi_agent",
    # graph (Phase 2)
    "StateGraph", "CompiledGraph", "build_feedback_graph",
    "get_feedback_graph", "run_graph",
    # safety (Phase 3)
    "AgentSafetyGuard", "get_safety_guard", "reset_safety_guard",
    "check_agent_call",
    # observability (Phase 3)
    "AgentTelemetry", "get_telemetry", "reset_telemetry",
    # cost_tracker (Phase 4)
    "CostTracker", "get_cost_tracker", "reset_cost_tracker",
    # mcp_client (Phase 4)
    "MCPClient", "BuiltinToolRegistry", "MCPServer",
    "get_mcp_client", "get_tool_registry", "reset_mcp_client",
    # mcp_external (P1-5)
    "ExternalMCPRegistry", "ExternalMCPServerConfig",
    "get_external_mcp_registry", "reset_external_mcp_registry",
]
