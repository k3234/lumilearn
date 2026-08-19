# -*- coding: utf-8 -*-
"""
LumiLearn 管理员认证
- 密码哈希存储（werkzeug.security）
- 会话令牌：内存存储 + 时间过期
- Flask 装饰器 require_admin 用于 API 鉴权
"""
import os
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

# 登录暴力破解防护：同一 IP+用户名 连续失败 N 次后锁定
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCK_SECONDS = 900  # 15 分钟
_login_failures: Dict[str, Dict] = {}
_login_failures_lock = threading.Lock()


def _client_ip() -> str:
    """获取客户端 IP（无请求上下文时返回 'unknown'，保证单元测试可调用）"""
    try:
        return request.remote_addr or "unknown"
    except Exception:
        return "unknown"


def _login_lock_check(username: str) -> Optional[Dict]:
    """检查登录是否处于锁定状态，返回锁定错误或 None"""
    key = f"{_client_ip()}|{username}"
    with _login_failures_lock:
        rec = _login_failures.get(key)
        if rec and rec.get("lock_until", 0) > time.time():
            remain = int(rec["lock_until"] - time.time())
            return {"success": False, "error": f"登录失败次数过多，已锁定 {remain} 秒，请稍后再试"}
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


class AdminAuth:
    """管理员认证服务"""

    def __init__(self):
        self._ensure_default_admin()

    def _ensure_default_admin(self):
        """首次运行时创建默认管理员（强随机密码，登录后强制改密）

        安全最佳实践：不再使用公开弱口令 admin/admin123；首次创建的默认
        管理员使用 secrets 生成的高熵密码，并标记 must_change_password=1，
        登录后必须修改密码才能继续使用管理功能。
        """
        try:
            if db.get_admins():
                return
            # 优先读环境变量（部署可注入），否则生成随机强密码
            initial_password = os.environ.get("LUMILEARN_ADMIN_INITIAL_PASSWORD") or \
                secrets.token_urlsafe(16)
            password_hash = generate_password_hash(initial_password)
            db.add_admin("admin", password_hash, display_name="超级管理员",
                         role="super_admin", must_change_password=1)
            db.add_system_log("info", "admin",
                              "已创建默认管理员 admin（随机初始密码，请登录后修改）")
            logger.info("Created default admin account 'admin' (random password, must change)")
        except Exception as e:
            logger.error(f"Failed to create default admin: {e}")

    def login(self, username: str, password: str) -> Dict:
        """管理员登录，成功返回 {token, admin}；连续失败触发锁定"""
        locked = _login_lock_check(username)
        if locked:
            return locked
        admin = db.get_admin_by_username(username)
        if not admin or not admin["is_active"]:
            _record_login_failure(username)
            return {"success": False, "error": "用户名或密码错误"}
        if not check_password_hash(admin["password_hash"], password):
            _record_login_failure(username)
            return {"success": False, "error": "用户名或密码错误"}
        _clear_login_failures(username)

        # 存量库弱口令检测：仍在使用公开弱口令 admin123 的账号 → 强制改密
        # （老版本首次运行默认创建 admin/admin123，登录成功后标记 must_change_password）
        if not admin.get("must_change_password") and password == "admin123":
            try:
                db.set_admin_must_change_password(admin["id"], True)
                admin["must_change_password"] = 1
            except Exception:
                pass

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
                "must_change_password": bool(admin.get("must_change_password", 0)),
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
        """修改管理员密码；改密成功后清除强制改密标志"""
        admin = db.get_admin(admin_id)
        if not admin:
            return {"success": False, "error": "管理员不存在"}
        if not check_password_hash(admin["password_hash"], old_password):
            return {"success": False, "error": "原密码错误"}
        # 强制改密场景（must_change_password=1）要求新密码满足最小强度
        if not new_password or len(new_password) < 6:
            return {"success": False, "error": "新密码长度至少 6 位"}
        db.update_admin_password(admin_id, generate_password_hash(new_password))
        db.set_admin_must_change_password(admin_id, False)
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
