# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — Verifier Agent（质量验证 / 反馈回路核心）

职责：
  1. 检查教学内容的准确性（与 RAG 知识库对比、结构完整性）
  2. 检查评分的合理性（维度一致性、分数区间）
  3. 检查建议的可行性（与掌握度匹配）

输出：
  - passed:    是否通过验证
  - confidence: 置信度（0-100）
  - issues:    问题清单
  - reason:    结论说明

设计要点（对齐 Roadmap Phase 2.2）：
  - 使用与 FeynmanTeacher 相同的轻量模型（保持一致性，控制延迟）
  - 验证失败时返回具体原因，而非简单拒绝
  - 置信度低于阈值时自动标记需重试
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.model_registry import ALL_MODELS_DICT, get_model


class VerifierAgent:
    """
    质量验证 Agent — 反馈回路核心。

    输入 payload:
        topic: 教学主题
        teaching_content: 教学内容（用于内容质量检查）
        steps: 费曼五步步骤列表（可选）
        score: 评分（可选，用于一致性检查）
        dimensions: 五维评分（可选）
        mastery_level: 掌握等级（可选）
        suggestions: 学习建议（可选）
        rag_sources: RAG 来源（可选）

    输出:
        {"passed": bool, "confidence": float(0-100),
         "issues": [{"level","item","detail"}], "reason": str,
         "model_used": str, "elapsed": float}
    """

    # 检查项权重（用于置信度计算）
    CHECK_WEIGHTS = {
        "content": 0.40,    # 内容质量（最重要）
        "score": 0.25,      # 评分一致性
        "suggestion": 0.20, # 建议可行性
        "structure": 0.15,  # 结构完整性
    }

    def __init__(self, model_name: Optional[str] = None,
                 timeout: int = 60, threshold: float = 60.0,
                 use_model: bool = True):
        """
        参数：
            model_name: 验证模型（默认轻量模型）
            timeout: 模型调用超时
            threshold: 置信度阈值（低于则判定 fail）
            use_model: 是否调用模型（False 时仅规则检查，测试用）
        """
        self.model_name = model_name or os.environ.get(
            "MULTI_AGENT_VERIFIER_MODEL", "qwen2.5:7b")
        self.timeout = timeout
        self.threshold = threshold
        self.use_model = use_model

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
                "reason": "缺少必要参数", "model_used": "rule_based",
                "elapsed": round(time.time() - t0, 3),
            }

        issues: List[Dict] = []
        checks: Dict[str, bool] = {}

        # 1. 结构完整性检查
        checks["structure"], s_issues = self._check_structure(payload)
        issues.extend(s_issues)

        # 2. 内容质量检查
        checks["content"], c_issues = self._check_content(payload)
        issues.extend(c_issues)

        # 3. 评分一致性检查
        checks["score"], sc_issues = self._check_score(payload)
        issues.extend(sc_issues)

        # 4. 建议可行性检查
        checks["suggestion"], g_issues = self._check_suggestion(payload)
        issues.extend(g_issues)

        # 5. 模型辅助验证（可选，增强准确性）
        model_issue = None
        if self.use_model:
            model_issue = self._model_verify(payload)

        # 计算置信度
        confidence = self._calc_confidence(checks)

        # 若模型发现问题，置信度再降 15%
        if model_issue:
            issues.append(model_issue)
            confidence = max(0.0, confidence - 15.0)

        # 存在 error 级 issue → 强制判定失败（即使置信度达标）
        has_fatal = any(i.get("level") == "error" for i in issues)
        passed = confidence >= self.threshold and not has_fatal

        elapsed = round(time.time() - t0, 3)
        return {
            "passed": passed,
            "confidence": round(confidence, 1),
            "issues": issues,
            "reason": "验证通过，质量达标" if passed else
                      f"验证未通过（置信度 {confidence:.0f}% < 阈值 {self.threshold}%），需重新生成",
            "model_used": self.model_name if self.use_model else "rule_based",
            "elapsed": elapsed,
            "checks": checks,
        }

    # ============================================================
    # 各检查项
    # ============================================================
    def _check_structure(self, payload: Dict) -> tuple[bool, List[Dict]]:
        """结构完整性：费曼五步教学应包含步骤"""
        issues = []
        steps = payload.get("steps") or payload.get("teaching_steps") or []
        content = (payload.get("teaching_content") or "").strip()

        if steps and isinstance(steps, list):
            # 步骤数过少
            if len(steps) < 2:
                issues.append({
                    "level": "warn", "item": "structure",
                    "detail": f"教学步骤数偏少（{len(steps)}步），正常应为 5 步",
                })
            # 步骤内容缺失
            empty_steps = [s.get("step_name", f"步骤{i+1}")
                           for i, s in enumerate(steps)
                           if not (s.get("content") or "").strip()]
            if empty_steps:
                issues.append({
                    "level": "error", "item": "structure",
                    "detail": f"以下步骤内容为空: {', '.join(empty_steps[:3])}",
                })
            return len(issues) == 0, issues
        elif content:
            # 无步骤但有整体内容
            if len(content) < 80:
                issues.append({
                    "level": "warn", "item": "structure",
                    "detail": "教学内容过短（<80字），可能不够完整",
                })
            return True, issues
        else:
            issues.append({
                "level": "error", "item": "structure",
                "detail": "既无步骤也无教学内容",
            })
            return False, issues

    def _check_content(self, payload: Dict) -> tuple[bool, List[Dict]]:
        """内容质量：长度、关键词、RAG 一致性（仅 error 级判定失败）"""
        issues = []
        topic = payload.get("topic", "")
        content = (payload.get("teaching_content") or "")
        steps = payload.get("steps") or payload.get("teaching_steps") or []
        # 若 steps 有内容，拼接做内容检查
        if steps and not content:
            content = " ".join(
                (s.get("content") or "") for s in steps if isinstance(s, dict))

        if not content.strip():
            issues.append({"level": "error", "item": "content",
                           "detail": "教学内容为空"})
            return False, issues

        # 长度检查（warn 级别，不判定失败）
        if len(content) < 100:
            issues.append({"level": "warn", "item": "content",
                           "detail": f"内容偏短（{len(content)}字），建议补充示例和误区说明"})
        elif len(content) > 4000:
            issues.append({"level": "warn", "item": "content",
                           "detail": f"内容过长（{len(content)}字），建议精简"})

        # 主题关键词检查：主题中的核心词应出现在内容中
        core_words = self._extract_core_words(topic)
        missing = [w for w in core_words if w and w not in content and len(w) >= 2]
        if missing:
            issues.append({"level": "warn", "item": "content",
                           "detail": f"内容未覆盖主题关键词: {', '.join(missing[:3])}"})

        # RAG 一致性（若提供 sources）
        rag_sources = payload.get("rag_sources") or []
        if rag_sources:
            matched = sum(1 for s in rag_sources
                          if isinstance(s, dict) and s.get("source"))
            if matched < len(rag_sources) * 0.5:
                issues.append({"level": "info", "item": "content",
                               "detail": "RAG 引用较少，可补充知识库内容增强准确性"})

        # 致命错误词检测（error 级 → 判定失败）
        # 兼容两种格式：完整占位符 "[xxx 不可用]" 或模型错误输出 "xxx 不可用: ..."
        if content.strip().startswith("[") and content.strip().endswith("]"):
            issues.append({"level": "error", "item": "content",
                           "detail": "内容为模型错误占位符"})
            return False, issues
        for bad in ("不可用", "无API Key", "调用失败", "HTTP4", "HTTP5"):
            if bad in content:
                issues.append({"level": "error", "item": "content",
                               "detail": f"内容包含错误占位符: {bad}"})
                return False, issues

        # 仅 error 级 issue 判定失败
        has_error = any(i.get("level") == "error" for i in issues)
        return not has_error, issues

    def _check_score(self, payload: Dict) -> tuple[bool, List[Dict]]:
        """评分一致性：分数与维度、掌握度匹配"""
        issues = []
        score = payload.get("score")
        dimensions = payload.get("dimensions") or {}
        mastery = payload.get("mastery_level") or ""

        if score is None:
            return True, issues  # 未评分则不检查

        try:
            score = float(score)
        except (TypeError, ValueError):
            return True, issues

        # 分数区间
        if score < 0 or score > 100:
            issues.append({"level": "error", "item": "score",
                           "detail": f"评分超出范围: {score}"})
            return False, issues

        # 维度一致性：维度分均值应接近总分
        if dimensions:
            dim_scores = [float(v.get("score", 0)) for v in dimensions.values()
                          if isinstance(v, dict)]
            if dim_scores:
                dim_avg = sum(dim_scores) / len(dim_scores)
                if abs(dim_avg - score) > 20:
                    issues.append({
                        "level": "warn", "item": "score",
                        "detail": f"总分({score:.0f})与维度均值({dim_avg:.0f})偏差过大，评分可能不一致",
                    })

        # 掌握度与分数匹配
        if mastery:
            mismatch = (
                (mastery == "优秀" and score < 85) or
                (mastery == "良好" and not 70 <= score < 85) or
                (mastery == "一般" and not 50 <= score < 70) or
                (mastery == "待加强" and score >= 50)
            )
            if mismatch:
                issues.append({
                    "level": "warn", "item": "score",
                    "detail": f"掌握等级({mastery})与评分({score:.0f})不匹配",
                })

        return len(issues) == 0, issues

    def _check_suggestion(self, payload: Dict) -> tuple[bool, List[Dict]]:
        """建议可行性：建议数量与掌握度匹配"""
        issues = []
        suggestions = payload.get("suggestions") or []
        mastery = payload.get("mastery_level") or ""
        score = payload.get("score")

        if not suggestions:
            issues.append({"level": "warn", "item": "suggestion",
                           "detail": "缺少学习建议"})
            return False, issues

        if not isinstance(suggestions, list):
            issues.append({"level": "error", "item": "suggestion",
                           "detail": "suggestions 格式错误（应为列表）"})
            return False, issues

        # 高掌握度下建议仍存在 → 正常；低掌握度建议过少 → 提示
        if score is not None:
            try:
                score = float(score)
                if score < 50 and len(suggestions) < 2:
                    issues.append({
                        "level": "warn", "item": "suggestion",
                        "detail": "掌握度低但建议过少，建议补充复习路径和练习题",
                    })
            except (TypeError, ValueError):
                pass

        # 建议内容质量
        empty = [s for s in suggestions if not str(s).strip()]
        if empty:
            issues.append({"level": "warn", "item": "suggestion",
                           "detail": "存在空建议"})

        return len(issues) == 0, issues

    def _model_verify(self, payload: Dict) -> Optional[Dict]:
        """模型辅助验证：让轻量模型判断内容是否与主题相关"""
        topic = payload.get("topic", "")
        content = (payload.get("teaching_content") or "")[:800]
        if not content:
            return None
        try:
            model = get_model(self.model_name)
            if not model:
                return None
            prompt = (
                f"你是教学质量审核员。请判断以下教学内容是否与主题'{topic}'相关、"
                f"是否包含明显错误。\n\n"
                f"教学内容:\n{content}\n\n"
                f"请只回复 PASS 或 FAIL，若 FAIL 请说明原因。"
            )
            raw = model.call(prompt, timeout=self.timeout)
            if raw.startswith("[") or not raw:
                return None
            if "FAIL" in raw.upper() and "PASS" not in raw.upper():
                return {"level": "error", "item": "model",
                        "detail": f"模型判定内容需改进: {raw[:100]}"}
        except Exception:
            pass
        return None

    def _calc_confidence(self, checks: Dict[str, bool]) -> float:
        """根据各项检查结果计算置信度"""
        if not checks:
            return 0.0
        score = 0.0
        total = 0.0
        for key, weight in self.CHECK_WEIGHTS.items():
            total += weight
            if checks.get(key, False):
                score += weight
        # 结构/内容为硬性项：任一失败且权重占比高，则置信度大幅下降
        if not checks.get("content", False):
            score -= 0.3
        if not checks.get("structure", False):
            score -= 0.2
        return max(0.0, min(1.0, score / total)) * 100

    def _extract_core_words(self, topic: str) -> List[str]:
        """从主题提取核心关键词（用于内容覆盖检查）"""
        if not topic:
            return []
        # 过滤常见无意义词
        stopwords = {"什么", "为什么", "如何", "怎么", "的", "是", "了", "和",
                     "与", "吗", "呢", "请", "解释", "一下", "简述", "分析",
                     "推导", "证明", "比较", "评价"}
        return [w for w in topic.replace(" ", "") if w not in stopwords]


# ================================================================
# 人工复核判定（P0-1：Verifier 阶段人工中断扩展）
# ================================================================
# 置信度低于该值 → 判定需要人工复核（自动重生成轮次耗尽仍无法达标）
HUMAN_REVIEW_CONFIDENCE_THRESHOLD = 45.0
# 出现以下 error 级检查项 → 判定内容质量异常，需要人工复核
HUMAN_REVIEW_ISSUE_ITEMS = ("content", "structure", "model")


def evaluate_human_review(
    verify: Dict,
    confidence_threshold: float = HUMAN_REVIEW_CONFIDENCE_THRESHOLD,
) -> Dict:
    """
    判断 Verifier 验证结果是否需要人工复核（P0-1）。

    触发条件（验证未通过时满足其一）：
      1. 低置信度：confidence < confidence_threshold
         （多轮自动重生成后质量仍不达标，继续自动兜底收益有限）
      2. 内容质量异常：存在 content / structure / model 的 error 级问题
         （如教学内容为空、模型错误占位符、模型判定 FAIL 等）

    返回：
        {"needs_review": bool, "reason": str, "confidence": float,
         "trigger": str, "error_issues": [..]}
      trigger: "low_confidence" / "content_anomaly" / ""（不触发）
    """
    passed = bool(verify.get("passed", False))
    confidence = float(verify.get("confidence", 0.0) or 0.0)
    issues = verify.get("issues") or []
    error_issues = [
        i for i in issues
        if isinstance(i, dict) and i.get("level") == "error"
    ]
    content_anomaly = any(
        i.get("item") in HUMAN_REVIEW_ISSUE_ITEMS for i in error_issues)
    low_confidence = confidence < confidence_threshold

    if passed or not (low_confidence or content_anomaly):
        return {
            "needs_review": False,
            "reason": "",
            "confidence": round(confidence, 1),
            "trigger": "",
            "error_issues": [],
        }

    if low_confidence:
        trigger = "low_confidence"
        reason = (
            f"验证未通过且置信度过低（{confidence:.0f}% < 人工复核阈值 "
            f"{confidence_threshold:.0f}%），自动重生成无法保证内容质量"
        )
    else:
        trigger = "content_anomaly"
        details = [
            i.get("detail", i.get("item", "")) for i in error_issues
            if i.get("item") in HUMAN_REVIEW_ISSUE_ITEMS
        ]
        reason = f"内容质量异常：{'；'.join(details[:3])}，需人工审核"

    return {
        "needs_review": True,
        "reason": reason,
        "confidence": round(confidence, 1),
        "trigger": trigger,
        "error_issues": error_issues,
    }


# ================================================================
# 单例
# ================================================================
_verifier_instance: Optional[VerifierAgent] = None


def get_verifier_agent(**kwargs) -> VerifierAgent:
    """获取 Verifier Agent 单例（可传参覆盖默认配置）"""
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = VerifierAgent(**kwargs)
    return _verifier_instance


def verify_teaching(payload: Dict, **kwargs) -> Dict:
    """一行调用 Verifier Agent"""
    return get_verifier_agent(**kwargs).run(payload)


if __name__ == "__main__":
    demo = {
        "topic": "函数的单调性",
        "teaching_content": "函数的单调性是描述函数值随自变量变化趋势的性质。"
                            "增函数：自变量增大时函数值增大，像上坡路。"
                            "减函数：自变量增大时函数值减小，像下坡路。"
                            "判断方法：导数法、定义法。常见误区：混淆增区间与单调区间。",
        "steps": [
            {"step_name": "现象引入", "content": "爬山的上坡下坡就是单调性"},
            {"step_name": "思维模型", "content": "增函数减函数定义"},
            {"step_name": "自主推导", "content": "用定义证明"},
            {"step_name": "认知冲突", "content": "单调区间并集误区"},
            {"step_name": "费曼测试", "content": "用自己的话讲一遍"},
        ],
        "score": 85,
        "mastery_level": "优秀",
        "suggestions": ["已掌握，挑战进阶题", "举一反三"],
    }
    result = get_verifier_agent(use_model=False).run(demo)
    print(f"通过: {result['passed']}")
    print(f"置信度: {result['confidence']}%")
    print(f"原因: {result['reason']}")
    if result["issues"]:
        print("问题清单:")
        for i in result["issues"]:
            print(f"  [{i['level']}] {i['item']}: {i['detail']}")
