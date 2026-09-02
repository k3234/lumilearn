# -*- coding: utf-8 -*-
"""
个性化互动策略引擎
基于学生画像动态选择引导策略、生成个性化提示、推荐学习路径
"""

from typing import Dict, List, Optional


class PersonalizedInteractionEngine:
    """个性化互动策略引擎"""

    def __init__(self):
        self.strategies = {
            "foundation": "基础强化型",
            "analogy": "类比引导型",
            "deduction": "推导引导型",
            "practice": "练习强化型"
        }

    def select_feynman_strategy(self, topic: str, profile: Dict) -> str:
        """根据画像选择费曼引导策略

        优先级：薄弱点 → 学习风格 → 默认(类比引导)
        """
        weaknesses = profile.get("weaknesses", [])
        learning_style = profile.get("learning_style", "")

        # 1. 检查是否有当前 topic 相关薄弱点
        for weak in weaknesses:
            weak_topic = weak.get("topic", "") or weak.get("node_id", "")
            if weak_topic and weak_topic in topic:
                return "foundation"

        # 2. 按学习风格选择
        style_map = {
            "visual": "analogy",
            "logical": "deduction",
            "practice": "practice",
        }
        if learning_style in style_map:
            return style_map[learning_style]

        # 3. 默认
        return "analogy"

    def generate_personalized_hint(self, topic: str, profile: Dict,
                                   error_history: List[Dict]) -> str:
        """生成个性化提示

        从 error_history 中提取与 topic 相关的错题，结合薄弱点生成提示
        """
        weak_topics = [
            w.get("topic", "") or w.get("node_id", "")
            for w in profile.get("weaknesses", [])
        ]

        def _err_topic(err):
            return err.get("topic", "") or err.get("node_id", "")

        related_errors = [
            e for e in error_history
            if any(
                _err_topic(e) == wt
                or _err_topic(e) in wt
                or wt in _err_topic(e)
                for wt in weak_topics
            )
        ]

        if not related_errors:
            related_errors = [
                e for e in error_history
                if topic in _err_topic(e) or _err_topic(e) in topic
            ]

        if not related_errors:
            return f"学习【{topic}】时，请放慢节奏，把核心概念先理解清楚。"

        error_msgs = [
            err.get("message", "") or err.get("error", "") or err.get("content", "")
            for err in related_errors[-3:]
        ]
        error_msgs = [m for m in error_msgs if m]

        if error_msgs:
            hint = " ".join(error_msgs[:2])
            return f"回顾之前的错题：{hint}。建议在理解基础概念后重新尝试。"

        return f"学习【{topic}】时，请放慢节奏，把核心概念先理解清楚。"

    def recommend_next_topic(self, profile: Dict,
                             knowledge_graph: Dict) -> str:
        """基于薄弱点推荐下一步学习主题

        返回掌握度最低且先决条件已满足的知识点
        """
        mastered = profile.get("mastery", {})

        candidates = []
        for node_id, node_info in knowledge_graph.items():
            current_mastery = mastered.get(node_id, 0.0)

            # 已掌握的节点跳过
            if current_mastery >= 0.8:
                continue

            prereqs = node_info.get("prerequisites", [])

            prereqs_met = all(
                mastered.get(p, 0.0) >= 0.7 for p in prereqs
            ) if prereqs else True

            if prereqs_met:
                candidates.append({
                    "node_id": node_id,
                    "name": node_info.get("name", node_id),
                    "mastery": current_mastery,
                    "prerequisites": prereqs,
                })

        if not candidates:
            return ""

        candidates.sort(key=lambda x: x["mastery"])
        return candidates[0]["node_id"]
