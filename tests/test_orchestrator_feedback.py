# -*- coding: utf-8 -*-
"""
UnifiedOrchestrator 反馈回路 / 超时 / token 预算 — 单元测试

覆盖：
  - run_with_critique 的自我批判反馈回路（首轮通过 / 重试后通过 / 重试耗尽）
  - _call_with_timeout 教学生成阻塞超时 → 降级结果，不抛异常
  - _check_token_budget 超预算 → 降级提示

完全离线：教学生成（teach_fn）与评分（SelfCritiqueAgent + llm_scorer）全部注入 fake，
不调用任何真实 LLM。依赖 tests/conftest.py 的 autouse isolated_db fixture。
"""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.orchestrator import UnifiedOrchestrator
from agent_core.self_critique import SelfCritiqueAgent


class FakeTeacher:
    """可配置输出序列的 fake 教学生成器，记录调用次数。

    第 N 次调用返回 outputs[N]（超出后复用最后一个），
    返回结构与 run() 兼容（teaching.content 承载生成文本）。
    """

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    def __call__(self, topic, subject="", **kwargs):
        self.calls += 1
        idx = min(self.calls - 1, len(self.outputs) - 1)
        return {
            "success": True,
            "topic": topic,
            "subject": subject,
            "teaching": {"content": self.outputs[idx]},
        }


def make_scorer(score_map, default=30):
    """按输出文本返回固定分数的 llm_scorer（未命中返回 default）。"""

    def scorer(text, topic, ctx):
        return {"score": score_map.get(text, default)}

    return scorer


class TestCritiqueFeedback(unittest.TestCase):
    """run_with_critique 自我批判反馈回路"""

    def setUp(self):
        self.orch = UnifiedOrchestrator()

    def test_critique_pass_no_retry(self):
        """首次评分即通过 → feedback_rounds=0，无重试"""
        teacher = FakeTeacher(["good"])
        critique = SelfCritiqueAgent(llm_scorer=make_scorer({"good": 90}))
        result = self.orch.run_with_critique(
            "牛顿第二定律", subject="物理",
            teach_fn=teacher, critique_agent=critique)

        self.assertEqual(result["feedback_rounds"], 0)
        self.assertTrue(result["critique_passed"])
        self.assertEqual(result["critique_score"], 90)
        self.assertEqual(teacher.calls, 1)  # 仅首轮生成，无重试
        self.assertNotIn("critique_warning", result)

    def test_critique_fail_retries(self):
        """前两次不通过、第三次通过 → feedback_rounds=2（重试后达标）"""
        teacher = FakeTeacher(["bad1", "bad2", "good"])
        critique = SelfCritiqueAgent(
            llm_scorer=make_scorer({"good": 85}, default=40))
        result = self.orch.run_with_critique(
            "函数概念", subject="数学",
            teach_fn=teacher, critique_agent=critique)

        self.assertEqual(teacher.calls, 3)  # 1 次生成 + 2 次重试
        self.assertEqual(result["feedback_rounds"], 2)
        self.assertTrue(result["critique_passed"])
        self.assertEqual(result["critique_score"], 85)
        self.assertNotIn("critique_warning", result)

    def test_critique_fail_max_retries(self):
        """一直不通过 → 最多重试 2 次，最终 critique_warning=True 接受最佳"""
        teacher = FakeTeacher(["bad", "bad", "bad"])
        critique = SelfCritiqueAgent(llm_scorer=make_scorer({"bad": 40}))
        result = self.orch.run_with_critique(
            "光合作用", subject="生物",
            teach_fn=teacher, critique_agent=critique)

        self.assertEqual(teacher.calls, 3)  # 1 次生成 + 2 次重试后停止
        self.assertEqual(result["feedback_rounds"], 2)
        self.assertTrue(result["critique_warning"])
        self.assertFalse(result["critique_passed"])
        self.assertEqual(result["critique_score"], 40)

    def test_timeout_degraded(self):
        """教学生成阻塞超时 → 返回降级结果，不抛异常"""
        def slow_teacher(topic, subject="", **kw):
            time.sleep(5)  # 阻塞远超 timeout_s
            return {"success": True, "teaching": {"content": "太慢"}}

        t0 = time.time()
        result = self.orch.run_with_critique(
            "导数", subject="数学", teach_fn=slow_teacher, timeout_s=0.3)
        elapsed = time.time() - t0

        self.assertLess(elapsed, 3)  # 未阻塞等满 5s，已及时降级
        self.assertTrue(result.get("degraded"))
        self.assertEqual(result["reason"], "timeout")
        self.assertFalse(result["success"])
        self.assertIn("message", result)

    def test_token_budget_exceeded(self):
        """超预算 → 返回降级提示，跳过评分与重试"""
        teacher = FakeTeacher(["content"])
        critique = SelfCritiqueAgent(llm_scorer=make_scorer({"content": 90}))
        result = self.orch.run_with_critique(
            "几何", subject="数学",
            teach_fn=teacher, critique_agent=critique,
            token_budget=100,
            _prompt_tokens=10, _completion_tokens=1000,  # 合计 1010 > 100
        )

        self.assertTrue(result.get("degraded"))
        self.assertEqual(result["reason"], "token_budget_exceeded")
        self.assertEqual(result["message"], "生成内容超过 token 预算，已截断处理")
        self.assertEqual(teacher.calls, 1)  # 超预算后未重试
        self.assertEqual(result["feedback_rounds"], 0)


if __name__ == "__main__":
    unittest.main()
