# -*- coding: utf-8 -*-
"""
个性化互动策略引擎
基于学生画像动态选择引导策略、生成个性化提示、推荐学习路径
"""

from typing import Dict, List, Optional

# 场景类型
SCENE_TYPES = ["slide", "whiteboard", "simulation", "quiz"]

# 知识点类型到默认场景的映射
TOPIC_TYPE_TO_SCENE = {
    "math_concept": "slide",       # 概念理解 → 幻灯片
    "math_calc": "whiteboard",     # 计算推导 → 白板
    "math_proof": "whiteboard",    # 逻辑证明 → 白板
    "geometry": "simulation",      # 几何 → 交互模拟
    "algebra": "whiteboard",       # 代数 → 白板
    "function": "simulation",      # 函数 → 交互模拟
    "probability": "slide",        # 概率 → 幻灯片
    "mechanics": "simulation",     # 力学 → 交互模拟
    "electromagnetism": "simulation",  # 电磁 → 交互模拟
    "grammar": "slide",            # 语法 → 幻灯片
    "vocabulary": "quiz",          # 词汇 → 测验
    "reaction": "simulation",      # 化学反应 → 交互模拟
}


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

    def recommend_scene_type(self, knowledge_node: Dict,
                              profile: Dict) -> str:
        """根据知识节点和学习者画像推荐最佳场景类型。

        推荐逻辑：
        1. 根据知识节点的数学子类型或主题类型映射默认场景
        2. 视觉型学习者优先 simulation
        3. 逻辑型学习者优先 whiteboard
        4. 薄弱点较多时优先 slide（低认知负荷）

        参数：
            knowledge_node: 知识节点字典，含 'category'/'description'/'name' 等
            profile: 学习者画像，含 'learning_style'/'weaknesses' 等

        返回：
            场景类型字符串：slide / whiteboard / simulation / quiz
        """
        name = knowledge_node.get("name", "") or ""
        desc = knowledge_node.get("description", "") or ""
        category = knowledge_node.get("category", "") or ""
        source = f"{name} {desc} {category}".lower()

        subject = self._infer_subject(source)
        if subject and subject in TOPIC_TYPE_TO_SCENE:
            scene = TOPIC_TYPE_TO_SCENE[subject]
        else:
            math_type = self._infer_math_type(source)
            scene = TOPIC_TYPE_TO_SCENE.get(math_type, "slide")

        learning_style = profile.get("learning_style", "")
        weaknesses = profile.get("weaknesses", [])

        if learning_style == "visual" and scene in ("slide", "whiteboard"):
            scene = "simulation"
        elif learning_style == "logical" and scene == "slide":
            scene = "whiteboard"

        if len(weaknesses) >= 3:
            scene = "slide"

        return scene

    def _infer_subject(self, source: str) -> str:
        """从文本推断学科类型，仅对非数学学科进行拦截（避免与数学类型推断冲突）。"""
        subject_keywords = {
            "vocabulary": ["词汇", "单词", "单词表", "词汇量", "英语单词", "词汇练习"],
            "grammar": ["语法", "时态", "语态", "从句", "介词用法", "英语语法", "语法规则"],
            "mechanics": ["物理力学", "牛顿定律", "受力分析"],
            "electromagnetism": ["电磁感应", "电路分析", "电场强度"],
            "reaction": ["化学反应", "化学方程式", "氧化还原", "酸碱中和", "化学实验"],
        }
        best_subject = ""
        best_score = 0
        for subj, keywords in subject_keywords.items():
            score = sum(1 for kw in keywords if kw in source)
            if score > best_score:
                best_score = score
                best_subject = subj
        return best_subject

    def _infer_math_type(self, source: str) -> str:
        """从文本推断数学知识点类型。"""
        from framework.engines.feynman_engine import MATH_TYPE_KEYWORDS
        best_type = "general"
        best_score = 0
        for mtype, keywords in MATH_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in source)
            if score > best_score:
                best_score = score
                best_type = mtype
        return best_type
