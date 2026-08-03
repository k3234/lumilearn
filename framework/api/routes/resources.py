#!/usr/bin/env python3
"""
灵学 lumilearn - 资源 API 路由
学习资源管理端点
"""
import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger("lumilearn.routes.resources")

resources_bp = Blueprint("resources", __name__)


@resources_bp.route("/api/resources", methods=["GET", "OPTIONS"])
def list_resources():
    """
    获取资源列表
    
    查询参数：
        subject: 学科筛选
        type: 资源类型筛选
        page: 页码
        per_page: 每页数量
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    
    subject = request.args.get("subject")
    resource_type = request.args.get("type")
    
    # TODO: 实现资源列表逻辑
    return jsonify({
        "status": "success",
        "resources": [],
        "total": 0
    })


@resources_bp.route("/api/resources/<resource_id>", methods=["GET", "OPTIONS"])
def get_resource(resource_id):
    """
    获取单个资源详情
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    
    # TODO: 实现资源详情逻辑
    return jsonify({
        "status": "success",
        "resource": None
    })


@resources_bp.route("/api/resources", methods=["POST", "OPTIONS"])
def create_resource():
    """
    创建资源
    
    请求体（JSON）:
        {
            "title": "资源标题",
            "content": "资源内容",
            "subject": "math",
            "type": "note"
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "请求体为空"}), 400
    
    # TODO: 实现资源创建逻辑
    return jsonify({
        "status": "success",
        "message": "资源创建功能开发中"
    })
