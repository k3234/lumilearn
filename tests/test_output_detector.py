#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 OutputDetector
覆盖：初始化、单次检测、检测报告生成、引导式强化、规则评分、历史记录
"""
import os
import sys

import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.output_detector import (
    OutputDetector,
    DetectionResult,
    GuidingRound,
    detect_output,
    run_guided_reinforcement,
    SCORING_DIMENSIONS,
)


class TestOutputDetectorInit(unittest.TestCase):
    """OutputDetector 初始化测试"""

    def setUp(self):
        db.init()

    def test_init_default_params(self):
        detector = OutputDetector(user_id=2)
        self.assertEqual(detector.user_id, 2)
        self.assertEqual(detector.model_name, "qwen2.5:7b")

    def test_init_custom_params(self):
        detector = OutputDetector(
            user_id=3,
            workflow_id="wf_123",
            model_name="llama3.2",
            timeout=30,
        )
        self.assertEqual(detector.user_id, 3)
        self.assertEqual(detector.workflow_id, "wf_123")
        self.assertEqual(detector.model_name, "llama3.2")
        self.assertEqual(detector.timeout, 30)


class TestOutputDetectorRunDetection(unittest.TestCase):
    """单次检测测试"""

    def setUp(self):
        db.init()

    def test_run_detection_empty_output(self):
        detector = OutputDetector(user_id=2001)
        result = detector.run_detection("勾股定理", "")
        self.assertEqual(result.total_score, 0)
        self.assertFalse(result.is_mastered)

    def test_run_detection_with_content(self):
        detector = OutputDetector(user_id=2001)
        output = "勾股定理是说直角三角形两直角边的平方和等于斜边的平方，也就是a²+b²=c²"
        result = detector.run_detection("勾股定理", output)
        self.assertIsInstance(result, DetectionResult)
        self.assertEqual(result.concept, "勾股定理")
        self.assertGreaterEqual(result.total_score, 0)
        self.assertLessEqual(result.total_score, 100)
        self.assertIsInstance(result.feedback, str)

    def test_run_detection_stores_history(self):
        detector = OutputDetector(user_id=2001)
        detector.run_detection("勾股定理", "测试输出内容")
        self.assertEqual(len(detector.detection_history), 1)
        self.assertEqual(detector.detection_history[0]["concept"], "勾股定理")

    def test_detection_result_structure(self):
        detector = OutputDetector(user_id=2001)
        result = detector.run_detection("测试概念", "这是一个测试输出，内容比较长")
        self.assertTrue(hasattr(result, 'concept'))
        self.assertTrue(hasattr(result, 'student_output'))
        self.assertTrue(hasattr(result, 'total_score'))
        self.assertTrue(hasattr(result, 'dimensions'))
        self.assertTrue(hasattr(result, 'feedback'))
        self.assertTrue(hasattr(result, 'is_mastered'))


class TestOutputDetectorReport(unittest.TestCase):
    """检测报告生成测试"""

    def setUp(self):
        db.init()

    def test_generate_report_basic(self):
        detector = OutputDetector(user_id=2)
        result = detector.run_detection("勾股定理", "直角三角形边长关系，a方加b方等于c方")
        report = detector.generate_detection_report(result)
        self.assertIn("concept", report)
        self.assertIn("total_score", report)
        self.assertIn("is_mastered", report)
        self.assertIn("level", report)

    def test_report_level_excellent(self):
        detector = OutputDetector(user_id=2)
        result = DetectionResult(
            concept="勾股定理",
            student_output="好理解",
            total_score=95,
            is_mastered=True,
        )
        report = detector.generate_detection_report(result)
        self.assertEqual(report["level"], "优秀")

    def test_report_level_good(self):
        detector = OutputDetector(user_id=2)
        result = DetectionResult(
            concept="测试",
            student_output="一般",
            total_score=75,
            is_mastered=True,
        )
        report = detector.generate_detection_report(result)
        self.assertEqual(report["level"], "良好")

    def test_report_level_weak(self):
        detector = OutputDetector(user_id=2)
        result = DetectionResult(
            concept="测试",
            student_output="短",
            total_score=30,
            is_mastered=False,
        )
        report = detector.generate_detection_report(result)
        self.assertEqual(report["level"], "需加强")


class TestOutputDetectorGuidedReinforcement(unittest.TestCase):
    """引导式强化测试"""

    def setUp(self):
        db.init()

    def test_guided_reinforcement_basic(self):
        detector = OutputDetector(user_id=2)
        result = detector.run_guided_reinforcement(
            concept="勾股定理",
            student_output="a²+b²=c²就是两个小边平方加起来等于大边平方",
            max_rounds=2,
            threshold=70,
        )
        self.assertIn("concept", result)
        self.assertIn("initial_score", result)
        self.assertIn("final_score", result)
        self.assertIn("is_mastered", result)
        self.assertIn("rounds", result)
        self.assertIsInstance(result["rounds"], list)

    def test_guided_reinforcement_stops_at_threshold(self):
        detector = OutputDetector(user_id=2)
        result = detector.run_guided_reinforcement(
            concept="勾股定理",
            student_output="勾股定理是直角三角形两直角边的平方和等于斜边平方，非常基础且准确",
            max_rounds=5,
            threshold=70,
        )
        self.assertIn("final_score", result)
        self.assertGreaterEqual(result["final_score"], 0)


class TestOutputDetectorGapIdentification(unittest.TestCase):
    """差距识别测试"""

    def setUp(self):
        db.init()

    def test_identify_gap_empty_dimensions(self):
        detector = OutputDetector(user_id=2001)
        result = DetectionResult(
            concept="测试",
            student_output="",
            total_score=0,
            is_mastered=False,
        )
        gap = detector._identify_gap(result)
        self.assertEqual(gap["weak_dimension"], "综合")
        self.assertEqual(gap["priority"], "high")

    def test_identify_gap_with_dimensions(self):
        detector = OutputDetector(user_id=2)
        from framework.output_detector import DimensionScore
        result = DetectionResult(
            concept="测试",
            student_output="内容",
            total_score=50,
            is_mastered=False,
            dimensions=[
                DimensionScore(name="简洁度", key="conciseness", score=5, comment="太啰嗦"),
                DimensionScore(name="准确度", key="accuracy", score=15, comment="尚可"),
            ],
        )
        gap = detector._identify_gap(result)
        self.assertEqual(gap["weak_dimension"], "简洁度")
        self.assertIn("gap_description", gap)


class TestOutputDetectorDatabase(unittest.TestCase):
    """数据库持久化测试"""

    def setUp(self):
        db.init()

    def test_save_to_database(self):
        detector = OutputDetector(user_id=2, workflow_id="db_test_wf")
        result = detector.run_detection("勾股定理", "a²+b²=c²")
        self.assertGreaterEqual(result.total_score, 0)

        detections = db.get_user_detections(user_id=2)
        self.assertGreaterEqual(len(detections), 1)

    def test_get_detection_summary(self):
        detector = OutputDetector(user_id=3)
        detector.run_detection("概念A", "输出A")
        detector.run_detection("概念B", "输出B")

        summary = detector.get_user_detection_summary()
        self.assertIn("total_detections", summary)
        self.assertGreaterEqual(summary["total_detections"], 2)
        self.assertIn("avg_score", summary)


class TestOutputDetectorHistory(unittest.TestCase):
    """历史记录测试"""

    def setUp(self):
        db.init()

    def test_get_detection_history(self):
        detector = OutputDetector(user_id=2)
        for i in range(5):
            detector.run_detection(f"概念{i}", f"输出{i}")
        history = detector.get_detection_history()
        self.assertEqual(len(history), 5)

    def test_get_detection_history_limit(self):
        detector = OutputDetector(user_id=2)
        for i in range(10):
            detector.run_detection(f"概念{i}", f"输出{i}")
        history = detector.get_detection_history(limit=5)
        self.assertEqual(len(history), 5)


class TestOutputDetectorRuleBasedScoring(unittest.TestCase):
    """规则评分测试"""

    def setUp(self):
        db.init()

    def test_rule_based_score_conciseness(self):
        detector = OutputDetector(user_id=2)
        short_output = "短"
        result = detector._rule_based_score("测试", short_output)
        self.assertIn("score", result)
        self.assertIn("dimensions", result)

    def test_rule_based_score_full_dimensions(self):
        detector = OutputDetector(user_id=2)
        result = detector._rule_based_score("测试", "这是一个测试输出内容")
        dims = result["dimensions"]
        self.assertIn("conciseness", dims)
        self.assertIn("accuracy", dims)
        self.assertIn("analogy", dims)
        self.assertIn("completeness", dims)
        self.assertIn("jargon_free", dims)


class TestOutputDetectorGenerateGuideQuestion(unittest.TestCase):
    """引导问题生成测试"""

    def setUp(self):
        db.init()

    def test_generate_question_conciseness(self):
        detector = OutputDetector(user_id=2001)
        gap = {"weak_dimension": "简洁度", "gap_description": "太啰嗦"}
        question = detector._generate_guide_question("勾股定理", gap)
        self.assertIn("勾股定理", question)
        self.assertLessEqual(len(question), 100)

    def test_generate_question_analogy(self):
        detector = OutputDetector(user_id=2001)
        gap = {"weak_dimension": "比喻", "gap_description": "缺乏比喻"}
        question = detector._generate_guide_question("勾股定理", gap)
        self.assertIn("就像", question)


class TestOutputDetectorDetectFunction(unittest.TestCase):
    """便捷函数测试"""

    def setUp(self):
        db.init()

    def test_detect_output_function(self):
        result = detect_output(
            user_id=2,
            concept="勾股定理",
            student_output="a²+b²=c²",
            detection_type="quiz",
        )
        self.assertIsInstance(result, DetectionResult)
        self.assertEqual(result.concept, "勾股定理")

    def test_run_guided_reinforcement_function(self):
        result = run_guided_reinforcement(
            user_id=2,
            concept="勾股定理",
            student_output="测试输出",
            max_rounds=1,
        )
        self.assertIn("concept", result)
        self.assertIn("initial_score", result)
        self.assertIn("final_score", result)


class TestScoringDimensions(unittest.TestCase):
    """评分维度定义测试"""

    def test_dimensions_defined(self):
        self.assertIn("简洁度", SCORING_DIMENSIONS)
        self.assertIn("准确度", SCORING_DIMENSIONS)
        self.assertIn("比喻", SCORING_DIMENSIONS)
        self.assertIn("完整度", SCORING_DIMENSIONS)
        self.assertIn("术语规避", SCORING_DIMENSIONS)

    def test_dimension_weights(self):
        total_weight = sum(d["weight"] for d in SCORING_DIMENSIONS.values())
        self.assertEqual(total_weight, 100)

    def test_dimension_keys(self):
        keys = [d["key"] for d in SCORING_DIMENSIONS.values()]
        self.assertIn("conciseness", keys)
        self.assertIn("accuracy", keys)
        self.assertIn("analogy", keys)
        self.assertIn("completeness", keys)
        self.assertIn("jargon_free", keys)


if __name__ == "__main__":
    unittest.main()
