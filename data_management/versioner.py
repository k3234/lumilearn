#!/usr/bin/env python3
"""
LumiLearn 数据版本管理
- 快照创建/恢复
- 增量差异计算
- 版本线追踪
"""
import os
import json
import csv
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter


class DataVersioner:
    def __init__(self, base_dir: str, master_csv: str):
        self.base_dir = Path(base_dir)
        self.master_csv = Path(master_csv)
        self.versions_dir = self.base_dir / "versions"
        self.snapshots_dir = self.base_dir / "snapshots"
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.versions_dir / "version_index.json"
        self.index = self._load_index()

    def _load_index(self) -> Dict:
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"versions": [], "latest": None}

    def _save_index(self):
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    def snapshot(self, tag: str = "", description: str = "") -> str:
        if not self.master_csv.exists():
            raise FileNotFoundError(f"Master CSV not found: {self.master_csv}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_hash = self._hash_file(self.master_csv)
        version_id = f"v{len(self.index['versions']) + 1:04d}_{timestamp}"

        snapshot_dir = self.snapshots_dir / version_id
        snapshot_dir.mkdir(exist_ok=True)
        snapshot_path = snapshot_dir / f"master_{version_id}.csv"
        shutil.copy2(self.master_csv, snapshot_path)

        records = self._count_records(snapshot_path)
        subjects = self._count_subjects(snapshot_path)

        version_info = {
            "version_id": version_id,
            "timestamp": timestamp,
            "tag": tag or f"Snapshot {version_id}",
            "description": description,
            "file_hash": file_hash,
            "record_count": records,
            "subject_distribution": dict(subjects),
            "snapshot_path": str(snapshot_path),
        }

        self.index["versions"].append(version_info)
        self.index["latest"] = version_id
        self._save_index()

        return version_id

    def get_version(self, version_id: str = None) -> Optional[Dict]:
        if version_id is None:
            version_id = self.index.get("latest")
        for v in self.index["versions"]:
            if v["version_id"] == version_id:
                return v
        return None

    def list_versions(self) -> List[Dict]:
        return self.index["versions"]

    def diff(self, v1: str, v2: str = None) -> Dict:
        if v2 is None:
            v2 = self.index.get("latest")

        v1_info = self.get_version(v1)
        v2_info = self.get_version(v2)

        if not v1_info or not v2_info:
            return {"error": "version not found"}

        v1_subjects = v1_info.get("subject_distribution", {})
        v2_subjects = v2_info.get("subject_distribution", {})

        all_subjects = set(v1_subjects.keys()) | set(v2_subjects.keys())
        changes = {}
        for s in all_subjects:
            old = v1_subjects.get(s, 0)
            new = v2_subjects.get(s, 0)
            changes[s] = {"before": old, "after": new, "delta": new - old}

        added = v2_info["record_count"] - v1_info["record_count"]

        return {
            "from": v1,
            "to": v2,
            "records_added": max(0, added),
            "records_removed": max(0, -added),
            "total_before": v1_info["record_count"],
            "total_after": v2_info["record_count"],
            "subject_changes": changes,
        }

    def restore(self, version_id: str) -> bool:
        version = self.get_version(version_id)
        if not version:
            return False

        snapshot_path = version["snapshot_path"]
        if not os.path.exists(snapshot_path):
            return False

        shutil.copy2(snapshot_path, self.master_csv)
        return True

    def _hash_file(self, path: Path) -> str:
        hasher = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()[:12]

    def _count_records(self, csv_path: Path) -> int:
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                return sum(1 for _ in f) - 1
        except:
            return 0

    def _count_subjects(self, csv_path: Path) -> Counter:
        counts = Counter()
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    counts[row.get("subject", "未知")] += 1
        except:
            pass
        return counts