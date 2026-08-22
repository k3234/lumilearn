# -*- coding: utf-8 -*-
"""复赛任务①：标准化对比评测 CLI（run_comparative_eval）测试"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest

from scripts.run_comparative_eval import (
    load_datasets,
    _answer_numbers,
    _answer_num_units,
    _answer_core_text,
    _equivalent_texts,
    check_hallucination_simple,
    is_answer_correct,
)


def test_load_datasets_per_subject():
    """per_subject 均衡加载：math/physics/chemistry 各 N 题"""
    items = load_datasets("all", per_subject=3)
    assert len(items) == 9
    from collections import Counter
    cnt = Counter(i["subject"] for i in items)
    assert cnt == {"math": 3, "physics": 3, "chemistry": 3}


def test_answer_numbers_ignores_common():
    """核心数值提取：忽略常见常数，保留答案数字"""
    assert _answer_numbers("5") == ["5"]
    assert _answer_numbers("1/2") == ["2"]      # "1" 是常见常数被忽略
    assert _answer_numbers("12") == ["12"]


def test_answer_num_units_real_only():
    """数值+单位提取：仅真实物理单位（排除 1/2 的 '/'、x² 变量）"""
    assert _answer_num_units("2m/s²") == [("2", "m/s²")]
    assert _answer_num_units("1/2") == []       # '/' 非真实单位
    assert _answer_num_units("3x²") == []       # x² 是变量非单位
    assert _answer_num_units("10N") == [("10", "N")]
    assert _answer_num_units("18g/mol") == [("18", "g/mol")]


def test_answer_core_text_strips_stopchars():
    """核心文本：剔除停用字与空白"""
    assert _answer_core_text("单调递减") == "单调递减"
    assert _answer_core_text("与推力方向相反") == "推力方向相反"
    assert _answer_core_text("cos x") == "cosx"


def test_equivalent_texts():
    """数值等价文本：分数→小数、π→近似"""
    assert "1/2" in _equivalent_texts("1/2")
    assert "0.5" in _equivalent_texts("1/2")
    assert "8π" in _equivalent_texts("8π")
    assert "25.12" in _equivalent_texts("8π")


def test_is_answer_correct_numeric():
    """数值答案答对判定"""
    assert is_answer_correct("斜边长为5。根据勾股定理...", {"answer": "5"})
    assert not is_answer_correct("答案是6。", {"answer": "5"})


def test_is_answer_correct_fraction():
    """分数答案：1/2 或 0.5 均判对"""
    assert is_answer_correct(r"答案是 \(\frac{1}{2}\)。", {"answer": "1/2"})
    assert is_answer_correct("答案是0.5。", {"answer": "1/2"})


def test_is_answer_correct_unit_aliases():
    """带单位答案：中文/符号单位别名均可"""
    assert is_answer_correct("该用电器的电功率为1100瓦。", {"answer": "1100W"})
    assert is_answer_correct("消耗电能为1千瓦时。", {"answer": "1kWh"})
    assert is_answer_correct("加速度为2 m/s²。", {"answer": "2m/s²"})


def test_is_answer_correct_text_synonym():
    """文本答案：近义词兜底"""
    assert is_answer_correct("在R上是严格递增的。", {"answer": "单调递增"})
    assert is_answer_correct("墙对人的反作用力方向是向后的。", {"answer": "与推力方向相反"})
    assert is_answer_correct("产物是氯化钠和水。", {"answer": "NaCl和H₂O"})


def test_hallucination_simple():
    """单路幻觉：同单位不同数值 → 1；正确值 → 0；无单位 → 0"""
    # 模型输出 10m/s，答案 20m/s → 矛盾
    assert check_hallucination_simple("速度是10 m/s。", {"answer": "20m/s"}) == 1
    # 模型输出 20m/s，答案 20m/s → 一致
    assert check_hallucination_simple("速度是20 m/s。", {"answer": "20m/s"}) == 0
    # 纯数字答案不做数值幻觉判定
    assert check_hallucination_simple("答案是5。", {"answer": "5"}) == 0
