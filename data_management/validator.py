#!/usr/bin/env python3
"""
LumiLearn 数据验证器
- Schema 校验
- 内容质量检查
- 领域覆盖分析
- 训练就绪度评估
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from collections import Counter

from .schema import DataSchema


@dataclass
class ValidationReport:
    total: int = 0
    valid: int = 0
    invalid: int = 0
    schema_errors: List[Dict] = field(default_factory=list)
    quality_warnings: List[Dict] = field(default_factory=list)
    distribution: Dict = field(default_factory=dict)
    readiness_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)


class DataValidator:
    def __init__(self, min_records_for_training: int = 5000):
        self.min_records_for_training = min_records_for_training

    def validate(self, records: List[Dict]) -> ValidationReport:
        report = ValidationReport(total=len(records))

        valid_records = []

        for i, record in enumerate(records):
            errors = DataSchema.validate_record(record)
            if errors:
                report.invalid += 1
                report.schema_errors.append({
                    "index": i,
                    "errors": errors,
                    "preview": str(record.get("content", ""))[:50]
                })
            else:
                valid_records.append(record)

            warnings = self._check_quality(record)
            if warnings:
                report.quality_warnings.append({
                    "index": i,
                    "warnings": warnings
                })

        report.valid = len(valid_records)
        report.distribution = self._analyze_distribution(valid_records)
        report.readiness_score = self._calculate_readiness(report, valid_records)
        report.recommendations = self._generate_recommendations(report)

        return report

    def _check_quality(self, record: Dict) -> List[str]:
        warnings = []
        content = record.get("content", "")

        if "\n\n\n" in content:
            warnings.append("过多连续空行")

        special_chars = sum(1 for c in content if not c.isprintable() and c not in '\n\r\t')
        if special_chars > 10:
            warnings.append(f"存在{special_chars}个不可打印字符")

        if not record.get("keywords"):
            warnings.append("缺少关键词")

        if not record.get("chapter"):
            warnings.append("缺少章节信息")

        return warnings

    def _analyze_distribution(self, records: List[Dict]) -> Dict:
        if not records:
            return {}

        subjects = Counter(r.get("subject", "未知") for r in records)
        difficulties = Counter(r.get("difficulty", "未知") for r in records)
        content_types = Counter(r.get("content_type", "未知") for r in records)
        grades = Counter(r.get("grade", "未知") for r in records)
        lengths = [len(r.get("content", "")) for r in records]

        return {
            "count": len(records),
            "subject_count": len(subjects),
            "subject_distribution": dict(subjects.most_common(20)),
            "difficulty_distribution": dict(difficulties.most_common(8)),
            "content_type_distribution": dict(content_types.most_common(8)),
            "grade_distribution": dict(grades.most_common(8)),
            "avg_length": sum(lengths) / len(lengths) if lengths else 0,
            "min_length": min(lengths) if lengths else 0,
            "max_length": max(lengths) if lengths else 0,
        }

    def _calculate_readiness(self, report: ValidationReport,
                             valid_records: List[Dict]) -> float:
        score = 0.0

        if len(valid_records) >= self.min_records_for_training:
            score += 40
        elif len(valid_records) >= self.min_records_for_training * 0.5:
            score += 20
        else:
            score += 5

        dist = report.distribution
        subject_count = dist.get("subject_count", 0)
        if subject_count >= 9:
            score += 25
        elif subject_count >= 6:
            score += 15
        elif subject_count >= 3:
            score += 5

        validity = report.valid / max(report.total, 1)
        if validity >= 0.95:
            score += 20
        elif validity >= 0.85:
            score += 10
        elif validity >= 0.70:
            score += 5

        avg_len = dist.get("avg_length", 0)
        if avg_len >= 300:
            score += 15
        elif avg_len >= 200:
            score += 10
        elif avg_len >= 100:
            score += 5

        return min(score, 100)

    def _generate_recommendations(self, report: ValidationReport) -> List[str]:
        recs = []

        if report.valid < self.min_records_for_training:
            recs.append(f"数据量不足: {report.valid}条 < {self.min_records_for_training}条目标，建议继续收集")

        dist = report.distribution
        subjects = dist.get("subject_distribution", {})

        if len(subjects) < 9:
            recs.append(f"学科覆盖不足: {len(subjects)}个 < 9个目标")

        for subject, count in subjects.items():
            if count < 500:
                recs.append(f"{subject}学科数据较少({count}条)，建议补充至500条以上")

        difficulties = dist.get("difficulty_distribution", {})
        if len(difficulties) < 2:
            recs.append("难度分布单一，建议增加不同难度层次的数据")

        if report.schema_errors:
            recs.append(f"存在{len(report.schema_errors)}条Schema错误，建议修复后重新验证")

        if report.readiness_score < 50:
            recs.insert(0, "整体就绪度低，建议完成数据补充后再启动训练")
        elif report.readiness_score < 75:
            recs.insert(0, "数据基本就绪，可启动训练但建议继续补充")
        else:
            recs.insert(0, "数据就绪度良好，可以启动正式训练")

        return recs