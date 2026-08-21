# -*- coding: utf-8 -*-
"""Task 5: 标准化学科测试集 + 自动化评测 CLI 测试"""
import json
import os
import sys

# 项目根加入 sys.path（scripts/ 在 pytest.ini norecursedirs 中，
# 不影响 import；此处确保根目录可导入 scripts.run_eval）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest

try:
    from scripts import run_eval
except ImportError:  # 兜底：手动把 scripts 目录加入 sys.path 再导入
    SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
    if SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, SCRIPTS_DIR)
    import run_eval


REQUIRED_FIELDS = ("id", "topic", "question", "expected_knowledge", "answer")
DATASET_FILES = {
    "math": os.path.join(PROJECT_ROOT, "data", "eval_dataset", "math.json"),
    "physics": os.path.join(PROJECT_ROOT, "data", "eval_dataset", "physics.json"),
    "chemistry": os.path.join(PROJECT_ROOT, "data", "eval_dataset", "chemistry.json"),
}


def _load_dataset(name: str):
    with open(DATASET_FILES[name], "r", encoding="utf-8") as f:
        return json.load(f)


def test_dataset_files_exist():
    """3 个数据集文件存在且各 50 题、字段齐全"""
    for name, path in DATASET_FILES.items():
        assert os.path.isfile(path), f"数据集文件缺失: {path}"
        data = _load_dataset(name)
        assert len(data) == 50, f"{name} 应为 50 题，实际 {len(data)}"
        ids = set()
        for item in data:
            for field in REQUIRED_FIELDS:
                assert field in item, f"{name} 题目缺少字段 {field}: {item}"
            assert item["id"] not in ids, f"{name} 存在重复 id: {item['id']}"
            ids.add(item["id"])
            assert isinstance(item["expected_knowledge"], list) and item["expected_knowledge"], \
                f"{name} 题目 expected_knowledge 必须为非空列表: {item['id']}"
            assert str(item["answer"]).strip(), f"{name} 题目 answer 不能为空: {item['id']}"


def test_run_eval_mock_metrics(tmp_path, monkeypatch):
    """mock 模式跑通（--limit 5），返回指标 dict，recall/accuracy 在 0-1 之间"""
    monkeypatch.setattr(run_eval, "REPORTS_DIR", str(tmp_path / "reports"))
    metrics = run_eval.run_evaluation(subject="all", limit=5, real=False)
    assert isinstance(metrics, dict)
    assert metrics["total_questions"] == 5
    assert metrics["mode"] == "mock"
    assert 0.0 <= metrics["knowledge_recall"] <= 1.0
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert 0.0 <= metrics["hit_rate"] <= 1.0
    assert metrics["hallucination_count"] == 0  # mock 模式幻觉恒为 0
    assert metrics["avg_latency_ms"] >= 0
    assert len(metrics["per_question"]) == 5


def test_eval_report_saved(tmp_path, monkeypatch):
    """跑完后 eval_reports 表有记录"""
    from framework.database import db
    monkeypatch.setattr(run_eval, "REPORTS_DIR", str(tmp_path / "reports"))
    run_eval.run_evaluation(subject="math", limit=3, real=False)
    reports = db.get_v25_eval_reports(limit=5)
    assert reports, "eval_reports 表应存在评测记录"
    top = reports[0]
    assert top["eval_type"] == "v25_dataset"
    assert top["total_questions"] == 3
    assert 0.0 <= top["knowledge_recall"] <= 1.0
    assert 0.0 <= top["accuracy"] <= 1.0
    assert top["detail_json"], "detail_json 不应为空"


def test_cli_parses_args(tmp_path, monkeypatch):
    """argparse 能解析 --subject/--limit/--real，且 mock 执行成功"""
    monkeypatch.setattr(run_eval, "REPORTS_DIR", str(tmp_path / "reports"))
    # 1) 参数解析
    args = run_eval.build_parser().parse_args(
        ["--subject", "math", "--limit", "10", "--real"])
    assert args.subject == "math"
    assert args.limit == 10
    assert args.real is True
    # 2) 默认值
    defaults = run_eval.build_parser().parse_args([])
    assert defaults.subject == "all" and defaults.limit == 0 and defaults.real is False
    # 3) main 可执行（mock 模式，避免依赖模型）
    assert run_eval.main(["--subject", "math", "--limit", "3"]) == 0
