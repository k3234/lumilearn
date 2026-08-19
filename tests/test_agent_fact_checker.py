# -*- coding: utf-8 -*-
"""
LumiLearn — P0-2 事实核查 Agent 测试

覆盖：
  - FactCheckerAgent 规则核查：一致通过 / 数值矛盾失败 / 无来源降级 /
    空内容失败 / 低关联度 warn / 主题覆盖不足 warn
  - MultiAgentPipeline 集成：fact_check 字段、失败触发人工复核标记
    （P0-1 协同）、开关可关闭、异常降级放行
  - UnifiedOrchestrator：事实核查失败 → awaiting_review(node=verifier)
"""

import sys
import os
import time
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.fact_checker import FactCheckerAgent, get_fact_checker_agent
from agent_core.multi_agent import MultiAgentPipeline
from agent_core.orchestrator import UnifiedOrchestrator


def _uniq(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}"


SOURCE_GRAVITY = {
    "source": "training_data", "id": 1, "title": "自由落体",
    "subject": "物理",
    "content": "重力加速度约为 9.8 m/s²。自由落体：初速度为零，"
               "仅受重力作用，下落快慢与质量无关。",
}

GOOD_CONTENT = (
    "重力加速度在地球表面约为 9.8 m/s²。自由落体运动是初速度为零、"
    "只受重力的运动，下落快慢与质量无关。常见误区：误以为质量大的物体下落更快。"
)

CONTRADICT_CONTENT = (
    "自由落体运动的加速度约为 20 m/s²。自由落体是初速度为零、只受重力的运动，"
    "下落快慢与质量无关。"
)

UNRELATED_CONTENT = "今天天气很好，我们去公园散步，顺便买了水果。"


def _good_teaching() -> dict:
    """正常教学输出（Verifier 通过）"""
    return {
        "success": True,
        "steps": [
            {"step_name": "现象引入", "content": "生活例子：" + "例" * 30},
            {"step_name": "思维模型", "content": "核心定义：" + "义" * 30},
            {"step_name": "自主推导", "content": "推导过程：" + "程" * 30},
            {"step_name": "认知冲突", "content": "常见误区：" + "区" * 30},
            {"step_name": "费曼测试", "content": "复述问题：" + "题" * 30},
        ],
        "full_content": GOOD_CONTENT + "内容补充" * 30,
        "rag_sources": [],
        "model_used": "mock",
        "elapsed": 0.05,
    }


# ================================================================
# 一、FactCheckerAgent 规则核查
# ================================================================
class TestFactCheckerAgent(unittest.TestCase):
    """事实核查规则：一致通过 / 矛盾失败 / 降级"""

    def setUp(self):
        self.fc = FactCheckerAgent(use_model=False)

    def test_consistent_content_passes(self):
        """内容与来源一致 → 通过，sources_checked >= 1"""
        result = self.fc.run({
            "topic": "重力加速度",
            "teaching_content": GOOD_CONTENT,
            "rag_sources": [SOURCE_GRAVITY],
        })
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["sources_checked"], 1)
        self.assertGreaterEqual(result["confidence"], self.fc.threshold)
        self.assertFalse(any(i["level"] == "error" for i in result["issues"]))

    def test_numeric_contradiction_fails(self):
        """内容数值与来源矛盾（20 vs 9.8 m/s²）→ 硬性失败"""
        result = self.fc.run({
            "topic": "重力加速度",
            "teaching_content": CONTRADICT_CONTENT,
            "rag_sources": [SOURCE_GRAVITY],
        })
        self.assertFalse(result["passed"])
        self.assertTrue(any(
            i["item"] == "contradiction" and i["level"] == "error"
            for i in result["issues"]))
        self.assertLess(result["confidence"], self.fc.threshold)
        self.assertEqual(result["sources_checked"], 1)

    def test_no_sources_degrades_pass(self):
        """无知识库来源 → 降级放行（不阻塞教学），sources_checked=0"""
        # Mock 检索器：隔离测试库预置知识点的影响，保证确定性
        fake_retriever = MagicMock()
        fake_retriever.search.return_value = []
        with patch("framework.services.knowledge_retrieval.get_knowledge_retriever",
                   return_value=fake_retriever):
            result = self.fc.run({
                "topic": "重力加速度",
                "teaching_content": GOOD_CONTENT,
                "rag_sources": [],
            })
        self.assertTrue(result["passed"])
        self.assertEqual(result["sources_checked"], 0)
        self.assertTrue(any(i["level"] == "info" for i in result["issues"]))

    def test_empty_content_fails(self):
        """教学内容为空 → 判定失败"""
        result = self.fc.run({"topic": "重力加速度", "teaching_content": ""})
        self.assertFalse(result["passed"])
        self.assertTrue(any(i["level"] == "error" for i in result["issues"]))

    def test_low_relation_warns_but_passes(self):
        """内容与来源关联度极低 → warn（疑似幻觉风险），但不硬性失败"""
        result = self.fc.run({
            "topic": "重力加速度",
            "teaching_content": UNRELATED_CONTENT,
            "rag_sources": [SOURCE_GRAVITY],
        })
        self.assertTrue(result["passed"])
        self.assertTrue(any(i["level"] == "warn" and i["item"] == "consistency"
                            for i in result["issues"]))

    def test_topic_not_covered_warns(self):
        """知识库来源未覆盖主题 → warn coverage"""
        result = self.fc.run({
            "topic": "英语时态",
            "teaching_content": GOOD_CONTENT,
            "rag_sources": [SOURCE_GRAVITY],
        })
        self.assertTrue(any(i["level"] == "warn" and i["item"] == "coverage"
                            for i in result["issues"]))

    def test_missing_topic_fails(self):
        result = self.fc.run({"topic": "  "})
        self.assertFalse(result["passed"])

    def test_singleton(self):
        f1 = get_fact_checker_agent(use_model=False)
        f2 = get_fact_checker_agent(use_model=False)
        self.assertIs(f1, f2)


# ================================================================
# 二、MultiAgentPipeline 集成
# ================================================================
class TestPipelineFactCheck(unittest.TestCase):
    """事实核查作为 pipeline 独立阶段，与 Verifier 协同"""

    def _make_pipeline(self, **kwargs):
        pipeline = MultiAgentPipeline(
            verifier_use_model=False, use_parallel=False, **kwargs)
        pipeline.feynman.run = MagicMock(return_value=_good_teaching())
        return pipeline

    def test_fact_check_field_present(self):
        """正常流程：报告含 fact_check 字段且不触发人工复核"""
        pipeline = self._make_pipeline()
        report = pipeline.run({"topic": _uniq("fc_ok"), "reuse_mode": "off"})
        self.assertIn("fact_check", report)
        self.assertTrue(report["fact_check"]["passed"])
        self.assertFalse(report.get("needs_human_review", False))
        self.assertIn("fact_check", report["agent_trace"])

    def test_fact_failure_flags_human_review(self):
        """事实核查发现矛盾（error）→ 与 P0-1 协同标记人工复核且不写回"""
        topic = _uniq("fc_fail")
        pipeline = self._make_pipeline()
        pipeline.fact_checker.run = MagicMock(return_value={
            "passed": False, "confidence": 30.0,
            "issues": [{"level": "error", "item": "contradiction",
                        "detail": "数值与知识库来源矛盾：内容「20m/s²」vs 来源「9.8m/s²」"}],
            "reason": "事实核查未通过，存在与知识库来源矛盾的内容",
            "sources_checked": 1, "elapsed": 0.01,
        })
        report = pipeline.run({"topic": topic, "reuse_mode": "off"})
        self.assertTrue(report.get("needs_human_review"))
        self.assertEqual(report["human_review"]["trigger"], "fact_check_failed")
        self.assertFalse(report["fact_check"]["passed"])
        # 需人工复核 → 不写回知识库
        self.assertFalse(report.get("knowledge_written", False))
        from agent_core.knowledge_cache import get_knowledge_cache
        hits = get_knowledge_cache().query(topic=topic, min_quality=0)
        self.assertEqual(len(hits), 0)

    def test_fact_check_disabled(self):
        """fact_check=False → 不运行事实核查"""
        pipeline = self._make_pipeline(fact_check=False)
        report = pipeline.run({"topic": _uniq("fc_off"), "reuse_mode": "off"})
        self.assertNotIn("fact_check", report)

    def test_fact_check_exception_degrades(self):
        """事实核查异常 → 降级放行，不影响主流程"""
        pipeline = self._make_pipeline()
        pipeline.fact_checker.run = MagicMock(side_effect=RuntimeError("boom"))
        report = pipeline.run({"topic": _uniq("fc_err"), "reuse_mode": "off"})
        self.assertTrue(report["fact_check"]["passed"])
        self.assertIn("降级放行", report["fact_check"]["reason"])
        self.assertFalse(report.get("needs_human_review", False))


# ================================================================
# 三、UnifiedOrchestrator 集成
# ================================================================
class TestOrchestratorFactCheckInterrupt(unittest.TestCase):
    """事实核查失败（矛盾）→ awaiting_review(node=verifier)"""

    def setUp(self):
        from agent_core.observability import reset_telemetry
        from agent_core.safety import reset_safety_guard
        reset_telemetry()
        reset_safety_guard()
        self.orch = UnifiedOrchestrator()

    def _mock_route(self):
        return patch.object(self.orch.router, "route", return_value={
            "route": "standard",
            "profile": {"complexity": "standard", "reasoning_type": "sequential",
                        "subject": "物理", "topic": "t", "estimated_calls": 3,
                        "confidence": 0.8, "keywords": []},
        })

    def test_fact_check_failure_interrupts(self):
        """pipeline 标记 fact_check_failed → run() 返回 awaiting_review"""
        bad_report = {
            "success": True,
            "needs_human_review": True,
            "human_review_reason": "事实核查未通过：存在与知识库来源矛盾的内容",
            "human_review": {"needs_review": True, "confidence": 30.0,
                             "trigger": "fact_check_failed",
                             "error_issues": [
                                 {"level": "error", "item": "contradiction",
                                  "detail": "数值矛盾"}]},
            "fact_check": {"passed": False, "confidence": 30.0,
                           "issues": [], "reason": "矛盾",
                           "sources_checked": 1},
            "teaching": {"full_content": GOOD_CONTENT},
        }
        with self._mock_route() as mr, \
             patch.object(self.orch, "_run_standard",
                          return_value=bad_report) as ms, \
             patch.object(self.orch.safety, "estimate_tokens", return_value=10):
            result = self.orch.run({"topic": "重力加速度", "user_id": 1})
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "awaiting_review")
            self.assertEqual(result["node"], "verifier")
            self.assertEqual(result["human_review"]["trigger"],
                             "fact_check_failed")
            self.assertGreaterEqual(len(self.orch.get_pending_interrupts()), 1)


if __name__ == "__main__":
    unittest.main()
