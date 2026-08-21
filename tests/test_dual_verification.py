# -*- coding: utf-8 -*-
"""
LumiLearn — 双路校验机制测试（P0-3）

覆盖：
  - FactCheckerAgent.verify_question 题目规范校验（合法 / 缺字段 / 空值）
  - verifier.dual_verify fail-open（模型抛异常 → 放行不崩溃）
  - verifier.dual_verify 判定（校验模型返回不合格 JSON → passed=False）

完全离线运行：所有模型调用均通过 unittest.mock.patch 替换。
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.verifier import dual_verify
from agent_core.fact_checker import FactCheckerAgent


# ================================================================
# 一、verify_question 题目规范校验
# ================================================================
class TestVerifyQuestion(unittest.TestCase):
    """题目 dict 是否符合规范：字段齐全 / answer 在 options 中 / 非空"""

    @staticmethod
    def _valid_question() -> dict:
        return {
            "question": "1 + 1 等于几？",
            "answer": "2",
            "explanation": "基础算术运算",
            "options": ["1", "2", "3", "4"],
        }

    def test_verify_question_valid(self):
        """合法题目（字段齐全、answer 在 options 中）→ True"""
        self.assertTrue(FactCheckerAgent.verify_question(self._valid_question()))

    def test_verify_question_invalid(self):
        """缺字段 / answer 不在 options / 空值 / 非 dict → False"""
        # 缺 explanation 字段
        q = self._valid_question()
        del q["explanation"]
        self.assertFalse(FactCheckerAgent.verify_question(q))

        # answer 不在 options 中
        q = self._valid_question()
        q["answer"] = "5"
        self.assertFalse(FactCheckerAgent.verify_question(q))

        # 空 question
        q = self._valid_question()
        q["question"] = "   "
        self.assertFalse(FactCheckerAgent.verify_question(q))

        # options 为空列表
        q = self._valid_question()
        q["options"] = []
        self.assertFalse(FactCheckerAgent.verify_question(q))

        # 非 dict 输入
        self.assertFalse(FactCheckerAgent.verify_question({}))
        self.assertFalse(FactCheckerAgent.verify_question(None))


# ================================================================
# 二、dual_verify 双路校验
# ================================================================
class TestDualVerify(unittest.TestCase):
    """双路校验：fail-open 兜底与不合格判定"""

    def test_dual_verify_model_unavailable(self):
        """校验模型调用抛异常 → fail-open 返回（passed=True, confidence=50）"""
        failing = MagicMock()
        failing.call.side_effect = RuntimeError("ollama 服务不可用")
        with patch("agent_core.verifier.get_model", return_value=failing):
            result = dual_verify("待复核内容", "请复核准确性")
        self.assertTrue(result["passed"])
        self.assertEqual(result["confidence"], 50)
        self.assertEqual(result["reason"], "校验模型不可用，跳过复核")

        # get_model 本身抛异常也应 fail-open
        with patch("agent_core.verifier.get_model",
                   side_effect=RuntimeError("模型注册表不可用")):
            result = dual_verify("待复核内容", "请复核准确性")
        self.assertTrue(result["passed"])
        self.assertEqual(result["confidence"], 50)
        self.assertEqual(result["reason"], "校验模型不可用，跳过复核")

    def test_dual_verify_rejects(self):
        """校验模型返回不合格 JSON → passed=False（不放行不合格内容）"""
        rejecting = MagicMock()
        rejecting.call.return_value = (
            '{"passed": false, "confidence": 30, '
            '"issues": ["答案与题目不匹配"], "reason": "存在明显错误"}'
        )
        with patch("agent_core.verifier.get_model", return_value=rejecting):
            result = dual_verify("待复核内容", "请复核准确性")
        self.assertFalse(result["passed"])
        self.assertEqual(result["confidence"], 30)
        self.assertGreaterEqual(len(result["issues"]), 1)
        self.assertEqual(result["reason"], "存在明显错误")

    def test_dual_verify_accepts(self):
        """校验模型返回合格 JSON → passed=True（复核通过）"""
        accepting = MagicMock()
        accepting.call.return_value = (
            '{"passed": true, "confidence": 90, '
            '"issues": [], "reason": "内容准确，复核通过"}'
        )
        with patch("agent_core.verifier.get_model", return_value=accepting):
            result = dual_verify("待复核内容", "请复核准确性")
        self.assertTrue(result["passed"])
        self.assertEqual(result["confidence"], 90)


if __name__ == "__main__":
    unittest.main()
