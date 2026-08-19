# -*- coding: utf-8 -*-
"""
LumiLearn — P0-3 日志归档与保留策略测试

覆盖：
  - 保留期配置：set_policy / get_policies / 非法表名
  - 单表归档：超期行导出 JSONL 并删除、新行保留、空表安全
  - max_rows 超量归档：超过行数上限的最老行被归档
  - agent_call_log FK 保护：被自积累知识库引用的行跳过
  - run_policy 一键执行：三表报告 + 单表失败降级
  - 统计与归档列表：get_stats / list_archives
"""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.log_retention import (
    LogRetentionManager, get_log_retention_manager, LOG_TABLES,
)


def _insert_old_system_log(n: int = 1, days: int = 40):
    """插入 n 条超期系统日志（created_at 手工回溯）"""
    from framework.database import db
    ts = datetime(2020, 1, 1, 12, 0, 0).strftime("%Y-%m-%d %H:%M:%S")
    for i in range(n):
        db._execute(
            "INSERT INTO system_logs (level, module, message, created_at) "
            "VALUES ('info', 'test', ?, ?)",
            (f"old_log_{i}", ts))


def _insert_fresh_system_log(n: int = 1):
    """插入 n 条新系统日志（默认 created_at = now）"""
    from framework.database import db
    for i in range(n):
        db._execute(
            "INSERT INTO system_logs (level, module, message) "
            "VALUES ('info', 'test', ?)",
            (f"fresh_log_{i}",))


class TestLogRetentionConfig(unittest.TestCase):
    """保留期配置"""

    def _fresh_manager(self) -> LogRetentionManager:
        # 独立实例避免单例状态跨测试残留
        return LogRetentionManager()

    def test_default_policy(self):
        mgr = self._fresh_manager()
        policies = mgr.get_policies()
        self.assertEqual(set(policies.keys()), set(LOG_TABLES))
        self.assertGreater(policies["system_logs"]["retention_days"], 0)
        self.assertGreater(policies["reasoning_logs"]["max_rows"], 0)

    def test_set_policy_updates(self):
        mgr = self._fresh_manager()
        mgr.set_policy("system_logs", retention_days=7, max_rows=1000)
        cfg = mgr.get_policies()["system_logs"]
        self.assertEqual(cfg["retention_days"], 7)
        self.assertEqual(cfg["max_rows"], 1000)

    def test_set_policy_clamps(self):
        mgr = self._fresh_manager()
        mgr.set_policy("system_logs", retention_days=0, max_rows=1)
        cfg = mgr.get_policies()["system_logs"]
        self.assertGreaterEqual(cfg["retention_days"], 1)
        self.assertGreaterEqual(cfg["max_rows"], 100)

    def test_unknown_table_raises(self):
        mgr = self._fresh_manager()
        with self.assertRaises(ValueError):
            mgr.set_policy("no_such_table", retention_days=7)


class TestArchiveSystemLogs(unittest.TestCase):
    """超期日志归档"""

    def test_old_rows_archived_and_deleted(self):
        from framework.database import db
        mgr = LogRetentionManager()
        _insert_old_system_log(3)
        report = mgr.archive("system_logs", older_than_days=7)
        self.assertEqual(report["archived"], 3)
        self.assertEqual(report["kept"], 0)
        self.assertTrue(report["file_path"].endswith(".jsonl"))
        self.assertTrue(os.path.exists(report["file_path"]))
        # 主表已清空
        row = db._query_one("SELECT COUNT(*) AS n FROM system_logs")
        self.assertEqual(row["n"], 0)
        # 归档文件有 3 行 JSONL
        with open(report["file_path"], encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        self.assertEqual(len(lines), 3)
        import json
        first = json.loads(lines[0])
        self.assertIn("_archived_at", first)
        self.assertEqual(first["message"], "old_log_0")

    def test_fresh_rows_kept(self):
        from framework.database import db
        mgr = LogRetentionManager()
        _insert_old_system_log(2)
        _insert_fresh_system_log(1)
        report = mgr.archive("system_logs", older_than_days=7)
        # 只归档超期的 2 条，新日志保留
        self.assertEqual(report["archived"], 2)
        self.assertEqual(report["kept"], 1)
        row = db._query_one("SELECT COUNT(*) AS n FROM system_logs")
        self.assertEqual(row["n"], 1)

    def test_empty_table_safe(self):
        mgr = LogRetentionManager()
        report = mgr.archive("system_logs")
        self.assertEqual(report["archived"], 0)
        self.assertEqual(report["kept"], 0)

    def test_max_rows_archives_overflow(self):
        from framework.database import db
        mgr = LogRetentionManager()
        # 插入 15 条新日志（保留期内），上限 10 → 最老 5 条被归档，最新 10 条保留
        _insert_fresh_system_log(15)
        report = mgr.archive("system_logs", older_than_days=7, max_rows=10)
        self.assertEqual(report["archived"], 5)
        self.assertEqual(report["kept"], 10)
        row = db._query_one("SELECT COUNT(*) AS n FROM system_logs")
        self.assertEqual(row["n"], 10)


class TestArchiveReasoningLogs(unittest.TestCase):
    """reasoning_logs 归档"""

    def test_archives_reasoning_logs(self):
        from framework.database import db
        mgr = LogRetentionManager()
        ts = "2020-01-01 12:00:00"
        db._execute(
            "INSERT INTO reasoning_logs (user_id, session_id, mode, topic, "
            "model_used, output, created_at) VALUES (1, 's', 'feynman', ?, "
            "'qwen2.5:7b', 'out', ?)", ("测试主题", ts))
        report = mgr.archive("reasoning_logs", older_than_days=7)
        self.assertEqual(report["archived"], 1)
        self.assertTrue(report["file_path"].endswith(".jsonl"))


class TestAgentCallLogFkProtection(unittest.TestCase):
    """agent_call_log 归档时保护被知识库引用的行"""

    def test_referenced_row_skipped(self):
        from framework.database import db
        mgr = LogRetentionManager()
        ts = "2020-01-01 12:00:00"
        # 两条超期调用日志（caller 必须是已注册的内置 Agent，满足 FK）
        db._execute(
            "INSERT INTO agent_call_log (call_id, caller_agent, target_agent, "
            "topic, created_at) VALUES ('old_call_1', 'feynman_teacher', "
            "'feynman_teacher', '主题A', ?)", (ts,))
        db._execute(
            "INSERT INTO agent_call_log (call_id, caller_agent, target_agent, "
            "topic, created_at) VALUES ('old_call_2', 'feynman_teacher', "
            "'feynman_teacher', '主题B', ?)", (ts,))
        call1 = db._query_one(
            "SELECT id FROM agent_call_log WHERE call_id='old_call_1'")

        # 知识库引用 old_call_1（FK 必须指向存在的 agent_call_log）
        db._execute(
            "INSERT INTO knowledge_accumulation (knowledge_id, topic, "
            "knowledge_type, content, source_agent, source_call_id) "
            "VALUES ('k_' || ?, '主题A', 'explanation', '内容', "
            "'feynman_teacher', ?)", (str(call1["id"]), call1["id"]))

        report = mgr.archive("agent_call_log", older_than_days=7)
        # 被引用的 old_call_1 跳过，old_call_2 被归档
        self.assertEqual(report["skipped_referenced"], 1)
        self.assertEqual(report["archived"], 1)
        self.assertEqual(report["kept"], 1)
        left = db._query("SELECT call_id FROM agent_call_log")
        self.assertEqual([r["call_id"] for r in left], ["old_call_1"])

    def test_unreferenced_rows_archived(self):
        mgr = LogRetentionManager()
        from framework.database import db
        ts = "2020-01-01 12:00:00"
        db._execute(
            "INSERT INTO agent_call_log (call_id, caller_agent, target_agent, "
            "topic, created_at) VALUES ('unref_1', 'feynman_teacher', "
            "'fact_checker', '主题', ?)", (ts,))
        report = mgr.archive("agent_call_log", older_than_days=7)
        self.assertEqual(report["skipped_referenced"], 0)
        self.assertEqual(report["archived"], 1)


class TestRunPolicy(unittest.TestCase):
    """一键执行"""

    def test_run_policy_archives_all_tables(self):
        mgr = LogRetentionManager()
        _insert_old_system_log(2)
        from framework.database import db
        ts = "2020-01-01 12:00:00"
        db._execute(
            "INSERT INTO agent_call_log (call_id, caller_agent, target_agent, "
            "topic, created_at) VALUES ('policy_1', 'feynman_teacher', "
            "'feynman_teacher', '主题', ?)", (ts,))
        result = mgr.run_policy()
        self.assertEqual(set(result["results"].keys()),
                         {"system_logs", "reasoning_logs", "agent_call_log"})
        self.assertEqual(result["results"]["system_logs"]["archived"], 2)
        self.assertGreaterEqual(result["total_archived"], 3)

    def test_run_policy_selected_tables(self):
        mgr = LogRetentionManager()
        result = mgr.run_policy(tables=["system_logs"])
        self.assertEqual(set(result["results"].keys()), {"system_logs"})


class TestStatsAndArchives(unittest.TestCase):
    """统计与归档列表"""

    def test_get_stats_structure(self):
        mgr = LogRetentionManager()
        _insert_fresh_system_log(2)
        stats = mgr.get_stats()
        self.assertEqual(set(stats["tables"].keys()), set(LOG_TABLES))
        self.assertEqual(stats["tables"]["system_logs"]["rows"], 2)
        self.assertGreaterEqual(stats["db_size_bytes"], 0)
        self.assertIsInstance(stats["archives"], list)

    def test_list_archives_filter(self):
        mgr = LogRetentionManager()
        _insert_old_system_log(1)
        mgr.archive("system_logs", older_than_days=7)
        all_archives = mgr.list_archives()
        self.assertEqual(len(all_archives), 1)
        self.assertEqual(all_archives[0]["table"], "system_logs")
        filtered = mgr.list_archives(table="system_logs")
        self.assertEqual(len(filtered), 1)
        empty = mgr.list_archives(table="reasoning_logs")
        self.assertEqual(len(empty), 0)


class TestSingleton(unittest.TestCase):
    def test_singleton(self):
        m1 = get_log_retention_manager()
        m2 = get_log_retention_manager()
        self.assertIs(m1, m2)


if __name__ == "__main__":
    unittest.main()
