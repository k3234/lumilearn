#!/usr/bin/env python3
"""
LumiLearn 数据加载模块
支持: JSONL/CSV格式, 训练/验证/测试划分, 动态批处理
"""
import json
import csv
import os
import random
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Iterator

import torch
from torch.utils.data import Dataset, DataLoader, IterableDataset

from .tokenizer import LumiLearnTokenizer
from .config import LumiLearnConfig


class LumiLearnDataset(Dataset):
    def __init__(self, records: List[Dict], tokenizer: LumiLearnTokenizer,
                 max_seq_len: int = 384, shuffle: bool = True):
        self.records = records
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len
        self._data = self._preprocess()

    def _preprocess(self) -> List[Dict]:
        processed = []
        for rec in self.records:
            content = rec.get("content", "")

            prefix = f"{rec.get('subject', '')} - {rec.get('chapter', '')} - "
            text = prefix + content

            ids = self.tokenizer.encode(text, add_special_tokens=True)

            if len(ids) > self.max_seq_len:
                ids = ids[:self.max_seq_len]
            else:
                pad_len = self.max_seq_len - len(ids)
                ids = ids + [self.tokenizer.pad_token_id] * pad_len

            input_ids = ids[:-1]
            labels = ids[1:]

            processed.append({
                "input_ids": torch.tensor(input_ids, dtype=torch.long),
                "labels": torch.tensor(labels, dtype=torch.long),
            })

        return processed

    def __len__(self) -> int:
        return len(self._data)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return self._data[idx]


class StreamingDataset(IterableDataset):
    def __init__(self, file_path: str, tokenizer: LumiLearnTokenizer,
                 max_seq_len: int = 384, shuffle_buffer: int = 10000):
        self.file_path = file_path
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len
        self.shuffle_buffer = shuffle_buffer

    def __iter__(self) -> Iterator[Dict[str, torch.Tensor]]:
        buffer = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    content = record.get("content", "")
                    prefix = f"{record.get('subject', '')} - "
                    text = prefix + content

                    ids = self.tokenizer.encode(text, add_special_tokens=True)
                    ids = ids[:self.max_seq_len] + [self.tokenizer.pad_token_id] * \
                          max(0, self.max_seq_len - len(ids))

                    buffer.append({
                        "input_ids": torch.tensor(ids[:-1], dtype=torch.long),
                        "labels": torch.tensor(ids[1:], dtype=torch.long),
                    })

                    if len(buffer) >= self.shuffle_buffer:
                        random.shuffle(buffer)
                        for item in buffer:
                            yield item
                        buffer = []

            if buffer:
                random.shuffle(buffer)
                for item in buffer:
                    yield item


def load_jsonl(filepath: str) -> List[Dict]:
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def load_csv(filepath: str) -> List[Dict]:
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            records.append(row)
    return records


def load_records(data_path: str) -> List[Dict]:
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found: {data_path}")

    ext = Path(data_path).suffix.lower()
    if ext == ".jsonl":
        return load_jsonl(data_path)
    elif ext == ".csv":
        return load_csv(data_path)
    elif ext == ".json":
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        raise ValueError(f"Unsupported format: {ext}")


def create_dataloaders(config: LumiLearnConfig,
                       data_path: str = None,
                       records: List[Dict] = None,
                       tokenizer: LumiLearnTokenizer = None
                       ) -> Tuple[DataLoader, DataLoader, DataLoader]:
    if records is None and data_path:
        records = load_records(data_path)

    if records is None:
        raise ValueError("Must provide either data_path or records")

    if tokenizer is None:
        tokenizer = LumiLearnTokenizer(config.model.vocab_size)

    random.seed(config.experiment.seed)
    random.shuffle(records)

    n = len(records)
    n_train = int(n * config.data.train_ratio)
    n_val = int(n * config.data.val_ratio)

    train_records = records[:n_train]
    val_records = records[n_train:n_train + n_val]
    test_records = records[n_train + n_val:]

    train_ds = LumiLearnDataset(train_records, tokenizer, config.model.max_seq_len)
    val_ds = LumiLearnDataset(val_records, tokenizer, config.model.max_seq_len)
    test_ds = LumiLearnDataset(test_records, tokenizer, config.model.max_seq_len)

    common_kwargs = dict(
        num_workers=config.data.num_workers,
        pin_memory=config.data.pin_memory,
        prefetch_factor=config.data.prefetch_factor if config.data.num_workers > 0 else None,
    )

    train_loader = DataLoader(train_ds, batch_size=config.training.batch_size,
                              shuffle=True, **common_kwargs)
    val_loader = DataLoader(val_ds, batch_size=config.training.batch_size,
                            shuffle=False, **common_kwargs)
    test_loader = DataLoader(test_ds, batch_size=config.training.batch_size,
                             shuffle=False, **common_kwargs)

    return train_loader, val_loader, test_loader