# -*- coding: utf-8 -*-
"""
Trace + 自动评测闭环 — 单元测试

覆盖 agent_core.observability.AgentTelemetry.eval_metrics 的指标计算，
以及 framework.database 的 system_eval 表读写闭环。

依赖 tests/conftest.py 的 autouse fixture isolated_db：
每个用例使用独立临时 SQLite 库，完全离线、不加载模型。
"""
import unittest

from agent_core.observability import get_telemetry
from framework.database import db


class TestEvalMetrics(unittest.TestCase):
    """eval_metrics 指标计算测试"""

    def setUp(self):
        self.tele = get_telemetry()

    def test_eval_metrics_recall(self):
        """部分召回 → 召回率等于交集/期望的正确比例"""
        metrics = self.tele.eval_metrics(
            expected_knowledge=["函数", "导数", "积分", "极限"],
            recalled_knowledge=["函数", "导数", "数列"],
            generated_questions=[],
            wrong_detected=0,
            wrong_actual=0,
        )
        # 交集 {函数, 导数} = 2，期望 4 个 → 0.5
        self.assertAlmostEqual(metrics["knowledge_recall"], 2 / 4)
        self.assertAlmostEqual(metrics["knowledge_recall"], 0.5)

    def test_eval_metrics_empty_expected(self):
        """期望知识点为空 → 召回率为 1.0"""
        metrics = self.tele.eval_metrics(
            expected_knowledge=[],
            recalled_knowledge=["函数"],
            generated_questions=[],
            wrong_detected=0,
            wrong_actual=0,
        )
        self.assertEqual(metrics["knowledge_recall"], 1.0)

    def test_eval_metrics_format_pass(self):
        """含/缺 question/answer/options 字段的题目 → 正确合格率"""
        questions = [
            {"question": "Q1", "answer": "A", "options": ["A", "B"]},
            {"question": "Q2", "answer": "B"},  # 缺 options
            {"question": "Q3", "answer": "C", "options": ["A", "C"]},
            "not-a-dict",  # 非法题目
        ]
        metrics = self.tele.eval_metrics(
            expected_knowledge=["函数"],
            recalled_knowledge=["函数"],
            generated_questions=questions,
            wrong_detected=0,
            wrong_actual=0,
        )
        # 4 题中 2 题合格 → 0.5
        self.assertAlmostEqual(metrics["format_pass_rate"], 2 / 4)
        self.assertAlmostEqual(metrics["format_pass_rate"], 0.5)

    def test_eval_metrics_accuracy(self):
        """检测错题数与实际错题数 → 正确准确率"""
        metrics = self.tele.eval_metrics(
            expected_knowledge=[],
            recalled_knowledge=[],
            generated_questions=[],
            wrong_detected=2,
            wrong_actual=4,
        )
        # accuracy = 1 - |2 - 4| / max(4, 1) = 1 - 0.5 = 0.5
        self.assertAlmostEqual(metrics["accuracy"], 0.5)

        # 检测数与实际数完全一致 → 1.0
        metrics_exact = self.tele.eval_metrics(
            expected_knowledge=[],
            recalled_knowledge=[],
            generated_questions=[],
            wrong_detected=3,
            wrong_actual=3,
        )
        self.assertEqual(metrics_exact["accuracy"], 1.0)


class TestEvalReports(unittest.TestCase):
    """system_eval 报告读写测试"""

    def test_save_and_get_reports(self):
        """写入评测报告后能完整读回"""
        report_id = db.save_eval_report(
            eval_type="quiz",
            recall_rate=0.8,
            format_pass_rate=1.0,
            accuracy=0.75,
            trace_id="trace_eval_test",
            detail_json='{"questions": 10}',
        )
        self.assertGreater(report_id, 0)

        reports = db.get_eval_reports()
        self.assertEqual(len(reports), 1)
        report = reports[0]
        self.assertEqual(report["eval_type"], "quiz")
        self.assertAlmostEqual(report["recall_rate"], 0.8)
        self.assertAlmostEqual(report["format_pass_rate"], 1.0)
        self.assertAlmostEqual(report["accuracy"], 0.75)
        self.assertEqual(report["trace_id"], "trace_eval_test")
        self.assertEqual(report["detail_json"], '{"questions": 10}')

        # 写入第二条后，最新优先返回
        db.save_eval_report("exam", 0.5, 0.6, 0.7, trace_id="trace2")
        reports2 = db.get_eval_reports(limit=1)
        self.assertEqual(len(reports2), 1)
        self.assertEqual(reports2[0]["eval_type"], "exam")
        self.assertEqual(reports2[0]["trace_id"], "trace2")


if __name__ == "__main__":
    unittest.main()
