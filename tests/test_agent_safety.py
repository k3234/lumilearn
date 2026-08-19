# -*- coding: utf-8 -*-
"""
LumiLearn Phase 3 — 安全集成测试（模拟 OWASP Top 10 for Agentic Applications）

覆盖交付物：
  - agent_core.safety:       Agent API 调用安全控制（频率/预算/白名单/输出过滤）
  - agent_core.observability: 可观测性（Trace/成本/审计/人工中断）
  - agent_core.orchestrator:  人工中断机制（interrupt/resume）
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.safety import (
    AgentSafetyGuard, get_safety_guard, reset_safety_guard, check_agent_call,
)
from agent_core.observability import (
    AgentTelemetry, get_telemetry, reset_telemetry,
)
from agent_core.orchestrator import UnifiedOrchestrator


# ================================================================
# 一、AgentSafetyGuard 测试
# ================================================================
class TestAgentSafetyGuard(unittest.TestCase):
    """Agent API 调用安全控制测试"""

    def setUp(self):
        reset_safety_guard()
        self.guard = AgentSafetyGuard(
            default_rate_limit=3,
            default_window_sec=60,
            default_budget_per_day=1000,
        )

    def test_normal_call_allowed(self):
        result = self.guard.check_call("agent1", "user1", "qwen2.5:7b", 100)
        self.assertTrue(result["allowed"])
        self.assertEqual(result["reason"], "ok")

    def test_rate_limit_enforced(self):
        # 超过 rate_limit=3 → 拒绝
        for i in range(3):
            r = self.guard.check_call("agent1", "user1")
            self.assertTrue(r["allowed"], f"第{i+1}次应允许")
        r = self.guard.check_call("agent1", "user1")
        self.assertFalse(r["allowed"])
        self.assertIn("频率", r["reason"])
        self.assertGreater(r["retry_after"], 0)

    def test_rate_limit_per_user(self):
        """频率限制按用户隔离"""
        for i in range(3):
            self.guard.check_call("agent1", "userA")
        self.assertFalse(self.guard.check_call("agent1", "userA")["allowed"])
        # 不同用户不受影响
        self.assertTrue(self.guard.check_call("agent1", "userB")["allowed"])

    def test_model_whitelist(self):
        self.guard.set_model_whitelist("agent1", ["qwen2.5:7b"])
        ok = self.guard.check_call("agent1", "user1", "qwen2.5:7b")
        self.assertTrue(ok["allowed"])
        denied = self.guard.check_call("agent1", "user1", "evil-model")
        self.assertFalse(denied["allowed"])
        self.assertIn("白名单", denied["reason"])

    def test_budget_control(self):
        self.guard.set_budget("user_b", 500)
        ok = self.guard.check_call("agent1", "user_b", budget_tokens=300)
        self.assertTrue(ok["allowed"])
        denied = self.guard.check_call("agent1", "user_b", budget_tokens=300)
        self.assertFalse(denied["allowed"])
        self.assertIn("预算", denied["reason"])

    def test_reset_rate(self):
        for i in range(3):
            self.guard.check_call("agent1", "user1")
        self.assertFalse(self.guard.check_call("agent1", "user1")["allowed"])
        self.guard.reset_rate("agent1", "user1")
        self.assertTrue(self.guard.check_call("agent1", "user1")["allowed"])

    def test_validate_output_credential_detection(self):
        result = self.guard.validate_output(
            "我的配置是 password=secret123 请勿泄露")
        self.assertFalse(result["safe"])
        self.assertTrue(any("凭据" in i for i in result["issues"]))
        self.assertNotIn("secret123", result["content"])

    def test_validate_output_internal_ip(self):
        result = self.guard.validate_output("服务器地址 http://192.168.1.10")
        self.assertFalse(result["safe"])
        self.assertTrue(any("IP" in i for i in result["issues"]))

    def test_validate_output_length_limit(self):
        self.guard.max_output_len = 100
        result = self.guard.validate_output("x" * 200)
        self.assertFalse(result["safe"])
        self.assertEqual(len(result["content"]), 100)

    def test_validate_output_clean_content(self):
        result = self.guard.validate_output("函数的单调性是正常教学内容，无敏感信息。")
        self.assertTrue(result["safe"])
        self.assertEqual(result["issues"], [])

    def test_estimate_tokens(self):
        # 10 个中文字 + 2 个英文词
        self.assertEqual(self.guard.estimate_tokens("一二三四五六七八九十 abc def"), 12)

    def test_get_safety_guard_singleton(self):
        g1 = get_safety_guard()
        g2 = get_safety_guard()
        self.assertIs(g1, g2)

    def test_check_agent_call_helper(self):
        result = check_agent_call("agent_x", "user_x")
        self.assertIn("allowed", result)


# ================================================================
# 二、AgentTelemetry 测试
# ================================================================
class TestAgentTelemetry(unittest.TestCase):
    """可观测性测试"""

    def setUp(self):
        reset_telemetry()
        self.tele = AgentTelemetry(buffer_size=100)

    def test_start_end_trace(self):
        tid = self.tele.start_trace("user1", "topic1")
        self.assertIsNotNone(tid)
        trace = self.tele.end_trace(tid)
        self.assertIsNotNone(trace)
        self.assertIn("summary", trace)
        self.assertEqual(trace["summary"]["call_count"], 0)

    def test_record_call(self):
        tid = self.tele.start_trace("user1")
        self.tele.record_call(tid, "feynman", "qwen2.5:7b",
                              latency_ms=100, input_tokens=100,
                              output_tokens=200, success=True)
        self.tele.record_call(tid, "verifier", "qwen2.5:7b",
                              latency_ms=50, input_tokens=50,
                              output_tokens=10, success=False, error="err")
        trace = self.tele.end_trace(tid)
        self.assertEqual(trace["summary"]["call_count"], 2)
        self.assertEqual(trace["summary"]["error_count"], 1)
        self.assertGreater(trace["summary"]["total_cost"], 0)

    def test_cost_calculation(self):
        cost_info = self.tele.trace_cost("qwen2.5:7b", 1000, 1000)
        # 0.001 元/千token × 2000
        self.assertEqual(cost_info["cost"], 0.002)

    def test_get_calls_filter(self):
        tid = self.tele.start_trace("u1")
        self.tele.record_call(tid, "agent_a", "m1", success=True)
        self.tele.record_call(tid, "agent_b", "m2", success=True)
        self.tele.end_trace(tid)
        calls_a = self.tele.get_calls(agent_id="agent_a")
        self.assertEqual(len(calls_a), 1)
        self.assertEqual(calls_a[0]["agent_id"], "agent_a")

    def test_cost_summary_by_model(self):
        tid = self.tele.start_trace("u1")
        self.tele.record_call(tid, "a", "m1", input_tokens=1000, output_tokens=1000)
        self.tele.record_call(tid, "b", "m2", input_tokens=1000, output_tokens=1000)
        self.tele.end_trace(tid)
        summary = self.tele.get_cost_summary()
        self.assertEqual(summary["total_calls"], 2)
        self.assertIn("m1", summary["by_model"])

    def test_audit_log_writes(self):
        row_id = self.tele.audit_log("info", "测试审计", "detail")
        self.assertGreaterEqual(row_id, 0)
        self.assertGreater(self.tele.get_stats()["total_calls"] + 0, -1)

    def test_human_interrupt_flow(self):
        """人工中断完整流程：请求 → 待审批 → 审批"""
        tid = self.tele.start_trace("u1")
        r = self.tele.request_interrupt(tid, "内容需人工审核", node="verifier")
        self.assertTrue(r["interrupted"])
        pending = self.tele.get_pending_interrupts()
        self.assertEqual(len(pending), 1)
        # 审批通过
        resolved = self.tele.resolve_interrupt(tid, "approved", "teacher1")
        self.assertEqual(resolved["decision"], "approved")
        # 不再待审批
        self.assertEqual(len(self.tele.get_pending_interrupts()), 0)

    def test_interrupt_marker_in_trace(self):
        tid = self.tele.start_trace("u1")
        self.tele.request_interrupt(tid, "人工介入")
        self.tele.end_trace(tid)
        self.assertIn("interrupted", self.tele.stats)
        self.assertGreaterEqual(self.tele.stats["interrupted"], 1)

    def test_measure_context_manager(self):
        tid = self.tele.start_trace("u1")
        with self.tele.measure(tid, "agent_test"):
            import time as _t
            _t.sleep(0.01)
        trace = self.tele.end_trace(tid)
        self.assertEqual(trace["summary"]["call_count"], 1)
        self.assertGreaterEqual(trace["summary"]["total_latency_ms"], 10)

    def test_get_telemetry_singleton(self):
        t1 = get_telemetry()
        t2 = get_telemetry()
        self.assertIs(t1, t2)


# ================================================================
# 三、UnifiedOrchestrator 人工中断机制测试
# ================================================================
class TestOrchestratorHumanInLoop(unittest.TestCase):
    """人工中断机制集成测试"""

    def setUp(self):
        reset_telemetry()
        reset_safety_guard()
        self.orch = UnifiedOrchestrator()

    def test_interrupt_and_resume(self):
        r = self.orch.interrupt("检测到高风险内容", node="verifier")
        self.assertTrue(r["interrupted"])
        tid = r["trace_id"]
        pending = self.orch.get_pending_interrupts()
        self.assertEqual(len(pending), 1)
        resolved = self.orch.resume("approved", "admin", trace_id=tid)
        self.assertEqual(resolved["decision"], "approved")
        self.assertEqual(len(self.orch.get_pending_interrupts()), 0)

    def test_interrupt_reject(self):
        r = self.orch.interrupt("需要终止")
        resolved = self.orch.resume("rejected", "admin", trace_id=r["trace_id"])
        self.assertEqual(resolved["decision"], "rejected")

    def test_run_integrates_telemetry_and_safety(self):
        """run() 集成追踪 + 安全检查"""
        # 模拟内部路径避免真实模型调用
        with patch.object(self.orch.router, 'route') as mock_route, \
             patch.object(self.orch, '_run_simple') as mock_simple, \
             patch.object(self.orch.safety, 'estimate_tokens', return_value=10):
            mock_route.return_value = {
                "route": "simple",
                "profile": {"complexity": "simple", "reasoning_type": "sequential",
                            "subject": "综合", "topic": "t", "estimated_calls": 1,
                            "confidence": 0.8},
            }
            mock_simple.return_value = {
                "success": True, "teaching": {"full_content": "正常内容"},
            }
            result = self.orch.run({"topic": "什么是函数", "user_id": 1})
            self.assertIn("trace_id", result)
            self.assertTrue(result["success"])
            # 追踪应已记录
            self.assertGreater(self.orch.telemetry.get_stats()["total_calls"], 0)


if __name__ == "__main__":
    unittest.main()
