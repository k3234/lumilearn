# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — FactChecker Agent（事实核查 / P0-2）

职责：
  对教学内容做二次事实校验（与 RAG 知识库来源核对），降低语义级幻觉风险
  （compliance 9.4）。作为独立 Agent 加入 MultiAgentPipeline，与 Verifier 协同：
    - Verifier：质量/结构/评分一致性验证
    - FactChecker：内容与知识库来源的事实一致性验证

检查项（规则模式，默认不调模型）：
  1. 内容非空（防御性）
  2. RAG 来源可用性：无来源则降级放行并标注（不阻塞教学主流程）
  3. 主题覆盖：教学主题核心词是否被知识库来源覆盖
  4. 声明一致性：内容句子与来源句子的 2-gram 重叠度（关联度低 → 疑似幻觉）
  5. 数值矛盾：内容中的「数值+单位」与来源中的同一单位数值冲突（硬性失败）
  6. 模型辅助校验（可选 use_model）：轻量模型对内容 vs 来源输出 PASS/FAIL

输出：
  - passed:    是否通过事实核查
  - confidence: 置信度（0-100）
  - issues:    问题清单（error 级 → 判定失败）
  - reason:    结论说明
  - sources_checked: 实际核对到的知识库来源数

设计要点：
  - 遵循单例模式 + 线程安全 + 文档字符串的开发纪律
  - 任何检索/模型失败都降级，绝不阻塞教学主流程
"""

from __future__ import annotations

import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.model_registry import get_model

# 数值提取：数字（含小数/科学计数法）+ 紧随其后的单位（字母/%/°C 等）
_NUM_RE = re.compile(r"(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([A-Za-z%℃°²³·/^\-]{1,4})?")
_SENT_SPLIT_RE = re.compile(r"[。！？!?；;\n]+")


class FactCheckerAgent:
    """
    事实核查 Agent — 教学内容与 RAG 知识库来源的一致性验证。

    输入 payload:
        topic: 教学主题（必填）
        teaching_content: 待核查的教学内容
        steps: 费曼五步步骤列表（可选，无 content 时拼接）
        rag_sources: 生成时使用的 RAG 来源（可选；带 content 字段时优先使用）
        subject: 学科（可选，用于检索）

    输出:
        {"passed": bool, "confidence": float(0-100),
         "issues": [{"level","item","detail"}], "reason": str,
         "sources_checked": int, "model_used": str, "elapsed": float}
    """

    # 与 Verifier 一致：error 级 issue 强制判定失败
    def __init__(self, model_name: Optional[str] = None,
                 timeout: int = 60, threshold: float = 60.0,
                 use_model: bool = False, top_k: int = 3):
        """
        参数：
            model_name: 辅助校验模型（默认轻量模型）
            timeout: 模型调用超时
            threshold: 置信度阈值（低于则判定未通过）
            use_model: 是否调用模型辅助校验（False 时仅规则检查，默认）
            top_k: 自查 RAG 来源条数
        """
        self.model_name = model_name or os.environ.get(
            "MULTI_AGENT_FACTCHECK_MODEL", "qwen2.5:7b")
        self.timeout = timeout
        self.threshold = threshold
        self.use_model = use_model
        self.top_k = top_k

    # ============================================================
    # 主入口
    # ============================================================
    def run(self, payload: Dict) -> Dict:
        t0 = time.time()
        topic = (payload.get("topic") or "").strip()
        if not topic:
            return {
                "passed": False, "confidence": 0.0,
                "issues": [{"level": "error", "item": "topic",
                            "detail": "缺少 topic 参数"}],
                "reason": "缺少必要参数", "sources_checked": 0,
                "model_used": "rule_based",
                "elapsed": round(time.time() - t0, 3),
            }

        content = (payload.get("teaching_content") or "").strip()
        steps = payload.get("steps") or payload.get("teaching_steps") or []
        if not content and isinstance(steps, list):
            content = " ".join(
                (s.get("content") or "") for s in steps if isinstance(s, dict)
            ).strip()

        if not content:
            return {
                "passed": False, "confidence": 0.0,
                "issues": [{"level": "error", "item": "content",
                            "detail": "教学内容为空，无法进行事实核查"}],
                "reason": "教学内容为空", "sources_checked": 0,
                "model_used": "rule_based",
                "elapsed": round(time.time() - t0, 3),
            }

        # ---------- 获取核对来源 ----------
        sources = self._collect_sources(payload, topic)
        sources_checked = len(sources)

        # 无来源 → 降级放行（不阻塞教学；标注供审计）
        if sources_checked == 0:
            return {
                "passed": True, "confidence": 100.0,
                "issues": [{"level": "info", "item": "rag",
                            "detail": "知识库无匹配来源，事实核查降级为仅规则检查"}],
                "reason": "无知识库来源可核对，降级放行", "sources_checked": 0,
                "model_used": "rule_based",
                "elapsed": round(time.time() - t0, 3),
            }

        issues: List[Dict] = []
        source_texts = [
            (s.get("content") or s.get("summary") or "").strip()
            for s in sources if isinstance(s, dict)
        ]
        source_texts = [t for t in source_texts if t]
        if not source_texts:
            return {
                "passed": True, "confidence": 100.0,
                "issues": [{"level": "info", "item": "rag",
                            "detail": "知识库来源无正文内容，事实核查降级"}],
                "reason": "来源无正文，降级放行", "sources_checked": 0,
                "model_used": "rule_based",
                "elapsed": round(time.time() - t0, 3),
            }

        # 1. 主题覆盖：主题核心词被来源覆盖的比例
        coverage = self._check_topic_coverage(topic, source_texts)
        if coverage < 0.5:
            issues.append({
                "level": "warn", "item": "coverage",
                "detail": f"知识库来源对主题「{topic}」覆盖不足（{coverage * 100:.0f}%），"
                          f"内容可能超出知识库范围",
            })

        # 2. 声明一致性：内容与来源的句子级重叠
        overlap = self._sentence_overlap(content, source_texts)
        if overlap < 0.1:
            issues.append({
                "level": "warn", "item": "consistency",
                "detail": f"内容与知识库来源关联度低（重叠 {overlap * 100:.0f}%），"
                          f"存在幻觉/无关内容风险",
            })

        # 3. 数值矛盾：内容中的「数值+单位」与来源冲突（硬性失败）
        contradictions = self._check_numeric_contradiction(content, source_texts)
        for num, unit, src_num, src_unit in contradictions:
            issues.append({
                "level": "error", "item": "contradiction",
                "detail": f"数值与知识库来源矛盾：内容「{num}{unit}」"
                          f"vs 来源「{src_num}{src_unit}」",
            })

        # 4. 模型辅助校验（可选）
        model_issue = None
        if self.use_model:
            model_issue = self._model_verify(payload, content, sources)
            if model_issue:
                issues.append(model_issue)

        # 计算置信度
        confidence = self._calc_confidence(coverage, overlap, issues)

        has_fatal = any(i.get("level") == "error" for i in issues)
        passed = confidence >= self.threshold and not has_fatal

        elapsed = round(time.time() - t0, 3)
        return {
            "passed": passed,
            "confidence": round(confidence, 1),
            "issues": issues,
            "reason": "事实核查通过，内容与知识库来源一致" if passed else
                      f"事实核查未通过（置信度 {confidence:.0f}%），存在与知识库来源矛盾的内容",
            "sources_checked": sources_checked,
            "model_used": self.model_name if self.use_model else "rule_based",
            "elapsed": elapsed,
            "checks": {
                "topic_coverage": round(coverage, 3),
                "sentence_overlap": round(overlap, 3),
                "contradictions": len(contradictions),
            },
        }

    # ============================================================
    # 各检查项
    # ============================================================
    def _collect_sources(self, payload: Dict, topic: str) -> List[Dict]:
        """收集核对来源：优先使用 payload 提供的（含 content），否则自行检索"""
        sources = payload.get("rag_sources") or []
        if isinstance(sources, list) and sources:
            # 使用带正文的来源；仅有元数据（无 content）时丢弃，避免误判
            with_content = [
                s for s in sources
                if isinstance(s, dict) and (s.get("content") or s.get("summary"))
            ]
            if with_content:
                return with_content
        try:
            from framework.services.knowledge_retrieval import (
                get_knowledge_retriever)
            retriever = get_knowledge_retriever()
            return retriever.search(
                topic, top_k=self.top_k,
                subject=payload.get("subject", "") or None) or []
        except Exception:
            return []

    def _check_topic_coverage(self, topic: str, source_texts: List[str]) -> float:
        """主题核心词被来源覆盖的比例（0-1）"""
        core = self._extract_core_words(topic)
        if not core:
            return 1.0
        joined = " ".join(source_texts)
        hit = sum(1 for w in core if w and w in joined)
        return hit / len(core)

    def _sentence_overlap(self, content: str, source_texts: List[str]) -> float:
        """内容句子与来源句子的平均 2-gram 重叠度（0-1）"""
        source_sents = []
        for t in source_texts:
            source_sents.extend(
                s.strip() for s in _SENT_SPLIT_RE.split(t) if len(s.strip()) >= 6)
        if not source_sents:
            return 0.0
        src_grams = [self._bigrams(s) for s in source_sents]
        content_sents = [
            s.strip() for s in _SENT_SPLIT_RE.split(content) if len(s.strip()) >= 6]
        if not content_sents:
            return 0.0

        scores = []
        for cs in content_sents:
            cg = self._bigrams(cs)
            if not cg:
                continue
            best = 0.0
            for sg in src_grams:
                if not sg:
                    continue
                inter = len(cg & sg)
                union = len(cg | sg)
                if union:
                    best = max(best, inter / union)
            scores.append(best)
        return sum(scores) / len(scores) if scores else 0.0

    def _check_numeric_contradiction(
            self, content: str,
            source_texts: List[str]) -> List[Tuple[str, str, str, str]]:
        """提取内容与来源中的「数值+单位」对，返回单位相同但数值不同的矛盾"""
        # 仅比较带单位的对：无单位裸数字（如"第5步""3个"）语义歧义大，跳过避免误报
        c_pairs = [(n, u) for n, u in self._extract_number_pairs(content) if u]
        s_pairs = [(n, u) for n, u in self._extract_number_pairs(" ".join(source_texts)) if u]
        if not c_pairs or not s_pairs:
            return []

        by_unit: Dict[str, List[str]] = {}
        for num, unit in s_pairs:
            by_unit.setdefault(unit, []).append(num)

        contradictions = []
        for num, unit in c_pairs:
            cands = by_unit.get(unit, [])
            for src_num in cands:
                if num == src_num:
                    continue
                # 相对差异 > 5% 视为矛盾（容忍舍入/近似差异）
                try:
                    a, b = float(num), float(src_num)
                except ValueError:
                    continue
                if a == 0 or b == 0:
                    continue
                if abs(a - b) / max(abs(a), abs(b)) > 0.05:
                    contradictions.append((num, unit, src_num, unit))
        return contradictions

    # ============================================================
    # 辅助
    # ============================================================
    def _extract_number_pairs(self, text: str) -> List[Tuple[str, str]]:
        """提取「数值, 单位」对（单位可为空串）"""
        pairs = []
        for m in _NUM_RE.finditer(text):
            num = m.group(1)
            unit = (m.group(2) or "").strip()
            if num is None:
                continue
            # 过滤明显非事实性数字（年份/序号等单独出现不带单位时跳过）
            pairs.append((num, unit))
        return pairs

    def _extract_core_words(self, topic: str) -> List[str]:
        """从主题提取核心词（与 Verifier 保持一致的轻量逻辑）"""
        if not topic:
            return []
        stopwords = {"什么", "为什么", "如何", "怎么", "的", "是", "了", "和",
                     "与", "吗", "呢", "请", "解释", "一下", "简述", "分析",
                     "推导", "证明", "比较", "评价"}
        return [w for w in topic.replace(" ", "") if w not in stopwords]

    @staticmethod
    def _bigrams(text: str) -> set:
        """中文/混合文本 2-gram（与检索器 tokenize 风格一致的轻量方案）"""
        han = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text)
        if len(han) <= 1:
            return {han} if han else set()
        return {han[i:i + 2] for i in range(len(han) - 1)}

    def _calc_confidence(self, coverage: float, overlap: float,
                         issues: List[Dict]) -> float:
        """根据检查结果计算置信度"""
        conf = 100.0
        if coverage < 0.5:
            conf -= 10
        if overlap < 0.1:
            conf -= 15
        for i in issues:
            if i.get("level") == "error":
                conf -= 40 if i.get("item") != "model" else 30
        if any(i.get("level") == "error" and i.get("item") == "contradiction"
               for i in issues):
            conf = min(conf, 30.0)  # 数值矛盾 → 硬性压低
        return max(0.0, conf)

    def _model_verify(self, payload: Dict, content: str,
                      sources: List[Dict]) -> Optional[Dict]:
        """模型辅助校验：内容 vs 来源是否一致"""
        try:
            from framework.services.knowledge_retrieval import format_rag_context
            model = get_model(self.model_name)
            if not model:
                return None
            rag_ctx = format_rag_context(sources, max_chars=1000)
            prompt = (
                f"你是事实核查员。请核对以下教学内容是否与知识库参考资料矛盾。\n\n"
                f"知识库参考资料:\n{rag_ctx}\n\n"
                f"教学内容:\n{content[:1200]}\n\n"
                f"请只回复 PASS 或 FAIL，若 FAIL 请说明具体矛盾点。"
            )
            raw = model.call(prompt, timeout=self.timeout)
            if not raw or raw.startswith("["):
                return None
            if "FAIL" in raw.upper() and "PASS" not in raw.upper():
                return {"level": "error", "item": "model",
                        "detail": f"模型判定内容与知识库矛盾: {raw[:100]}"}
        except Exception:
            pass
        return None


# ================================================================
# 单例
# ================================================================
_fact_checker_instance: Optional[FactCheckerAgent] = None


def get_fact_checker_agent(**kwargs) -> FactCheckerAgent:
    """获取 FactChecker Agent 单例（可传参覆盖默认配置）"""
    global _fact_checker_instance
    if _fact_checker_instance is None:
        _fact_checker_instance = FactCheckerAgent(**kwargs)
    return _fact_checker_instance


def fact_check(payload: Dict, **kwargs) -> Dict:
    """一行调用 FactChecker Agent"""
    return get_fact_checker_agent(**kwargs).run(payload)


if __name__ == "__main__":
    demo = {
        "topic": "重力加速度",
        "teaching_content": "重力加速度在地球表面约为 9.8 m/s²。"
                            "自由落体运动是初速度为零、只受重力的运动。"
                            "常见误区：误以为质量大的物体下落更快。",
        "rag_sources": [
            {"source": "training_data", "id": 1, "title": "自由落体",
             "content": "重力加速度约为 9.8 m/s²。自由落体：初速度为零，"
                        "仅受重力作用，下落快慢与质量无关。"},
        ],
    }
    result = get_fact_checker_agent().run(demo)
    print(f"通过: {result['passed']}")
    print(f"置信度: {result['confidence']}%")
    print(f"核对来源: {result['sources_checked']} 条")
    print(f"原因: {result['reason']}")
    if result["issues"]:
        print("问题清单:")
        for i in result["issues"]:
            print(f"  [{i['level']}] {i['item']}: {i['detail']}")
