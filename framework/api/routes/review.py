# -*- coding: utf-8 -*-
"""
灵学 lumilearn - Review API 路由
讲解内容审查端点：提交讲解内容，返回多维度质量评分和改进建议

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-02
"""

import logging
from flask import Blueprint, request, jsonify

from framework.services.review_service import get_review_service

logger = logging.getLogger("lumilearn.routes.review")

review_bp = Blueprint("review", __name__)

VALID_MODES = {"quick", "full", "strict"}
VALID_LEVELS = {"junior", "senior", "college", "general"}


@review_bp.route("/api/review", methods=["POST", "OPTIONS"])
def review():
    """
    讲解内容审查端点

    请求体（JSON）：
        {
            "content": "讲解内容文本",
            "mode": "quick" | "full" | "strict",
            "student_level": "junior" | "senior" | "college" | "general"
        }

    响应（JSON）：
        {
            "scores": {
                "accuracy": 8,
                "completeness": 7,
                "guidance": 6,
                "difficulty_fit": 8
            },
            "total_score": 7.5,
            "dimensions": {...},
            "suggestions": [...],
            "summary": "...",
            "mode": "full",
            "student_level": "junior",
            "model": "qwen2.5:7b"
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "请求体为空，请提供JSON格式数据"}), 400

    content = data.get("content", "")
    if not content or not content.strip():
        return jsonify({"error": "缺少 content 字段或内容为空"}), 400

    mode = data.get("mode", "full")
    student_level = data.get("student_level", "junior")

    if mode not in VALID_MODES:
        return jsonify({
            "error": f"不支持的审查模式: {mode}，支持: {', '.join(sorted(VALID_MODES))}"
        }), 400

    if student_level not in VALID_LEVELS:
        return jsonify({
            "error": f"不支持的学生水平: {student_level}，支持: {', '.join(sorted(VALID_LEVELS))}"
        }), 400

    try:
        review_service = get_review_service()
        result = review_service.review(content, student_level=student_level,
                                       mode=mode)

        return jsonify({
            "scores": {
                "accuracy": result.get("accuracy", 0),
                "completeness": result.get("completeness", 0),
                "guidance": result.get("guidance", 0),
                "difficulty_fit": result.get("difficulty_fit", 0)
            },
            "total_score": result.get("overall", 0),
            "dimensions": {
                "accuracy": {"score": result.get("accuracy", 0)},
                "completeness": {"score": result.get("completeness", 0)},
                "guidance": {"score": result.get("guidance", 0)},
                "difficulty": {"score": result.get("difficulty_fit", 0)}
            },
            "suggestions": result.get("suggestions", []),
            "summary": result.get("summary", ""),
            "mode": mode,
            "student_level": student_level,
            "model": result.get("model", "")
        })

    except Exception as e:
        logger.error(f"审查失败: {e}")
        return jsonify({"error": f"审查失败: {str(e)}"}), 500


@review_bp.route("/api/review/stats", methods=["GET", "OPTIONS"])
def review_stats():
    """获取审查统计信息"""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    try:
        review_service = get_review_service()
        stats = review_service.get_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500