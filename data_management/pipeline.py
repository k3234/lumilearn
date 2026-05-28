#!/usr/bin/env python3
"""
LumiLearn 数据管理流水线
串联: 加载 → 格式转换 → 清洗 → 验证 → 版本快照 → 输出训练集
"""
import os
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from .schema import DataSchema, TrainingRecord
from .cleaner import DataCleaner, CleaningReport
from .validator import DataValidator, ValidationReport
from .versioner import DataVersioner


class DataPipeline:
    def __init__(self, base_dir: str, master_csv: str):
        self.base_dir = Path(base_dir)
        self.master_csv = Path(master_csv)
        self.cleaner = DataCleaner()
        self.validator = DataValidator()
        self.versioner = DataVersioner(base_dir, master_csv)

        self.training_dir = self.base_dir / "training_data"
        self.cleaned_dir = self.training_dir / "cleaned"
        self.splits_dir = self.training_dir / "splits"
        for d in [self.training_dir, self.cleaned_dir, self.splits_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def snapshot_before_run(self, tag: str = "") -> str:
        return self.versioner.snapshot(tag=tag or "pre_pipeline")

    def load_legacy_master(self) -> List[Dict]:
        if not self.master_csv.exists():
            return []

        records = []
        with open(self.master_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
        return records

    def convert_to_standard(self, legacy_records: List[Dict]) -> List[Dict]:
        standard = []
        conversion_map = []

        for i, old in enumerate(legacy_records):
            try:
                record = DataSchema.from_legacy_record(old)
                standard.append(record.to_dict())
                conversion_map.append({
                    "legacy_index": i,
                    "legacy_id": old.get("id", ""),
                    "new_hash": record.hash,
                    "status": "converted"
                })
            except Exception as e:
                conversion_map.append({
                    "legacy_index": i,
                    "legacy_id": old.get("id", ""),
                    "error": str(e),
                    "status": "failed"
                })

        return standard

    def run_full_pipeline(self,
                          legacy_records: Optional[List[Dict]] = None,
                          make_snapshot: bool = True) -> Dict:
        if make_snapshot:
            snapshot_id = self.snapshot_before_run("auto_before_pipeline")
        else:
            snapshot_id = None

        if legacy_records is None:
            legacy_records = self.load_legacy_master()

        print(f"\n{'='*70}")
        print(f"📋 LumiLearn 数据管理流水线")
        print(f"{'='*70}")
        print(f"  输入: {len(legacy_records)} 条旧格式记录")

        standard = self.convert_to_standard(legacy_records)
        print(f"  转换: {len(standard)} 条标准格式记录")

        cleaned, cleaning_report = self.cleaner.clean_batch(standard)
        print(f"  清洗: {cleaning_report.passed} 条通过 "
              f"(移除 {cleaning_report.removed_duplicate} 重复, "
              f"{cleaning_report.removed_short} 过短, "
              f"{cleaning_report.removed_noise} 噪声)")

        validation = self.validator.validate(cleaned)
        print(f"  验证: {validation.valid} 条有效, "
              f"{validation.invalid} 条无效")

        train, val, test = self._split_data(cleaned)
        print(f"  划分: 训练{len(train)} / 验证{len(val)} / 测试{len(test)}")

        self._save_splits(train, val, test)
        self._save_cleaned(cleaned, cleaning_report, validation)

        result = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "snapshot_id": snapshot_id,
            "input_records": len(legacy_records),
            "converted": len(standard),
            "cleaned": cleaning_report.passed,
            "valid": validation.valid,
            "train_split": len(train),
            "val_split": len(val),
            "test_split": len(test),
            "cleaning_report": cleaning_report.__dict__,
            "validation_report": {
                "total": validation.total,
                "valid": validation.valid,
                "invalid": validation.invalid,
                "readiness_score": validation.readiness_score,
                "distribution": validation.distribution,
                "recommendations": validation.recommendations,
            },
            "output_paths": {
                "train": str(self.splits_dir / "train.jsonl"),
                "val": str(self.splits_dir / "val.jsonl"),
                "test": str(self.splits_dir / "test.jsonl"),
                "cleaned": str(self.cleaned_dir / "cleaned_master.jsonl"),
            }
        }

        pipeline_report_path = self.training_dir / "pipeline_report.json"
        with open(pipeline_report_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n  就绪度: {validation.readiness_score:.1f}/100")
        for rec in validation.recommendations[:5]:
            print(f"  → {rec}")
        print(f"\n  报告: {pipeline_report_path}")
        print(f"{'='*70}")

        return result

    def _split_data(self, records: List[Dict],
                    train_ratio: float = 0.90,
                    val_ratio: float = 0.05) -> Tuple[List, List, List]:
        import random
        random.seed(42)
        shuffled = records.copy()
        random.shuffle(shuffled)

        n = len(shuffled)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        train = shuffled[:n_train]
        val = shuffled[n_train:n_train + n_val]
        test = shuffled[n_train + n_val:]

        return train, val, test

    def _save_splits(self, train: List, val: List, test: List):
        for name, data in [("train", train), ("val", val), ("test", test)]:
            path = self.splits_dir / f"{name}.jsonl"
            with open(path, "w", encoding="utf-8") as f:
                for record in data:
                    record_copy = {"content": record.get("content", ""),
                                   "subject": record.get("subject", ""),
                                   "chapter": record.get("chapter", ""),
                                   "difficulty": record.get("difficulty", ""),
                                   "content_type": record.get("content_type", "")}
                    f.write(json.dumps(record_copy, ensure_ascii=False) + "\n")

    def _save_cleaned(self, records: List, cleaning_report: CleaningReport,
                      validation: ValidationReport):
        path = self.cleaned_dir / "cleaned_master.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")