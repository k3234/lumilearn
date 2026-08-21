# -*- coding: utf-8 -*-
"""
三层记忆系统 — 单元测试

依赖 tests/conftest.py 的 autouse fixture isolated_db：
每个用例使用独立临时 SQLite 库，完全离线、不加载模型。
"""
import unittest

from framework.database import db
from framework.storage.layered_memory import LayeredMemory


class TestLayeredMemory(unittest.TestCase):
    """三层记忆系统测试"""

    def setUp(self):
        self.mem = LayeredMemory()
        self.user_id = "1"

    def test_save_short_term(self):
        """写入短期记忆后，get_active_memories 能读到"""
        mem_id = self.mem.save_short_term(
            self.user_id, session_id="sess-1", content="函数定义：f(x)=x+1", topic="函数")
        self.assertGreater(mem_id, 0)

        active = self.mem.get_active_memories(self.user_id, session_id="sess-1")
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["memory_type"], "short")
        self.assertEqual(active[0]["content"], "函数定义：f(x)=x+1")
        self.assertEqual(active[0]["session_id"], "sess-1")
        # 短期记忆带过期时间
        self.assertIsNotNone(active[0]["expires_at"])

        # 不带 session 过滤也应能查到
        active_all = self.mem.get_active_memories(self.user_id)
        self.assertGreaterEqual(len(active_all), 1)

    def test_short_term_expires(self):
        """手动构造已过期短期记忆，compact 后应被删除"""
        # 正常短期记忆（未过期）
        self.mem.save_short_term(
            self.user_id, session_id="sess-ok", content="有效记忆")
        # 手动构造已过期的短期记忆
        db.save_memory(
            user_id=self.user_id, memory_type="short", session_id="sess-expired",
            content="过期记忆", expires_at="2000-01-01 00:00:00")

        # 过期记忆不应出现在活跃记忆中
        active = self.mem.get_active_memories(self.user_id)
        contents = [r["content"] for r in active]
        self.assertIn("有效记忆", contents)
        self.assertNotIn("过期记忆", contents)

        result = self.mem.compact()
        self.assertEqual(result["expired_removed"], 1)

        # compact 后数据库中已无过期记录
        rows = db._query(
            "SELECT * FROM layered_memory WHERE content = ?", ("过期记忆",))
        self.assertEqual(len(rows), 0)
        # 有效记忆保留
        rows = db._query(
            "SELECT * FROM layered_memory WHERE content = ?", ("有效记忆",))
        self.assertEqual(len(rows), 1)

    def test_save_long_term_wrong_answer(self):
        """is_wrong_answer=1 的长期记忆可查询"""
        mem_id = self.mem.save_long_term(
            self.user_id, content="勾股定理：a²+b²=c²",
            topic="几何", is_wrong_answer=1)
        self.assertGreater(mem_id, 0)

        long_term = self.mem.get_long_term_memories(self.user_id)
        self.assertEqual(len(long_term), 1)
        self.assertEqual(long_term[0]["memory_type"], "long")
        self.assertEqual(long_term[0]["is_wrong_answer"], 1)
        self.assertEqual(long_term[0]["topic"], "几何")
        # 长期记忆无过期时间
        self.assertIsNone(long_term[0]["expires_at"])

        # 长期记忆不应出现在短期/中期活跃记忆中
        active = self.mem.get_active_memories(self.user_id)
        self.assertNotIn("勾股定理：a²+b²=c²", [r["content"] for r in active])

    def test_compact_stats(self):
        """compact 返回统计 dict，get_memory_stats 返回各类型数量"""
        self.mem.save_short_term(self.user_id, session_id="s1", content="短期1")
        self.mem.save_short_term(self.user_id, session_id="s2", content="短期2")
        self.mem.save_mid_term(self.user_id, chapter="第1章", content="中期1")
        self.mem.save_long_term(self.user_id, content="长期1")
        # 一条已过期记忆
        db.save_memory(
            user_id=self.user_id, memory_type="short", session_id="s3",
            content="过期", expires_at="2000-01-01 00:00:00")

        result = self.mem.compact(user_id=self.user_id)
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result.keys()), {"expired_removed", "long_compacted"})
        self.assertIsInstance(result["expired_removed"], int)
        self.assertIsInstance(result["long_compacted"], int)
        self.assertEqual(result["expired_removed"], 1)
        self.assertEqual(result["long_compacted"], 0)

        stats = self.mem.get_memory_stats(self.user_id)
        self.assertIsInstance(stats, dict)
        self.assertEqual(set(stats.keys()), {"short", "mid", "long", "total"})
        self.assertEqual(stats["short"], 2)
        self.assertEqual(stats["mid"], 1)
        self.assertEqual(stats["long"], 1)
        self.assertEqual(stats["total"], 4)


if __name__ == "__main__":
    unittest.main()
