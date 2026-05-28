#!/usr/bin/env python3
"""
LumiLearn 数据清洗流水线
- 文本规范化
- 重复检测
- 质量评估
- HTML标签清洗
- 特殊字符清理
"""
import re
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from collections import Counter


@dataclass
class CleaningReport:
    total_input: int = 0
    passed: int = 0
    removed_duplicate: int = 0
    removed_short: int = 0
    removed_long: int = 0
    removed_noise: int = 0
    removed_empty: int = 0
    issues: List[Dict] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)


class DataCleaner:
    def __init__(self, min_length: int = 80, max_length: int = 2000,
                 dup_threshold: float = 0.85):
        self.min_length = min_length
        self.max_length = max_length
        self.dup_threshold = dup_threshold

    def clean_batch(self, records: List[Dict]) -> Tuple[List[Dict], CleaningReport]:
        report = CleaningReport(total_input=len(records))

        cleaned = []
        seen_hashes: Set[str] = set()
        seen_texts: List[str] = []

        for record in records:
            content = record.get("content", "")

            if not content or not content.strip():
                report.removed_empty += 1
                continue

            content = self._normalize_text(content)
            content = self._clean_html(content)
            content = self._clean_special_chars(content)

            if len(content) < self.min_length:
                report.removed_short += 1
                report.issues.append({
                    "type": "too_short",
                    "length": len(content),
                    "preview": content[:50]
                })
                continue

            if len(content) > self.max_length:
                chunks = self._split_long_content(content, self.max_length)
                for chunk in chunks:
                    if len(chunk) >= self.min_length:
                        record["content"] = chunk
                        if self._is_unique(chunk, seen_hashes, seen_texts):
                            cleaned.append(record.copy())
                            report.passed += 1
                report.removed_long += 1
                continue

            record["content"] = content

            content_hash = hashlib.md5(content.encode()).hexdigest()
            if content_hash in seen_hashes:
                report.removed_duplicate += 1
                continue

            if not self._is_unique(content, seen_hashes, seen_texts):
                report.removed_duplicate += 1
                continue

            if self._is_noise(content):
                report.removed_noise += 1
                report.issues.append({
                    "type": "noise",
                    "preview": content[:50]
                })
                continue

            seen_hashes.add(content_hash)
            seen_texts.append(content)
            cleaned.append(record)
            report.passed += 1

        report.stats = self._generate_stats(cleaned)
        return cleaned, report

    def _normalize_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        text = re.sub(r'[「」『』]', '"', text)
        text = re.sub(r'[【】]', '[', text)
        text = re.sub(r'（）', '()', text)
        return text.strip()

    def _clean_html(self, text: str) -> str:
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'&[a-z]+;', '', text)
        text = re.sub(r'https?://\S+', '', text)
        return text

    def _clean_special_chars(self, text: str) -> str:
        text = re.sub(r'[\ufeff\u200b\u200e\u200f]', '', text)
        text = re.sub(r'\u3000', ' ', text)
        text = re.sub(r'[\U0001F600-\U0001F64F'
                      r'\U0001F300-\U0001F5FF'
                      r'\U0001F680-\U0001F6FF'
                      r'\U0001F1E0-\U0001F1FF'
                      r'\U00002702-\U000027B0'
                      r'\U000024C2-\U000024FF'
                      r'\U000025A0-\U000025FF'
                      r'\U00002600-\U000026FF'
                      r'\U0001F900-\U0001F9FF'
                      r'\U0001FA00-\U0001FA6F'
                      r'\U0001FA70-\U0001FAFF'
                      r'\U0001F004-\U0001F0CF'
                      r'\U0001F200-\U0001F251]', '', text)
        return text

    def _is_unique(self, text: str, hashes: Set[str], existing: List[str]) -> bool:
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in hashes:
            return False

        text_trigrams = self._get_trigrams(text[:300])
        if not text_trigrams:
            return True

        sample = existing[-50:] if len(existing) > 50 else existing
        for old in sample:
            old_trigrams = self._get_trigrams(old[:300])
            if not old_trigrams:
                continue
            intersection = len(text_trigrams & old_trigrams)
            union = len(text_trigrams | old_trigrams)
            jaccard = intersection / max(union, 1)
            if jaccard > self.dup_threshold:
                return False
        return True

    def _get_trigrams(self, text: str) -> set:
        if len(text) < 3:
            return set()
        return {text[i:i+3] for i in range(len(text) - 2)}

    def _is_noise(self, text: str) -> bool:
        noise_patterns = [
            r'^\d+$',
            r'^[\W_]+$',
            r'(.)\1{50,}',
            r'^(举报|投诉|建议|联系|客服|广告|推广)',
        ]
        for pattern in noise_patterns:
            if re.search(pattern, text):
                return True

        char_ratio = len(re.findall(r'[\u4e00-\u9fff]', text)) / max(len(text), 1)
        if char_ratio < 0.1:
            return True

        return False

    def _split_long_content(self, text: str, max_len: int) -> List[str]:
        chunks = []
        sentences = re.split(r'([。！？\n])', text)
        current = ""
        for i in range(0, len(sentences), 2):
            sent = sentences[i]
            if i + 1 < len(sentences):
                sent += sentences[i + 1]
            if len(current) + len(sent) <= max_len:
                current += sent
            else:
                if current:
                    chunks.append(current)
                current = sent
        if current:
            chunks.append(current)
        return chunks if chunks else [text[:max_len]]

    def _generate_stats(self, records: List[Dict]) -> Dict:
        if not records:
            return {}

        lengths = [len(r.get("content", "")) for r in records]
        subjects = Counter(r.get("subject", "未知") for r in records)
        types = Counter(r.get("content_type", "未知") for r in records)

        return {
            "count": len(records),
            "avg_length": sum(lengths) / len(lengths),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "subject_distribution": dict(subjects.most_common(15)),
            "type_distribution": dict(types.most_common(10)),
        }