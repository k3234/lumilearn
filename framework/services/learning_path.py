# -*- coding: utf-8 -*-
"""
L4 学习路径引擎 — 基于 BKT 的自适应学习路径生成

在 AdaptiveLearningEngine 的基础上，使用 BKT 掌握度替代简单的 EMA 掌握度，
实现真正的自适应学习路径。
"""

import json
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

from framework.services.adaptive_learning import (
    AdaptiveLearningEngine,
    KNOWLEDGE_GRAPH,
)
from framework.services.bkt_student_model import (
    StudentModel,
    get_student,
    BKT_DEFAULT_PRIOR,
)


@dataclass
class LearningStep:
    """学习路径中的单一步骤"""
    node_id: str
    name: str
    category: str
    difficulty: int
    mastery: float
    reason: str          # 为什么选这个节点
    estimated_time_min: int
    action: str          # "explain" | "practice" | "test" | "review"
    animation_type: str = "auto"


class AdaptivePathEngine:
    """
    自适应学习路径引擎（L3→L4 过渡）

    核心策略：
    1. 前置依赖检查：未掌握前置知识点则不开放后续知识点
    2. 薄弱点优先：掌握度最低的先学习
    3. BKT 动态调整：根据答题结果实时调整路径
    4. 认知状态感知：困惑/挫败时切换教学策略
    """

    def __init__(self, adaptive_engine: Optional[AdaptiveLearningEngine] = None):
        self.adaptive = adaptive_engine or AdaptiveLearningEngine()
        self._bkt_params: Dict[str, Dict] = {}

    def set_bkt_params(self, params: Dict[str, Dict]):
        """为特定知识点设置 BKT 参数（可覆盖默认值）"""
        self._bkt_params.update(params)

    def get_learning_path(self, student_id: str,
                          target_node_id: Optional[str] = None,
                          max_steps: int = 10) -> List[Dict]:
        """
        生成个性化学习路径

        策略：
        1. 从 target_node_id 逆向查找所有前置依赖
        2. 按拓扑排序，优先掌握度低的节点
        3. 标记每步的学习动作（讲解/练习/测试/复习）

        返回:
            List[LearningStep] 序列化的学习路径
        """
        student = get_student(student_id, self._bkt_params)
        graph = self.adaptive.graph

        # 1. 确定目标节点及其所有前置依赖
        target = target_node_id
        if not target:
            # 无目标时，选择掌握度最低且前置条件满足的节点
            target = self._find_lowest_mastery_target(student, graph)

        if not target or target not in graph:
            return []

        # 2. 收集所有需要学习的前置节点（BFS 逆向）
        needed_nodes = self._collect_prerequisites(target, graph, student)

        # 3. 按掌握度 + 拓扑排序生成路径
        path = []
        visited = set()

        while len(path) < max_steps and needed_nodes - visited:
            # 找入度为 0 的候选节点（所有前置已学习）
            candidates = []
            for nid in needed_nodes - visited:
                node = graph.get(nid)
                if not node:
                    continue
                prereqs_met = all(
                    student.get_mastery(pid) >= 0.7
                    for pid in node.prerequisites
                    if pid in needed_nodes
                )
                if prereqs_met:
                    mastery = student.get_mastery(nid)
                    candidates.append((nid, mastery, node))

            if not candidates:
                # 有未满足的前置，加入最低掌握度的候选
                remaining = needed_nodes - visited
                if not remaining:
                    break
                nid = min(remaining, key=lambda x: student.get_mastery(x))
                node = graph[nid]
                candidates = [(nid, student.get_mastery(nid), node)]

            # 按掌握度排序（最低优先）
            candidates.sort(key=lambda x: x[1])
            nid, mastery, node = candidates[0]

            # 确定学习动作
            action = self._determine_action(nid, mastery, student)

            path.append(LearningStep(
                node_id=nid,
                name=node.name,
                category=node.category,
                difficulty=node.difficulty,
                mastery=round(mastery, 3),
                reason=self._reason_for_choice(nid, mastery, node, student),
                estimated_time_min=node.difficulty * 5 + 3,
                action=action,
                animation_type=node.animation_type,
            ).__dict__)

            visited.add(nid)

        return path

    def _find_lowest_mastery_target(self, student: StudentModel,
                                    graph: Dict) -> Optional[str]:
        """找到掌握度最低且前置条件满足的节点"""
        best = None
        best_mastery = 1.0
        for nid, node in graph.items():
            if student.get_mastery(nid) >= 0.85:
                continue
            prereqs_met = all(
                student.get_mastery(pid) >= 0.7
                for pid in node.prerequisites
            )
            if prereqs_met:
                m = student.get_mastery(nid)
                if m < best_mastery:
                    best = nid
                    best_mastery = m
        return best

    def _collect_prerequisites(self, target_node_id: str,
                               graph: Dict,
                               student: StudentModel) -> set:
        """递归收集目标节点的所有前置依赖（排除已掌握的）"""
        result = set()
        stack = [target_node_id]
        while stack:
            nid = stack.pop()
            if nid in result:
                continue
            node = graph.get(nid)
            if not node:
                continue
            result.add(nid)
            for pid in node.prerequisites:
                if student.get_mastery(pid) < 0.7:
                    stack.append(pid)
        return result

    def _determine_action(self, node_id: str, mastery: float,
                          student: StudentModel) -> str:
        """根据掌握度推断学习动作"""
        if mastery < 0.1:
            return "explain"       # 从未学过 → 讲解
        elif mastery < 0.4:
            return "review"        # 学过了但不熟 → 复习
        elif mastery < 0.7:
            return "practice"      # 基本掌握 → 练习
        else:
            return "test"          # 接近掌握 → 测试

    def _reason_for_choice(self, node_id: str, mastery: float,
                           node, student: StudentModel) -> str:
        """生成选择此节点的理由（用于前端展示）"""
        if mastery < 0.1:
            return f"全新知识点，需要先学习【{node.name}】的基础概念"
        elif mastery < 0.4:
            graph = self.adaptive.graph
            prereqs = [graph[pid].name for pid in node.prerequisites
                       if pid in graph and student.get_mastery(pid) < 0.7]
            if prereqs:
                return f"前置知识点【{', '.join(prereqs)}】尚未完全掌握，建议先巩固"
            return f"【{node.name}】掌握度偏低，需要加强练习"
        elif mastery < 0.7:
            return f"【{node.name}】已有一定基础，通过练习进一步提升"
        else:
            return f"【{node.name}】接近掌握，通过测试验证"

    def generate_practice_set(self, student_id: str,
                              node_id: str,
                              count: int = 5) -> List[Dict]:
        """
        为指定知识点生成练习题目

        基于 BKT 预测的准确率和当前认知状态，动态选择题目难度。
        """
        student = get_student(student_id, self._bkt_params)
        mastery = student.get_mastery(node_id)
        cog = student.get_cognitive_state()

        # 根据掌握度和认知状态调整题目难度
        if mastery < 0.3 and cog.get("state") in ("confused", "frustrated"):
            base_difficulty = 1
            hint_mode = "heavy"
        elif mastery < 0.6:
            base_difficulty = 2
            hint_mode = "medium"
        else:
            base_difficulty = 3
            hint_mode = "light"

        # 返回模拟题目（实际项目中从题库中检索）
        return [{
            "question_id": f"{node_id}_q{i+1}",
            "difficulty": min(base_difficulty + i % 2, 5),
            "hint_mode": hint_mode,
            "estimated_time_sec": (base_difficulty + 1) * 30,
            "question_type": "multiple_choice" if base_difficulty <= 2 else "open_ended",
        } for i in range(count)]


# ============================================================
# 全局单例
# ============================================================
_path_engine: Optional[AdaptivePathEngine] = None


def get_path_engine() -> AdaptivePathEngine:
    global _path_engine
    if _path_engine is None:
        _path_engine = AdaptivePathEngine()
    return _path_engine
