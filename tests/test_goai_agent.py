# -*- coding: utf-8 -*-
"""
goai_agent 核心模块 — 轻量单元测试
核心设备压力约束：全部使用 mock，绝不发起真实网络请求 / 模型调用 / 写库。
"""
import os
import sys
from unittest import mock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import goai_agent  # noqa: E402
from goai_agent import (  # noqa: E402
    FlowOrchestrator,
    LumiLearnAgent,
    ResultDelivery,
    TaskUnderstanding,
    ToolCaller,
)


# ---------- 任务理解 ----------
class TestTaskUnderstanding:
    def test_detect_subject_math(self):
        task = TaskUnderstanding().understand("我想理解函数的单调性")
        assert task["subject"] == "数学"
        assert task["learning_type"] == "概念理解"

    def test_detect_subject_physics(self):
        assert TaskUnderstanding().understand("帮我复习牛顿第二定律")["subject"] == "物理"

    def test_detect_subject_chemistry(self):
        assert TaskUnderstanding().understand("学习化学平衡移动")["subject"] == "化学"

    def test_detect_difficulty(self):
        assert TaskUnderstanding().understand("高考真题 圆锥曲线")["difficulty"] == "高中"
        assert TaskUnderstanding().understand("初一数学 有理数")["difficulty"] == "初中"

    def test_detect_learning_type(self):
        assert TaskUnderstanding().understand("做几道三角函数题型训练")["learning_type"] == "题型训练"
        assert TaskUnderstanding().understand("复习一遍动量定理")["learning_type"] == "复习巩固"

    def test_core_topic_cleaned(self):
        task = TaskUnderstanding().understand("什么是勾股定理")
        assert "勾股定理" in task["core_topic"]


# ---------- 流程编排 ----------
class TestFlowOrchestrator:
    def test_five_steps(self):
        flow = FlowOrchestrator().orchestrate({
            "subject": "数学", "topic_type": "函数", "difficulty": "高中",
            "core_topic": "单调性", "learning_type": "概念理解", "confidence": 0.9,
        })
        assert len(flow) == 5
        assert [s["name"] for s in flow] == ["现象引入", "认知冲突", "思维模型", "自主推导", "费曼测试"]
        assert all(s["status"] == "pending" for s in flow)
        assert all("费曼教学法" in s["prompt"] for s in flow)


# ---------- 工具调用（全 mock，不触网） ----------
class TestToolCaller:
    @mock.patch("requests.get")
    def test_availability_detects_model(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"models": [{"name": "lumilearn-v2:latest"}]}
        tc = ToolCaller(ollama_url="http://mock:11434", preferred_model="lumilearn-v2")
        assert tc.available is True
        assert tc.preferred_model == "lumilearn-v2"

    @mock.patch("requests.get")
    @mock.patch("requests.post")
    def test_call_ollama_returns_content(self, mock_post, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"models": [{"name": "qwen2.5:7b"}]}
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"response": "教学内容mock"}
        tc = ToolCaller(ollama_url="http://mock:11434", preferred_model="qwen2.5:7b")
        res = tc.call("教学主题：函数")
        assert res["success"] is True
        assert res["content"] == "教学内容mock"
        assert tc.call_log and tc.call_log[-1]["success"]

    @mock.patch("requests.get")
    def test_fallback_when_unavailable(self, mock_get):
        mock_get.side_effect = Exception("网络不可达")
        tc = ToolCaller(ollama_url="http://mock:11434")
        assert tc.available is False
        res = tc.call("教学主题：函数", task_type="teach")
        assert res["success"] is True
        assert "rule_fallback" in res["model"]
        assert "函数" in res["content"]


# ---------- 结果交付 ----------
class TestResultDelivery:
    def test_report_structure_and_mastery(self):
        task = {"core_topic": "单调性", "subject": "数学", "topic_type": "函数",
                "difficulty": "高中", "learning_type": "概念理解", "confidence": 0.9}
        flow_results = [
            {"success": True, "content": "a", "elapsed": 1.0, "model": "m", "step": i, "name": n}
            for i, n in enumerate(["现象引入", "认知冲突", "思维模型", "自主推导"], 1)
        ] + [{"success": False, "content": "", "elapsed": 1.0, "model": "m", "step": 5, "name": "费曼测试"}]
        report = ResultDelivery().generate_report(task, flow_results, {"total_calls": 5})
        assert report["teaching_flow"]["completed_steps"] == 4
        assert report["mastery_assessment"]["score"] == 80
        assert "费曼测试" in report["weak_points"][0]
        assert len(report["next_steps"]) >= 3


# ---------- 主引擎（mock 掉模型调用与落盘，不写仓库、不触网） ----------
class TestLumiLearnAgent:
    def test_run_produces_report(self, tmp_path, monkeypatch):
        with mock.patch("requests.get", side_effect=Exception("offline")):
            agent = LumiLearnAgent(ollama_url="http://mock:11434", model="lumilearn-v2")

        def fake_call(prompt, task_type="teach"):
            return {"content": "教学内容", "model": "mock-model",
                    "elapsed": 0.01, "success": True, "step": 1, "name": "x"}

        monkeypatch.setattr(agent.tool_caller, "call", fake_call)
        monkeypatch.setattr(agent.tool_caller, "get_call_summary",
                            lambda: {"total_calls": 5, "success_rate": 1.0})
        monkeypatch.setattr(
            agent.result_delivery, "save_report",
            lambda report, output_dir="goai_output": (str(tmp_path / "r.json"), str(tmp_path / "r.md")),
        )
        monkeypatch.setattr("framework.database.db.add_reasoning_log", lambda **kw: None)

        report = agent.run("我想理解函数的单调性", interactive=False, user_id=1)
        assert report["task_understanding"]["subject"] == "数学"
        assert report["teaching_flow"]["total_steps"] == 5
        assert report["mastery_assessment"]["score"] == 100
        assert "单调性" in report["title"]
