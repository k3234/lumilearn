# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — SelfCritique Agent（自我批判 / 自评 Agent）

职责：
  对模型生成的输出做自我质量评估。采用「启发式评分兜底 + 可选 LLM 打分器」
  的 fail-open 设计：LLM 打分器不可用、返回 None 或抛异常时一律回退到
  启发式评分，绝不向上抛异常阻塞主流程。

启发式评分规则（无模型兜底）：
  1. 基础分 50
  2. 输出长度：< 30 字 -20；30~80 字 +10；> 80 字 +20
  3. 空泛词（大概 / 可能 / 不知道 / 我不清楚 / 也许）：每个 -10，最多 -30
  4. 知识点命中：knowledge_context 中的关键词在输出中出现，每个 +5，最多 +20
  5. 包含 topic 相关词：+10
  6. 总分裁剪到 [0, 100]，passed = score >= threshold（默认 70）

用法示例：
    from agent_core.self_critique import SelfCritiqueAgent

    agent = SelfCritiqueAgent()
    result = agent.score(
        "自由落体运动是初速度为零、只受重力作用的运动。重力加速度约为 9.8 m/s²，"
        "下落快慢与质量无关。",
        topic="自由落体",
        knowledge_context="自由落体 重力加速度 初速度为零",
    )
    # -> {"score": int, "reason": "...", "passed": True}

    # 注入 LLM 打分器（可选）：期望返回 {"score": int}，返回 None / 抛异常时回退启发式
    def llm_scorer(text, topic, ctx):
        return {"score": 95}
    agent = SelfCritiqueAgent(llm_scorer=llm_scorer)
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional

# 空泛词：输出中出现即扣分（每个 -10，最多 -30）
_VAGUE_WORDS = ("大概", "可能", "不知道", "我不清楚", "也许")

# 关键词提取时过滤的停用词（中英文）
_STOPWORDS = frozenset({
    "的", "了", "是", "和", "与", "在", "对", "等", "或", "及", "之",
    "于", "为", "中", "上", "下", "个", "有", "无", "不", "就", "都",
    "a", "an", "the", "and", "of", "to", "in", "for", "with", "on",
})

# 按标点/空白切分（中文标点 + 英文标点 + 空白）
_SPLIT_RE = re.compile(r"[\s，。、；：！？,.!?;:()（）\[\]【】\"'“”‘’《》<>/-]+")


class SelfCritiqueAgent:
    """
    自我批判 Agent — 对生成输出进行质量自评。

    支持两种评分路径：
      - LLM 打分器（注入可选）：调用 llm_scorer(output_text, topic, knowledge_context)，
        期望返回 {"score": int} 或 None；调用异常 / 返回 None / 分数非法时回退启发式评分。
      - 启发式评分（无模型兜底）：按长度、空泛词、知识点命中、主题词命中计算得分。
    """

    def __init__(self, llm_scorer: Optional[Callable] = None, threshold: int = 70):
        """
        参数：
            llm_scorer: 可选 LLM 打分器，签名 llm_scorer(output_text, topic, knowledge_context)
                        -> {"score": int} 或 None；异常时自动回退启发式（fail-open）
            threshold: 通过阈值，默认 70（passed = score >= threshold）
        """
        self.llm_scorer = llm_scorer
        self.threshold = threshold

    # ============================================================
    # 主入口
    # ============================================================
    def score(self, output_text: str, topic: str = "",
              knowledge_context: str = "") -> Dict:
        """
        对输出文本进行自我批判评分。

        参数：
            output_text: 待评分的生成输出
            topic: 主题（用于主题相关词加分）
            knowledge_context: 知识上下文（从中提取关键词做命中加分）

        返回：
            {"score": int(0-100), "reason": str, "passed": bool}
        """
        # 优先使用 LLM 打分器；任何失败都回退启发式评分（fail-open，绝不抛异常）
        if self.llm_scorer is not None:
            try:
                llm_result = self.llm_scorer(output_text, topic, knowledge_context)
                if isinstance(llm_result, dict) and isinstance(llm_result.get("score"), int):
                    llm_score = max(0, min(100, llm_result["score"]))
                    return {
                        "score": llm_score,
                        "reason": f"LLM 打分器给出 {llm_score} 分",
                        "passed": llm_score >= self.threshold,
                    }
            except Exception:
                pass  # fail-open：LLM 打分器异常时静默回退启发式评分
        return self._heuristic_score(output_text, topic, knowledge_context)

    # ============================================================
    # 启发式评分（无模型兜底）
    # ============================================================
    def _heuristic_score(self, output_text: str, topic: str = "",
                         knowledge_context: str = "") -> Dict:
        """启发式评分：长度 / 空泛词 / 知识点命中 / 主题词命中"""
        text = output_text or ""
        length = len(text)
        score = 50  # 基础分

        # 1. 长度分：< 30 字 -20；30~80 字 +10；> 80 字 +20
        if length < 30:
            score -= 20
            len_note = "输出过短"
        elif length <= 80:
            score += 10
            len_note = "输出长度适中"
        else:
            score += 20
            len_note = "输出内容充实"

        # 2. 空泛词：每个 -10，最多 -30
        vague_hits = [w for w in _VAGUE_WORDS if w in text]
        score -= min(len(vague_hits) * 10, 30)

        # 3. 知识点命中：knowledge_context 关键词每个 +5，最多 +20
        keywords = self._extract_keywords(knowledge_context)
        kp_hits = [kw for kw in keywords if kw in text]
        score += min(len(kp_hits) * 5, 20)

        # 4. 主题相关词：命中 +10
        topic_hit = self._contains_topic(text, topic)
        if topic_hit:
            score += 10

        # 5. 裁剪到 [0, 100]
        score = max(0, min(100, score))

        # 汇总评分依据
        notes = [len_note]
        if vague_hits:
            notes.append(f"含空泛词（{len(vague_hits)}个）")
        if kp_hits:
            notes.append(f"知识点命中良好（{len(kp_hits)}个）")
        if topic_hit:
            notes.append("包含主题相关词")
        notes.append(f"得分{score}分")
        reason = "；".join(notes)

        return {
            "score": score,
            "reason": reason,
            "passed": score >= self.threshold,
        }

    # ============================================================
    # 辅助方法
    # ============================================================
    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """从文本提取候选关键词：长度 >= 2、非停用词、去重"""
        if not text:
            return []
        keywords: List[str] = []
        seen = set()
        for token in _SPLIT_RE.split(text):
            token = token.strip()
            if len(token) < 2 or token in _STOPWORDS or token in seen:
                continue
            seen.add(token)
            keywords.append(token)
        return keywords

    @staticmethod
    def _contains_topic(text: str, topic: str) -> bool:
        """输出是否包含主题相关词（topic 核心词任一命中；无核心词时整段匹配）"""
        if not topic:
            return False
        core = SelfCritiqueAgent._extract_keywords(topic)
        if not core:
            return topic in text
        return any(c in text for c in core)


if __name__ == "__main__":
    # 简单自测示例
    demo_agent = SelfCritiqueAgent()
    demo_result = demo_agent.score(
        "自由落体运动是初速度为零、只受重力作用的运动。重力加速度约为 9.8 m/s²，"
        "下落快慢与质量无关。常见误区：误以为质量大的物体下落更快。",
        topic="自由落体",
        knowledge_context="自由落体 重力加速度 初速度为零 质量",
    )
    print(f"分数: {demo_result['score']}")
    print(f"原因: {demo_result['reason']}")
    print(f"通过: {demo_result['passed']}")
