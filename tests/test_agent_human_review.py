# -*- coding: utf-8 -*-
"""
LumiLearn — P0-1 人工中断全链路扩展（Verifier 阶段）测试

覆盖：
  - evaluate_human_review 判定逻辑（低置信度 / 内容质量异常 / 通过不触发）
  - MultiAgentPipeline 标记 needs_human_review（验证未通过且低置信度）
  - 需人工复核的内容不写回知识库（避免污染自积累知识库）
  - UnifiedOrchestrator.run() 接线：
      质量异常 → awaiting_review(node=verifier) → resume(approved)
      → 带 _interrupt_approved 重跑放行（human_review_approved）
  - 验证通过时不触发中断；human_review 开关可关闭
"""

import sys
import os
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.verifier import (
    VerifierAgent, evaluate_human_review,
    HUMAN_REVIEW_CONFIDENCE_THRESHOLD,
)
from agent_core.multi_agent import MultiAgentPipeline
from agent_core.orchestrator import UnifiedOrchestrator


def _uniq(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}"


def _good_teaching() -> dict:
    """正常教学输出（Verifier 应通过）"""
    return {
        "success": True,
        "steps": [
            {"step_name": "现象引入", "content": "生活例子：" + "例" * 30},
            {"step_name": "思维模型", "content": "核心定义：" + "义" * 30},
            {"step_name": "自主推导", "content": "推导过程：" + "程" * 30},
            {"step_name": "认知冲突", "content": "常见误区：" + "区" * 30},
            {"step_name": "费曼测试", "content": "复述问题：" + "题" * 30},
        ],
        "full_content": "函数的单调性……" + "内容" * 120,
        "rag_sources": [],
        "model_used": "mock",
        "elapsed": 0.05,
    }


# ================================================================
# 一、evaluate_human_review 判定逻辑
# ================================================================
class TestEvaluateHumanReview(unittest.TestCase):
    """人工复核判定：低置信度 / 内容质量异常 / 通过不触发"""

    def setUp(self):
        self.verifier = VerifierAgent(use_model=False)

    def test_passed_no_review(self):
        """验证通过 → 不触发人工复核"""
        payload = {
            "topic": "函数的单调性",
            "teaching_content": _good_teaching()["full_content"],
            "steps": _good_teaching()["steps"],
            "score": 85,
            "mastery_level": "优秀",
            "suggestions": ["已掌握，挑战进阶题"],
        }
        verify = self.verifier.run(payload)
        self.assertTrue(verify["passed"])
        decision = evaluate_human_review(verify)
        self.assertFalse(decision["needs_review"])
        self.assertEqual(decision["trigger"], "")

    def test_low_confidence_triggers_review(self):
        """空内容 → 结构与内容均 error → 置信度 0 → 低置信度触发"""
        verify = self.verifier.run({"topic": "某主题", "teaching_content": ""})
        self.assertFalse(verify["passed"])
        decision = evaluate_human_review(verify)
        self.assertTrue(decision["needs_review"])
        self.assertEqual(decision["trigger"], "low_confidence")
        self.assertLess(decision["confidence"],
                        HUMAN_REVIEW_CONFIDENCE_THRESHOLD)
        self.assertGreaterEqual(len(decision["error_issues"]), 1)

    def test_content_anomaly_triggers_review(self):
        """内容质量异常（error 级 content 问题）→ 即使置信度达标也触发"""
        decision = evaluate_human_review({
            "passed": False,
            "confidence": 70.0,
            "issues": [
                {"level": "error", "item": "content",
                 "detail": "内容包含错误占位符: 不可用"},
                {"level": "warn", "item": "score", "detail": "评分偏差"},
            ],
        }, confidence_threshold=45.0)
        self.assertTrue(decision["needs_review"])
        self.assertEqual(decision["trigger"], "content_anomaly")

    def test_non_content_error_not_enough(self):
        """仅 score/suggestion 类 error（非内容质量）→ 不触发复核"""
        decision = evaluate_human_review({
            "passed": False,
            "confidence": 70.0,
            "issues": [
                {"level": "error", "item": "score", "detail": "评分超出范围"},
            ],
        }, confidence_threshold=45.0)
        self.assertFalse(decision["needs_review"])

    def test_passed_wins_over_threshold(self):
        """passed=True 时即使 confidence 低于阈值也不触发（passed 优先）"""
        decision = evaluate_human_review({
            "passed": True, "confidence": 30.0, "issues": []},
            confidence_threshold=60.0)
        self.assertFalse(decision["needs_review"])


# ================================================================
# 二、MultiAgentPipeline 标记 needs_human_review
# ================================================================
class TestPipelineHumanReviewFlag(unittest.TestCase):
    """流水线在验证未通过且质量异常时标记 needs_human_review（不自行中断）"""

    def test_bad_content_flagged_and_not_written(self):
        """空内容 → 低置信度 → 标记 needs_human_review，且不写回知识库"""
        topic = _uniq("review_pipeline")
        pipeline = MultiAgentPipeline(verifier_use_model=False, use_parallel=False)
        # 注入全新 Verifier 实例：隔离 test_multi_agent_parallel 对单例 run 的 Mock 污染
        pipeline.verifier = VerifierAgent(use_model=False)
        with patch.object(pipeline.feynman, "run", return_value={
            "success": True, "steps": [],
            "full_content": "",  # 空内容 → verifier error → 低置信度
            "rag_sources": [], "model_used": "mock", "elapsed": 0.01,
        }):
            report = pipeline.run({"topic": topic, "reuse_mode": "off"})
        self.assertFalse(report["verifier"]["passed"])
        self.assertTrue(report.get("needs_human_review"))
        self.assertEqual(report["human_review"]["trigger"], "low_confidence")
        self.assertTrue(report["human_review_reason"])
        self.assertIn("置信度", report["human_review_reason"])
        # 需人工复核的内容不写回知识库
        self.assertFalse(report.get("knowledge_written", False))
        from agent_core.knowledge_cache import get_knowledge_cache
        hits = get_knowledge_cache().query(topic=topic, min_quality=0)
        self.assertEqual(len(hits), 0)

    def test_good_content_not_flagged(self):
        """验证通过 → 不标记"""
        topic = _uniq("review_ok")
        pipeline = MultiAgentPipeline(verifier_use_model=False, use_parallel=False)
        pipeline.verifier = VerifierAgent(use_model=False)
        with patch.object(pipeline.feynman, "run", return_value=_good_teaching()):
            report = pipeline.run({"topic": topic, "reuse_mode": "off"})
        self.assertTrue(report["verifier"]["passed"])
        self.assertFalse(report.get("needs_human_review", False))

    def test_human_review_disabled(self):
        """human_review=False → 关闭复核标记"""
        topic = _uniq("review_off")
        pipeline = MultiAgentPipeline(
            verifier_use_model=False, use_parallel=False, human_review=False)
        pipeline.verifier = VerifierAgent(use_model=False)
        with patch.object(pipeline.feynman, "run", return_value={
            "success": True, "steps": [],
            "full_content": "",
            "rag_sources": [], "model_used": "mock", "elapsed": 0.01,
        }):
            report = pipeline.run({"topic": topic, "reuse_mode": "off"})
        self.assertFalse(report.get("needs_human_review", False))


# ================================================================
# 三、UnifiedOrchestrator Verifier 阶段人工中断接线
# ================================================================
class TestOrchestratorVerifierInterrupt(unittest.TestCase):
    """run() 流程：质量异常 → awaiting_review(node=verifier) → 审批 → 放行"""

    def setUp(self):
        from agent_core.observability import reset_telemetry
        from agent_core.safety import reset_safety_guard
        reset_telemetry()
        reset_safety_guard()
        self.orch = UnifiedOrchestrator()

    def _mock_route(self, subject="综合", keywords=None):
        return patch.object(self.orch.router, "route", return_value={
            "route": "standard",
            "profile": {"complexity": "standard", "reasoning_type": "sequential",
                        "subject": subject, "topic": "t", "estimated_calls": 3,
                        "confidence": 0.8, "keywords": keywords or []},
        })

    def _bad_report(self) -> dict:
        """模拟 _run_standard 返回的质量异常报告"""
        return {
            "success": True,
            "needs_human_review": True,
            "human_review_reason": (
                "验证未通过且置信度过低（30.0% < 人工复核阈值 45.0%）"),
            "human_review": {"needs_review": True, "confidence": 30.0,
                             "trigger": "low_confidence", "error_issues": []},
            "teaching": {"full_content": "低质量教学内容"},
        }

    def test_verifier_anomaly_returns_awaiting_review(self):
        """质量异常 → 返回 awaiting_review（node=verifier），中断入队"""
        with self._mock_route() as mr, \
             patch.object(self.orch, "_run_standard",
                          return_value=self._bad_report()) as ms, \
             patch.object(self.orch.safety, "estimate_tokens", return_value=10):
            result = self.orch.run({"topic": "量子力学入门", "user_id": 1})
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "awaiting_review")
            self.assertEqual(result["node"], "verifier")
            self.assertIn("trace_id", result)
            self.assertEqual(result["human_review"]["trigger"], "low_confidence")
            ms.assert_called_once()  # 已生成，但未直接交付
            self.assertGreaterEqual(len(self.orch.get_pending_interrupts()), 1)

    def test_resume_approved_rerun_passes(self):
        """完整流程：中断 → 审批通过 → 带标记重跑 → 放行（human_review_approved）"""
        with self._mock_route() as mr, \
             patch.object(self.orch, "_run_standard",
                          return_value=self._bad_report()) as ms, \
             patch.object(self.orch.safety, "estimate_tokens", return_value=10):
            # 第一次：质量异常 → 等待人工审核
            r1 = self.orch.run({"topic": "量子力学入门", "user_id": 1})
            self.assertEqual(r1["status"], "awaiting_review")
            tid = r1["trace_id"]

            # 管理员审批通过
            resolved = self.orch.resume("approved", "admin", trace_id=tid)
            self.assertEqual(resolved["decision"], "approved")
            self.assertEqual(len(self.orch.get_pending_interrupts()), 0)

            # 携带审批标记重新请求 → 放行执行，保留 human_review_approved
            r2 = self.orch.run({"topic": "量子力学入门", "user_id": 1,
                                "_interrupt_approved": True})
            self.assertTrue(r2["success"])
            self.assertTrue(r2.get("human_review_approved"))
            self.assertEqual(len(self.orch.get_pending_interrupts()), 0)

    def test_rejected_interrupt_stays_pending(self):
        """rejected → 无待审队列残留且状态为 rejected"""
        with self._mock_route() as mr, \
             patch.object(self.orch, "_run_standard",
                          return_value=self._bad_report()) as ms, \
             patch.object(self.orch.safety, "estimate_tokens", return_value=10):
            r1 = self.orch.run({"topic": "量子力学入门", "user_id": 1})
            tid = r1["trace_id"]
            resolved = self.orch.resume("rejected", "teacher1", trace_id=tid)
            self.assertEqual(resolved["decision"], "rejected")
            self.assertEqual(len(self.orch.get_pending_interrupts()), 0)

    def test_normal_quality_no_interrupt(self):
        """验证通过 → 不触发中断"""
        with self._mock_route(subject="数学") as mr, \
             patch.object(self.orch, "_run_standard",
                          return_value={
                              "success": True,
                              "teaching": {"full_content": "正常教学内容"}}) as ms, \
             patch.object(self.orch.safety, "estimate_tokens", return_value=10):
            result = self.orch.run({"topic": "什么是函数", "user_id": 1})
            self.assertTrue(result["success"])
            self.assertEqual(len(self.orch.get_pending_interrupts()), 0)


# ================================================================
# 四、UnifiedOrchestrator complex_parallel 质量 poor 路径（P0-1 扩展）
# ================================================================
class TestOrchestratorComplexParallelPoor(unittest.TestCase):
    """run() 流程：complex_parallel → quality.level=poor → needs_human_review → awaiting_review"""

    def setUp(self):
        from agent_core.observability import reset_telemetry
        from agent_core.safety import reset_safety_guard
        reset_telemetry()
        reset_safety_guard()
        self.orch = UnifiedOrchestrator()

    def _mock_route_complex(self):
        return patch.object(self.orch.router, "route", return_value={
            "route": "complex_parallel",
            "profile": {"complexity": "complex", "reasoning_type": "parallel",
                        "subject": "综合", "topic": "t", "estimated_calls": 5,
                        "confidence": 0.9, "keywords": []},
        })

    def _poor_parallel_report(self) -> dict:
        """模拟 _run_parallel 返回的 quality=poor 报告（与 orchestrator.py:391-401 对应）"""
        return {
            "success": True,
            "route": "complex_parallel",
            "needs_human_review": True,
            "human_review_reason": (
                "多模型并行质量报告为 poor（可用模型/权重不足），置信度过低，需人工审核"),
            "human_review": {
                "needs_review": True,
                "confidence": 25.0,
                "trigger": "low_confidence",
                "error_issues": [],
            },
            "teaching": {"full_content": "低质量并行教学内容"},
        }

    def test_complex_parallel_poor_returns_awaiting_review(self):
        """complex_parallel 质量 poor → 返回 awaiting_review（node=verifier），中断入队"""
        with self._mock_route_complex(), \
             patch.object(self.orch, "_run_parallel",
                          return_value=self._poor_parallel_report()) as mpar, \
             patch.object(self.orch.safety, "estimate_tokens", return_value=10):
            result = self.orch.run({"topic": "量子纠缠入门", "user_id": 1})
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "awaiting_review")
            self.assertEqual(result["node"], "verifier")
            self.assertIn("trace_id", result)
            self.assertEqual(result["human_review"]["trigger"], "low_confidence")
            # interrupt() 返回 {"interrupted": True, "trace_id": ...}，
            # reason 在 get_pending_interrupts() 中可查
            pending = self.orch.get_pending_interrupts()
            self.assertGreaterEqual(len(pending), 1)
            self.assertIn("置信度", pending[0]["reason"])
            mpar.assert_called_once()
            self.assertGreaterEqual(len(self.orch.get_pending_interrupts()), 1)

    def test_complex_parallel_poor_resume_approved_rerun_passes(self):
        """完整流程：complex_parallel poor → 中断 → 审批通过 → 带标记重跑放行"""
        with self._mock_route_complex(), \
             patch.object(self.orch, "_run_parallel",
                          return_value=self._poor_parallel_report()) as mpar, \
             patch.object(self.orch.safety, "estimate_tokens", return_value=10):
            # 第一次：质量 poor → 等待人工审核
            r1 = self.orch.run({"topic": "量子纠缠入门", "user_id": 1})
            self.assertEqual(r1["status"], "awaiting_review")
            tid = r1["trace_id"]

            # 管理员审批通过
            resolved = self.orch.resume("approved", "admin", trace_id=tid)
            self.assertEqual(resolved["decision"], "approved")
            self.assertEqual(len(self.orch.get_pending_interrupts()), 0)

            # 携带审批标记重新请求 → 放行执行，保留 human_review_approved
            r2 = self.orch.run({"topic": "量子纠缠入门", "user_id": 1,
                                "_interrupt_approved": True})
            self.assertTrue(r2["success"])
            self.assertTrue(r2.get("human_review_approved"))
            self.assertEqual(len(self.orch.get_pending_interrupts()), 0)
            # 第二次仍调用 _run_parallel（非 _run_standard）
            mpar.assert_called()

    def test_complex_parallel_good_no_interrupt(self):
        """complex_parallel 质量正常 → 不触发中断"""
        good_report = {
            "success": True,
            "route": "complex_parallel",
            "teaching": {"full_content": "高质量并行教学内容"},
        }
        with self._mock_route_complex(), \
             patch.object(self.orch, "_run_parallel",
                          return_value=good_report) as mpar, \
             patch.object(self.orch.safety, "estimate_tokens", return_value=10):
            result = self.orch.run({"topic": "麦克斯韦方程组", "user_id": 1})
            self.assertTrue(result["success"])
            self.assertFalse(result.get("needs_human_review", False))
            self.assertEqual(len(self.orch.get_pending_interrupts()), 0)
            mpar.assert_called_once()


# ================================================================
# 五、get_all_interrupts() 全量中断查询（P1-4 管理面板）
# ================================================================
class TestGetAllInterruptsIncludesResolved(unittest.TestCase):
    """get_all_interrupts() 同时包含 pending 与已审批中断，且 status 正确"""

    def setUp(self):
        from agent_core.observability import reset_telemetry
        from agent_core.safety import reset_safety_guard
        reset_telemetry()
        reset_safety_guard()
        self.orch = UnifiedOrchestrator()

    def test_get_all_interrupts_includes_resolved(self):
        from agent_core.observability import get_telemetry

        # 创建两个中断：一个保持 pending，一个审批为 approved
        i1 = self.orch.interrupt("待审批中断A：内容需人工审核", node="verifier")
        i2 = self.orch.interrupt("待审批中断B：内容需人工审核", node="verifier")
        tid_approved = i1["trace_id"]
        tid_pending = i2["trace_id"]
        self.assertNotEqual(tid_approved, tid_pending)

        resolved = self.orch.resume("approved", "admin", trace_id=tid_approved)
        self.assertEqual(resolved["decision"], "approved")

        all_interrupts = get_telemetry().get_all_interrupts()
        by_tid = {item["trace_id"]: item for item in all_interrupts}
        # 两者都在全量列表中
        self.assertIn(tid_approved, by_tid)
        self.assertIn(tid_pending, by_tid)
        # 状态正确
        self.assertEqual(by_tid[tid_approved]["status"], "approved")
        self.assertEqual(by_tid[tid_approved]["reviewer"], "admin")
        self.assertEqual(by_tid[tid_pending]["status"], "pending")
        # 待审批队列仅剩未审批的那个
        pending = self.orch.get_pending_interrupts()
        self.assertEqual([p["trace_id"] for p in pending], [tid_pending])


if __name__ == "__main__":
    unittest.main()
