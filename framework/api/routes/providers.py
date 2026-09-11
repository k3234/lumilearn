#!/usr/bin/env python3
"""
灵学 lumilearn - 提供者 API 路由
只读的模型提供者列表（不返回任何明文 api_key）
"""
import logging

from flask import Blueprint, jsonify, request

logger = logging.getLogger("lumilearn.routes.providers")

providers_bp = Blueprint("providers", __name__)


@providers_bp.route("/api/providers", methods=["GET", "OPTIONS"])
def list_providers():
    """获取所有模型提供者列表（只读，绝不返回明文 api_key）。

    提供者的增删改由管理员接口 /api/admin/providers 负责；本接口仅暴露非敏感
    摘要字段（key/name/base_url/enabled/has_api_key/protocol/local/models），
    供前端展示与模型选择使用。api_key 只以布尔 has_api_key 呈现。
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    from framework.services.provider_service import get_provider_service
    ps = get_provider_service()
    # list_providers() 已剥离明文 Key，仅保留 has_api_key 布尔值
    return jsonify({
        "status": "success",
        "providers": ps.list_providers(),
        "templates": ps.get_available_templates(),
    })
