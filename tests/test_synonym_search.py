#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task 4: 同义词词典 + 查询扩展 + 引用来源 单元测试

覆盖：
  - expand_query 命中/未命中
  - 学科同义词组数量统计（数/物/化各 >= 20 条）
  - 同义词扩展召回（不依赖真实数据库，mock _load_docs）
  - search_semantic 占位返回 []
  - search 结果包含 source/snippet 结构化字段
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.services.knowledge_retrieval import KnowledgeRetriever
from framework.services.synonym_dict import (
    expand_query,
    get_synonym_stats,
    get_synonyms,
)

# 构造的内存测试文档（不依赖数据库）
_TEST_DOCS = [
    {
        "source": "training_data",
        "id": 1,
        "title": "函数单调性",
        "subject": "数学",
        "grade": "高一",
        "difficulty": "medium",
        "content": (
            "函数单调性定义：设函数 f(x) 在区间 D 上有定义，"
            "若对任意 x1<x2 都有 f(x1)<f(x2)，则称 f 在 D 上单调递增。"
        ),
        "keywords": "单调性,函数",
        "_text": "数学 高一 函数单调性 函数单调性定义：设函数 f(x) 在区间 D 上有定义",
    },
    {
        "source": "knowledge_node",
        "id": 2,
        "title": "牛顿第二定律",
        "subject": "物理",
        "grade": "",
        "difficulty": "easy",
        "content": (
            "牛顿第二定律：物体加速度的大小跟作用力成正比，"
            "跟物体的质量成反比，加速度的方向跟作用力的方向相同。"
        ),
        "keywords": "",
        "_text": "物理 牛顿第二定律 物体加速度的大小跟作用力成正比",
    },
]


def _make_retriever() -> KnowledgeRetriever:
    """实例化检索器并 mock 数据源，避免访问真实数据库"""
    r = KnowledgeRetriever()
    r._load_docs = lambda: [dict(d) for d in _TEST_DOCS]
    return r


def test_expand_query_hit():
    """query 含同义词组成员时返回整组"""
    expanded = expand_query("函数单调性")
    assert expanded[0] == "函数单调性"
    group = {"单调性", "增减性", "单调", "增减"}
    assert group.issubset(set(expanded))
    # 学科限定不误伤：数学组的词在物理学科下不扩展
    assert expand_query("单调性", subject="物理") == ["单调性"]


def test_expand_query_no_hit():
    """不命中任何同义词组时返回 [query]"""
    assert expand_query("恐龙时代") == ["恐龙时代"]
    assert expand_query("光合作用") == ["光合作用"]
    # 空查询返回 [原值]
    assert expand_query("") == [""]


def test_synonym_stats():
    """数/物/化各组同义词组数 >= 20 条"""
    stats = get_synonym_stats()
    for subj in ("数学", "物理", "化学"):
        assert subj in stats
        assert stats[subj] >= 20, f"{subj} 同义词组数 {stats[subj]} < 20"
    assert stats["total"] >= 60
    # get_synonyms 单点验证
    assert "增减性" in get_synonyms("单调性")
    assert get_synonyms("单调性") == ["增减性", "单调", "增减"]
    assert get_synonyms("不存在的词") == []


def test_search_synonym_recall():
    """查询"增减性"能召回含"单调"的文档（同义词扩展生效）"""
    r = _make_retriever()
    r.build_index()
    results = r.search("增减性", top_k=5, subject="数学")
    ids = {d.get("id") for d in results}
    assert 1 in ids, f"同义词扩展未召回单调性文档，实际: {results}"


def test_search_semantic_placeholder():
    """search_semantic 占位方法返回 []"""
    r = _make_retriever()
    assert r.search_semantic("任意查询", top_k=5) == []
    assert r.search_semantic("牛顿第二定律", subject="物理") == []


def test_result_structured_fields():
    """search 返回结果含 source/snippet 字段（doc_id 用 id）"""
    r = _make_retriever()
    r.build_index()
    results = r.search("牛顿第二定律", top_k=5)
    assert results, "牛顿第二定律应召回物理文档"
    for res in results:
        assert "source" in res and res["source"]
        assert "id" in res
        assert "snippet" in res
        # snippet 为 content 前 200 字
        assert res["snippet"] == (res.get("content") or "")[:200]
