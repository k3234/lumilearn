# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — 统一数据模型

定义 Agent 系统共用的数据结构：
  - AgentState     : LangGraph 风格的有状态节点数据
  - ToolCall       : 工具调用记录
  - AgentResult    : Agent 执行结果
  - TaskProfile    : 任务画像（Router 使用）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict


# ================================================================
# 一、AgentState — LangGraph 风格状态
# ================================================================
class AgentState(TypedDict, total=False):
    """
    LangGraph 风格的统一状态，覆盖所有 Agent 节点的数据交换。

    字段说明：
      input_topic        : 用户输入的主题
      input_context      : 补充上下文
      task_profile       : Router 生成的任务画像
      routing_decision   : Router 的路由决策（simple / standard / complex）
      teaching_steps     : Feynman 五步教学内容
      teaching_content   : 合并后的完整讲解
      rag_sources        : RAG 检索来源
      score              : 五维评分总分
      dimensions         : 五维评分详情
      is_mastered        : 是否掌握
      feedback           : 综合评语
      mastery_level      : 掌握等级
      suggestions        : 学习建议列表
      next_topics        : 下一步推荐知识点
      model_responses    : 多模型并行调用结果 {model_id: {...}}
      multi_formats      : 多格式输出 {model_id: {format: content}}
      vote_result        : 投票聚合结果
      verifier_result    : Verifier Agent 验证结果
      verified           : 是否通过验证
      retry_count        : 当前重试次数
      max_retries        : 最大重试次数
      agent_trace        : 各 Agent 阶段状态追踪
      cost_trace         : 成本追踪记录
      latency_trace      : 延迟追踪记录
      final_output       : 最终输出
      error              : 错误信息（如有）
    """
    input_topic: str
    input_context: str
    task_profile: Dict[str, Any]
    routing_decision: str
    teaching_steps: List[Dict[str, Any]]
    teaching_content: str
    rag_sources: List[Dict[str, Any]]
    score: int
    dimensions: Dict[str, Dict[str, Any]]
    is_mastered: bool
    feedback: str
    mastery_level: str
    suggestions: List[str]
    next_topics: List[Dict[str, Any]]
    model_responses: Dict[str, Dict[str, Any]]
    multi_formats: Dict[str, Dict[str, str]]
    vote_result: Dict[str, Any]
    verifier_result: Dict[str, Any]
    verified: bool
    retry_count: int
    max_retries: int
    agent_trace: Dict[str, Dict[str, Any]]
    cost_trace: List[Dict[str, Any]]
    latency_trace: List[Dict[str, Any]]
    final_output: Dict[str, Any]
    error: str


# ================================================================
# 二、ToolCall — 工具调用记录
# ================================================================
@dataclass
class ToolCall:
    """记录一次工具调用的完整信息"""
    tool_name: str
    arguments: Dict[str, Any]
    result: str = ""
    elapsed: float = 0.0
    error: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result_len": len(self.result),
            "elapsed": self.elapsed,
            "error": self.error,
            "timestamp": self.timestamp,
        }


# ================================================================
# 三、AgentResult — Agent 执行结果
# ================================================================
@dataclass
class AgentResult:
    """
    Agent 执行结果的标准封装。

    所有 Agent 的 run() 方法返回此对象，保证接口一致性。
    """
    success: bool
    agent_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    elapsed: float = 0.0
    model_used: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0.0

    @property
    def result_dict(self) -> Dict:
        """转换为标准字典格式（与现有 API 兼容）"""
        base = {
            "success": self.success,
            "agent_id": self.agent_id,
            "elapsed": self.elapsed,
            "model_used": self.model_used,
        }
        if self.error:
            base["error"] = self.error
        if self.cost > 0:
            base["cost"] = self.cost
        base.update(self.data)
        return base

    @classmethod
    def failure(cls, agent_id: str, error: str, elapsed: float = 0.0) -> "AgentResult":
        return cls(
            success=False,
            agent_id=agent_id,
            error=error,
            elapsed=elapsed,
        )

    @classmethod
    def from_dict(cls, agent_id: str, result: Dict) -> "AgentResult":
        """从字典构建 AgentResult（用于兼容性）"""
        return cls(
            success=result.get("success", False),
            agent_id=agent_id,
            data={k: v for k, v in result.items()
                  if k not in ("success", "agent_id", "elapsed", "model_used", "error", "cost")},
            error=result.get("error", ""),
            elapsed=result.get("elapsed", 0.0),
            model_used=result.get("model_used", ""),
            cost=result.get("cost", 0.0),
        )


# ================================================================
# 四、TaskProfile — 任务画像（Router 使用）
# ================================================================
@dataclass
class TaskProfile:
    """
    任务画像：Router/Triage Agent 对输入任务的分析结果。

    路由决策依据：
      - complexity: simple / standard / complex
      - reasoning_type: sequential / parallel / hybrid
      - subject: 学科
      - topic: 核心主题
      - estimated_calls: 预估 LLM 调用次数
      - confidence: 分析置信度
    """
    complexity: str = "standard"
    reasoning_type: str = "sequential"
    subject: str = "综合"
    topic: str = ""
    estimated_calls: int = 1
    confidence: float = 0.5
    keywords: List[str] = field(default_factory=list)
    raw_input: str = ""

    # 路由决策
    @property
    def route(self) -> str:
        """返回路由路径：simple / standard / complex"""
        if self.complexity == "simple":
            return "simple"
        if self.complexity == "complex" and self.reasoning_type == "parallel":
            return "complex_parallel"
        return "standard"

    def to_dict(self) -> Dict:
        return {
            "complexity": self.complexity,
            "reasoning_type": self.reasoning_type,
            "subject": self.subject,
            "topic": self.topic,
            "estimated_calls": self.estimated_calls,
            "confidence": self.confidence,
            "keywords": self.keywords,
        }
