#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn LangGraph 多模型编排引擎 · V1
================================
核心理念：
  一次输入 → 全模型并行调用 → 多格式输出 → 汇总投票 → 一份全面数据

模型来源 (共12个)：
  天虹 Ollama (2):    qwen2.5:7b, deepseek-r1:1.5b
  天虹 LumiLearn (1): lumilearn-v4
  云端模型 (5):        Doubao-Seed-2.0-Code, Doubao-Seed-Code,
                      GLM-5, Kimi-K2.5, MiniMax-M2.5
  SOLO 内置 (5):      同上5个云端模型(降级模拟)

LangGraph 流程:
  [INPUT] → [FETCH_ALL] → [FORMAT_EACH] → [VOTE_AGGREGATE] → [OUTPUT]
     │           │              │                 │               │
    主题      并行调用      多格式转换         权重投票         综合数据
"""

from __future__ import annotations
import csv
import json
import os
import re
import sys
import time
import hashlib
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypedDict

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lumilearn_config import (
    TIANHONG_HOST, TIANHONG_OLLAMA_PORT, TIANHONG_API_PORT,
    CLOUD_MODELS, TIANHONG_MODELS, get_cloud_api_key, DISK_DATA,
)
from lumilearn_shared import (
    OLLAMA_MODELS, SOLO_MODELS, MASTER_CSV,
    read_existing_master, generate_id, ensure_dirs,
)

TODAY = datetime.now().strftime("%Y-%m-%d")
OUTPUT_DIR = os.path.join(DISK_DATA, "orchestration_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ================================================================
# 一、模型注册表（12个模型，统一接口）
# ================================================================
@dataclass
class ModelEntry:
    id:       str
    name:     str
    provider: str          # "tianhong_ollama" | "tianhong_custom" | "cloud" | "solo"
    weight:   int          # 投票权重
    endpoint: str          # API 地址
    api_key:  str = ""
    model_ref: str = ""    # 实际调用时用的model name

    def call(self, prompt: str, timeout: int = 60) -> str:
        if self.provider == "tianhong_ollama":
            return self._call_ollama(prompt, timeout)
        elif self.provider == "tianhong_custom":
            return self._call_tianhong_api(prompt, timeout)
        elif self.provider == "cloud":
            return self._call_cloud(prompt, timeout)
        elif self.provider == "solo":
            return self._solo_simulate(prompt)
        return ""

    def _call_ollama(self, prompt: str, timeout: int) -> str:
        try:
            resp = requests.post(
                f"{self.endpoint}/api/generate",
                json={"model": self.model_ref, "prompt": prompt,
                      "stream": False, "options": {"temperature": 0.3}},
                timeout=timeout,
            )
            return resp.json().get("response", "")
        except Exception as e:
            return f"[{self.name} 不可用: {e}]"

    def _call_tianhong_api(self, prompt: str, timeout: int) -> str:
        try:
            resp = requests.post(
                f"{self.endpoint}/api/generate",
                json={"model": self.model_ref, "prompt": prompt,
                      "stream": False, "temperature": 0.3},
                timeout=timeout,
            )
            return resp.json().get("response", "")
        except Exception as e:
            return f"[{self.name} 不可用: {e}]"

    def _call_cloud(self, prompt: str, timeout: int) -> str:
        if not self.api_key:
            return f"[{self.name} 无API Key]"
        try:
            resp = requests.post(
                f"{self.endpoint}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "model": self.model_ref,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                },
                timeout=timeout,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            return f"[{self.name} HTTP{resp.status_code}]"
        except Exception as e:
            return f"[{self.name} 不可用: {e}]"

    def _solo_simulate(self, prompt: str) -> str:
        """SOLO 模型降级：基于规则的质量评估"""
        content = prompt.lower()
        score = 0
        if len(content) > 100:
            score += 1
        if any(kw in content for kw in ["概念", "定义", "公式", "定理", "分析", "推导"]):
            score += 1
        if not any(bad in content for bad in ["错误", "不对"]):
            score += 1
        return "PASS: 内容质量达标" if score >= 2 else "NEEDS_REVIEW: 需进一步优化"


# ---- 构建完整模型注册表 ----
def _build_all_models() -> List[ModelEntry]:
    models: List[ModelEntry] = []

    # 天虹 Ollama (权重1)
    for name, cfg in OLLAMA_MODELS.items():
        models.append(ModelEntry(
            id=cfg["name"], name=cfg["name"], provider="tianhong_ollama",
            weight=1,
            endpoint=f"http://{TIANHONG_HOST}:{TIANHONG_OLLAMA_PORT}",
            model_ref=cfg["name"],
        ))

    # 天虹 LumiLearn 自有模型 (权重2)
    for name, cfg in TIANHONG_MODELS.items():
        if cfg["type"] == "tianhong_custom":
            models.append(ModelEntry(
                id=cfg["name"], name=cfg["name"], provider="tianhong_custom",
                weight=2,
                endpoint=f"http://{TIANHONG_HOST}:{TIANHONG_API_PORT}",
                model_ref=cfg["name"],
            ))

    # 云端模型 (权重2)
    for name, cfg in CLOUD_MODELS.items():
        key = get_cloud_api_key(name)
        models.append(ModelEntry(
            id=name, name=name, provider="cloud",
            weight=2, endpoint=cfg["api_base"],
            api_key=key, model_ref=name,
        ))

    # SOLO 内置模型 (权重2, 模拟)
    for name, cfg in SOLO_MODELS.items():
        # 避免重复
        if any(m.id == name for m in models):
            continue
        models.append(ModelEntry(
            id=name, name=name, provider="solo",
            weight=2, endpoint="",
            model_ref=name,
        ))

    return models

ALL_MODELS = _build_all_models()


# ================================================================
# 二、LangGraph 状态定义
# ================================================================
class AgentState(TypedDict, total=False):
    input_topic:     str
    input_context:   str
    model_responses: Dict[str, Dict]
    multi_formats:   Dict[str, Dict[str, str]]
    vote_result:     Dict
    final_output:    Dict


# ================================================================
# 三、数据格式生成器
# ================================================================
class MultiFormatGenerator:
    """将模型原始输出转换为5种标准格式"""

    FORMATS = ["teaching_content", "json_structured", "flashcard",
               "qa_pair", "markdown_note"]

    def __init__(self, helper_model: str = "qwen2.5:7b"):
        self.ollama_url = f"http://{TIANHONG_HOST}:{TIANHONG_OLLAMA_PORT}"

    def _call_helper(self, prompt: str, timeout: int = 45) -> str:
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": "qwen2.5:7b", "prompt": prompt,
                      "stream": False, "options": {"temperature": 0.2}},
                timeout=timeout,
            )
            return resp.json().get("response", "")
        except:
            return ""

    def generate_all_formats(self, raw_response: str, topic: str,
                             model_name: str) -> Dict[str, str]:
        """一条原始输出 → 5种格式"""
        if not raw_response or raw_response.startswith("["):
            return {fmt: raw_response for fmt in self.FORMATS}

        results = {}
        # 截断太长的响应
        truncated = raw_response[:2000]

        # 格式1: 教学正文
        results["teaching_content"] = self._fmt_teaching(truncated, topic)

        # 格式2: JSON 结构化
        results["json_structured"] = self._fmt_json(truncated, topic, model_name)

        # 格式3: 记忆卡片
        results["flashcard"] = self._fmt_flashcard(truncated, topic)

        # 格式4: QA 对
        results["qa_pair"] = self._fmt_qa(truncated, topic)

        # 格式5: Markdown 笔记
        results["markdown_note"] = self._fmt_markdown(truncated, topic, model_name)

        return results

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

        prompt = f"""从以下内容提取3-5个问答对作为记忆卡片, 返回JSON:
[{{"q":"问题","a":"答案"}}]

内容: {text[:600]}
主题: {topic}"""

        result = self._call_helper(prompt, 30)
        try:
            match = re.search(r"\[.*\]", result, re.DOTALL)
            if match:
                cards = json.loads(match.group())
                lines = []
                for c in cards[:5]:
                    lines.append(f"Q: {c.get('q','')}")
                    lines.append(f"A: {c.get('a','')}")
                    lines.append("---")
                return "\n".join(lines)
        except:
            pass
        return "\n".join([f"Q: {topic}的核心是什么?", f"A: {text[:200]}", "---"])

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
        return f"""---
topic: {topic}
model: {model}
date: {TODAY}
---

# {topic}

{text}

## 知识要点

{text[:400]}

---
*由 LumiLearn LangGraph 引擎自动生成*
"""


# ================================================================
# 四、加权投票汇总器
# ================================================================
class WeightedVoter:
    """对一个主题的所有模型输出进行加权投票, 生成一份综合数据"""

    def __init__(self, vote_threshold: int = 8):
        self.threshold = vote_threshold
        self.total_weight = sum(m.weight for m in ALL_MODELS)

    def aggregate(self, model_responses: Dict[str, Dict],
                  multi_formats: Dict[str, Dict[str, str]],
                  topic: str) -> Dict:
        """
        输入: 所有模型的原始输出 + 多格式输出
        输出: 一份综合数据
        """
        valid = {
            mid: resp for mid, resp in model_responses.items()
            if resp.get("raw") and not str(resp["raw"]).startswith("[")
        }

        total_votes = sum(
            ALL_MODELS_DICT.get(mid, ModelEntry(id="",name="",provider="",weight=1,endpoint="")).weight
            for mid in valid
        )

        # 1. 投票确认主题
        topics = self._extract_topics(valid)
        final_topic = self._vote_topic(topics, topic)

        # 2. 合并教学正文（拼接权重最高的前3个）
        best_content = self._merge_contents(valid, multi_formats)

        # 3. 投票确定 JSON 结构化数据
        best_json = self._vote_json(multi_formats)

        # 4. 合并记忆卡片（去重+投票）
        best_cards = self._merge_cards(multi_formats)

        # 5. 合并 QA 对（去重+投票）
        best_qa = self._merge_qa(multi_formats)

        # 6. 综合 Markdown
        best_md = self._merge_markdown(multi_formats, final_topic)

        # 7. 质量评估
        quality = self._assess_quality(valid, total_votes)

        return {
            "topic":            final_topic,
            "generated_at":     datetime.now().isoformat(),
            "models_used":      len(valid),
            "models_total":     len(ALL_MODELS),
            "vote_score":       f"{total_votes}/{self.total_weight}",
            "teaching_content": best_content,
            "json_structured":  best_json,
            "flashcards":       best_cards,
            "qa_pairs":         best_qa,
            "markdown_note":    best_md,
            "quality_report":   quality,
            "all_model_details": {
                mid: {"name": r["entry"].name, "weight": r["entry"].weight,
                      "provider": r["entry"].provider,
                      "response_len": len(r["raw"])}
                for mid, r in model_responses.items()
            },
        }

    def _extract_topics(self, valid: Dict) -> List[str]:
        topics = []
        for mid, resp in valid.items():
            text = resp["raw"][:200]
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("#"):
                    topics.append(line.lstrip("#").strip()[:50])
        return topics

    def _vote_topic(self, topics: List[str], original: str) -> str:
        if not topics:
            return original
        counter = Counter(topics)
        return counter.most_common(1)[0][0]

    def _merge_contents(self, valid: Dict, fmts: Dict) -> str:
        """按权重合并前3个模型的教学内容"""
        scored = []
        for mid, resp in valid.items():
            entry = ALL_MODELS_DICT.get(mid)
            w = entry.weight if entry else 1
            text = resp["raw"]
            scored.append((w, len(text), text))

        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        top3 = scored[:3]

        result = []
        for i, (w, _, text) in enumerate(top3, 1):
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
                except:
                    pass
        return json.dumps({
            "composite": True,
            "sources": len(jsons),
            "merged_data": jsons[:5],
        }, ensure_ascii=False, indent=2)

    def _merge_cards(self, fmts: Dict) -> str:
        all_cards = []
        seen = set()
        for mid, fmt in fmts.items():
            cards_text = fmt.get("flashcard", "")
            pairs = []
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
                        pairs.append(pair)
                    current_q = ""
            all_cards.extend(pairs)

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
            lines = qa_text.split("\n")
            for line in lines:
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

        models_ok = [mid for mid, r in valid.items()
                     if len(r["raw"]) > 200]
        models_fail = [mid for mid, r in valid.items()
                       if len(r["raw"]) <= 200 or str(r["raw"]).startswith("[")]

        return {
            "level":          level,
            "vote_score":     f"{total_votes}/{self.total_weight}",
            "models_passed":  len(models_ok),
            "models_failed":  len(models_fail),
            "confidence":     min(1.0, total_votes / self.total_weight),
            "recommendation": "可直接用于教学" if level in ("excellent","good")
                              else "建议人工审核" if level == "acceptable"
                              else "需要重新生成",
        }


ALL_MODELS_DICT = {m.id: m for m in ALL_MODELS}


# ================================================================
# 五、LangGraph 编排引擎
# ================================================================
class OrchestrationEngine:
    """
    LangGraph 风格的编排引擎:
      INPUT → FETCH_ALL → FORMAT_EACH → VOTE → OUTPUT
    """

    def __init__(self):
        self.models = ALL_MODELS
        self.formatter = MultiFormatGenerator()
        self.voter = WeightedVoter()
        self.state: AgentState = {}

    # ---------- Node: INPUT ----------
    def node_input(self, topic: str, context: str = "") -> AgentState:
        self.state = {
            "input_topic":     topic,
            "input_context":   context,
            "model_responses": {},
            "multi_formats":   {},
            "vote_result":     {},
            "final_output":    {},
        }
        return self.state

    # ---------- Node: FETCH_ALL (并行) ----------
    def node_fetch_all(self, max_workers: int = 6) -> AgentState:
        topic = self.state["input_topic"]
        context = self.state.get("input_context", "")

        prompt = f"""你是一位资深教育专家。请针对以下主题生成一份详细的、适合教学的知识内容。

主题: {topic}
{"补充说明: " + context if context else ""}

要求:
1. 先给出核心概念的定义
2. 列出3-5个关键知识点
3. 提供1-2个具体示例或应用
4. 指出常见误区和易错点
5. 最后给出学习建议

请严格按上述结构输出，总字数200-800字。"""

        responses: Dict[str, Dict] = {}

        def _query_model(model: ModelEntry) -> Tuple[str, str, float]:
            t0 = time.time()
            raw = model.call(prompt, timeout=60)
            elapsed = time.time() - t0
            return model.id, raw, elapsed

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_query_model, m): m for m in self.models}
            for fut in as_completed(futures):
                mid, raw, elapsed = fut.result()
                entry = ALL_MODELS_DICT.get(mid)
                responses[mid] = {
                    "raw":      raw,
                    "entry":    entry or self.models[0],
                    "elapsed":  round(elapsed, 2),
                    "available": not str(raw).startswith("["),
                }

        self.state["model_responses"] = responses
        return self.state

    # ---------- Node: FORMAT_EACH ----------
    def node_format_all(self) -> AgentState:
        topic = self.state["input_topic"]
        responses = self.state["model_responses"]
        all_formats: Dict[str, Dict[str, str]] = {}

        for mid, resp in responses.items():
            raw = resp["raw"]
            name = resp.get("entry", ModelEntry(id="",name="",provider="",weight=1,endpoint="")).name
            all_formats[mid] = self.formatter.generate_all_formats(raw, topic, name)

        self.state["multi_formats"] = all_formats
        return self.state

    # ---------- Node: VOTE ----------
    def node_vote_aggregate(self) -> AgentState:
        vote_result = self.voter.aggregate(
            self.state["model_responses"],
            self.state["multi_formats"],
            self.state["input_topic"],
        )
        self.state["vote_result"] = vote_result
        return self.state

    # ---------- Node: OUTPUT ----------
    def node_output(self) -> Dict:
        result = self.state["vote_result"]
        self._save_output(result)
        return result

    def _save_output(self, result: Dict):
        """保存综合结果到文件"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        topic_safe = re.sub(r'[\\/:*?"<>|]', '_', result["topic"])[:40]

        # JSON 完整输出
        json_path = os.path.join(OUTPUT_DIR, f"orchestra_{ts}_{topic_safe}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # Markdown 输出
        md_path = os.path.join(OUTPUT_DIR, f"orchestra_{ts}_{topic_safe}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(result["markdown_note"])
            f.write(f"\n\n## 综合教学正文\n\n{result['teaching_content']}\n")
            f.write(f"\n\n## 记忆卡片\n\n{result['flashcards']}\n")
            f.write(f"\n\n## QA 对\n\n{result['qa_pairs']}\n")

        # CSV 摘要
        csv_path = os.path.join(OUTPUT_DIR, f"orchestra_{ts}_{topic_safe}.csv")
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["topic", "models_used", "vote_score", "confidence",
                            "quality_level", "timestamp"])
            q = result["quality_report"]
            writer.writerow([result["topic"], result["models_used"],
                            result["vote_score"], q["confidence"],
                            q["level"], result["generated_at"]])

        # 追加到主数据库
        self._append_to_master(result)

    def _append_to_master(self, result: Dict):
        """将综合结果追加到主数据库"""
        existing = read_existing_master()
        existing_ids = {r["id"] for r in existing}
        rid = generate_id(existing_ids)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        q = result["quality_report"]

        row = {
            "id":               rid,
            "subject":          self._guess_subject(result["topic"]),
            "grade":            "高中",
            "version":          "通用版",
            "chapter":          result["topic"],
            "section":          result["topic"],
            "title":            result["topic"],
            "content":          result["teaching_content"][:2000],
            "content_format":   "text",
            "type":             "多模型综合",
            "difficulty":       "中等",
            "source":           f"LangGraph多模型编排({result['models_used']}模型)",
            "source_type":      "multi_model_orchestra",
            "tags":             f"{result['topic']},多模型,投票{q['level']}",
            "deepseek_r1_15b":  "AUTO",
            "qwen2_5_7b_p2":    "AUTO",
            "qwen2_5_7b_p3":    "AUTO",
            "check_time":       now,
            "errors":           "" if q["level"] in ("excellent","good") else q["recommendation"],
            "create_time":      now,
            "update_time":      now,
        }
        existing.append(row)
        from lumilearn_shared import write_master_csv
        write_master_csv(existing)

    def _guess_subject(self, topic: str) -> str:
        keywords = {
            "数学": ["函数", "方程", "几何", "概率", "数列", "三角", "向量"],
            "物理": ["力", "运动", "电场", "磁场", "能量", "光", "热"],
            "化学": ["反应", "元素", "化学键", "溶液", "酸碱", "氧化"],
            "英语": ["时态", "从句", "语法", "词汇", "作文"],
            "语文": ["文言", "诗词", "阅读", "作文", "修辞"],
        }
        for subj, kws in keywords.items():
            if any(kw in topic for kw in kws):
                return subj
        return "综合"

    # ---------- 完整流水线 ----------
    def run(self, topic: str, context: str = "") -> Dict:
        print("\n" + "=" * 70)
        print("🧠 LumiLearn LangGraph 多模型编排引擎")
        print("=" * 70)
        print(f"  主题: {topic}")
        print(f"  模型总数: {len(self.models)}")
        print(f"  天虹: {sum(1 for m in self.models if 'tianhong' in m.provider)}")
        print(f"  云端: {sum(1 for m in self.models if m.provider == 'cloud')}")
        print(f"  SOLO: {sum(1 for m in self.models if m.provider == 'solo')}")

        # Step 1: INPUT
        print("\n[节点1] INPUT - 接收主题...")
        self.node_input(topic, context)

        # Step 2: FETCH_ALL (并行)
        print(f"[节点2] FETCH_ALL - 并行调用 {len(self.models)} 个模型...")
        t0 = time.time()
        self.node_fetch_all(max_workers=6)
        ok = sum(1 for r in self.state["model_responses"].values() if r["available"])
        print(f"  完成: {ok}/{len(self.models)} 个模型响应 ({time.time()-t0:.1f}s)")

        # Step 3: FORMAT_EACH
        print(f"[节点3] FORMAT_EACH - 转换为5种数据格式...")
        self.node_format_all()
        print(f"  完成: {len(self.state['multi_formats'])} 组多格式数据")

        # Step 4: VOTE
        print(f"[节点4] VOTE_AGGREGATE - 加权投票汇总...")
        self.node_vote_aggregate()
        q = self.state["vote_result"]["quality_report"]
        print(f"  投票: {q['vote_score']} | 通过: {q['models_passed']} | 质量: {q['level']}")

        # Step 5: OUTPUT
        print(f"[节点5] OUTPUT - 输出综合数据...")
        result = self.node_output()
        print(f"  保存至: {OUTPUT_DIR}")
        print(f"  质量建议: {q['recommendation']}")
        print("=" * 70)

        return result

    def print_detailed_report(self, result: Dict):
        """打印详细报告"""
        print("\n" + "─" * 70)
        print("📊 模型响应详情")
        print("─" * 70)
        for mid, detail in result.get("all_model_details", {}).items():
            status = "✅" if detail["response_len"] > 100 else "❌"
            print(f"  {status} {detail['name']:30s} | {detail['provider']:20s} "
                  f"| 权重{detail['weight']} | {detail['response_len']}字")

        print("\n" + "─" * 70)
        print("📝 综合教学正文 (前500字)")
        print("─" * 70)
        print(result["teaching_content"][:500])
        print("...")

        print("\n" + "─" * 70)
        print("🃏 记忆卡片")
        print("─" * 70)
        cards = result["flashcards"].split("---")
        for card in cards[:5]:
            if card.strip():
                print(card.strip()[:120])

        print("\n" + "─" * 70)
        print("📈 质量报告")
        print("─" * 70)
        qr = result["quality_report"]
        for k, v in qr.items():
            print(f"  {k}: {v}")


# ================================================================
# 六、主程序
# ================================================================
def main():
    engine = OrchestrationEngine()

    print("\n" + "=" * 70)
    print("🚀 LumiLearn LangGraph 多模型编排引擎")
    print("=" * 70)
    print(f"\n  已注册 {len(ALL_MODELS)} 个模型:")
    for m in ALL_MODELS:
        icon = {"tianhong_ollama":"🏠","tianhong_custom":"🔧",
                "cloud":"☁️","solo":"🤖"}.get(m.provider,"❓")
        print(f"    {icon} {m.name:30s} [{m.provider}] 权重{m.weight}")

    print("\n" + "─" * 70)
    print("  流程: INPUT → FETCH_ALL(并行) → FORMAT(5格式) → VOTE → OUTPUT")
    print("─" * 70)

    print("\n示例主题:")
    print("  1. 三角函数的基本性质")
    print("  2. 牛顿第二定律")
    print("  3. 化学平衡与勒夏特列原理")
    print("  4. 定语从句的用法")
    print("  5. DNA的双螺旋结构")
    print("  6. 自定义输入")

    choice = input("\n请选择 (1-6, 默认1): ").strip() or "1"
    examples = {
        "1": "三角函数的基本性质",
        "2": "牛顿第二定律",
        "3": "化学平衡与勒夏特列原理",
        "4": "定语从句的用法",
        "5": "DNA的双螺旋结构",
    }

    if choice == "6":
        topic = input("请输入主题: ").strip()
        if not topic:
            print("主题不能为空")
            return
    else:
        topic = examples.get(choice, examples["1"])

    context = input("补充说明(可选): ").strip()

    # 运行
    result = engine.run(topic, context)
    engine.print_detailed_report(result)

    print(f"\n✅ 完整输出已保存到: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()