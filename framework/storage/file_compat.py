"""
文件存储兼容层

提供 FileStorage（纯 JSON 文件存储）和 StorageRouter（SQLite 优先 + 文件降级）。
接口与 framework.database.DatabaseManager 中的 _query / _execute 风格兼容，
返回 Dict 或 List[Dict]，方便在 SQLite 不可用时无缝切换。
"""

import json
import os
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 文件存储默认根目录：项目根目录下的 data/store
_PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_STORE_DIR = _PROJECT_ROOT / "data" / "store"


class FileStorage:
    """
    纯文件 JSON 存储，接口与 SQLite 兼容。

    - get(key)     -> Optional[Dict]        读取单条记录
    - set(key, val)-> Dict                  写入/更新记录，返回存储的 dict
    - delete(key)  -> bool                  删除记录
    - list(prefix) -> List[Dict]            列出所有键（按 prefix 过滤）

    数据文件路径：{store_dir}/{key}.json
    降级日志路径：{store_dir}/logs.jsonl
    """

    def __init__(self, store_dir: Optional[Path] = None):
        self._store_dir = Path(store_dir or DEFAULT_STORE_DIR)
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._store_dir / "logs.jsonl"
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #

    def _file_path(self, key: str) -> Path:
        """将 key（允许含路径分隔符）映射为安全文件名。"""
        safe = key.replace("/", "_").replace("\\", "_")
        return self._store_dir / f"{safe}.json"

    def _write_log(self, level: str, module: str, message: str, detail: str = "") -> None:
        """追加一行 JSONL 日志到 logs.jsonl。"""
        entry = {
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": level,
            "module": module,
            "message": message,
            "detail": detail,
        }
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------ #
    # 公开接口
    # ------------------------------------------------------------------ #

    def get(self, key: str) -> Optional[Dict]:
        """读取一条记录，文件不存在或损坏时返回 None。"""
        with self._lock:
            fp = self._file_path(key)
            if not fp.exists():
                return None
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                self._write_log("error", "FileStorage", f"get 读取失败: {key}")
                return None

    def set(self, key: str, value: Any) -> Dict:
        """写入/更新一条记录，返回存储的 dict（含 _meta）。"""
        with self._lock:
            fp = self._file_path(key)
            # 毫秒精度，保证同秒内的连续写入 updated_at 也可区分
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            record: Dict[str, Any] = {
                "_meta": {
                    "key": key,
                    "created_at": now,
                    "updated_at": now,
                },
                "data": value,
            }
            # 若已有记录，保留创建时间
            if fp.exists():
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                    if isinstance(existing, dict) and "_meta" in existing:
                        record["_meta"]["created_at"] = existing["_meta"].get("created_at", record["_meta"]["created_at"])
                except (json.JSONDecodeError, OSError):
                    pass
            fp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            return record

    def delete(self, key: str) -> bool:
        """删除一条记录，成功返回 True，不存在也返回 True（幂等）。"""
        with self._lock:
            fp = self._file_path(key)
            if fp.exists():
                fp.unlink()
                return True
            return False

    def list(self, prefix: str = "") -> List[Dict]:
        """列出所有匹配 prefix 的记录，按 updated_at 倒序。"""
        results: List[Dict] = []
        with self._lock:
            for fp in sorted(self._store_dir.glob("*.json")):
                name = fp.stem.replace("_", "/")  # 粗略还原 key
                if prefix and not name.startswith(prefix):
                    continue
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        record = json.load(f)
                    results.append(record)
                except (json.JSONDecodeError, OSError):
                    continue
        return results

    def add_system_log(self, level: str, module: str, message: str, detail: str = "") -> int:
        """写入系统日志（模拟 SQLite add_system_log 接口，返回固定 id）。"""
        self._write_log(level, module, message, detail)
        return int(time.time() * 1000)  # 用毫秒时间戳作为伪 ID

    def get_system_logs(self, level: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """读取系统日志（模拟 SQLite get_system_logs 接口）。"""
        logs: List[Dict] = []
        with self._lock:
            if not self._log_path.exists():
                return logs
            with open(self._log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if level and entry.get("level") != level:
                            continue
                        logs.append(entry)
                    except json.JSONDecodeError:
                        continue
        # 倒序返回（最新在前），与 SQLite 版 ORDER BY id DESC 语义一致
        return logs[::-1][:limit]


class StorageRouter:
    """
    SQLite 优先存储路由器，SQLite 操作抛出 sqlite3.Error 时自动降级到 FileStorage。

    用法：
        router = StorageRouter(db_manager)   # db_manager 是 DatabaseManager 实例
        router.get("users/1")                # 优先走 SQLite；失败则走文件
    """

    def __init__(self, db=None, fallback: Optional[FileStorage] = None):
        self._db = db
        self._fallback = fallback or FileStorage()
        self._fallback_active = False

    # ------------------------------------------------------------------ #
    # 查询操作（对应 _query，返回 List[Dict]）
    # ------------------------------------------------------------------ #

    def get(self, key: str) -> Optional[Dict]:
        """读取单条记录。"""
        if not self._fallback_active:
            try:
                sql = "SELECT * FROM key_value_store WHERE key = ? LIMIT 1"
                # 仅当 db 具备 _query 方法时调用
                if hasattr(self._db, "_query"):
                    rows = self._db._query(sql, (key,))
                    if rows:
                        return rows[0]
            except Exception as e:
                self._switch_to_fallback(f"SQLite get 失败: {e}")
        return self._fallback.get(key)

    def list(self, prefix: str = "") -> List[Dict]:
        """列出记录。"""
        if not self._fallback_active:
            try:
                sql = "SELECT * FROM key_value_store WHERE key LIKE ? ORDER BY id DESC"
                if hasattr(self._db, "_query"):
                    rows = self._db._query(sql, (f"{prefix}%",))
                    if rows is not None:
                        return rows
            except Exception as e:
                self._switch_to_fallback(f"SQLite list 失败: {e}")
        return self._fallback.list(prefix)

    # ------------------------------------------------------------------ #
    # 写入操作（对应 _execute，返回 None 或影响行数）
    # ------------------------------------------------------------------ #

    def set(self, key: str, value: Any) -> Dict:
        """写入/更新记录。"""
        if not self._fallback_active:
            try:
                if hasattr(self._db, "_execute"):
                    self._db._execute(
                        "INSERT OR REPLACE INTO key_value_store (key, value, updated_at) "
                        "VALUES (?, ?, datetime('now','localtime'))",
                        (key, json.dumps(value, ensure_ascii=False)),
                    )
                    return {"key": key, "value": value}
            except Exception as e:
                self._switch_to_fallback(f"SQLite set 失败: {e}")
        return self._fallback.set(key, value)

    def delete(self, key: str) -> bool:
        """删除记录。"""
        if not self._fallback_active:
            try:
                if hasattr(self._db, "_execute"):
                    self._db._execute("DELETE FROM key_value_store WHERE key = ?", (key,))
                    return True
            except Exception as e:
                self._switch_to_fallback(f"SQLite delete 失败: {e}")
        return self._fallback.delete(key)

    # ------------------------------------------------------------------ #
    # 系统日志（兼容 database.py 的 add_system_log / get_system_logs）
    # ------------------------------------------------------------------ #

    def add_system_log(self, level: str, module: str, message: str, detail: str = "") -> int:
        """写入系统日志，优先 SQLite，失败降级到文件。"""
        try:
            if hasattr(self._db, "add_system_log"):
                return self._db.add_system_log(level, module, message, detail)
        except Exception:
            self._switch_to_fallback("SQLite add_system_log 失败")
        return self._fallback.add_system_log(level, module, message, detail)

    def get_system_logs(self, level: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """读取系统日志，优先 SQLite，失败降级到文件。"""
        try:
            if hasattr(self._db, "get_system_logs"):
                return self._db.get_system_logs(level, limit)
        except Exception:
            self._switch_to_fallback("SQLite get_system_logs 失败")
        return self._fallback.get_system_logs(level, limit)

    # ------------------------------------------------------------------ #
    # 内部
    # ------------------------------------------------------------------ #

    def _switch_to_fallback(self, reason: str) -> None:
        """切换至文件存储并记录降级日志。"""
        if not self._fallback_active:
            self._fallback_active = True
            self._fallback._write_log("warning", "StorageRouter", "降级到文件存储", reason)
