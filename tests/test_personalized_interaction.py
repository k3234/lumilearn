# -*- coding: utf-8 -*-
"""
tests/test_personalized_interaction.py
PersonalizedInteractionEngine 单元测试
覆盖：策略选择、个性化提示生成、知识点推荐
"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from framework.services.personalized_interaction import PersonalizedInteractionEngine


@pytest.fixture
def engine():
    return PersonalizedInteractionEngine()


# ========== 策略选择测试 ==========

class TestSelectStrategy:
    """测试 select_feynman_strategy 方法"""

    def test_select_strategy_foundation(self, engine):
        """有薄弱点时选基础强化"""
        profile = {
            "weaknesses": [{"topic": "勾股定理", "mastery": 0.3}],
            "learning_style": "visual",
        }
        result = engine.select_feynman_strategy("勾股定理", profile)
        assert result == "foundation"

    def test_select_strategy_analogy(self, engine):
        """视觉型选类比引导"""
        profile = {
            "weaknesses": [],
            "learning_style": "visual",
        }
        result = engine.select_feynman_strategy("任意主题", profile)
        assert result == "analogy"

    def test_select_strategy_deduction(self, engine):
        """逻辑型选推导引导"""
        profile = {
            "weaknesses": [],
            "learning_style": "logical",
        }
        result = engine.select_feynman_strategy("任意主题", profile)
        assert result == "deduction"

    def test_select_strategy_practice(self, engine):
        """练习型选练习强化"""
        profile = {
            "weaknesses": [],
            "learning_style": "practice",
        }
        result = engine.select_feynman_strategy("任意主题", profile)
        assert result == "practice"

    def test_select_strategy_default(self, engine):
        """无薄弱点且无学习风格时默认类比引导"""
        profile = {
            "weaknesses": [],
            "learning_style": "",
        }
        result = engine.select_feynman_strategy("任意主题", profile)
        assert result == "analogy"

    def test_select_strategy_weakness_priority(self, engine):
        """薄弱点优先级高于学习风格"""
        profile = {
            "weaknesses": [{"topic": "导数", "mastery": 0.2}],
            "learning_style": "logical",
        }
        result = engine.select_feynman_strategy("导数应用", profile)
        assert result == "foundation"


# ========== 个性化提示测试 ==========

class TestGeneratePersonalizedHint:
    """测试 generate_personalized_hint 方法"""

    def test_hint_with_error_history(self, engine):
        """错题历史正确关联"""
        profile = {
            "weaknesses": [{"topic": "勾股定理", "node_id": "pythagorean"}],
        }
        error_history = [
            {
                "topic": "pythagorean",
                "message": "忘记验证是否为直角三角形",
            },
            {
                "topic": "pythagorean",
                "message": "计算错误",
            },
        ]
        result = engine.generate_personalized_hint("pythagorean", profile, error_history)
        assert "pythagorean" in result or "直角三角形" in result

    def test_hint_empty_history(self, engine):
        """空错题历史返回通用提示"""
        profile = {"weaknesses": []}
        result = engine.generate_personalized_hint("任意主题", profile, [])
        assert "放慢节奏" in result

    def test_hint_unrelated_error(self, engine):
        """无关错题不应干扰提示"""
        profile = {
            "weaknesses": [{"topic": "函数", "node_id": "function_concept"}],
        }
        error_history = [
            {
                "topic": "geometry",
                "message": "几何题计算错误",
            },
        ]
        result = engine.generate_personalized_hint("function_concept", profile, error_history)
        assert "放慢节奏" in result or "function_concept" in result


# ========== 知识点推荐测试 ==========

class TestRecommendNextTopic:
    """测试 recommend_next_topic 方法"""

    def test_recommend_next_topic(self, engine):
        """推荐逻辑正确"""
        profile = {
            "mastery": {
                "triangle_basics": 0.9,
                "pythagorean": 0.3,
                "circle_area": 0.0,
            }
        }
        knowledge_graph = {
            "triangle_basics": {
                "name": "三角形基础",
                "prerequisites": [],
            },
            "pythagorean": {
                "name": "勾股定理",
                "prerequisites": ["triangle_basics"],
            },
            "circle_area": {
                "name": "圆面积",
                "prerequisites": ["triangle_basics"],
            },
        }
        result = engine.recommend_next_topic(profile, knowledge_graph)
        assert result == "circle_area"

    def test_recommend_with_unmet_prereqs(self, engine):
        """前置条件未满足的节点不被推荐"""
        profile = {
            "mastery": {
                "triangle_basics": 0.5,
            }
        }
        knowledge_graph = {
            "triangle_basics": {
                "name": "三角形基础",
                "prerequisites": [],
            },
            "pythagorean": {
                "name": "勾股定理",
                "prerequisites": ["triangle_basics"],
            },
        }
        result = engine.recommend_next_topic(profile, knowledge_graph)
        assert result == "triangle_basics"

    def test_recommend_empty_graph(self, engine):
        """空知识图谱返回空字符串"""
        result = engine.recommend_next_topic({"mastery": {}}, {})
        assert result == ""

    def test_recommend_all_mastered(self, engine):
        """所有知识点都已掌握时返回空"""
        profile = {
            "mastery": {
                "triangle_basics": 0.9,
                "pythagorean": 0.9,
            }
        }
        knowledge_graph = {
            "triangle_basics": {"name": "三角形基础", "prerequisites": []},
            "pythagorean": {"name": "勾股定理", "prerequisites": ["triangle_basics"]},
        }
        result = engine.recommend_next_topic(profile, knowledge_graph)
        assert result == ""
