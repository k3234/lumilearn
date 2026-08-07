#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端测试：LearningPipeline
测试完整学习流程：工作流启动 → 提交输出 → 输出检测 → 强化引导 → 结果归档
"""
import os
import sys

import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.workflow_engine import LearningWorkflowEngine, run_learning_workflow
from framework.output_detector import (
    OutputDetector,
    DetectionResult,
    detect_output,
    run_guided_reinforcement,
)


class TestEndToEndLearningPipeline(unittest.TestCase):
    """端到端学习流程测试"""

    def setUp(self):
        db.init()
        self.test_user_id = 2
        self.test_topic = "勾股定理"
        self.test_workflow_id = "e2e_test_wf"

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_full_workflow_pipeline(self, mock_feynman_cls):
        """测试完整工作流：启动→提交→完成"""
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "现象引入内容", "key_points": [], "animation_hint": "h1"},
                {"content": "认知冲突内容", "key_points": [], "animation_hint": "h2"},
                {"content": "思维模型内容", "key_points": [], "animation_hint": "h3"},
                {"content": "自主推导内容", "key_points": [], "animation_hint": "h4"},
                {"content": "费曼测试内容", "key_points": [], "animation_hint": "h5"},
            ]
        }
        mock_feynman_cls.return_value.thirty_second_test.return_value = {
            "score": 80, "feedback": "很好", "dimensions": {}, "is_feynman_worthy": True
        }

        # 1. 启动工作流
        engine = LearningWorkflowEngine(
            topic=self.test_topic,
            user_id=self.test_user_id,
            workflow_id=self.test_workflow_id,
        )
        start_result = engine.start_workflow()
        self.assertEqual(start_result["status"], "active")
        self.assertEqual(start_result["topic"], self.test_topic)
        self.assertEqual(start_result["total_steps"], 5)
        row_id = start_result["row_id"]

        # 2. 逐步骤提交输出
        sample_outputs = [
            "我在生活中见过勾股定理的例子，比如看屋顶的三角形结构",
            "但是为什么直角三角形才有这个关系呢？其他三角形呢？",
            "哦！我理解了，勾股定理就像是用正方形面积来比较边长关系",
            "让我推导一下，如果直角边是3和4，斜边应该是5，因为9+16=25",
            "30秒总结：勾股定理就是直角三角形两直角边的平方和等于斜边的平方",
        ]
        for i, output in enumerate(sample_outputs):
            result = engine.submit_step_output(step_order=i + 1, user_output=output)
            self.assertTrue(result["step_completed"])
            self.assertIn("score", result)

        # 3. 完成工作流
        final_result = engine.complete_workflow()
        self.assertEqual(final_result["status"], "completed")
        self.assertIsInstance(final_result["total_score"], (int, float))
        self.assertGreaterEqual(final_result["total_score"], 0)
        self.assertLessEqual(final_result["total_score"], 100)
        self.assertIsInstance(final_result["archive_id"], int)

        # 4. 验证数据库记录
        db_wf = db.get_workflow(row_id)
        self.assertIsNotNone(db_wf)
        self.assertEqual(db_wf["status"], "completed")

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_full_workflow_with_output_detection(self, mock_feynman_cls):
        """测试工作流集成输出检测"""
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }
        mock_feynman_cls.return_value.thirty_second_test.return_value = {
            "score": 75, "feedback": "不错", "dimensions": {}, "is_feynman_worthy": False
        }

        # 启动工作流
        engine = LearningWorkflowEngine(topic="牛顿第二定律", user_id=2)
        engine.start_workflow()

        # 提交所有步骤
        for i in range(1, 6):
            engine.submit_step_output(i, f"这是第{i}步的输出内容，用于测试")

        # 完成工作流
        final = engine.complete_workflow()

        # 验证检测结果已保存
        detections = db.get_user_detections(user_id=2)
        self.assertGreaterEqual(len(detections), 1)

    def test_output_detector_integration(self):
        """测试输出检测器独立工作"""
        detector = OutputDetector(user_id=3)

        # 单次检测
        result = detector.run_detection(
            concept="勾股定理",
            student_output="a²+b²=c²，直角三角形边长关系",
            detection_type="quiz",
        )
        self.assertIsInstance(result, DetectionResult)
        self.assertGreaterEqual(result.total_score, 0)
        self.assertLessEqual(result.total_score, 100)

        # 生成报告
        report = detector.generate_detection_report(result)
        self.assertIn("level", report)
        self.assertIn("total_score", report)

    def test_guided_reinforcement_integration(self):
        """测试引导式强化集成"""
        detector = OutputDetector(user_id=3)

        result = detector.run_guided_reinforcement(
            concept="勾股定理",
            student_output="就是a方加b方等于c方",
            max_rounds=2,
            threshold=70,
        )

        self.assertIn("initial_score", result)
        self.assertIn("final_score", result)
        self.assertIn("is_mastered", result)
        self.assertIsInstance(result["rounds"], list)

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_run_learning_workflow_convenience_function(self, mock_feynman_cls):
        """测试便捷函数 run_learning_workflow"""
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }

        result = run_learning_workflow(
            topic="测试主题",
            user_id=3,
            level="junior",
            auto_submit_outputs=[
                "输出1", "输出2", "输出3", "输出4", "输出5"
            ],
        )
        self.assertEqual(result["status"], "completed")
        self.assertIsInstance(result["total_score"], (int, float))
        self.assertIsInstance(result["archive_id"], int)

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_multiple_users_isolation(self, mock_feynman_cls):
        """测试多用户数据隔离"""
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }
        mock_feynman_cls.return_value.thirty_second_test.return_value = {
            "score": 70, "feedback": "ok", "dimensions": {}, "is_feynman_worthy": False
        }

        # 用户A的工作流
        engine_a = LearningWorkflowEngine(topic="主题A", user_id=2, workflow_id="wf_a")
        engine_a.start_workflow()
        for i in range(1, 6):
            engine_a.submit_step_output(i, f"A的输出{i}")
        result_a = engine_a.complete_workflow()

        # 用户B的工作流
        engine_b = LearningWorkflowEngine(topic="主题B", user_id=3, workflow_id="wf_b")
        engine_b.start_workflow()
        for i in range(1, 6):
            engine_b.submit_step_output(i, f"B的输出{i}")
        result_b = engine_b.complete_workflow()

        # 验证用户数据隔离
        wf_a = db.get_user_workflows(user_id=2)
        wf_b = db.get_user_workflows(user_id=3)
        self.assertGreaterEqual(len(wf_a), 1)
        self.assertGreaterEqual(len(wf_b), 1)
        workflow_ids_a = [w["workflow_id"] for w in wf_a]
        workflow_ids_b = [w["workflow_id"] for w in wf_b]
        self.assertIn("wf_a", workflow_ids_a)
        self.assertIn("wf_b", workflow_ids_b)

    def test_detection_summary_across_operations(self):
        """测试检测统计汇总"""
        detector = OutputDetector(user_id=3)

        # 多次检测
        for i in range(3):
            detector.run_detection(f"概念_summary_{i}", f"输出内容{i}")

        summary = detector.get_user_detection_summary()
        self.assertGreaterEqual(summary["total_detections"], 3)
        self.assertGreaterEqual(summary["avg_score"], 0)
        self.assertGreaterEqual(summary["reinforced_count"], 0)

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_workflow_status_tracking(self, mock_feynman_cls):
        """测试工作流状态跟踪"""
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }

        engine = LearningWorkflowEngine(topic="状态跟踪测试", user_id=2)
        engine.start_workflow()

        # 初始状态
        status = engine.get_workflow_status()
        self.assertEqual(status["status"], "active")
        self.assertEqual(status["current_step"], 0)

        # 提交部分步骤
        engine.submit_step_output(1, "输出1")
        engine.submit_step_output(2, "输出2")
        status = engine.get_workflow_status()
        self.assertEqual(status["current_step"], 2)
        self.assertEqual(status["status"], "active")

        # 完成全部
        for i in range(3, 6):
            engine.submit_step_output(i, f"输出{i}")
        engine.complete_workflow()
        status = engine.get_workflow_status()
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["current_step"], 5)


class TestPipelineErrorHandling(unittest.TestCase):
    """管道错误处理测试"""

    def setUp(self):
        db.init()

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_workflow_id_uniqueness(self, mock_feynman_cls):
        """测试工作流ID唯一性"""
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }

        engine1 = LearningWorkflowEngine(topic="主题1", user_id=2)
        engine2 = LearningWorkflowEngine(topic="主题2", user_id=3)
        engine1.start_workflow()
        engine2.start_workflow()
        self.assertNotEqual(engine1.workflow_id, engine2.workflow_id)

    def test_detector_empty_detection(self):
        """测试空检测处理"""
        detector = OutputDetector(user_id=2)
        result = detector.run_detection("测试", "")
        self.assertEqual(result.total_score, 0)
        self.assertFalse(result.is_mastered)

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_workflow_restarts_cleanly(self, mock_feynman_cls):
        """测试工作流可重复启动"""
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }

        # 第一次运行
        engine1 = LearningWorkflowEngine(topic="可重复测试", user_id=2, workflow_id="repeat_wf")
        engine1.start_workflow()
        for i in range(1, 6):
            engine1.submit_step_output(i, f"输出{i}")
        result1 = engine1.complete_workflow()

        # 第二次运行相同主题
        engine2 = LearningWorkflowEngine(topic="可重复测试", user_id=2, workflow_id="repeat_wf_2")
        engine2.start_workflow()
        result2 = engine2.start_workflow()
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)


class TestPipelineDataConsistency(unittest.TestCase):
    """数据一致性测试"""

    def setUp(self):
        db.init()

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_score_consistency(self, mock_feynman_cls):
        """测试分数一致性"""
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }
        mock_feynman_cls.return_value.thirty_second_test.return_value = {
            "score": 80, "feedback": "ok", "dimensions": {}, "is_feynman_worthy": True
        }

        engine = LearningWorkflowEngine(topic="一致性测试", user_id=2)
        engine.start_workflow()

        # 提交所有步骤，使用相同的输出
        for i in range(1, 6):
            engine.submit_step_output(i, "这是一致的测试输出内容")

        final = engine.complete_workflow()

        # 验证总分在合理范围内
        self.assertGreaterEqual(final["total_score"], 0)
        self.assertLessEqual(final["total_score"], 100)

    def test_detection_history_order(self):
        """测试检测历史顺序"""
        detector = OutputDetector(user_id=3)

        for i in range(5):
            detector.run_detection(f"概念_history_{i}", f"输出{i}")

        history = detector.get_detection_history()
        self.assertEqual(len(history), 5)
        # 最新的是最后一个
        self.assertEqual(history[-1]["concept"], "概念_history_4")


class TestPipelineIntegrationScenarios(unittest.TestCase):
    """集成场景测试"""

    def setUp(self):
        db.init()

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_scenario_math_topic(self, mock_feynman_cls):
        """数学主题学习场景"""
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "从生活中的三角形引入", "key_points": [], "animation_hint": "math_geometry"},
                {"content": "为什么只有直角三角形满足这个关系？", "key_points": [], "animation_hint": "math_puzzle"},
                {"content": "用面积法理解", "key_points": [], "animation_hint": "math_visualization"},
                {"content": "推导过程", "key_points": [], "animation_hint": "math_proof"},
                {"content": "总结测试", "key_points": [], "animation_hint": "math_summary"},
            ]
        }
        mock_feynman_cls.return_value.thirty_second_test.return_value = {
            "score": 85, "feedback": "理解很好", "dimensions": {}, "is_feynman_worthy": True
        }

        engine = LearningWorkflowEngine(topic="勾股定理", user_id=2, level="junior")
        start = engine.start_workflow()
        self.assertEqual(start["topic"], "勾股定理")

        for i in range(1, 6):
            engine.submit_step_output(i, f"我对勾股定理的理解：{i}")

        final = engine.complete_workflow()
        self.assertGreaterEqual(final["total_score"], 0)

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_scenario_physics_topic(self, mock_feynman_cls):
        """物理主题学习场景"""
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }
        mock_feynman_cls.return_value.thirty_second_test.return_value = {
            "score": 70, "feedback": "还可以", "dimensions": {}, "is_feynman_worthy": False
        }

        engine = LearningWorkflowEngine(topic="牛顿第二定律", user_id=3, level="senior")
        start = engine.start_workflow()
        self.assertEqual(start["topic"], "牛顿第二定律")

        for i in range(1, 6):
            engine.submit_step_output(i, f"对牛顿第二定律的理解：{i}")

        final = engine.complete_workflow()
        self.assertEqual(final["status"], "completed")

    def test_scenario_output_detection_only(self):
        """仅输出检测场景"""
        detector = OutputDetector(user_id=3)

        # 检测多种类型的输出
        outputs = [
            ("勾股定理", "a²+b²=c²，很简单", "quiz"),
            ("牛顿定律", "力等于质量乘以加速度", "essay"),
            ("化学反应", "酸碱中和生成盐和水", "project"),
        ]

        for concept, output, dtype in outputs:
            result = detector.run_detection(concept, output, detection_type=dtype)
            self.assertIsNotNone(result)
            self.assertGreaterEqual(result.total_score, 0)

    def test_scenario_guided_reinforcement_only(self):
        """仅引导强化场景"""
        detector = OutputDetector(user_id=3)

        result = detector.run_guided_reinforcement(
            concept="勾股定理",
            student_output="就是两个小边平方加起来等于大边平方",
            max_rounds=3,
            threshold=70,
        )

        self.assertIn("initial_score", result)
        self.assertIn("final_score", result)
        self.assertIn("is_mastered", result)
        self.assertGreaterEqual(result["total_rounds"], 0)


if __name__ == "__main__":
    unittest.main()
