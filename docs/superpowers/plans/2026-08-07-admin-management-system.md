# 管理员与模型/Agent 管理系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 LumiLearn 增加完整的管理员系统，包含管理员认证、模型管理、Agent 管理、系统监控四大子系统，提供 Web 管理面板 + CLI + REST API 三入口。

**Architecture:** 新增 `framework/admin/` 包承载认证与 Agent 注册表逻辑；数据库新增 `admins`/`agents`/`system_logs`/`api_keys` 四张表；新增 `admin_bp` Flask 蓝图注册到现有单端口服务器；前端新增 `admin.html` 管理面板页面（复用现有模板风格，通过 `/admin` 路由访问）。

**Tech Stack:** Python 3.10+ / Flask / SQLite / werkzeug.security（密码哈希）/ JavaScript 原生 fetch（前端）

---

## 文件结构

```
framework/
├── admin/                          # 新建：管理员系统包
│   ├── __init__.py                 # 包导出
│   ├── auth.py                     # 认证：密码哈希 + 会话令牌
│   ├── agents.py                   # Agent 注册表 + 内置 Agent
│   └── service.py                  # 管理服务：用户/模型/Agent/系统管理
├── api/
│   ├── routes/
│   │   └── admin.py                # 新建：管理员 API 蓝图
│   ├── routes/__init__.py          # 修改：导出 admin_bp
│   └── server.py                   # 修改：注册 admin_bp + /admin 页面路由
├── database.py                     # 修改：4 张新表 + CRUD 方法
└── core/config.py                  # 修改：admin 配置项
config/framework.yaml               # 修改：admin 配置
scripts/db_admin.py                 # 修改：admin 子命令
remote/templates/admin.html       # 新建：管理面板前端
tests/
├── test_admin_auth.py              # 新建：认证测试
├── test_admin_api.py               # 新建：管理 API 测试
└── test_agents.py                  # 新建：Agent 管理测试
docs/admin_guide.md                 # 新建：管理员使用指南（Task 9）
```

---

### Task 1: 数据库扩展 — 4 张新表 + CRUD 方法

**Files:**
- Modify: `framework/database.py`（在 `_SCHEMA` 末尾、`learning_workflows` 之后追加表定义；在类末尾追加方法）

- [ ] **Step 1: 在 `_SCHEMA` 末尾追加 4 张表定义**

在 `framework/database.py` 的 `_SCHEMA` 字符串末尾（`CREATE INDEX IF NOT EXISTS idx_detections_type ...` 之后、末尾 `"""` 之前）追加：

```python
CREATE TABLE IF NOT EXISTS admins (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name  TEXT DEFAULT '',
    role          TEXT DEFAULT 'super_admin',  -- super_admin / operator
    is_active     INTEGER DEFAULT 1,
    last_login_at TEXT,
    created_at    TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_admins_username ON admins(username);

CREATE TABLE IF NOT EXISTS agents (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id       TEXT UNIQUE NOT NULL,
    name           TEXT NOT NULL,
    agent_type     TEXT NOT NULL,             -- feynman / detector / adaptive / chat
    description    TEXT DEFAULT '',
    config         TEXT DEFAULT '{}',         -- JSON 配置
    status         TEXT DEFAULT 'stopped',    -- running / stopped / error
    last_heartbeat TEXT,
    created_at     TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(agent_type);

CREATE TABLE IF NOT EXISTS system_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    level      TEXT DEFAULT 'info',           -- debug/info/warning/error
    module     TEXT DEFAULT '',
    message    TEXT DEFAULT '',
    detail     TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_created ON system_logs(created_at);

CREATE TABLE IF NOT EXISTS api_keys (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    key_name   TEXT NOT NULL,
    api_key    TEXT UNIQUE NOT NULL,
    scope      TEXT DEFAULT 'read',           -- read / write / admin
    is_active  INTEGER DEFAULT 1,
    last_used_at TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_api_keys_scope ON api_keys(scope);
```

- [ ] **Step 2: 在 Database 类末尾追加 CRUD 方法（在类最后一个方法之后、类缩进内）**

```python
    # ============================================================
    # Z1. 管理员管理
    # ============================================================

    def add_admin(self, username: str, password_hash: str,
                  display_name: str = "", role: str = "super_admin") -> Dict:
        cur = self._execute(
            "INSERT INTO admins (username, password_hash, display_name, role) VALUES (?, ?, ?, ?)",
            (username, password_hash, display_name, role)
        )
        return {"id": cur.lastrowid, "username": username, "role": role}

    def get_admin_by_username(self, username: str) -> Optional[Dict]:
        return self._query_one("SELECT * FROM admins WHERE username = ?", (username,))

    def get_admin(self, admin_id: int) -> Optional[Dict]:
        return self._query_one("SELECT * FROM admins WHERE id = ?", (admin_id,))

    def get_admins(self) -> List[Dict]:
        return self._query("SELECT * FROM admins ORDER BY id")

    def update_admin_login(self, admin_id: int) -> None:
        self._execute(
            "UPDATE admins SET last_login_at = datetime('now','localtime') WHERE id = ?",
            (admin_id,)
        )

    def set_admin_active(self, admin_id: int, is_active: int) -> bool:
        cur = self._execute("UPDATE admins SET is_active = ? WHERE id = ?", (is_active, admin_id))
        return cur.rowcount > 0

    def update_admin_password(self, admin_id: int, password_hash: str) -> bool:
        cur = self._execute("UPDATE admins SET password_hash = ? WHERE id = ?", (password_hash, admin_id))
        return cur.rowcount > 0

    # ============================================================
    # Z2. Agent 管理
    # ============================================================

    def register_agent(self, agent_id: str, name: str, agent_type: str,
                       description: str = "", config: str = "{}") -> Dict:
        cur = self._execute(
            "INSERT OR REPLACE INTO agents (agent_id, name, agent_type, description, config) VALUES (?, ?, ?, ?, ?)",
            (agent_id, name, agent_type, description, config)
        )
        return {"id": cur.lastrowid, "agent_id": agent_id}

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        return self._query_one("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))

    def get_agents(self, agent_type: Optional[str] = None) -> List[Dict]:
        if agent_type:
            return self._query("SELECT * FROM agents WHERE agent_type = ? ORDER BY id", (agent_type,))
        return self._query("SELECT * FROM agents ORDER BY id")

    def update_agent_status(self, agent_id: str, status: str) -> bool:
        cur = self._execute(
            "UPDATE agents SET status = ?, last_heartbeat = datetime('now','localtime') WHERE agent_id = ?",
            (status, agent_id)
        )
        return cur.rowcount > 0

    def update_agent_config(self, agent_id: str, config: str) -> bool:
        cur = self._execute("UPDATE agents SET config = ? WHERE agent_id = ?", (config, agent_id))
        return cur.rowcount > 0

    def delete_agent(self, agent_id: str) -> bool:
        cur = self._execute("DELETE FROM agents WHERE agent_id = ?", (agent_id,))
        return cur.rowcount > 0

    # ============================================================
    # Z3. 系统日志
    # ============================================================

    def add_system_log(self, level: str, module: str, message: str, detail: str = "") -> int:
        cur = self._execute(
            "INSERT INTO system_logs (level, module, message, detail) VALUES (?, ?, ?, ?)",
            (level, module, message, detail)
        )
        return cur.lastrowid

    def get_system_logs(self, level: Optional[str] = None, limit: int = 100) -> List[Dict]:
        if level:
            return self._query(
                "SELECT * FROM system_logs WHERE level = ? ORDER BY id DESC LIMIT ?",
                (level, limit)
            )
        return self._query("SELECT * FROM system_logs ORDER BY id DESC LIMIT ?", (limit,))

    def clear_system_logs(self, older_than_days: int = 7) -> int:
        cur = self._execute(
            "DELETE FROM system_logs WHERE created_at < datetime('now', ?)",
            (f'-{older_than_days} days',)
        )
        return cur.rowcount

    # ============================================================
    # Z4. API 密钥管理
    # ============================================================

    def add_api_key(self, key_name: str, api_key: str, scope: str = "read") -> Dict:
        cur = self._execute(
            "INSERT INTO api_keys (key_name, api_key, scope) VALUES (?, ?, ?)",
            (key_name, api_key, scope)
        )
        return {"id": cur.lastrowid, "key_name": key_name, "api_key": api_key, "scope": scope}

    def get_api_keys(self, scope: Optional[str] = None) -> List[Dict]:
        if scope:
            return self._query("SELECT * FROM api_keys WHERE scope = ? ORDER BY id", (scope,))
        return self._query("SELECT * FROM api_keys ORDER BY id")

    def validate_api_key(self, api_key: str) -> Optional[Dict]:
        key = self._query_one("SELECT * FROM api_keys WHERE api_key = ? AND is_active = 1", (api_key,))
        if key:
            self._execute(
                "UPDATE api_keys SET last_used_at = datetime('now','localtime') WHERE id = ?",
                (key["id"],)
            )
        return key

    def delete_api_key(self, api_key: str) -> bool:
        cur = self._execute("DELETE FROM api_keys WHERE api_key = ?", (api_key,))
        return cur.rowcount > 0
```

- [ ] **Step 3: 运行测试验证表创建成功**

Run: `python -c "import sys; sys.path.insert(0,'.'); from framework.database import db; db.init(); print(db.get_admins()); print(db.get_agents()); print(db.get_api_keys()); print(db.get_system_logs(limit=3))"`
Expected: 四个空列表输出，无异常（说明表已创建）

- [ ] **Step 4: Commit**

```bash
git add framework/database.py
git commit -m "feat(admin): add admins/agents/system_logs/api_keys tables and CRUD"
```

---

### Task 2: 管理员认证系统

**Files:**
- Create: `framework/admin/__init__.py`
- Create: `framework/admin/auth.py`
- Test: `tests/test_admin_auth.py`

- [ ] **Step 1: 创建 `framework/admin/__init__.py`**

```python
# -*- coding: utf-8 -*-
"""
LumiLearn 管理员系统
- 认证：密码哈希 + 会话令牌
- Agent 注册表：内置 Agent 生命周期管理
- 管理服务：用户/模型/系统管理
"""
from .auth import AdminAuth, get_admin_auth, require_admin
from .agents import AgentRegistry, get_agent_registry

__all__ = [
    "AdminAuth",
    "get_admin_auth",
    "require_admin",
    "AgentRegistry",
    "get_agent_registry",
]
```

- [ ] **Step 2: 创建 `framework/admin/auth.py`（完整实现）**

```python
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
        """首次运行时创建默认管理员"""
        try:
            if db.get_admins():
                return
            password_hash = generate_password_hash("[REDACTED]")
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
```

- [ ] **Step 3: 创建 `tests/test_admin_auth.py`**

```python
# -*- coding: utf-8 -*-
"""管理员认证测试"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.admin.auth import get_admin_auth


class TestAdminAuth(unittest.TestCase):
    def setUp(self):
        db.init()
        self.auth = get_admin_auth()

    def test_default_admin_exists(self):
        admin = db.get_admin_by_username("admin")
        self.assertIsNotNone(admin)
        self.assertEqual(admin["role"], "super_admin")
        self.assertTrue(admin["is_active"])

    def test_login_success(self):
        result = self.auth.login("admin", "[REDACTED]")
        self.assertTrue(result["success"])
        self.assertIn("token", result)
        self.assertEqual(result["admin"]["username"], "admin")

    def test_login_wrong_password(self):
        result = self.auth.login("admin", "wrongpass")
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_login_unknown_user(self):
        result = self.auth.login("nobody", "[REDACTED]")
        self.assertFalse(result["success"])

    def test_verify_valid_token(self):
        login = self.auth.login("admin", "[REDACTED]")
        admin = self.auth.verify(login["token"])
        self.assertIsNotNone(admin)
        self.assertEqual(admin["username"], "admin")

    def test_verify_invalid_token(self):
        self.assertIsNone(self.auth.verify("invalid_token_xyz"))

    def test_logout_invalidates_token(self):
        login = self.auth.login("admin", "[REDACTED]")
        self.auth.logout(login["token"])
        self.assertIsNone(self.auth.verify(login["token"]))

    def test_change_password_and_login(self):
        admin = db.get_admin_by_username("admin")
        result = self.auth.change_password(admin["id"], "[REDACTED]", "newpass456")
        self.assertTrue(result["success"])

        # 新密码可登录
        login = self.auth.login("admin", "newpass456")
        self.assertTrue(login["success"])

        # 旧密码失效
        failed = self.auth.login("admin", "[REDACTED]")
        self.assertFalse(failed["success"])

        # 还原密码
        self.auth.change_password(admin["id"], "newpass456", "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: 运行测试**

Run: `python -m unittest tests.test_admin_auth -v`
Expected: 8 个测试全部 PASS

- [ ] **Step 5: Commit**

```bash
git add framework/admin/ tests/test_admin_auth.py
git commit -m "feat(admin): add admin authentication with sessions"
```

---

### Task 3: Agent 管理系统

**Files:**
- Create: `framework/admin/agents.py`
- Test: `tests/test_agents.py`

- [ ] **Step 1: 创建 `framework/admin/agents.py`（完整实现）**

```python
# -*- coding: utf-8 -*-
"""
LumiLearn Agent 管理系统
- Agent 基类：统一生命周期（start/stop/status/run）
- 内置 Agent：feynman / detector / adaptive / chat
- Agent 注册表：注册、获取、启停、持久化到数据库
"""
impo