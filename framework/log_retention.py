# -*- coding: utf-8 -*-
"""
LumiLearn — 日志归档与保留策略（P0-3 / compliance 12.6）

对三张日志表提供统一的生命周期管理：
    system_logs     系统事件日志
    reasoning_logs  模型推理过程记录
    agent_call_log  Agent 调用日志

能力：
    1. 保留期配置（retention_days + max_rows，三表独立）
    2. 归档：超期/超量日志导出为 JSONL 归档文件后从主表删除
    3. 一键执行 run_policy()：按配置归档全部表并返回报告
    4. 统计与归档列表查询（存储膨胀监控）
    5. agent_call_log 归档保护：被自积累知识库（knowledge_accumulation）
       引用的行跳过，保证 FK 完整性

设计要点：
    - 依赖 framework.database.db 单例（_query / _execute）
    - 任何归档失败都不影响主流程，降级返回部分结果
    - 归档文件按表 + 时间戳命名，append 模式累积
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Dict, List, Optional

from framework.database import db

# 归档目录名（位于数据库文件同目录下）
_ARCHIVE_DIR = "logs_archive"

# 受管理日志表
LOG_TABLES = ("system_logs", "reasoning_logs", "agent_call_log")

# 默认保留策略（天 / 最大行数）
DEFAULT_POLICY = {
    "system_logs": {"retention_days": 30, "max_rows": 5000},
    "reasoning_logs": {"retention_days": 30, "max_rows": 5000},
    "agent_call_log": {"retention_days": 90, "max_rows": 10000},
}


class LogRetentionManager:
    """日志归档与保留策略管理器（单例）"""

    def __init__(self):
        self._policies: Dict[str, Dict] = {
            table: dict(cfg) for table, cfg in DEFAULT_POLICY.items()
        }
        self._lock = threading.RLock()

    # ============================================================
    # 配置
    # ============================================================
    def set_policy(self, table: str, retention_days: Optional[int] = None,
                   max_rows: Optional[int] = None) -> Dict:
        """
        配置单张日志表的保留策略。

        参数：
            table: 表名（system_logs / reasoning_logs / agent_call_log）
            retention_days: 保留天数（None 表示不修改）
            max_rows: 最大行数上限（None 表示不修改）

        返回：
            更新后的策略配置
        """
        if table not in LOG_TABLES:
            raise ValueError(f"未知日志表: {table}，可选 {LOG_TABLES}")
        with self._lock:
            cfg = self._policies[table]
            if retention_days is not None:
                cfg["retention_days"] = max(1, int(retention_days))
            if max_rows is not None:
                cfg["max_rows"] = max(100, int(max_rows))
            return dict(cfg)

    def get_policies(self) -> Dict[str, Dict]:
        """查看全部日志表保留策略"""
        with self._lock:
            return {t: dict(cfg) for t, cfg in self._policies.items()}

    # ============================================================
    # 归档
    # ============================================================
    def archive(self, table: str,
                older_than_days: Optional[int] = None,
                max_rows: Optional[int] = None) -> Dict:
        """
        归档单张日志表：
          1. 超期行（created_at < 当前时间 - retention_days）导出并删除
          2. 若剩余行数仍超过 max_rows，最老的超额行同样归档

        参数：
            table: 表名
            older_than_days: 覆盖配置的保留天数（None 用配置值）
            max_rows: 覆盖配置的行数上限（None 用配置值）

        返回：
            {"table", "archived", "kept", "file_path", "skipped_referenced",
             "elapsed"}
        """
        t0 = time.time()
        if table not in LOG_TABLES:
            return {"table": table, "error": f"未知日志表: {table}",
                    "archived": 0, "kept": 0, "file_path": ""}

        with self._lock:
            cfg = self._policies[table]
            days = int(older_than_days if older_than_days is not None
                       else cfg["retention_days"])
            rows_limit = int(max_rows if max_rows is not None else cfg["max_rows"])

            # 1. 收集超期行 id
            expired = db._query(
                f"SELECT id FROM {table} "
                "WHERE created_at < datetime('now', 'localtime', ?) "
                "ORDER BY id ASC",
                (f'-{days} days',))
            candidate_ids = [r["id"] for r in expired]

            # 2. 超出行数上限的最老行（在超期清理之后仍超量）
            remaining = self._row_count(table)
            overflow = max(0, remaining - rows_limit)
            overflow_ids = []
            if overflow > 0:
                extra = db._query(
                    f"SELECT id FROM {table} ORDER BY created_at ASC, id ASC "
                    "LIMIT ?", (overflow,))
                overflow_ids = [r["id"] for r in extra]

            to_archive = list(dict.fromkeys(candidate_ids + overflow_ids))
            skipped = 0
            if table == "agent_call_log":
                # FK 保护：被知识库引用的调用日志不归档删除
                referenced = self._referenced_call_ids()
                if referenced:
                    before = len(to_archive)
                    to_archive = [i for i in to_archive if i not in referenced]
                    skipped = before - len(to_archive)

            archived = 0
            file_path = ""
            if to_archive:
                rows = self._fetch_rows(table, to_archive)
                file_path = self._write_archive(table, rows)
                archived = self._delete_ids(table, to_archive)

            return {
                "table": table,
                "archived": archived,
                "kept": self._row_count(table),
                "file_path": file_path,
                "skipped_referenced": skipped,
                "elapsed": round(time.time() - t0, 3),
            }

    def run_policy(self, tables: Optional[List[str]] = None) -> Dict:
        """
        按配置一键归档全部日志表。

        参数：
            tables: 指定表列表（默认全部 LOG_TABLES）

        返回：
            {"results": {table: report}, "total_archived": int}
        """
        targets = [t for t in (tables or LOG_TABLES) if t in LOG_TABLES]
        results = {}
        total = 0
        for table in targets:
            try:
                report = self.archive(table)
                results[table] = report
                total += report.get("archived", 0)
            except Exception as e:  # 单表失败不阻塞其他表
                results[table] = {"table": table, "error": str(e),
                                  "archived": 0, "kept": self._row_count(table)}
        return {"results": results, "total_archived": total}

    # ============================================================
    # 统计 / 归档列表
    # ============================================================
    def get_stats(self) -> Dict:
        """
        存储膨胀监控：各日志表行数 + 主表大小 + 归档文件统计。
        """
        db_size = 0
        try:
            db_size = os.path.getsize(db.db_path) if os.path.exists(db.db_path) else 0
        except OSError:
            pass
        tables = {}
        for table in LOG_TABLES:
            tables[table] = {"rows": self._row_count(table)}
        archives = self.list_archives()
        return {
            "db_path": db.db_path,
            "db_size_bytes": db_size,
            "tables": tables,
            "archives": archives,
            "total_archives": len(archives),
            "archive_size_bytes": sum(a.get("size_bytes", 0) for a in archives),
        }

    def list_archives(self, table: Optional[str] = None) -> List[Dict]:
        """列出归档文件（可按表过滤）"""
        archive_dir = self._archive_dir()
        items = []
        if not os.path.isdir(archive_dir):
            return items
        for fname in sorted(os.listdir(archive_dir)):
            if not fname.endswith(".jsonl"):
                continue
            fpath = os.path.join(archive_dir, fname)
            base = fname[: -len(".jsonl")]
            tbl = next((t for t in LOG_TABLES if base.startswith(f"{t}_")),
                       base.split("_")[0])
            if table and tbl != table:
                continue
            items.append({
                "table": tbl,
                "file": fname,
                "path": fpath,
                "size_bytes": os.path.getsize(fpath),
                "archived_at": os.path.getmtime(fpath),
            })
        return items

    # ============================================================
    # 内部工具
    # ============================================================
    def _archive_dir(self) -> str:
        """归档目录：数据库文件同目录下的 logs_archive/"""
        base = os.path.dirname(os.path.abspath(db.db_path))
        return os.path.join(base, _ARCHIVE_DIR)

    def _row_count(self, table: str) -> int:
        row = db._query_one(f"SELECT COUNT(*) AS n FROM {table}")
        return int((row or {}).get("n", 0))

    def _fetch_rows(self, table: str, ids: List[int]) -> List[Dict]:
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        return db._query(
            f"SELECT * FROM {table} WHERE id IN ({placeholders}) "
            "ORDER BY id ASC", tuple(ids))

    def _write_archive(self, table: str, rows: List[Dict]) -> str:
        """将行写入 JSONL 归档文件（append），返回文件路径"""
        archive_dir = self._archive_dir()
        os.makedirs(archive_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        fpath = os.path.join(archive_dir, f"{table}_{ts}.jsonl")
        with open(fpath, "a", encoding="utf-8") as f:
            for row in rows:
                record = dict(row)
                record["_archived_at"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime())
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return fpath

    def _delete_ids(self, table: str, ids: List[int]) -> int:
        """按 id 批量删除，返回删除数"""
        if not ids:
            return 0
        deleted = 0
        batch = 500
        for i in range(0, len(ids), batch):
            chunk = ids[i:i + batch]
            placeholders = ",".join("?" * len(chunk))
            cur = db._execute(
                f"DELETE FROM {table} WHERE id IN ({placeholders})", tuple(chunk))
            deleted += (cur.rowcount or 0)
        return deleted

    def _referenced_call_ids(self) -> set:
        """被 knowledge_accumulation.source_call_id 引用的 agent_call_log.id 集合"""
        try:
            rows = db._query(
                "SELECT DISTINCT source_call_id FROM knowledge_accumulation "
                "WHERE source_call_id IS NOT NULL AND source_call_id > 0")
            return {int(r["source_call_id"]) for r in rows}
        except Exception:
            return set()


# ================================================================
# 单例
# ================================================================
_instance: Optional[LogRetentionManager] = None


def get_log_retention_manager() -> LogRetentionManager:
    """获取日志保留策略管理器单例"""
    global _instance
    if _instance is None:
        _instance = LogRetentionManager()
    return _instance


def run_log_retention_policy() -> Dict:
    """一行调用：按配置归档全部日志表"""
    return get_log_retention_manager().run_policy()


if __name__ == "__main__":
    mgr = get_log_retention_manager()
    print("当前保留策略:")
    for table, cfg in mgr.get_policies().items():
        print(f"  {table}: {cfg}")
    print("\n归档执行: run_policy() →")
    print(mgr.run_policy())
    print("\n统计:")
    print(mgr.get_stats())
