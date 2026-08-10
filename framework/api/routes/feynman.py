# -*- coding: utf-8 -*-
"""
灵学 lumilearn - 费曼教学 API 路由
费曼讲解和30秒测试端点

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-02
"""

import logging
from flask import Blueprint, request, jsonify

from framework.engines.feynman_engine import FeynmanEngine, quick_explain, quick_test
from framework.services.feynman_animation_bridge import get_animation_for_feynman

logger = logging.getLogger("lumilearn.routes.feynman")

feynman_bp = Blueprint("feynman", __name__)

VALID_LEVELS = {"junior", "senior", "college", "general"}


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

    try:
        engine = FeynmanEngine(model_name=model)
        result = engine.explain(topic.strip(), level)

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

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"费曼讲解失败: {e}")
        return jsonify({"error": f"费曼讲解失败: {str(e)}"}), 500


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
        return jsonify({"error": f"费曼测试失败: {str(e)}"}), 500