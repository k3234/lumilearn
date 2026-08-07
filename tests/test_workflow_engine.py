#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 LearningWorkflowEngine
覆盖：初始化、启动工作流、提交输出、完成工作流、状态查询、错误处理
"""
import os
import sys

import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.workflow_engine import LearningWorkflowEngine


class TestWorkflowEngineInit(unittest.TestCase):
    """工作流引擎初始化测试"""

    def setUp(self):
        db.init()

    def test_init_default_params(self):
        engine = LearningWorkflowEngine(topic="勾股定理")
        self.assertEqual(engine.topic, "勾股定理")
        self.assertEqual(engine.user_id, 1)
        self.assertEqual(engine.level, "junior")
        self.assertEqual(engine.model_name, "qwen2.5:7b")
        self.assertIsNotNone(engine.workflow_id)

    def test_init_custom_params(self):
        engine = LearningWorkflowEngine(
            topic="牛顿第二定律",
            user_id=5,
            level="senior",
            model_name="llama3.2",
            workflow_id="test_wf_001"
        )
        self.assertEqual(engine.topic, "牛顿第二定律")
        self.assertEqual(engine.user_id, 5)
        self.assertEqual(engine.level, "senior")
        self.assertEqual(engine.model_name, "llama3.2")
        self.assertEqual(engine.workflow_id, "test_wf_001")


class TestWorkflowEngineStart(unittest.TestCase):
    """启动工作流测试"""

    def setUp(self):
        db.init()

    @patch('framework.workflow_engine.FeynmanEngine')
    def test_start_workflow(self, mock_feynman_cls):
        mock_engine = MagicMock()
        mock_feynman_cls.return_value = mock_engine
        mock_engine.explain.return_value = {
            "steps": [
                {"content": "现象引入内容", "key_points": [], "animation_hint": "hint1"},
                {"content": "认知冲突内容", "key_points": [], "animation_hint": "hint2"},
                {"content": "思维模型内容", "key_points": [], "animation_hint": "hint3"},
                {"content": "自主推导内容", "key_points": [], "animation_hint": "hint4"},
                {"content": "费曼测试内容", "key_points": [], "animation_hint": "hint5"},
            ]
        }

        engine = LearningWorkflowEngine(topic="勾股定理", user_id=2)
        result = engine.start_workflow()

        self.assertEqual(result["topic"], "勾股定理")
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["total_steps"], 5)
        self.assertIsNotNone(result["row_id"])

    @patch('framework.workflow_engine.FeynmanEngine')
    def test_start_workflow_creates_db_record(self, mock_feynman_cls):
        mock_engine = MagicMock()
        mock_feynman_cls.return_value = mock_engine
        mock_engine.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }

        engine = LearningWorkflowEngine(topic="测试", user_id=2, workflow_id="db_test_wf")
        result = engine.start_workflow()

        db_wf = db.get_workflow(result["row_id"])
        self.assertIsNotNone(db_wf)
        self.assertEqual(db_wf["user_id"], 2)
        self.assertEqual(db_wf["workflow_id"], "db_test_wf")
        self.assertEqual(db_wf["status"], "active")


class TestWorkflowEngineSubmit(unittest.TestCase):
    """提交步骤输出测试"""

    def setUp(self):
        db.init()

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_submit_valid_step(self, mock_feynman_cls):
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }
        engine = LearningWorkflowEngine(topic="勾股定理", user_id=2)
        engine._steps = [
            {"step_order": 1, "step_key": "phenomenon", "step_name": "现象引入",
             "step_desc": "", "content": "c1", "key_points": [], "animation_hint": "",
             "user_output": "", "output_score": 0.0, "step_completed": False},
            {"step_order": 2, "step_key": "conflict", "step_name": "认知冲突",
             "step_desc": "", "content": "c2", "key_points": [], "animation_hint": "",
             "user_output": "", "output_score": 0.0, "step_completed": False},
            {"step_order": 3, "step_key": "model", "step_name": "思维模型",
             "step_desc": "", "content": "c3", "key_points": [], "animation_hint": "",
             "user_output": "", "output_score": 0.0, "step_completed": False},
            {"step_order": 4, "step_key": "derive", "step_name": "自主推导",
             "step_desc": "", "content": "c4", "key_points": [], "animation_hint": "",
             "user_output": "", "output_score": 0.0, "step_completed": False},
            {"step_order": 5, "step_key": "test", "step_name": "费曼测试",
             "step_desc": "", "content": "c5", "key_points": [], "animation_hint": "",
             "user_output": "", "output_score": 0.0, "step_completed": False},
        ]

        result = engine.submit_step_output(1, "我在生活中见过勾股定理的例子，比如金字塔")
        self.assertEqual(result["step_order"], 1)
        self.assertEqual(result["step_name"], "现象引入")
        self.assertTrue(result["step_completed"])
        self.assertIn("score", result)

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_submit_invalid_step_order(self, mock_feynman_cls):
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }
        engine = LearningWorkflowEngine(topic="勾股定理", user_id=2)
        engine._steps = [
            {"step_order": 1, "step_key": "phenomenon", "step_name": "现象引入",
             "step_desc": "", "content": "c1", "key_points": [], "animation_hint": "",
             "user_output": "", "output_score": 0.0, "step_completed": False},
            {"step_order": 2, "step_key": "conflict", "step_name": "认知冲突",
             "step_desc": "", "content": "c2", "key_points": [], "animation_hint": "",
             "user_output": "", "output_score": 0.0, "step_completed": False},
            {"step_order": 3, "step_key": "model", "step_name": "思维模型",
             "step_desc": "", "content": "c3", "key_points": [], "animation_hint": "",
             "user_output": "", "output_score": 0.0, "step_completed": False},
            {"step_order": 4, "step_key": "derive", "step_name": "自主推导",
             "step_desc": "", "content": "c4", "key_points": [], "animation_hint": "",
             "user_output": "", "output_score": 0.0, "step_completed": False},
            {"step_order": 5, "step_key": "test", "step_name": "费曼测试",
             "step_desc": "", "content": "c5", "key_points": [], "animation_hint": "",
             "user_output": "", "output_score": 0.0, "step_completed": False},
        ]

        with self.assertRaises(ValueError):
            engine.submit_step_output(0, "无效步骤")
        with self.assertRaises(ValueError):
            engine.submit_step_output(6, "超出范围")

    def test_rule_score(self):
        engine = LearningWorkflowEngine(topic="测试")
        result = engine._rule_score("现象引入", "因为勾股定理很简单，所以我知道它")
        self.assertIn("score", result)
        self.assertIn("feedback", result)
        self.assertIsInstance(result["score"], int)
        self.assertTrue(0 <= result["score"] <= 100)


class TestWorkflowEngineComplete(unittest.TestCase):
    """完成工作流测试"""

    def setUp(self):
        db.init()

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_complete_workflow(self, mock_feynman_cls):
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

        engine = LearningWorkflowEngine(topic="勾股定理", user_id=2)
        engine.start_workflow()

        for i in range(1, 6):
            engine.submit_step_output(i, f"步骤{i}的输出内容，这是测试数据")

        result = engine.complete_workflow()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["topic"], "勾股定理")
        self.assertIsInstance(result["total_score"], (int, float))
        self.assertIsInstance(result["archive_id"], int)
        self.assertEqual(len(result["step_results"]), 5)

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_complete_without_start(self, mock_feynman_cls):
        engine = LearningWorkflowEngine(topic="测试")
        with self.assertRaises(RuntimeError):
            engine.complete_workflow()

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_complete_with_incomplete_steps(self, mock_feynman_cls):
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }
        engine = LearningWorkflowEngine(topic="勾股定理", user_id=2)
        engine.start_workflow()
        engine.submit_step_output(1, "输出1")
        engine.submit_step_output(2, "输出2")

        with self.assertRaises(RuntimeError):
            engine.complete_workflow()


class TestWorkflowEngineStatus(unittest.TestCase):
    """工作流状态查询测试"""

    def setUp(self):
        db.init()

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_get_status_before_start(self, mock_feynman_cls):
        engine = LearningWorkflowEngine(topic="测试")
        status = engine.get_workflow_status()
        self.assertEqual(status["status"], "active")
        self.assertEqual(status["current_step"], 0)

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_get_status_after_start(self, mock_feynman_cls):
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }
        engine = LearningWorkflowEngine(topic="勾股定理", user_id=2)
        engine.start_workflow()
        status = engine.get_workflow_status()

        self.assertEqual(status["status"], "active")
        self.assertEqual(status["topic"], "勾股定理")
        self.assertEqual(status["total_steps"], 5)

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_get_status_after_completion(self, mock_feynman_cls):
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
            "score": 75, "feedback": "ok", "dimensions": {}, "is_feynman_worthy": False
        }
        engine = LearningWorkflowEngine(topic="勾股定理", user_id=2)
        engine.start_workflow()
        for i in range(1, 6):
            engine.submit_step_output(i, f"输出{i}")
        engine.complete_workflow()

        status = engine.get_workflow_status()
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["current_step"], 5)


class TestWorkflowEnginePersistence(unittest.TestCase):
    """工作流持久化测试"""

    def setUp(self):
        db.init()

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_workflow_saved_to_db(self, mock_feynman_cls):
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }
        engine = LearningWorkflowEngine(topic="数据库测试", user_id=2, workflow_id="persist_test")
        start_result = engine.start_workflow()

        db_wf = db.get_workflow(start_result["row_id"])
        self.assertIsNotNone(db_wf)
        self.assertEqual(db_wf["workflow_id"], "persist_test")
        self.assertEqual(db_wf["status"], "active")

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_step_progress_persisted(self, mock_feynman_cls):
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }
        engine = LearningWorkflowEngine(topic="进度测试", user_id=2)
        engine.start_workflow()
        engine.submit_step_output(3, "第三步输出")

        db_wf = db.get_workflow(engine._workflow_row_id)
        self.assertEqual(db_wf["current_step"], 3)


class TestWorkflowEngineUserWorkflows(unittest.TestCase):
    """用户工作流查询测试"""

    def setUp(self):
        db.init()

    @patch('framework.workflow_engine.FeynmanEngine', return_value=MagicMock())
    def test_get_user_workflows(self, mock_feynman_cls):
        mock_feynman_cls.return_value.explain.return_value = {
            "steps": [
                {"content": "c1", "key_points": [], "animation_hint": ""},
                {"content": "c2", "key_points": [], "animation_hint": ""},
                {"content": "c3", "key_points": [], "animation_hint": ""},
                {"content": "c4", "key_points": [], "animation_hint": ""},
                {"content": "c5", "key_points": [], "animation_hint": ""},
            ]
        }
        engine1 = LearningWorkflowEngine(topic="主题A", user_id=2, workflow_id="wf_a")
        engine1.start_workflow()

        engine2 = LearningWorkflowEngine(topic="主题B", user_id=2, workflow_id="wf_b")
        engine2.start_workflow()

        workflows = db.get_user_workflows(user_id=2)
        self.assertGreaterEqual(len(workflows), 2)
        workflow_ids = [w["workflow_id"] for w in workflows]
        self.assertIn("wf_a", workflow_ids)
        self.assertIn("wf_b", workflow_ids)


if __name__ == "__main__":
    unittest.main()
