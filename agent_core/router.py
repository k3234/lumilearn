# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — Router / Triage Agent

职责：
  1. 分析用户输入的任务特征（学科、难度、复杂度）
  2. 判断任务类型：simple / standard / complex
  3. 根据 Google 研究结论选择合适的架构：
     - 顺序推理任务 → 单Agent（准确率高39-70%）
     - 并行化任务   → 多Agent并行（快30-50%）
  4. 预估成本并设置预算限制

路由规则：
  - simple   : 简单问答、定义解释 → 单模型（低成本）
  - standard : 概念理解、单一知识点 → FeynmanTeacher 单模型
  - complex  : 综合分析、多步骤推理 → 多Agent并行+反馈回路
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from agent_core.models import TaskProfile


# ================================================================
# 任务复杂度关键词
# ================================================================
SIMPLE_KEYWORDS = [
    "什么是", "定义", "解释", "简述", "列举", "写出",
    "含义", "意思", "概念", "有哪些", "列举",
]

COMPLEX_KEYWORDS = [
    "分析", "推导", "证明", "比较", "对比", "评价",
    "综合", "总结", "论证", "探讨", "研究", "为什么",
    "如何证明", "如何推导", "深入分析", "全面分析",
]

PARALLEL_KEYWORDS = [
    "对比", "比较", "同时", "分别", "各个", "多个",
    "不同", "差异", "异同", "优劣",
]

SEQUENTIAL_KEYWORDS = [
    "推导", "证明", "逐步", "依次", "首先", "然后",
    "接着", "最后", "步骤", "过程",
]

# 成本估算参数（Phase 4 成本感知路由）
# 以最低价模型（qwen2.5:7b ≈ 0.001 元/千token）估算路由成本上限
MODEL_UNIT_PRICE_PER_1K = 0.001


# ================================================================
# Router Agent
# ================================================================
class RouterAgent:
    """
    Router / Triage Agent — 任务复杂度评估与路由决策

    基于 Google 2026 研究（引用 [18]）：
      - 并行化任务：多Agent比单Agent快30-50%
      - 顺序推理任务：单Agent比多Agent准确39-70%

    Phase 4 成本感知：
      - route() 返回 estimated_cost（预估成本，元）
      - route_with_budget() 支持成本上限，超支自动降级
    """

    # 各路由默认 token 预算
    ROUTE_BUDGET = {
        "simple": 1000,
        "standard": 4000,
        "complex_parallel": 8000,
    }

    # 各路由默认调用次数
    ROUTE_CALLS = {
        "simple": 1,
        "standard": 5,
        "complex_parallel": 15,
    }

    # 降级链（成本超支时逐级降）
    DOWNGRADE_CHAIN = {
        "complex_parallel": "standard",
        "standard": "simple",
        "simple": None,
    }

    # 学科关键词映射（与 lumilearn_agent.py 保持一致）
    SUBJECT_KEYWORDS = {
        "数学": ["数学", "代数", "几何", "函数", "方程", "概率", "数列", "三角",
                 "向量", "矩阵", "导数", "积分", "不等式", "圆", "椭圆", "勾股",
                 "正余弦", "正弦", "余弦", "多项式", "微积分", "极限", "定理"],
        "物理": ["物理", "力学", "电", "磁", "光", "热", "声", "速度", "加速度",
                 "牛顿", "能量", "功率", "电压", "电流", "电阻", "磁场", "功",
                 "欧姆", "焦耳", "法拉第", "波", "粒子"],
        "化学": ["化学", "元素", "周期", "反应", "分子", "原子", "离子", "化合",
                 "分解", "酸", "碱", "盐", "氧化", "还原", "催化剂", "方程式",
                 "摩尔", "配平", "有机", "无机"],
        "英语": ["英语", "英文", "语法", "单词", "词汇", "写作", "阅读", "翻译",
                 "时态", "口语", "听力", "发音", "从句", "sentence", "grammar"],
        "语文": ["语文", "文言", "诗词", "阅读", "作文", "修辞", "成语", "病句",
                 "古文", "诗歌", "散文"],
    }

    # 难度指示词
    DIFFICULTY_INDICATORS = {
        "初中": ["初中", "初一", "初二", "初三", "中考"],
        "高中": ["高中", "高一", "高二", "高三", "高考", "会考"],
        "大学": ["大学", "高数", "微积分", "线性代数", "考研", "本科"],
    }

    def __init__(self, max_simple_calls: int = 3, max_complex_calls: int = 15):
        self.max_simple_calls = max_simple_calls
        self.max_complex_calls = max_complex_calls

    def analyze(self, user_input: str, context: str = "") -> TaskProfile:
        """
        分析用户输入，生成任务画像。

        Args:
            user_input: 用户原始输入
            context:    补充上下文

        Returns:
            TaskProfile: 任务画像
        """
        text = (user_input + " " + context).strip()
        if not text:
            return TaskProfile(raw_input=user_input)

        subject = self._detect_subject(text)
        topic = self._detect_topic(text)
        difficulty = self._detect_difficulty(text)
        complexity = self._detect_complexity(text)
        reasoning_type = self._detect_reasoning_type(text)
        keywords = self._extract_keywords(text)

        # 根据复杂度估算调用次数
        if complexity == "simple":
            estimated_calls = min(self.max_simple_calls, 3)
        elif complexity == "complex":
            estimated_calls = min(self.max_complex_calls, 15)
        else:
            estimated_calls = 5

        # 置信度
        confidence = 0.9 if subject != "综合" else 0.6
        if topic:
            confidence = min(1.0, confidence + 0.05)

        profile = TaskProfile(
            complexity=complexity,
            reasoning_type=reasoning_type,
            subject=subject,
            topic=topic,
            estimated_calls=estimated_calls,
            confidence=confidence,
            keywords=keywords,
            raw_input=user_input,
        )
        return profile

    def route(self, user_input: str, context: str = "") -> Dict:
        """
        执行完整路由决策。

        Returns:
            {
                "route": "simple" | "standard" | "complex_parallel",
                "profile": TaskProfile,
                "model_suggestion": str,
                "budget": int,  # 最大token预算
            }
        """
        profile = self.analyze(user_input, context)
        route = profile.route

        # 模型建议
        if route == "simple":
            model_suggestion = "cheap_fast"  # 使用轻量模型
        elif route == "complex_parallel":
            model_suggestion = "multi_model_parallel"  # 多模型并行
        else:
            model_suggestion = "standard"  # 标准单模型

        budget = self.ROUTE_BUDGET.get(route, 4000)

        return {
            "route": route,
            "profile": profile.to_dict(),
            "model_suggestion": model_suggestion,
            "budget": budget,
            "estimated_calls": profile.estimated_calls,
            "estimated_cost": self.estimate_cost(route),  # Phase 4 成本预估
        }

    def estimate_cost(self, route: str) -> float:
        """
        预估指定路由的单次任务成本（元，按最低价模型估算）。

        公式：token预算 × 2（输入+输出） × 单价/千token × 调用次数
        """
        budget = self.ROUTE_BUDGET.get(route, 4000)
        calls = self.ROUTE_CALLS.get(route, 5)
        return round(
            budget * 2 * MODEL_UNIT_PRICE_PER_1K / 1000 * calls, 6)

    def route_with_budget(self, user_input: str, context: str = "",
                          max_cost: float = 0.05) -> Dict:
        """
        成本感知路由：在成本上限内选择最合理的执行路径。

        参数：
            max_cost: 单次任务成本上限（元）。默认 0.05（≈$0.007）。

        规则：
            - 初始按复杂度路由；若预估成本超过上限，则沿降级链降级
              （complex_parallel → standard → simple），并在结果中标记 downgraded。

        返回：
            route() 结果 + {"downgraded": bool, "original_route": str}
        """
        decision = self.route(user_input, context)
        original = decision["route"]
        decision["original_route"] = original
        decision["downgraded"] = False

        while decision["estimated_cost"] > max_cost:
            next_route = self.DOWNGRADE_CHAIN.get(decision["route"])
            if next_route is None:
                break
            decision["route"] = next_route
            decision["downgraded"] = True
            decision["budget"] = self.ROUTE_BUDGET.get(next_route, 4000)
            decision["estimated_cost"] = self.estimate_cost(next_route)
            decision["estimated_calls"] = self.ROUTE_CALLS.get(next_route, 5)
            if next_route == "simple":
                decision["model_suggestion"] = "cheap_fast"
            else:
                decision["model_suggestion"] = "standard"

        if decision["downgraded"]:
            decision["downgrade_reason"] = (
                f"原路由 {original} 预估成本 "
                f"{self.estimate_cost(original)} 元超过上限 {max_cost} 元，"
                f"已降级为 {decision['route']}")
        return decision

    def should_use_multi_agent(self, user_input: str, context: str = "") -> bool:
        """
        判断是否应该使用多Agent架构。

        依据 Google 2026 研究：
          - 并行化任务 → 多Agent（无论复杂度）
          - 顺序推理任务 → 单Agent
        """
        profile = self.analyze(user_input, context)
        return profile.reasoning_type == "parallel"

    # ---------- 私有方法 ----------

    def _detect_subject(self, text: str) -> str:
        scores = {}
        for subject, keywords in self.SUBJECT_KEYWORDS.items():
            scores[subject] = sum(1 for kw in keywords if kw in text)
        if not any(scores.values()):
            return "综合"
        return max(scores, key=scores.get)

    def _detect_topic(self, text: str) -> str:
        """从输入中提取核心主题（支持多层前缀/后缀剥离）"""
        # 移除常见前缀（循环剥离直到无法匹配）
        prefixes = [
            "请帮我", "我想学", "帮我学习", "学习一下", "请学习",
            "请", "帮我", "我想", "学习", "关于", "讲解", "介绍一下",
            "想学", "学一下",
        ]
        topic = text
        changed = True
        while changed:
            changed = False
            for prefix in prefixes:
                if topic.startswith(prefix):
                    topic = topic[len(prefix):].strip()
                    changed = True
                    break
        # 移除常见后缀
        suffixes = ["谢谢", "请讲解", "帮我学习", "我想了解"]
        changed = True
        while changed:
            changed = False
            for suffix in suffixes:
                if topic.endswith(suffix):
                    topic = topic[:-len(suffix)].strip()
                    changed = True
                    break
        # 移除结尾标点
        topic = re.sub(r'[？?！!。]', '', topic).strip()
        return topic[:50] if topic else ""

    def _detect_difficulty(self, text: str) -> str:
        for level, keywords in self.DIFFICULTY_INDICATORS.items():
            if any(kw in text for kw in keywords):
                return level
        return "高中"  # 默认

    def _detect_complexity(self, text: str) -> str:
        simple_score = sum(1 for kw in SIMPLE_KEYWORDS if kw in text)
        complex_score = sum(1 for kw in COMPLEX_KEYWORDS if kw in text)

        if complex_score >= 2:
            return "complex"
        if simple_score >= 1:
            return "simple"
        return "standard"

    def _detect_reasoning_type(self, text: str) -> str:
        parallel_score = sum(1 for kw in PARALLEL_KEYWORDS if kw in text)
        sequential_score = sum(1 for kw in SEQUENTIAL_KEYWORDS if kw in text)

        if parallel_score > sequential_score:
            return "parallel"
        if sequential_score > parallel_score:
            return "sequential"
        return "hybrid"

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        keywords = []
        for subject_kws in self.SUBJECT_KEYWORDS.values():
            for kw in subject_kws:
                if kw in text and len(kw) >= 2:
                    keywords.append(kw)
        return list(set(keywords))[:10]


# ================================================================
# 单例
# ================================================================
_router_instance: Optional[RouterAgent] = None


def get_router_agent() -> RouterAgent:
    global _router_instance
    if _router_instance is None:
        _router_instance = RouterAgent()
    return _router_instance


# ================================================================
# 便捷入口
# ================================================================
def route_task(user_input: str, context: str = "") -> Dict:
    """一行调用路由"""
    return get_router_agent().route(user_input, context)
