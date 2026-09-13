# -*- coding: utf-8 -*-
"""
灵学 lumilearn - 费曼教学 API 路由
费曼讲解和30秒测试端点

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-02
"""

import logging
import os
import re
import time
from datetime import datetime

import requests
from flask import Blueprint, jsonify, request

from framework.database import db
from framework.engines.feynman_engine import FeynmanEngine
from framework.engines.feynman_templates import get_template
from framework.services.feynman_animation_bridge import get_animation_for_feynman
from framework.services.agent_classroom import AgentClassroom
from framework.services.review_service import get_review_service

logger = logging.getLogger("lumilearn.routes.feynman")

feynman_bp = Blueprint("feynman", __name__)

VALID_LEVELS = {"junior", "senior", "college", "general"}

# 讲解内容审查阈值（与幻灯片链路同一口径）：overall 与费曼度任一项低于阈值即判定
# 不合格，降级到模板讲解。overall==0 视为「审查不可用」，放行不误杀。
REVIEW_OVERALL_THRESHOLD = float(os.getenv("FEYNMAN_REVIEW_OVERALL_THRESHOLD", "6.0"))
REVIEW_FEYNMAN_THRESHOLD = float(os.getenv("FEYNMAN_REVIEW_FEYNMAN_THRESHOLD", "5.0"))

# ---------------------------------------------------------------------------
# 模块级缓存（explain / classroom 结果，TTL 3600s）
# ---------------------------------------------------------------------------
_result_cache: dict = {}
_RESULT_CACHE_TTL = 3600  # 1 小时


def _cache_get(cache_key: str) -> dict:
    """从缓存获取结果，过期则返回 None"""
    entry = _result_cache.get(cache_key)
    if entry is None:
        return None
    if time.time() - entry["ts"] > _RESULT_CACHE_TTL:
        _result_cache.pop(cache_key, None)
        return None
    return entry["data"]


def _cache_set(cache_key: str, data: dict) -> None:
    """写入缓存"""
    _result_cache[cache_key] = {"data": data, "ts": time.time()}
    # 限制缓存大小，防止内存无限增长
    if len(_result_cache) > 200:
        oldest = min(_result_cache, key=lambda k: _result_cache[k]["ts"])
        _result_cache.pop(oldest)


_OLLAMA_PING_CACHE = {}
_OLLAMA_PING_TTL = 10  # 10 秒内不重复检测


def _is_ollama_available() -> bool:
    """快速检测 Ollama 是否可连接（< 1s），结果缓存 10s。"""
    now = time.time()
    for key, (ts, val) in _OLLAMA_PING_CACHE.items():
        if now - ts < _OLLAMA_PING_TTL:
            return val
    try:
        base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        r = requests.get(f"{base}/api/tags", timeout=1)
        ok = r.status_code == 200
    except Exception:
        ok = False
    _OLLAMA_PING_CACHE.clear()
    _OLLAMA_PING_CACHE[("ok",)] = (now, ok)
    return ok


def _build_template_explain(topic: str, level: str) -> dict:
    """Ollama 不可用时，用模板快速生成五步费曼讲解（< 50ms）。"""
    t0 = time.time()
    engine = FeynmanEngine(model_name="template-fallback")
    subject, topic_type = engine._detect_subject_and_type(topic)

    steps_config = [
        ("phenomenon", "现象引入"),
        ("conflict", "认知冲突"),
        ("model", "思维模型"),
        ("derive", "自主推导"),
        ("test", "费曼测试"),
    ]

    steps = []
    for key, name in steps_config:
        content = get_template(subject, topic_type, key, topic)
        steps.append({
            "step_name": name,
            "step_order": steps_config.index((key, name)) + 1,
            "content": content.strip(),
            "key_points": [f"用模板模式讲解{topic}的{name}"],
            "animation_hint": engine._generate_animation_hint(name, topic, subject, topic_type),
        })

    full_content = "\n\n".join(
        f"【第{i+1}步：{s['step_name']}】\n{s['content']}"
        for i, s in enumerate(steps)
    )
    return {
        "topic": topic,
        "level": level,
        "subject": subject,
        "topic_type": topic_type,
        "steps": steps,
        "full_content": full_content,
        "model_used": "template-fallback",
        "mode": "template",
        "fallback_reason": "Ollama 服务不可用，已自动降级到模板模式",
        "total_time": round(time.time() - t0, 2),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _review_explain(result: dict, level: str, do_review: bool):
    """审查五步讲解内容，据此决定呈现还是降级。

    审查对象是「讲解内容的整体质量」，因此以去掉步骤标记后的合并正文为准。

    返回 (review_status, review_result)：
      - approved：达阈值，按原样呈现。
      - rejected：overall 或费曼度低于阈值，调用方降级到模板讲解。
      - skipped：请求关闭审查，或审查不可用（overall==0）时放行原结果，不误杀。
    """
    if not do_review:
        return "skipped", None

    text = (result or {}).get("full_content", "") or ""
    # 去掉【第N步：xxx】步骤标记，只留讲解正文
    text = re.sub(r"【[^】]*】", " ", text).strip()
    if not text:
        return "skipped", None

    try:
        review_result = get_review_service().review(
            text, student_level=level, mode="quick"
        )
    except Exception as e:  # 审查自身异常不阻断讲解
        logger.warning(f"费曼讲解内容审查异常，放行: {e}")
        return "skipped", None

    overall = review_result.get("overall", 0)
    # 审查不可用（模型失败/解析失败）：放行，不做误判
    if overall <= 0:
        return "skipped", review_result

    feynman = review_result.get("feynman_score", 0)
    if overall < REVIEW_OVERALL_THRESHOLD or feynman < REVIEW_FEYNMAN_THRESHOLD:
        logger.info(
            f"费曼讲解审查未达标(overall={overall}, feynman={feynman})，降级模板"
        )
        return "rejected", review_result

    return "approved", review_result


@feynman_bp.route("/api/feynman/explain", methods=["POST", "OPTIONS"])
def feynman_explain():
    """
    费曼五步教学讲解端点

    请求体（JSON）：
        {
            "topic": "勾股定理",
            "level": "junior" | "senior" | "college" | "general",
            "model": "qwen2.5:7b"
        }

    响应（JSON）：
        {
            "topic": "勾股定理",
            "level": "junior",
            "subject": "math",
            "topic_type": "geometry",
            "steps": [
                {
                    "step_name": "现象引入",
                    "step_order": 1,
                    "content": "...",
                    "key_points": [...]
                },
                ...
            ],
            "full_content": "合并后的完整讲解内容",
            "model_used": "qwen2.5:7b",
            "total_time": 12.5,
            "timestamp": "2026-06-02 12:00:00"
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "请求体为空，请提供JSON格式数据"}), 400

    topic = data.get("topic", "")
    if not topic or not topic.strip():
        return jsonify({"error": "缺少 topic 字段或内容为空"}), 400

    level = data.get("level", "junior")
    if level not in VALID_LEVELS:
        return jsonify({
            "error": f"不支持的学生水平: {level}，支持: {', '.join(sorted(VALID_LEVELS))}"
        }), 400

    model = data.get("model", "lumilearn-v2:latest")
    do_review = bool(data.get("review", True))

    # 检查缓存（缓存键含审查开关，避免未审查结果被审查请求命中）
    cache_key = f"explain:{topic.strip().lower()}:{level}:{model}:{int(do_review)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        cached["cached"] = True
        return jsonify(cached)

    # Ollama 离线时直接走模板，避免 5 步 × 8s 的无谓等待
    if not _is_ollama_available():
        logger.info("Ollama 未连接，explain 直接走模板模式")
        template_result = _build_template_explain(topic.strip(), level)
        _cache_set(cache_key, template_result)
        return jsonify(template_result)

    try:
        engine = FeynmanEngine(model_name=model)
        result = engine.explain(topic.strip(), level)

        # 内容审查：不达标的讲解不直接呈现给学生，降级到模板讲解
        review_status, review_result = _review_explain(
            result, level, do_review=do_review
        )
        review_score = review_result.get("overall") if review_result else None
        if review_status == "rejected":
            logger.info("费曼讲解审查未达标，降级到模板模式")
            result = _build_template_explain(topic.strip(), level)
            # 覆盖模板默认的降级原因，如实说明是审查未达标而非服务不可用
            result["fallback_reason"] = "生成内容审查未达标，已降级到模板讲解"

        # 检测费曼五步法教学，触发动画联动
        animation_info = get_animation_for_feynman(
            user_input=topic.strip(),
            response_text=result.get("full_content", ""),
            user_id=data.get("user_id", "default"),
        )

        response_data = {
            "topic": result["topic"],
            "level": result["level"],
            "subject": result["subject"],
            "topic_type": result["topic_type"],
            "steps": result["steps"],
            "full_content": result["full_content"],
            "model_used": result["model_used"],
            "total_time": result["total_time"],
            "timestamp": result["timestamp"],
        }

        if animation_info:
            response_data["animation"] = animation_info

        if review_status:
            response_data["review_status"] = review_status
            if review_score is not None:
                response_data["review_score"] = review_score
        if result.get("fallback_reason"):
            response_data["fallback_reason"] = result["fallback_reason"]

        # 写入缓存
        _cache_set(cache_key, response_data)

        # 推理过程写库（供管理员/教师查看用户真实使用记录；失败不影响主流程）
        try:
            db.init()
            steps_summary = "\n".join(
                f"{s.get('step_order', i+1)}.{s.get('step_name', '')}: {str(s.get('content', ''))[:150]}"
                for i, s in enumerate(result.get("steps", []))
            )[:4000]
            db.add_reasoning_log(
                user_id=data.get("user_id", 0) or 0,
                session_id=f"feynman:{topic.strip()[:50]}",
                mode="feynman_review_fallback" if review_status == "rejected" else "feynman",
                topic=topic.strip()[:200],
                step_order=0,
                step_name=f"五步讲解（共{len(result.get('steps', []))}步）",
                model_used=result.get("model_used", ""),
                input_context=f"学生水平: {level}；主题: {topic.strip()}",
                output=steps_summary,
                latency_ms=int(float(result.get("total_time", 0)) * 1000),
                status="success",
            )
        except Exception as _e:
            logger.warning(f"费曼讲解推理日志写库失败: {_e}")

        return jsonify(response_data)

    except Exception as e:
        logger.warning(f"Ollama 不可用，降级到模板模式: {e}")
        template_result = _build_template_explain(topic.strip(), level)
        try:
            db.init()
            steps_summary = "\n".join(
                f"{s.get('step_order', i+1)}.{s.get('step_name', '')}: {str(s.get('content', ''))[:150]}"
                for i, s in enumerate(template_result.get("steps", []))
            )[:4000]
            db.add_reasoning_log(
                user_id=data.get("user_id", 0) or 0,
                session_id=f"feynman:{topic.strip()[:50]}",
                mode="feynman_template_fallback",
                topic=topic.strip()[:200],
                step_order=0,
                step_name=f"五步讲解（模板降级，共{len(template_result.get('steps', []))}步）",
                model_used=template_result.get("model_used", ""),
                input_context=f"学生水平: {level}；主题: {topic.strip()}；原因: Ollama不可用",
                output=steps_summary,
                latency_ms=int(float(template_result.get("total_time", 0)) * 1000),
                status="success",
            )
        except Exception as _e:
            logger.warning(f"模板降级推理日志写库失败: {_e}")
        _cache_set(cache_key, template_result)
        return jsonify(template_result)


@feynman_bp.route("/api/feynman/test", methods=["POST", "OPTIONS"])
def feynman_test():
    """
    费曼30秒测试端点

    请求体（JSON）：
        {
            "concept": "勾股定理",
            "explanation": "学生用自己的话解释...",
            "model": "qwen2.5:7b"
        }

    响应（JSON）：
        {
            "score": 85,
            "dimensions": {
                "simplicity": {"score": 18, "comment": "..."},
                "accuracy": {"score": 17, "comment": "..."},
                "analogy": {"score": 16, "comment": "..."},
                "completeness": {"score": 15, "comment": "..."},
                "jargon_free": {"score": 19, "comment": "..."}
            },
            "feedback": "综合评语",
            "is_feynman_worthy": true,
            "model_used": "qwen2.5:7b"
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "请求体为空，请提供JSON格式数据"}), 400

    concept = data.get("concept", "")
    if not concept or not concept.strip():
        return jsonify({"error": "缺少 concept 字段或内容为空"}), 400

    explanation = data.get("explanation", "")
    if not explanation or not explanation.strip():
        return jsonify({"error": "缺少 explanation 字段或内容为空"}), 400

    model = data.get("model", "lumilearn-v2:latest")

    try:
        engine = FeynmanEngine(model_name=model)
        result = engine.thirty_second_test(concept.strip(), explanation.strip())

        return jsonify({
            "score": result["score"],
            "dimensions": result["dimensions"],
            "feedback": result["feedback"],
            "is_feynman_worthy": result["is_feynman_worthy"],
            "model_used": result["model_used"]
        })

    except Exception as e:
        logger.error(f"费曼测试失败: {e}")
        return jsonify({"error": "费曼测试失败，请稍后重试或联系管理员"}), 500


@feynman_bp.route("/api/feynman/classroom", methods=["POST", "OPTIONS"])
def feynman_classroom():
    """
    多智能体课堂对话端点

    请求体（JSON）：
        {
            "topic": "勾股定理",
            "level": "junior" | "senior" | "college" | "general",
            "knowledge_node": {"name": "勾股定理", "category": "math", "tags": ["几何", "证明"]},
            "max_turns": 5
        }

    响应（JSON）：
        {
            "topic": "勾股定理",
            "level": "junior",
            "dialogue": [
                {"role": "teacher", "content": "..."},
                {"role": "peer", "content": "..."},
                {"role": "ta", "content": "..."},
                ...
            ],
            "role_distribution": {"teacher": 3, "peer": 1, "ta": 1},
            "math_type": "math_proof",
            "whiteboard_svg": "...",
            "model_used": "lumilearn-v2:latest"
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "请求体为空，请提供JSON格式数据"}), 400

    topic = data.get("topic", "")
    if not topic or not topic.strip():
        return jsonify({"error": "缺少 topic 字段或内容为空"}), 400

    level = data.get("level", "junior")
    if level not in VALID_LEVELS:
        return jsonify({
            "error": f"不支持的学生水平: {level}，支持: {', '.join(sorted(VALID_LEVELS))}"
        }), 400

    knowledge_node = data.get("knowledge_node", {}) or {}
    max_turns = data.get("max_turns", 5)
    if not isinstance(max_turns, int) or max_turns < 1:
        max_turns = 5

    # 检查缓存
    cn_key = f"classroom:{topic.strip().lower()}:{level}:{max_turns}"
    cn_cached = _cache_get(cn_key)
    if cn_cached is not None:
        cn_cached["cached"] = True
        return jsonify(cn_cached)

    try:
        # 生成课堂对话
        classroom = AgentClassroom()
        dialogue = classroom.generate_classroom_dialogue(topic.strip(), knowledge_node, max_turns)

        # 计算角色分配
        role_distribution = classroom.distribute_speaking_roles(list(range(max_turns)))

        # 推断数学类型
        engine = FeynmanEngine(model_name=data.get("model", "lumilearn-v2:latest"))
        math_type = engine.detect_math_type(knowledge_node, topic.strip())

        # 白板数据（数学推导类）
        whiteboard_svg = None
        if math_type in ("math_calc", "math_proof"):
            from framework.services.whiteboard import WhiteboardEngine
            wb = WhiteboardEngine()
            whiteboard_svg = wb.generate_formula_svg(topic.strip(), [])

        response_data = {
            "topic": topic.strip(),
            "level": level,
            "dialogue": dialogue,
            "role_distribution": role_distribution,
            "math_type": math_type,
            "model_used": data.get("model", "lumilearn-v2:latest"),
        }

        if whiteboard_svg:
            response_data["whiteboard_svg"] = whiteboard_svg

        # 写入缓存
        _cache_set(cn_key, response_data)

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"多智能体课堂生成失败: {e}")
        return jsonify({"error": "课堂内容生成失败，请稍后重试或联系管理员"}), 500
