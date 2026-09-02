# -*- coding: utf-8 -*-
"""
LumiLearn 学习者画像系统 — 单元测试

覆盖：
  - AdaptiveLearningEngine.get_student_profile: 学生画像获取与缓存
  - AdaptiveLearningEngine.update_profile_after_learning: 学习活动后更新画像
  - AdaptiveLearningEngine.infer_learning_style: 学习风格推断
  - 薄弱点检测（掌握度<0.4）
  - 错题历史记录

完全离线运行，不依赖网络。
"""

import os
import sys
import tempfile
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from framework.services.adaptive_learning import AdaptiveLearningEngine


class TestStudentProfile:
    """学习者画像系统测试"""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.engine = AdaptiveLearningEngine(data_dir=self.tmpdir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ---------- test_get_profile_empty ----------

    def test_get_profile_empty(self):
        """新用户画像为空"""
        profile = self.engine.get_student_profile("new_user_001")

        assert profile["user_id"] == "new_user_001"
        assert profile["mastery_scores"] == {}
        assert profile["weak_points"] == []
        assert profile["error_history"] == []
        assert profile["learning_style"] == "visual"

    def test_get_profile_empty_cache_empty(self):
        """空画像不会触发误缓存"""
        profile1 = self.engine.get_student_profile("user_cache_test")
        profile2 = self.engine.get_student_profile("user_cache_test")
        assert profile1 is profile2  # 同一引用（缓存命中）

    # ---------- test_get_profile_after_learning ----------

    def test_get_profile_after_learning(self):
        """学习后画像正确更新"""
        uid = "profile_user_002"
        # 多次学习使掌握度累积到0.4以上（EMA alpha=0.3，需多次累积）
        for _ in range(4):
            self.engine.record_learning(uid, "triangle_basics", score=0.9, time_spent=20)
        for _ in range(4):
            self.engine.record_learning(uid, "pythagorean", score=0.9, time_spent=25)

        profile = self.engine.get_student_profile(uid)

        assert "triangle_basics" in profile["mastery_scores"]
        assert "pythagorean" in profile["mastery_scores"]
        assert profile["mastery_scores"]["triangle_basics"] > 0
        assert profile["mastery_scores"]["pythagorean"] > 0
        assert profile["weak_points"] == []
        assert len(profile["error_history"]) == 0

    def test_update_profile_after_learning_invalidates_cache(self):
        """update_profile_after_learning 清除缓存"""
        uid = "cache_invalidate_test"
        self.engine.record_learning(uid, "triangle_basics", score=0.5)
        self.engine.get_student_profile(uid)  # 预热缓存

        self.engine.update_profile_after_learning(uid, "pythagorean", score=0.3, time_spent=60)

        # 缓存应被清除，再次获取应重新计算
        profile = self.engine.get_student_profile(uid)
        assert "pythagorean" in profile["mastery_scores"]
        assert profile["mastery_scores"]["pythagorean"] < 0.4
        assert "pythagorean" in profile["weak_points"]

    # ---------- test_weak_points_detection ----------

    def test_weak_points_detection(self):
        """薄弱点正确识别（掌握度<0.4）"""
        uid = "weak_points_user"
        # 学习低分知识点（单次学习后掌握度=0.2*0.3=0.06<0.4）
        self.engine.record_learning(uid, "triangle_basics", score=0.2, time_spent=45)
        self.engine.record_learning(uid, "pythagorean", score=0.15, time_spent=50)
        # 多次学习高分知识点使其掌握度超过0.4（需约5次累积到>0.4）
        for _ in range(6):
            self.engine.record_learning(uid, "mean_median", score=0.95, time_spent=15)

        profile = self.engine.get_student_profile(uid)

        weak = profile["weak_points"]
        assert "triangle_basics" in weak
        assert "pythagorean" in weak
        assert "mean_median" not in weak

    def test_weak_points_empty_when_all_mastered(self):
        """全部掌握时薄弱点列表为空"""
        uid = "all_mastered"
        for _ in range(6):
            self.engine.record_learning(uid, "triangle_basics", score=0.95, time_spent=10)
            self.engine.record_learning(uid, "pythagorean", score=0.95, time_spent=10)

        profile = self.engine.get_student_profile(uid)
        assert profile["weak_points"] == []

    # ---------- test_infer_learning_style ----------

    def test_infer_learning_style_logical(self):
        """逻辑型风格：快速答题且正确率高"""
        history = [
            {"node_id": "quadratic_formula", "score": 0.9, "time_spent": 15},
            {"node_id": "polynomial", "score": 0.85, "time_spent": 20},
            {"node_id": "inequality_solving", "score": 0.8, "time_spent": 25},
            {"node_id": "mean_median", "score": 0.9, "time_spent": 10},
            {"node_id": "counting_principle", "score": 0.75, "time_spent": 28},
        ]
        style = self.engine.infer_learning_style(history)
        assert style == "logical"

    def test_infer_learning_style_visual(self):
        """视觉型风格：几何/图形类知识点多"""
        history = [
            {"node_id": "triangle_basics", "score": 0.85, "time_spent": 40},
            {"node_id": "pythagorean", "score": 0.8, "time_spent": 35},
            {"node_id": "circle_area", "score": 0.8, "time_spent": 45},
            {"node_id": "vector_concept", "score": 0.85, "time_spent": 50},
            {"node_id": "quadratic_formula", "score": 0.8, "time_spent": 20},
        ]
        style = self.engine.infer_learning_style(history)
        # 4/5=80% geometry，且无慢答低分记录，应判定为 visual
        assert style == "visual"

    def test_infer_learning_style_practice(self):
        """练习型风格：答题慢且分数低（持续练习）"""
        history = [
            {"node_id": "pythagorean", "score": 0.3, "time_spent": 120},
            {"node_id": "cosine_rule", "score": 0.25, "time_spent": 150},
            {"node_id": "triangle_basics", "score": 0.4, "time_spent": 90},
            {"node_id": "quadratic_formula", "score": 0.5, "time_spent": 100},
        ]
        style = self.engine.infer_learning_style(history)
        assert style == "practice"

    def test_infer_learning_style_empty_history(self):
        """空历史默认返回 visual"""
        style = self.engine.infer_learning_style([])
        assert style == "visual"

    def test_infer_learning_style_low_geometry_ratio(self):
        """几何占比不足但答题快的情况"""
        history = [
            {"node_id": "triangle_basics", "score": 0.7, "time_spent": 40},
            {"node_id": "quadratic_formula", "score": 0.8, "time_spent": 20},
            {"node_id": "polynomial", "score": 0.75, "time_spent": 25},
        ]
        style = self.engine.infer_learning_style(history)
        # 1/3 geometry不满足visual条件，fast_correct=2/3满足logical条件
        assert style == "logical"

    # ---------- test_error_history ----------

    def test_error_history_filters_low_scores(self):
        """错题历史只包含低分记录"""
        uid = "error_history_test"
        self.engine.record_learning(uid, "triangle_basics", score=0.9, time_spent=15)
        self.engine.record_learning(uid, "pythagorean", score=0.3, time_spent=60)
        self.engine.record_learning(uid, "circle_area", score=0.1, time_spent=80)
        self.engine.record_learning(uid, "mean_median", score=0.85, time_spent=20)

        profile = self.engine.get_student_profile(uid)

        assert len(profile["error_history"]) == 2
        error_nodes = {e["node_id"] for e in profile["error_history"]}
        assert "pythagorean" in error_nodes
        assert "circle_area" in error_nodes
        assert "triangle_basics" not in error_nodes
        assert "mean_median" not in error_nodes

    # ---------- test_profile_caching ----------

    def test_profile_cached_until_new_learning(self):
        """画像缓存在学习活动后自动失效"""
        uid = "cache_test"
        self.engine.record_learning(uid, "triangle_basics", score=0.9)
        profile1 = self.engine.get_student_profile(uid)
        master_before = profile1["mastery_scores"].get("triangle_basics", 0)

        # 再次学习同一节点
        self.engine.update_profile_after_learning(uid, "triangle_basics", score=0.5, time_spent=30)

        profile2 = self.engine.get_student_profile(uid)
        master_after = profile2["mastery_scores"].get("triangle_basics", 0)

        assert master_after != master_before

    def test_profile_includes_user_id(self):
        """画像中包含正确的用户ID"""
        uid = "specific_user_42"
        profile = self.engine.get_student_profile(uid)
        assert profile["user_id"] == uid
