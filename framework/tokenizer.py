#!/usr/bin/env python3
"""
LumiLearn BPE Tokenizer
基于 HuggingFace tokenizers 库的 BPE 子词级分词器
"""

import os
from typing import List, Dict, Optional

from tokenizers import Tokenizer as HFTokenizer


class LumiLearnTokenizer:
    def __init__(self, vocab_size: int = 8000, tokenizer_path: Optional[str] = None):
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

        if tokenizer_path is None:
            tokenizer_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "bpe_tokenizer.json"
            )

        self._tokenizer = HFTokenizer.from_file(tokenizer_path)

        if self._tokenizer.token_to_id("[PAD]") is not None:
            self._tokenizer.enable_padding(
                pad_id=self._tokenizer.token_to_id("[PAD]"),
                pad_token="[PAD]",
            )

    def encode(self, text: str, add_special_tokens: bool = True) -> List[int]:
        encoded = self._tokenizer.encode(text)
        ids = encoded.ids
        if not add_special_tokens:
            if ids and ids[0] == self.bos_token_id:
                ids = ids[1:]
            if ids and ids[-1] == self.eos_token_id:
                ids = ids[:-1]
        return ids

    def decode(self, ids: List[int], skip_special: bool = True) -> str:
        if skip_special:
            ids = [
                i for i in ids
                if i not in (self.pad_token_id, self.eos_token_id,
                             self.bos_token_id, self.unk_token_id)
            ]
        if not ids:
            return ""
        return self._tokenizer.decode(ids)

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
        self._tokenizer.save(path)

    @classmethod
    def load(cls, path: str) -> "LumiLearnTokenizer":
        instance = cls.__new__(cls)
        instance._tokenizer = HFTokenizer.from_file(path)
        instance.vocab_size = instance._tokenizer.get_vocab_size()
        instance.pad_token_id = instance._tokenizer.token_to_id("[PAD]") or 0
        instance.eos_token_id = instance._tokenizer.token_to_id("[EOS]") or 1
        instance.bos_token_id = instance._tokenizer.token_to_id("[BOS]") or 2
        instance.unk_token_id = instance._tokenizer.token_to_id("[UNK]") or 3
        instance.special_tokens = {
            "pad": instance.pad_token_id,
            "eos": instance.eos_token_id,
            "bos": instance.bos_token_id,
            "unk": instance.unk_token_id,
        }
        return instance

    @property
    def vocab_size_actual(self) -> int:
        return self._tokenizer.get_vocab_size()