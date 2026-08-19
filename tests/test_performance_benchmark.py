# -*- coding: utf-8 -*-
"""
LumiLearn Phase 4 — 性能基准与成本优化测试

覆盖交付物：
  - agent_core.cost_tracker : 成本追踪（记录/汇总/趋势/异常/报告）
  - agent_core.mcp_client   : MCP 1.0 客户端（本地 Server 端到端）
  - agent_core.router       : 成本感知路由（预估成本 / 超支降级）
  - 核心路径性能 smoke 测试（宽松阈值，避免 CI 抖动）
"""

import sys
import os
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.cost_tracker import CostTracker, get_cost_tracker, reset_cost_tracker
from agent_core.mcp_client import MCPServer, MCPClient, BuiltinToolRegistry
from agent_core.router import RouterAgent, get_router_agent


# ================================================================
# 一、成本感知路由测试
# ================================================================
class TestRouterCostRouting(unittest.TestCase):
    """Router 成本感知路由"""

    def setUp(self):
        self.router = RouterAgent()

    def test_route_includes_estimated_cost(self):
        result = self.router.route("什么是函数")
        self.assertIn("estimated_cost", result)
        self.assertGreaterEqual(result["estimated_cost"], 0)

    def test_cost_targets(self):
        """Roadmap 成本目标（$1≈7.2元）：
        简单任务 < $0.01（≈0.07 元），复杂任务 < $0.10（≈0.72 元）"""
        simple = self.router.estimate_cost("simple")
        standard = self.router.estimate_cost("standard")
        complex_p = self.router.estimate_cost("complex_parallel")
        self.assertLess(simple, 0.07)     # < $0.01
        self.assertLess(complex_p, 0.72)  # < $0.10
        self.assertLess(simple, standard)
        self.assertLess(standard, complex_p)

    def test_complex_route_cost_exceeds_simple(self):
        """复杂任务预估成本应明显高于简单任务"""
        complex_result = self.router.route("请深入分析并比较凸透镜与凹透镜的异同，推导成像规律")
        simple_result = self.router.route("什么是函数")
        self.assertEqual(complex_result["route"], "complex_parallel")
        self.assertGreater(complex_result["estimated_cost"],
                           simple_result["estimated_cost"])

    def test_downgrade_with_tight_budget(self):
        """成本上限过紧时自动降级"""
        result = self.router.route_with_budget(
            "请深入分析并比较凸透镜与凹透镜的异同，推导成像规律",
            max_cost=0.005,  # 极低上限 → 必触发降级
        )
        self.assertTrue(result["downgraded"])
        self.assertNotEqual(result["route"], result["original_route"])
        self.assertLessEqual(result["estimated_cost"], 0.005)
        self.assertIn("downgrade_reason", result)

    def test_no_downgrade_with_high_budget(self):
        """成本上限充足（> 复杂任务预估 0.24 元）时不降级"""
        result = self.router.route_with_budget(
            "请深入分析并比较凸透镜与凹透镜的异同，推导成像规律",
            max_cost=0.5,
        )
        self.assertFalse(result["downgraded"])
        self.assertEqual(result["route"], "complex_parallel")

    def test_simple_route_never_downgrades_below_simple(self):
        result = self.router.route_with_budget("什么是函数", max_cost=0.0001)
        self.assertEqual(result["route"], "simple")
        self.assertFalse(result["downgraded"])


# ================================================================
# 二、CostTracker 成本追踪测试
# ================================================================
class TestCostTracker(unittest.TestCase):
    """成本追踪与优化报告"""

    def setUp(self):
        reset_cost_tracker()
        self.tracker = CostTracker()

    def test_record_and_summary(self):
        self.tracker.record("feynman", "qwen2.5:7b", 300, 900)
        self.tracker.record("verifier", "qwen2.5:7b", 100, 50)
        summary = self.tracker.get_summary()
        self.assertEqual(summary["total_calls"], 2)
        self.assertGreater(summary["total_cost"], 0)
        self.assertIn("feynman", summary["by_agent"])
        self.assertIn("verifier", summary["by_agent"])

    def test_cost_calculation_matches_unit_price(self):
        # qwen2.5:7b = 0.001 元/千token，1000+1000 token → 0.002 元
        record = self.tracker.record("a", "qwen2.5:7b", 1000, 1000)
        self.assertEqual(record["cost"], 0.002)

    def test_daily_trend(self):
        self.tracker.record("a", "qwen2.5:7b", 100, 100)
        trend = self.tracker.get_daily_trend(3)
        self.assertEqual(len(trend), 3)
        self.assertTrue(any(t["calls"] > 0 for t in trend))

    def test_cost_by_agent_share(self):
        self.tracker.record("a", "qwen2.5:7b", 1000, 1000)
        self.tracker.record("b", "GLM-5", 1000, 1000)  # 单价更高
        shares = self.tracker.get_cost_by_agent()
        self.assertGreater(shares["b"]["share"], shares["a"]["share"])

    def test_anomaly_single_cost_high(self):
        self.tracker.anomaly_cost_threshold = 0.01
        self.tracker.record("coach", "GLM-5", 5000, 5000)  # 0.1 元 > 0.01
        anomalies = self.tracker.detect_anomalies()
        self.assertTrue(any(a["type"] == "single_cost_high" for a in anomalies))

    def test_generate_report_structure(self):
        self.tracker.record("feynman", "qwen2.5:7b", 300, 700)
        report = self.tracker.generate_report()
        self.assertIn("summary", report)
        self.assertIn("daily_trend", report)
        self.assertIn("by_agent", report)
        self.assertIn("anomalies", report)
        self.assertIn("suggestions", report)

    def test_singleton(self):
        t1 = get_cost_tracker()
        t2 = get_cost_tracker()
        self.assertIs(t1, t2)


# ================================================================
# 三、MCP 客户端 + 本地 Server 端到端测试
# ================================================================
class TestMCPServerClient(unittest.TestCase):
    """MCP 1.0 协议端到端（本地 HTTP Server ↔ 客户端）"""

    @classmethod
    def setUpClass(cls):
        cls.server = MCPServer(port=0)  # 随机端口
        cls.server.start()
        cls.client = MCPClient()
        cls.client.connect_http(cls.server.url)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.server.stop()

    def test_initialize_handshake(self):
        self.assertTrue(self.client._initialized)
        self.assertEqual(self.client.server_info["name"], "lumilearn-tools")

    def test_list_tools(self):
        tools = self.client.list_tools()
        names = {t["name"] for t in tools}
        self.assertIn("knowledge_retrieval", names)
        self.assertIn("generate_question", names)
        self.assertIn("render_chart", names)
        for t in tools:
            self.assertIn("inputSchema", t)

    def test_call_generate_question(self):
        result = self.client.call_tool(
            "generate_question", {"topic": "函数单调性", "difficulty": "困难"})
        self.assertFalse(result["isError"])
        self.assertIn("函数单调性", result["text"])

    def test_call_unknown_tool_returns_error(self):
        result = self.client.call_tool("nonexistent_tool", {})
        self.assertTrue(result["isError"])

    def test_call_render_chart(self):
        result = self.client.call_tool(
            "render_chart", {"chart_type": "bar", "title": "成绩分布",
                             "points": [80, 90, 75]})
        self.assertFalse(result["isError"])
        self.assertIn("bar", result["text"])

    def test_registry_register_custom_tool(self):
        registry = BuiltinToolRegistry()
        registry.register_tool(
            "echo", "回声测试", {"type": "object",
                                 "properties": {"msg": {"type": "string"}}},
            lambda args: f"echo: {args.get('msg', '')}")
        result = registry.call_tool("echo", {"msg": "你好"})
        self.assertFalse(result["isError"])
        self.assertEqual(result["content"][0]["text"], "echo: 你好")


# ================================================================
# 四、核心路径性能 smoke 测试（宽松阈值）
# ================================================================
class TestPerformanceSmoke(unittest.TestCase):
    """核心路径延迟 smoke 测试"""

    def _avg_ms(self, fn, rounds=50):
        t0 = time.time()
        for _ in range(rounds):
            fn()
        return (time.time() - t0) / rounds * 1000

    def test_router_route_latency(self):
        router = get_router_agent()
        avg = self._avg_ms(lambda: router.route("请分析函数单调性并比较两种解法"))
        self.assertLess(avg, 5.0, f"route() 平均延迟 {avg:.2f}ms 超阈值")

    def test_router_analyze_latency(self):
        router = get_router_agent()
        avg = self._avg_ms(lambda: router.analyze("什么是牛顿第二定律"))
        self.assertLess(avg, 2.0)

    def test_cost_tracker_record_latency(self):
        tracker = get_cost_tracker()
        avg = self._avg_ms(
            lambda: tracker.record("a", "qwen2.5:7b", 100, 200))
        self.assertLess(avg, 0.5, f"record() 平均延迟 {avg:.2f}ms 超阈值")

    def test_mcp_call_tool_latency(self):
        client = MCPClient()
        server = MCPServer(port=0)
        server.start()
        client.connect_http(server.url)
        try:
            # 基线：Windows 本地 http.server + 每次请求新建连接/线程，
            # 阈值取宽松值（~500ms），重点防明显回归
            avg = self._avg_ms(
                lambda: client.call_tool("generate_question",
                                         {"topic": "函数"}), rounds=10)
            self.assertLess(avg, 1000.0,
                            f"MCP tools/call 平均延迟 {avg:.2f}ms 超阈值")
        finally:
            client.close()
            server.stop()


# ================================================================
# 五、动态权重感知的模型选优（P1-7）
# ================================================================
class TestDynamicWeightRanking(unittest.TestCase):
    """高动态权重可改写静态排序：低静态权重模型进入 Top3（P1-7）"""

    def test_dynamic_weight_ranking(self):
        from agent_core.model_registry import (
            get_best_models,
            get_best_models_by_dynamic_weight,
            get_model,
        )
        from agent_core.weight_manager import get_weight_manager
        from framework.database import db

        # 选定一个低静态权重模型（remote_ollama，weight=1）
        low_id = "qwen2.5:7b"
        low_model = get_model(low_id)
        self.assertIsNotNone(low_model)
        self.assertEqual(low_model.weight, 1)

        static_top3 = [m.id for m in get_best_models(3)]
        self.assertEqual(len(static_top3), 3)
        self.assertNotIn(low_id, static_top3)  # 纯静态排序不含低权重模型

        wm = get_weight_manager()
        # 外键约束：agent_weight_config.agent_id 须先存在于 agents 表
        db.register_agent(low_id, f"dynweight-{low_id}", "solo",
                          "动态权重排序测试用临时Agent")
        orig_row = db.get_agent_weight(low_id)
        orig = dict(orig_row) if orig_row else None

        # 提高该模型动态权重：base=10 且成功调用（0 延迟）→ dynamic_weight=10.0
        wm.set_base_weight(low_id, 10.0)
        wm.update_weight(low_id, latency_ms=0, success=True)

        try:
            ranked = get_best_models_by_dynamic_weight(3)
            self.assertEqual(len(ranked), 3)
            ranked_ids = [m.id for m in ranked]
            # 综合分 10.0 最高 → 进入 Top3 且排第一
            self.assertIn(low_id, ranked_ids)
            self.assertEqual(ranked_ids[0], low_id)
            # 动态排序不同于纯静态排序
            self.assertNotEqual(ranked_ids, static_top3)
        finally:
            # 恢复权重：清理缓存并还原 DB 行（避免污染其他用例）
            wm._weight_cache.pop(low_id, None)
            if orig is None:
                db._execute(
                    "DELETE FROM agent_weight_config WHERE agent_id = ?",
                    (low_id,))
                db._execute("DELETE FROM agents WHERE agent_id = ?", (low_id,))
            else:
                wm.set_base_weight(low_id, orig["base_weight"])
                db.update_agent_weight_stats(
                    low_id, orig["call_count"], orig["success_count"],
                    orig["fail_count"], orig["avg_latency_ms"],
                    orig["dynamic_weight"])
                wm._weight_cache.pop(low_id, None)


if __name__ == "__main__":
    unittest.main()
