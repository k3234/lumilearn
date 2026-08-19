# -*- coding: utf-8 -*-
"""
LumiLearn 学习 Dashboard / 进度记录 API — 单元测试（P0 UX 任务 A1/A2）
核心设备压力约束：使用 Flask test_client + mock，绝不发起真实网络请求 / 模型调用。
"""
import os
import sys
from unittest import mock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import goai_web  # noqa: E402


class _FakeUser:
    def __getitem__(self, k):
        return {
            "id": 1, "name": "测试学生", "role": "student",
            "username": "tester", "password_hash": "x",
        }[k]

    def get(self, k, default=None):
        return self[k] if k in ("id", "name", "role", "username") else default


# ---------- 主题 → 知识节点匹配 ----------
class TestMatchKnowledgeNode:
    def test_match_monotonicity(self):
        assert goai_web._match_knowledge_node("我想理解函数的单调性") == "function_monotonicity"

    def test_match_newton_second_law(self):
        assert goai_web._match_knowledge_node("牛顿第二定律 F=ma") == "newton_second_law"

    def test_match_chemical_equilibrium(self):
        assert goai_web._match_knowledge_node("化学平衡移动原理") == "chemical_equilibrium"

    def test_match_pythagorean(self):
        assert goai_web._match_knowledge_node("勾股定理") == "pythagorean"

    def test_match_derivative(self):
        assert goai_web._match_knowledge_node("导数的概念") == "derivative"

    def test_no_match_unknown(self):
        assert goai_web._match_knowledge_node("自定义冷门主题XYZ") is None

    def test_no_match_empty(self):
        assert goai_web._match_knowledge_node("") is None

    def test_fallback_to_node_name(self):
        # 兜底：整词包含节点名
        assert goai_web._match_knowledge_node("请讲讲正态分布的应用") == "normal_distribution"


# ---------- 学习进度记录 /api/learning/progress ----------
class TestLearningProgress:
    def setup_method(self):
        goai_web.app.config["TESTING"] = True
        self.client = goai_web.app.test_client()

    def _login(self):
        with self.client.session_transaction() as s:
            s["user_id"] = 1

    def test_requires_login(self):
        resp = self.client.post("/api/learning/progress",
                                json={"topic": "勾股定理", "score": 80})
        assert resp.status_code == 401

    def test_missing_topic(self):
        self._login()
        resp = self.client.post("/api/learning/progress", json={})
        assert resp.status_code == 400

    def test_record_score_100_scale(self):
        self._login()
        engine = mock.Mock()
        with mock.patch.object(goai_web, "_get_adaptive_engine", return_value=engine):
            resp = self.client.post("/api/learning/progress",
                                    json={"topic": "勾股定理", "score": 80})
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["node_id"] == "pythagorean"
        # 0-100 分制归一化到 0-1
        engine.record_learning.assert_called_once_with("1", "pythagorean",
                                                       score=mock.ANY,
                                                       time_spent=0.0)
        assert engine.record_learning.call_args[1]["score"] == 0.8

    def test_record_score_01_scale(self):
        self._login()
        engine = mock.Mock()
        with mock.patch.object(goai_web, "_get_adaptive_engine", return_value=engine):
            resp = self.client.post("/api/learning/progress",
                                    json={"topic": "牛顿第二定律", "score": 0.65})
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["score"] == 0.65

    def test_record_unmatched_topic(self):
        self._login()
        engine = mock.Mock()
        with mock.patch.object(goai_web, "_get_adaptive_engine", return_value=engine):
            resp = self.client.post("/api/learning/progress",
                                    json={"topic": "冷门主题", "score": 90})
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["matched"] is False
        # 未匹配节点不调用 record_learning
        engine.record_learning.assert_not_called()

    def test_engine_unavailable(self):
        self._login()
        with mock.patch.object(goai_web, "_get_adaptive_engine", return_value=None):
            resp = self.client.post("/api/learning/progress",
                                    json={"topic": "勾股定理", "score": 80})
        assert resp.status_code == 500

    def test_score_clamped(self):
        self._login()
        engine = mock.Mock()
        with mock.patch.object(goai_web, "_get_adaptive_engine", return_value=engine):
            resp = self.client.post("/api/learning/progress",
                                    json={"topic": "勾股定理", "score": 200})
        assert resp.get_json()["data"]["score"] == 1.0


# ---------- 学习首页聚合 /api/learning/dashboard ----------
class TestLearningDashboard:
    def setup_method(self):
        goai_web.app.config["TESTING"] = True
        self.client = goai_web.app.test_client()

    def _login(self):
        with self.client.session_transaction() as s:
            s["user_id"] = 1

    def test_requires_login(self):
        resp = self.client.get("/api/learning/dashboard")
        assert resp.status_code == 401

    def test_dashboard_aggregates(self):
        self._login()
        engine = mock.Mock()
        engine.get_progress.return_value = {
            "overall_progress": 12.5, "mastered_nodes": 1, "learning_nodes": 2,
            "studied_nodes": 3, "total_knowledge_nodes": 18,
            "recent_history": [{"node_id": "pythagorean", "score": 0.8}],
        }
        engine.analyze_weaknesses.return_value = [
            {"node_id": "pythagorean", "name": "勾股定理", "mastery": 0.4},
        ]
        engine.recommend_next.return_value = [
            {"node_id": "cosine_rule", "name": "余弦定理", "recommendation_score": 0.9},
        ]
        with mock.patch.object(goai_web, "_get_adaptive_engine", return_value=engine):
            resp = self.client.get("/api/learning/dashboard")
        data = resp.get_json()
        assert data["success"] is True
        d = data["data"]
        assert d["overall_progress"] == 12.5
        assert d["mastered_nodes"] == 1
        assert len(d["weaknesses"]) == 1
        assert d["weaknesses"][0]["name"] == "勾股定理"
        assert len(d["recommended"]) == 1
        assert len(d["recent_history"]) == 1

    def test_dashboard_empty_history_uses_reports(self):
        self._login()
        engine = mock.Mock()
        engine.get_progress.return_value = {
            "overall_progress": 0, "mastered_nodes": 0, "learning_nodes": 0,
            "studied_nodes": 0, "total_knowledge_nodes": 18, "recent_history": [],
        }
        engine.analyze_weaknesses.return_value = []
        engine.recommend_next.return_value = []
        with mock.patch.object(goai_web, "_get_adaptive_engine", return_value=engine), \
             mock.patch.object(goai_web.db, "get_learning_reports",
                               return_value=[{"topic": "勾股定理", "report": {
                                   "task_understanding": {"subject": "数学"},
                                   "mastery_assessment": {"score": 85},
                                   "generated_at": "2026-08-15",
                               }, "created_at": "2026-08-15"}]):
            resp = self.client.get("/api/learning/dashboard")
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["recent_reports"][0]["topic"] == "勾股定理"
        assert data["data"]["recent_reports"][0]["score"] == 85

    def test_dashboard_engine_unavailable(self):
        self._login()
        with mock.patch.object(goai_web, "_get_adaptive_engine", return_value=None):
            resp = self.client.get("/api/learning/dashboard")
        assert resp.status_code == 500
