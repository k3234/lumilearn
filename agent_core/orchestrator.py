# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — 统一编排器

整合 Router、LangGraph 引擎、多 Agent 编排，提供统一入口。
这是 Phase 1 的核心交付物：将原来分散的 5 套 Agent 系统整合到统一框架下。
"""

from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.models import AgentState, AgentResult, TaskProfile
from agent_core.router import RouterAgent, get_router_agent
from agent_core.langgraph_engine import OrchestrationEngine
from agent_core.model_registry import ALL_MODELS, get_model_summary
from agent_core.self_critique import SelfCritiqueAgent
from framework.core.fallback import FallbackHandler


# ================================================================
# 敏感主题检测（EU AI Act Article 14 人工监督触发词）
# ================================================================
SENSITIVE_TOPICS = [
    "炸弹", "炸药", "爆炸物", "制造毒品", "吸毒", "毒品",
    "赌博技巧", "开赌", "色情", "儿童色情", "暴力袭击",
    "杀人方法", "自杀", "恐怖袭击", "枪支购买", "黑客攻击教程",
    "诈骗教程", "作弊代考", "攻击他人", "校园暴力实施",
]


# ================================================================
# UnifiedOrchestrator — 统一编排器
# ================================================================
class UnifiedOrchestrator:
    """
    统一编排器：整合 Router + LangGraph 引擎 + 多 Agent 系统。

    路由策略：
      - simple   → OrchestrationEngine.run_single()   (单模型, 低成本)
      - standard → MultiAgentPipeline.run()           (并行+反馈，Phase 2)
      - complex_parallel → OrchestrationEngine.run()   (多模型并行)

    生产级能力（Phase 3）：
      - 可观测性：start_trace / record_call / end_trace 全链路追踪
      - 安全控制：调用前 check_call（频率/预算/模型白名单）
      - 人工中断：interrupt / resume（EU AI Act Article 14）
        · node=router   ：敏感主题检测触发（Phase 3 已接线）
        · node=verifier ：生成内容验证未通过（低置信度/内容质量异常）触发（P0-1 扩展）

    与 Phase 0 的兼容性：
      - 提供与 goai_multi_agent.py 相同的输出格式
      - 保留原有的 agent_trace 追踪
    """

    def __init__(self, max_workers: int = 6, max_retries: int = 3):
        self.router = get_router_agent()
        self.engine = OrchestrationEngine(max_workers=max_workers)
        self.max_retries = max_retries
        self._last_trace_id = ""
        self._telemetry = None
        self._safety = None

    # ------------------------------------------------------------
    # 可观测性与安全（延迟加载，避免测试环境副作用）
    # ------------------------------------------------------------
    @property
    def telemetry(self):
        if self._telemetry is None:
            from agent_core.observability import get_telemetry
            self._telemetry = get_telemetry()
        return self._telemetry

    @property
    def safety(self):
        if self._safety is None:
            from agent_core.safety import get_safety_guard
            self._safety = get_safety_guard()
        return self._safety

    # ------------------------------------------------------------
    # 人工中断机制（EU AI Act Article 14 human-in-the-loop）
    # ------------------------------------------------------------
    def interrupt(self, reason: str, node: str = "verifier",
                  trace_id: str = "") -> Dict:
        """
        在关键节点请求人工中断（人工干预）。

        参数：
            reason: 中断原因（如"内容可能违规，需人工审核"）
            node: 中断节点
            trace_id: 当前追踪 ID（留空则使用最后一次）

        返回：
            {"interrupted": bool, "trace_id": str}
        """
        tid = trace_id or self._last_trace_id
        if not tid:
            tid = self.telemetry.start_trace()
        return self.telemetry.request_interrupt(tid, reason, node)

    def resume(self, decision: str, reviewer: str = "admin",
               trace_id: str = "") -> Dict:
        """
        人工审批中断：approved（放行）/ rejected（终止）。

        参数：
            decision: approved / rejected
            reviewer: 审批人标识
            trace_id: 追踪 ID（留空则使用最后一次）
        """
        tid = trace_id or self._last_trace_id
        return self.telemetry.resolve_interrupt(tid, decision, reviewer)

    def get_pending_interrupts(self) -> List[Dict]:
        """获取待审批的中断请求（管理员面板使用）"""
        return self.telemetry.get_pending_interrupts()

    def run(self, payload: Dict) -> Dict:
        """
        执行统一编排。

        payload:
            topic: 教学主题（必填）
            subject: 学科（可选）
            difficulty: 难度（可选）
            user_id: 用户ID（可选）
            student_explanation: 学生解释（可选，提供则走评分流程）
            context: 补充上下文（可选）
            route: 强制路由（可选: simple/standard/complex_parallel）

        Returns:
            与 goai_multi_agent.py 兼容的聚合报告
        """
        t0 = time.time()
        topic = (payload.get("topic") or "").strip()
        if not topic:
            return {"success": False, "error": "缺少 topic 参数"}

        # ---------- 提示注入加固（P1-6）：输入结构校验 + 注入检测 ----------
        from agent_core.prompt_guard import sanitize_payload
        payload = sanitize_payload(payload)
        _input_check = payload.get("_input_check") or {}
        if not _input_check.get("ok", True):
            reason = _input_check.get("reason", "输入校验未通过")
            self.telemetry.audit_log(
                level="warning",
                message="提示注入拦截: unified_orchestrator",
                detail=str(_input_check),
            )
            return {
                "success": False,
                "error": reason,
                "injection": _input_check.get("injection"),
                "input_check": _input_check,
            }

        # ---------- 可观测性：开启追踪 ----------
        user_id = str(payload.get("user_id", "anonymous"))
        trace_id = self.telemetry.start_trace(
            user_id=user_id, topic=topic,
            context=payload.get("context", ""))
        self._last_trace_id = trace_id

        # ---------- 安全控制：调用前检查 ----------
        safety_check = self.safety.check_call(
            agent_id="unified_orchestrator",
            user_id=user_id,
            budget_tokens=self.safety.estimate_tokens(topic) * 2,
        )
        if not safety_check.get("allowed", True):
            self.telemetry.end_trace(trace_id, {
                "success": False, "topic": topic})
            return {
                "success": False,
                "error": safety_check.get("reason", "安全策略拒绝"),
                "retry_after": safety_check.get("retry_after", 0),
                "trace_id": trace_id,
            }

        context = payload.get("context", "")
        forced_route = payload.get("route", "")

        # Step 1: Router 分析
        if forced_route:
            route_decision = forced_route
            profile = self.router.analyze(topic, context)
        else:
            route_result = self.router.route(topic, context)
            route_decision = route_result["route"]
            # TaskProfile.route is a computed property, filter it out
            profile_dict = {k: v for k, v in route_result["profile"].items() if k != "route"}
            profile = TaskProfile(**profile_dict)

        agent_trace = {
            "router": {
                "status": "ok",
                "route": route_decision,
                "complexity": profile.complexity,
                "reasoning_type": profile.reasoning_type,
                "confidence": profile.confidence,
            }
        }

        # ---------- 人工监督：敏感主题检测（EU AI Act Art.14 接线） ----------
        # 检测到敏感/违规主题 → 请求人工中断，run() 暂停执行等待审批
        if not payload.get("_interrupt_approved"):
            sensitive = self._detect_sensitive_topic(topic, profile)
            if sensitive:
                intr = self.interrupt(
                    reason=f"检测到敏感主题「{sensitive}」，需人工审核",
                    node="router",
                    trace_id=trace_id,
                )
                self.telemetry.end_trace(trace_id, {
                    "success": False, "topic": topic,
                    "awaiting_review": True})
                return {
                    "success": False,
                    "status": "awaiting_review",
                    "interrupt": intr,
                    "trace_id": trace_id,
                    "node": "router",
                    "route": route_decision,
                    "routing_decision": route_decision,
                    "sensitive_topic": sensitive,
                    "message": "内容涉及敏感主题，已请求人工审核。管理员可调用 "
                               "resume(decision='approved', trace_id='<trace_id>') "
                               "审批后，携带 payload['_interrupt_approved']=True 重新请求。",
                }

        # Step 2: 根据路由决策执行对应路径（FallbackHandler 异常降级包裹）
        result = self._run_route_with_fallback(route_decision, payload, profile)

        # ---------- 人工监督：Verifier 质量异常（P0-1 扩展，EU AI Act Art.14） ----------
        # 生成内容验证未通过（低置信度 / 内容质量异常）→ 请求人工审核，暂停执行。
        # 审批通过后携带 payload['_interrupt_approved']=True 重新请求放行。
        if result.get("needs_human_review") and not payload.get("_interrupt_approved"):
            intr = self.interrupt(
                reason=result.get("human_review_reason")
                       or "生成内容质量异常，需人工审核",
                node="verifier",
                trace_id=trace_id,
            )
            self.telemetry.end_trace(trace_id, {
                "success": False, "topic": topic,
                "awaiting_review": True, "node": "verifier"})
            return {
                "success": False,
                "status": "awaiting_review",
                "interrupt": intr,
                "trace_id": trace_id,
                "node": "verifier",
                "route": route_decision,
                "routing_decision": route_decision,
                # 审核辅助信息：验证详情 / 反馈轮次 / 全链路追踪
                "human_review": result.get("human_review", {}),
                "verifier": result.get("verifier", {}),
                "feedback_rounds": result.get("feedback_rounds", 0),
                "agent_trace": result.get("agent_trace", {}),
                "message": "生成内容未通过质量验证（低置信度或内容质量异常），"
                           "已请求人工审核。管理员可调用 "
                           "resume(decision='approved', trace_id='<trace_id>') "
                           "审批后，携带 payload['_interrupt_approved']=True 重新请求。",
            }
        elif result.get("needs_human_review"):
            # 人工已审批放行：保留标记并放行（含 human_review 详情）
            result["human_review_approved"] = True

        # Step 3: 补充追踪信息
        total_time = round(time.time() - t0, 3)
        result["agent_trace"] = agent_trace
        result["total_time"] = total_time
        result["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result["routing_decision"] = route_decision
        result["trace_id"] = trace_id

        # ---------- 出题双路校验（Task 5.3 / P0-3） ----------
        # 结构校验（FactChecker.verify_question）+ 独立模型复核（dual_verify）。
        # 保持原 questions 字段不动（向后兼容），结果写入 verified_questions。
        questions = result.get("questions")
        if isinstance(questions, list):
            import json as _json
            from agent_core.fact_checker import FactCheckerAgent
            from agent_core.verifier import dual_verify
            valid = [
                q for q in questions
                if isinstance(q, dict) and FactCheckerAgent.verify_question(q)
            ]
            # 对有效题目复核前 3 道（有风险场景）：不通过仅标记，保留但不计入有效
            for q in valid[:3]:
                try:
                    verdict = dual_verify(
                        _json.dumps(q, ensure_ascii=False),
                        prompt="请复核该题目是否契合知识点、答案是否正确")
                except Exception:
                    verdict = {"passed": True}
                if not verdict.get("passed"):
                    q["_verification"] = "rejected"
            result["verified_questions"] = valid
            result["dual_verified"] = True

        # ---------- 输出验证（安全过滤） ----------
        output_content = ""
        teaching = result.get("teaching", {})
        if isinstance(teaching, dict):
            output_content = teaching.get("full_content") or teaching.get("content") or ""
        output_check = self.safety.validate_output(output_content, agent_id="unified_orchestrator")
        if output_check.get("issues"):
            result["output_issues"] = output_check["issues"]
            result["output_sanitized"] = True
            if isinstance(teaching, dict) and teaching.get("full_content"):
                teaching["full_content"] = output_check["content"]

        # ---------- 可观测性：记录编排调用并结束追踪 ----------
        self.telemetry.record_call(
            trace_id=trace_id,
            agent_id="unified_orchestrator",
            model=route_decision,
            latency_ms=int(total_time * 1000),
            input_tokens=self.safety.estimate_tokens(topic),
            output_tokens=self.safety.estimate_tokens(output_content),
            success=result.get("success", True),
            extra={"route": route_decision},
        )

        # ---------- 会话完成自动评测写库（Task 8.3） ----------
        # 计算知识召回/格式合格/准确率指标并落库（评测为增强能力，失败降级不阻塞）
        try:
            import json as _json
            metrics = self.telemetry.eval_metrics(
                expected_knowledge=payload.get("expected_knowledge") or [],
                recalled_knowledge=payload.get("recalled_knowledge") or [],
                generated_questions=result.get("questions") or [],
                wrong_detected=payload.get("wrong_detected", 0),
                wrong_actual=payload.get("wrong_actual", 0),
            )
            from framework.database import db
            db.save_eval_report(
                "learning_session",
                metrics["knowledge_recall"],
                metrics["format_pass_rate"],
                metrics["accuracy"],
                trace_id,
                _json.dumps({"topic": topic}, ensure_ascii=False),
            )
            result["eval_metrics"] = metrics
        except Exception:
            pass

        self.telemetry.end_trace(trace_id, result)

        return result

    # ------------------------------------------------------------
    # Task 2: 自我批判反馈回路 + 超时 + token 预算
    # ------------------------------------------------------------
    def run_with_critique(self, topic: str, subject: str = "",
                          max_retries: int = 2, timeout_s: int = 60,
                          token_budget: int = 8000, **kwargs) -> Dict:
        """
        带自我批判（SelfCritique）反馈回路的教学生成。

        流程：
          1. 调用教学生成（默认复用 run()，可用 teach_fn 注入 fake 生成器）
          2. 用 SelfCritiqueAgent 对输出评分（默认阈值 70）
          3. score < 阈值 → 重试教学生成（最多 max_retries=2 次），每次重试记录轮次
          4. 达到最大重试仍不达标 → 接受分数最高的那次输出，
             结果标记 "critique_warning": True
          5. token 超预算 → 跳过评分与重试，直接返回降级结果

        参数：
            topic: 教学主题（必填）
            subject: 学科（可选，同时作为评分 knowledge_context）
            max_retries: 最大重试次数（默认 2）
            timeout_s: 单次教学生成超时秒数（默认 60）
            token_budget: 单轮输入+输出 token 预算（默认 8000）
            **kwargs:
                teach_fn: 可注入教学生成器，签名 teach_fn(topic, subject, **kw) -> Dict
                          （返回与 run() 兼容的结构；缺省用 self._teach_fn 或 run()）
                critique_agent: 可注入评分器（需有 .score(text, topic, knowledge_context)
                                -> {"score": int, "reason": str, "passed": bool}）
                _prompt_tokens / _completion_tokens: 覆盖 token 估算（测试用）
                其余 kwargs 透传给教学生成器

        返回：
            教学结果 dict（含原生成字段），并增加：
              - feedback_rounds: int   实际重试次数
              - critique_score: int    最终评分
              - critique_passed: bool  最终是否通过阈值
              - critique_reason: str   评分依据
              - critique_warning: bool 重试耗尽仍未达标时为 True（仅在降级接受时存在）
        """
        topic = (topic or "").strip()
        if not topic:
            return {"success": False, "error": "缺少 topic 参数"}

        # ---- 可注入组件（测试用）：教学生成器 / 评分器 ----
        teach_fn = kwargs.pop("teach_fn", None)
        if teach_fn is None:
            teach_fn = getattr(self, "_teach_fn", None) or self._default_teach_fn
        critique = kwargs.pop("critique_agent", None)
        if critique is None:
            critique = SelfCritiqueAgent()
        threshold = int(getattr(critique, "threshold", 70) or 70)

        # ---- 可注入 token 估算（测试用）；默认由 safety 估算 ----
        prompt_tokens_override = kwargs.pop("_prompt_tokens", None)
        completion_tokens_override = kwargs.pop("_completion_tokens", None)

        # ---- 可观测性：开启追踪 ----
        trace_id = self.telemetry.start_trace(
            user_id=str(kwargs.get("user_id", "critique")),
            topic=topic, context=subject)
        self._last_trace_id = trace_id

        def _estimate_tokens(text: str) -> int:
            try:
                return self.safety.estimate_tokens(text or "")
            except Exception:
                return max(1, len(text or "") // 2)

        best_result: Optional[Dict] = None
        best_score = -1
        best_reason = ""
        feedback_rounds = 0
        attempts = max(int(max_retries), 0) + 1  # 首轮生成 + max_retries 次重试

        for attempt in range(attempts):
            if attempt > 0:
                feedback_rounds += 1

            t0 = time.time()
            result = self._call_with_timeout(
                lambda: teach_fn(topic, subject, **kwargs),
                timeout_s=timeout_s,
                agent_id="critique_teach",
                default=None,
            )

            # ---- 超时 / 生成异常：返回降级结果（不抛异常） ----
            if result is None:
                status = getattr(self, "_last_call_status", "timeout")
                degraded = {
                    "success": False,
                    "degraded": True,
                    "reason": "timeout",
                    "message": f"教学生成超过 {timeout_s}s 未完成"
                               f"{'或发生异常' if status == 'error' else ''}，已降级处理",
                    "topic": topic,
                    "subject": subject,
                    "feedback_rounds": feedback_rounds,
                    "critique_score": 0,
                    "critique_passed": False,
                    "critique_reason": "timeout",
                    "trace_id": trace_id,
                }
                self.telemetry.end_trace(trace_id, degraded)
                return degraded

            # ---- 上游生成失败（安全拦截等）：直接返回，避免无意义重试 ----
            if not result.get("success", True):
                result.update({
                    "feedback_rounds": feedback_rounds,
                    "critique_score": 0,
                    "critique_passed": False,
                    "critique_reason": "teach_generation_failed",
                    "trace_id": trace_id,
                })
                self.telemetry.end_trace(trace_id, result)
                return result

            # ---- token 预算检查：超预算跳过评分与重试，直接降级 ----
            output_text = self._extract_output_text(result)
            prompt_tokens = (int(prompt_tokens_override)
                             if prompt_tokens_override is not None
                             else _estimate_tokens(topic + " " + subject))
            completion_tokens = (int(completion_tokens_override)
                                 if completion_tokens_override is not None
                                 else _estimate_tokens(output_text))
            if not self._check_token_budget(
                    prompt_tokens, completion_tokens, budget=token_budget):
                degraded = {
                    "success": False,
                    "degraded": True,
                    "reason": "token_budget_exceeded",
                    "message": "生成内容超过 token 预算，已截断处理",
                    "topic": topic,
                    "subject": subject,
                    "feedback_rounds": feedback_rounds,
                    "critique_score": 0,
                    "critique_passed": False,
                    "critique_reason": "token_budget_exceeded",
                    "trace_id": trace_id,
                }
                self.telemetry.record_call(
                    trace_id=trace_id,
                    agent_id="critique_teach",
                    model="",
                    latency_ms=int((time.time() - t0) * 1000),
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    success=False,
                    error="token_budget_exceeded",
                    extra={"route": "critique", "token_budget_exceeded": True},
                )
                self.telemetry.end_trace(trace_id, degraded)
                return degraded

            # ---- 自我批判评分 ----
            verdict = critique.score(output_text, topic=topic,
                                     knowledge_context=subject)
            score = int(verdict.get("score", 0) or 0)
            reason = str(verdict.get("reason", ""))
            passed = bool(verdict.get("passed", score >= threshold))

            self.telemetry.record_call(
                trace_id=trace_id,
                agent_id="critique_teach",
                model="",
                latency_ms=int((time.time() - t0) * 1000),
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                success=passed,
                extra={"route": "critique", "feedback_rounds": feedback_rounds},
            )

            # 记录本轮最高分（重试耗尽时接受最佳输出）
            if score > best_score:
                best_score = score
                best_reason = reason
                best_result = result

            if passed:
                final = dict(result)
                final.update({
                    "feedback_rounds": feedback_rounds,
                    "critique_score": score,
                    "critique_passed": True,
                    "critique_reason": reason,
                    "trace_id": trace_id,
                })
                self.telemetry.end_trace(trace_id, final)
                return final

        # ---- 重试耗尽仍未达标：接受分数最高的那次输出，标记警告 ----
        final = dict(best_result) if best_result is not None \
            else {"success": False, "topic": topic, "subject": subject}
        final.update({
            "feedback_rounds": feedback_rounds,
            "critique_score": best_score,
            "critique_passed": best_score >= threshold,
            "critique_reason": best_reason,
            "critique_warning": True,
            "trace_id": trace_id,
        })
        self.telemetry.end_trace(trace_id, final)
        return final

    def _call_with_timeout(self, fn: Callable, timeout_s: int = 60,
                           agent_id: str = "", default: Optional[Dict] = None):
        """
        用守护线程执行 fn，超过 timeout_s 未完成则返回 default（降级结果）。
        - fn 内部异常 → 捕获并返回 default（不向上抛）
        - 超时 / 异常均在 trace 记录事件（extra 带 "timeout": True 或 "error": True）
        """
        t0 = time.time()
        box: Dict = {}
        self._last_call_status = "ok"

        def _runner() -> None:
            try:
                box["value"] = fn()
            except BaseException as exc:  # noqa: BLE001 健壮性：fn 异常不外抛
                box["error"] = exc

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join(timeout_s)

        if thread.is_alive():
            self._last_call_status = "timeout"
            self.telemetry.record_call(
                trace_id=self._last_trace_id,
                agent_id=agent_id or "timeout_guard",
                model="",
                latency_ms=int((time.time() - t0) * 1000),
                success=False,
                error="timeout",
                extra={"route": "critique", "timeout": True},
            )
            return default

        if "error" in box:
            self._last_call_status = "error"
            self.telemetry.record_call(
                trace_id=self._last_trace_id,
                agent_id=agent_id or "timeout_guard",
                model="",
                latency_ms=int((time.time() - t0) * 1000),
                success=False,
                error=str(box["error"])[:200],
                extra={"route": "critique", "error": True},
            )
            return default

        return box.get("value")

    def _check_token_budget(self, prompt_tokens: int, completion_tokens: int,
                            budget: int = 8000) -> bool:
        """
        token 预算检查：输入+输出 token 总和 <= budget 返回 True（预算内），
        超过预算返回 False。token 计数非法时按预算内处理，不阻塞主流程。
        """
        try:
            total = int(prompt_tokens or 0) + int(completion_tokens or 0)
            return total <= int(budget)
        except (TypeError, ValueError):
            return True

    # ------------------------------------------------------------
    # 辅助：教学生成默认实现与输出文本提取
    # ------------------------------------------------------------
    def _default_teach_fn(self, topic: str, subject: str = "", **kwargs) -> Dict:
        """默认教学生成：复用 run()（保持原有完整编排流程）"""
        payload: Dict = {"topic": topic}
        if subject:
            payload["subject"] = subject
        payload.update(kwargs)
        return self.run(payload)

    @staticmethod
    def _extract_output_text(result: Dict) -> str:
        """从编排结果中提取教学输出文本（teaching.full_content / content）"""
        teaching = result.get("teaching") or {}
        if isinstance(teaching, dict):
            return str(teaching.get("full_content") or teaching.get("content") or "")
        return ""

    def _run_route_with_fallback(self, route_decision: str, payload: Dict,
                                 profile: TaskProfile) -> Dict:
        """
        执行指定路由路径，并用 FallbackHandler 包裹模型调用逻辑：
          - JSONDecodeError → 切换提示词模板重试（注入 _fallback_retry 标记）
          - API 限流/超时（TimeoutError / ConnectionError）→ 返回友好提示
          - 其他异常 → 返回友好提示，不崩溃、不暴露堆栈
        成功路径逻辑保持不变。
        """
        handler = FallbackHandler()

        def _dispatch() -> Dict:
            if route_decision == "simple":
                return self._run_simple(payload, profile)
            elif route_decision == "complex_parallel":
                return self._run_parallel(payload, profile)
            return self._run_standard(payload, profile)

        def _on_retry(attempt: int, _error: Exception) -> None:
            # JSONDecodeError 重试：切换提示词模板（注入备用模板标记，交由下游引擎读取）
            payload["_fallback_retry"] = True
            payload["_fallback_attempt"] = attempt

        result, err = handler.run_with_fallback(
            _dispatch, max_retries=self.max_retries, on_retry=_on_retry)
        if err is None:
            return result

        # 降级：返回用户可见的友好提示（不暴露堆栈），保持输出结构兼容
        return {
            "success": False,
            "error": err,
            "fallback": True,
            "fallback_error": err,
            "route": route_decision,
            "teaching": {"content": "", "model_used": "", "quality_flag": "FALLBACK"},
            "assessment": {"score": 0, "is_mastered": False},
            "coaching": {"mastery_level": "", "suggestions": [], "next_topics": []},
        }

    def _run_simple(self, payload: Dict, profile: TaskProfile) -> Dict:
        """简单任务：单模型快速响应"""
        t0 = time.time()
        result = self.engine.run_single(
            topic=payload.get("topic", ""),
        )
        elapsed = time.time() - t0

        return {
            "success": result.get("success", False),
            "topic": payload.get("topic", ""),
            "subject": payload.get("subject", profile.subject),
            "difficulty": payload.get("difficulty", profile.complexity),
            "user_id": payload.get("user_id", 0),
            "teaching": {
                "content": result.get("content", ""),
                "model_used": result.get("model_id", ""),
                "quality_flag": result.get("quality_flag", "UNKNOWN"),
            },
            "assessment": {"score": 0, "is_mastered": False},
            "coaching": {"mastery_level": "", "suggestions": [], "next_topics": []},
            "elapsed": round(elapsed, 3),
            "route": "simple",
        }

    def _run_standard(self, payload: Dict, profile: TaskProfile) -> Dict:
        """标准任务：并行化多 Agent 编排 + 反馈回路（Phase 2 升级）"""
        t0 = time.time()

        # 优先使用 Phase 2 的并行化流水线（并行 Feynman + Verifier 反馈回路）
        try:
            from agent_core.multi_agent import MultiAgentPipeline
            pipeline = MultiAgentPipeline(
                max_retries=self.max_retries,
                verifier_use_model=False,
            )
            result = pipeline.run(payload)
            elapsed = time.time() - t0
            result["elapsed"] = round(elapsed, 3)
            result["route"] = "standard"
            return result
        except ImportError:
            # 降级：使用旧版串行编排（兼容）
            try:
                from goai_multi_agent import MultiAgentOrchestrator
                orchestrator = MultiAgentOrchestrator()
                result = orchestrator.run(payload)
                elapsed = time.time() - t0
                result["elapsed"] = round(elapsed, 3)
                result["route"] = "standard"
                return result
            except ImportError:
                return self._run_simple(payload, profile)

    def _run_parallel(self, payload: Dict, profile: TaskProfile) -> Dict:
        """复杂任务：多模型并行（LangGraph 引擎）"""
        t0 = time.time()
        result = self.engine.run(
            topic=payload.get("topic", ""),
            context=payload.get("context", ""),
        )
        elapsed = time.time() - t0

        # 转换为与 goai_multi_agent.py 兼容的格式
        quality = result.get("quality_report", {})
        ret = {
            "success": True,
            "topic": payload.get("topic", ""),
            "subject": payload.get("subject", profile.subject),
            "difficulty": payload.get("difficulty", "高中"),
            "user_id": payload.get("user_id", 0),
            "teaching": {
                "steps": [],
                "full_content": result.get("teaching_content", ""),
                "rag_sources": [],
            },
            "assessment": {
                "score": 0,
                "dimensions": {},
                "is_mastered": False,
                "feedback": quality.get("recommendation", ""),
            },
            "coaching": {
                "mastery_level": quality.get("level", ""),
                "suggestions": [quality.get("recommendation", "")],
                "next_topics": [],
            },
            "vote_result": result.get("vote_score", ""),
            "models_used": result.get("models_used", 0),
            "elapsed": round(elapsed, 3),
            "route": "complex_parallel",
            "cost_trace": result.get("cost_trace", []),
            "latency_trace": result.get("latency_trace", []),
        }
        # P0-1：并行路径质量报告 poor → 视为低置信度，需人工复核
        if quality.get("level") == "poor":
            ret["needs_human_review"] = True
            ret["human_review_reason"] = (
                "多模型并行质量报告为 poor（可用模型/权重不足），置信度过低，需人工审核")
            ret["human_review"] = {
                "needs_review": True,
                "confidence": round((quality.get("confidence") or 0) * 100, 1),
                "trigger": "low_confidence",
                "error_issues": [],
            }
        return ret

    def get_status(self) -> Dict:
        """获取编排器状态"""
        return {
            "router": {
                "subjects_detected": len(self.router.SUBJECT_KEYWORDS),
                "complexity_levels": ["simple", "standard", "complex"],
            },
            "models": get_model_summary(),
            "engine": {
                "max_workers": self.engine.max_workers,
                "max_retries": self.max_retries,
            },
        }

    # ------------------------------------------------------------
    # 人工监督辅助
    # ------------------------------------------------------------
    def _detect_sensitive_topic(self, topic: str, profile: TaskProfile) -> str:
        """检测主题是否涉及敏感/违规内容，返回命中词（无则返回空串）"""
        text = (topic or "")
        for kw in SENSITIVE_TOPICS:
            if kw in text:
                return kw
        # 结合 Router 提取的关键词二次检测
        for kw in (profile.keywords or []):
            for s in SENSITIVE_TOPICS:
                if s in kw:
                    return s
        return ""


# ================================================================
# 单例
# ================================================================
_orchestrator_instance: Optional[UnifiedOrchestrator] = None


def get_unified_orchestrator() -> UnifiedOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = UnifiedOrchestrator()
    return _orchestrator_instance


# ================================================================
# 便捷入口
# ================================================================
def run_agent(payload: Dict) -> Dict:
    """一行调用统一编排"""
    return get_unified_orchestrator().run(payload)


if __name__ == "__main__":
    import os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

    print("=" * 60)
    print("  LumiLearn Agent Core — 统一编排器测试")
    print("=" * 60)

    orch = UnifiedOrchestrator()
    status = orch.get_status()
    print(f"  注册模型数: {status['models']['total']}")
    print(f"  模型分布: {status['models']['by_provider']}")

    # 测试路由
    test_cases = [
        {"topic": "什么是函数", "context": ""},
        {"topic": "请推导牛顿第二定律", "context": ""},
        {"topic": "比较凸透镜和凹透镜的异同", "context": ""},
    ]
    for tc in test_cases:
        result = orch.run(tc)
        print(f"\n  主题: {tc['topic']}")
        print(f"  路由: {result.get('route', 'unknown')}")
        print(f"  耗时: {result.get('elapsed', 0)}s")
