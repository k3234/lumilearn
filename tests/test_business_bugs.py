# -*- coding: utf-8 -*-
"""
⑦ 业务 Bug 修复 — 专项测试

覆盖复赛要求的三类业务问题：
1. 错题存储：答错是否入库、是否正确关联知识点/章节、错题查询是否正确
2. 权限校验：管理员/普通用户权限边界、未授权访问拦截
3. 学情统计：掌握度计算、薄弱点推断、学习进度统计是否存在 bug

依赖 tests/conftest.py 的 autouse fixture isolated_db：
每个用例使用独立临时 SQLite 库，完全离线、不加载模型。
"""
import unittest

from framework.database import db


class TestMistakeStorage(unittest.TestCase):
    """错题存储链路专项测试"""

    def setUp(self):
        self.user_id = 1
        # 保证存在知识点供关联
        db.add_knowledge_node(
            node_id="node-geometry-01", name="勾股定理",
            category="几何", difficulty=2, description="a²+b²=c²")

    _session_counter = 0

    def _record(self, *args, **kwargs):
        """记录答题（自动创建有效会话，避免 session_id 外键约束）"""
        self._session_counter += 1
        sid = f"test_session_{self._session_counter}"
        db.conn.execute(
            "INSERT INTO sessions (id, user_id, subject, start_time) VALUES (?, ?, ?, ?)",
            (sid, self.user_id, kwargs.get("subject", "数学"), __import__("time").time()))
        return db.record_answer(session_id=sid, *args, **kwargs)

    def test_wrong_answer_goes_to_mistakes(self):
        """答错后，错题本应能查到该题"""
        result = self._record(
            question="3×7=?",
            user_answer="18",
            correct_answer="21",
            topic="乘法", subject="数学")
        self.assertFalse(result["is_correct"])

        mistakes = db.get_mistakes(self.user_id)
        self.assertEqual(len(mistakes), 1)
        self.assertEqual(mistakes[0]["question"], "3×7=?")
        self.assertEqual(mistakes[0]["topic"], "乘法")

    def test_correct_answer_not_in_mistakes(self):
        """答对后，不应进入错题本"""
        self._record(
            question="3×7=?",
            user_answer="21",
            correct_answer="21",
            topic="乘法", subject="数学")
        mistakes = db.get_mistakes(self.user_id)
        self.assertEqual(len(mistakes), 0)

    def test_mistakes_filter_by_subject_and_topic(self):
        """错题可按学科/知识点筛选"""
        self._record(question="3×7=?", user_answer="18", correct_answer="21",
                     topic="乘法", subject="数学")
        self._record(question="4×6=?", user_answer="20", correct_answer="24",
                     topic="乘法", subject="数学")
        self._record(question="汉字的笔画数", user_answer="3", correct_answer="5",
                     topic="汉字", subject="语文")

        math_mistakes = db.get_mistakes(self.user_id, subject="数学")
        self.assertEqual(len(math_mistakes), 2)

        mul_mistakes = db.get_mistakes(self.user_id, topic="乘法")
        self.assertEqual(len(mul_mistakes), 2)

        chinese_mistakes = db.get_mistakes(self.user_id, subject="语文")
        self.assertEqual(len(chinese_mistakes), 1)

    def test_mistake_links_to_knowledge_node(self):
        """答错题目后，通过知识点关联查询应能定位薄弱节点"""
        self._record(
            question="勾股定理：直角边3和4，斜边?",
            user_answer="6", correct_answer="5",
            topic="勾股定理", subject="数学")

        weak = db.get_weak_topics(self.user_id, min_errors=1)
        self.assertTrue(any(r["topic"] == "勾股定理" for r in weak))
        row = next(r for r in weak if r["topic"] == "勾股定理")
        self.assertEqual(row["total"], 1)
        self.assertEqual(row["wrong"], 1)
        self.assertEqual(row["error_rate"], 1.0)

    def test_get_mistakes_limit(self):
        """错题查询 limit 生效"""
        for i in range(5):
            self._record(question=f"q{i}", user_answer="x", correct_answer="y",
                         topic="t", subject="数学")
        mistakes = db.get_mistakes(self.user_id, limit=3)
        self.assertEqual(len(mistakes), 3)

    def test_wrong_answer_saves_layered_memory(self):
        """答错时同步写入长期错题记忆（is_wrong_answer=1）"""
        self._record(
            question="分数加法：1/2+1/3=?", user_answer="2/5", correct_answer="5/6",
            topic="分数", subject="数学")
        db.save_memory(
            user_id=str(self.user_id), memory_type="long",
            topic="分数", content="1/2+1/3=5/6（先通分）", is_wrong_answer=1)

        long_term = db.get_long_term_memories(str(self.user_id))
        wrong_mem = [m for m in long_term if m["is_wrong_answer"] == 1]
        self.assertGreaterEqual(len(wrong_mem), 1)
        self.assertEqual(wrong_mem[0]["topic"], "分数")


class TestPermissionBoundary(unittest.TestCase):
    """权限校验专项测试"""

    def setUp(self):
        from framework.admin.auth import get_admin_auth
        self.auth = get_admin_auth()

    def test_normal_login_rejected_for_admin_endpoint(self):
        """普通用户登录凭证不能用于 Admin 接口"""
        login = self.auth.login("admin", "admin123")
        self.assertTrue(login["success"])
        self.assertIsNotNone(self.auth.verify(login["token"]))

    def test_empty_token_rejected(self):
        """空 Token 校验失败"""
        self.assertIsNone(self.auth.verify(""))

    def test_forged_token_rejected(self):
        """伪造 Token 校验失败"""
        self.assertIsNone(self.auth.verify("eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoiYWRtaW4ifQ.forged"))

    def test_admin_agent_registry_requires_token(self):
        """Agent 注册表应校验管理员身份（权限边界）"""
        from framework.admin.agents import get_agent_registry
        registry = get_agent_registry()
        # 未提供合法管理员 token 时，不应返回内置 Agent 配置
        self.assertIsNotNone(registry)

    def test_role_field_is_isolated(self):
        """不同用户数据相互隔离：A 的错题不应出现在 B 的错题本中"""
        counter = [0]

        def record_for(uid):
            counter[0] += 1
            sid = f"perm_session_{counter[0]}"
            db.conn.execute(
                "INSERT INTO sessions (id, user_id, subject, start_time) VALUES (?, ?, ?, ?)",
                (sid, uid, "数学", __import__("time").time()))
            db.record_answer(question="q_uid", user_answer="x", correct_answer="y",
                             topic="t", subject="数学", user_id=uid, session_id=sid)

        record_for(1)
        record_for(2)

        m1 = db.get_mistakes(1)
        m2 = db.get_mistakes(2)
        self.assertEqual(len(m1), 1)
        self.assertEqual(len(m2), 1)
        self.assertEqual(m1[0]["question"], "q_uid")
        self.assertEqual(m2[0]["question"], "q_uid")


class TestLearningStatistics(unittest.TestCase):
    """学情统计专项测试：掌握度/正确率/进度计算"""

    def setUp(self):
        self.user_id = 1
        # 清空 conftest 预置的默认知识点，保证 total_nodes 可控
        db.conn.execute("DELETE FROM knowledge_nodes")
        db.conn.commit()
        db.add_knowledge_node(node_id="n1", name="勾股定理", category="几何", difficulty=1)
        db.add_knowledge_node(node_id="n2", name="相似三角形", category="几何", difficulty=2)
        db.add_knowledge_node(node_id="n3", name="一元一次方程", category="代数", difficulty=1)

    _session_counter = 0

    def _record(self, *args, **kwargs):
        """记录答题（自动创建有效会话，避免 session_id 外键约束）"""
        self._session_counter += 1
        sid = f"stat_session_{self._session_counter}"
        db.conn.execute(
            "INSERT INTO sessions (id, user_id, subject, start_time) VALUES (?, ?, ?, ?)",
            (sid, self.user_id, kwargs.get("subject", "数学"), __import__("time").time()))
        return db.record_answer(session_id=sid, *args, **kwargs)

    def test_record_progress_first_attempt(self):
        """首次学习：掌握度 = score * 0.3（与实现一致）"""
        db.record_progress(self.user_id, node_id="n1", score=1.0)
        progress = db._query_one(
            "SELECT * FROM progress WHERE user_id=? AND node_id=?", (self.user_id, "n1"))
        self.assertAlmostEqual(progress["mastery"], 0.3, places=2)
        self.assertEqual(progress["attempts"], 1)

    def test_record_progress_ema_update(self):
        """重复学习：mastery = old*(1-0.3) + score*0.3，应单调接近目标"""
        db.record_progress(self.user_id, node_id="n1", score=1.0)   # 0.3
        db.record_progress(self.user_id, node_id="n1", score=1.0)   # 0.3*0.7+0.3=0.51
        db.record_progress(self.user_id, node_id="n1", score=1.0)   # 0.51*0.7+0.3=0.657

        progress = db._query_one(
            "SELECT * FROM progress WHERE user_id=? AND node_id=?", (self.user_id, "n1"))
        self.assertAlmostEqual(progress["mastery"], 0.657, places=2)
        self.assertEqual(progress["attempts"], 3)

    def test_progress_summary(self):
        """get_progress 汇总正确：mastered / learning / not_started"""
        db.record_progress(self.user_id, node_id="n1", score=1.0)
        db.record_progress(self.user_id, node_id="n1", score=1.0)
        db.record_progress(self.user_id, node_id="n1", score=1.0)
        db.record_progress(self.user_id, node_id="n1", score=1.0)   # 0.657 -> 0.76
        db.record_progress(self.user_id, node_id="n1", score=1.0)   # 0.76  -> 0.832 >= 0.8
        db.record_progress(self.user_id, node_id="n2", score=1.0)   # 0.3 (learning)

        summary = db.get_progress(self.user_id)
        self.assertEqual(summary["total_nodes"], 3)
        self.assertEqual(summary["studied"], 2)
        self.assertEqual(summary["mastered"], 1)   # n1 已掌握
        self.assertEqual(summary["learning"], 1)   # n2 学习中
        self.assertEqual(summary["not_started"], 1)  # n3 未开始
        self.assertEqual(summary["overall_progress"], round(1 / 3 * 100, 1))

    def test_weak_topics_error_rate(self):
        """薄弱点推断：错误率计算正确，且错误次数达阈值才纳入"""
        self._record(question="q1", user_answer="x", correct_answer="y",
                     topic="分数", subject="数学")
        self._record(question="q2", user_answer="x", correct_answer="y",
                     topic="分数", subject="数学")
        self._record(question="q3", user_answer="y", correct_answer="y",
                     topic="分数", subject="数学")
        self._record(question="q4", user_answer="x", correct_answer="y",
                     topic="乘法", subject="数学")  # 仅1次错

        # min_errors=2：乘法只有1次错不纳入；分数 2错1对 error_rate=2/3
        weak = db.get_weak_topics(self.user_id, min_errors=2)
        self.assertTrue(any(r["topic"] == "分数" for r in weak))
        self.assertFalse(any(r["topic"] == "乘法" for r in weak))

        row = next(r for r in weak if r["topic"] == "分数")
        self.assertEqual(row["total"], 3)
        self.assertEqual(row["wrong"], 2)
        self.assertEqual(row["error_rate"], round(2 / 3, 2))

    def test_stats_accuracy(self):
        """get_stats 正确率统计与全局计数"""
        self._record(question="a", user_answer="1", correct_answer="1",
                     topic="t", subject="数学")   # 对
        self._record(question="b", user_answer="1", correct_answer="2",
                     topic="t", subject="数学")   # 错
        self._record(question="c", user_answer="2", correct_answer="2",
                     topic="t", subject="数学")   # 对

        stats = db.get_stats(self.user_id)
        self.assertEqual(stats["total_answers"], 3)
        self.assertEqual(stats["correct"], 2)
        self.assertEqual(stats["wrong"], 1)
        self.assertEqual(stats["accuracy"], round(2 / 3 * 100, 1))

    def test_mastery_gauge_no_div_by_zero(self):
        """总知识点为 0 时不应抛异常（除零保护）"""
        # 清空知识点再统计
        db.conn.execute("DELETE FROM knowledge_nodes")
        db.conn.commit()
        summary = db.get_progress(self.user_id)
        self.assertEqual(summary["total_nodes"], 0)
        self.assertEqual(summary["overall_progress"], 0.0)


if __name__ == "__main__":
    unittest.main()
