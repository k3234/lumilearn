# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — LangGraph 风格图定义

实现 Router / Feynman / Score / Coach / Verifier 五节点的有向图，
支持条件边（反馈回路）与节点级追踪。

设计说明：
  - 零外部依赖：自实现轻量 StateGraph（不引入 langgraph 库），
    保持与现有 langgraph_engine.py 一致的"LangGraph 风格"实现。
  - 若未来需要接入官方 langgraph，只需替换本文件的 StateGraph 实现，
    节点函数签名（state -> state）保持兼容。

节点：
  router   : 任务路由（复用 RouterAgent）
  feynman  : 费曼教学（并行多模型）
  score    : 五维评分
  coach    : 学习建议
  verifier : 质量验证 + 反馈回路

条件边（反馈回路）：
  verifier ──passed──→ END
           └─failed──→ feynman（重新生成，受 max_retries 限制）
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Union

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.models import AgentState
from agent_core.router import RouterAgent, get_router_agent
from agent_core.multi_agent import MultiAgentPipeline, get_multi_agent_pipeline


# ================================================================
# 轻量 StateGraph 实现
# ================================================================
class Node:
    """图节点"""

    def __init__(self, name: str, func: Callable[[AgentState], Union[AgentState, Dict]]):
        self.name = name
        self.func = func


class StateGraph:
    """
    轻量 LangGraph 风格有向图。

    用法：
        g = StateGraph(AgentState)
        g.add_node("router", router_node)
        g.add_edge("router", "feynman")
        g.add_conditional_edges("verifier", router_condition, {...})
        graph = g.compile()
        result = graph.invoke(state)
    """

    def __init__(self, state_schema: Any = None):
        self.state_schema = state_schema or dict
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, str] = {}          # name -> next name
        self.conditional_edges: Dict[str, Dict] = {}  # name -> {condition_func, mapping}
        self.entry_point: Optional[str] = None

    def add_node(self, name: str, func: Callable) -> None:
        self.nodes[name] = Node(name, func)
        if self.entry_point is None:
            self.entry_point = name

    def add_edge(self, start: str, end: str) -> None:
        self.edges[start] = end

    def add_conditional_edges(
        self,
        start: str,
        condition_func: Callable[[AgentState], str],
        mapping: Dict[str, str],
    ) -> None:
        self.conditional_edges[start] = {
            "condition": condition_func,
            "mapping": mapping,
        }

    def set_entry_point(self, name: str) -> None:
        self.entry_point = name

    def compile(self) -> "CompiledGraph":
        return CompiledGraph(self)


class CompiledGraph:
    """编译后的可执行图"""

    def __init__(self, graph: StateGraph):
        self.graph = graph
        self.execution_path: List[str] = []

    def invoke(
        self,
        state: AgentState,
        max_steps: int = 20,
        stop_node: Optional[str] = None,
    ) -> AgentState:
        """
        执行图（含反馈回路）。

        参数：
            state: 初始状态
            max_steps: 最大执行步数（防止无限循环）
            stop_node: 到达该节点后结束（可选）

        返回：
            最终状态（含 agent_trace 追踪）
        """
        current = self.graph.entry_point
        if not current:
            return state

        state = dict(state)
        trace = state.setdefault("agent_trace", {})
        state.setdefault("retry_count", 0)
        state.setdefault("max_retries", 3)

        self.execution_path = []

        for step in range(max_steps):
            if current is None or current not in self.graph.nodes:
                break

            self.execution_path.append(current)
            node = self.graph.nodes[current]
            t0 = time.time()

            try:
                result = node.func(state)
                if isinstance(result, dict) and "agent_trace" in result:
                    result = result["agent_trace"]  # 兼容节点返回 trace
                elif isinstance(result, dict):
                    # 节点返回新状态 → 合并
                    state.update({k: v for k, v in result.items()})
            except Exception as e:
                trace[f"{current}"] = {
                    "status": "error", "error": str(e),
                    "elapsed": round(time.time() - t0, 3)}
                break

            # 记录节点追踪
            if current not in trace:
                trace[current] = {"status": "ok",
                                  "elapsed": round(time.time() - t0, 3)}

            # 检查 stop_node
            if stop_node and current == stop_node:
                break

            # 条件边优先
            if current in self.graph.conditional_edges:
                cond = self.graph.conditional_edges[current]
                try:
                    decision = cond["condition"](state)
                except Exception:
                    decision = "end"
                nxt = cond["mapping"].get(decision)
                if nxt is None:
                    # 无映射目标 → 视为 END
                    break
                # 反馈回路计数（verifier → feynman 重试）
                if nxt == "feynman":
                    state["retry_count"] = state.get("retry_count", 0) + 1
                    if state["retry_count"] > state.get("max_retries", 3):
                        trace["feedback"] = {
                            "status": "max_retries_exceeded",
                            "rounds": state["retry_count"]}
                        break
                current = nxt
                continue

            # 普通边
            nxt = self.graph.edges.get(current)
            if nxt is None:
                break
            current = nxt

        state["execution_path"] = self.execution_path
        return state


# ================================================================
# 节点函数
# ================================================================
def router_node(state: AgentState) -> AgentState:
    """Router: 分析任务复杂度，决定路由路径"""
    router = get_router_agent()
    topic = state.get("input_topic", "")
    context = state.get("input_context", "")
    route_result = router.route(topic, context)
    state["task_profile"] = route_result.get("profile", {})
    state["routing_decision"] = route_result.get("route", "standard")
    return state


def feynman_node(state: AgentState) -> AgentState:
    """Feynman: 并行多模型费曼教学"""
    pipeline = get_multi_agent_pipeline()
    topic = state.get("input_topic", "")
    payload = {
        "topic": topic,
        "subject": state.get("input_context", ""),
        "difficulty": "高中",
        "context": state.get("verifier_feedback", ""),
        "parallel": True,
    }
    result = pipeline.feynman.run_parallel(payload)
    if result.get("success"):
        state["teaching_steps"] = result.get("steps", [])
        state["teaching_content"] = result.get("full_content", "")
        state["rag_sources"] = result.get("rag_sources", [])
        state["feynman_stats"] = {
            "models_used": result.get("models_used", 0),
            "best_model": result.get("best_model", ""),
        }
    else:
        state["error"] = result.get("error", "费曼教学失败")
    return state


def score_node(state: AgentState) -> AgentState:
    """Score: 五维评分（无学生解释则跳过）"""
    student_explanation = state.get("student_explanation", "")
    if not student_explanation:
        state["score"] = 0
        state["is_mastered"] = False
        return state
    pipeline = get_multi_agent_pipeline()
    result = pipeline.score.run({
        "topic": state.get("input_topic", ""),
        "student_explanation": student_explanation,
        "user_id": state.get("user_id", 0),
    })
    if result.get("success"):
        state["score"] = result.get("score", 0)
        state["dimensions"] = result.get("dimensions", {})
        state["is_mastered"] = result.get("is_mastered", False)
        state["feedback"] = result.get("feedback", "")
    return state


def coach_node(state: AgentState) -> AgentState:
    """Coach: 学习建议"""
    pipeline = get_multi_agent_pipeline()
    result = pipeline.coach.run({
        "user_id": state.get("user_id", 0),
        "score": state.get("score", 0),
        "topic": state.get("input_topic", ""),
        "weak_topics": state.get("weak_topics", []),
    })
    if result.get("success"):
        state["mastery_level"] = result.get("mastery_level", "")
        state["suggestions"] = result.get("suggestions", [])
        state["next_topics"] = result.get("next_topics", [])
    return state


def verifier_node(state: AgentState) -> AgentState:
    """Verifier: 质量验证 + 反馈回路决策"""
    pipeline = get_multi_agent_pipeline()
    verify = pipeline.verifier.run({
        "topic": state.get("input_topic", ""),
        "teaching_content": state.get("teaching_content", ""),
        "steps": state.get("teaching_steps", []),
        "score": state.get("score"),
        "mastery_level": state.get("mastery_level", ""),
        "suggestions": state.get("suggestions", []),
    })
    state["verifier_result"] = verify
    state["verified"] = verify.get("passed", False)
    # 反馈内容注入下一轮费曼教学
    if not verify.get("passed", False) and verify.get("issues"):
        details = "; ".join(i.get("detail", "") for i in verify.get("issues", [])[:3])
        state["verifier_feedback"] = (
            f"上次验证反馈: {verify.get('reason', '')} {details}")
    return state


# ================================================================
# 条件函数
# ================================================================
def verifier_condition(state: AgentState) -> str:
    """Verifier 条件边：通过→END，未通过→feynman（反馈回路）"""
    return "end" if state.get("verified", False) else "feynman"


def router_condition(state: AgentState) -> str:
    """Router 条件边（预留）：simple→单模型（跳过验证），complex→完整流程"""
    decision = state.get("routing_decision", "standard")
    if decision == "simple":
        return "single"
    return "full"


# ================================================================
# 构建完整图
# ================================================================
def build_feedback_graph() -> CompiledGraph:
    """
    构建带反馈回路的完整执行图：

        router → feynman → score → coach → verifier
                                              │
                                    passed───→ END
                                    failed────→ feynman（反馈回路）
    """
    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("feynman", feynman_node)
    graph.add_node("score", score_node)
    graph.add_node("coach", coach_node)
    graph.add_node("verifier", verifier_node)

    graph.add_edge("router", "feynman")
    graph.add_edge("feynman", "score")
    graph.add_edge("score", "coach")
    graph.add_edge("coach", "verifier")

    # 反馈回路：verifier 失败 → feynman 重新生成
    graph.add_conditional_edges(
        "verifier",
        verifier_condition,
        {"end": "", "feynman": "feynman"},
    )

    return graph.compile()


# ================================================================
# 便捷入口
# ================================================================
_feedback_graph: Optional[CompiledGraph] = None


def get_feedback_graph() -> CompiledGraph:
    """获取带反馈回路的执行图单例"""
    global _feedback_graph
    if _feedback_graph is None:
        _feedback_graph = build_feedback_graph()
    return _feedback_graph


def run_graph(topic: str, context: str = "", student_explanation: str = "",
              max_retries: int = 3) -> Dict:
    """
    一行调用带反馈回路的图执行。

    参数：
        topic: 教学主题
        context: 补充上下文
        student_explanation: 学生解释（可选）
        max_retries: 最大反馈轮次

    返回：
        最终 AgentState（含 teaching/score/coach/verifier 全部结果）
    """
    graph = build_feedback_graph()
    state: AgentState = {
        "input_topic": topic,
        "input_context": context,
        "student_explanation": student_explanation,
        "max_retries": max_retries,
        "retry_count": 0,
    }
    return graph.invoke(state)


if __name__ == "__main__":
    print("=" * 60)
    print("  LumiLearn Agent Graph — Phase 2 测试")
    print("=" * 60)

    graph = get_feedback_graph()
    print("  节点:", list(graph.graph.nodes.keys()))
    print("  条件边:", list(graph.graph.conditional_edges.keys()))

    state = {
        "input_topic": "函数的单调性",
        "input_context": "高中数学",
        "student_explanation": "",
        "max_retries": 2,
        "retry_count": 0,
    }
    result = graph.invoke(state)
    print("  执行路径:", result.get("execution_path", []))
    print("  验证通过:", result.get("verified", False))
    print("  反馈轮次:", result.get("retry_count", 0))
    print("  教学内容长度:", len(result.get("teaching_content", "")))
    print("=" * 60)
