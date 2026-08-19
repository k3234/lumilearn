# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — LangGraph 风格编排引擎

重构自 langgraph_engine.py，保留核心编排能力：
  INPUT → FETCH_ALL(并行) → FORMAT_EACH → VOTE_AGGREGATE → OUTPUT

新增能力：
  - 与 agent_core.models.AgentState 集成
  - 成本追踪（cost_trace）
  - 延迟追踪（latency_trace）
  - 可配置的最大 Workers 数
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
import hashlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.model_registry import (
    ALL_MODELS, ALL_MODELS_DICT, ModelEntry,
)
from agent_core.models import AgentState


# ================================================================
# 数据格式生成器（从原 langgraph_engine 提取）
# ================================================================
class MultiFormatGenerator:
    """将模型原始输出转换为5种标准格式"""

    FORMATS = ["teaching_content", "json_structured", "flashcard",
               "qa_pair", "markdown_note"]

    def __init__(self, helper_model: str = "qwen2.5:7b"):
        self.helper_model = helper_model
        self.ollama_url = f"http://localhost:11434"

    def generate_all_formats(self, raw_response: str, topic: str,
                             model_name: str) -> Dict[str, str]:
        """一条原始输出 → 5种格式"""
        if not raw_response or raw_response.startswith("["):
            return {fmt: raw_response for fmt in self.FORMATS}

        truncated = raw_response[:2000]
        return {
            "teaching_content": self._fmt_teaching(truncated, topic),
            "json_structured":  self._fmt_json(truncated, topic, model_name),
            "flashcard":        self._fmt_flashcard(truncated, topic),
            "qa_pair":          self._fmt_qa(truncated, topic),
            "markdown_note":    self._fmt_markdown(truncated, topic, model_name),
        }

    def _fmt_teaching(self, text: str, topic: str) -> str:
        lines = [l for l in text.split("\n") if l.strip()]
        header = f"# {topic}\n\n"
        if lines and not lines[0].startswith("#"):
            return header + text
        return text

    def _fmt_json(self, text: str, topic: str, model: str) -> str:
        return json.dumps({
            "topic": topic, "model": model,
            "timestamp": datetime.now().isoformat(),
            "content_summary": text[:300],
            "full_content": text,
            "word_count": len(text),
            "quality_flag": "PASS" if len(text) > 200 else "LOW",
        }, ensure_ascii=False, indent=2)

    def _fmt_flashcard(self, text: str, topic: str) -> str:
        sentences = re.split(r'[。！？]', text)
        key_points = [s.strip() for s in sentences if len(s.strip()) > 15][:5]
        if not key_points:
            return f"Q: {topic}的核心是什么?\nA: {text[:200]}\n---"
        lines = []
        for kp in key_points:
            lines.append(f"Q: {kp}")
            lines.append(f"A: 请用自己的话解释这个要点")
            lines.append("---")
        return "\n".join(lines)

    def _fmt_qa(self, text: str, topic: str) -> str:
        sentences = re.split(r'[。！？]', text)
        key = [s.strip() for s in sentences if len(s.strip()) > 20]
        items = []
        for i, s in enumerate(key[:5], 1):
            items.append(f"问题{i}: 请解释: {s[:60]}...")
            items.append(f"答案{i}: {s}")
            items.append("")
        return "\n".join(items) if items else text

    def _fmt_markdown(self, text: str, topic: str, model: str) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        return (
            f"---\ntopic: {topic}\nmodel: {model}\ndate: {today}\n---\n\n"
            f"# {topic}\n\n{text}\n\n"
            f"## 知识要点\n\n{text[:400]}\n\n"
            f"---\n*由 LumiLearn Agent Core 自动生成*\n"
        )


# ================================================================
# 加权投票汇总器（从原 langgraph_engine 提取）
# ================================================================
class WeightedVoter:
    """对一个主题的所有模型输出进行加权投票, 生成一份综合数据"""

    def __init__(self, vote_threshold: int = 8):
        self.threshold = vote_threshold
        self.total_weight = sum(m.weight for m in ALL_MODELS)

    def aggregate(self, model_responses: Dict[str, Dict],
                  multi_formats: Dict[str, Dict[str, str]],
                  topic: str) -> Dict:
        valid = {
            mid: resp for mid, resp in model_responses.items()
            if resp.get("raw") and not str(resp["raw"]).startswith("[")
        }

        total_votes = sum(
            ALL_MODELS_DICT.get(mid, ModelEntry(id="", name="", provider="", weight=1, endpoint="")).weight
            for mid in valid
        )

        return {
            "topic": topic,
            "generated_at": datetime.now().isoformat(),
            "models_used": len(valid),
            "models_total": len(ALL_MODELS),
            "vote_score": f"{total_votes}/{self.total_weight}",
            "teaching_content": self._merge_contents(valid, multi_formats),
            "json_structured": self._vote_json(multi_formats),
            "flashcards": self._merge_cards(multi_formats),
            "qa_pairs": self._merge_qa(multi_formats),
            "markdown_note": self._merge_markdown(multi_formats, topic),
            "quality_report": self._assess_quality(valid, total_votes),
            "all_model_details": {
                mid: {"name": resp.get("entry", ModelEntry(id="", name="", provider="", weight=1, endpoint="")).name,
                      "weight": resp.get("entry", ModelEntry(id="", name="", provider="", weight=1, endpoint="")).weight,
                      "provider": resp.get("entry", ModelEntry(id="", name="", provider="", weight=1, endpoint="")).provider,
                      "response_len": len(resp["raw"])}
                for mid, resp in valid.items()
            },
        }

    def _merge_contents(self, valid: Dict, fmts: Dict) -> str:
        scored = []
        for mid, resp in valid.items():
            entry = resp.get("entry", ModelEntry(id="", name="", provider="", weight=1, endpoint=""))
            w = entry.weight if entry else 1
            scored.append((w, len(resp["raw"]), resp["raw"]))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        result = []
        for i, (w, _, text) in enumerate(scored[:3], 1):
            result.append(f"## 来源{i} (权重{w})\n\n{text[:800]}\n")
        return "\n".join(result)

    def _vote_json(self, fmts: Dict) -> str:
        jsons = []
        for mid, fmt in fmts.items():
            j = fmt.get("json_structured", "")
            if j:
                try:
                    parsed = json.loads(j)
                    parsed["source_model"] = mid
                    jsons.append(parsed)
                except Exception:
                    pass
        return json.dumps({
            "composite": True, "sources": len(jsons),
            "merged_data": jsons[:5],
        }, ensure_ascii=False, indent=2)

    def _merge_cards(self, fmts: Dict) -> str:
        all_cards = []
        seen = set()
        for mid, fmt in fmts.items():
            cards_text = fmt.get("flashcard", "")
            lines = cards_text.split("\n")
            current_q = ""
            for line in lines:
                if line.startswith("Q:") or line.startswith("问题"):
                    current_q = line
                elif (line.startswith("A:") or line.startswith("答案")) and current_q:
                    pair = (current_q.strip(), line.strip())
                    h = hashlib.md5(pair[0].encode()).hexdigest()[:8]
                    if h not in seen:
                        seen.add(h)
                        all_cards.append(pair)
                    current_q = ""
            all_cards.extend(all_cards)
        result = []
        for i, (q, a) in enumerate(all_cards[:10], 1):
            result.append(f"Q{i}: {q.replace('Q:','').strip()}")
            result.append(f"A{i}: {a.replace('A:','').strip()}")
            result.append("---")
        return "\n".join(result) if result else "无卡片"

    def _merge_qa(self, fmts: Dict) -> str:
        all_qa = []
        seen = set()
        for mid, fmt in fmts.items():
            qa_text = fmt.get("qa_pair", "")
            for line in qa_text.split("\n"):
                if line.startswith("问题") or line.startswith("答案"):
                    h = hashlib.md5(line.encode()).hexdigest()[:8]
                    if h not in seen:
                        seen.add(h)
                        all_qa.append(line)
        return "\n".join(all_qa[:30]) if all_qa else "无QA对"

    def _merge_markdown(self, fmts: Dict, topic: str) -> str:
        parts = [f"# {topic}\n\n> 由 {len(fmts)} 个模型联合生成\n"]
        for i, (mid, fmt) in enumerate(fmts.items(), 1):
            md = fmt.get("markdown_note", "")
            if md and len(md) > 50:
                parts.append(f"\n## 模型{i}: {mid}\n\n{md[:600]}\n")
        return "\n".join(parts)

    def _assess_quality(self, valid: Dict, total_votes: int) -> Dict:
        level = "excellent" if total_votes >= 12 else \
                "good" if total_votes >= 8 else \
                "acceptable" if total_votes >= 4 else "poor"
        models_ok = [mid for mid, r in valid.items() if len(r["raw"]) > 200]
        models_fail = [mid for mid, r in valid.items()
                       if len(r["raw"]) <= 200 or str(r["raw"]).startswith("[")]
        return {
            "level": level,
            "vote_score": f"{total_votes}/{self.total_weight}",
            "models_passed": len(models_ok),
            "models_failed": len(models_fail),
            "confidence": min(1.0, total_votes / self.total_weight),
            "recommendation": "可直接用于教学" if level in ("excellent", "good")
                              else "建议人工审核" if level == "acceptable"
                              else "需要重新生成",
        }


# ================================================================
# LangGraph 编排引擎
# ================================================================
class OrchestrationEngine:
    """
    LangGraph 风格的统一编排引擎。

    流程：INPUT → FETCH_ALL(并行) → FORMAT_EACH → VOTE → OUTPUT

    与 Phase 0 的区别：
      - 使用 agent_core.models.AgentState 统一状态
      - 增加 cost_trace 和 latency_trace
      - 输出格式与现有 goai_multi_agent.py 兼容
    """

    def __init__(self, max_workers: int = 6):
        self.max_workers = max_workers
        self.formatter = MultiFormatGenerator()
        self.voter = WeightedVoter()
        self._state: AgentState = {}
        self.cost_trace: List[Dict[str, Any]] = []
        self.latency_trace: List[Dict[str, Any]] = []

    @property
    def state(self) -> AgentState:
        return self._state

    def node_input(self, topic: str, context: str = "") -> AgentState:
        self._state = AgentState(
            input_topic=topic,
            input_context=context,
            model_responses={},
            multi_formats={},
            vote_result={},
            final_output={},
            agent_trace={},
            cost_trace=[],
            latency_trace=[],
            retry_count=0,
            max_retries=3,
        )
        return self._state

    def node_fetch_all(self) -> AgentState:
        topic = self._state["input_topic"]
        context = self._state.get("input_context", "")

        prompt = (
            f"你是一位资深教育专家。请针对以下主题生成一份详细的、适合教学的知识内容。\n\n"
            f"主题: {topic}\n"
            f"{'补充说明: ' + context if context else ''}\n\n"
            f"要求:\n"
            f"1. 先给出核心概念的定义\n"
            f"2. 列出3-5个关键知识点\n"
            f"3. 提供1-2个具体示例或应用\n"
            f"4. 指出常见误区和易错点\n"
            f"5. 最后给出学习建议\n\n"
            f"请严格按上述结构输出，总字数200-800字。"
        )

        responses: Dict[str, Dict] = {}

        def _query_model(model: ModelEntry) -> Tuple[str, str, float]:
            t0 = time.time()
            raw = model.call(prompt, timeout=60)
            elapsed = time.time() - t0
            return model.id, raw, elapsed

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(_query_model, m): m for m in ALL_MODELS}
            for fut in as_completed(futures):
                mid, raw, elapsed = fut.result()
                entry = ALL_MODELS_DICT.get(mid)
                responses[mid] = {
                    "raw": raw,
                    "entry": entry or ALL_MODELS[0],
                    "elapsed": round(elapsed, 2),
                    "available": not str(raw).startswith("["),
                }
                # 追踪延迟
                self.latency_trace.append({
                    "model_id": mid,
                    "provider": (entry or ALL_MODELS[0]).provider,
                    "elapsed": round(elapsed, 3),
                })

        self._state["model_responses"] = responses
        return self._state

    def node_format_all(self) -> AgentState:
        topic = self._state["input_topic"]
        responses = self._state["model_responses"]
        all_formats: Dict[str, Dict[str, str]] = {}

        for mid, resp in responses.items():
            raw = resp["raw"]
            name = resp.get("entry", ModelEntry(id="", name="", provider="", weight=1, endpoint="")).name
            all_formats[mid] = self.formatter.generate_all_formats(raw, topic, name)

        self._state["multi_formats"] = all_formats
        return self._state

    def node_vote_aggregate(self) -> AgentState:
        vote_result = self.voter.aggregate(
            self._state["model_responses"],
            self._state["multi_formats"],
            self._state["input_topic"],
        )
        self._state["vote_result"] = vote_result
        return self._state

    def node_output(self) -> Dict:
        result = self._state["vote_result"]
        result["cost_trace"] = self.cost_trace
        result["latency_trace"] = self.latency_trace
        result["agent_trace"] = self._state.get("agent_trace", {})
        return result

    def run(self, topic: str, context: str = "") -> Dict:
        """
        执行完整编排流水线。

        Args:
            topic: 教学主题
            context: 补充上下文

        Returns:
            综合输出字典（含 cost_trace, latency_trace, agent_trace）
        """
        # Step 1: INPUT
        self.node_input(topic, context)

        # Step 2: FETCH_ALL (并行)
        t0 = time.time()
        self.node_fetch_all()
        fetch_time = time.time() - t0
        ok = sum(1 for r in self._state["model_responses"].values() if r["available"])

        # 追踪成本（简单估算：每模型约 $0.001-0.01）
        self.cost_trace.append({
            "stage": "fetch_all",
            "models_called": len(ALL_MODELS),
            "models_ok": ok,
            "elapsed": round(fetch_time, 3),
            "estimated_cost": round(ok * 0.003, 4),
        })

        # Step 3: FORMAT_EACH
        self.node_format_all()

        # Step 4: VOTE
        self.node_vote_aggregate()

        # Step 5: OUTPUT
        result = self.node_output()
        result["total_time"] = round(time.time() - t0, 3)
        return result

    def run_single(self, topic: str, model_id: str = "") -> Dict:
        """
        单模型执行（用于简单任务路由）。

        Args:
            topic: 教学主题
            model_id: 指定模型ID（为空则使用第一个可用模型）

        Returns:
            单模型输出
        """
        if not model_id:
            best_models = [m for m in ALL_MODELS if m.provider != "solo"]
            model_id = best_models[0].id if best_models else ALL_MODELS[0].id

        model = ALL_MODELS_DICT.get(model_id)
        if not model:
            return {"success": False, "error": f"模型不存在: {model_id}"}

        t0 = time.time()
        prompt = (
            f"你是一位资深教育专家。请针对以下主题生成一份详细的、适合教学的知识内容。\n\n"
            f"主题: {topic}\n\n"
            f"要求:\n"
            f"1. 先给出核心概念的定义\n"
            f"2. 列出3-5个关键知识点\n"
            f"3. 提供1-2个具体示例或应用\n"
            f"4. 指出常见误区和易错点\n"
            f"5. 最后给出学习建议\n\n"
            f"请严格按上述结构输出，总字数200-800字。"
        )
        raw = model.call(prompt, timeout=60)
        elapsed = time.time() - t0

        # 生成标准格式
        formatter = MultiFormatGenerator()
        formats = formatter.generate_all_formats(raw, topic, model.name)

        return {
            "success": True,
            "topic": topic,
            "model_id": model_id,
            "model_name": model.name,
            "provider": model.provider,
            "elapsed": round(elapsed, 3),
            "content": formats["teaching_content"],
            "formats": formats,
            "quality_flag": "PASS" if len(raw) > 200 else "LOW",
        }


# ================================================================
# 便捷入口
# ================================================================
def run_orchestration(topic: str, context: str = "", max_workers: int = 6) -> Dict:
    """一行调用编排引擎"""
    engine = OrchestrationEngine(max_workers=max_workers)
    return engine.run(topic, context)


def run_single_model(topic: str, model_id: str = "") -> Dict:
    """一行调用单模型"""
    engine = OrchestrationEngine()
    return engine.run_single(topic, model_id)
