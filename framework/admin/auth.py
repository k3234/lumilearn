# -*- coding: utf-8 -*-
"""
LumiLearn 管理员认证
- 密码哈希存储（werkzeug.security）
- 会话令牌：内存存储 + 时间过期
- Flask 装饰器 require_admin 用于 API 鉴权
"""
import secrets
import time
import threading
import logging
from typing import Dict, Optional, Callable

from flask import request, jsonify
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

from framework.database import db

logger = logging.getLogger("lumilearn.admin.auth")

# 会话令牌存储：{token: {"admin_id": int, "expires_at": float}}
_sessions: Dict[str, Dict] = {}
_sessions_lock = threading.Lock()
SESSION_TTL = 12 * 3600  # 12 小时过期


class AdminAuth:
    """管理员认证服务"""

    def __init__(self):
        self._ensure_default_admin()

    def _ensure_default_admin(self):
        """首次运行时创建默认管理员 admin / admin123"""
        try:
            if db.get_admins():
                return
            password_hash = generate_password_hash("admin123")
            db.add_admin("admin", password_hash, display_name="超级管理员", role="super_admin")
            db.add_system_log("info", "admin", "已创建默认管理员 admin（请尽快修改密码）")
            logger.info("Created default admin account 'admin'")
        except Exception as e:
            logger.error(f"Failed to create default admin: {e}")

    def login(self, username: str, password: str) -> Dict:
        """管理员登录，成功返回 {token, admin}"""
        admin = db.get_admin_by_username(username)
        if not admin or not admin["is_active"]:
            return {"success": False, "error": "用户名或密码错误"}
        if not check_password_hash(admin["password_hash"], password):
            return {"success": False, "error": "用户名或密码错误"}

        token = secrets.token_hex(32)
        with _sessions_lock:
            _sessions[token] = {"admin_id": admin["id"], "expires_at": time.time() + SESSION_TTL}
        db.update_admin_login(admin["id"])

        return {
            "success": True,
            "token": token,
            "admin": {
                "id": admin["id"],
                "username": admin["username"],
                "display_name": admin["display_name"],
                "role": admin["role"],
            },
        }

    def logout(self, token: str) -> bool:
        with _sessions_lock:
            return _sessions.pop(token, None) is not None

    def verify(self, token: str) -> Optional[Dict]:
        """校验令牌，返回管理员信息或 None"""
        with _sessions_lock:
            session = _sessions.get(token)
            if not session:
                return None
            if session["expires_at"] < time.time():
                _sessions.pop(token, None)
                return None
        return db.get_admin(session["admin_id"])

    def change_password(self, admin_id: int, old_password: str, new_password: str) -> Dict:
        """修改管理员密码"""
        admin = db.get_admin(admin_id)
        if not admin:
            return {"success": False, "error": "管理员不存在"}
        if not check_password_hash(admin["password_hash"], old_password):
            return {"success": False, "error": "原密码错误"}
        db.update_admin_password(admin_id, generate_password_hash(new_password))
        return {"success": True, "message": "密码修改成功"}

    @staticmethod
    def _cleanup_expired():
        """清理过期会话（供定时调用）"""
        now = time.time()
        with _sessions_lock:
            expired = [t for t, s in _sessions.items() if s["expires_at"] < now]
            for t in expired:
                _sessions.pop(t, None)
        return len(expired)


# 单例
_auth_instance: Optional[AdminAuth] = None


def get_admin_auth() -> AdminAuth:
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = AdminAuth()
    return _auth_instance


def require_admin(f: Callable) -> Callable:
    """Flask 装饰器：要求有效管理员会话"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Admin-Token", "")
        if not token:
            return jsonify({"error": "未登录，请先登录管理员"}), 401
        admin = get_admin_auth().verify(token)
        if not admin:
            return jsonify({"error": "会话已过期或无效"}), 401
        request.admin = admin  # type: ignore
        return f(*args, **kwargs)
    return wrapper
