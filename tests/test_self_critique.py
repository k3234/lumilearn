# -*- coding: utf-8 -*-
"""
LumiLearn — SelfCritique Agent（自我批判）测试

覆盖：
  - 高质量长输出（含知识点 / 主题词）→ passed=True
  - 短且含空泛词的输出 → passed=False
  - 恰好 70 分边界 → passed=True
  - 注入 LLM 打分器 → 使用其分数
  - LLM 打分器异常 / 返回 None → 回退启发式评分（fail-open，不崩溃）
  - 空输出 → 低分失败
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.self_critique import SelfCritiqueAgent


GOOD_OUTPUT = (
    "自由落体运动是初速度为零、只受重力作用的运动。重力加速度约为9.8米每二次方秒，"
    "下落快慢与质量无关。常见误区是认为质量大的物体下落更快，实际上在真空中"
    "所有物体下落快慢相同。伽利略的比萨斜塔实验证明了这一点。"
)


def test_high_quality_passes():
    """长且含知识点的输出 → 高分通过"""
    agent = SelfCritiqueAgent()
    result = agent.score(
        GOOD_OUTPUT,
        topic="自由落体",
        knowledge_context="自由落体 重力加速度 初速度为零 伽利略",
    )
    assert result["passed"] is True
    assert result["score"] >= 70
    assert "知识点命中" in result["reason"]


def test_low_quality_fails():
    """短且含空泛词的输出 → 低分失败"""
    agent = SelfCritiqueAgent()
    result = agent.score("大概可能不知道，也许吧。")
    assert result["passed"] is False
    assert result["score"] < 70
    assert "空泛词" in result["reason"]


def test_boundary_70():
    """恰好 70 分（基础 50 + 长度>80 加 20）→ passed=True"""
    agent = SelfCritiqueAgent()
    output = "长内容" * 30  # 90 字，> 80 加 20 分
    result = agent.score(output)
    assert result["score"] == 70
    assert result["passed"] is True


def test_llm_scorer_used():
    """注入 llm_scorer 时使用其分数"""
    calls = []

    def llm_scorer(text, topic, ctx):
        calls.append((text, topic, ctx))
        return {"score": 99}

    agent = SelfCritiqueAgent(llm_scorer=llm_scorer)
    result = agent.score("随便什么内容", topic="t", knowledge_context="k")
    assert result["score"] == 99
    assert result["passed"] is True
    assert len(calls) == 1  # 确认确实调用了 LLM 打分器


def test_llm_scorer_fallback():
    """llm_scorer 抛异常或返回 None → 回退启发式评分，不崩溃"""
    def raising_scorer(text, topic, ctx):
        raise RuntimeError("llm down")

    agent = SelfCritiqueAgent(llm_scorer=raising_scorer)
    result = agent.score("大概也许吧")  # 不应抛异常
    assert isinstance(result["score"], int)
    assert result["score"] < 70
    assert result["passed"] is False

    # 返回 None 同样回退启发式评分
    agent_none = SelfCritiqueAgent(llm_scorer=lambda *args: None)
    result_none = agent_none.score(GOOD_OUTPUT)
    assert isinstance(result_none["score"], int)
    assert result_none["passed"] is True


def test_empty_output():
    """空输出 → 低分失败"""
    agent = SelfCritiqueAgent()
    result = agent.score("")
    assert result["score"] <= 30
    assert result["passed"] is False
    assert "输出过短" in result["reason"]
