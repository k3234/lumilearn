# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — 可观测性基础设施（Phase 3）

实现 Agent 调用链全量追踪，满足 EU AI Act Article 12（日志记录）要求：

  - Trace ID：每次用户请求生成唯一追踪 ID，贯穿所有 Agent 调用
  - record_call()：记录每次 Agent 调用（agent_id/模型/耗时/成本/结果）
  - trace_cost()：成本追踪（token 估算 + 模型成本）
  - audit_log()：审计日志（落库 system_logs + 内存缓冲）
  - human_in_loop()：人工中断标记（EU AI Act Article 14）

设计：
  - 内存环形缓冲（最近 N 条）+ 持久化到 system_logs 表
  - 线程安全，单例模式
  - 支持按 trace_id / agent_id / user_id 检索
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger("lumilearn.agent.telemetry")

# 模型单价（元/千token，粗略估算，用于成本追踪）
MODEL_COST_PER_1K = {
    "qwen2.5:7b": 0.001,
    "deepseek-r1:1.5b": 0.0005,
    "lumilearn-remote": 0.002,
    "Doubao-Seed-2.0-Code": 0.008,
    "GLM-5": 0.01,
    "Kimi-K2.5": 0.012,
    "MiniMax-M2.5": 0.009,
    "Doubao-Seed-Code": 0.008,
}
DEFAULT_COST = 0.005


class AgentTelemetry:
    """
    Agent 调用链追踪。

    用法：
        tele = get_telemetry()
        trace_id = tele.start_trace(user_id, topic)
        tele.record_call(trace_id, agent_id="feynman", model="qwen2.5:7b",
                         latency_ms=1200, input_tokens=200, output_tokens=800,
                         success=True)
        tele.end_trace(trace_id)
    """

    def __init__(self, buffer_size: int = 5000):
        # 使用可重入锁：request_interrupt / resolve_interrupt 在持锁时调用
        # audit_log，get_stats 在持锁时调用 get_pending_interrupts，
        # 普通 Lock 会导致嵌套加锁死锁。
        self._lock = threading.RLock()
        self._buffer: Deque[Dict] = deque(maxlen=buffer_size)
        self._active_traces: Dict[str, Dict] = {}
        self._interrupts: Dict[str, Dict] = {}  # human-in-the-loop 标记
        self._trace_counter = 0
        self.stats = {
            "total_calls": 0,
            "total_traces": 0,
            "total_cost": 0.0,
            "error_count": 0,
            "interrupted": 0,
        }

    # ============================================================
    # Trace 生命周期
    # ============================================================
    def start_trace(self, user_id: str = "anonymous",
                    topic: str = "", context: str = "") -> str:
        """开启一条调用链追踪，返回 trace_id"""
        trace_id = f"trace_{uuid.uuid4().hex[:10]}"
        with self._lock:
            self._trace_counter += 1
            self._active_traces[trace_id] = {
                "trace_id": trace_id,
                "user_id": user_id,
                "topic": topic,
                "context": context,
                "started_at": datetime.now().isoformat(),
                "calls": [],
                "interrupted": False,
                "interrupt_reason": "",
            }
            self.stats["total_traces"] += 1
        return trace_id

    def end_trace(self, trace_id: str, result: Dict = None) -> Optional[Dict]:
        """结束一条追踪，返回汇总"""
        with self._lock:
            trace = self._active_traces.pop(trace_id, None)
            if not trace:
                return None
            calls = trace["calls"]
            total_latency = sum(c.get("latency_ms", 0) for c in calls)
            total_cost = sum(c.get("cost", 0) for c in calls)
            errors = sum(1 for c in calls if not c.get("success", True))
            trace["ended_at"] = datetime.now().isoformat()
            trace["summary"] = {
                "call_count": len(calls),
                "total_latency_ms": total_latency,
                "total_cost": round(total_cost, 6),
                "error_count": errors,
            }
            if result:
                trace["result_summary"] = {
                    k: str(v)[:200] for k, v in result.items()
                    if k in ("topic", "success", "verified", "route",
                             "feedback_rounds")
                }
            self.stats["total_cost"] += total_cost
            self.stats["error_count"] += errors
            self._buffer.append(trace)

        # 持久化调用链汇总（一条 status=completed 记录，detail_json 存 summary）
        # 落库失败不影响主流程
        if trace.get("summary"):
            try:
                from framework.database import db
                db.save_agent_trace(
                    trace_id=trace_id,
                    user_id=trace.get("user_id", ""),
                    topic=trace.get("topic", ""),
                    agent_id="__trace_summary__",
                    model="",
                    latency_ms=trace["summary"].get("total_latency_ms", 0),
                    input_tokens=0,
                    output_tokens=0,
                    success=trace["summary"].get("error_count", 0) == 0,
                    error="",
                    status="completed",
                    detail_json=json.dumps(
                        {"summary": trace["summary"],
                         "result_summary": trace.get("result_summary", {})},
                        ensure_ascii=False),
                )
            except Exception as e:  # noqa: BLE001 - 落库失败仅告警
                logger.warning(f"Trace 汇总落库失败: {e}")
        return trace

    # ============================================================
    # 调用记录
    # ============================================================
    def record_call(
        self,
        trace_id: str = "",
        agent_id: str = "",
        model: str = "",
        latency_ms: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        success: bool = True,
        error: str = "",
        extra: Dict = None,
    ) -> Dict:
        """
        记录一次 Agent 调用。

        参数：
            trace_id: 所属追踪链（空则自动生成）
            agent_id: Agent 标识
            model: 使用的模型
            latency_ms: 耗时
            input_tokens / output_tokens: token 计数
            success: 是否成功
            error: 错误信息
            extra: 附加字段（如 route、feedback_rounds）

        返回：
            调用记录（含计算的 cost）
        """
        cost = self._calc_cost(model, input_tokens, output_tokens)
        record = {
            "trace_id": trace_id,
            "agent_id": agent_id,
            "model": model,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "success": success,
            "error": error[:200] if error else "",
            "timestamp": datetime.now().isoformat(),
        }
        if extra:
            record["extra"] = {k: str(v)[:100] for k, v in extra.items()}

        with self._lock:
            self.stats["total_calls"] += 1
            if not success:
                self.stats["error_count"] += 1
            self._buffer.append(record)
            if trace_id and trace_id in self._active_traces:
                self._active_traces[trace_id]["calls"].append(record)

        # 审计日志（持久化）
        if not success or error:
            self.audit_log(
                level="warning" if not success else "info",
                message=f"Agent {agent_id} 调用{'失败' if not success else '完成'}",
                detail=f"trace={trace_id} model={model} latency={latency_ms}ms "
                       f"error={error[:100] if error else '无'}",
            )

        # 持久化到 agent_traces（延迟导入避免循环依赖；落库失败不影响主流程）
        try:
            from framework.database import db
            db.save_agent_trace(
                trace_id=trace_id,
                agent_id=agent_id,
                model=model,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                success=success,
                error=error[:200] if error else "",
            )
        except Exception as e:  # noqa: BLE001 - 落库失败仅告警
            logger.warning(f"Agent 调用追踪落库失败: {e}")
        return record

    def measure(self, trace_id: str = "", agent_id: str = ""):
        """上下文管理器：自动测量耗时并记录"""
        return _TimedCall(self, trace_id, agent_id)

    # ============================================================
    # 成本追踪
    # ============================================================
    def _calc_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """估算调用成本（元）"""
        price = MODEL_COST_PER_1K.get(model, DEFAULT_COST)
        return round((input_tokens + output_tokens) * price / 1000, 6)

    def trace_cost(self, model: str, input_tokens: int = 0,
                   output_tokens: int = 0) -> Dict:
        """单次成本追踪"""
        cost = self._calc_cost(model, input_tokens, output_tokens)
        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost,
        }

    def get_cost_summary(self, agent_id: str = "") -> Dict:
        """成本汇总"""
        with self._lock:
            if agent_id:
                calls = [c for c in self._buffer
                         if c.get("agent_id") == agent_id]
            else:
                # 仅统计真实调用记录（排除 audit 与 end_trace 追加的 trace 汇总）
                calls = [c for c in self._buffer
                         if c.get("type") != "audit" and "cost" in c]
            total_cost = sum(c.get("cost", 0) for c in calls)
            total_tokens = sum(
                c.get("input_tokens", 0) + c.get("output_tokens", 0)
                for c in calls)
            by_model: Dict[str, Dict] = {}
            for c in calls:
                m = c.get("model", "unknown")
                by_model.setdefault(m, {"calls": 0, "cost": 0.0})
                by_model[m]["calls"] += 1
                by_model[m]["cost"] += c.get("cost", 0)
            return {
                "total_calls": len(calls),
                "total_cost": round(total_cost, 6),
                "total_tokens": total_tokens,
                "by_model": by_model,
            }

    # ============================================================
    # 审计日志（EU AI Act Article 12）
    # ============================================================
    def audit_log(self, level: str = "info", message: str = "",
                  detail: str = "", module: str = "agent_core") -> int:
        """写审计日志（持久化到 system_logs + 内存缓冲）"""
        level = level if level in ("debug", "info", "warning", "error") else "info"
        try:
            from framework.database import db
            row_id = db.add_system_log(level, module, message, detail)
            with self._lock:
                self._buffer.append({
                    "type": "audit",
                    "level": level,
                    "module": module,
                    "message": message,
                    "detail": detail,
                    "timestamp": datetime.now().isoformat(),
                })
            return row_id
        except Exception as e:
            logger.warning(f"审计日志写入失败: {e}")
            return 0

    # ============================================================
    # 人工中断（EU AI Act Article 14 human-in-the-loop）
    # ============================================================
    def request_interrupt(self, trace_id: str, reason: str,
                          node: str = "") -> Dict:
        """
        请求人工中断：在关键节点标记需要人工审批。

        参数：
            trace_id: 追踪 ID
            reason: 中断原因
            node: 中断节点（如 verifier）

        返回：
            {"interrupted": bool, "trace_id": str}
        """
        with self._lock:
            self.stats["interrupted"] += 1
            self._interrupts[trace_id] = {
                "trace_id": trace_id,
                "reason": reason,
                "node": node,
                "requested_at": datetime.now().isoformat(),
                "status": "pending",  # pending / approved / rejected
                "reviewer": "",
                "reviewed_at": "",
            }
            if trace_id in self._active_traces:
                self._active_traces[trace_id]["interrupted"] = True
                self._active_traces[trace_id]["interrupt_reason"] = reason
            self.audit_log(
                level="warning",
                message=f"人工中断请求: trace={trace_id} node={node}",
                detail=reason,
            )
            return {"interrupted": True, "trace_id": trace_id}

    def resolve_interrupt(self, trace_id: str, decision: str,
                          reviewer: str = "admin") -> Dict:
        """
        人工审批中断：approved（放行）/ rejected（拒绝/终止）

        参数：
            trace_id: 追踪 ID
            decision: approved / rejected
            reviewer: 审批人
        """
        with self._lock:
            interrupt = self._interrupts.get(trace_id)
            if not interrupt:
                return {"interrupted": False, "error": "中断请求不存在"}
            interrupt["status"] = decision
            interrupt["reviewer"] = reviewer
            interrupt["reviewed_at"] = datetime.now().isoformat()
            self.audit_log(
                level="info",
                message=f"人工审批: trace={trace_id} → {decision} by {reviewer}",
                detail=interrupt["reason"],
            )
            return {"interrupted": True, "trace_id": trace_id,
                    "decision": decision}

    def get_pending_interrupts(self) -> List[Dict]:
        """获取待审批的中断请求"""
        with self._lock:
            return [i for i in self._interrupts.values()
                    if i["status"] == "pending"]

    def get_all_interrupts(self) -> List[Dict]:
        """获取全部中断请求（含已审批，按请求时间倒序）"""
        with self._lock:
            return sorted(
                self._interrupts.values(),
                key=lambda i: i.get("requested_at", ""),
                reverse=True)

    # ============================================================
    # 自动评测指标（Trace + 自动评测闭环）
    # ============================================================
    def eval_metrics(self, expected_knowledge: list, recalled_knowledge: list,
                     generated_questions: list, wrong_detected: int,
                     wrong_actual: int) -> Dict:
        """
        计算一次自动评测的量化指标。

        参数：
            expected_knowledge: 期望覆盖的知识点列表
            recalled_knowledge: 实际召回的知识点列表
            generated_questions: 生成的题目列表（每题为 dict）
            wrong_detected: 系统检测出的错题数
            wrong_actual: 实际错题数（人工/标准答案核对）

        返回：
            {"knowledge_recall": float, "format_pass_rate": float,
             "accuracy": float}
        """
        # 知识召回率：召回知识点 ∩ 期望知识点 / 期望知识点（期望为空视为满分）
        expected = set(expected_knowledge)
        recalled = set(recalled_knowledge)
        if len(expected) == 0:
            knowledge_recall = 1.0
        else:
            knowledge_recall = len(expected & recalled) / len(expected)

        # 格式合格率：同时含 question/answer/options 字段的题目占比
        # （生成题目为空视为满分，与 expected 为空的处理保持一致）
        if not generated_questions:
            format_pass_rate = 1.0
        else:
            passed = sum(
                1 for q in generated_questions
                if isinstance(q, dict) and all(
                    k in q for k in ("question", "answer", "options")))
            format_pass_rate = passed / len(generated_questions)

        # 检测准确率：1 - |检测数 - 实际数| / max(实际数, 1)
        accuracy = 1 - abs(wrong_detected - wrong_actual) / max(wrong_actual, 1)

        return {
            "knowledge_recall": float(knowledge_recall),
            "format_pass_rate": float(format_pass_rate),
            "accuracy": float(accuracy),
        }

    # ============================================================
    # 查询
    # ============================================================
    def get_trace(self, trace_id: str) -> Optional[Dict]:
        """按 trace_id 查询完整调用链"""
        with self._lock:
            if trace_id in self._active_traces:
                return self._active_traces[trace_id]
            for rec in reversed(self._buffer):
                if rec.get("trace_id") == trace_id:
                    return rec
        return None

    def get_calls(self, agent_id: str = "", limit: int = 100) -> List[Dict]:
        """查询调用记录"""
        with self._lock:
            calls = [c for c in self._buffer
                     if c.get("type") != "audit" and c.get("agent_id")]
            if agent_id:
                calls = [c for c in calls if c.get("agent_id") == agent_id]
            return list(reversed(calls))[:limit]

    def get_stats(self) -> Dict:
        """全局统计"""
        with self._lock:
            return {
                **self.stats,
                "buffer_size": len(self._buffer),
                "active_traces": len(self._active_traces),
                "pending_interrupts": len(self.get_pending_interrupts()),
            }


class _TimedCall:
    """耗时测量上下文管理器"""

    def __init__(self, telemetry: AgentTelemetry, trace_id: str, agent_id: str):
        self.telemetry = telemetry
        self.trace_id = trace_id
        self.agent_id = agent_id
        self.t0 = 0.0

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        latency = int((time.time() - self.t0) * 1000)
        self.telemetry.record_call(
            trace_id=self.trace_id,
            agent_id=self.agent_id,
            latency_ms=latency,
            success=exc_type is None,
            error=str(exc_val) if exc_val else "",
        )
        return False


# ================================================================
# 单例
# ================================================================
_telemetry: Optional[AgentTelemetry] = None


def get_telemetry(**kwargs) -> AgentTelemetry:
    """获取可观测性单例"""
    global _telemetry
    if _telemetry is None:
        _telemetry = AgentTelemetry(**kwargs)
    return _telemetry


def reset_telemetry():
    """重置可观测性（测试用）"""
    global _telemetry
    _telemetry = None


if __name__ == "__main__":
    tele = get_telemetry()
    print("=== Agent 可观测性测试 ===")

    # 1. 完整调用链
    tid = tele.start_trace("user1", "函数的单调性")
    with tele.measure(tid, "feynman"):
        pass  # 模拟耗时
    tele.record_call(tid, "feynman", "qwen2.5:7b",
                     latency_ms=1200, input_tokens=300, output_tokens=900,
                     success=True)
    tele.record_call(tid, "verifier", "qwen2.5:7b",
                     latency_ms=200, input_tokens=100, output_tokens=50,
                     success=True)
    trace = tele.end_trace(tid)
    print(f"Trace 汇总: calls={trace['summary']['call_count']} "
          f"cost={trace['summary']['total_cost']}")

    # 2. 人工中断
    tid2 = tele.start_trace("user2", "危险主题")
    tele.request_interrupt(tid2, "内容可能违规，需人工审核", node="verifier")
    pending = tele.get_pending_interrupts()
    print(f"待审批中断: {len(pending)} 条")
    tele.resolve_interrupt(tid2, "rejected", "teacher1")
    print(f"审批后状态: {tele._interrupts[tid2]['status']}")

    # 3. 成本汇总
    summary = tele.get_cost_summary()
    print(f"总成本: {summary['total_cost']} 元, 调用 {summary['total_calls']} 次")

    # 4. 审计日志
    tele.audit_log("info", "系统启动", "Phase 3 可观测性验证")
    print(f"全局统计: {tele.get_stats()}")
