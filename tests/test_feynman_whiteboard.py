# -*- coding: utf-8 -*-
"""
tests/test_feynman_whiteboard.py
费曼引擎白板推导集成单元测试
"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from framework.engines.feynman_engine import FeynmanEngine, MATH_TYPE_KEYWORDS


@pytest.fixture
def engine():
    return FeynmanEngine(model_name="dummy")


class TestDetectMathType:
    """测试数学知识点类型检测"""

    def test_math_calc_type(self, engine):
        node = {"name": "导数", "description": "求导数计算"}
        assert engine.detect_math_type(node, "") == "math_calc"

    def test_math_proof_type(self, engine):
        node = {"name": "勾股定理", "description": "几何证明"}
        assert engine.detect_math_type(node, "") == "math_proof"

    def test_math_concept_type(self, engine):
        node = {"name": "函数单调性", "description": "函数性质理解"}
        assert engine.detect_math_type(node, "") == "math_concept"

    def test_topic_string(self, engine):
        assert engine.detect_math_type(None, "求导数") == "math_calc"

    def test_general_type(self, engine):
        assert engine.detect_math_type(None, "英语过去式") == "general"


class TestStep4WithWhiteboard:
    """测试带白板的第四步推导（使用 dummy 模型）"""

    def test_math_calc_generates_formula_svg(self, engine):
        result = engine._step4_derive_with_whiteboard(
            topic="导数定义",
            level="senior",
            knowledge_node={"name": "导数", "description": "求导数"}
        )
        assert result["step_name"] == "自主推导"
        assert result["step_order"] == 4
        assert result["math_type"] == "math_calc"
        assert result["whiteboard_svg"] is not None
        assert "<?xml version" in result["whiteboard_svg"]
        assert "</svg>" in result["whiteboard_svg"]

    def test_math_proof_generates_formula_svg(self, engine):
        result = engine._step4_derive_with_whiteboard(
            topic="勾股定理证明",
            level="senior",
            knowledge_node={"name": "勾股定理", "description": "几何证明"}
        )
        assert result["math_type"] == "math_proof"
        assert result["whiteboard_svg"] is not None
        assert "<?xml version" in result["whiteboard_svg"]

    def test_math_concept_geometry(self, engine):
        result = engine._step4_derive_with_whiteboard(
            topic="圆的面积",
            level="junior",
            knowledge_node={"name": "圆", "description": "圆的面积公式推导"}
        )
        assert result["math_type"] == "math_proof"
        assert result["whiteboard_svg"] is not None
        assert "<?xml version" in result["whiteboard_svg"]

    def test_non_math_no_whiteboard(self, engine):
        result = engine._step4_derive_with_whiteboard(
            topic="英语过去式",
            level="junior"
        )
        assert result["math_type"] == "general"
        assert result["whiteboard_svg"] is None

    def test_whiteboard_animation_data(self, engine):
        result = engine._step4_derive_with_whiteboard(
            topic="导数定义",
            level="senior",
            knowledge_node={"name": "导数", "description": "求导数"}
        )
        if result["whiteboard_animation"]:
            assert isinstance(result["whiteboard_animation"], list)
            assert len(result["whiteboard_animation"]) > 0
            for frame in result["whiteboard_animation"]:
                assert "step" in frame
                assert "content" in frame
                assert "delay" in frame

    def test_content_not_empty(self, engine):
        result = engine._step4_derive_with_whiteboard(
            topic="导数定义",
            level="junior"
        )
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0
