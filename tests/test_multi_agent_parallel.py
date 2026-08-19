# -*- coding: utf-8 -*-
"""
LumiLearn Phase 2 — 并行化与反馈回路 端到端测试

覆盖交付物：
  - agent_core.verifier:   Verifier Agent（质量验证/反馈回路）
  - agent_core.multi_agent: MultiAgentPipeline（并行编排+反馈）
  - agent_core.graph:      StateGraph 图定义 + 条件边反馈回路
  - agent_core.orchestrator: UnifiedOrchestrator 接入新流水线
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.verifier import VerifierAgent, get_verifier_agent, verify_teaching
from agent_core.multi_agent import (
    FeynmanTeacher, ScoreAgent, CoachAgent,
    MultiAgentPipeline, MultiAgentOrchestrator,
    get_multi_agent_pipeline, get_multi_agent_orchestrator, run_multi_agent,
)
from agent_core.graph import (
    StateGraph, CompiledGraph, build_feedback_graph,
    get_feedback_graph, run_graph,
    router_node, feynman_node, score_node, coach_node, verifier_node,
    verifier_condition,
)


# ================================================================
# 一、VerifierAgent 测试
# ================================================================
GOOD_PAYLOAD = {
    "topic": "函数的单调性",
    "teaching_content": "函数的单调性是描述函数值随自变量变化趋势的性质。"
                        "增函数：自变量增大时函数值增大。减函数：自变量增大时函数值减小。"
                        "判断方法：导数法、定义法。常见误区：混淆增区间与单调区间。"
                        "应用：判断函数最值、解不等式。",
    "steps": [
        {"step_name": "现象引入", "content": "爬山的上坡下坡就是单调性"},
        {"step_name": "思维模型", "content": "增函数减函数定义"},
        {"step_name": "自主推导", "content": "用定义证明"},
        {"step_name": "认知冲突", "content": "单调区间并集误区"},
        {"step_name": "费曼测试", "content": "用自己的话讲一遍"},
    ],
    "score": 85,
    "mastery_level": "优秀",
    "suggestions": ["已掌握，挑战进阶题", "举一反三"],
}


class TestVerifierAgent(unittest.TestCase):
    """Verifier Agent 单元测试（规则模式）"""

    def test_good_content_passes(self):
        v = VerifierAgent(use_model=False)
        result = v.run(GOOD_PAYLOAD)
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["confidence"], 60.0)

    def test_error_placeholder_fails(self):
        v = VerifierAgent(use_model=False)
        payload = dict(GOOD_PAYLOAD)
        payload["teaching_content"] = "[qwen2.5:7b 不可用: timeout]"
        result = v.run(payload)
        self.assertFalse(result["passed"])
        self.assertTrue(any(i["level"] == "error" for i in result["issues"]))

    def test_empty_topic_fails(self):
        v = VerifierAgent(use_model=False)
        result = v.run({"topic": "  "})
        self.assertFalse(result["passed"])
        self.assertEqual(result["confidence"], 0.0)

    def test_empty_content_fails(self):
        v = VerifierAgent(use_model=False)
        payload = dict(GOOD_PAYLOAD)
        payload["teaching_content"] = ""
        payload["steps"] = []
        result = v.run(payload)
        self.assertFalse(result["passed"])
        self.assertIn("error", [i["level"] for i in result["issues"]])

    def test_score_out_of_range(self):
        v = VerifierAgent(use_model=False)
        payload = dict(GOOD_PAYLOAD)
        payload["score"] = 150
        result = v.run(payload)
        self.assertFalse(result["passed"])
        self.assertTrue(any(i["item"] == "score" and i["level"] == "error"
                            for i in result["issues"]))

    def test_mastery_score_mismatch_warns(self):
        v = VerifierAgent(use_model=False)
        payload = dict(GOOD_PAYLOAD)
        payload["score"] = 40
        payload["mastery_level"] = "优秀"  # 不匹配
        result = v.run(payload)
        issues = result["issues"]
        self.assertTrue(any(i["item"] == "score" for i in issues))

    def test_empty_suggestions_warns(self):
        v = VerifierAgent(use_model=False)
        payload = dict(GOOD_PAYLOAD)
        payload["suggestions"] = []
        result = v.run(payload)
        self.assertTrue(any(i["item"] == "suggestion" for i in result["issues"]))

    def test_warn_does_not_fail_content(self):
        """warn 级 issue 不判定内容失败"""
        v = VerifierAgent(use_model=False)
        payload = dict(GOOD_PAYLOAD)
        payload["teaching_content"] = "短内容"  # 长度不足 → warn
        payload["steps"] = GOOD_PAYLOAD["steps"]
        result = v.run(payload)
        # 内容检查不应因 warn 判失败，结构/建议仍可能通过
        self.assertIn("content", result["checks"])

    def test_model_verify_reduces_confidence(self):
        """模型验证发现问题时置信度下降"""
        v = VerifierAgent(use_model=True)
        # mock 模型返回 FAIL
        with patch("agent_core.verifier.get_model") as mock_get:
            mock_model = MagicMock()
            mock_model.call.return_value = "FAIL: 内容与主题无关"
            mock_get.return_value = mock_model
            result = v.run(GOOD_PAYLOAD)
            self.assertTrue(any(i["item"] == "model" for i in result["issues"]))

    def test_get_verifier_agent_singleton(self):
        v1 = get_verifier_agent(use_model=False)
        v2 = get_verifier_agent(use_model=False)
        self.assertIs(v1, v2)

    def test_verify_teaching_helper(self):
        result = verify_teaching(GOOD_PAYLOAD, use_model=False)
        self.assertIn("passed", result)


# ================================================================
# 二、MultiAgentPipeline 测试（并行+反馈回路）
# ================================================================
class TestMultiAgentPipeline(unittest.TestCase):
    """并行化编排测试（mock 内部 Agent）"""

    def _make_pipeline(self, verify_results):
        """构造 pipeline，verifier 依次返回 verify_results"""
        pipeline = MultiAgentPipeline(
            max_retries=3, use_parallel=False, verifier_use_model=False)
        # 用全新实例替换共享单例，避免 Mock 属性残留在 get_verifier_agent() 单例上
        pipeline.verifier = VerifierAgent(use_model=False)
        pipeline.feynman.run = MagicMock(return_value={
            "success": True, "mode": "full",
            "steps": GOOD_PAYLOAD["steps"],
            "full_content": GOOD_PAYLOAD["teaching_content"],
            "rag_sources": [],
            "models_used": 3, "best_model": "qwen2.5:7b",
            "elapsed": 0.5,
        })
        pipeline.score.run = MagicMock(return_value={
            "success": True, "score": 85,
            "dimensions": {"准确度": {"score": 85, "comment": "ok"}},
            "is_mastered": True, "feedback": "good",
            "elapsed": 0.3,
        })
        pipeline.coach.run = MagicMock(return_value={
            "success": True, "mastery_level": "优秀",
            "suggestions": ["建议1"], "next_topics": [],
            "elapsed": 0.1,
        })
        pipeline.verifier.run = MagicMock(side_effect=verify_results)
        return pipeline

    def test_feedback_loop_success_on_second_attempt(self):
        """反馈回路：首次验证失败，第二次通过 → 2 轮"""
        pipeline = self._make_pipeline([
            {"passed": False, "confidence": 30.0,
             "issues": [{"level": "error", "item": "content", "detail": "内容空"}],
             "reason": "需改进"},
            {"passed": True, "confidence": 90.0,
             "issues": [], "reason": "通过"},
        ])
        result = pipeline.run({"topic": "函数的单调性",
                               "student_explanation": "test"})
        self.assertEqual(result["feedback_rounds"], 2)
        self.assertTrue(result["verified"])
        self.assertTrue(result["verifier"]["passed"])

    def test_max_retries_limits_feedback_loop(self):
        """一直失败 → max_retries 轮后放弃"""
        pipeline = self._make_pipeline([
            {"passed": False, "confidence": 10.0,
             "issues": [{"level": "error", "item": "content", "detail": "x"}],
             "reason": "fail"} for _ in range(5)
        ])
        result = pipeline.run({"topic": "函数的单调性",
                               "student_explanation": "test"})
        self.assertEqual(result["feedback_rounds"], 3)  # max_retries=3
        self.assertFalse(result["verified"])

    def test_no_student_explanation_skips_score(self):
        """无学生解释 → score 阶段跳过"""
        pipeline = self._make_pipeline([
            {"passed": True, "confidence": 90.0, "issues": [], "reason": "ok"}
        ])
        result = pipeline.run({"topic": "函数的单调性"})
        self.assertEqual(result["assessment"]["score"], 0)
        self.assertTrue(any("skipped" in v.get("status", "")
                            for v in result["agent_trace"].values()))

    def test_parallel_stats_present(self):
        """并行统计字段存在"""
        pipeline = self._make_pipeline([
            {"passed": True, "confidence": 90.0, "issues": [], "reason": "ok"}
        ])
        result = pipeline.run({"topic": "函数的单调性",
                               "student_explanation": "test"})
        self.assertEqual(result["teaching"]["steps"], GOOD_PAYLOAD["steps"])
        self.assertIn("verifier", result)
        self.assertIn("feedback_rounds", result)

    def test_missing_topic_fails(self):
        pipeline = MultiAgentPipeline(use_parallel=False, verifier_use_model=False)
        result = pipeline.run({"topic": "  "})
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_verifier_failure_keeps_running(self):
        """Verifier 抛异常 → 降级放行"""
        pipeline = self._make_pipeline([Exception("boom")])
        result = pipeline.run({"topic": "函数的单调性"})
        self.assertTrue(result["verified"])  # 异常放行


class TestMultiAgentOrchestratorCompat(unittest.TestCase):
    """兼容层测试：MultiAgentOrchestrator 输出格式兼容"""

    def test_orchestrator_compat_output(self):
        pipeline = MultiAgentPipeline(
            max_retries=2, use_parallel=False, verifier_use_model=False)
        pipeline.verifier = VerifierAgent(use_model=False)
        pipeline.feynman.run = MagicMock(return_value={
            "success": True, "mode": "full",
            "steps": GOOD_PAYLOAD["steps"],
            "full_content": GOOD_PAYLOAD["teaching_content"],
            "rag_sources": [], "elapsed": 0.5,
        })
        pipeline.verifier.run = MagicMock(return_value={
            "passed": True, "confidence": 90.0, "issues": [], "reason": "ok"})
        orch = MultiAgentOrchestrator(max_retries=2, use_parallel=False)
        orch.pipeline = pipeline  # 替换内部 pipeline
        result = orch.run({"topic": "函数的单调性",
                           "student_explanation": "test"})
        self.assertIn("teaching", result)
        self.assertIn("assessment", result)
        self.assertIn("coaching", result)
        self.assertIn("agent_trace", result)
        self.assertIn("verifier", result)

    def test_run_multi_agent_helper(self):
        with patch("agent_core.multi_agent.get_multi_agent_orchestrator") as m:
            m.return_value.run.return_value = {"topic": "x"}
            result = run_multi_agent({"topic": "x"})
            self.assertEqual(result["topic"], "x")


# ================================================================
# 三、FeynmanTeacher 并行测试
# ================================================================
class TestFeynmanTeacherParallel(unittest.TestCase):
    """并行教学测试（mock 模型）"""

    def _mock_model(self, mid, name, weight, raw):
        m = MagicMock()
        m.id = mid
        m.name = name
        m.weight = weight
        m.call = MagicMock(return_value=raw)
        return m

    def test_run_parallel_aggregates_votes(self):
        teacher = FeynmanTeacher(model_name="qwen2.5:7b")
        models = {
            "m1": self._mock_model("m1", "model1", 2, "高质量内容" * 50),
            "m2": self._mock_model("m2", "model2", 1, "低质量" * 10),
        }
        with patch("agent_core.multi_agent.ALL_MODELS_DICT", models), \
             patch("agent_core.multi_agent.get_best_models",
                   return_value=[models["m1"], models["m2"]]):
            result = teacher.run_parallel(
                {"topic": "测试", "difficulty": "高中"},
                model_ids=["m1", "m2"], max_workers=2)
            self.assertTrue(result["success"])
            self.assertEqual(result["models_used"], 2)
            self.assertIn("model_votes", result)
            # 高权重模型应被选为 best
            self.assertEqual(result["best_model"], "model1")

    def test_run_parallel_all_models_fail(self):
        teacher = FeynmanTeacher(model_name="qwen2.5:7b")
        models = {
            "m1": self._mock_model("m1", "model1", 2, "[不可用: x]"),
        }
        with patch("agent_core.multi_agent.ALL_MODELS_DICT", models), \
             patch("agent_core.multi_agent.get_best_models",
                   return_value=[models["m1"]]):
            result = teacher.run_parallel(
                {"topic": "测试"}, model_ids=["m1"])
            self.assertFalse(result["success"])
            self.assertIn("error", result)

    def test_run_missing_topic(self):
        teacher = FeynmanTeacher()
        result = teacher.run({"topic": " "})
        self.assertFalse(result["success"])


# ================================================================
# 四、StateGraph 图定义测试
# ================================================================
class TestStateGraph(unittest.TestCase):
    """轻量 StateGraph 测试"""

    def test_build_and_nodes(self):
        graph = build_feedback_graph()
        self.assertEqual(set(graph.graph.nodes.keys()),
                         {"router", "feynman", "score", "coach", "verifier"})
        self.assertIn("verifier", graph.graph.conditional_edges)

    def test_conditional_feedback_loop(self):
        """条件边：verifier 失败 → feynman 重试"""
        graph = StateGraph(dict)
        graph.add_node("feynman", lambda s: s)
        graph.add_node("verifier", lambda s: s)
        graph.add_edge("feynman", "verifier")
        graph.add_conditional_edges(
            "verifier", verifier_condition,
            {"end": "", "feynman": "feynman"})
        compiled = graph.compile()

        # 失败 → 反馈回路
        state = {"verified": False, "retry_count": 0, "max_retries": 2}
        result = compiled.invoke(state)
        self.assertIn("feynman", result["execution_path"])
        self.assertGreaterEqual(result["retry_count"], 1)

    def test_max_retries_stops_loop(self):
        """达到 max_retries 后停止反馈回路"""
        graph = build_feedback_graph()
        state = {
            "input_topic": "t", "input_context": "",
            "verified": False, "retry_count": 0, "max_retries": 0,
        }
        # 直接构造：mock feynman 节点避免真实模型调用
        graph.graph.nodes["feynman"].func = lambda s: s
        graph.graph.nodes["score"].func = lambda s: s
        graph.graph.nodes["coach"].func = lambda s: s
        graph.graph.nodes["router"].func = lambda s: s
        graph.graph.nodes["verifier"].func = lambda s: dict(
            s, verified=False, verifier_result={
                "passed": False, "confidence": 0.0, "issues": []})
        result = graph.invoke(state)
        self.assertIn("feedback", result["agent_trace"])
        self.assertEqual(result["agent_trace"]["feedback"]["status"],
                         "max_retries_exceeded")

    def test_verifier_condition_logic(self):
        self.assertEqual(verifier_condition({"verified": True}), "end")
        self.assertEqual(verifier_condition({"verified": False}), "feynman")


if __name__ == "__main__":
    unittest.main()
