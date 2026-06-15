# -*- coding: utf-8 -*-
"""
灵学 lumilearn - Resources API 路由
学习资源搜索端点：提交查询关键词和分类，返回搜索资源和AI摘要

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-02
"""

import logging
from flask import Blueprint, request, jsonify

from framework.services.resource_service import get_resource_service, CATEGORIES

logger = logging.getLogger("lumilearn.routes.resources")

resources_bp = Blueprint("resources", __name__)


@resources_bp.route("/api/resources", methods=["POST", "OPTIONS"])
def resources():
    """
    学习资源搜索端点

    请求体（JSON）：
        {
            "keyword": "搜索关键词",
            "category": "math" | "english" | "physics" | "chinese" | "general",
            "max_results": 5,
            "include_summary": true
        }

    响应（JSON）：
        {
            "resources": [{"title": "...", "url": "...", "summary": "..."}, ...],
            "rag_summary": "AI生成的摘要",
            "source": "web" | "preset"
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "请求体为空，请提供JSON格式数据"}), 400

    query = data.get("keyword", data.get("query", ""))
    if not query or not query.strip():
        return jsonify({"error": "缺少 keyword 字段或内容为空"}), 400

    category = data.get("category", "general")
    if category not in CATEGORIES:
        return jsonify({
            "error": f"不支持的分类: {category}，支持: {', '.join(CATEGORIES)}"
        }), 400

    max_results = data.get("max_results", 5)
    if not isinstance(max_results, int) or max_results < 1 or max_results > 10:
        return jsonify({"error": "max_results 必须为 1-10 的整数"}), 400

    include_summary = data.get("include_summary", True)

    try:
        resource_service = get_resource_service()
        if include_summary:
            result = resource_service.search_with_summary(
                query.strip(), category=category, max_results=max_results
            )
            return jsonify({
                "resources": result["resources"],
                "rag_summary": result["summary"]["summary"],
                "source": "web" if result["resources"] else "preset"
            })
        else:
            resources_list = resource_service.search(
                query.strip(), category=category, max_results=max_results
            )
            return jsonify({
                "resources": resources_list,
                "source": "web" if resources_list else "preset"
            })

    except Exception as e:
        logger.error(f"资源搜索失败: {e}")
        return jsonify({"error": f"资源搜索失败: {str(e)}"}), 500