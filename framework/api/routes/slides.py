# -*- coding: utf-8 -*-
"""
LumiLearn - Slides API 路由
提供幻灯片生成端点

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-07
"""

import json
import logging
import sys
from pathlib import Path
from flask import Blueprint, request, jsonify

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from smart_reply_engine import generate_slides

logger = logging.getLogger("lumilearn.routes.slides")

slides_bp = Blueprint("slides", __name__)


@slides_bp.route("/api/slides/generate", methods=["POST", "OPTIONS"])
def slides_generate():
    """
    幻灯片生成API端点

    请求体（JSON）：
        {
            "topic": "勾股定理",
            "slide_count": 5,
            "style": "detailed"
        }

    响应：
        {
            "slides": [
                {
                    "title": "...",
                    "subtitle": "...",
                    "content": "...",
                    "katex": "..."
                }
            ]
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json(force=True)
    topic = data.get("topic", "")
    slide_count = data.get("slide_count", 5)
    style = data.get("style", "detailed")

    if not topic:
        return jsonify({"error": "缺少 topic 字段"}), 400

    if not isinstance(slide_count, int) or slide_count < 1 or slide_count > 20:
        return jsonify({"error": "slide_count 必须在 1-20 之间"}), 400

    if style not in ("detailed", "concise", "outline"):
        return jsonify({"error": "style 必须是 detailed, concise 或 outline"}), 400

    try:
        slides = generate_slides(topic, slide_count=slide_count, style=style)
        return jsonify({"slides": slides})
    except Exception as e:
        logger.error(f"幻灯片生成失败: {e}")
        return jsonify({"error": f"幻灯片生成失败: {str(e)}"}), 500