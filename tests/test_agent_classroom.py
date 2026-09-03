# -*- coding: utf-8 -*-
"""
tests/test_agent_classroom.py
多智能体课堂角色系统 单元测试
覆盖：Agent 创建、属性校验、提问生成、角色分配、对话生成
"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from framework.services.agent_classroom import (
    AgentClassroom,
    PeerAgent,
    TAAgent,
    TeacherAgent,
)

# ---------- 固定知识点数据 ----------

CALC_NODE = {
    "id": "derivative",
    "name": "导数",
    "category": "algebra",
    "type": "calc",
    "tags": ["导数", "公式", "推导", "极限"],
    "description": "导数是函数在某一点的瞬时变化率",
    "prerequisites": ["极限", "函数"],
    "key_points": ["极限定义", "几何意义", "求导公式"],
}

CONCEPT_NODE = {
    "id": "function_def",
    "name": "函数定义",
    "category": "algebra",
    "type": "concept",
    "tags": ["定义", "概念", "映射"],
    "description": "函数是两个集合之间的一种对应关系",
    "prerequisites": ["集合", "映射"],
    "key_points": ["定义域", "值域", "对应法则"],
}

GEOMETRY_NODE = {
    "id": "triangle_angle",
    "name": "三角形内角和",
    "category": "geometry",
    "type": "geometry",
    "tags": ["三角形", "角度", "几何"],
    "description": "三角形三个内角之和等于 180 度",
    "prerequisites": ["角度", "平行线"],
    "key_points": ["内角和定理", "外角定理"],
}

SAMPLE_LESSON_PLAN = ["引入", "讲解", "提问", "练习", "总结"]


# ============================================================
# Agent 创建测试
# ============================================================

class TestTeacherAgentCreation:
    def test_teacher_agent_creation(self):
        agent = TeacherAgent()
        assert isinstance(agent, TeacherAgent)
        assert agent.name == "老师"
        assert agent.knowledge_level == "advanced"

    def test_teacher_agent_custom(self):
        agent = TeacherAgent(
            personality="幽默风趣",
            speaking_style="生动活泼",
            knowledge_level="advanced",
        )
        assert agent.personality == "幽默风趣"
        assert agent.speaking_style == "生动活泼"


class TestPeerAgentCreation:
    def test_peer_agent_creation(self):
        agent = PeerAgent()
        assert isinstance(agent, PeerAgent)
        assert agent.name == "小明"
        assert agent.knowledge_level == "beginner"

    def test_peer_agent_custom(self):
        agent = PeerAgent(
            personality="爱思考",
            speaking_style="质疑精神",
            knowledge_level="beginner",
        )
        assert agent.personality == "爱思考"
        assert agent.knowledge_level == "beginner"


class TestTAAgentCreation:
    def test_ta_agent_creation(self):
        agent = TAAgent()
        assert isinstance(agent, TAAgent)
        assert agent.name == "助教"
        assert agent.knowledge_level == "intermediate"

    def test_ta_agent_custom(self):
        agent = TAAgent(
            personality="温和耐心",
            speaking_style="条理清晰",
            knowledge_level="intermediate",
        )
        assert agent.personality == "温和耐心"
        assert agent.knowledge_level == "intermediate"


class TestAgentAttributes:
    def test_all_agents_have_three_attributes(self):
        """每个 Agent 都必须有 personality / speaking_style / knowledge_level"""
        for agent_cls in (TeacherAgent, PeerAgent, TAAgent):
            agent = agent_cls()
            assert isinstance(agent.personality, str) and agent.personality
            assert isinstance(agent.speaking_style, str) and agent.speaking_style
            assert agent.knowledge_level in ("beginner", "intermediate", "advanced")

    def test_teacher_is_advanced(self):
        assert TeacherAgent().knowledge_level == "advanced"

    def test_peer_is_beginner(self):
        assert PeerAgent().knowledge_level == "beginner"

    def test_ta_is_intermediate(self):
        assert TAAgent().knowledge_level == "intermediate"


# ============================================================
# generate_peer_question 测试
# ============================================================

class TestGeneratePeerQuestion:
    def test_generate_peer_question_calc(self):
        """计算类：应出现推导/公式相关关键词"""
        room = AgentClassroom()
        q = room.generate_peer_question("导数", CALC_NODE)
        assert isinstance(q, str) and len(q) > 0
        assert "推导" in q or "公式" in q or "计算" in q

    def test_generate_peer_question_concept(self):
        """概念类：应出现区别/定义相关关键词，并引用前序主题"""
        room = AgentClassroom()
        q = room.generate_peer_question("函数定义", CONCEPT_NODE)
        assert isinstance(q, str) and len(q) > 0
        assert "区别" in q or "定义" in q or "以前" in q

    def test_generate_peer_question_geometry(self):
        """几何类：应出现图形/变化相关关键词"""
        room = AgentClassroom()
        q = room.generate_peer_question("三角形内角和", GEOMETRY_NODE)
        assert isinstance(q, str) and len(q) > 0
        assert "图形" in q or "为什么" in q or "这样" in q

    def test_question_type_detection_calc(self):
        room = AgentClassroom()
        assert room._detect_question_type("导数计算", CALC_NODE) == "calc"

    def test_question_type_detection_concept(self):
        room = AgentClassroom()
        assert room._detect_question_type("函数定义", CONCEPT_NODE) == "concept"

    def test_question_type_detection_geometry(self):
        room = AgentClassroom()
        assert room._detect_question_type("三角形内角和", GEOMETRY_NODE) == "geometry"

    def test_question_default_to_concept(self):
        """无匹配关键词时默认返回 concept"""
        room = AgentClassroom()
        assert room._detect_question_type("随机话题", {"tags": [], "category": ""}) == "concept"


# ============================================================
# distribute_speaking_roles 测试
# ============================================================

class TestDistributeSpeakingRoles:
    def test_distribute_speaking_roles(self):
        room = AgentClassroom()
        result = room.distribute_speaking_roles(SAMPLE_LESSON_PLAN)
        assert set(result.keys()) == {"teacher", "peer", "ta"}
        assert isinstance(result["teacher"], int)
        assert isinstance(result["peer"], int)
        assert isinstance(result["ta"], int)

    def test_distribute_ratios_approximately_correct(self):
        room = AgentClassroom()
        # 10 个环节 → 期望 teacher≈6, peer≈3, ta≈1
        result = room.distribute_speaking_roles(list(range(10)))
        assert result["teacher"] == 6
        assert result["peer"] == 2 or result["peer"] == 3
        assert result["ta"] == 1 or result["ta"] == 2
        assert result["teacher"] + result["peer"] + result["ta"] == 10

    def test_distribute_empty_plan(self):
        room = AgentClassroom()
        result = room.distribute_speaking_roles([])
        assert result["teacher"] == 0
        assert result["peer"] == 0
        assert result["ta"] == 0


# ============================================================
# generate_classroom_dialogue 测试
# ============================================================

class TestGenerateClassroomDialogue:
    def test_generate_classroom_dialogue(self):
        room = AgentClassroom()
        dialogue = room.generate_classroom_dialogue("导数", CALC_NODE, max_turns=4)
        assert isinstance(dialogue, list)
        assert len(dialogue) == 4
        for turn in dialogue:
            assert "role" in turn
            assert "content" in turn
            assert turn["role"] in ("teacher", "peer", "ta")
            assert isinstance(turn["content"], str) and len(turn["content"]) > 0

    def test_dialogue_always_starts_with_teacher(self):
        room = AgentClassroom()
        for turns in (3, 5, 7):
            dialogue = room.generate_classroom_dialogue("函数", CONCEPT_NODE, max_turns=turns)
            assert dialogue[0]["role"] == "teacher"

    def test_dialogue_role_distribution(self):
        room = AgentClassroom()
        dialogue = room.generate_classroom_dialogue("导数", CALC_NODE, max_turns=8)
        role_counts = {}
        for turn in dialogue:
            role_counts[turn["role"]] = role_counts.get(turn["role"], 0) + 1
        assert role_counts["teacher"] > role_counts["peer"]
        assert role_counts["teacher"] > role_counts["ta"]
        assert "peer" in role_counts
        assert "ta" in role_counts

    def test_dialogue_max_turns_respected(self):
        room = AgentClassroom()
        dialogue = room.generate_classroom_dialogue("几何", GEOMETRY_NODE, max_turns=3)
        assert len(dialogue) == 3

    def test_peer_question_appears_in_dialogue(self):
        room = AgentClassroom()
        dialogue = room.generate_classroom_dialogue("导数", CALC_NODE, max_turns=5)
        peer_turns = [d for d in dialogue if d["role"] == "peer"]
        assert len(peer_turns) >= 1
        content = peer_turns[0]["content"]
        assert len(content) > 0

    def test_full_workflow_calc(self):
        room = AgentClassroom()
        dialogue = room.generate_classroom_dialogue("导数", CALC_NODE, max_turns=6)
        assert len(dialogue) == 6
        assert dialogue[0]["role"] == "teacher"
        roles = [t["role"] for t in dialogue]
        assert "peer" in roles

    def test_full_workflow_geometry(self):
        room = AgentClassroom()
        dialogue = room.generate_classroom_dialogue("圆", GEOMETRY_NODE, max_turns=5)
        assert len(dialogue) == 5
        peer_turns = [d for d in dialogue if d["role"] == "peer"]
        assert any("图形" in d["content"] for d in peer_turns)


# ============================================================
# 集成测试
# ============================================================

class TestAgentClassroomIntegration:
    def test_full_workflow_calc(self):
        room = AgentClassroom()
        dialogue = room.generate_classroom_dialogue("导数", CALC_NODE, max_turns=6)
        assert len(dialogue) == 6
        assert dialogue[0]["role"] == "teacher"
        roles = [t["role"] for t in dialogue]
        assert "peer" in roles

    def test_full_workflow_geometry(self):
        room = AgentClassroom()
        dialogue = room.generate_classroom_dialogue("圆", GEOMETRY_NODE, max_turns=5)
        assert len(dialogue) == 5
        peer_turns = [d for d in dialogue if d["role"] == "peer"]
        assert any("图形" in d["content"] for d in peer_turns)
