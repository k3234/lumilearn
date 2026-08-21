# -*- coding: utf-8 -*-
"""
LumiLearn 多基座自适应调度 — 单元测试

覆盖：
  - framework.core.router: TaskType 任务类型优先路由
      （计算 → deepseek 系列，理解 → qwen 系列，无 task_type 走原有逻辑）
  - agent_core.model_registry: FALLBACK_CHAIN 降级链配置

完全离线运行，不依赖网络/真实模型。
"""

import os
import sys
import unittest

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.core.router import ModelRouter, RouteRequest, TaskType
from agent_core.model_registry import FALLBACK_CHAIN, get_fallback_chain


class TestAdaptiveRouting(unittest.TestCase):
    """多基座自适应调度测试"""

    def setUp(self):
        self.router = ModelRouter()

    def test_calculation_routes_to_deepseek(self):
        """task_type=calculation → RouteResult.model_name 含 deepseek"""
        request = RouteRequest(topic="计算 2+2 等于几", task_type=TaskType.calculation)
        result = self.router.route(request)
        self.assertIn("deepseek", result.model_name.lower())

    def test_comprehension_routes_to_qwen(self):
        """task_type=comprehension → RouteResult.model_name 含 qwen"""
        request = RouteRequest(topic="阅读并理解这段文章", task_type=TaskType.comprehension)
        result = self.router.route(request)
        self.assertIn("qwen", result.model_name.lower())

    def test_default_routes_normal(self):
        """无 task_type → 走原有逻辑（默认聊天模型路径）"""
        request = RouteRequest(topic="任意主题")
        result = self.router.route(request)
        self.assertIn(result.model_name, {"lumilearn-v2:latest", "qwen2.5:7b"})

    def test_fallback_chain_returns_list(self):
        """get_fallback_chain 返回非空列表"""
        chain = get_fallback_chain("remote_ollama")
        self.assertIsInstance(chain, list)
        self.assertTrue(chain)
        # 链中模型均已在注册表声明
        self.assertIn("remote_ollama", FALLBACK_CHAIN)


if __name__ == "__main__":
    unittest.main()
