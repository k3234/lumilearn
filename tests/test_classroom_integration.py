# -*- coding: utf-8 -*-
"""
tests/test_classroom_integration.py
多智能体课堂集成端到端测试
"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from framework.engines.feynman_engine import FeynmanEngine
from framework.services.agent_classroom import AgentClassroom
from framework.services.whiteboard import WhiteboardEngine


@pytest.fixture
def engine():
    return FeynmanEngine(model_name="dummy")


@pytest.fixture
def classroom():
    return AgentClassroom()


@pytest.fixture
def whiteboard():
    return WhiteboardEngine()


class TestExplainWithWhiteboard:
    """测试 explain() 方法集成白板数据"""

    def test_math_calc_explain_includes_whiteboard(self, engine):
        result = engine.explain("导数定义", "senior", knowledge_node={"name": "导数", "description": "求导数"})
        assert result["topic"] == "导数定义"
        assert result["math_type"] == "math_calc"
        assert result["whiteboard_svg"] is not None
        assert "<?xml version" in result["whiteboard_svg"]
        assert "</svg>" in result["whiteboard_svg"]
        assert "whiteboard_animation" in result
        assert len(result["steps"]) == 5

    def test_math_proof_explain_includes_whiteboard(self, engine):
        result = engine.explain("勾股定理", "junior", knowledge_node={"name": "勾股定理", "description": "几何证明"})
        assert result["math_type"] == "math_proof"
        assert result["whiteboard_svg"] is not None
        assert "<?xml version" in result["whiteboard_svg"]

    def test_non_math_explain_no_whiteboard(self, engine):
        result = engine.explain("英语过去式", "junior")
        assert "whiteboard_svg" not in result or result.get("whiteboard_svg") is None
        assert "math_type" not in result or result.get("math_type") == "general"

    def test_explain_steps_structure(self, engine):
        result = engine.explain("导数定义", "senior")
        assert len(result["steps"]) == 5
        step_names = [s["step_name"] for s in result["steps"]]
        assert "现象引入" in step_names
        assert "自主推导" in step_names
        assert "费曼测试" in step_names


class TestClassroomDialogue:
    """测试多智能体课堂对话生成"""

    def test_generate_dialogue(self, classroom):
        dialogue = classroom.generate_classroom_dialogue("勾股定理", {"name": "勾股定理", "tags": ["几何", "证明"]}, max_turns=5)
        assert isinstance(dialogue, list)
        assert len(dialogue) == 5
        roles = [d["role"] for d in dialogue]
        assert "teacher" in roles
        assert "peer" in roles
        assert "ta" in roles

    def test_role_distribution(self, classroom):
        dist = classroom.distribute_speaking_roles(list(range(6)))
        assert dist["teacher"] == 4
        assert dist["peer"] == 2
        assert dist["ta"] == 0
        assert sum(dist.values()) == 6

    def test_peer_question_generated(self, classroom):
        question = classroom.generate_peer_question("勾股定理", {"name": "勾股定理", "tags": ["几何", "证明"]})
        assert isinstance(question, str)
        assert len(question) > 0

    def test_empty_distribution(self, classroom):
        dist = classroom.distribute_speaking_roles([])
        assert dist == {"teacher": 0, "peer": 0, "ta": 0}
