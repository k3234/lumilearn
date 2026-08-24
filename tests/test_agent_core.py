# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — 单元测试

覆盖 Phase 1 交付物：
  - agent_core.models: AgentState, ToolCall, AgentResult, TaskProfile
  - agent_core.router: RouterAgent 路由逻辑
  - agent_core.model_registry: 模型注册表
  - agent_core.langgraph_engine: 编排引擎基础功能
  - agent_core.orchestrator: 统一编排器
  - framework.admin.agents: 新 Agent 注册
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.models import AgentState, ToolCall, AgentResult, TaskProfile
from agent_core.router import RouterAgent, route_task, get_router_agent
from agent_core.model_registry import (
    ModelEntry, build_model_registry, get_model_summary,
    get_model, get_models_by_provider, get_best_models,
    ALL_MODELS,
)
from agent_core.langgraph_engine import (
    MultiFormatGenerator, WeightedVoter, OrchestrationEngine,
    run_orchestration, run_single_model,
)
from agent_core.orchestrator import UnifiedOrchestrator, get_unified_orchestrator, run_agent
from framework.admin.agents import (
    RouterTaskAgent, UnifiedOrchestratorAgent,
    BUILTIN_AGENTS, AgentRegistry,
)


# ================================================================
# 一、models.py 测试
# ================================================================
class TestAgentState(unittest.TestCase):
    """AgentState TypedDict 测试"""

    def test_basic_state(self):
        state = AgentState(input_topic="函数", input_context="高中数学")
        self.assertEqual(state["input_topic"], "函数")
        self.assertEqual(state["input_context"], "高中数学")

    def test_empty_state(self):
        state = AgentState()
        self.assertEqual(state.get("input_topic", ""), "")

    def test_full_state(self):
        state = AgentState(
            input_topic="牛顿定律",
            input_context="物理",
            task_profile={"complexity": "standard"},
            routing_decision="standard",
            score=85,
            is_mastered=True,
            agent_trace={"router": {"status": "ok"}},
        )
        self.assertEqual(state["score"], 85)
        self.assertTrue(state["is_mastered"])
        self.assertIn("router", state["agent_trace"])


class TestToolCall(unittest.TestCase):
    """ToolCall 数据类测试"""

    def test_basic_call(self):
        call = ToolCall(tool_name="search", arguments={"query": "AI"})
        self.assertEqual(call.tool_name, "search")
        self.assertEqual(call.arguments["query"], "AI")
        self.assertEqual(call.result, "")
        self.assertEqual(call.elapsed, 0.0)

    def test_call_with_result(self):
        call = ToolCall(
            tool_name="calculate",
            arguments={"expr": "2+2"},
            result="4",
            elapsed=0.5,
        )
        d = call.to_dict()
        self.assertEqual(d["tool_name"], "calculate")
        self.assertEqual(d["result_len"], 1)
        self.assertEqual(d["elapsed"], 0.5)

    def test_call_with_error(self):
        call = ToolCall(
            tool_name="execute",
            arguments={"code": "bad"},
            error="SyntaxError",
        )
        d = call.to_dict()
        self.assertEqual(d["error"], "SyntaxError")


class TestAgentResult(unittest.TestCase):
    """AgentResult 数据类测试"""

    def test_success_result(self):
        result = AgentResult(
            success=True,
            agent_id="test_agent",
            data={"score": 90},
            elapsed=1.5,
            model_used="qwen2.5:7b",
            cost=0.003,
        )
        d = result.result_dict
        self.assertTrue(d["success"])
        self.assertEqual(d["score"], 90)
        self.assertEqual(d["cost"], 0.003)

    def test_failure_result(self):
        result = AgentResult.failure("test_agent", "model unavailable", 0.0)
        self.assertFalse(result.success)
        self.assertEqual(result.error, "model unavailable")

    def test_from_dict(self):
        d = {
            "success": True,
            "score": 85,
            "feedback": "很好",
            "elapsed": 2.0,
            "model_used": "deepseek-r1",
            "cost": 0.005,
        }
        result = AgentResult.from_dict("detector", d)
        self.assertTrue(result.success)
        self.assertEqual(result.data["score"], 85)
        self.assertEqual(result.model_used, "deepseek-r1")


class TestTaskProfile(unittest.TestCase):
    """TaskProfile 数据类测试"""

    def test_simple_profile(self):
        profile = TaskProfile(complexity="simple", reasoning_type="sequential")
        self.assertEqual(profile.route, "simple")
        d = profile.to_dict()
        self.assertEqual(d["complexity"], "simple")
        self.assertNotIn("route", d)  # to_dict 不包含 route

    def test_complex_parallel_profile(self):
        profile = TaskProfile(complexity="complex", reasoning_type="parallel")
        self.assertEqual(profile.route, "complex_parallel")

    def test_standard_profile(self):
        profile = TaskProfile(complexity="standard", reasoning_type="hybrid")
        self.assertEqual(profile.route, "standard")


# ================================================================
# 二、router.py 测试
# ================================================================
class TestRouterAgent(unittest.TestCase):
    """RouterAgent 路由逻辑测试"""

    def setUp(self):
        self.router = RouterAgent()

    def test_simple_task_detection(self):
        """简单任务：定义/概念类（需要足够多的简单关键词）"""
        profile = self.router.analyze("请解释函数的定义和含义")
        self.assertEqual(profile.complexity, "simple")
        self.assertEqual(profile.route, "simple")

    def test_complex_task_detection(self):
        """复杂任务：分析/推导类"""
        profile = self.router.analyze("请推导牛顿第二定律并分析其应用")
        self.assertEqual(profile.complexity, "complex")

    def test_parallel_task_detection(self):
        """并行任务：对比/比较类"""
        profile = self.router.analyze("比较凸透镜和凹透镜的异同及优劣")
        self.assertEqual(profile.reasoning_type, "parallel")

    def test_subject_detection_math(self):
        profile = self.router.analyze("函数的单调性如何判断")
        self.assertEqual(profile.subject, "数学")

    def test_subject_detection_physics(self):
        profile = self.router.analyze("牛顿第二定律的推导")
        self.assertEqual(profile.subject, "物理")

    def test_subject_detection_chemistry(self):
        profile = self.router.analyze("化学平衡的移动规律")
        self.assertEqual(profile.subject, "化学")

    def test_difficulty_detection(self):
        profile = self.router.analyze("初中数学中的勾股定理")
        # difficulty is used internally, not stored in TaskProfile
        self.assertEqual(profile.complexity, "standard")

        profile2 = self.router.analyze("高考数学压轴题")
        self.assertEqual(profile2.complexity, "standard")

        profile3 = self.router.analyze("大学微积分")
        self.assertEqual(profile3.complexity, "standard")

    def test_route_method(self):
        result = self.router.route("请解释导数的定义和含义")
        self.assertEqual(result["route"], "simple")
        self.assertEqual(result["model_suggestion"], "cheap_fast")
        self.assertEqual(result["budget"], 1000)

    def test_route_complex(self):
        result = self.router.route("请综合分析 climate change 的影响和应对措施")
        # "综合分析" → complexity=complex, reasoning_type=hybrid → route=standard
        self.assertEqual(result["route"], "standard")

    def test_should_use_multi_agent(self):
        self.assertTrue(self.router.should_use_multi_agent(
            "比较以下三种能源的异同"))
        self.assertFalse(self.router.should_use_multi_agent(
            "请解释光合作用的定义"))

    def test_empty_input(self):
        profile = self.router.analyze("")
        self.assertEqual(profile.topic, "")
        self.assertEqual(profile.confidence, 0.5)

    def test_keyword_extraction(self):
        profile = self.router.analyze("函数的单调性和奇偶性")
        self.assertIn("函数", profile.keywords)

    def test_topic_extraction(self):
        profile = self.router.analyze("请帮我学习一下函数的单调性")
        self.assertEqual(profile.topic, "函数的单调性")


class TestRouterSingleton(unittest.TestCase):
    """Router 单例测试"""

    def test_singleton(self):
        r1 = get_router_agent()
        r2 = get_router_agent()
        self.assertIs(r1, r2)
# ================================================================
# 三、model_registry.py 测试
# ================================================================
class TestModelRegistry(unittest.TestCase):
    """模型注册表测试"""

    def test_registry_built(self):
        self.assertGreater(len(ALL_MODELS), 0)

    def test_registry_count(self):
        """应该注册12个模型"""
        self.assertEqual(len(ALL_MODELS), 12)

    def test_provider_distribution(self):
        providers = set(m.provider for m in ALL_MODELS)
        self.assertIn("remote_ollama", providers)
        self.assertIn("cloud", providers)
        self.assertIn("solo", providers)

    def test_get_model_by_id(self):
        model = get_model(ALL_MODELS[0].id)
        self.assertIsNotNone(model)
        self.assertEqual(model.id, ALL_MODELS[0].id)

    def test_get_model_not_found(self):
        model = get_model("nonexistent_model")
        self.assertIsNone(model)

    def test_get_models_by_provider(self):
        cloud_models = get_models_by_provider("cloud")
        self.assertGreater(len(cloud_models), 0)
        for m in cloud_models:
            self.assertEqual(m.provider, "cloud")

    def test_get_best_models(self):
        best = get_best_models(3)
        self.assertEqual(len(best), 3)
        for m in best:
            self.assertGreaterEqual(m.weight, best[-1].weight)

    def test_get_model_summary(self):
        summary = get_model_summary()
        self.assertGreater(summary["total"], 0)
        self.assertIn("by_provider", summary)
        self.assertIn("models", summary)

    def test_registry_count(self):
        """注册表应包含多个模型"""
        self.assertGreater(len(ALL_MODELS), 0)
        self.assertEqual(len(ALL_MODELS), 8)

    def test_model_call_solo(self):
        solo_models = get_models_by_provider("solo")
        if solo_models:
            m = solo_models[0]
            result = m.call("请解释函数的概念")
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)


# ================================================================
# 四、langgraph_engine.py 测试
# ================================================================
class TestMultiFormatGenerator(unittest.TestCase):
    """多格式生成器测试"""

    def setUp(self):
        self.generator = MultiFormatGenerator()

    def test_generate_all_formats(self):
        raw = "函数是描述两个变量之间对应关系的数学概念。"
        formats = self.generator.generate_all_formats(raw, "函数", "test_model")
        self.assertIn("teaching_content", formats)
        self.assertIn("json_structured", formats)
        self.assertIn("flashcard", formats)
        self.assertIn("qa_pair", formats)
        self.assertIn("markdown_note", formats)

    def test_empty_response(self):
        formats = self.generator.generate_all_formats("", "topic", "model")
        for fmt in formats.values():
            self.assertEqual(fmt, "")

    def test_invalid_response(self):
        formats = self.generator.generate_all_formats("[error]", "topic", "model")
        for fmt in formats.values():
            self.assertEqual(fmt, "[error]")

    def test_json_format_valid(self):
        raw = "这是一个测试内容。"
        formats = self.generator.generate_all_formats(raw, "测试", "model")
        json_str = formats["json_structured"]
        parsed = __import__("json").loads(json_str)
        self.assertEqual(parsed["topic"], "测试")
        self.assertEqual(parsed["model"], "model")

    def test_teaching_format_has_header(self):
        raw = "函数定义：设A,B是非空的数集..."
        formats = self.generator.generate_all_formats(raw, "函数", "model")
        self.assertTrue(formats["teaching_content"].startswith("# 函数"))


class TestWeightedVoter(unittest.TestCase):
    """加权投票汇总器测试"""

    def setUp(self):
        self.voter = WeightedVoter()

    def test_aggregate_empty(self):
        result = self.voter.aggregate({}, {}, "test_topic")
        self.assertEqual(result["topic"], "test_topic")
        self.assertEqual(result["models_used"], 0)

    def test_aggregate_with_responses(self):
        responses = {
            "model1": {"raw": "好的教学内容", "entry": ALL_MODELS[0]},
            "model2": {"raw": "另一份内容", "entry": ALL_MODELS[1]},
        }
        formats = {
            "model1": {"teaching_content": "内容1", "json_structured": "{}"},
            "model2": {"teaching_content": "内容2", "json_structured": "{}"},
        }
        result = self.voter.aggregate(responses, formats, "测试主题")
        self.assertEqual(result["models_used"], 2)
        self.assertIn("teaching_content", result)
        self.assertIn("quality_report", result)

    def test_quality_assessment(self):
        responses = {
            m.id: {"raw": "x" * 300, "entry": m}
            for m in ALL_MODELS[:4]
        }
        formats = {m.id: {"teaching_content": "x" * 300} for m in ALL_MODELS[:4]}
        result = self.voter.aggregate(responses, formats, "topic")
        quality = result["quality_report"]
        self.assertIn(quality["level"], ["excellent", "good", "acceptable", "poor"])


class TestOrchestrationEngine(unittest.TestCase):
    """编排引擎测试（不实际调用模型）"""

    def test_node_input(self):
        engine = OrchestrationEngine()
        state = engine.node_input("函数", "高中数学")
        self.assertEqual(state["input_topic"], "函数")
        self.assertEqual(state["input_context"], "高中数学")

    def test_run_single_no_model(self):
        engine = OrchestrationEngine()
        result = engine.run_single("")
        # 空主题返回 success=True 但 content 为空
        self.assertTrue(result.get("success", False))

    def test_run_single_invalid_model(self):
        engine = OrchestrationEngine()
        result = engine.run_single("测试", model_id="nonexistent")
        self.assertFalse(result.get("success", True))


# ================================================================
# 五、orchestrator.py 测试
# ================================================================
class TestUnifiedOrchestrator(unittest.TestCase):
    """统一编排器测试"""

    def setUp(self):
        self.orch = UnifiedOrchestrator()

    def test_run_missing_topic(self):
        result = self.orch.run({})
        self.assertFalse(result.get("success", True))
        self.assertIn("error", result)

    def test_run_simple_task(self):
        result = self.orch.run({"topic": "什么是函数"})
        # 简单任务路由到 simple 或 standard（取决于关键词匹配）
        self.assertIn(result["route"], ["simple", "standard"])
        self.assertIn("agent_trace", result)
        self.assertIn("total_time", result)

    def test_run_complex_task(self):
        result = self.orch.run({"topic": "比较三种函数的异同"})
        self.assertIn("route", result)
        self.assertIn("agent_trace", result)

    def test_force_route(self):
        result = self.orch.run({
            "topic": "什么是函数",
            "route": "complex_parallel",
        })
        self.assertEqual(result["route"], "complex_parallel")

    def test_get_status(self):
        status = self.orch.get_status()
        self.assertIn("router", status)
        self.assertIn("models", status)
        self.assertGreater(status["models"]["total"], 0)

    def test_singleton(self):
        o1 = get_unified_orchestrator()
        o2 = get_unified_orchestrator()
        self.assertIs(o1, o2)

    def test_run_agent_convenience(self):
        result = run_agent({"topic": "勾股定理"})
        self.assertIn("route", result)


# ================================================================
# 六、framework/admin/agents.py 扩展测试
# ================================================================
class TestNewAgents(unittest.TestCase):
    """Phase 1 新增 Agent 测试"""

    def test_router_task_agent_creation(self):
        agent = RouterTaskAgent()
        self.assertEqual(agent.agent_id, "router_task")
        self.assertEqual(agent.agent_type, "router")

    def test_router_task_agent_run(self):
        agent = RouterTaskAgent()
        result = agent.run({"topic": "什么是导数"})
        self.assertTrue(result["success"])
        self.assertIn("route_result", result)
        self.assertIn("route", result["route_result"])

    def test_router_task_agent_health(self):
        agent = RouterTaskAgent()
        health = agent.health()
        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["type"], "router")

    def test_unified_orchestrator_agent_creation(self):
        agent = UnifiedOrchestratorAgent()
        self.assertEqual(agent.agent_id, "unified_orchestrator")
        self.assertEqual(agent.agent_type, "unified_orchestrator")

    def test_unified_orchestrator_agent_run(self):
        agent = UnifiedOrchestratorAgent()
        result = agent.run({"topic": "牛顿定律"})
        self.assertIn("route", result)
        self.assertIn("agent_trace", result)

    def test_unified_orchestrator_agent_health(self):
        agent = UnifiedOrchestratorAgent()
        health = agent.health()
        self.assertEqual(health["status"], "healthy")
        self.assertGreater(health.get("registered_models", 0), 0)

    def test_builtin_agents_includes_new(self):
        agent_ids = {a().agent_id for a in BUILTIN_AGENTS}
        self.assertIn("router_task", agent_ids)
        self.assertIn("unified_orchestrator", agent_ids)
        # P0-2：事实核查 Agent 注册
        self.assertIn("fact_checker", agent_ids)
        # 原有 Agent 仍保留
        self.assertIn("feynman_teacher", agent_ids)
        self.assertIn("output_detector", agent_ids)


class TestAgentRegistryWithNewAgents(unittest.TestCase):
    """AgentRegistry 与新 Agent 集成测试"""

    def test_registry_lists_new_agents(self):
        registry = AgentRegistry()
        agents = registry.list_agents()
        agent_ids = {a["agent_id"] for a in agents}
        self.assertIn("router_task", agent_ids)
        self.assertIn("unified_orchestrator", agent_ids)

    def test_registry_starts_new_agents(self):
        registry = AgentRegistry()
        result = registry.start("router_task")
        self.assertTrue(result["success"])
        registry.stop("router_task")


# ================================================================
# 七、兼容性测试
# ================================================================
class TestBackwardCompatibility(unittest.TestCase):
    """与 Phase 0 的兼容性测试"""

    def test_lumilearn_multi_agent_still_works(self):
        """兼容性 shim lumilearn_multi_agent.py 仍可导入 _map_level"""
        try:
            from lumilearn_multi_agent import _map_level
            self.assertEqual(_map_level("高中"), "senior")
        except ImportError as e:
            self.fail(f"导入 lumilearn_multi_agent 兼容性 shim 失败: {e}")

    def test_langgraph_engine_still_works(self):
        """langgraph_engine 兼容层可导入（统一走 agent_core 版本）"""
        try:
            from agent_core.langgraph_engine import OrchestrationEngine
            engine = OrchestrationEngine()
            self.assertIsNotNone(engine)
        except ImportError as e:
            self.fail(f"导入 langgraph_engine 失败: {e}")

    def test_agent_core_imports(self):
        """agent_core 模块可正常导入"""
        from agent_core import AgentState, ToolCall, AgentResult, TaskProfile, RouterAgent
        self.assertIsNotNone(AgentState)
        self.assertIsNotNone(RouterAgent)

    def test_framework_agents_import(self):
        """framework.admin.agents 可正常导入"""
        from framework.admin.agents import (
            BaseAgent, FeynmanAgent, DetectionAgent,
            AdaptiveAgent, ChatAgent,
            RouterTaskAgent, UnifiedOrchestratorAgent,
        )
        self.assertTrue(issubclass(RouterTaskAgent, BaseAgent))
        self.assertTrue(issubclass(UnifiedOrchestratorAgent, BaseAgent))


# ================================================================
# 运行测试
# ================================================================
if __name__ == "__main__":
    unittest.main(verbosity=2)
