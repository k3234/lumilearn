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
import time
from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, request, session

from framework.admin.auth import get_admin_auth
from framework.database import db

logger = logging.getLogger("lumilearn.routes.auth")

auth_bp = Blueprint("auth", __name__)

# 内存 token 表：{token: {"user_id", "username", "role", "created_at", "expires_at"}}
_TOKENS = {}
_TOKENS_LOCK = threading.Lock()
TOKEN_TTL_SECONDS = 12 * 3600  # 12 小时有效

# 登录暴力破解防护：同一 IP+用户名 连续失败 N 次后锁定
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCK_SECONDS = 900  # 15 分钟
_login_failures = {}
_login_failures_lock = threading.Lock()


def _client_ip() -> str:
    """获取客户端 IP（无请求上下文时返回 'unknown'，保证可测试）"""
    try:
        return request.remote_addr or "unknown"
    except Exception:
        return "unknown"


def _login_lock_check(username: str):
    """登录锁定检查；处于锁定期返回 (剩余秒数)，否则 None"""
    key = f"{_client_ip()}|{username}"
    with _login_failures_lock:
        rec = _login_failures.get(key)
        if rec and rec.get("lock_until", 0) > time.time():
            return int(rec["lock_until"] - time.time())
    return None


def _record_login_failure(username: str):
    """记录一次登录失败；达到阈值则触发锁定"""
    key = f"{_client_ip()}|{username}"
    with _login_failures_lock:
        rec = _login_failures.get(key) or {"count": 0, "lock_until": 0}
        if rec["lock_until"] > time.time():
            return  # 已处于锁定中，不再叠加
        rec["count"] += 1
        if rec["count"] >= LOGIN_MAX_ATTEMPTS:
            rec["lock_until"] = time.time() + LOGIN_LOCK_SECONDS
            rec["count"] = 0
        _login_failures[key] = rec


def _clear_login_failures(username: str):
    """登录成功后清除失败记录"""
    key = f"{_client_ip()}|{username}"
    with _login_failures_lock:
        _login_failures.pop(key, None)


def _issue_token(user) -> str:
    token = secrets.token_hex(24)
    with _TOKENS_LOCK:
        _TOKENS[token] = {
            "user_id": user["id"],
            "username": user.get("username") or user["name"],
            "role": user.get("role", "user"),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at": time.time() + TOKEN_TTL_SECONDS,
        }
    return token


def get_user_by_token(token: str):
    """供其他路由解析当前登录用户（未登录/已过期返回 None）"""
    if not token:
        return None
    with _TOKENS_LOCK:
        entry = _TOKENS.get(token)
        # Token 过期检查：定义 TTL 后必须真正执行，否则 token 永不过期
        if entry and entry.get("expires_at", 0) < time.time():
            _TOKENS.pop(token, None)
            entry = None
    if not entry:
        return None
    return db.get_user(entry["user_id"])


def require_user_token():
    """从请求头解析当前用户（X-Auth-Token / Authorization: Bearer），回退 cookie 会话"""
    token = request.headers.get("X-Auth-Token", "")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[len("Bearer "):]
    user = get_user_by_token(token)
    if user:
        return user
    # 回退：cookie 会话（teacher/student 门户复用同一 session）
    uid = session.get("user_id")
    if uid:
        return db.get_user(uid)
    return None


def require_role(*roles):
    """角色守卫装饰器：需登录且角色在 roles 中。

    - 未登录 → 返回 401（统一契约 {code: 401, error, message}）
    - 角色不符 → 返回 403（统一契约 {code: 403, error, message}）
    内部调用 require_user_token()，支持 token / cookie 会话双凭据。
    用法：@auth_bp.route(...); @require_role("teacher", "admin")。
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = require_user_token()
            if not user:
                return jsonify({"error": "未登录", "code": 401, "message": "未登录"}), 401
            role = user.get("role", "user")
            if role not in roles:
                return jsonify({"error": "无权限访问", "code": 403, "message": "无权限访问"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def current_user():
    """便捷返回当前登录用户（未登录返回 None），供控制器内直接使用。"""
    return require_user_token()


@auth_bp.route("/api/auth/login", methods=["POST", "OPTIONS"])
def api_auth_login():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "请输入用户名和密码"}), 400

    # 暴力破解防护：锁定期内直接拒绝
    remain = _login_lock_check(username)
    if remain:
        return jsonify({"error": f"登录失败次数过多，已锁定 {remain} 秒，请稍后再试"}), 429

    user = db.verify_user_login(username, password)
    if not user:
        # 兼容管理员账号：admins 表独立认证。
        # 修复「管理员浏览器无法登录」——首页登录表单此前只查 users 表，
        # 管理员凭据永远 401，且 /admin 页面门禁会将其弹回首页，形成死锁。
        admin_res = get_admin_auth().login(username, password)
        if admin_res.get("success"):
            admin = admin_res["admin"]
            _clear_login_failures(username)
            role = admin.get("role") or "admin"
            # 写入页面级会话角色，使 _page_role("admin","super_admin") 放行
            session["role"] = role
            session["admin_id"] = admin["id"]
            public = {
                "id": admin["id"],
                "name": admin.get("display_name") or admin["username"],
                "username": admin["username"],
                "role": role,
            }
            return jsonify({
                "success": True,
                "code": 0,
                "token": admin_res["token"],
                "admin_token": admin_res["token"],
                "user": public,
                "data": {"id": public["id"], "name": public["name"], "role": public["role"]},
                "must_change_password": bool(admin.get("must_change_password", False)),
            })
        _record_login_failure(username)
        return jsonify({"error": "用户名或密码错误"}), 401

    _clear_login_failures(username)
    token = _issue_token(user)
    # 同时写入 cookie 会话，供 teacher/student 门户（session 认证）复用同一登录态
    session["user_id"] = user["id"]
    session["role"] = user.get("role", "user")
    public = {
        "id": user["id"],
        "name": user["name"],
        "username": user.get("username") or user["name"],
        "role": user.get("role", "user"),
    }
    return jsonify({
        "success": True,
        "code": 0,  # 学生端前端 {code,data} 契约
        "token": token,  # 框架/管理端 {success,token} 契约
        "user": public,
        "data": {"id": public["id"], "name": public["name"], "role": public["role"]},
    })


@auth_bp.route("/api/auth/me", methods=["GET", "OPTIONS"])
def api_auth_me():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    user = require_user_token()
    if not user:
        # 管理员会话回退：管理员经首页登录后 cookie 会话仅有 admin_id/role，
        # 无 users 表记录，需单独识别，保证首页登录态展示与页面门禁一致。
        admin_id = session.get("admin_id")
        role = session.get("role") or ""
        if admin_id and role in ("admin", "super_admin"):
            admin = db.get_admin(admin_id)
            if admin:
                public = {
                    "id": admin["id"],
                    "name": admin.get("display_name") or admin["username"],
                    "username": admin["username"],
                    "role": role,
                }
                return jsonify({
                    "success": True,
                    "code": 0,
                    "user": public,
                    "data": {"id": public["id"], "name": public["name"], "role": public["role"]},
                    "must_change_password": bool(admin.get("must_change_password", 0)),
                })
        return jsonify({"error": "未登录", "code": 401, "message": "未登录"}), 401
    public = {
        "id": user["id"],
        "name": user["name"],
        "username": user.get("username") or user["name"],
        "role": user.get("role", "user"),
    }
    return jsonify({
        "success": True,
        "code": 0,
        "user": public,
        "data": {"id": public["id"], "name": public["name"], "role": public["role"]},
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
    # 统一认证：教师/学生门户复用同一 cookie 会话登出时一并清空，
    # 避免「登出后刷新仍为登录态」（session 认证接管后必需）。
    session.clear()
    return jsonify({"success": True, "message": "已退出登录"})
