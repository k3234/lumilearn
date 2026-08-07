# -*- coding: utf-8 -*-
"""Agent 管理系统测试"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.admin.agents import (
    AgentRegistry,
    get_agent_registry,
    FeynmanAgent,
    DetectionAgent,
    AdaptiveAgent,
    ChatAgent,
)


class TestAgentRegistry(unittest.TestCase):
    def setUp(self):
        db.init()
        self.registry = get_agent_registry()

    def test_builtin_agents_registered(self):
        agents = self.registry.list_agents()
        agent_ids = {a["agent_id"] for a in agents}
        self.assertIn("feynman_teacher", agent_ids)
        self.assertIn("output_detector", agent_ids)
        self.assertIn("adaptive_path", agent_ids)
        self.assertIn("chat_assistant", agent_ids)

    def test_list_agents_by_type(self):
        agents = self.registry.list_agents(agent_type="feynman")
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0]["agent_type"], "feynman")

    def test_register_custom_agent(self):
        result = self.registry.register(
            agent_id="test_custom_agent",
            name="测试Agent",
            agent_type="custom",
            description="单元测试用",
            config={"enabled": True},
        )
        self.assertIn("agent_id", result)
        agent = db.get_agent("test_custom_agent")
        self.assertIsNotNone(agent)
        self.assertEqual(agent["name"], "测试Agent")

    def test_start_and_stop_agent(self):
        self.registry.start("chat_assistant")
        agent = db.get_agent("chat_assistant")
        self.assertEqual(agent["status"], "running")

        self.registry.stop("chat_assistant")
        agent = db.get_agent("chat_assistant")
        self.assertEqual(agent["status"], "stopped")

    def test_run_feynman_agent(self):
        with patch("framework.engines.feynman_engine.FeynmanEngine") as MockEngine:
            MockEngine.return_value.explain.return_value = {"steps": []}
            result = self.registry.run_agent("feynman_teacher", {"topic": "勾股定理", "level": "junior"})
        self.assertTrue(result["success"])
        self.assertEqual(result["topic"], "勾股定理")

    def test_run_agent_missing_param(self):
        result = self.registry.run_agent("feynman_teacher", {})
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_run_chat_agent(self):
        with patch("framework.services.chat_service.get_chat_service") as mock_service:
            mock_service.return_value.chat_sync.return_value = {"content": "你好！"}
            result = self.registry.run_agent("chat_assistant", {"message": "你好"})
        self.assertTrue(result["success"])
        self.assertEqual(result["reply"], "你好！")

    def test_delete_agent(self):
        self.registry.register("to_delete_agent", "待删除", "custom", "临时")
        result = self.registry.delete("to_delete_agent")
        self.assertTrue(result["success"])
        self.assertIsNone(db.get_agent("to_delete_agent"))

    def test_health_check(self):
        health = self.registry.health()
        self.assertIn("total", health)
        self.assertEqual(health["total"], len(db.get_agents()))

    def test_get_nonexistent_agent_raises(self):
        with self.assertRaises(KeyError):
            self.registry.get_agent("does_not_exist")


class TestBuiltinAgents(unittest.TestCase):
    def test_feynman_agent_meta(self):
        agent = FeynmanAgent()
        self.assertEqual(agent.agent_type, "feynman")
        self.assertIn("status", agent.health())

    def test_detection_agent_meta(self):
        agent = DetectionAgent()
        self.assertEqual(agent.agent_id, "output_detector")

    def test_adaptive_agent_meta(self):
        agent = AdaptiveAgent()
        self.assertEqual(agent.agent_type, "adaptive")

    def test_chat_agent_meta(self):
        agent = ChatAgent()
        self.assertEqual(agent.agent_id, "chat_assistant")
        self.assertIn("status", agent.health())


if __name__ == "__main__":
    unittest.main()
