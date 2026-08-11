#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn GOAI 多 Agent 协作系统
====================================
三 Agent 串行编排：FeynmanTeacher（教学）→ ScoreAgent（评分）→ CoachAgent（建议）

架构：
  用户输入
    │
    ▼
┌──────────────────┐
│ FeynmanTeacher   │  教学 Agent — 费曼五步教学（FeynmanEngine）
└───────┬──────────┘
        ▼
┌──────────────────┐
│ ScoreAgent       │  评分 Agent — 五维评估（OutputDetector）
└───────┬──────────┘
        ▼
┌──────────────────┐
│ CoachAgent       │  建议 Agent — 学习路径推荐（AdaptiveLearningEngine）
└───────┬──────────┘
        ▼
   聚合报告

设计要点：
- 每个 Agent 独立 ToolCaller / 独立模型，可配置不同模型
- 串行执行，上一步输出注入下一步输入
- 单 Agent 失败不阻塞后续 Agent（记录 warning，降级继续）
- 完整耗时追踪（total_time + 每 Agent 耗时）

作者：LumiLearn
版本：1.0.0
日期：2026-08-12
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 尝试加载 .env（模型配置等）；缺失时不报错
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "lumilearn-v2")


# 难度映射：中文难度 → 费曼引擎 level
LEVEL_MAP = {
    "初中": "junior",
    "高中": "senior",
    "大学": "college",
    "大学及以上": "college",
    "general": "general",
}


def _map_level(difficulty: str) -> str:
    """将中文/英文难度映射为 FeynmanEngine 的 level 参数"""
    if not difficulty:
        return "senior"
    return LEVEL_MAP.get(difficulty, LEVEL_MAP.get(difficulty.lower(), "senior"))


# ============================================================
# 一、FeynmanTeacher — 教学 Agent
# ============================================================
class FeynmanTeacher:
    """教学 Agent：基于费曼五步学习法讲解知识点（调用 FeynmanEngine）"""

    def __init__(self, model_name: Optional[str] = None, timeout: int = 120):
        self.model_name = model_name or os.environ.get(
            "MULTI_AGENT_FEYNMAN_MODEL", DEFAULT_MODEL)
        self.timeout = timeout

    def run(self, payload: Dict) -> Dict:
        """
        执行教学，返回五步教学内容。

        payload:
            topic: 教学主题（必填）
            difficulty: 难度（初中/高中/大学）
            dialogue: 可选对话历史（提供则走交互式单步引导）

        返回:
            {"success": True,
             "steps": [{"step_name","step_order","content","key_points"}, ...],
             "full_content": 合并后的完整讲解,
             "model_used": 模型名, "elapsed": 耗时}
        """
        topic = (payload.get("topic") or "").strip()
        if not topic:
            return {"success": False, "error": "缺少 topic 参数"}

        from framework.engines.feynman_engine import FeynmanEngine
        level = _map_level(payload.get("difficulty", "高中"))
        dialogue = payload.get("dialogue")

        engine = FeynmanEngine(model_name=self.model_name, timeout=self.timeout)
        t0 = time.time()

        try:
            if dialogue:
                # 交互式单步引导（保持上下文连贯）
                step = engine.explain_step(topic=topic, level=level, dialogue=dialogue)
                elapsed = round(time.time() - t0, 2)
                return {
                    "success": True,
                    "mode": "interactive",
                    "step": step,
                    "model_used": self.model_name,
                    "elapsed": elapsed,
                }
            # 全流程五步讲解
            result = engine.explain(topic=topic, level=level)
            elapsed = round(time.time() - t0, 2)
            return {
                "success": True,
                "mode": "full",
                "topic": topic,
                "level": level,
                "steps": result.get("steps", []),
                "full_content": result.get("full_content", ""),
                "model_used": result.get("model_used", self.model_name),
                "elapsed": elapsed,
            }
        except Exception as e:
            # 兜底：使用模板生成（FeynmanEngine 内部也有兜底，此处兜最后一层）
            elapsed = round(time.time() - t0, 2)
            try:
                fallback = engine.explain(topic=topic, level=level) if not dialogue else None
                if fallback:
                    return {
                        "success": True, "mode": "fallback",
                        "topic": topic, "level": level,
                        "steps": fallback.get("steps", []),
                        "full_content": fallback.get("full_content", ""),
                        "model_used": "template_fallback",
                        "elapsed": elapsed,
                        "warning": str(e),
                    }
            except Exception:
                pass
            return {"success": False, "error": str(e), "elapsed": elapsed}


# ============================================================
# 二、ScoreAgent — 评分 Agent
# ============================================================
class ScoreAgent:
    """评分 Agent：评估学生理解质量（调用 OutputDetector 五维评分）"""

    DIMENSION_KEYS = ["简洁度", "准确度", "比喻", "完整度", "术语规避"]

    def __init__(self, model_name: Optional[str] = None, timeout: int = 60):
        self.model_name = model_name or os.environ.get(
            "MULTI_AGENT_SCORE_MODEL", DEFAULT_MODEL)
        self.timeout = timeout

    def run(self, payload: Dict) -> Dict:
        """
        评估学生的解释/讲解，返回五维评分。

        payload:
            topic: 概念/主题（必填）
            student_explanation: 学生的解释文本（必填，为空则返回失败）
            user_id: 用户 ID

        返回:
            {"success": True, "score": 总分(0-100),
             "dimensions": {"简洁度": {"score","comment"}, ...},
             "feedback": 综合评语, "is_mastered": 是否掌握,
             "model_used", "elapsed"}
        """
        concept = (payload.get("topic") or "").strip()
        student_output = (payload.get("student_explanation") or "").strip()
        if not concept:
            return {"success": False, "error": "缺少 topic 参数", "score": 0}
        if not student_output:
            return {"success": False, "error": "缺少 student_explanation 参数", "score": 0}

        from framework.output_detector import OutputDetector
        user_id = payload.get("user_id", 0) or 0
        detector = OutputDetector(
            user_id=user_id,
            model_name=self.model_name,
            timeout=self.timeout,
        )
        t0 = time.time()
        try:
            result = detector.run_detection(concept, student_output)
            elapsed = round(time.time() - t0, 2)
            dimensions = {}
            for d in getattr(result, "dimensions", []):
                dimensions[d.name] = {"score": d.score, "comment": d.comment}
            return {
                "success": True,
                "score": getattr(result, "total_score", 0),
                "dimensions": dimensions,
                "feedback": getattr(result, "feedback", ""),
                "is_mastered": getattr(result, "is_mastered", False),
                "model_used": self.model_name,
                "elapsed": elapsed,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "score": 0, "elapsed": 0.0}


# ============================================================
# 三、CoachAgent — 建议 Agent
# ============================================================
class CoachAgent:
    """建议 Agent：根据掌握度与学习进度推荐下一步（调用 AdaptiveLearningEngine）"""

    def __init__(self):
        # 建议 Agent 主要是检索推荐，无模型调用；预留模型名供统一接口
        self.model_name = "adaptive_engine"

    def _mastery_level(self, score: int) -> str:
        """根据评分返回掌握等级与通用建议"""
        if score >= 85:
            return "优秀", "已掌握核心概念，可以挑战更高难度的进阶题目。"
        if score >= 70:
            return "良好", "基本掌握，建议通过练习题巩固并尝试举一反三。"
        if score >= 50:
            return "一般", "理解尚不完整，建议重新回顾薄弱环节后再练习。"
        return "待加强", "需要从基础概念重新学习，建议先掌握前置知识点。"

    def run(self, payload: Dict) -> Dict:
        """
        生成学习建议与下一步推荐。

        payload:
            user_id: 用户 ID
            score: 本次掌握度评分（0-100）
            topic: 当前主题（用于组织建议文案）
            weak_topics: 薄弱知识点列表（可选）

        返回:
            {"success": True,
             "mastery_level": "优秀/良好/一般/待加强",
             "suggestions": [通用建议, 薄弱点建议, ...],
             "next_topics": [{"node_id","name","difficulty","current_mastery",...}, ...],
             "model_used", "elapsed"}
        """
        user_id = payload.get("user_id", 0)
        score = payload.get("score", 0) or 0
        topic = (payload.get("topic") or "").strip()
        weak_topics = payload.get("weak_topics") or []

        t0 = time.time()
        suggestions = []
        next_topics = []

        # 1. 掌握度通用建议
        level, advice = self._mastery_level(score)
        suggestions.append(advice)

        # 2. 薄弱点建议
        for wp in weak_topics[:3]:
            if isinstance(wp, str):
                suggestions.append(f"重点复习「{wp}」：建议用费曼法重新讲一遍。")
            elif isinstance(wp, dict) and wp.get("topic"):
                suggestions.append(f"重点复习「{wp['topic']}」：建议用费曼法重新讲一遍。")

        # 3. 学习路径推荐（AdaptiveLearningEngine）
        try:
            from framework.services.adaptive_learning import get_adaptive_engine
            service = get_adaptive_engine()
            recs = service.recommend_next(user_id=str(user_id or "default"), count=5)
            next_topics = recs
            if not suggestions and not recs and topic:
                suggestions.append(f"继续深入「{topic}」的延伸知识，构建完整的知识网络。")
        except Exception:
            # 推荐失败：给出基于当前主题的兜底建议
            if topic:
                suggestions.append(f"完成「{topic}」后，可尝试用费曼法教给他人来检验掌握程度。")

        elapsed = round(time.time() - t0, 2)
        return {
            "success": True,
            "mastery_level": level,
            "suggestions": suggestions,
            "next_topics": next_topics,
            "model_used": self.model_name,
            "elapsed": elapsed,
        }


# ============================================================
# 四、MultiAgentOrchestrator — 三 Agent 串行编排器
# ============================================================
class MultiAgentOrchestrator:
    """
    三 Agent 串行编排器。

    流程：
        1. FeynmanTeacher  教学 → 五步教学内容
        2. ScoreAgent      评分 → 掌握度评估（可选：无学生解释则跳过评分）
        3. CoachAgent      建议 → 学习建议 + 下一步推荐

    失败降级：
        - 某 Agent 失败记录 warning，后续 Agent 继续执行
        - 最终报告标记各阶段状态（ok / skipped / fallback / failed）
    """

    def __init__(
        self,
        feynman_model: Optional[str] = None,
        score_model: Optional[str] = None,
        coach_model: Optional[str] = None,
    ):
        self.agents = {
            "feynman": FeynmanTeacher(model_name=feynman_model),
            "score": ScoreAgent(model_name=score_model),
            "coach": CoachAgent(),
        }
        # 各 Agent 独立模型配置（端口模型配置可覆盖）
        self._model_overrides = {
            "feynman": feynman_model,
            "score": score_model,
            "coach": coach_model,
        }

    def _apply_port_model(self):
        """尝试从端口模型配置读取模型（可选增强，失败忽略）"""
        try:
            from framework.services.provider_service import get_provider_service
            cfg = get_provider_service().get_port_model_map().get("goai_web", {})
            model = cfg.get("model")
            if model:
                if not self._model_overrides.get("feynman"):
                    self.agents["feynman"].model_name = model
                if not self._model_overrides.get("score"):
                    self.agents["score"].model_name = model
        except Exception:
            pass

    def run(self, payload: Dict) -> Dict:
        """
        执行三 Agent 串行编排，返回聚合报告。

        payload:
            topic: 教学主题（必填）
            subject: 学科（可选，用于报告展示）
            difficulty: 难度（初中/高中/大学）
            user_id: 用户 ID
            student_explanation: 学生解释（可选；提供则评分，否则评分阶段跳过）
            weak_topics: 薄弱知识点（可选）

        返回聚合报告：
            {topic, subject, difficulty, user_id,
             teaching: {...}, assessment: {...}, coaching: {...},
             total_time, timestamp}
        """
        t0 = time.time()
        payload = dict(payload or {})
        self._apply_port_model()

        trace = {}  # 各 Agent 阶段状态

        # ---------- 1. FeynmanTeacher 教学 ----------
        try:
            teach = self.agents["feynman"].run(payload)
            if teach.get("success"):
                payload["teaching_steps"] = teach.get("steps", [])
                payload["teaching_content"] = teach.get("full_content", "")
                trace["feynman"] = {"status": "ok", "elapsed": teach.get("elapsed", 0),
                                    "mode": teach.get("mode", "full")}
            else:
                trace["feynman"] = {"status": "failed", "elapsed": teach.get("elapsed", 0),
                                    "error": teach.get("error", "")}
        except Exception as e:
            trace["feynman"] = {"status": "failed", "elapsed": 0, "error": str(e)}

        # ---------- 2. ScoreAgent 评分（可选） ----------
        student_explanation = (payload.get("student_explanation") or "").strip()
        if student_explanation:
            try:
                score_result = self.agents["score"].run(payload)
                if score_result.get("success"):
                    payload["score"] = score_result.get("score", 0)
                    payload["dimensions"] = score_result.get("dimensions", {})
                    payload["is_mastered"] = score_result.get("is_mastered", False)
                    payload["feedback"] = score_result.get("feedback", "")
                    trace["score"] = {"status": "ok", "elapsed": score_result.get("elapsed", 0)}
                else:
                    trace["score"] = {"status": "failed", "elapsed": 0,
                                      "error": score_result.get("error", "")}
            except Exception as e:
                trace["score"] = {"status": "failed", "elapsed": 0, "error": str(e)}
        else:
            # 无学生解释：评分阶段跳过，用教学步骤数估计掌握度（提示用户补充分数）
            payload.setdefault("score", 0)
            trace["score"] = {"status": "skipped", "elapsed": 0,
                              "reason": "未提供 student_explanation"}

        # ---------- 3. CoachAgent 建议 ----------
        try:
            coach = self.agents["coach"].run(payload)
            if coach.get("success"):
                payload["mastery_level"] = coach.get("mastery_level", "")
                payload["suggestions"] = coach.get("suggestions", [])
                payload["next_topics"] = coach.get("next_topics", [])
                trace["coach"] = {"status": "ok", "elapsed": coach.get("elapsed", 0)}
            else:
                trace["coach"] = {"status": "failed", "elapsed": 0,
                                  "error": coach.get("error", "")}
        except Exception as e:
            trace["coach"] = {"status": "failed", "elapsed": 0, "error": str(e)}

        # ---------- 聚合报告 ----------
        total_time = round(time.time() - t0, 2)
        report = {
            "topic": payload.get("topic", ""),
            "subject": payload.get("subject", ""),
            "difficulty": payload.get("difficulty", "高中"),
            "user_id": payload.get("user_id", 0),
            "teaching": {
                "steps": payload.get("teaching_steps", []),
                "full_content": payload.get("teaching_content", ""),
            },
            "assessment": {
                "score": payload.get("score", 0),
                "dimensions": payload.get("dimensions", {}),
                "is_mastered": payload.get("is_mastered", False),
                "feedback": payload.get("feedback", ""),
            },
            "coaching": {
                "mastery_level": payload.get("mastery_level", ""),
                "suggestions": payload.get("suggestions", []),
                "next_topics": payload.get("next_topics", []),
            },
            "agent_trace": trace,
            "total_time": total_time,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return report


# 单例（与 goai_agent 的 agent 全局实例保持一致的访问方式）
_orchestrator_instance: Optional[MultiAgentOrchestrator] = None


def get_multi_agent_orchestrator() -> MultiAgentOrchestrator:
    """获取全局多 Agent 编排器单例"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = MultiAgentOrchestrator()
    return _orchestrator_instance


# ============================================================
# 便捷入口
# ============================================================
def run_multi_agent(payload: Dict) -> Dict:
    """一行调用多 Agent 编排（默认单例）"""
    return get_multi_agent_orchestrator().run(payload)


if __name__ == "__main__":
    print("=" * 60)
    print("  🤖 多 Agent 协作系统 - 测试")
    print("=" * 60)
    demo = {
        "topic": "函数的单调性",
        "subject": "数学",
        "difficulty": "高中",
        "user_id": 1,
        "student_explanation": "函数的单调性就是自变量增大时函数值跟着增大或减小的性质，"
                               "增函数就像上坡路，减函数就像下坡路。",
    }
    orchestrator = MultiAgentOrchestrator()
    result = orchestrator.run(demo)
    print("  主题: %s" % result["topic"])
    print("  教学步骤数: %d" % len(result["teaching"]["steps"]))
    print("  评分: %s" % result["assessment"]["score"])
    print("  掌握等级: %s" % result["coaching"]["mastery_level"])
    print("  建议数: %d" % len(result["coaching"]["suggestions"]))
    print("  推荐知识点: %d" % len(result["coaching"]["next_topics"]))
    print("  Agent 状态: %s" % {k: v["status"] for k, v in result["agent_trace"].items()})
    print("  总耗时: %ss" % result["total_time"])
    print("=" * 60)
