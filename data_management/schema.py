#!/usr/bin/env python3
"""
LumiLearn 数据标准格式定义
所有输入输出数据必须遵循此 Schema
"""
import csv
import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict


class Difficulty(Enum):
    BEGINNER = "入门"
    BASIC = "基础"
    MEDIUM = "中等"
    ADVANCED = "困难"
    EXPERT = "专家"


class ContentType(Enum):
    CONCEPT = "概念定义"
    FORMULA = "公式推导"
    EXAMPLE = "例题解析"
    EXERCISE = "练习题"
    SUMMARY = "知识总结"
    EXPERIMENT = "实验说明"
    HISTORY = "学科历史"
    METHOD = "解题方法"


class GradeLevel(Enum):
    JUNIOR_7 = "初一"
    JUNIOR_8 = "初二"
    JUNIOR_9 = "初三"
    SENIOR_10 = "高一"
    SENIOR_11 = "高二"
    SENIOR_12 = "高三"
    COLLEGE = "大学"
    GENERAL = "通用"


@dataclass
class TrainingRecord:
    """训练数据标准记录 - 所有数据必须转换为此格式"""
    subject: str
    chapter: str
    title: str
    content: str
    grade: str = "高中"
    content_type: str = "概念定义"
    difficulty: str = "基础"
    keywords: str = ""
    prerequisites: str = ""
    learning_objectives: str = ""
    common_mistakes: str = ""
    source: str = "unknown"
    source_type: str = "generated"
    quality_score: float = 0.0
    word_count: int = 0
    token_count: int = 0
    hash: str = ""
    version: int = 1
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.hash:
            self.hash = self._compute_hash()
        if not self.word_count:
            self.word_count = len(self.content)
        if not self.quality_score:
            self.quality_score = self._compute_quality()

    def _compute_hash(self) -> str:
        text = f"{self.subject}|{self.chapter}|{self.title}|{self.content[:200]}"
        return hashlib.md5(text.encode()).hexdigest()[:12]

    def _compute_quality(self) -> float:
        score = 1.0
        content = self.content

        if len(content) < 100:
            score -= 0.3
        elif len(content) < 200:
            score -= 0.1

        if self.keywords:
            score += 0.1
        if self.learning_objectives:
            score += 0.1
        if self.common_mistakes:
            score += 0.1
        if self.prerequisites:
            score += 0.05

        return max(0.0, min(score, 1.0))

    def to_dict(self) -> dict:
        return asdict(self)

    def to_csv_row(self, fieldnames: List[str]) -> dict:
        d = self.to_dict()
        return {k: d.get(k, "") for k in fieldnames}


class DataSchema:
    """训练数据标准 Schema"""

    CSV_FIELDS = [
        "subject", "chapter", "title", "content", "grade",
        "content_type", "difficulty", "keywords", "prerequisites",
        "learning_objectives", "common_mistakes",
        "source", "source_type", "quality_score",
        "word_count", "token_count", "hash", "version",
        "created_at", "updated_at",
    ]

    JSON_FIELDS = CSV_FIELDS + ["metadata"]

    REQUIRED_FIELDS = {"subject", "chapter", "title", "content"}

    QUALITY_THRESHOLDS = {
        "min_words": 80,
        "max_words": 4000,
        "min_quality": 0.3,
    }

    ALLOWED_SUBJECTS = {
        "数学", "英语", "语文", "物理", "化学", "生物",
        "历史", "地理", "政治", "信息技术", "通用技术",
        "编程", "AI基础", "高等数学", "考研数学", "考研英语",
        "线性代数", "概率论与数理统计", "离散数学",
        "大学物理", "大学英语", "考研政治",
        "计算机科学", "Python编程", "数据结构与算法",
        "计算机网络", "数据分析", "AI与机器学习",
        "AI模型开发", "办公技能", "常识百科",
        "心理健康", "科学", "思想品德", "逻辑推理",
        "项目管理", "音乐素养", "美术素养", "体育健康",
    }

    ALLOWED_CONTENT_TYPES = {e.value for e in ContentType}
    ALLOWED_GRADES = {e.value for e in GradeLevel}
    ALLOWED_DIFFICULTIES = {e.value for e in Difficulty}

    LEGACY_TYPE_MAP = {
        "知识点": "概念定义",
        "概念": "概念定义",
        "重点": "知识总结",
        "考点": "知识总结",
        "易错题": "练习题",
        "例题": "例题解析",
        "基础": "概念定义",
        "中等": "例题解析",
        "困难": "练习题",
        "练习题": "练习题",
        "問答": "练习题",
        "问答": "练习题",
        "文言文": "概念定义",
        "文化常识": "学科历史",
        "古诗词": "概念定义",
        "语法": "概念定义",
        "词汇": "概念定义",
        "写作": "解题方法",
        "阅读": "例题解析",
        "听说": "概念定义",
        "实验": "实验说明",
        "定理": "公式推导",
        "公式": "公式推导",
        "综合": "知识总结",
    }

    @classmethod
    def validate_record(cls, record: Dict) -> List[str]:
        errors = []
        for field in cls.REQUIRED_FIELDS:
            if not record.get(field, "").strip():
                errors.append(f"缺少必填字段: {field}")

        content = record.get("content", "")
        if len(content) < cls.QUALITY_THRESHOLDS["min_words"]:
            errors.append(f"内容过短: {len(content)}字 < {cls.QUALITY_THRESHOLDS['min_words']}字")
        if len(content) > cls.QUALITY_THRESHOLDS["max_words"]:
            errors.append(f"内容过长: {len(content)}字 > {cls.QUALITY_THRESHOLDS['max_words']}字")

        subject = record.get("subject", "")
        if subject and subject not in cls.ALLOWED_SUBJECTS:
            errors.append(f"未知学科: {subject}")

        content_type = record.get("content_type", "")
        if content_type and content_type not in cls.ALLOWED_CONTENT_TYPES:
            errors.append(f"未知内容类型: {content_type}")

        return errors

    @classmethod
    def from_legacy_record(cls, old_record: Dict) -> TrainingRecord:
        subject = old_record.get("subject", "")
        chapter = old_record.get("chapter") or old_record.get("section") or ""
        if not chapter.strip():
            chapter = old_record.get("title", subject)
        title = old_record.get("title", "")
        content = old_record.get("content", "")
        grade = old_record.get("grade", "高中")
        raw_type = old_record.get("type", "知识点")
        content_type = cls.LEGACY_TYPE_MAP.get(raw_type, "概念定义")
        difficulty = old_record.get("difficulty", "基础")
        source = old_record.get("source", "")
        source_type = old_record.get("source_type", "generated")
        tags = old_record.get("tags", "")

        return TrainingRecord(
            subject=subject,
            chapter=chapter,
            title=title,
            content=content,
            grade=grade,
            content_type=content_type,
            difficulty=difficulty,
            keywords=tags,
            source=source,
            source_type=source_type,
        )