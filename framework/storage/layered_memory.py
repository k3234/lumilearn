# -*- coding: utf-8 -*-
"""
三层记忆系统服务

- 短期记忆（short）：绑定会话，24 小时后过期，会话内即时上下文
- 中期记忆（mid）  ：按章节沉淀，长期有效
- 长期记忆（long） ：持久保存，可标记错题（is_wrong_answer=1），超量时淘汰最旧

存储层基于 framework.database 的单例 db（SQLite），完全离线可用。
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from framework.database import db


class LayeredMemory:
    """三层记忆服务：封装短期 / 中期 / 长期记忆的读写与压缩"""

    SHORT_TERM_TTL_HOURS = 24   # 短期记忆有效期（小时）
    LONG_TERM_LIMIT = 500       # 长期记忆数量上限

    # ------------------------------------------------------------------ #
    # 写入
    # ------------------------------------------------------------------ #

    def save_short_term(self, user_id: str, session_id: str, content: str,
                        topic: str = "") -> int:
        """写入短期记忆（24 小时后过期），返回记录 id"""
        expires_at = (datetime.now() + timedelta(hours=self.SHORT_TERM_TTL_HOURS)
                      ).strftime("%Y-%m-%d %H:%M:%S")
        return db.save_memory(
            user_id=user_id, memory_type="short",
            session_id=session_id, topic=topic or None,
            content=content, expires_at=expires_at)

    def save_mid_term(self, user_id: str, chapter: str, content: str,
                      topic: str = "") -> int:
        """写入中期记忆（按章节沉淀，无过期），返回记录 id"""
        return db.save_memory(
            user_id=user_id, memory_type="mid",
            chapter=chapter, topic=topic or None, content=content)

    def save_long_term(self, user_id: str, content: str, topic: str = "",
                       is_wrong_answer: int = 0) -> int:
        """写入长期记忆（持久保存），is_wrong_answer=1 标记错题，返回记录 id"""
        return db.save_memory(
            user_id=user_id, memory_type="long",
            topic=topic or None, content=content,
            is_wrong_answer=int(is_wrong_answer))

    # ------------------------------------------------------------------ #
    # 读取
    # ------------------------------------------------------------------ #

    def get_active_memories(self, user_id: str,
                            session_id: Optional[str] = None) -> List[Dict]:
        """查询未过期的短期 + 中期记忆，可选按 session 过滤"""
        return db.get_active_memories(user_id, session_id=session_id)

    def get_long_term_memories(self, user_id: str,
                               limit: int = 500) -> List[Dict]:
        """查询长期记忆（最新优先）"""
        return db.get_long_term_memories(user_id, limit=limit)

    # ------------------------------------------------------------------ #
    # 压缩 / 统计
    # ------------------------------------------------------------------ #

    def compact(self, user_id: Optional[str] = None) -> Dict:
        """
        记忆压缩：
        - 删除所有已过期的记忆（短期记忆自然过期）
        - 指定 user_id 时，若该用户长期记忆超过上限，淘汰最早的记录
        返回 {"expired_removed": n, "long_compacted": n}
        """
        expired_removed = db.delete_expired_memories()
        long_compacted = 0
        if user_id:
            long_compacted = self._compact_long_term(user_id)
        return {"expired_removed": expired_removed,
                "long_compacted": long_compacted}

    def _compact_long_term(self, user_id: str) -> int:
        """长期记忆超过 LONG_TERM_LIMIT 条时，淘汰最早的记录，返回淘汰条数"""
        limit = self.LONG_TERM_LIMIT
        rows = db.get_long_term_memories(user_id, limit=limit + 1)
        if len(rows) <= limit:
            return 0
        keep_ids = [r["id"] for r in rows[:limit]]
        placeholders = ",".join("?" for _ in keep_ids)
        cur = db._execute(
            f"DELETE FROM layered_memory "
            f"WHERE user_id = ? AND memory_type = 'long' "
            f"AND id NOT IN ({placeholders})",
            (user_id, *keep_ids))
        return cur.rowcount

    def get_memory_stats(self, user_id: str) -> Dict:
        """返回该用户各类型记忆数量 {"short": n, "mid": n, "long": n, "total": n}"""
        rows = db._query(
            """SELECT memory_type, COUNT(*) AS cnt FROM layered_memory
               WHERE user_id = ? GROUP BY memory_type""",
            (user_id,))
        stats: Dict = {"short": 0, "mid": 0, "long": 0, "total": 0}
        for r in rows:
            stats[r["memory_type"]] = r["cnt"]
            stats["total"] += r["cnt"]
        return stats
