# -*- coding: utf-8 -*-
"""
灵学 lumilearn - 讲解审查服务
基于学习科学原理（布鲁姆分类法、脚手架理论、最近发展区）
对AI生成的讲解内容进行多维度质量审查

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-01
"""

import json
import re
import logging
from typing import Any, Dict, List, Optional

from lumilearn_shared import call_ollama

logger = logging.getLogger("lumilearn.review_service")

DEFAULT_MODEL = "qwen2.5:7b"

STUDENT_LEVELS = {
    "junior": "初中生，基础知识薄弱，需要直观比喻和循序渐进引导",
    "senior": "高中生，有一定学科基础，需要逻辑推导和深度思考",
    "college": "大学生，基础扎实，需要学术严谨性和批判性思维",
    "general": "普通学习者，无特定学段，需要通俗易懂、有趣味性的讲解"
}

REVIEW_MODES = {
    "quick": "快速审查模式：仅给出各维度评分和总分，不提供详细建议",
    "full": "完整审查模式：给出各维度评分、总分和详细改进建议",
    "strict": "严格审查模式：以更高标准评分，对每个问题零容忍，给出详尽批评和建议"
}

REVIEW_PROMPT_TEMPLATE = """你是一位资深教育质量评估专家，精通学习科学理论。请对以下AI生成的讲解内容进行多维度质量审查。

【审查维度与评分标准】（每项1-10分）

1. 准确性（Accuracy）：知识点是否准确无误
   - 10分：所有知识点完全正确，引用精准，无任何错误
   - 7-9分：核心知识点正确，偶有表述不够精确
   - 4-6分：存在一些概念模糊或不够准确的地方
   - 1-3分：存在明显知识性错误

2. 完整性（Completeness）：是否覆盖所有关键要点
   - 10分：完整覆盖所有要点，逻辑链条完整，无遗漏
   - 7-9分：覆盖了大部分要点，有少量可补充之处
   - 4-6分：缺失了一些重要知识点
   - 1-3分：严重不完整，遗漏大量核心内容

3. 引导性（Guidance）：是否引导思考而非直接给答案
   - 10分：巧妙引导，激发好奇心，层层递进，符合脚手架理论
   - 7-9分：有一定的引导性，但部分内容过于直接
   - 4-6分：大多是直接灌输，缺少启发式引导
   - 1-3分：完全灌输式，没有思考空间

4. 难度适合度（Difficulty Fit）：是否匹配目标学生水平
   - 10分：难度完美匹配，在最近发展区内，既不太难也不太简单
   - 7-9分：基本匹配，偶有偏难或偏易之处
   - 4-6分：难度明显不匹配，过难或过简单
   - 1-3分：完全不适合目标学生水平

【学习科学理论参考】
- 布鲁姆分类法：知识层次从记忆→理解→应用→分析→评价→创造
- 脚手架理论：提供适当支持，随着能力提升逐步撤除
- 最近发展区（ZPD）：内容难度应在学生现有水平和潜在水平之间

【目标学生水平】
{student_level_desc}

【审查模式】
{mode_desc}

【讲解内容】
{content}

请以JSON格式返回审查结果，格式如下：
```json
{output_format}
```

注意事项：
{notes}
"""


def _build_review_prompt(content, student_level, mode):
    """构建审查Prompt"""
    student_level_desc = STUDENT_LEVELS.get(student_level, STUDENT_LEVELS["general"])
    mode_desc = REVIEW_MODES.get(mode, REVIEW_MODES["full"])

    if mode == "quick":
        output_format = (
            '{"accuracy": 8, "completeness": 7, "guidance": 6, "difficulty_fit": 8, '
            '"overall": 7.5, "summary": "一句话总结"}'
        )
        notes = "只返回JSON，不要任何额外文字。summary为一句话总结，不超过30字。"
    elif mode == "strict":
        output_format = (
            '{"accuracy": 8, "completeness": 7, "guidance": 6, "difficulty_fit": 8, '
            '"overall": 7.5, "suggestions": [{"dimension": "准确性", "issue": "问题描述", '
            '"fix": "改进建议", "severity": "高/中/低"}], '
            '"summary": "总体评价", "critical_issues": ["严重问题1", "严重问题2"]}'
        )
        notes = (
            "以最严格的标准评分，不放过任何小问题。severity分为高/中/低。"
            "critical_issues列出不容忽视的严重问题。只返回JSON，不要任何额外文字。"
        )
    else:
        output_format = (
            '{"accuracy": 8, "completeness": 7, "guidance": 6, "difficulty_fit": 8, '
            '"overall": 7.5, "suggestions": [{"dimension": "准确性", "issue": "问题描述", '
            '"fix": "改进建议"}], "summary": "总体评价"}'
        )
        notes = "只返回JSON，不要任何额外文字。summary为总体评价，不超过50字。"

    return REVIEW_PROMPT_TEMPLATE.format(
        content=content,
        student_level_desc=student_level_desc,
        mode_desc=mode_desc,
        output_format=output_format,
        notes=notes
    )


def _parse_review_response(response_text):
    """从模型响应中解析JSON"""
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if not json_match:
        return None
    try:
        return json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return None


class ReviewService:
    """
    讲解内容审查服务

    基于学习科学原理，对AI生成的讲解内容进行多维度质量审查。
    支持三种审查模式：quick（快速）、full（完整）、strict（严格）。

    集成费曼度评分机制，评估讲解是否达到费曼教学标准。
    """

    def __init__(self, model_name: str = None):
        self._model_name = model_name or DEFAULT_MODEL
        self._history: List[Dict] = []

    def review(self, content: str, student_level: str = "junior",
               mode: str = "full") -> Dict[str, Any]:
        """
        审查讲解内容

        参数：
            content: 待审查的讲解内容文本
            student_level: 学生水平，可选 "junior"/"senior"/"college"/"general"
            mode: 审查模式，可选 "quick"/"full"/"strict"

        返回：
            {
                "accuracy": int,
                "completeness": int,
                "guidance": int,
                "difficulty_fit": int,
                "overall": float,
                "suggestions": list,
                "summary": str,
                "mode": str,
                "student_level": str,
                "model": str
            }
        """
        if not content or not content.strip():
            return {
                "accuracy": 0, "completeness": 0, "guidance": 0,
                "difficulty_fit": 0, "overall": 0, "suggestions": [],
                "feynman_score": 0,
                "summary": "内容为空，无法审查",
                "mode": mode, "student_level": student_level,
                "model": self._model_name
            }

        if mode not in REVIEW_MODES:
            mode = "full"

        if student_level not in STUDENT_LEVELS:
            student_level = "general"

        prompt = _build_review_prompt(content, student_level, mode)
        response = call_ollama(self._model_name, prompt, timeout=120)
        result = _parse_review_response(response)

        if result is None:
            return {
                "accuracy": 0, "completeness": 0, "guidance": 0,
                "difficulty_fit": 0, "overall": 0, "suggestions": [],
                "feynman_score": 0,
                "summary": "模型响应解析失败，请重试",
                "mode": mode, "student_level": student_level,
                "model": self._model_name,
                "raw_response": response[:500] if response else ""
            }

        result["mode"] = mode
        result["student_level"] = student_level
        result["model"] = self._model_name

        # 计算费曼度评分（基于四维度的加权平均）
        scores = [
            result.get("accuracy", 0),
            result.get("completeness", 0),
            result.get("guidance", 0),
            result.get("difficulty_fit", 0)
        ]
        # 费曼度侧重引导性和难度适合度
        feynman_score = round(
            (result.get("guidance", 0) * 0.35 +
             result.get("difficulty_fit", 0) * 0.25 +
             result.get("accuracy", 0) * 0.20 +
             result.get("completeness", 0) * 0.20),
            2
        )
        result["feynman_score"] = feynman_score

        # 记录审查历史
        self._history.append({
            "scores": {
                "accuracy": result.get("accuracy", 0),
                "completeness": result.get("completeness", 0),
                "guidance": result.get("guidance", 0),
                "difficulty_fit": result.get("difficulty_fit", 0),
                "overall": result.get("overall", 0),
                "feynman_score": feynman_score
            },
            "mode": mode,
            "student_level": student_level
        })

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """获取审查统计信息"""
        if not self._history:
            return {
                "count": 0, "avg_accuracy": 0, "avg_completeness": 0,
                "avg_guidance": 0, "avg_difficulty_fit": 0, "avg_overall": 0,
                "avg_feynman_score": 0,
                "trend": "无数据", "best_dimension": "N/A", "worst_dimension": "N/A"
            }

        count = len(self._history)
        dims = ["accuracy", "completeness", "guidance", "difficulty_fit"]

        avgs = {}
        for dim in dims:
            values = [r["scores"].get(dim, 0) for r in self._history]
            avgs[dim] = round(sum(values) / count, 2) if count > 0 else 0

        overalls = [r["scores"].get("overall", 0) for r in self._history]
        avg_overall = round(sum(overalls) / count, 2) if count > 0 else 0

        feynman_scores = [r["scores"].get("feynman_score", 0) for r in self._history]
        avg_feynman = round(sum(feynman_scores) / count, 2) if count > 0 else 0

        dim_labels = {
            "accuracy": "准确性", "completeness": "完整性",
            "guidance": "引导性", "difficulty_fit": "难度适合度"
        }
        best_dim = max(dims, key=lambda d: avgs[d])
        worst_dim = min(dims, key=lambda d: avgs[d])

        if count >= 2:
            first = self._history[0]["scores"].get("overall", 0)
            last = self._history[-1]["scores"].get("overall", 0)
            diff = last - first
            if diff > 0.5:
                trend = "上升趋势 ↑"
            elif diff < -0.5:
                trend = "下降趋势 ↓"
            else:
                trend = "保持稳定 →"
        else:
            trend = "数据不足，需至少2次审查"

        return {
            "count": count,
            "avg_accuracy": avgs["accuracy"],
            "avg_completeness": avgs["completeness"],
            "avg_guidance": avgs["guidance"],
            "avg_difficulty_fit": avgs["difficulty_fit"],
            "avg_overall": avg_overall,
            "avg_feynman_score": avg_feynman,
            "trend": trend,
            "best_dimension": dim_labels[best_dim],
            "worst_dimension": dim_labels[worst_dim]
        }

    def clear_history(self):
        """清除审查历史"""
        self._history.clear()

    @property
    def model_name(self) -> str:
        return self._model_name


_review_service_instance: Optional[ReviewService] = None


def get_review_service(model_name: str = None) -> ReviewService:
    """获取ReviewService单例"""
    global _review_service_instance
    if _review_service_instance is None:
        _review_service_instance = ReviewService(model_name)
    return _review_service_instance