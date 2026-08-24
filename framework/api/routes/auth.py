# -*- coding: utf-8 -*-
"""
LumiLearn 账号认证路由（users 表）
==================================
供框架端口（18080 终端 / 18081 REST API / 18082 模型管理）使用账号登录：

    POST /api/auth/login   { username, password } → { token, user }
    GET  /api/auth/me      头 X-Auth-Token → { user }
    POST /api/auth/logout  头 X-Auth-Token → 注销 token

采用轻量内存 token（服务重启后失效），不引入额外依赖；
与 student_portal / teacher_portal 的 users 表登录保持同一套账号。
"""
import logging
import secrets
import threading
from datetime import datetime

from flask import Blueprint, jsonify, request

from framework.database import db

logger = logging.getLogger("lumilearn.routes.auth")

auth_bp = Blueprint("auth", __name__)

# 内存 token 表：{token: {"user_id": int, "username": str, "created_at": str}}
_TOKENS = {}
_TOKENS_LOCK = threading.Lock()
TOKEN_TTL_SECONDS = 12 * 3600  # 12 小时有效


def _issue_token(user) -> str:
    token = secrets.token_hex(24)
    with _TOKENS_LOCK:
        _TOKENS[token] = {
            "user_id": user["id"],
            "username": user.get("username") or user["name"],
            "role": user.get("role", "user"),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    return token


def get_user_by_token(token: str):
    """供其他路由解析当前登录用户（未登录返回 None）"""
    if not token:
        return None
    with _TOKENS_LOCK:
        entry = _TOKENS.get(token)
    if not entry:
        return None
    return db.get_user(entry["user_id"])


def require_user_token():
    """从请求头解析当前用户（X-Auth-Token / Authorization: Bearer）"""
    token = request.headers.get("X-Auth-Token", "")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[len("Bearer "):]
    return get_user_by_token(token)


@auth_bp.route("/api/auth/login", methods=["POST", "OPTIONS"])
def api_auth_login():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "请输入用户名和密码"}), 400
    user = db.verify_user_login(username, password)
    if not user:
        return jsonify({"error": "用户名或密码错误"}), 401
    token = _issue_token(user)
    return jsonify({
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "username": user.get("username") or user["name"],
            "role": user.get("role", "user"),
        },
    })


@auth_bp.route("/api/auth/me", methods=["GET", "OPTIONS"])
def api_auth_me():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    user = require_user_token()
    if not user:
        return jsonify({"error": "未登录"}), 401
    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "username": user.get("username") or user["name"],
            "role": user.get("role", "user"),
        },
    })


@auth_bp.route("/api/auth/logout", methods=["POST", "OPTIONS"])
def api_auth_logout():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    token = request.headers.get("X-Auth-Token", "")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[len("Bearer "):]
    with _TOKENS_LOCK:
        _TOKENS.pop(token, None)
    return jsonify({"success": True, "message": "已退出登录"})
