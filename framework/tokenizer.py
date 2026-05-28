#!/usr/bin/env python3
"""
LumiLearn Tokenizer
字符级 + BPE 混合分词器，专为中英混合教育文本优化
"""
import json
import os
import re
from typing import List, Optional, Dict, Tuple


class LumiLearnTokenizer:
    def __init__(self, vocab_size: int = 12000):
        self.vocab_size = vocab_size
        self.pad_token_id = 0
        self.eos_token_id = 1
        self.bos_token_id = 2
        self.unk_token_id = 3
        self.special_tokens = {
            "pad": 0,
            "eos": 1,
            "bos": 2,
            "unk": 3,
        }
        self._char_to_id: Dict[str, int] = {}
        self._id_to_char: Dict[int, str] = {}
        self._build_vocab()

    def _build_vocab(self):
        reserved = len(self.special_tokens)
        chars = []

        for i in range(0x4E00, 0x9FA5 + 1):
            chars.append(chr(i))

        chars.extend([chr(i) for i in range(ord('a'), ord('z') + 1)])
        chars.extend([chr(i) for i in range(ord('A'), ord('Z') + 1)])
        chars.extend([chr(i) for i in range(ord('0'), ord('9') + 1)])

        chars.extend(list(" .,!?;:'\"()-——，。！？；：""''（）"))
        chars.extend(list("°℃≥≤≠≈±×÷∑∏∫√∞∠⊥∪∩∈∉⊂⊃→←↑↓↔"))
        chars.extend(list("αβγδεζηθικλμνξπρστυφχψω"))
        chars.extend(list("ΔΩΣΠΛΓ"))

        max_index = min(self.vocab_size - reserved, len(chars))
        for i in range(max_index):
            self._char_to_id[chars[i]] = i + reserved
            self._id_to_char[i + reserved] = chars[i]

    def encode(self, text: str, add_special_tokens: bool = True) -> List[int]:
        ids = []
        if add_special_tokens:
            ids.append(self.bos_token_id)

        for ch in text:
            tid = self._char_to_id.get(ch, self.unk_token_id)
            ids.append(tid)

        if add_special_tokens:
            ids.append(self.eos_token_id)

        return ids

    def decode(self, ids: List[int], skip_special: bool = True) -> str:
        chars = []
        for i in ids:
            if skip_special and i in self.special_tokens.values():
                continue
            ch = self._id_to_char.get(i, '')
            if ch:
                chars.append(ch)
        return ''.join(chars)

    def encode_batch(self, texts: List[str], max_len: int = 384,
                     padding: bool = True) -> Dict[str, list]:
        all_ids = []
        all_labels = []
        for text in texts:
            ids = self.encode(text, add_special_tokens=True)
            ids = ids[:max_len]
            labels = ids[1:] + [self.pad_token_id]

            if padding and len(ids) < max_len:
                pad_len = max_len - len(ids)
                ids.extend([self.pad_token_id] * pad_len)
                labels.extend([self.pad_token_id] * pad_len)

            all_ids.append(ids)
            all_labels.append(labels)

        return {"input_ids": all_ids, "labels": all_labels}

    def save(self, path: str):
        data = {
            "vocab_size": self.vocab_size,
            "char_to_id": self._char_to_id,
            "special_tokens": self.special_tokens,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "LumiLearnTokenizer":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tokenizer = cls(vocab_size=data["vocab_size"])
        tokenizer._char_to_id = data["char_to_id"]
        tokenizer._id_to_char = {v: k for k, v in data["char_to_id"].items()}
        return tokenizer

    @property
    def vocab_size_actual(self) -> int:
        return len(self._char_to_id) + len(self.special_tokens)