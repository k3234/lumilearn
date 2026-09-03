# -*- coding: utf-8 -*-
"""
多智能体课堂角色系统
====================
实现 TeacherAgent、PeerAgent、TAAgent 三个角色，
并通过 AgentClassroom 编排课堂对话流程。

作者：LumiLearn
版本：1.0.0
日期：2026-09-03
"""

import hashlib
from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Optional


# ============================================================
# Agent 数据类定义
# ============================================================

@dataclass
class TeacherAgent:
    """主讲教师，风格稳重、条理清晰"""
    personality: str = "严谨负责、循循善诱"
    speaking_style: str = "条理清晰、循序渐进"
    knowledge_level: str = "advanced"
    name: str = "老师"


@dataclass
class PeerAgent:
    """AI 同学，主动提问、表达不同理解"""
    personality: str = "好奇心强、敢于质疑"
    speaking_style: str = "直接、带有疑惑和探索精神"
    knowledge_level: str = "beginner"
    name: str = "小明"


@dataclass
class TAAgent:
    """AI 助教，辅助答疑、补充说明、总结要点"""
    personality: str = "耐心细致、善于归纳"
    speaking_style: str = "简洁明了、重点突出"
    knowledge_level: str = "intermediate"
    name: str = "助教"


# ============================================================
# 课堂编排主类
# ============================================================

@dataclass
class AgentClassroom:
    """多智能体课堂编排器"""

    teacher: TeacherAgent = field(default_factory=TeacherAgent)
    peer: PeerAgent = field(default_factory=PeerAgent)
    ta: TAAgent = field(default_factory=TAAgent)

    # 发言权重比例（teacher : peer : ta）
    ROLE_WEIGHTS: ClassVar[Dict[str, float]] = {
        "teacher": 0.6,
        "peer": 0.25,
        "ta": 0.15,
    }

    # 知识点类型识别关键词
    CALC_KEYWORDS: ClassVar[List[str]] = [
        "推导", "计算", "公式", "证明", "方程", "求解", "积分", "导数",
        "极限", "求和", "展开", "化简", "代入", "解不等式", "解方程",
    ]
    CONCEPT_KEYWORDS: ClassVar[List[str]] = [
        "定义", "概念", "什么是", "区别", "对比", "性质", "特征",
        "定理", "公理", "法则", "意义", "本质", "内涵",
    ]
    GEOMETRY_KEYWORDS: ClassVar[List[str]] = [
        "图形", "几何", "三角形", "圆", "正方形", "长方形", "角度",
        "坐标", "对称", "旋转", "平移", "投影", "抛物线", "椭圆",
        "立体", "体积", "表面积", "截面",
    ]

    # 各类型对应的提问模板
    CALC_QUESTION_TEMPLATES: ClassVar[List[str]] = [
        "老师，这一步是怎么推导出来的？能详细讲一下吗？",
        "这个公式是怎么来的？推导过程能再展开一遍吗？",
        "这一步变形是怎么想到的？有没有其他推导方法？",
        "为什么这里可以这样化简？推导依据是什么？",
        "这个计算结果的由来能详细说明吗？我有点跟不上。",
    ]
    CONCEPT_QUESTION_TEMPLATES: ClassVar[List[str]] = [
        "这个定义和之前的 {prev_topic} 概念有什么区别？",
        "{topic} 和我们学过的 {prev_topic} 有什么不同？",
        "这两个概念的边界在哪里？能对比一下吗？",
        "这个性质是怎么定义的？和以前的 {prev_topic} 有什么联系？",
        "我觉得 {topic} 和 {prev_topic} 好像很像，它们到底有什么区别？",
    ]
    GEOMETRY_QUESTION_TEMPLATES: ClassVar[List[str]] = [
        "为什么图形会变成这样？能解释一下吗？",
        "这个几何图形为什么会这样变化？背后的原理是什么？",
        "为什么旋转之后图形变成了这个样子？",
        "这个图形的性质是怎么来的？为什么是这样的？",
        "图形发生变换的条件是什么？为什么必须满足这些条件？",
    ]

    def generate_peer_question(self, topic: str, knowledge_node: dict) -> str:
        """
        根据知识点类型生成 AI 同学的合理疑问。

        对于计算类知识点：问"这一步是怎么推导出来的？"
        对于概念类知识点：问"这个定义和之前的XX概念有什么区别？"
        对于几何类知识点：问"为什么图形会变成这样？"

        Args:
            topic: 当前学习主题
            knowledge_node: 知识点字典，包含 type / tags / category 等字段

        Returns:
            生成的疑问字符串
        """
        qtype = self._detect_question_type(topic, knowledge_node)

        if qtype == "calc":
            return self._pick_template(self.CALC_QUESTION_TEMPLATES, topic)
        elif qtype == "concept":
            prev_topic = self._infer_previous_topic(topic, knowledge_node)
            template = self._pick_template(self.CONCEPT_QUESTION_TEMPLATES, prev_topic)
            return template.format(topic=topic, prev_topic=prev_topic)
        else:  # geometry
            return self._pick_template(self.GEOMETRY_QUESTION_TEMPLATES, topic)

    def distribute_speaking_roles(self, lesson_plan: list) -> dict:
        """
        按 60%/25%/15% 比例分配发言权重。

        Args:
            lesson_plan: 教学环节列表，每个元素代表一个教学步骤

        Returns:
            {"teacher": count, "peer": count, "ta": count}
        """
        total = len(lesson_plan)
        if total == 0:
            return {"teacher": 0, "peer": 0, "ta": 0}
        teacher_count = round(total * self.ROLE_WEIGHTS["teacher"])
        peer_count = round(total * self.ROLE_WEIGHTS["peer"])
        # ta 取余数，保证三者之和等于 lesson_plan 长度
        ta_count = total - teacher_count - peer_count
        # 防止 ta_count 为负
        ta_count = max(ta_count, 0)

        return {
            "teacher": teacher_count,
            "peer": peer_count,
            "ta": ta_count,
        }

    def generate_classroom_dialogue(
        self,
        topic: str,
        knowledge_node: dict,
        max_turns: int = 5,
    ) -> list:
        """
        生成课堂对话脚本。

        标准流程：
          1. Teacher 开场讲解
          2. Peer 提出疑问
          3. Teacher 回应
          4. TA 补充说明
          5. 重复直至达到 max_turns

        Args:
            topic: 当前学习主题
            knowledge_node: 知识点字典
            max_turns: 最大对话轮数

        Returns:
            [{"role": "teacher"/"peer"/"ta", "content": "..."}, ...]
        """
        distribution = self.distribute_speaking_roles(list(range(max_turns)))
        role_order = self._build_role_sequence(distribution, max_turns)
        dialogue = []

        question = self.generate_peer_question(topic, knowledge_node)

        for i, role in enumerate(role_order):
            if role == "teacher":
                content = self._teacher_turn(topic, knowledge_node, i)
            elif role == "peer":
                content = question
            elif role == "ta":
                content = self._ta_turn(topic, knowledge_node, dialogue)
            else:
                continue

            dialogue.append({"role": role, "content": content})

        return dialogue

    # ---------- 私有辅助方法 ----------

    def _detect_question_type(self, topic: str, knowledge_node: dict) -> str:
        """识别知识点类型，返回 calc / concept / geometry"""
        tags: list = knowledge_node.get("tags", [])
        category: str = knowledge_node.get("category", "").lower()
        node_type: str = knowledge_node.get("type", "").lower()
        combined = (topic + " " + category + " " + node_type
                    + " " + " ".join(str(t) for t in tags)).lower()

        for kw in self.CALC_KEYWORDS:
            if kw in combined:
                return "calc"
        for kw in self.CONCEPT_KEYWORDS:
            if kw in combined:
                return "concept"
        for kw in self.GEOMETRY_KEYWORDS:
            if kw in combined:
                return "geometry"
        return "concept"  # 默认按概念类处理

    def _infer_previous_topic(self, topic: str, knowledge_node: dict) -> str:
        """从先修知识或标签中推断前序主题"""
        prereqs: list = knowledge_node.get("prerequisites", [])
        if prereqs:
            return prereqs[0]
        tags: list = knowledge_node.get("tags", [])
        if tags:
            return str(tags[0])
        return "相关知识点"

    def _pick_template(self, templates: list, *format_args) -> str:
        """从模板列表中按确定性哈希选取，确保相同输入始终返回同一模板"""
        h = int(hashlib.md5(str(format_args).encode()).hexdigest(), 16) % len(templates)
        return templates[h]

    def _teacher_turn(self, topic: str, knowledge_node: dict, turn: int) -> str:
        """生成教师的讲解内容"""
        explanations = {
            0: (
                f"同学们好，今天我们一起来学习「{topic}」。"
                f"这个知识点是本章的核心内容，请大家认真听讲。"
            ),
            1: (
                f"接下来，我们来深入理解「{topic}」的关键步骤。"
                f"请大家注意我板书上的推导过程。"
            ),
            2: (
                f"关于「{topic}」，有一个非常重要的结论需要注意。"
                f"它的适用条件是 {knowledge_node.get('description', '满足基本定义即可')}。"
            ),
            3: (
                f"让我们回顾一下「{topic}」的学习要点。"
                f"掌握这个知识需要反复练习，不要急于求成。"
            ),
            4: (
                f"今天的「{topic}」就讲到这里。"
                f"同学们课后要完成对应的练习题，巩固所学内容。"
            ),
        }
        return explanations.get(turn % len(explanations),
                                f"关于「{topic}」，请同学们注意核心要点。")

    def _ta_turn(self, topic: str, knowledge_node: dict, dialogue: list) -> str:
        """生成助教的补充说明"""
        key_points = knowledge_node.get("key_points", [])
        if key_points:
            points_str = "、".join(str(p) for p in key_points[:3])
            return (
                f"我来总结一下本节的要点：{points_str}。"
                f"这些是「{topic}」中最容易出错的地方，请大家重点关注。"
            )
        prev_teacher = [d for d in dialogue if d["role"] == "teacher"]
        last = prev_teacher[-1]["content"] if prev_teacher else ""
        return (
            f"针对刚才老师讲的内容，我再补充两点：第一，"
            f"要注意概念的细节；第二，多做练习才能熟练掌握。"
        )

    def _build_role_sequence(self, distribution: dict, max_turns: int) -> list:
        """
        根据发言分配比例，构建角色顺序列表。
        尽量按 teacher(60%)、peer(25%)、ta(15%) 的比例交替出现。
        """
        teacher_q = distribution["teacher"]
        peer_q = distribution["peer"]
        ta_q = distribution["ta"]

        weights = ["teacher"] * teacher_q + ["peer"] * peer_q + ["ta"] * ta_q
        # 固定种子，保证可复现性
        seed = int(hashlib.sha256(str(max_turns).encode()).hexdigest(), 16)
        # 简单确定性打乱
        shuffled = sorted(weights, key=lambda x: int(hashlib.md5(
            f"{seed}{x}{max_turns}".encode()
        ).hexdigest(), 16))

        # 确保第一个是 teacher
        if shuffled and shuffled[0] != "teacher":
            teacher_idx = next(i for i, r in enumerate(shuffled) if r == "teacher")
            shuffled[0], shuffled[teacher_idx] = shuffled[teacher_idx], shuffled[0]

        return shuffled[:max_turns]
