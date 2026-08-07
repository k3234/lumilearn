# -*- coding: utf-8 -*-
"""
灵学 lumilearn - 学生学习成果输出检测引擎
评估学生概念理解输出质量，识别理解差距并提供引导式强化

评分维度：简洁度 / 准确度 / 比喻 / 完整度 / 术语规避
引导式加强：最多5轮迭代优化
"""

import re
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

# 导入框架模块
from framework.database import db
from framework.engines.feynman_engine import FeynmanEngine, FEYNMAN_TEMPLATES


# ============================================================
# 评分维度定义
# ============================================================

SCORING_DIMENSIONS = {
    "简洁度": {
        "key": "conciseness",
        "desc": "解释是否足够简洁精炼，能用最短的话讲清楚",
        "weight": 20,
    },
    "准确度": {
        "key": "accuracy",
        "desc": "解释在概念上是否正确，有无事实性错误",
        "weight": 25,
    },
    "比喻": {
        "key": "analogy",
        "desc": "是否用了生活化的比喻/类比帮助理解",
        "weight": 20,
    },
    "完整度": {
        "key": "completeness",
        "desc": "是否抓住了核心要点，有无重大遗漏",
        "weight": 20,
    },
    "术语规避": {
        "key": "jargon_free",
        "desc": "是否避免使用专业术语，或用通俗语言解释",
        "weight": 15,
    },
}

MAX_GUIDING_ROUNDS = 5


# ============================================================
# 数据模型
# ============================================================

@dataclass
class DimensionScore:
    """单个评分维度"""
    name: str                    # 维度名称（中文）
    key: str                     # 维度标识（英文）
    score: int                   # 得分 (0-20)
    comment: str = ""            # 评语


@dataclass
class DetectionResult:
    """单次检测结果"""
    concept: str                 # 被检测的概念
    student_output: str          # 学生输出
    total_score: int             # 总分 (0-100)
    dimensions: List[DimensionScore] = field(default_factory=list)
    feedback: str = ""           # 综合评语
    is_mastered: bool = False    # 是否通过（>=70分）
    detected_at: str = ""        # 检测时间


@dataclass
class GuidingRound:
    """引导强化轮次"""
    round_num: int               # 轮次 (1-5)
    question: str = ""           # AI引导问题
    student_answer: str = ""     # 学生回答
    score_before: int = 0        # 强化前分数
    score_after: int = 0         # 强化后分数
    improvement: int = 0         # 提升幅度
    ai_hint: str = ""            # AI提示
    round_result: Optional[DetectionResult] = None  # 本轮检测结果


# ============================================================
# OutputDetector 类
# ============================================================

class OutputDetector:
    """
    学生学习成果输出检测引擎

    功能：
    1. 评估学生概念解释的输出质量
    2. 识别理解差距并提供针对性引导
    3. 生成可存储的检测报告

    使用示例：
        detector = OutputDetector(user_id=1)
        result = detector.run_detection(
            concept="勾股定理",
            student_output="a²+b²=c²",
        )
        report = detector.generate_detection_report(result)
    """

    def __init__(
        self,
        user_id: int,
        workflow_id: str = "",
        model_name: str = "qwen2.5:7b",
        timeout: int = 60,
    ):
        """
        初始化检测引擎

        参数：
            user_id:    学生用户ID
            workflow_id: 关联工作流标识（可选）
            model_name: Ollama模型名称
            timeout:    调用超时（秒）
        """
        self.user_id = user_id
        self.workflow_id = workflow_id
        self.model_name = model_name
        self.timeout = timeout

        # 费曼引擎（复用）
        self.feynman = FeynmanEngine(model_name=model_name, timeout=timeout)

        # 历史记录
        self.detection_history: List[Dict] = []

        # 初始化数据库
        db.init()

    # ============================================================
    # 核心方法：run_detection
    # ============================================================

    def run_detection(
        self,
        concept: str,
        student_output: str,
        detection_type: str = "quiz",
        prompt: str = "",
    ) -> DetectionResult:
        """
        运行单次检测评估

        参数：
            concept:        被检测的概念/主题
            student_output: 学生的输出/解释
            detection_type: 检测类型 (quiz/essay/project/peer_review)
            prompt:         检测题目/提示（可选）

        返回：
            DetectionResult 检测结果对象
        """
        if not student_output.strip():
            return DetectionResult(
                concept=concept,
                student_output=student_output,
                total_score=0,
                is_mastered=False,
                detected_at=self._now_str(),
            )

        # AI评分（五维度）
        ai_result = self._ai_score(concept, student_output)

        # 规则兜底评分
        if not ai_result or ai_result.get("score", 0) == 0:
            ai_result = self._rule_based_score(concept, student_output)

        # 组装检测结果
        result = DetectionResult(
            concept=concept,
            student_output=student_output,
            total_score=ai_result.get("score", 0),
            dimensions=[
                DimensionScore(
                    name=d.get("name", k),
                    key=k,
                    score=d.get("score", 0),
                    comment=d.get("comment", ""),
                )
                for k, d in ai_result.get("dimensions", {}).items()
            ],
            feedback=ai_result.get("feedback", ""),
            is_mastered=ai_result.get("is_mastered", False),
            detected_at=self._now_str(),
        )

        # 记录历史
        self.detection_history.append({
            "concept": concept,
            "score": result.total_score,
            "is_mastered": result.is_mastered,
            "timestamp": result.detected_at,
        })

        # 持久化到数据库
        self._save_to_database(detection_type, prompt, result)

        return result

    # ============================================================
    # 核心方法：run_guided_reinforcement
    # ============================================================

    def run_guided_reinforcement(
        self,
        concept: str,
        student_output: str,
        max_rounds: int = MAX_GUIDING_ROUNDS,
        threshold: int = 70,
    ) -> Dict:
        """
        引导式强化：最多 max_rounds 轮，每轮针对薄弱维度提问并重新评估

        参数：
            concept:      概念/主题
            student_output: 学生初始输出
            max_rounds:   最大强化轮次（默认5）
            threshold:    通过阈值（默认70分）

        返回：
            {
                "concept": str,
                "initial_score": int,
                "final_score": int,
                "rounds": [GuidingRound...],
                "is_mastered": bool,
                "final_output": str,
            }
        """
        # 初始检测
        initial_result = self.run_detection(concept, student_output)
        current_output = student_output
        current_score = initial_result.total_score
        rounds: List[GuidingRound] = []

        for round_num in range(1, max_rounds + 1):
            # 已达到阈值，停止强化
            if current_score >= threshold:
                break

            # 识别薄弱维度
            gap = self._identify_gap(initial_result, current_result=initial_result if round_num == 1 else None)

            # 生成引导问题
            guide_question = self._generate_guide_question(concept, gap)

            # 构造本轮学生输出（模拟：将原输出+引导内容融合）
            enriched_output = self._enrich_output(current_output, gap, guide_question)

            # 重新检测
            round_result = self.run_detection(concept, enriched_output, detection_type="guided_reinforcement")
            score_after = round_result.total_score

            round_obj = GuidingRound(
                round_num=round_num,
                question=guide_question,
                student_answer=enriched_output,
                score_before=current_score,
                score_after=score_after,
                improvement=score_after - current_score,
                ai_hint=gap.get("recommendation", ""),
                round_result=round_result,
            )
            rounds.append(round_obj)

            current_output = enriched_output
            current_score = score_after

            # 达到阈值，停止
            if current_score >= threshold:
                break

        return {
            "concept": concept,
            "initial_score": initial_result.total_score,
            "final_score": current_score,
            "rounds": rounds,
            "is_mastered": current_score >= threshold,
            "final_output": current_output,
            "total_rounds": len(rounds),
        }

    # ============================================================
    # 核心方法：generate_detection_report
    # ============================================================

    def generate_detection_report(
        self,
        result: DetectionResult,
        reinforcement_history: Optional[Dict] = None,
    ) -> Dict:
        """
        生成检测报告的可视化数据

        参数：
            result:                  检测结果
            reinforcement_history:   强化历史记录（可选）

        返回：
            结构化报告字典，可直接序列化为JSON
        """
        report: Dict[str, Any] = {
            "concept": result.concept,
            "detected_at": result.detected_at,
            "total_score": result.total_score,
            "is_mastered": result.is_mastered,
            "dimensions": [
                {
                    "name": d.name,
                    "key": d.key,
                    "score": d.score,
                    "comment": d.comment,
                }
                for d in result.dimensions
            ],
            "feedback": result.feedback,
            "student_output_preview": result.student_output[:300] + "..." if len(result.student_output) > 300 else result.student_output,
        }

        # 附加强化历史（如有）
        if reinforcement_history:
            report["reinforcement"] = {
                "initial_score": reinforcement_history.get("initial_score", 0),
                "final_score": reinforcement_history.get("final_score", 0),
                "total_rounds": reinforcement_history.get("total_rounds", 0),
                "improvement": reinforcement_history.get("final_score", 0) - reinforcement_history.get("initial_score", 0),
                "rounds_detail": [
                    {
                        "round": r.round_num,
                        "score_before": r.score_before,
                        "score_after": r.score_after,
                        "improvement": r.improvement,
                        "question": r.question,
                        "ai_hint": r.ai_hint,
                    }
                    for r in reinforcement_history.get("rounds", [])
                ],
            }

        # 生成等级标签
        score = result.total_score
        if score >= 90:
            report["level"] = "优秀"
            report["level_icon"] = "🌟"
        elif score >= 70:
            report["level"] = "良好"
            report["level_icon"] = "✅"
        elif score >= 50:
            report["level"] = "中等"
            report["level_icon"] = "📝"
        else:
            report["level"] = "需加强"
            report["level_icon"] = "⚠️"

        # 薄弱维度排序
        sorted_dims = sorted(report["dimensions"], key=lambda x: x["score"])
        report["weakest_dimension"] = sorted_dims[0] if sorted_dims else None
        report["strongest_dimension"] = sorted_dims[-1] if sorted_dims else None

        return report

    # ============================================================
    # 内部方法：_identify_gap
    # ============================================================

    def _identify_gap(
        self,
        result: DetectionResult,
        current_result: Optional[DetectionResult] = None,
    ) -> Dict:
        """
        识别理解差距

        分析评分结果，找出最薄弱的维度，生成针对性诊断

        返回：
            {
                "weak_dimension": str,          # 最弱维度
                "gap_description": str,         # 差距描述
                "recommendation": str,          # 改进建议
                "priority": str,                # 优先级 (high/medium/low)
            }
        """
        if not result.dimensions:
            return {
                "weak_dimension": "综合",
                "gap_description": "输出为空，无法评估",
                "recommendation": "请先提供对概念的完整解释",
                "priority": "high",
            }

        # 找最低分维度
        min_dim = min(result.dimensions, key=lambda d: d.score)

        # 根据维度生成差距描述和建议
        gap_map = {
            "conciseness": {
                "description": "解释过于冗长，核心信息被淹没",
                "recommendation": "尝试用不超过50字概括核心要点，删除所有非必要修饰语",
            },
            "accuracy": {
                "description": "存在概念性错误或不准确表述",
                "recommendation": "重新审视概念定义，对照标准解释找出偏差",
            },
            "analogy": {
                "description": "缺乏生活化比喻，理解停留在抽象层面",
                "recommendation": "尝试用'就像...'或'想象...'的句式，举一个生活中的例子",
            },
            "completeness": {
                "description": "解释遗漏了关键要素",
                "recommendation": "检查是否涵盖了概念的定义、核心性质和典型应用",
            },
            "jargon_free": {
                "description": "过多使用专业术语，未做通俗解释",
                "recommendation": "把每个术语换成大白话，或用比喻替代",
            },
        }

        gap_info = gap_map.get(min_dim.key, {
            "description": "该维度需要提升",
            "recommendation": "参考费曼教学法重新组织解释",
        })

        return {
            "weak_dimension": min_dim.name,
            "gap_description": gap_info["description"],
            "recommendation": gap_info["recommendation"],
            "priority": "high" if min_dim.score < 10 else "medium",
            "dimension_score": min_dim.score,
        }

    # ============================================================
    # 内部方法：_generate_recommendation
    # ============================================================

    def _generate_recommendation(
        self,
        concept: str,
        gap_info: Dict,
        student_output: str,
    ) -> str:
        """
        生成个性化推荐（针对学生的具体输出）

        参数：
            concept:      概念名
            gap_info:     _identify_gap 返回的差距信息
            student_output: 学生原始输出

        返回：
            个性化推荐文本
        """
        # 基于费曼引擎生成推荐
        try:
            prompt = f"""你是费曼教学法老师，需要帮助学生改进对"{concept}"的解释。

学生的当前解释：
"{student_output[:200]}"

薄弱维度：{gap_info.get("weak_dimension", "综合")}
差距描述：{gap_info.get("gap_description", "")}
改进建议：{gap_info.get("recommendation", "")}

请给出具体的改进指导：
1. 指出当前解释中需要修改的具体位置
2. 给出一个改进后的示例（不超过100字）
3. 解释为什么要这样改进

用亲切、鼓励的语气，像朋友一样给学生建议。"""

            response = self.feynman.ask_guiding_question(concept, prompt)
            if response:
                return response.strip()
        except Exception:
            pass

        # 兜底：基于模板生成推荐
        subject, _ = self.feynman._detect_subject_and_type(concept)
        template = FEYNMAN_TEMPLATES.get(subject, {}).get("default", {}).get("test", "")
        return f"""建议改进方向：{gap_info.get("recommendation", "请参考费曼教学法重新组织解释")}

示例参考：{template}

请尝试按照这个方向重新解释"{concept}"。"""

    # ============================================================
    # 内部方法：AI评分
    # ============================================================

    def _ai_score(self, concept: str, student_output: str) -> Optional[Dict]:
        """调用费曼引擎的AI评分"""
        try:
            result = self.feynman.thirty_second_test(concept, student_output)
            return {
                "score": result.get("score", 0),
                "dimensions": {
                    "conciseness": result.get("dimensions", {}).get("simplicity", {"score": 0, "comment": ""}),
                    "accuracy": result.get("dimensions", {}).get("accuracy", {"score": 0, "comment": ""}),
                    "analogy": result.get("dimensions", {}).get("analogy", {"score": 0, "comment": ""}),
                    "completeness": result.get("dimensions", {}).get("completeness", {"score": 0, "comment": ""}),
                    "jargon_free": result.get("dimensions", {}).get("jargon_free", {"score": 0, "comment": ""}),
                },
                "feedback": result.get("feedback", ""),
                "is_mastered": result.get("is_feynman_worthy", False),
            }
        except Exception as e:
            return None

    # ============================================================
    # 内部方法：规则兜底评分
    # ============================================================

    def _rule_based_score(self, concept: str, student_output: str) -> Dict:
        """基于规则的评分（AI不可用时的兜底）"""
        text = student_output.strip()
        char_count = len(text)

        # 简洁度：字数越精炼越好
        if char_count <= 50:
            conciseness = 18
        elif char_count <= 100:
            conciseness = 16
        elif char_count <= 200:
            conciseness = 13
        elif char_count <= 350:
            conciseness = 10
        else:
            conciseness = 6

        # 准确度：包含概念关键词则给高分
        concept_keywords = concept.replace(" ", "").split("的")
        accuracy = 10
        for kw in concept_keywords:
            if kw and kw in text:
                accuracy += 3
        accuracy = min(20, accuracy)

        # 比喻：检查比喻关键词
        analogy_keywords = ["像", "好像", "比如", "例如", "就像", "好比", "类似",
                           "想象", "可以看作", "可以理解成", "犹如", "如同"]
        analogy_count = sum(1 for kw in analogy_keywords if kw in text)
        analogy = min(20, analogy_count * 4 + 4)

        # 完整度：检查核心结构词
        completeness_keywords = ["因为", "所以", "定义", "公式", "关键", "核心", "意思是"]
        completeness_count = sum(1 for kw in completeness_keywords if kw in text)
        completeness = min(20, completeness_count * 3 + 5)

        # 术语规避：检查专业符号/术语
        jargon_chars = set("^±×÷∑∫√π∞αβγθλμΔΩ∇∂∈∉∪∩⊂⊃⊆⊇∧∨¬→⇒↔∀∃∄≡≈≠≤≥")
        jargon_count = sum(1 for c in text if c in jargon_chars)
        if jargon_count == 0:
            jargon_free = 18
        elif jargon_count <= 2:
            jargon_free = 14
        elif jargon_count <= 5:
            jargon_free = 10
        else:
            jargon_free = 5

        total = conciseness + accuracy + analogy + completeness + jargon_free

        return {
            "score": total,
            "dimensions": {
                "conciseness": {"score": conciseness, "comment": "字数精炼" if conciseness >= 14 else "可以更简洁"},
                "accuracy": {"score": accuracy, "comment": "概念准确" if accuracy >= 14 else "需检查准确性"},
                "analogy": {"score": analogy, "comment": "比喻丰富" if analogy >= 12 else "建议加入生活比喻"},
                "completeness": {"score": completeness, "comment": "要点全面" if completeness >= 14 else "需补充关键要素"},
                "jargon_free": {"score": jargon_free, "comment": "术语控制良好" if jargon_free >= 14 else "建议减少专业术语"},
            },
            "feedback": "评分基于规则（AI模型不可用时的兜底方案）。" if total < 70 else "整体理解较好，继续保持！",
            "is_mastered": total >= 70,
        }

    # ============================================================
    # 内部方法：生成引导问题
    # ============================================================

    def _generate_guide_question(self, concept: str, gap_info: Dict) -> str:
        """
        根据差距信息生成引导性问题

        返回：
            引导性问题文本
        """
        weak_dim = gap_info.get("weak_dimension", "")
        gap_desc = gap_info.get("gap_description", "")

        # 针对不同维度生成不同风格的问题
        if weak_dim == "简洁度":
            return f"请用不超过30个字概括{concept}最核心的意思，只保留最关键的信息。"
        elif weak_dim == "准确度":
            return f"重新思考{concept}的定义，确保解释与教材定义一致。你能说出它的标准定义吗？"
        elif weak_dim == "比喻":
            return f"请用'就像...'的句式，为{concept}找一个生活中的类比。"
        elif weak_dim == "完整度":
            return f"请从定义、核心性质、典型应用三个方面完整解释{concept}。"
        elif weak_dim == "术语规避":
            return f"请用大白话解释{concept}，把每个术语都换成普通人能听懂的说法。"
        else:
            return f"请重新解释{concept}，注意：{gap_desc}"

    # ============================================================
    # 内部方法：丰富学生输出
    # ============================================================

    def _enrich_output(self, original: str, gap_info: Dict, guide_question: str) -> str:
        """
        将学生原始输出与引导内容融合，生成改进后的输出

        模拟学生的改进过程，保留原输出核心，补充引导内容
        """
        # 提取原输出的核心部分
        original_clean = original.strip()

        # 根据薄弱维度生成补充内容
        weak_dim = gap_info.get("weak_dimension", "")
        supplement = ""

        if weak_dim == "比喻":
            supplement = f"\n打个比方：{concept}就像日常生活中处理类似问题的方法。"
        elif weak_dim == "简洁度":
            # 截断到更简洁的版本
            words = original_clean.split()
            if len(words) > 15:
                original_clean = " ".join(words[:15]) + "..."
        elif weak_dim == "完整度":
            supplement = "\n核心要点：定义上，{concept}指的是...；性质上，它具有...；应用上，我们常用来..."
        elif weak_dim == "术语规避":
            supplement = "\n（用通俗语言重述：...）"

        enriched = original_clean + supplement
        return enriched.strip()

    # ============================================================
    # 内部方法：数据库持久化
    # ============================================================

    def _save_to_database(self, detection_type: str, prompt: str, result: DetectionResult):
        """保存检测结果到数据库"""
        try:
            # 创建检测记录
            det_record = db.create_output_detection(
                user_id=self.user_id,
                detection_type=detection_type,
                prompt=prompt,
                workflow_id=self.workflow_id,
            )
            detection_id = det_record.get("id")

            if detection_id:
                # 更新检测结果
                feedback_text = json.dumps(
                    {
                        "score": result.total_score,
                        "dimensions": [
                            {"name": d.name, "score": d.score, "comment": d.comment}
                            for d in result.dimensions
                        ],
                        "feedback": result.feedback,
                    },
                    ensure_ascii=False,
                )
                db.update_detection_result(
                    detection_id=detection_id,
                    score=result.total_score,
                    feedback=feedback_text,
                    user_output=result.student_output,
                )
                if result.is_mastered:
                    db.mark_reinforced(detection_id)
        except Exception as e:
            # 记录失败但不中断主流程
            print(f"[OutputDetector] 数据库保存失败: {e}")

    # ============================================================
    # 辅助方法
    # ============================================================

    def _now_str(self) -> str:
        """返回当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_detection_history(self, limit: int = 20) -> List[Dict]:
        """获取检测历史记录"""
        return self.detection_history[-limit:]

    def get_user_detection_summary(self) -> Dict:
        """获取用户检测统计摘要"""
        return db.get_detection_summary(self.user_id)


# ============================================================
# 便捷函数
# ============================================================

def detect_output(
    user_id: int,
    concept: str,
    student_output: str,
    detection_type: str = "quiz",
    prompt: str = "",
    workflow_id: str = "",
    model_name: str = "qwen2.5:7b",
) -> DetectionResult:
    """
    便捷函数：单次输出检测

    参数：
        user_id:        用户ID
        concept:        概念/主题
        student_output: 学生输出
        detection_type: 检测类型 (quiz/essay/project/peer_review)
        prompt:         检测题目（可选）
        workflow_id:    工作流ID（可选）
        model_name:     模型名称（可选）

    返回：
        DetectionResult 检测结果
    """
    detector = OutputDetector(
        user_id=user_id,
        workflow_id=workflow_id,
        model_name=model_name,
    )
    return detector.run_detection(concept, student_output, detection_type, prompt)


def run_guided_reinforcement(
    user_id: int,
    concept: str,
    student_output: str,
    max_rounds: int = MAX_GUIDING_ROUNDS,
    threshold: int = 70,
    workflow_id: str = "",
    model_name: str = "qwen2.5:7b",
) -> Dict:
    """
    便捷函数：引导式强化（最多5轮）

    参数：
        user_id:        用户ID
        concept:        概念/主题
        student_output: 学生输出
        max_rounds:     最大强化轮次（默认5）
        threshold:      通过阈值（默认70）
        workflow_id:    工作流ID（可选）
        model_name:     模型名称（可选）

    返回：
        强化结果字典（含初始分数、最终分数、每轮详情、是否通过）
    """
    detector = OutputDetector(
        user_id=user_id,
        workflow_id=workflow_id,
        model_name=model_name,
    )
    return detector.run_guided_reinforcement(
        concept, student_output, max_rounds=max_rounds, threshold=threshold
    )


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 学生学习成果输出检测引擎 - 测试")
    print("=" * 60)

    # 测试1：单次检测
    print("\n【测试1】单次检测")
    result = detect_output(
        user_id=1,
        concept="勾股定理",
        student_output="勾股定理是说直角三角形两直角边的平方和等于斜边的平方，也就是a²+b²=c²。",
        detection_type="quiz",
    )
    print(f"  概念: {result.concept}")
    print(f"  总分: {result.total_score}/100")
    print(f"  通过: {'✅' if result.is_mastered else '❌'}")
    for d in result.dimensions:
        print(f"    {d.name}: {d.score}/20 - {d.comment}")
    print(f"  评语: {result.feedback}")

    # 测试2：检测报告
    print("\n【测试2】检测报告")
    report = OutputDetector(user_id=1).generate_detection_report(result)
    print(f"  等级: {report.get('level_icon', '')} {report.get('level', 'N/A')}")
    print(f"  最弱维度: {report.get('weakest_dimension', {}).get('name', 'N/A')} ({report.get('weakest_dimension', {}).get('score', 0)}/20)")
    print(f"  最强维度: {report.get('strongest_dimension', {}).get('name', 'N/A')} ({report.get('strongest_dimension', {}).get('score', 0)}/20)")

    # 测试3：引导式强化
    print("\n【测试3】引导式强化（最多5轮）")
    reinforcement = run_guided_reinforcement(
        user_id=1,
        concept="勾股定理",
        student_output="a²+b²=c²，就是两个小边平方加起来等于大边平方。",
        max_rounds=3,
    )
    print(f"  初始分数: {reinforcement['initial_score']}")
    print(f"  最终分数: {reinforcement['final_score']}")
    print(f"  强化轮次: {reinforcement['total_rounds']}")
    print(f"  通过: {'✅' if reinforcement['is_mastered'] else '❌'}")
    for r in reinforcement.get("rounds", []):
        print(f"    第{r.round_num}轮: {r.score_before}→{r.score_after} (提升{r.improvement})")
        print(f"      问题: {r.question[:60]}...")

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
