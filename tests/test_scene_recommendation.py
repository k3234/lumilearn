# -*- coding: utf-8 -*-
"""
tests/test_scene_recommendation.py
场景类型自动分配单元测试
"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from framework.services.personalized_interaction import (
    PersonalizedInteractionEngine, SCENE_TYPES
)


@pytest.fixture
def engine():
    return PersonalizedInteractionEngine()


@pytest.fixture
def visual_profile():
    return {"learning_style": "visual", "weaknesses": []}


@pytest.fixture
def logical_profile():
    return {"learning_style": "logical", "weaknesses": []}


@pytest.fixture
def weak_profile():
    return {"learning_style": "", "weaknesses": [{"topic": "a"}, {"topic": "b"}, {"topic": "c"}]}


class TestSceneTypeBasic:
    """测试基础场景推荐逻辑"""

    def test_calc_recommends_whiteboard(self, engine):
        node = {"name": "导数", "description": "求导数计算"}
        assert engine.recommend_scene_type(node, {}) == "whiteboard"

    def test_proof_recommends_whiteboard(self, engine):
        node = {"name": "勾股定理", "description": "几何证明"}
        assert engine.recommend_scene_type(node, {}) == "whiteboard"

    def test_concept_recommends_slide(self, engine):
        node = {"name": "函数单调性", "description": "函数性质理解"}
        assert engine.recommend_scene_type(node, {}) == "slide"

    def test_grammar_recommends_slide(self, engine):
        node = {"name": "语法", "description": "英语语法讲解"}
        assert engine.recommend_scene_type(node, {}) == "slide"

    def test_vocabulary_recommends_quiz(self, engine):
        node = {"name": "词汇", "description": "英语单词"}
        assert engine.recommend_scene_type(node, {}) == "quiz"


class TestLearningStyleAdjustment:
    """测试学习者风格调整"""

    def test_visual_learns_simulation(self, engine, visual_profile):
        node = {"name": "导数", "description": "求导数计算"}
        result = engine.recommend_scene_type(node, visual_profile)
        assert result == "simulation"

    def test_visual_slide_to_simulation(self, engine, visual_profile):
        node = {"name": "函数单调性", "description": "函数性质理解"}
        result = engine.recommend_scene_type(node, visual_profile)
        assert result == "simulation"

    def test_logical_learns_whiteboard(self, engine, logical_profile):
        node = {"name": "函数单调性", "description": "函数性质理解"}
        result = engine.recommend_scene_type(node, logical_profile)
        assert result == "whiteboard"


class TestWeaknessAdjustment:
    """测试薄弱点调整"""

    def test_many_weaknesses_downgrade_to_slide(self, engine, weak_profile):
        node = {"name": "导数", "description": "求导数计算"}
        result = engine.recommend_scene_type(node, weak_profile)
        assert result == "slide"

    def test_few_weaknesses_no_change(self, engine):
        node = {"name": "导数", "description": "求导数计算"}
        profile = {"learning_style": "", "weaknesses": [{"topic": "a"}]}
        result = engine.recommend_scene_type(node, profile)
        assert result == "whiteboard"


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_node(self, engine):
        result = engine.recommend_scene_type({}, {})
        assert result in SCENE_TYPES

    def test_empty_profile(self, engine):
        node = {"name": "导数", "description": "求导数"}
        result = engine.recommend_scene_type(node, {})
        assert result in SCENE_TYPES

    def test_returns_valid_scene_type(self, engine):
        node = {"name": "任意主题", "description": "测试"}
        for profile in [{}, {"learning_style": "visual"}, {"learning_style": "logical"}]:
            result = engine.recommend_scene_type(node, profile)
            assert result in SCENE_TYPES


class TestInferMathType:
    """测试数学类型推断"""

    def test_calc_keywords(self, engine):
        assert engine._infer_math_type("导数 求导 极限") == "math_calc"

    def test_proof_keywords(self, engine):
        assert engine._infer_math_type("证明 定理 勾股") == "math_proof"

    def test_concept_keywords(self, engine):
        assert engine._infer_math_type("函数 定义域 值域") == "math_concept"

    def test_general_fallback(self, engine):
        assert engine._infer_math_type("英语语法") == "general"
