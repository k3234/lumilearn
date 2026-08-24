# -*- coding: utf-8 -*-
"""
LumiLearn 统一异常处理
======================
注册全局 404 / 500 错误处理器，供所有 Flask 应用复用：

- 404：API 请求（/api/ 前缀）→ 友好 JSON；页面请求 → 优先渲染 404.html，
       模板缺失时回退 JSON
- 500：记录错误日志并返回友好 JSON（不向客户端泄露堆栈）

用法：
    from framework.api.errors import register_error_handlers
    register_error_handlers(app)
"""

import logging

from flask import jsonify, render_template, request

from framework.security.sanitize import mask_query_string, sanitize_text

logger = logging.getLogger("lumilearn.errors")


def register_error_handlers(app):
    """为 Flask 应用注册统一 404 / 500 错误处理器（幂等，可重复调用）。"""

    @app.errorhandler(404)
    def _handle_not_found(e):  # noqa: ANN001 - Flask 传入 HTTPException
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "code": 404, "error": "资源不存在"}), 404
        try:
            return render_template("404.html"), 404
        except Exception:
            return jsonify({"success": False, "code": 404, "error": "资源不存在"}), 404

    @app.errorhandler(500)
    def _handle_internal_error(e):  # noqa: ANN001 - Flask 传入异常
        # 记录前脱敏：路径中的查询参数可能携带 token/key，异常信息可能内联凭据
        logger.error("服务器内部错误 %s %s: %s",
                     request.method, mask_query_string(request.path),
                     sanitize_text(str(e)), exc_info=True)
        return jsonify({"success": False, "code": 500, "error": "服务器内部错误，请稍后重试"}), 500

    return app
