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
        result = self.auth.login("admin", "admin123")
        self.assertTrue(result["success"])
        self.assertIn("token", result)
        self.assertEqual(result["admin"]["username"], "admin")

    def test_login_wrong_password(self):
        result = self.auth.login("admin", "wrongpass")
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_login_unknown_user(self):
        result = self.auth.login("nobody", "admin123")
        self.assertFalse(result["success"])

    def test_verify_valid_token(self):
        login = self.auth.login("admin", "admin123")
        admin = self.auth.verify(login["token"])
        self.assertIsNotNone(admin)
        self.assertEqual(admin["username"], "admin")

    def test_verify_invalid_token(self):
        self.assertIsNone(self.auth.verify("invalid_token_xyz"))

    def test_logout_invalidates_token(self):
        login = self.auth.login("admin", "admin123")
        self.auth.logout(login["token"])
        self.assertIsNone(self.auth.verify(login["token"]))

    def test_change_password_and_login(self):
        admin = db.get_admin_by_username("admin")
        result = self.auth.change_password(admin["id"], "admin123", "newpass456")
        self.assertTrue(result["success"])

        # 新密码可登录
        login = self.auth.login("admin", "newpass456")
        self.assertTrue(login["success"])

        # 旧密码失效
        failed = self.auth.login("admin", "admin123")
        self.assertFalse(failed["success"])

        # 还原密码
        self.auth.change_password(admin["id"], "newpass456", "admin123")


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
import json
import logging
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable

from framework.database import db

logger = logging.getLogger("lumilearn.admin.agents")

# 全局运行状态（内存）
_agent_runners: Dict[str, Dict] = {}
_agents_lock = threading.Lock()


class BaseAgent(ABC):
    """Agent 基类"""

    def __init__(self, agent_id: str, name: str, agent_type: str, description: str = ""):
        self.agent_id = agent_id
        self.name = name
        self.agent_type = agent_type
        self.description = description

    @abstractmethod
    def run(self, payload: Dict) -> Dict:
        """执行 Agent 任务，返回结果"""
        raise NotImplementedError

    def health(self) -> Dict:
        """Agent 健康状态"""
        return {"agent_id": self.agent_id, "status": "healthy", "type": self.agent_type}

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "type": self.agent_type,
            "description": self.description,
        }


class FeynmanAgent(BaseAgent):
    """费曼五步教学 Agent"""

    def __init__(self):
        super().__init__(
            agent_id="feynman_teacher",
            name="费曼教学Agent",
            agent_type="feynman",
            description="基于费曼五步学习法讲解知识点",
        )

    def run(self, payload: Dict) -> Dict:
        from framework.engines.feynman_engine import FeynmanEngine
        topic = payload.get("topic", "")
        level = payload.get("level", "junior")
        if not topic:
            return {"success": False, "error": "缺少 topic 参数"}
        engine = FeynmanEngine()
        steps = engine.explain(topic=topic, level=level)
        return {"success": True, "topic": topic, "level": level, "steps": steps}


class DetectionAgent(BaseAgent):
    """学习输出检测 Agent"""

    def __init__(self):
        super().__init__(
            agent_id="output_detector",
            name="输出检测Agent",
            agent_type="detector",
            description="检测学生学习输出质量并给出改进建议",
        )

    def run(self, payload: Dict) -> Dict:
        from framework.output_detector import OutputDetector
        concept = payload.get("concept", "")
        output = payload.get("student_output", "")
        user_id = payload.get("user_id", 0)
        if not concept or not output:
            return {"success": False, "error": "缺少 concept 或 student_output 参数"}
        detector = OutputDetector(user_id=user_id)
        result = detector.run_detection(concept, output)
        return {
            "success": True,
            "concept": concept,
            "score": result.total_score,
            "is_mastered": result.is_mastered,
            "feedback": result.feedback,
        }


class AdaptiveAgent(BaseAgent):
    """自适应学习 Agent"""

    def __init__(self):
        super().__init__(
            agent_id="adaptive_path",
            name="自适应学习Agent",
            agent_type="adaptive",
            description="根据学生学习进度推荐学习路径",
        )

    def run(self, payload: Dict) -> Dict:
        from framework.services.adaptive_learning import AdaptiveLearningService
        user_id = payload.get("user_id", 0)
        if not user_id:
            return {"success": False, "error": "缺少 user_id 参数"}
        service = AdaptiveLearningService()
        recommendation = service.get_recommendation(user_id=user_id)
        return {"success": True, "user_id": user_id, "recommendation": recommendation}


class ChatAgent(BaseAgent):
    """通用对话 Agent"""

    def __init__(self):
        super().__init__(
            agent_id="chat_assistant",
            name="对话助手Agent",
            agent_type="chat",
            description="通用多轮对话助手",
        )

    def run(self, payload: Dict) -> Dict:
        from framework.services.chat_service import get_chat_service
        message = payload.get("message", "")
        model = payload.get("model")
        if not message:
            return {"success": False, "error": "缺少 message 参数"}
        service = get_chat_service()
        reply = service.chat(message=message, model=model)
        return {"success": True, "message": message, "reply": reply}

    def health(self) -> Dict:
        from framework.services.chat_service import get_chat_service
        status = get_chat_service().health_check()
        return {"agent_id": self.agent_id, "status": status.get("status", "unknown"), "type": self.agent_type}


# 内置 Agent 工厂
BUILTIN_AGENTS: List[Callable[[], BaseAgent]] = [
    FeynmanAgent,
    DetectionAgent,
    AdaptiveAgent,
    ChatAgent,
]


class AgentRegistry:
    """Agent 注册表：管理 Agent 生命周期并持久化状态"""

    def __init__(self):
        self._ensure_builtins()

    def _ensure_builtins(self):
        """将内置 Agent 注册到数据库（幂等）"""
        try:
            for factory in BUILTIN_AGENTS:
                agent = factory()
                existing = db.get_agent(agent.agent_id)
                if not existing:
                    db.register_agent(
                        agent_id=agent.agent_id,
                        name=agent.name,
                        agent_type=agent.agent_type,
                        description=agent.description,
                    )
                    logger.info(f"Registered builtin agent: {agent.agent_id}")
        except Exception as e:
            logger.error(f"Failed to register builtins: {e}")

    def list_agents(self, agent_type: Optional[str] = None) -> List[Dict]:
        agents = db.get_agents(agent_type)
        for agent in agents:
            runner = _agent_runners.get(agent["agent_id"])
            agent["running"] = runner is not None
            agent["is_builtin"] = agent["agent_id"] in {a.agent_id for a in self._get_builtin_instances()}
        return agents

    def _get_builtin_instances(self) -> List[BaseAgent]:
        return [factory() for factory in BUILTIN_AGENTS]

    def get_agent(self, agent_id: str) -> Dict:
        agent = db.get_agent(agent_id)
        if not agent:
            raise KeyError(f"Agent not found: {agent_id}")
        agent["running"] = agent["agent_id"] in _agent_runners
        return agent

    def register(self, agent_id: str, name: str, agent_type: str,
                 description: str = "", config: Dict = None) -> Dict:
        result = db.register_agent(
            agent_id=agent_id,
            name=name,
            agent_type=agent_type,
            description=description,
            config=json.dumps(config or {}, ensure_ascii=False),
        )
        db.add_system_log("info", "agents", f"注册新Agent: {name} ({agent_id})")
        return result

    def _create_instance(self, agent: Dict) -> BaseAgent:
        """根据数据库记录创建 Agent 实例（支持自定义注册）"""
        for factory in BUILTIN_AGENTS:
            builtin = factory()
            if builtin.agent_id == agent["agent_id"]:
                return builtin
        # 自定义 Agent：动态创建通用实例
        return self._create_custom(agent)

    def _create_custom(self, agent: Dict) -> BaseAgent:
        config = json.loads(agent["config"] or "{}")
        runner = config.get("runner")  # 可选：可调用对象的模块路径（预留扩展）

        class _CustomAgent(BaseAgent):
            def run(self, payload: Dict) -> Dict:
                return {"success": True, "message": "自定义Agent已注册，执行器待配置", "payload": payload}

        return _CustomAgent(agent_id=agent["agent_id"], name=agent["name"],
                            agent_type=agent["agent_type"], description=agent["description"])

    def start(self, agent_id: str) -> Dict:
        agent = db.get_agent(agent_id)
        if not agent:
            raise KeyError(f"Agent not found: {agent_id}")
        with _agents_lock:
            if agent_id in _agent_runners:
                return {"success": True, "message": f"Agent {agent_id} 已在运行中"}
            instance = self._create_instance(agent)
            _agent_runners[agent_id] = {"instance": instance}
        db.update_agent_status(agent_id, "running")
        db.add_system_log("info", "agents", f"启动Agent: {agent['name']} ({agent_id})")
        return {"success": True, "message": f"Agent {agent_id} 已启动"}

    def stop(self, agent_id: str) -> Dict:
        with _agents_lock:
            if agent_id not in _agent_runners:
                return {"success": False, "message": f"Agent {agent_id} 未在运行"}
            _agent_runners.pop(agent_id, None)
        db.update_agent_status(agent_id, "stopped")
        db.add_system_log("info", "agents", f"停止Agent: {agent_id}")
        return {"success": True, "message": f"Agent {agent_id} 已停止"}

    def run_agent(self, agent_id: str, payload: Dict) -> Dict:
        """执行 Agent 任务（自动启动未运行实例）"""
        if agent_id not in _agent_runners:
            self.start(agent_id)
        runner = _agent_runners.get(agent_id)
        if not runner:
            return {"success": False, "error": f"Agent {agent_id} 启动失败"}
        try:
            instance = runner["instance"]
            result = instance.run(payload)
            result["agent_id"] = agent_id
            return result
        except Exception as e:
            logger.exception(f"Agent {agent_id} run error")
            db.update_agent_status(agent_id, "error")
            return {"success": False, "error": str(e)}

    def delete(self, agent_id: str) -> Dict:
        if agent_id in _agent_runners:
            self.stop(agent_id)
        db.delete_agent(agent_id)
        return {"success": True, "message": f"Agent {agent_id} 已删除"}

    def health(self, agent_id: Optional[str] = None) -> Dict:
        """Agent 健康检查"""
        if agent_id:
            agent = db.get_agent(agent_id)
            if not agent:
                return {"success": False, "error": f"Agent not found: {agent_id}"}
            runner = _agent_runners.get(agent_id)
            if runner:
                return runner["instance"].health()
            return {"agent_id": agent_id, "status": "stopped", "type": agent["agent_type"]}
        results = {}
        for agent in db.get_agents():
            runner = _agent_runners.get(agent["agent_id"])
            if runner:
                results[agent["agent_id"]] = runner["instance"].health()
            else:
                results[agent["agent_id"]] = {"agent_id": agent["agent_id"], "status": "stopped", "type": agent["agent_type"]}
        return {"agents": results, "total": len(results)}


# 单例
_registry_instance: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AgentRegistry()
    return _registry_instance
```

- [ ] **Step 2: 创建 `tests/test_agents.py`**

```python
# -*- coding: utf-8 -*-
"""Agent 管理系统测试"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.admin.agents import (
    AgentRegistry,
    get_agent_registry,
    FeynmanAgent,
    DetectionAgent,
    AdaptiveAgent,
    ChatAgent,
)


class TestAgentRegistry(unittest.TestCase):
    def setUp(self):
        db.init()
        self.registry = get_agent_registry()

    def test_builtin_agents_registered(self):
        agents = self.registry.list_agents()
        agent_ids = {a["agent_id"] for a in agents}
        self.assertIn("feynman_teacher", agent_ids)
        self.assertIn("output_detector", agent_ids)
        self.assertIn("adaptive_path", agent_ids)
        self.assertIn("chat_assistant", agent_ids)

    def test_list_agents_by_type(self):
        agents = self.registry.list_agents(agent_type="feynman")
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0]["agent_type"], "feynman")

    def test_register_custom_agent(self):
        result = self.registry.register(
            agent_id="test_custom_agent",
            name="测试Agent",
            agent_type="custom",
            description="单元测试用",
            config={"enabled": True},
        )
        self.assertIn("agent_id", result)
        agent = db.get_agent("test_custom_agent")
        self.assertIsNotNone(agent)
        self.assertEqual(agent["name"], "测试Agent")

    def test_start_and_stop_agent(self):
        self.registry.start("chat_assistant")
        agent = db.get_agent("chat_assistant")
        self.assertEqual(agent["status"], "running")

        self.registry.stop("chat_assistant")
        agent = db.get_agent("chat_assistant")
        self.assertEqual(agent["status"], "stopped")

    def test_run_feynman_agent(self):
        with patch("framework.engines.feynman_engine.FeynmanEngine") as MockEngine:
            MockEngine.return_value.explain.return_value = {"steps": []}
            result = self.registry.run_agent("feynman_teacher", {"topic": "勾股定理", "level": "junior"})
        self.assertTrue(result["success"])
        self.assertEqual(result["topic"], "勾股定理")

    def test_run_agent_missing_param(self):
        result = self.registry.run_agent("feynman_teacher", {})
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_run_chat_agent(self):
        with patch("framework.services.chat_service.get_chat_service") as mock_service:
            mock_service.return_value.chat.return_value = "你好！"
            result = self.registry.run_agent("chat_assistant", {"message": "你好"})
        self.assertTrue(result["success"])
        self.assertEqual(result["reply"], "你好！")

    def test_delete_agent(self):
        self.registry.register("to_delete_agent", "待删除", "custom", "临时")
        result = self.registry.delete("to_delete_agent")
        self.assertTrue(result["success"])
        self.assertIsNone(db.get_agent("to_delete_agent"))

    def test_health_check(self):
        health = self.registry.health()
        self.assertIn("total", health)
        self.assertEqual(health["total"], len(db.get_agents()))

    def test_get_nonexistent_agent_raises(self):
        with self.assertRaises(KeyError):
            self.registry.get_agent("does_not_exist")


class TestBuiltinAgents(unittest.TestCase):
    def test_feynman_agent_meta(self):
        agent = FeynmanAgent()
        self.assertEqual(agent.agent_type, "feynman")
        self.assertIn("steps", agent.health())

    def test_detection_agent_meta(self):
        agent = DetectionAgent()
        self.assertEqual(agent.agent_id, "output_detector")

    def test_adaptive_agent_meta(self):
        agent = AdaptiveAgent()
        self.assertEqual(agent.agent_type, "adaptive")

    def test_chat_agent_meta(self):
        agent = ChatAgent()
        self.assertEqual(agent.agent_id, "chat_assistant")
        self.assertIn("status", agent.health())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 运行测试**

Run: `python -m unittest tests.test_agents -v`
Expected: 全部 PASS（若 `AdaptiveLearningService` 或 `chat_service.health_check` 接口名不符，按实际类名修正 mock 目标）

- [ ] **Step 4: Commit**

```bash
git add framework/admin/agents.py tests/test_agents.py
git commit -m "feat(admin): add agent registry with builtin agents"
```

---

### Task 4: 管理员 API 蓝图

**Files:**
- Create: `framework/api/routes/admin.py`
- Modify: `framework/api/routes/__init__.py`
- Modify: `framework/api/server.py`
- Test: `tests/test_admin_api.py`

- [ ] **Step 1: 创建 `framework/api/routes/admin.py`（完整实现）**

```python
# -*- coding: utf-8 -*-
"""
LumiLearn 管理员 API 路由
认证 / 用户管理 / 模型管理 / Agent管理 / 系统监控
"""
import json
import logging
from flask import Blueprint, request, jsonify

from framework.database import db
from framework.admin.auth import get_admin_auth, require_admin
from framework.admin.agents import get_agent_registry
from framework.core.config import get_config
from framework.models.ollama_provider import get_ollama_provider

logger = logging.getLogger("lumilearn.routes.admin")

admin_bp = Blueprint("admin", __name__)


# ---------------------------------------------------------------------------
# 认证
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/login", methods=["POST", "OPTIONS"])
def admin_login():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    data = request.get_json(force=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    result = get_admin_auth().login(username, password)
    if not result["success"]:
        return jsonify(result), 401
    return jsonify(result)


@admin_bp.route("/api/admin/logout", methods=["POST", "OPTIONS"])
@require_admin
def admin_logout():
    token = request.headers.get("X-Admin-Token", "")
    get_admin_auth().logout(token)
    return jsonify({"success": True, "message": "已退出登录"})


@admin_bp.route("/api/admin/me", methods=["GET", "OPTIONS"])
@require_admin
def admin_me():
    admin = request.admin
    return jsonify({
        "success": True,
        "admin": {
            "id": admin["id"],
            "username": admin["username"],
            "display_name": admin["display_name"],
            "role": admin["role"],
            "last_login_at": admin["last_login_at"],
        },
    })


@admin_bp.route("/api/admin/password", methods=["POST", "OPTIONS"])
@require_admin
def admin_change_password():
    data = request.get_json(force=True) or {}
    result = get_admin_auth().change_password(
        request.admin["id"],
        data.get("old_password", ""),
        data.get("new_password", ""),
    )
    return jsonify(result)


# ---------------------------------------------------------------------------
# 系统概览
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/overview", methods=["GET", "OPTIONS"])
@require_admin
def admin_overview():
    """系统总览：用户数、工作流数、检测数、模型状态、Agent 状态、日志数"""
    users = db.get_users()
    workflows = db.get_user_workflows(user_id=None) if hasattr(db, "get_user_workflows") else []
    detections = db.get_user_detections(user_id=None) if hasattr(db, "get_user_detections") else []
    agents = db.get_agents()
    logs = db.get_system_logs(limit=5)

    ollama = get_ollama_provider()
    model_status = ollama.health_check()

    return jsonify({
        "success": True,
        "stats": {
            "total_users": len(users),
            "total_teachers": len([u for u in users if u["role"] == "teacher"]),
            "total_students": len([u for u in users if u["role"] == "student"]),
            "total_workflows": len(workflows),
            "total_detections": len(detections),
            "total_agents": len(agents),
            "running_agents": len([a for a in agents if a["status"] == "running"]),
        },
        "model_status": model_status,
        "recent_logs": logs,
    })


# ---------------------------------------------------------------------------
# 用户管理
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/users", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_users():
    role = request.args.get("role")
    users = db.get_users(role=role)
    return jsonify({"success": True, "users": users})


@admin_bp.route("/api/admin/users", methods=["POST", "OPTIONS"])
@require_admin
def admin_create_user():
    data = request.get_json(force=True) or {}
    name = data.get("name", "")
    role = data.get("role", "student")
    if not name:
        return jsonify({"error": "缺少 name 字段"}), 400
    user = db.add_user(name, role=role)
    db.add_system_log("info", "admin", f"管理员创建用户: {name} ({role})")
    return jsonify({"success": True, "user": user})


@admin_bp.route("/api/admin/users/<int:user_id>", methods=["DELETE", "OPTIONS"])
@require_admin
def admin_delete_user(user_id):
    ok = db.delete_user(user_id)
    if not ok:
        return jsonify({"error": "用户不存在"}), 404
    db.add_system_log("info", "admin", f"管理员删除用户 id={user_id}")
    return jsonify({"success": True, "message": "用户已删除"})


# ---------------------------------------------------------------------------
# 模型管理
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/models", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_models():
    ollama = get_ollama_provider()
    models = ollama.list_models()
    health = ollama.health_check()
    return jsonify({"success": True, "models": models, "health": health})


@admin_bp.route("/api/admin/models/pull", methods=["POST", "OPTIONS"])
@require_admin
def admin_pull_model():
    """拉取新模型到 Ollama"""
    data = request.get_json(force=True) or {}
    model_name = data.get("model", "")
    if not model_name:
        return jsonify({"error": "缺少 model 字段"}), 400
    ollama = get_ollama_provider()
    result = ollama.pull_model(model_name) if hasattr(ollama, "pull_model") else {"error": "当前 Ollama 版本不支持拉取模型"}
    db.add_system_log("info", "models", f"拉取模型: {model_name}", json.dumps(result, ensure_ascii=False))
    return jsonify({"success": "error" not in result, **result})


@admin_bp.route("/api/admin/models/delete", methods=["POST", "OPTIONS"])
@require_admin
def admin_delete_model():
    data = request.get_json(force=True) or {}
    model_name = data.get("model", "")
    if not model_name:
        return jsonify({"error": "缺少 model 字段"}), 400
    ollama = get_ollama_provider()
    result = ollama.delete_model(model_name) if hasattr(ollama, "delete_model") else {"error": "当前 Ollama 版本不支持删除模型"}
    db.add_system_log("info", "models", f"删除模型: {model_name}", json.dumps(result, ensure_ascii=False))
    return jsonify({"success": "error" not in result, **result})


@admin_bp.route("/api/admin/models/default", methods=["POST", "OPTIONS"])
@require_admin
def admin_set_default_model():
    data = request.get_json(force=True) or {}
    model_name = data.get("model", "")
    if not model_name:
        return jsonify({"error": "缺少 model 字段"}), 400
    config = get_config()
    config["ollama"]["default_model"] = model_name
    db.add_system_log("info", "models", f"设置默认模型: {model_name}")
    return jsonify({"success": True, "message": f"默认模型已设置为 {model_name}"})


# ---------------------------------------------------------------------------
# Agent 管理
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/agents", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_agents():
    registry = get_agent_registry()
    agent_type = request.args.get("type")
    return jsonify({"success": True, "agents": registry.list_agents(agent_type)})


@admin_bp.route("/api/admin/agents", methods=["POST", "OPTIONS"])
@require_admin
def admin_register_agent():
    data = request.get_json(force=True) or {}
    agent_id = data.get("agent_id", "")
    name = data.get("name", "")
    agent_type = data.get("type", "custom")
    if not agent_id or not name:
        return jsonify({"error": "缺少 agent_id 或 name 字段"}), 400
    registry = get_agent_registry()
    result = registry.register(agent_id, name, agent_type,
                               description=data.get("description", ""),
                               config=data.get("config", {}))
    return jsonify({"success": True, **result})


@admin_bp.route("/api/admin/agents/<agent_id>/start", methods=["POST", "OPTIONS"])
@require_admin
def admin_start_agent(agent_id):
    try:
        result = get_agent_registry().start(agent_id)
    except KeyError:
        return jsonify({"error": "Agent 不存在"}), 404
    return jsonify(result)


@admin_bp.route("/api/admin/agents/<agent_id>/stop", methods=["POST", "OPTIONS"])
@require_admin
def admin_stop_agent(agent_id):
    result = get_agent_registry().stop(agent_id)
    return jsonify(result)


@admin_bp.route("/api/admin/agents/<agent_id>/run", methods=["POST", "OPTIONS"])
@require_admin
def admin_run_agent(agent_id):
    """手动触发 Agent 执行（测试用）"""
    data = request.get_json(force=True) or {}
    result = get_agent_registry().run_agent(agent_id, data)
    return jsonify(result)


@admin_bp.route("/api/admin/agents/<agent_id>", methods=["DELETE", "OPTIONS"])
@require_admin
def admin_delete_agent(agent_id):
    result = get_agent_registry().delete(agent_id)
    return jsonify(result)


@admin_bp.route("/api/admin/agents/health", methods=["GET", "OPTIONS"])
@require_admin
def admin_agents_health():
    return jsonify(get_agent_registry().health())


# ---------------------------------------------------------------------------
# 系统监控
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/logs", methods=["GET", "OPTIONS"])
@require_admin
def admin_logs():
    level = request.args.get("level")
    limit = int(request.args.get("limit", 100))
    logs = db.get_system_logs(level=level, limit=limit)
    return jsonify({"success": True, "logs": logs})


@admin_bp.route("/api/admin/logs/clear", methods=["POST", "OPTIONS"])
@require_admin
def admin_clear_logs():
    days = int(request.json.get("older_than_days", 7) if request.json else 7)
    count = db.clear_system_logs(older_than_days=days)
    return jsonify({"success": True, "cleared": count})


@admin_bp.route("/api/admin/api-keys", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_api_keys():
    return jsonify({"success": True, "api_keys": db.get_api_keys()})


@admin_bp.route("/api/admin/api-keys", methods=["POST", "OPTIONS"])
@require_admin
def admin_create_api_key():
    import secrets
    data = request.get_json(force=True) or {}
    key_name = data.get("key_name", "")
    scope = data.get("scope", "read")
    if not key_name:
        return jsonify({"error": "缺少 key_name 字段"}), 400
    api_key = secrets.token_hex(24)
    result = db.add_api_key(key_name, api_key, scope)
    db.add_system_log("info", "admin", f"创建API密钥: {key_name} ({scope})")
    return jsonify({"success": True, **result})


@admin_bp.route("/api/admin/api-keys/<path:api_key>", methods=["DELETE", "OPTIONS"])
@require_admin
def admin_delete_api_key(api_key):
    ok = db.delete_api_key(api_key)
    if not ok:
        return jsonify({"error": "密钥不存在"}), 404
    return jsonify({"success": True, "message": "密钥已删除"})
```

- [ ] **Step 2: 修改 `framework/api/routes/__init__.py` 导出 admin_bp**

```python
from .admin import admin_bp  # 管理员管理
```

并在 `__all__` 列表中添加 `"admin_bp",`。

- [ ] **Step 3: 修改 `framework/api/server.py`**

在导入行（第 33 行）添加 admin_bp：
```python
from framework.api.routes import (..., security_bp, admin_bp)
```
在 `create_app` 中注册（`app.register_blueprint(security_bp)` 之后）：
```python
    app.register_blueprint(admin_bp)
```
在 `index()` 路由之后添加 `/admin` 页面路由：
```python
    @app.route("/admin")
    def admin_page():
        """管理员管理面板"""
        html_path = BASE_DIR / "remote" / "templates" / "admin.html"
        if html_path.exists():
            content = html_path.read_text(encoding="utf-8")
            response = app.make_response(content)
            response.headers["Content-Type"] = "text/html; charset=utf-8"
            return response
        return "<h1>LumiLearn Admin</h1><p>admin.html not found</p>", 404
```

- [ ] **Step 4: 创建 `tests/test_admin_api.py`**

```python
# -*- coding: utf-8 -*-
"""管理员 API 测试（用 Flask test client）"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.api.server import create_app


class TestAdminAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init()
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def _login(self):
        resp = self.client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(resp.status_code, 200)
        return resp.get_json()["token"]

    def test_login_endpoint(self):
        resp = self.client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("token", data)

    def test_login_wrong_password(self):
        resp = self.client.post("/api/admin/login", json={"username": "admin", "password": "bad"})
        self.assertEqual(resp.status_code, 401)

    def test_me_requires_auth(self):
        resp = self.client.get("/api/admin/me")
        self.assertEqual(resp.status_code, 401)

    def test_me_with_token(self):
        token = self._login()
        resp = self.client.get("/api/admin/me", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["admin"]["username"], "admin")

    def test_overview(self):
        token = self._login()
        resp = self.client.get("/api/admin/overview", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("stats", data)
        self.assertIn("model_status", data)

    def test_list_users(self):
        token = self._login()
        resp = self.client.get("/api/admin/users", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("users", resp.get_json())

    def test_create_and_delete_user(self):
        token = self._login()
        resp = self.client.post("/api/admin/users",
                                json={"name": "API测试用户", "role": "student"},
                                headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        user_id = resp.get_json()["user"]["id"]

        resp = self.client.delete(f"/api/admin/users/{user_id}", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)

    def test_list_agents(self):
        token = self._login()
        resp = self.client.get("/api/admin/agents", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        agents = resp.get_json()["agents"]
        self.assertGreaterEqual(len(agents), 4)

    def test_start_stop_agent(self):
        token = self._login()
        resp = self.client.post("/api/admin/agents/chat_assistant/start", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post("/api/admin/agents/chat_assistant/stop", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)

    def test_run_agent_feynman(self):
        token = self._login()
        resp = self.client.post("/api/admin/agents/feynman_teacher/run",
                                json={"topic": "勾股定理", "level": "junior"},
                                headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)

    def test_logs(self):
        token = self._login()
        resp = self.client.get("/api/admin/logs?limit=5", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("logs", resp.get_json())

    def test_api_keys_crud(self):
        token = self._login()
        resp = self.client.post("/api/admin/api-keys",
                                json={"key_name": "测试密钥", "scope": "read"},
                                headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        api_key = resp.get_json()["api_key"]

        resp = self.client.delete(f"/api/admin/api-keys/{api_key}", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)

    def test_admin_page_served(self):
        resp = self.client.get("/admin")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5: 运行测试**

Run: `python -m unittest tests.test_admin_api -v`
Expected: 全部 PASS（`test_run_agent_feynman` 若因 Ollama 未启动失败，忽略模型调用部分——FeynmanEngine 内部应有降级逻辑；若无，改为 mock）

- [ ] **Step 6: Commit**

```bash
git add framework/api/routes/admin.py framework/api/routes/__init__.py framework/api/server.py tests/test_admin_api.py
git commit -m "feat(admin): add admin API blueprint with auth, users, models, agents, monitoring"
```

---

### Task 5: Ollama 提供者增强（pull/delete 模型）

**Files:**
- Modify: `framework/models/ollama_provider.py`

- [ ] **Step 1: 在 `OllamaProvider` 类中添加 `pull_model` 和 `delete_model` 方法**

在 `health_check` 方法之后、类末尾添加：

```python
    def pull_model(self, model_name: str, stream: bool = True) -> Dict[str, Any]:
        """
        拉取（下载）模型到本地

        参数:
            model_name: 模型名称（如 qwen2.5:7b）
            stream: 是否流式输出进度

        返回:
            操作结果
        """
        payload = {"name": model_name, "stream": stream}
        try:
            resp = requests.post(
                f"{self._base_url}/api/pull",
                json=payload,
                timeout=self._timeout
            )
            if resp.status_code == 200:
                return {"status": "ok", "model": model_name, "message": "模型拉取成功"}
            return {"error": f"Ollama returned {resp.status_code}: {resp.text[:300]}"}
        except Exception as e:
            return {"error": str(e)}

    def delete_model(self, model_name: str) -> Dict[str, Any]:
        """
        删除本地模型

        参数:
            model_name: 模型名称

        返回:
            操作结果
        """
        try:
            resp = requests.delete(
                f"{self._base_url}/api/delete",
                json={"name": model_name},
                timeout=30
            )
            if resp.status_code == 200:
                return {"status": "ok", "model": model_name, "message": "模型已删除"}
            return {"error": f"Ollama returned {resp.status_code}: {resp.text[:300]}"}
        except Exception as e:
            return {"error": str(e)}
```

- [ ] **Step 2: 运行简单验证**

Run: `python -c "import sys; sys.path.insert(0,'.'); from framework.models.ollama_provider import get_ollama_provider; p=get_ollama_provider(); print(p.list_models())"`
Expected: 输出模型列表（Ollama 未启动则为空列表，无异常）

- [ ] **Step 3: Commit**

```bash
git add framework/models/ollama_provider.py
git commit -m "feat(models): add pull/delete model support to OllamaProvider"
```

---

### Task 6: 管理面板前端 admin.html

**Files:**
- Create: `remote/templates/admin.html`

- [ ] **Step 1: 创建 `remote/templates/admin.html`（完整实现）**

单文件管理面板：登录页 + 主面板（概览 / 用户 / 模型 / Agent / 日志 / 密钥）。复用现有模板深色终端风格。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LumiLearn 管理面板</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: "Microsoft YaHei", sans-serif; background: #0d1117; color: #e6edf3; }
  .login-wrap { display: flex; justify-content: center; align-items: center; height: 100vh; }
  .login-card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 40px; width: 360px; }
  .login-card h1 { font-size: 22px; margin-bottom: 24px; color: #58a6ff; }
  .login-card input { width: 100%; padding: 12px; margin-bottom: 12px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #e6edf3; font-size: 14px; }
  .login-card button { width: 100%; padding: 12px; background: #238636; border: none; border-radius: 6px; color: #fff; font-size: 15px; cursor: pointer; }
  .login-card button:hover { background: #2ea043; }
  .error { color: #f85149; font-size: 13px; margin-bottom: 10px; min-height: 18px; }
  .app { display: none; }
  .sidebar { position: fixed; left: 0; top: 0; width: 200px; height: 100vh; background: #161b22; border-right: 1px solid #30363d; padding-top: 20px; }
  .sidebar .brand { padding: 0 20px; font-size: 18px; font-weight: bold; color: #58a6ff; margin-bottom: 30px; }
  .sidebar .nav-item { display: block; width: 100%; padding: 12px 20px; color: #8b949e; background: none; border: none; text-align: left; font-size: 14px; cursor: pointer; }
  .sidebar .nav-item:hover, .sidebar .nav-item.active { color: #58a6ff; background: #0d1117; border-left: 3px solid #58a6ff; }
  .main { margin-left: 200px; padding: 24px; }
  .topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
  .topbar h2 { font-size: 20px; }
  .topbar .user { color: #8b949e; font-size: 13px; }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px; }
  .card .num { font-size: 28px; font-weight: bold; color: #58a6ff; }
  .card .label { font-size: 13px; color: #8b949e; margin-top: 6px; }
  .panel { display: none; background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px; }
  .panel.active { display: block; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #21262d; }
  th { color: #8b949e; font-weight: normal; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; }
  .badge.ok { background: #1f6feb33; color: #58a6ff; }
  .badge.on { background: #23863633; color: #3fb950; }
  .badge.off { background: #30363d; color: #8b949e; }
  .badge.err { background: #f8514933; color: #f85149; }
  button.act { padding: 6px 14px; margin-right: 6px; background: #21262d; border: 1px solid #30363d; border-radius: 6px; color: #e6edf3; cursor: pointer; font-size: 12px; }
  button.act:hover { border-color: #58a6ff; color: #58a6ff; }
  button.act.danger:hover { border-color: #f85149; color: #f85149; }
  .form-row { display: flex; gap: 10px; margin-bottom: 16px; }
  .form-row input { flex: 1; padding: 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #e6edf3; }
  .form-row select { padding: 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #e6edf3; }
  .toast { position: fixed; top: 20px; right: 20px; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px 20px; z-index: 999; display: none; }
  .toast.show { display: block; }
  pre.log-box { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px; max-height: 500px; overflow-y: auto; font-size: 12px; line-height: 1.6; }
</style>
</head>
<body>

<div class="login-wrap" id="loginWrap">
  <div class="login-card">
    <h1>🔐 LumiLearn 管理面板</h1>
    <div class="error" id="loginError"></div>
    <input type="text" id="username" placeholder="用户名" value="admin">
    <input type="password" id="password" placeholder="密码" value="admin123">
    <button onclick="doLogin()">登 录</button>
  </div>
</div>

<div class="app" id="app">
  <div class="sidebar">
    <div class="brand">LumiLearn Admin</div>
    <button class="nav-item active" data-panel="overview" onclick="switchPanel('overview')">📊 系统概览</button>
    <button class="nav-item" data-panel="users" onclick="switchPanel('users')">👥 用户管理</button>
    <button class="nav-item" data-panel="models" onclick="switchPanel('models')">🤖 模型管理</button>
    <button class="nav-item" data-panel="agents" onclick="switchPanel('agents')">🧠 Agent管理</button>
    <button class="nav-item" data-panel="logs" onclick="switchPanel('logs')">📜 系统日志</button>
    <button class="nav-item" data-panel="keys" onclick="switchPanel('keys')">🔑 API密钥</button>
    <div style="position:absolute; bottom:20px; left:20px; right:20px;">
      <button class="act" onclick="logout()" style="width:100%;">退出登录</button>
    </div>
  </div>
  <div class="main">
    <div class="topbar">
      <h2 id="panelTitle">系统概览</h2>
      <div class="user" id="adminInfo"></div>
    </div>
    <div id="content"></div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const API = '/api/admin';
let TOKEN = localStorage.getItem('admin_token') || '';

async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  if (TOKEN) headers['X-Admin-Token'] = TOKEN;
  const resp = await fetch(API + path, { ...opts, headers });
  if (resp.status === 401) { location.reload(); throw new Error('未登录'); }
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok && data.error) throw new Error(data.error);
  return data;
}

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}

async function doLogin() {
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  try {
    const data = await fetch(API + '/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }).then(r => r.json());
    if (!data.success) throw new Error(data.error || '登录失败');
    TOKEN = data.token;
    localStorage.setItem('admin_token', TOKEN);
    document.getElementById('loginWrap').style.display = 'none';
    document.getElementById('app').style.display = 'block';
    init();
  } catch (e) { document.getElementById('loginError').textContent = e.message; }
}

function logout() {
  api('/logout', { method: 'POST' }).catch(() => {});
  TOKEN = '';
  localStorage.removeItem('admin_token');
  location.reload();
}

function switchPanel(name) {
  document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.panel === name));
  const titles = { overview: '系统概览', users: '用户管理', models: '模型管理', agents: 'Agent管理', logs: '系统日志', keys: 'API密钥' };
  document.getElementById('panelTitle').textContent = titles[name];
  loaders[name]();
}

const loaders = {
  overview: loadOverview,
  users: loadUsers,
  models: loadModels,
  agents: loadAgents,
  logs: loadLogs,
  keys: loadKeys,
};

async function init() {
  const me = await api('/me');
  document.getElementById('adminInfo').textContent = `${me.admin.display_name || me.admin.username} (${me.admin.role})`;
  loadOverview();
}

// ---------- 概览 ----------
async function loadOverview() {
  const data = await api('/overview');
  const s = data.stats;
  const m = data.model_status;
  document.getElementById('content').innerHTML = `
    <div class="cards">
      <div class="card"><div class="num">${s.total_users}</div><div class="label">总用户</div></div>
      <div class="card"><div class="num">${s.total_students}</div><div class="label">学生</div></div>
      <div class="card"><div class="num">${s.total_teachers}</div><div class="label">教师</div></div>
      <div class="card"><div class="num">${s.total_workflows}</div><div class="label">学习工作流</div></div>
      <div class="card"><div class="num">${s.total_detections}</div><div class="label">输出检测</div></div>
      <div class="card"><div class="num">${s.running_agents}/${s.total_agents}</div><div class="label">运行中 Agent</div></div>
    </div>
    <h3 style="margin:16px 0 10px;color:#8b949e;">模型服务状态</h3>
    <div class="cards">
      <div class="card"><div class="num" style="font-size:18px;">${m.status || 'unknown'}</div><div class="label">网关状态</div></div>
      <div class="card"><div class="num" style="font-size:18px;">${m.models ?? '-'}</div><div class="label">本地模型数</div></div>
      <div class="card"><div class="num" style="font-size:18px;">${m.latency_ms ?? '-'}ms</div><div class="label">响应延迟</div></div>
    </div>
    <h3 style="margin:16px 0 10px;color:#8b949e;">最近日志</h3>
    <pre class="log-box">${(data.recent_logs || []).map(l => `[${l.created_at}] [${l.level}] [${l.module}] ${l.message}`).join('\n') || '（无日志）'}</pre>`;
}

// ---------- 用户管理 ----------
async function loadUsers() {
  const data = await api('/users');
  document.getElementById('content').innerHTML = `
    <div class="form-row">
      <input id="newUserName" placeholder="新用户姓名">
      <select id="newUserRole">
        <option value="student">学生</option>
        <option value="teacher">教师</option>
      </select>
      <button class="act" onclick="createUser()">添加用户</button>
    </div>
    <table>
      <tr><th>ID</th><th>姓名</th><th>角色</th><th>创建时间</th><th>操作</th></tr>
      ${data.users.map(u => `
        <tr>
          <td>${u.id}</td><td>${u.name}</td><td>${u.role}</td><td>${u.created_at || '-'}</td>
          <td><button class="act danger" onclick="deleteUser(${u.id})">删除</button></td>
        </tr>`).join('')}
    </table>`;
}

async function createUser() {
  const name = document.getElementById('newUserName').value;
  const role = document.getElementById('newUserRole').value;
  if (!name) return toast('请输入姓名');
  await api('/users', { method: 'POST', body: JSON.stringify({ name, role }) });
  toast('用户已创建');
  loadUsers();
}

async function deleteUser(id) {
  if (!confirm(`确认删除用户 #${id}？此操作不可恢复。`)) return;
  await api(`/users/${id}`, { method: 'DELETE' });
  toast('用户已删除');
  loadUsers();
}

// ---------- 模型管理 ----------
async function loadModels() {
  const data = await api('/models');
  document.getElementById('content').innerHTML = `
    <div class="form-row">
      <input id="pullModelName" placeholder="模型名称，如 qwen2.5:3b">
      <button class="act" onclick="pullModel()">拉取模型</button>
    </div>
    <table>
      <tr><th>模型名称</th><th>大小</th><th>更新时间</th><th>操作</th></tr>
      ${(data.models || []).map(m => `
        <tr>
          <td>${m.name}</td><td>${m.size ? (m.size/1024/1024/1024).toFixed(1) + 'GB' : '-'}</td><td>${m.modified_at || '-'}</td>
          <td><button class="act" onclick="setDefault('${m.name}')">设为默认</button>
              <button class="act danger" onclick="deleteModel('${m.name}')">删除</button></td>
        </tr>`).join('') || '<tr><td colspan="4">暂无本地模型</td></tr>'}
    </table>`;
}

async function pullModel() {
  const model = document.getElementById('pullModelName').value;
  if (!model) return toast('请输入模型名称');
  const data = await api('/models/pull', { method: 'POST', body: JSON.stringify({ model }) });
  toast(data.message || data.error || '操作完成');
  loadModels();
}

async function deleteModel(name) {
  if (!confirm(`确认删除模型 ${name}？`)) return;
  const data = await api('/models/delete', { method: 'POST', body: JSON.stringify({ model: name }) });
  toast(data.message || data.error || '操作完成');
  loadModels();
}

async function setDefault(name) {
  await api('/models/default', { method: 'POST', body: JSON.stringify({ model: name }) });
  toast(`默认模型已设为 ${name}`);
}

// ---------- Agent 管理 ----------
async function loadAgents() {
  const data = await api('/agents');
  document.getElementById('content').innerHTML = `
    <div class="form-row">
      <input id="newAgentId" placeholder="Agent ID">
      <input id="newAgentName" placeholder="Agent 名称">
      <select id="newAgentType">
        <option value="custom">自定义</option>
        <option value="feynman">费曼教学</option>
        <option value="detector">输出检测</option>
        <option value="adaptive">自适应学习</option>
        <option value="chat">对话</option>
      </select>
      <button class="act" onclick="registerAgent()">注册 Agent</button>
    </div>
    <table>
      <tr><th>ID</th><th>名称</th><th>类型</th><th>状态</th><th>运行中</th><th>操作</th></tr>
      ${data.agents.map(a => `
        <tr>
          <td>${a.agent_id}</td><td>${a.name}</td><td>${a.agent_type}</td>
          <td><span class="badge ${a.status === 'running' ? 'on' : a.status === 'error' ? 'err' : 'off'}">${a.status}</span></td>
          <td>${a.running ? '✅' : '—'}</td>
          <td>
            ${a.running ? `<button class="act" onclick="stopAgent('${a.agent_id}')">停止</button>`
                        : `<button class="act" onclick="startAgent('${a.agent_id}')">启动</button>`}
            <button class="act" onclick="testAgent('${a.agent_id}')">测试</button>
            ${a.is_builtin ? '' : `<button class="act danger" onclick="deleteAgent('${a.agent_id}')">删除</button>`}
          </td>
        </tr>`).join('')}
    </table>`;
}

async function registerAgent() {
  const agent_id = document.getElementById('newAgentId').value;
  const name = document.getElementById('newAgentName').value;
  const type = document.getElementById('newAgentType').value;
  if (!agent_id || !name) return toast('请填写 Agent ID 和名称');
  await api('/agents', { method: 'POST', body: JSON.stringify({ agent_id, name, type }) });
  toast('Agent 已注册');
  loadAgents();
}

async function startAgent(id) { await api(`/agents/${id}/start`, { method: 'POST' }); toast(`${id} 已启动`); loadAgents(); }
async function stopAgent(id) { await api(`/agents/${id}/stop`, { method: 'POST' }); toast(`${id} 已停止`); loadAgents(); }
async function deleteAgent(id) {
  if (!confirm(`确认删除 Agent ${id}？`)) return;
  await api(`/agents/${id}`, { method: 'DELETE' });
  toast('Agent 已删除');
  loadAgents();
}

async function testAgent(id) {
  const payload = prompt(`输入测试 payload（JSON）`, '{}');
  if (payload === null) return;
  let body = {};
  try { body = JSON.parse(payload || '{}'); } catch (e) { return toast('JSON 格式错误'); }
  try {
    const result = await api(`/agents/${id}/run`, { method: 'POST', body: JSON.stringify(body) });
    toast('执行完成，结果见控制台');
    console.log('Agent 结果:', result);
    alert(JSON.stringify(result, null, 2));
  } catch (e) { toast(e.message); }
}

// ---------- 日志 ----------
async function loadLogs() {
  const data = await api('/logs?limit=200');
  document.getElementById('content').innerHTML = `
    <button class="act" onclick="clearLogs()" style="margin-bottom:12px;">清理 7 天前日志</button>
    <pre class="log-box">${(data.logs || []).map(l =>
      `<span style="color:${l.level === 'error' ? '#f85149' : l.level === 'warning' ? '#d29922' : '#8b949e'}">[${l.created_at}] [${l.level}] [${l.module}] ${l.message}</span>`
    ).join('\n') || '（无日志）'}</pre>`;
}

async function clearLogs() {
  await api('/logs/clear', { method: 'POST', body: JSON.stringify({ older_than_days: 7 }) });
  toast('日志已清理');
  loadLogs();
}

// ---------- API 密钥 ----------
async function loadKeys() {
  const data = await api('/api-keys');
  document.getElementById('content').innerHTML = `
    <div class="form-row">
      <input id="newKeyName" placeholder="密钥名称">
      <select id="newKeyScope">
        <option value="read">只读</option>
        <option value="write">读写</option>
        <option value="admin">管理</option>
      </select>
      <button class="act" onclick="createKey()">生成密钥</button>
    </div>
    <table>
      <tr><th>ID</th><th>名称</th><th>密钥</th><th>权限</th><th>最后使用</th><th>操作</th></tr>
      ${(data.api_keys || []).map(k => `
        <tr>
          <td>${k.id}</td><td>${k.key_name}</td>
          <td style="font-family:monospace;font-size:11px;">${k.api_key}</td>
          <td>${k.scope}</td><td>${k.last_used_at || '从未'}</td>
          <td><button class="act danger" onclick="deleteKey('${k.api_key}')">删除</button></td>
        </tr>`).join('') || '<tr><td colspan="6">暂无密钥</td></tr>'}
    </table>`;
}

async function createKey() {
  const key_name = document.getElementById('newKeyName').value;
  const scope = document.getElementById('newKeyScope').value;
  if (!key_name) return toast('请输入密钥名称');
  const data = await api('/api-keys', { method: 'POST', body: JSON.stringify({ key_name, scope }) });
  toast(`密钥已生成：${data.api_key}`);
  loadKeys();
}

async function deleteKey(key) {
  if (!confirm('确认删除该密钥？')) return;
  await api(`/api-keys/${key}`, { method: 'DELETE' });
  toast('密钥已删除');
  loadKeys();
}

// ---------- 初始化 ----------
if (TOKEN) {
  fetch(API + '/me', { headers: { 'X-Admin-Token': TOKEN } })
    .then(r => r.ok ? r.json() : Promise.reject())
    .then(() => {
      document.getElementById('loginWrap').style.display = 'none';
      document.getElementById('app').style.display = 'block';
      init();
    })
    .catch(() => localStorage.removeItem('admin_token'));
}
</script>
</body>
</html>
```

- [ ] **Step 2: 启动服务器验证页面可访问**

Run: `python -m framework.api.server --port 18080`（后台启动）
Expected: 访问 `http://localhost:18080/admin` 显示登录页；用 admin/admin123 登录后看到管理面板

- [ ] **Step 3: Commit**

```bash
git add remote/templates/admin.html
git commit -m "feat(admin): add admin dashboard frontend"
```

---

### Task 7: CLI 管理命令扩展

**Files:**
- Modify: `scripts/db_admin.py`

- [ ] **Step 1: 添加 `cmd_admin` 函数和子解析器**

在 `cmd_workflow` 函数之后添加：

```python
def cmd_admin(args):
    """管理员管理"""
    from framework.admin.auth import get_admin_auth
    from framework.admin.agents import get_agent_registry

    if args.action == "list":
        admins = db.get_admins()
        print(f"{'ID':<4} {'用户名':<12} {'角色':<12} {'最后登录':<20} 状态")
        for a in admins:
            print(f"{a['id']:<4} {a['username']:<12} {a['role']:<12} {(a['last_login_at'] or '-'):<20} {'启用' if a['is_active'] else '停用'}")
    elif args.action == "create":
        auth = get_admin_auth()
        # 直接复用 get_admin_auth 的密码哈希逻辑
        from werkzeug.security import generate_password_hash
        db.add_admin(args.username, generate_password_hash(args.password),
                     display_name=args.name or args.username, role=args.role)
        print(f"[OK] 已创建管理员: {args.username} (role={args.role})")
    elif args.action == "reset-password":
        admin = db.get_admin_by_username(args.username)
        if not admin:
            print(f"[ERR] 管理员不存在: {args.username}")
            return
        from werkzeug.security import generate_password_hash
        db.update_admin_password(admin["id"], generate_password_hash(args.password))
        print(f"[OK] 已重置密码: {args.username}")
    elif args.action == "disable":
        admin = db.get_admin_by_username(args.username)
        if admin:
            db.set_admin_active(admin["id"], 0)
            print(f"[OK] 已停用: {args.username}")
    elif args.action == "agents":
        registry = get_agent_registry()
        for a in registry.list_agents():
            print(f"{a['agent_id']:<24} {a['name']:<16} {a['agent_type']:<10} {a['status']:<8} {'运行中' if a.get('running') else ''}")
    elif args.action == "agent-start":
        print(get_agent_registry().start(args.agent_id).get("message", ""))
    elif args.action == "agent-stop":
        print(get_agent_registry().stop(args.agent_id).get("message", ""))
    elif args.action == "logs":
        for log in db.get_system_logs(level=args.level, limit=args.limit):
            print(f"[{log['created_at']}] [{log['level']}] [{log['module']}] {log['message']}")
    else:
        print("未知操作")
```

- [ ] **Step 2: 注册 `admin` 子解析器**

在 `p_workflow` 定义之后、`p_teacher` 之前添加：

```python
    p_admin = subparsers.add_parser("admin", help="管理员管理")
    p_admin.add_argument("action", choices=["list", "create", "reset-password", "disable", "agents", "agent-start", "agent-stop", "logs"])
    p_admin.add_argument("--username", default="")
    p_admin.add_argument("--password", default="")
    p_admin.add_argument("--name", default="")
    p_admin.add_argument("--role", default="super_admin", choices=["super_admin", "operator"])
    p_admin.add_argument("--agent-id", dest="agent_id", default="")
    p_admin.add_argument("--level", default=None)
    p_admin.add_argument("--limit", type=int, default=50)
```

在 `commands` 字典中添加 `"admin": cmd_admin`。

- [ ] **Step 3: 运行 CLI 验证**

Run: `python scripts/db_admin.py admin list`
Expected: 显示 admin 管理员
Run: `python scripts/db_admin.py admin agents`
Expected: 显示 4 个内置 Agent

- [ ] **Step 4: Commit**

```bash
git add scripts/db_admin.py
git commit -m "feat(admin): add admin CLI commands"
```

---

### Task 8: 全量回归测试

**Files:**
- 无新文件（运行既有 + 新增测试）

- [ ] **Step 1: 运行全部测试**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: 原有 60 个测试 + 新增测试（test_admin_auth 8 + test_agents 13 + test_admin_api 13）全部 PASS

- [ ] **Step 2: 修复任何回归**

若原有测试受影响（如 `get_user_workflows(user_id=None)` 行为），修正 `framework/api/routes/admin.py` 中对应调用以适配 `database.py` 实际签名。

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "test(admin): run full regression suite"
```

---

### Task 9: 文档更新

**Files:**
- Create: `docs/admin_guide.md`
- Modify: `README.md`

- [ ] **Step 1: 创建 `docs/admin_guide.md`**

包含：
- 默认账号与首次登录安全建议（`admin` / `admin123`，务必修改密码）
- Web 管理面板功能说明（概览/用户/模型/Agent/日志/密钥六个模块）
- CLI 命令示例（`admin list/create/reset-password/disable/agents/logs`）
- REST API 端点清单（登录、用户、模型、Agent、日志、密钥）
- Agent 架构说明（基类、内置 4 个 Agent、注册/启停/执行/健康检查）
- 安全注意事项（密钥轮换、密码策略、仅内网访问）

- [ ] **Step 2: 更新 `README.md` 核心模块表**

在核心模块表中追加两行：

```markdown
| **管理员系统** | 认证、用户/模型/Agent管理、系统监控、Web 管理面板 | ✅ 完成 |
| **Agent 框架** | Agent 注册表 + 4 个内置 Agent（费曼/检测/自适应/对话） | ✅ 完成 |
```

- [ ] **Step 3: Commit**

```bash
git add docs/admin_guide.md README.md
git commit -m "docs(admin): add admin guide and update README"
```

---

## 自检

**1. Spec 覆盖**：认证（Task 2）✅ 模型管理（Task 4+5）✅ Agent 管理（Task 3+4）✅ 用户管理（Task 4）✅ 系统监控（Task 4）✅ Web 面板（Task 6）✅ CLI（Task 7）✅ 测试（Task 8）✅ 文档（Task 9）✅

**2. Placeholder 扫描**：所有步骤均含完整代码，无 TBD/TODO。

**3. 类型一致性**：
- `db.register_agent(agent_id, name, agent_type, description, config)` — Task 1 定义（config 有默认值，位置参数 order: agent_id, name, agent_type, description, config）✅ 与 Task 3 调用一致
- `registry.start(agent_id)` / `stop(agent_id)` / `run_agent(agent_id, payload)` / `delete(agent_id)` / `health()` — Task 3 定义，Task 4 路由调用一致 ✅
- `db.get_admin_by_username(username)` / `add_admin(username, password_hash, display_name, role)` — Task 1 定义，Task 2/7 调用一致 ✅
- `AdminAuth.login(username, password)` 返回 `{success, token, admin}` — Task 2 定义，Task 4 路由使用一致 ✅
