# -*- coding: utf-8 -*-
"""
LumiLearn 多轮对话持久化（chat_history）
========================================
轻量独立模块：为费曼教学 / 通用对话提供多轮会话上下文存储。

设计原则（核心设备压力约束）：
- 独立于 framework/database.py（避免改动 150KB 大文件），但共享同一个 SQLite 库
  （LUMILEARN_DB_PATH 环境变量优先，默认项目根 lumilearn.db）。
- 惰性连接：首次调用方法时才打开数据库，空闲不占用连接与内存。
- 纯标准库 sqlite3，零第三方依赖，单次写入为瞬时操作。

结构：chat_sessions（会话头）+ chat_history（消息，构成多轮上下文）。
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL DEFAULT 0,
    title      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role       TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content    TEXT NOT NULL,
    model      TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chat_history_session
    ON chat_history (session_id, id);
"""


def _default_db_path() -> str:
    """与 framework/database._get_db_path 同源解析：环境变量优先，默认项目根。"""
    env_path = os.environ.get("LUMILEARN_DB_PATH")
    if env_path:
        return env_path
    return str(Path(__file__).resolve().parent.parent.parent / "lumilearn.db")


class ConversationStore:
    """多轮对话持久化存储（惰性连接，线程安全模式同 database.py）"""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def db_path(self) -> str:
        return self._db_path or _default_db_path()

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            # SQLite 默认不启用外键；开启后 chat_history 才能随会话级联删除
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ---------- 会话 ----------

    def create_session(self, title: str, user_id: int = 0) -> int:
        """新建会话，返回 session_id。"""
        conn = self._connect()
        cur = conn.execute(
            "INSERT INTO chat_sessions (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, title, self._now(), self._now()),
        )
        conn.commit()
        return int(cur.lastrowid)

    def list_sessions(self, user_id: int = 0, limit: int = 20) -> List[Dict]:
        """按最近更新排序列出会话（含消息数、最后一条消息预览）。"""
        conn = self._connect()
        rows = conn.execute(
            """
            SELECT s.*,
                   (SELECT COUNT(*) FROM chat_history h WHERE h.session_id = s.id) AS msg_count,
                   (SELECT content FROM chat_history h
                     WHERE h.session_id = s.id ORDER BY h.id DESC LIMIT 1) AS last_message
            FROM chat_sessions s
            WHERE s.user_id = ?
            ORDER BY s.updated_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_session(self, session_id: int) -> Optional[Dict]:
        conn = self._connect()
        row = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(row) if row else None

    def delete_session(self, session_id: int) -> bool:
        """删除会话（chat_history 级联删除）。"""
        conn = self._connect()
        cur = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        conn.commit()
        return cur.rowcount > 0

    # ---------- 消息 ----------

    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        model: Optional[str] = None,
    ) -> int:
        """追加一条消息，返回 message_id；同时刷新会话 updated_at。"""
        conn = self._connect()
        cur = conn.execute(
            "INSERT INTO chat_history (session_id, role, content, model, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, model, self._now()),
        )
        conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (self._now(), session_id))
        conn.commit()
        return int(cur.lastrowid)

    def get_messages(self, session_id: int, limit: Optional[int] = None) -> List[Dict]:
        """按时间正序取会话全部（或末尾 limit 条）消息。"""
        conn = self._connect()
        if limit:
            rows = conn.execute(
                "SELECT * FROM (SELECT * FROM chat_history WHERE session_id = ? "
                "ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
                (session_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM chat_history WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def clear_session(self, session_id: int) -> int:
        """清空某会话的消息，返回删除条数。"""
        conn = self._connect()
        cur = conn.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
        conn.commit()
        return cur.rowcount


# 全局单例：惰性连接，空闲零开销（核心设备压力友好）
conversation_store = ConversationStore()
