# -*- coding: utf-8 -*-
"""
LumiLearn — file_compat 兼容层测试

覆盖：
  - test_sqlite_path：SQLite 正常时 get/set/list/delete 走数据库路径
  - test_file_fallback：SQLite 抛 sqlite3.Error 时自动降级到文件存储
  - test_logs_written：降级日志写入 logs.jsonl（文件模式）或 system_logs 表（SQLite 模式）
"""

import json
import os
import sys
import tempfile
import sqlite3
from pathlib import Path

import pytest

# 确保项目根可被 import
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from framework.storage.file_compat import FileStorage, StorageRouter


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def store_dir(tmp_path):
    """每个测试使用独立的临时 store 目录。"""
    d = tmp_path / "store"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def file_storage(store_dir):
    return FileStorage(store_dir=store_dir)


@pytest.fixture
def sqlite_db(tmp_path):
    """创建一个带 key_value_store 表的内存 SQLite 数据库，返回 connection。"""
    db_path = str(tmp_path / "test_compat.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS key_value_store (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            key        TEXT UNIQUE NOT NULL,
            value      TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            level      TEXT DEFAULT 'info',
            module     TEXT DEFAULT '',
            message    TEXT DEFAULT '',
            detail     TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def mock_db_manager(sqlite_db):
    """
    模拟 DatabaseManager 的最小接口（_query / _execute / add_system_log / get_system_logs）。
    不继承真实类，避免导入整个 framework.database。
    """
    class FakeDB:
        def __init__(self, conn):
            self.conn = conn

        def _query(self, sql, params=()):
            cur = self.conn.execute(sql, params)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in rows]

        def _execute(self, sql, params=()):
            self.conn.execute(sql, params)
            self.conn.commit()

        def add_system_log(self, level, module, message, detail=""):
            self.conn.execute(
                "INSERT INTO system_logs (level, module, message, detail) VALUES (?, ?, ?, ?)",
                (level, module, message, detail),
            )
            self.conn.commit()
            return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        def get_system_logs(self, level=None, limit=100):
            if level:
                return self._query(
                    "SELECT * FROM system_logs WHERE level = ? ORDER BY id DESC LIMIT ?",
                    (level, limit),
                )
            return self._query(
                "SELECT * FROM system_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            )

    return FakeDB(sqlite_db)


# ------------------------------------------------------------------ #
# test_sqlite_path：SQLite 正常路径下的 get / set / delete / list
# ------------------------------------------------------------------ #

class TestSQLitePath:
    def test_set_and_get(self, mock_db_manager):
        router = StorageRouter(db=mock_db_manager)
        result = router.set("user/1", {"name": "小明", "role": "student"})
        assert result["key"] == "user/1"

        got = router.get("user/1")
        assert got is not None
        assert got["key"] == "user/1"

    def test_list(self, mock_db_manager):
        router = StorageRouter(db=mock_db_manager)
        router.set("user/1", {"name": "小明"})
        router.set("user/2", {"name": "小红"})
        router.set("teacher/1", {"name": "王老师"})

        all_items = router.list()
        assert len(all_items) == 3

        users = router.list(prefix="user/")
        assert len(users) == 2

    def test_delete(self, mock_db_manager):
        router = StorageRouter(db=mock_db_manager)
        router.set("del_key", "should_gone")
        assert router.get("del_key") is not None

        assert router.delete("del_key") is True
        assert router.get("del_key") is None

    def test_delete_nonexistent(self, mock_db_manager):
        router = StorageRouter(db=mock_db_manager)
        assert router.delete("no_such_key") is True  # 幂等

    def test_system_logs_write_and_read(self, mock_db_manager):
        router = StorageRouter(db=mock_db_manager)
        router.add_system_log("info", "test", "hello")
        logs = router.get_system_logs()
        assert len(logs) >= 1
        assert any(log["message"] == "hello" for log in logs)


# ------------------------------------------------------------------ #
# test_file_fallback：SQLite 抛 sqlite3.Error 时降级到文件存储
# ------------------------------------------------------------------ #

class FailingDB:
    """故意让所有 SQLite 操作抛出 sqlite3.Error 的假 DB。"""

    def _query(self, sql, params=()):
        raise sqlite3.OperationalError("simulated sqlite failure")

    def _execute(self, sql, params=()):
        raise sqlite3.OperationalError("simulated sqlite failure")

    def add_system_log(self, level, module, message, detail=""):
        raise sqlite3.OperationalError("simulated sqlite failure")

    def get_system_logs(self, level=None, limit=100):
        raise sqlite3.OperationalError("simulated sqlite failure")


class TestFileFallback:
    def test_get_falls_back(self, store_dir):
        router = StorageRouter(db=FailingDB(), fallback=FileStorage(store_dir=store_dir))
        result = router.set("fb_key", {"x": 1})
        # FileStorage.set 返回 {_meta, data} 结构（无顶层 key 字段）
        assert result["data"] == {"x": 1}

        got = router.get("fb_key")
        assert got is not None
        assert got["data"]["x"] == 1

    def test_list_falls_back(self, store_dir):
        router = StorageRouter(db=FailingDB(), fallback=FileStorage(store_dir=store_dir))
        router.set("a/1", {"v": 1})
        router.set("a/2", {"v": 2})
        router.set("b/1", {"v": 3})

        items = router.list()
        assert len(items) == 3

        a_items = router.list(prefix="a/")
        assert len(a_items) == 2

    def test_delete_falls_back(self, store_dir):
        router = StorageRouter(db=FailingDB(), fallback=FileStorage(store_dir=store_dir))
        router.set("del_fb", "bye")
        assert router.get("del_fb") is not None
        assert router.delete("del_fb") is True
        assert router.get("del_fb") is None

    def test_system_logs_falls_back(self, store_dir):
        router = StorageRouter(db=FailingDB(), fallback=FileStorage(store_dir=store_dir))
        router.add_system_log("warning", "test", "db down")
        logs = router.get_system_logs()
        assert any(log.get("message") == "db down" for log in logs)

    def test_fallback_flag_set_after_failure(self, store_dir):
        router = StorageRouter(db=FailingDB(), fallback=FileStorage(store_dir=store_dir))
        router.set("k", "v")
        assert router._fallback_active is True

    def test_no_db_no_fallback_issues_no_error(self, store_dir):
        """没有传 db 参数时（db=None），StorageRouter 直接使用 fallback。"""
        router = StorageRouter(fallback=FileStorage(store_dir=store_dir))
        router.set("standalone", "yes")
        got = router.get("standalone")
        assert got is not None
        assert got["data"] == "yes"


# ------------------------------------------------------------------ #
# test_logs_written：验证降级日志被记录
# ------------------------------------------------------------------ #

class TestLogsWritten:
    def test_fallback_log_in_jsonl(self, store_dir):
        """降级时，FileStorage 的 _write_log 会写入 logs.jsonl。"""
        fb = FileStorage(store_dir=store_dir)
        router = StorageRouter(db=FailingDB(), fallback=fb)
        router.set("log_test", 1)

        log_file = store_dir / "logs.jsonl"
        assert log_file.exists()

        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 1

        last_entry = json.loads(lines[-1])
        assert last_entry["level"] == "warning"
        assert last_entry["module"] == "StorageRouter"
        assert "降级" in last_entry["message"]

    def test_fallback_log_content_detail(self, store_dir):
        fb = FileStorage(store_dir=store_dir)
        router = StorageRouter(db=FailingDB(), fallback=fb)
        router.get("any_key")  # 触发降级

        log_file = store_dir / "logs.jsonl"
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        entries = [json.loads(l) for l in lines]

        # 找到降级日志
        fallback_entries = [e for e in entries if e["module"] == "StorageRouter" and e["level"] == "warning"]
        assert len(fallback_entries) >= 1
        assert "SQLite" in fallback_entries[0].get("detail", "")

    def test_file_storage_own_log(self, store_dir):
        """FileStorage 自身写入的日志（如 get 损坏文件时 error 级别）。"""
        fb = FileStorage(store_dir=store_dir)
        fb._write_log("info", "test_module", "direct_log_test")

        log_file = store_dir / "logs.jsonl"
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        entries = [json.loads(l) for l in lines]

        assert any(e["message"] == "direct_log_test" for e in entries)
        assert any(e["level"] == "info" for e in entries)

    def test_get_system_logs_reads_jsonl(self, store_dir):
        fb = FileStorage(store_dir=store_dir)
        fb._write_log("info", "mod", "msg_a")
        fb._write_log("error", "mod", "msg_b")

        logs = fb.get_system_logs()
        assert len(logs) == 2
        assert logs[0]["message"] == "msg_b"  # 最新在前

        logs_info = fb.get_system_logs(level="info")
        assert len(logs_info) == 1
        assert logs_info[0]["message"] == "msg_a"

    def test_set_preserves_created_at(self, store_dir):
        """set 第二次调用时保留首次 created_at。"""
        fb = FileStorage(store_dir=store_dir)
        r1 = fb.set("persist", "v1")
        created_1 = r1["_meta"]["created_at"]

        import time
        time.sleep(0.01)

        r2 = fb.set("persist", "v2")
        created_2 = r2["_meta"]["created_at"]

        assert created_1 == created_2
        assert r2["_meta"]["updated_at"] != created_1
