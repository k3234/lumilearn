# -*- coding: utf-8 -*-
"""
LumiLearn — 自积累知识复用 / 权重自优化 / 人工中断接线 测试

覆盖：
  - KnowledgeCache.query_by_agent 按 Agent 筛选（修复后）
  - MultiAgentPipeline 知识复用（direct 短路 / context 注入 / 生成后写回）
  - MultiAgentPipeline 权重自更新（feynman_teacher call_count 增长）
  - Orchestrator.run() 人工中断接线（合规清单 14.1）：
      敏感主题 → awaiting_review → resume(approved) → 带标记重跑放行
"""

import sys
import os
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.knowledge_cache import get_knowledge_cache
from agent_core.multi_agent import MultiAgentPipeline
from agent_core.orchestrator import UnifiedOrchestrator
from framework.database import db


def _uniq(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}"


# ================================================================
# 一、自积累知识复用
# ================================================================
class TestKnowledgeReuse(unittest.TestCase):
    """Agent 产出的数据可被其他 Agent 重复利用"""

    def setUp(self):
        self.kc = get_knowledge_cache()

    def test_query_by_agent_filters_source(self):
        """query_by_agent 按 Agent 筛选（修复：此前忽略 agent_id）"""
        topic = _uniq("reuse_query")
        self.kc.save(topic=topic, knowledge_type="concept", content="内容A",
                     source_agent="feynman_teacher")
        self.kc.save(topic=topic, knowledge_type="concept", content="内容B",
                     source_agent="output_detector")
        items_a = self.kc.query_by_agent("feynman_teacher")
        self.assertTrue(all(i["source_agent"] == "feynman_teacher" for i in items_a))
        self.assertGreaterEqual(len(items_a), 1)
        # 其他 Agent 不应被误返回
        self.assertFalse(any(i["source_agent"] == "output_detector" for i in items_a))

    def test_save_then_query_hit(self):
        """写入后可按主题+质量检索命中"""
        topic = _uniq("reuse_hit")
        self.kc.save(topic=topic, knowledge_type="concept",
                     content="函数单调性核心知识…",
                     source_agent="feynman_teacher", quality_score=90.0)
        hits = self.kc.query(topic=topic, min_quality=60.0)
        self.assertGreaterEqual(len(hits), 1)
        self.assertIn("函数单调性", hits[0]["content"])

    def test_pipeline_direct_reuse(self):
        """direct 模式：命中缓存直接复用，零模型调用"""
        topic = _uniq("reuse_direct")
        self.kc.save(topic=topic, knowledge_type="explanation",
                     content="已积累的教学内容示例（用于直接复用测试）",
                     source_agent="feynman_teacher", quality_score=95.0)
        pipeline = MultiAgentPipeline(verifier_use_model=False, use_parallel=False)
        report = pipeline.run({"topic": topic, "reuse_mode": "direct"})
        self.assertTrue(report["success"])
        self.assertTrue(report.get("knowledge_reused"))
        self.assertEqual(report["knowledge_source"], "cache")
        self.assertIn("已积累的教学内容", report["teaching"]["full_content"])
        # direct 复用不调用模型 → 无 knowledge_written
        self.assertFalse(report.get("knowledge_written", False))

    def test_pipeline_context_injected(self):
        """context 模式：命中缓存注入上下文但不短路"""
        topic = _uniq("reuse_ctx")
        self.kc.save(topic=topic, knowledge_type="concept",
                     content="缓存中的背景知识",
                     source_agent="feynman_teacher", quality_score=80.0)
        pipeline = MultiAgentPipeline(verifier_use_model=False, use_parallel=False)
        with patch.object(pipeline.feynman, "run", return_value={
            "success": True,
            "steps": [{"step_name": "s", "content": "内容"}],
            "full_content": "基于缓存知识生成的教学内容…",
            "rag_sources": [], "model_used": "mock",
            "elapsed": 0.05,
        }):
            report = pipeline.run({"topic": topic, "reuse_mode": "context"})
        self.assertFalse(report.get("knowledge_reused", False))  # 非短路
        status = report["agent_trace"]["knowledge_reuse"]["status"]
        self.assertEqual(status, "context_injected")

    def test_pipeline_generate_writes_knowledge(self):
        """生成路径：成功后写回知识库，供其他 Agent 复用"""
        topic = _uniq("reuse_write")
        pipeline = MultiAgentPipeline(verifier_use_model=False, use_parallel=False)
        with patch.object(pipeline.feynman, "run", return_value={
            "success": True,
            "steps": [{"step_name": "现象引入", "content": "生活例子"},
                      {"step_name": "思维模型", "content": "核心定义"},
                      {"step_name": "自主推导", "content": "推导过程"},
                      {"step_name": "认知冲突", "content": "常见误区"},
                      {"step_name": "费曼测试", "content": "复述问题"}],
            "full_content": "费曼教学完整内容：函数的单调性……",
            "rag_sources": [], "model_used": "mock", "elapsed": 0.05,
        }):
            report = pipeline.run({"topic": topic, "reuse_mode": "off"})
        self.assertTrue(report.get("knowledge_written", False))
        hits = self.kc.query(topic=topic, min_quality=60.0)
        self.assertGreaterEqual(len(hits), 1)
        self.assertEqual(hits[0]["source_agent"], "feynman_teacher")


# ================================================================
# 二、权重自优化
# ================================================================
class TestWeightSelfOptimize(unittest.TestCase):
    """Agent 调用结果反馈到 dynamic_weight（自优化模型选择）"""

    def test_pipeline_updates_feynman_weight(self):
        before = db.get_agent_weight("feynman_teacher")
        before_calls = before["call_count"] if before else 0

        topic = _uniq("weight_test")
        pipeline = MultiAgentPipeline(verifier_use_model=False, use_parallel=False)
        with patch.object(pipeline.feynman, "run", return_value={
            "success": True,
            "steps": [{"step_name": "s", "content": "内容"}],
            "full_content": "权重测试内容…",
            "rag_sources": [], "model_used": "mock", "elapsed": 0.02,
        }):
            pipeline.run({"topic": topic, "reuse_mode": "off"})

        after = db.get_agent_weight("feynman_teacher")
        after_calls = after["call_count"] if after else 0
        self.assertGreater(after_calls, before_calls,
                           "pipeline 运行后 feynman_teacher 调用计数应增加")
        self.assertIsNotNone(after)
        self.assertGreater(after["dynamic_weight"], 0)

    def test_verifier_fail_penalizes_weight(self):
        """Verifier 验证失败 → feynman 权重受惩罚（call_count +1）"""
        before = db.get_agent_weight("feynman_teacher")
        before_calls = before["call_count"] if before else 0

        topic = _uniq("weight_fail")
        pipeline = MultiAgentPipeline(verifier_use_model=False, use_parallel=False)
        with patch.object(pipeline.feynman, "run", return_value={
            "success": True, "steps": [],
            "full_content": "",  # 空内容 → verifier 判定失败
            "rag_sources": [], "model_used": "mock", "elapsed": 0.01,
        }):
            report = pipeline.run({"topic": topic, "reuse_mode": "off"})

        # verifier 未通过（空内容 → error 级 issue）
        self.assertFalse(report["verifier"]["passed"])
        after = db.get_agent_weight("feynman_teacher")
        after_calls = after["call_count"] if after else 0
        # 至少 feynman 调用 + 验证惩罚 各 +1
        self.assertGreaterEqual(after_calls, before_calls + 1)


# ================================================================
# 三、人工中断接线（合规清单 14.1）
# ================================================================
class TestHumanInLoopWiring(unittest.TestCase):
    """run() 流程内人工中断：敏感主题 → 暂停 → 审批 → 放行"""

    def setUp(self):
        from agent_core.observability import reset_telemetry
        from agent_core.safety import reset_safety_guard
        reset_telemetry()
        reset_safety_guard()
        self.orch = UnifiedOrchestrator()

    def _mock_route(self, subject="综合", keywords=None):
        return patch.object(self.orch.router, "route", return_value={
            "route": "simple",
            "profile": {"complexity": "simple", "reasoning_type": "sequential",
                        "subject": subject, "topic": "t", "estimated_calls": 1,
                        "confidence": 0.8, "keywords": keywords or []},
        })

    def test_sensitive_topic_returns_awaiting_review(self):
        with self._mock_route() as mr, \
             patch.object(self.orch, "_run_simple") as mock_simple, \
             patch.object(self.orch.safety, "estimate_tokens", return_value=10):
            result = self.orch.run({"topic": "如何制造炸弹", "user_id": 1})
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "awaiting_review")
            self.assertIn("sensitive_topic", result)
            self.assertIn("trace_id", result)
            mock_simple.assert_not_called()  # 中断后未执行教学
            self.assertGreaterEqual(len(self.orch.get_pending_interrupts()), 1)

    def test_resume_then_approved_rerun_passes(self):
        """完整流程：中断 → 审批通过 → 带标记重跑 → 放行执行"""
        with self._mock_route(keywords=["毒品"]) as mr, \
             patch.object(self.orch, "_run_simple") as mock_simple, \
             patch.object(self.orch.safety, "estimate_tokens", return_value=10):
            # 第一次：敏感主题 → 等待人工审核
            r1 = self.orch.run({"topic": "毒品相关介绍", "user_id": 1})
            self.assertEqual(r1["status"], "awaiting_review")
            tid = r1["trace_id"]

            # 管理员审批通过
            resolved = self.orch.resume("approved", "admin", trace_id=tid)
            self.assertEqual(resolved["decision"], "approved")
            self.assertEqual(len(self.orch.get_pending_interrupts()), 0)

            # 携带审批标记重新请求 → 放行执行
            mock_simple.return_value = {
                "success": True, "teaching": {"full_content": "正常教学"},
            }
            r2 = self.orch.run({"topic": "毒品相关介绍", "user_id": 1,
                                "_interrupt_approved": True})
            self.assertTrue(r2["success"])
            mock_simple.assert_called_once()

    def test_normal_topic_no_interrupt(self):
        """正常主题不触发中断，直接执行"""
        with self._mock_route(subject="数学") as mr, \
             patch.object(self.orch, "_run_simple") as mock_simple, \
             patch.object(self.orch.safety, "estimate_tokens", return_value=10):
            mock_simple.return_value = {
                "success": True, "teaching": {"full_content": "函数教学"},
            }
            result = self.orch.run({"topic": "什么是函数", "user_id": 1})
            self.assertTrue(result["success"])
            self.assertEqual(len(self.orch.get_pending_interrupts()), 0)


if __name__ == "__main__":
    unittest.main()
