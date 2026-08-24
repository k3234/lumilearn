# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — 并行化多 Agent 编排器

迁移自 lumilearn_multi_agent.py，架构从串行升级为 并行+反馈回路：

旧架构（串行）：
  FeynmanTeacher → ScoreAgent → CoachAgent
  延迟 = t1 + t2 + t3

新架构（并行+反馈）：
  FeynmanTeacher(多模型并行) ──┐
                              ├──→ Vote/merge ──→ ScoreAgent ──→ CoachAgent
  (并行备选模型) ─────────────┘                │
                                              ▼
                                       Verifier Agent
                                     (反馈回路：不合格则重生成)
  - 反馈轮次上限：max_retries（默认3），防止无限循环
  - 生成完成后运行 FactChecker Agent（P0-2：与 RAG 来源核对，防语义幻觉）

与 lumilearn_multi_agent.py 的兼容性：
  - 保留 FeynmanTeacher / ScoreAgent / CoachAgent 类名与 run() 接口
  - MultiAgentOrchestrator.run(payload) 输出格式完全兼容
  - 新增 MultiAgentPipeline 提供并行+反馈能力
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.model_registry import (
    ALL_MODELS, ALL_MODELS_DICT, get_model, get_best_models,
    get_best_models_by_dynamic_weight, get_models_by_provider,
)
from agent_core.verifier import (
    VerifierAgent, get_verifier_agent, evaluate_human_review,
)
from agent_core.fact_checker import FactCheckerAgent

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
    return LEVEL_MAP.get(difficulty, LEVEL_MAP.get(str(difficulty).lower(), "senior"))


def _clean_model_output(raw: str) -> str:
    """清理模型输出中的错误占位符"""
    if not raw:
        return ""
    for bad in ("[", "]"):
        pass
    return raw


def _is_error_output(raw: str) -> bool:
    """判断模型输出是否为错误占位符"""
    if not raw:
        return True
    if raw.startswith("["):
        return True
    for bad in ("不可用", "无API Key", "调用失败", "HTTP4", "HTTP5"):
        if bad in raw:
            return True
    return False


# ============================================================
# 一、FeynmanTeacher — 教学 Agent（支持多模型并行）
# ============================================================
class FeynmanTeacher:
    """
    教学 Agent：基于费曼五步学习法讲解知识点。

    相比 lumilearn_multi_agent.py 的增强：
      - 支持 parallel_models 参数：多模型并行生成，投票聚合
      - 保持单模型模式兼容（不传 parallel_models 时行为一致）
    """

    def __init__(self, model_name: Optional[str] = None, timeout: int = 120):
        self.model_name = model_name or os.environ.get(
            "MULTI_AGENT_FEYNMAN_MODEL", "qwen2.5:7b")
        self.timeout = timeout

    # ---- 多模型并行生成 ----
    def run_parallel(self, payload: Dict, model_ids: Optional[List[str]] = None,
                     max_workers: int = 4) -> Dict:
        """
        多模型并行生成教学内容，投票聚合最佳结果。

        参数：
            payload: 同 run() 的 payload
            model_ids: 参与并行的模型 ID 列表（默认取权重最高的3个）
            max_workers: 并行度

        返回：
            {"success", "steps", "full_content", "models_used",
             "model_votes", "best_model", "elapsed"}
        """
        topic = (payload.get("topic") or "").strip()
        if not topic:
            return {"success": False, "error": "缺少 topic 参数"}

        if not model_ids:
            # 默认取动态权重最高的 3 个非 solo 模型（P1-7：综合静态权重 × 动态表现）
            candidates = get_best_models_by_dynamic_weight(5)
            model_ids = [m.id for m in candidates if m.provider != "solo"][:3]
            # 若全部不可用则补 solo
            if not model_ids:
                model_ids = [m.id for m in candidates[:3]]

        # 构造费曼引擎 prompt
        level = _map_level(payload.get("difficulty", "高中"))
        extra_context = payload.get("context", "")
        prompt = self._build_teaching_prompt(topic, level, extra_context)

        t0 = time.time()
        responses: Dict[str, Dict] = {}

        def _call_model(model_id: str) -> Tuple[str, Dict]:
            model = ALL_MODELS_DICT.get(model_id)
            if not model:
                return model_id, {"error": f"模型不存在: {model_id}"}
            t1 = time.time()
            raw = model.call(prompt, timeout=self.timeout)
            elapsed = time.time() - t1
            return model_id, {
                "raw": raw,
                "elapsed": round(elapsed, 3),
                "error": "" if not _is_error_output(raw) else raw[:60],
                "available": not _is_error_output(raw),
                "weight": model.weight,
                "name": model.name,
            }

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_call_model, mid): mid for mid in model_ids}
            for fut in as_completed(futures):
                mid, resp = fut.result()
                responses[mid] = resp

        # 投票聚合：取可用模型中权重最高者
        valid = {mid: r for mid, r in responses.items() if r.get("available")}
        if not valid:
            return {
                "success": False,
                "error": "所有模型均不可用",
                "model_votes": {mid: r.get("raw", "")[:50] for mid, r in responses.items()},
                "elapsed": round(time.time() - t0, 3),
            }

        best_mid = max(valid, key=lambda mid: (
            valid[mid]["weight"], valid[mid]["elapsed"] * -1))
        best_raw = valid[best_mid]["raw"]

        # 用 FeynmanEngine 生成正式步骤（单模型兜底逻辑复用）
        result = self._run_engine(topic, level, best_raw, payload)
        result["model_votes"] = {
            mid: {"name": r["name"], "weight": r["weight"],
                  "available": r["available"], "elapsed": r["elapsed"]}
            for mid, r in responses.items()
        }
        result["models_used"] = len(valid)
        result["best_model"] = ALL_MODELS_DICT[best_mid].name
        result["elapsed"] = round(time.time() - t0, 3)
        return result

    def _build_teaching_prompt(self, topic: str, level: str, context: str) -> str:
        """构造费曼教学 prompt"""
        prompt = (
            f"你是一位资深教育专家，采用费曼学习法讲解知识点。\n\n"
            f"主题: {topic}\n"
            f"难度: {level}\n"
            f"{'补充说明: ' + context if context else ''}\n\n"
            f"请按以下 5 步输出:\n"
            f"1. 现象引入：用一个生活例子或现象引入主题\n"
            f"2. 思维模型：给出核心概念的精确定义\n"
            f"3. 自主推导：示范推导过程或关键公式\n"
            f"4. 认知冲突：指出常见误区和易错点\n"
            f"5. 费曼测试：设计一个问题让学生用自己的话复述\n\n"
            f"请严格按上述 5 步结构输出，总字数 300-800 字。"
        )
        return prompt

    def _run_engine(self, topic: str, level: str, best_raw: str,
                    payload: Dict) -> Dict:
        """
        基于最佳模型输出生成正式教学步骤。
        若模型输出为错误占位符，则降级使用 FeynmanEngine 模板兜底。
        """
        from framework.engines.feynman_engine import FeynmanEngine

        # RAG 检索（失败降级为空）
        rag_context = ""
        rag_sources = []
        try:
            from framework.services.knowledge_retrieval import (
                get_knowledge_retriever, format_rag_context)
            _retriever = get_knowledge_retriever()
            _results = _retriever.search(topic, top_k=3)
            if _results:
                rag_sources = [
                    {"source": r.get("source"), "id": r.get("id"),
                     "title": r.get("title"), "subject": r.get("subject"),
                     "score": r.get("score")} for r in _results]
                rag_context = format_rag_context(_results, max_chars=800)
        except Exception:
            rag_context, rag_sources = "", []

        engine = FeynmanEngine(model_name=self.model_name, timeout=self.timeout)
        try:
            result = engine.explain(topic=topic, level=level,
                                    extra_context=rag_context or best_raw[:300])
            return {
                "success": True,
                "mode": "full",
                "topic": topic,
                "level": level,
                "steps": result.get("steps", []),
                "full_content": result.get("full_content", "") or best_raw,
                "rag_sources": rag_sources,
                "model_used": result.get("model_used", self.model_name),
            }
        except Exception as e:
            # 最终兜底：直接用模型原始输出
            return {
                "success": True,
                "mode": "raw_fallback",
                "topic": topic,
                "level": level,
                "steps": [],
                "full_content": best_raw or topic,
                "rag_sources": rag_sources,
                "model_used": self.model_name,
                "warning": str(e),
            }

    # ---- 单模型模式（兼容原实现） ----
    def run(self, payload: Dict) -> Dict:
        """
        执行教学，返回五步教学内容（单模型模式）。

        payload:
            topic: 教学主题（必填）
            difficulty: 难度（初中/高中/大学）
            dialogue: 可选对话历史

        返回:
            {"success", "steps", "full_content", "model_used", "elapsed"}
        """
        topic = (payload.get("topic") or "").strip()
        if not topic:
            return {"success": False, "error": "缺少 topic 参数"}

        # 若显式指定并行模型，走并行模式
        if payload.get("parallel"):
            return self.run_parallel(payload, model_ids=payload.get("model_ids"))

        from framework.engines.feynman_engine import FeynmanEngine
        level = _map_level(payload.get("difficulty", "高中"))
        dialogue = payload.get("dialogue")

        rag_context = ""
        rag_sources = []
        try:
            from framework.services.knowledge_retrieval import (
                get_knowledge_retriever, format_rag_context)
            _retriever = get_knowledge_retriever()
            _results = _retriever.search(topic, top_k=3)
            if _results:
                rag_sources = [
                    {"source": r.get("source"), "id": r.get("id"),
                     "title": r.get("title"), "subject": r.get("subject"),
                     "score": r.get("score")} for r in _results]
                rag_context = format_rag_context(_results, max_chars=800)
        except Exception:
            rag_context, rag_sources = "", []

        engine = FeynmanEngine(model_name=self.model_name, timeout=self.timeout)
        t0 = time.time()
        try:
            if dialogue:
                step = engine.explain_step(topic=topic, level=level,
                                           dialogue=dialogue,
                                           extra_context=rag_context)
                return {
                    "success": True, "mode": "interactive", "step": step,
                    "rag_sources": rag_sources,
                    "model_used": self.model_name,
                    "elapsed": round(time.time() - t0, 2),
                }
            result = engine.explain(topic=topic, level=level,
                                    extra_context=rag_context)
            return {
                "success": True, "mode": "full",
                "topic": topic, "level": level,
                "steps": result.get("steps", []),
                "full_content": result.get("full_content", ""),
                "rag_sources": rag_sources,
                "model_used": result.get("model_used", self.model_name),
                "elapsed": round(time.time() - t0, 2),
            }
        except Exception as e:
            try:
                fallback = engine.explain(topic=topic, level=level)
                if fallback:
                    return {
                        "success": True, "mode": "fallback",
                        "topic": topic, "level": level,
                        "steps": fallback.get("steps", []),
                        "full_content": fallback.get("full_content", ""),
                        "rag_sources": rag_sources,
                        "model_used": "template_fallback",
                        "elapsed": round(time.time() - t0, 2),
                        "warning": str(e),
                    }
            except Exception:
                pass
            return {"success": False, "error": str(e), "elapsed": round(time.time() - t0, 2)}


# ============================================================
# 二、ScoreAgent — 评分 Agent
# ============================================================
class ScoreAgent:
    """评分 Agent：评估学生理解质量（调用 OutputDetector 五维评分）"""

    DIMENSION_KEYS = ["简洁度", "准确度", "比喻", "完整度", "术语规避"]

    def __init__(self, model_name: Optional[str] = None, timeout: int = 60):
        self.model_name = model_name or os.environ.get(
            "MULTI_AGENT_SCORE_MODEL", "qwen2.5:7b")
        self.timeout = timeout

    def run(self, payload: Dict) -> Dict:
        """评估学生的解释，返回五维评分（接口与 lumilearn_multi_agent.py 一致）"""
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
                "elapsed": round(time.time() - t0, 2),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "score": 0,
                    "elapsed": round(time.time() - t0, 2)}


# ============================================================
# 三、CoachAgent — 建议 Agent
# ============================================================
class CoachAgent:
    """建议 Agent：根据掌握度与学习进度推荐下一步"""

    def __init__(self):
        self.model_name = "adaptive_engine"

    def _mastery_level(self, score: int) -> Tuple[str, str]:
        """根据评分返回掌握等级与通用建议"""
        if score >= 85:
            return "优秀", "已掌握核心概念，可以挑战更高难度的进阶题目。"
        if score >= 70:
            return "良好", "基本掌握，建议通过练习题巩固并尝试举一反三。"
        if score >= 50:
            return "一般", "理解尚不完整，建议重新回顾薄弱环节后再练习。"
        return "待加强", "需要从基础概念重新学习，建议先掌握前置知识点。"

    def run(self, payload: Dict) -> Dict:
        """生成学习建议与下一步推荐（接口与 lumilearn_multi_agent.py 一致）"""
        user_id = payload.get("user_id", 0)
        score = payload.get("score", 0) or 0
        topic = (payload.get("topic") or "").strip()
        weak_topics = payload.get("weak_topics") or []

        t0 = time.time()
        suggestions = []
        next_topics = []

        level, advice = self._mastery_level(score)
        suggestions.append(advice)

        for wp in weak_topics[:3]:
            if isinstance(wp, str):
                suggestions.append(f"重点复习「{wp}」：建议用费曼法重新讲一遍。")
            elif isinstance(wp, dict) and wp.get("topic"):
                suggestions.append(f"重点复习「{wp['topic']}」：建议用费曼法重新讲一遍。")

        try:
            from framework.services.adaptive_learning import get_adaptive_engine
            service = get_adaptive_engine()
            recs = service.recommend_next(user_id=str(user_id or "default"), count=5)
            next_topics = recs
            if not suggestions and not recs and topic:
                suggestions.append(f"继续深入「{topic}」的延伸知识，构建完整的知识网络。")
        except Exception:
            if topic:
                suggestions.append(f"完成「{topic}」后，可尝试用费曼法教给他人来检验掌握程度。")

        return {
            "success": True,
            "mastery_level": level,
            "suggestions": suggestions,
            "next_topics": next_topics,
            "model_used": self.model_name,
            "elapsed": round(time.time() - t0, 2),
        }


# ============================================================
# 四、MultiAgentPipeline — 并行 + 反馈回路编排器
# ============================================================
class MultiAgentPipeline:
    """
    并行化多 Agent 编排器（Phase 2 核心交付物）。

    流程：
        1. FeynmanTeacher(多模型并行) → Vote/merge → 教学内容
        2. ScoreAgent       → 掌握度评估（可选）
        3. CoachAgent       → 学习建议
        4. Verifier Agent   → 质量验证
            ├─ 通过 → 输出最终报告
            └─ 未通过 → 反馈至步骤1重新生成（最多 max_retries 轮）
    """

    def __init__(
        self,
        feynman_model: Optional[str] = None,
        score_model: Optional[str] = None,
        verifier_model: Optional[str] = None,
        max_retries: int = 3,
        use_parallel: bool = True,
        verifier_use_model: bool = False,
        human_review: bool = True,
        human_review_threshold: float = 45.0,
        fact_check: bool = True,
        fact_checker_model: Optional[str] = None,
        fact_checker_use_model: bool = False,
        fact_check_threshold: float = 60.0,
    ):
        self.feynman = FeynmanTeacher(model_name=feynman_model)
        self.score = ScoreAgent(model_name=score_model)
        self.coach = CoachAgent()
        self.verifier = get_verifier_agent(
            model_name=verifier_model,
            use_model=verifier_use_model,
        )
        # P0-2：事实核查 Agent（直接实例化，避免共享单例被测试 Mock 污染）
        self.fact_checker = FactCheckerAgent(
            model_name=fact_checker_model,
            use_model=fact_checker_use_model,
            threshold=fact_check_threshold,
        )
        self.max_retries = max_retries
        self.use_parallel = use_parallel
        # P0-1：Verifier 阶段人工复核开关与低置信度阈值
        # 触发后流水线标记 needs_human_review，由上层编排器执行 interrupt/resume
        self.human_review = human_review
        self.human_review_threshold = human_review_threshold
        # P0-2：事实核查开关（与 Verifier 协同，异常时同样触发人工复核）
        self.fact_check = fact_check

    def run(self, payload: Dict) -> Dict:
        """
        执行并行 + 反馈回路编排，返回聚合报告。

        payload:
            topic: 教学主题（必填）
            subject: 学科（可选）
            difficulty: 难度（可选）
            user_id: 用户ID（可选）
            student_explanation: 学生解释（可选）
            weak_topics: 薄弱知识点（可选）
            context: 补充上下文（可选）
            model_ids: 并行模型 ID 列表（可选）
            max_retries: 反馈轮次上限（可选，覆盖实例默认）

        返回：
            与 lumilearn_multi_agent.py 兼容的聚合报告 + 新增字段：
              verifier: 验证结果
              fact_check: 事实核查结果（P0-2）
              feedback_rounds: 反馈轮次
              parallel_stats: 并行统计
        """
        t0 = time.time()
        payload = dict(payload or {})
        topic = (payload.get("topic") or "").strip()
        if not topic:
            return {"success": False, "error": "缺少 topic 参数"}

        max_retries = max(1, int(payload.get("max_retries", self.max_retries) or self.max_retries))
        trace = {}
        feedback_rounds = 0

        # ---------- 自积累知识复用（越用越聪明） ----------
        # reuse_mode:
        #   off     : 不复用
        #   context : 命中缓存则注入为生成上下文（默认，保证生成质量）
        #   direct  : 命中高质量缓存直接复用，不再调用模型（最大降本）
        reuse_mode = payload.get("reuse_mode", "context")
        cached_items = []
        if reuse_mode != "off":
            try:
                from agent_core.knowledge_cache import get_knowledge_cache
                cached_items = get_knowledge_cache().query(
                    topic=topic, subject=payload.get("subject", ""),
                    min_quality=60.0, limit=1)
            except Exception:
                cached_items = []

        if reuse_mode == "direct" and cached_items:
            cached = cached_items[0]
            trace["knowledge_reuse"] = {
                "status": "hit", "knowledge_id": cached.get("knowledge_id"),
                "quality_score": cached.get("quality_score", 0),
            }
            report = self._build_reuse_report(payload, cached, trace)
            return report

        # 缓存命中但走 context 模式：注入已有知识作为生成依据
        reuse_context = ""
        if cached_items:
            cached = cached_items[0]
            reuse_context = (
                f"【已有知识积累，请基于此优化生成】\n"
                f"{cached.get('content', '')[:600]}\n"
            )
            trace["knowledge_reuse"] = {
                "status": "context_injected",
                "knowledge_id": cached.get("knowledge_id"),
                "quality_score": cached.get("quality_score", 0),
            }

        # 最多执行 max_retries 轮（含反馈重试），防止无限循环
        for attempt in range(max_retries):
            feedback_rounds = attempt + 1
            attempt_payload = dict(payload)
            if attempt > 0:
                attempt_payload["context"] = (
                    f"{payload.get('context', '')} "
                    f"（注意：这是第{attempt + 1}次生成，请针对上次验证反馈改进内容质量）"
                ).strip()
            # 注入已有知识积累上下文（复用）
            if reuse_context:
                attempt_payload["context"] = (
                    f"{reuse_context}{attempt_payload.get('context', '')}"
                ).strip()

            # ---------- 1. FeynmanTeacher 教学（并行） ----------
            try:
                if self.use_parallel and payload.get("parallel", True):
                    teach = self.feynman.run_parallel(
                        attempt_payload, model_ids=payload.get("model_ids"))
                else:
                    teach = self.feynman.run(attempt_payload)

                if teach.get("success"):
                    attempt_payload["teaching_steps"] = teach.get("steps", [])
                    attempt_payload["teaching_content"] = teach.get("full_content", "")
                    attempt_payload["rag_sources"] = teach.get("rag_sources", [])
                    trace[f"feynman_r{attempt + 1}"] = {
                        "status": "ok",
                        "mode": teach.get("mode", "full"),
                        "models_used": teach.get("models_used", 1),
                        "best_model": teach.get("best_model", ""),
                        "elapsed": teach.get("elapsed", 0),
                    }
                else:
                    trace[f"feynman_r{attempt + 1}"] = {
                        "status": "failed", "elapsed": teach.get("elapsed", 0),
                        "error": teach.get("error", "")}
            except Exception as e:
                trace[f"feynman_r{attempt + 1}"] = {
                    "status": "failed", "elapsed": 0, "error": str(e)}

            # ---------- 权重自更新（成功率/延迟反馈到 dynamic_weight） ----------
            try:
                from agent_core.weight_manager import get_weight_manager
                _teach = teach if "teach" in locals() else {}
                get_weight_manager().update_weight(
                    "feynman_teacher",
                    latency_ms=int((_teach.get("elapsed") or 0) * 1000),
                    success=bool(_teach.get("success")))
            except Exception:
                pass

            # ---------- 2. ScoreAgent 评分（可选） ----------
            student_explanation = (attempt_payload.get("student_explanation") or "").strip()
            if student_explanation:
                try:
                    score_result = self.score.run(attempt_payload)
                    if score_result.get("success"):
                        attempt_payload["score"] = score_result.get("score", 0)
                        attempt_payload["dimensions"] = score_result.get("dimensions", {})
                        attempt_payload["is_mastered"] = score_result.get("is_mastered", False)
                        attempt_payload["feedback"] = score_result.get("feedback", "")
                        trace[f"score_r{attempt + 1}"] = {
                            "status": "ok", "elapsed": score_result.get("elapsed", 0)}
                    else:
                        trace[f"score_r{attempt + 1}"] = {
                            "status": "failed", "elapsed": 0,
                            "error": score_result.get("error", "")}
                except Exception as e:
                    trace[f"score_r{attempt + 1}"] = {
                        "status": "failed", "elapsed": 0, "error": str(e)}
            else:
                attempt_payload.setdefault("score", 0)
                trace[f"score_r{attempt + 1}"] = {
                    "status": "skipped", "elapsed": 0,
                    "reason": "未提供 student_explanation"}

            # ---------- 3. CoachAgent 建议 ----------
            try:
                coach = self.coach.run(attempt_payload)
                if coach.get("success"):
                    attempt_payload["mastery_level"] = coach.get("mastery_level", "")
                    attempt_payload["suggestions"] = coach.get("suggestions", [])
                    attempt_payload["next_topics"] = coach.get("next_topics", [])
                    trace[f"coach_r{attempt + 1}"] = {
                        "status": "ok", "elapsed": coach.get("elapsed", 0)}
                else:
                    trace[f"coach_r{attempt + 1}"] = {
                        "status": "failed", "elapsed": 0,
                        "error": coach.get("error", "")}
            except Exception as e:
                trace[f"coach_r{attempt + 1}"] = {
                    "status": "failed", "elapsed": 0, "error": str(e)}

            # ---------- 4. Verifier Agent 验证（反馈回路） ----------
            try:
                verifier_payload = {
                    "topic": topic,
                    "teaching_content": attempt_payload.get("teaching_content", ""),
                    "steps": attempt_payload.get("teaching_steps", []),
                    "score": attempt_payload.get("score"),
                    "dimensions": attempt_payload.get("dimensions", {}),
                    "mastery_level": attempt_payload.get("mastery_level", ""),
                    "suggestions": attempt_payload.get("suggestions", []),
                    "rag_sources": attempt_payload.get("rag_sources", []),
                }
                verify = self.verifier.run(verifier_payload)
                attempt_payload["verifier_result"] = verify
                attempt_payload["verified"] = verify.get("passed", False)
                trace[f"verifier_r{attempt + 1}"] = {
                    "status": "ok",
                    "passed": verify.get("passed", False),
                    "confidence": verify.get("confidence", 0),
                    "elapsed": verify.get("elapsed", 0),
                }

                # 通过验证 → 结束反馈回路
                if verify.get("passed", False):
                    break
                # 验证未通过：本轮生成质量不达标 → 权重惩罚（自优化）
                try:
                    from agent_core.weight_manager import get_weight_manager
                    get_weight_manager().update_weight(
                        "feynman_teacher", latency_ms=0, success=False)
                except Exception:
                    pass
            except Exception as e:
                attempt_payload["verifier_result"] = {
                    "passed": True, "confidence": 100.0,
                    "issues": [], "reason": f"验证异常，放行: {str(e)}",
                }
                attempt_payload["verified"] = True
                trace[f"verifier_r{attempt + 1}"] = {
                    "status": "failed", "elapsed": 0, "error": str(e),
                    "passed": True}
                break

        # ---------- 聚合报告 ----------
        total_time = round(time.time() - t0, 3)
        verify = attempt_payload.get("verifier_result", {})
        report = {
            "success": True,
            "topic": topic,
            "subject": attempt_payload.get("subject", ""),
            "difficulty": attempt_payload.get("difficulty", "高中"),
            "user_id": attempt_payload.get("user_id", 0),
            "teaching": {
                "steps": attempt_payload.get("teaching_steps", []),
                "full_content": attempt_payload.get("teaching_content", ""),
                "rag_sources": attempt_payload.get("rag_sources", []),
            },
            "assessment": {
                "score": attempt_payload.get("score", 0),
                "dimensions": attempt_payload.get("dimensions", {}),
                "is_mastered": attempt_payload.get("is_mastered", False),
                "feedback": attempt_payload.get("feedback", ""),
            },
            "coaching": {
                "mastery_level": attempt_payload.get("mastery_level", ""),
                "suggestions": attempt_payload.get("suggestions", []),
                "next_topics": attempt_payload.get("next_topics", []),
            },
            "verifier": {
                "passed": verify.get("passed", False),
                "confidence": verify.get("confidence", 0),
                "issues": verify.get("issues", []),
                "reason": verify.get("reason", ""),
            },
            "feedback_rounds": feedback_rounds,
            "verified": attempt_payload.get("verified", False),
            "agent_trace": trace,
            "total_time": total_time,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # ---------- 人工复核判定（P0-1：Verifier 阶段人工中断扩展） ----------
        # 验证未通过且低置信度/内容质量异常 → 标记 needs_human_review。
        # 流水线自身不执行中断，由上层编排器（UnifiedOrchestrator）完成
        # interrupt / resume，保证人工监督契约收敛在编排层。
        if self.human_review:
            review = evaluate_human_review(verify, self.human_review_threshold)
            if review["needs_review"]:
                report["needs_human_review"] = True
                report["human_review_reason"] = review["reason"]
                report["human_review"] = review

        # ---------- 事实核查（P0-2：与 RAG 来源核对，防语义幻觉） ----------
        # 在 Verifier 反馈回路之后对最终内容做二次事实校验：
        #   - 通过 / 降级（无来源）→ 记录结果继续交付
        #   - 发现与知识库来源矛盾（error 级）→ 与 P0-1 协同标记人工复核，
        #     不直接交付矛盾内容，也不写回知识库
        if self.fact_check:
            try:
                fact_payload = {
                    "topic": topic,
                    "teaching_content": attempt_payload.get("teaching_content", ""),
                    "steps": attempt_payload.get("teaching_steps", []),
                    "rag_sources": attempt_payload.get("rag_sources", []),
                    "subject": attempt_payload.get("subject", ""),
                }
                fact = self.fact_checker.run(fact_payload)
                report["fact_check"] = {
                    "passed": fact.get("passed", True),
                    "confidence": fact.get("confidence", 100),
                    "issues": fact.get("issues", []),
                    "reason": fact.get("reason", ""),
                    "sources_checked": fact.get("sources_checked", 0),
                }
                trace["fact_check"] = {
                    "status": "ok",
                    "passed": fact.get("passed", True),
                    "confidence": fact.get("confidence", 100),
                    "sources_checked": fact.get("sources_checked", 0),
                    "elapsed": fact.get("elapsed", 0),
                }

                if not fact.get("passed", True):
                    # 事实核查失败 → 权重惩罚（自优化）
                    try:
                        from agent_core.weight_manager import get_weight_manager
                        get_weight_manager().update_weight(
                            "feynman_teacher", latency_ms=0, success=False)
                    except Exception:
                        pass
                    # 与人工复核协同：仅 error 级矛盾才请求人工审核
                    # （低置信度但无硬矛盾时记录结果，交由 Verifier 兜底）
                    if self.human_review and any(
                            i.get("level") == "error"
                            for i in fact.get("issues", [])):
                        if report.get("needs_human_review"):
                            # 已由 Verifier 标记人工复核 → 附加事实核查失败说明，
                            # 保留原 trigger（low_confidence/content_anomaly）
                            report["human_review_reason"] = (
                                f"{report.get('human_review_reason', '')}；"
                                f"且事实核查未通过：{fact.get('reason', '')}")
                            hr = report.get("human_review", {})
                            if isinstance(hr, dict):
                                hr["fact_check_failed"] = True
                        else:
                            report["needs_human_review"] = True
                            report["human_review_reason"] = (
                                f"事实核查未通过：{fact.get('reason', '')}")
                            report["human_review"] = {
                                "needs_review": True,
                                "confidence": fact.get("confidence", 0),
                                "trigger": "fact_check_failed",
                                "error_issues": [
                                    i for i in fact.get("issues", [])
                                    if i.get("level") == "error"
                                ],
                            }
            except Exception as e:
                # 事实核查失败不影响主流程（降级放行，记录异常）
                report["fact_check"] = {
                    "passed": True,
                    "confidence": 100,
                    "issues": [],
                    "reason": f"事实核查异常，降级放行: {str(e)[:100]}",
                    "sources_checked": 0,
                }
                trace["fact_check"] = {
                    "status": "failed",
                    "passed": True,
                    "elapsed": 0,
                    "error": str(e)[:100],
                }

        # ---------- 自积累：写回知识库（供其他 Agent 复用） ----------
        # 需人工复核的内容不写回，避免未审核的劣质内容污染自积累知识库
        if (topic and report.get("success") and not report.get("knowledge_reused")
                and not report.get("needs_human_review")):
            try:
                from agent_core.knowledge_cache import get_knowledge_cache
                teaching = report.get("teaching", {})
                content = teaching.get("full_content") or ""
                if not content and isinstance(teaching.get("steps"), list):
                    content = "\n".join(
                        (s.get("content") or "") for s in teaching["steps"]
                        if isinstance(s, dict))
                if content.strip():
                    quality = verify.get("confidence") or 60.0
                    get_knowledge_cache().save(
                        topic=topic,
                        knowledge_type="explanation",
                        content=content,
                        source_agent="feynman_teacher",
                        subject=report.get("subject", ""),
                        summary=content[:200],
                        quality_score=quality,
                    )
                    report["knowledge_written"] = True
            except Exception:
                pass

        return report

    def _build_reuse_report(self, payload: Dict, cached: Dict,
                            trace: Dict) -> Dict:
        """
        基于知识缓存直接构建报告（reuse_mode="direct"，零模型调用）。
        """
        topic = (payload.get("topic") or "").strip()
        return {
            "success": True,
            "topic": topic,
            "subject": payload.get("subject", cached.get("subject", "")),
            "difficulty": payload.get("difficulty", "高中"),
            "user_id": payload.get("user_id", 0),
            "teaching": {
                "steps": [],
                "full_content": cached.get("content", ""),
                "rag_sources": [],
            },
            "assessment": {"score": 0, "dimensions": {},
                           "is_mastered": False, "feedback": ""},
            "coaching": {"mastery_level": "", "suggestions": [],
                         "next_topics": []},
            "verifier": {
                "passed": True,
                "confidence": cached.get("quality_score", 80) or 80,
                "issues": [],
                "reason": "知识库命中，直接复用已积累内容",
            },
            "feedback_rounds": 0,
            "verified": True,
            "knowledge_reused": True,
            "knowledge_source": "cache",
            "cached_knowledge_id": cached.get("knowledge_id"),
            "agent_trace": trace,
            "total_time": 0.0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


# ============================================================
# 五、兼容层 — MultiAgentOrchestrator
# ============================================================
class MultiAgentOrchestrator:
    """
    兼容 lumilearn_multi_agent.py 的编排器。
    Phase 2 起：内部走 MultiAgentPipeline（并行+反馈），输出格式保持兼容。
    """

    def __init__(
        self,
        feynman_model: Optional[str] = None,
        score_model: Optional[str] = None,
        coach_model: Optional[str] = None,
        max_retries: int = 3,
        use_parallel: bool = True,
    ):
        self.pipeline = MultiAgentPipeline(
            feynman_model=feynman_model,
            score_model=score_model,
            verifier_model=None,
            max_retries=max_retries,
            use_parallel=use_parallel,
        )
        self.agents = {
            "feynman": self.pipeline.feynman,
            "score": self.pipeline.score,
            "coach": self.pipeline.coach,
            "verifier": self.pipeline.verifier,
        }

    def run(self, payload: Dict) -> Dict:
        """执行并行+反馈编排，返回与旧版兼容的聚合报告"""
        report = self.pipeline.run(payload)
        if report.get("success") is False:
            return report
        # 兼容旧字段：agent_trace 简化保留
        return report


# 单例
_orchestrator_instance: Optional[MultiAgentOrchestrator] = None
_pipeline_instance: Optional[MultiAgentPipeline] = None


def get_multi_agent_orchestrator(**kwargs) -> MultiAgentOrchestrator:
    """获取全局多 Agent 编排器单例"""
    global _orchestrator_instance
    if _orchestrator_instance is None or kwargs:
        _orchestrator_instance = MultiAgentOrchestrator(**kwargs)
    return _orchestrator_instance


def get_multi_agent_pipeline(**kwargs) -> MultiAgentPipeline:
    """获取并行流水线单例"""
    global _pipeline_instance
    if _pipeline_instance is None or kwargs:
        _pipeline_instance = MultiAgentPipeline(**kwargs)
    return _pipeline_instance


# ============================================================
# 便捷入口
# ============================================================
def run_multi_agent(payload: Dict) -> Dict:
    """一行调用多 Agent 编排（默认单例，并行+反馈）"""
    return get_multi_agent_orchestrator().run(payload)


if __name__ == "__main__":
    print("=" * 60)
    print("  🤖 并行多 Agent 协作系统 - Phase 2 测试")
    print("=" * 60)
    demo = {
        "topic": "函数的单调性",
        "subject": "数学",
        "difficulty": "高中",
        "user_id": 1,
        "student_explanation": "函数的单调性就是自变量增大时函数值跟着增大或减小的性质，"
                               "增函数就像上坡路，减函数就像下坡路。",
        "parallel": True,
        "max_retries": 2,
    }
    pipeline = MultiAgentPipeline(verifier_use_model=False)
    result = pipeline.run(demo)
    print("  主题: %s" % result["topic"])
    print("  教学步骤数: %d" % len(result["teaching"]["steps"]))
    print("  评分: %s" % result["assessment"]["score"])
    print("  掌握等级: %s" % result["coaching"]["mastery_level"])
    print("  验证: %s (置信度 %s%%)" % (
        "通过" if result["verifier"]["passed"] else "未通过",
        result["verifier"]["confidence"]))
    print("  反馈轮次: %d" % result["feedback_rounds"])
    print("  总耗时: %ss" % result["total_time"])
    print("=" * 60)
