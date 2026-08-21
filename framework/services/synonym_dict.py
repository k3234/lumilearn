# -*- coding: utf-8 -*-
"""
LumiLearn 学科同义词词典与查询扩展
=====================================
用于提升关键词检索召回率：
  - 数学/物理/化学三大学科内置同义词组（每组 >= 20 条）
  - expand_query()：对查询文本做同义词扩展（同义词 OR 关系）
  - get_synonyms()：返回某词的同义词列表（不含自身）
  - get_synonym_stats()：各学科同义词组数统计

用法：
    from framework.services.synonym_dict import expand_query
    expand_query("函数的单调性", subject="数学")
    # -> ["函数的单调性", "单调性", "增减性", "单调", "增减"]

作者：LumiLearn
版本：1.0.0
日期：2026-08-21
"""

from typing import Dict, List

# 学科同义词组：学科 -> [同义词组...]，每组内任意词互为同义/近义表达
SYNONYM_GROUPS: Dict[str, List[List[str]]] = {
    # ---------------- 数学（22 组） ----------------
    "数学": [
        ["单调性", "增减性", "单调", "增减"],
        ["勾股定理", "毕达哥拉斯定理"],
        ["一元二次方程", "二次方程"],
        ["定义域", "自变量取值范围"],
        ["值域", "函数取值范围"],
        ["因式分解", "分解因式"],
        ["一次函数", "线性函数"],
        ["二次函数", "抛物线函数"],
        ["等差数列", "等差序列"],
        ["等比数列", "等比序列"],
        ["无理数", "无限不循环小数"],
        ["倒数", "互为倒数"],
        ["平行线", "平行直线"],
        ["垂直平分线", "中垂线"],
        ["三角形内角和", "内角和"],
        ["轴对称图形", "对称图形"],
        ["概率", "可能性"],
        ["平均数", "均值"],
        ["众数", "出现最多的数"],
        ["未知数", "变量"],
        ["幂", "次方"],
        ["开方", "平方根"],
        ["周长", "周界"],
        ["直角坐标系", "平面直角坐标系"],
    ],
    # ---------------- 物理（24 组） ----------------
    "物理": [
        ["牛顿第二定律", "第二运动定律"],
        ["加速度", "加速率"],
        ["动量", "冲量"],
        ["自由落体", "自由落体运动"],
        ["欧姆定律", "电流电压关系"],
        ["重力", "地心引力"],
        ["摩擦力", "摩擦阻力"],
        ["惯性定律", "牛顿第一定律"],
        ["匀速直线运动", "匀速运动"],
        ["动能定理", "功能定理"],
        ["电势差", "电压"],
        ["安培力", "磁场力"],
        ["焦耳定律", "电流热效应"],
        ["反射", "光的反射"],
        ["折射", "光的折射"],
        ["凸透镜", "会聚透镜"],
        ["凹透镜", "发散透镜"],
        ["液体压强", "液压"],
        ["浮力定律", "阿基米德原理"],
        ["杠杆平衡条件", "杠杆原理"],
        ["功", "做功"],
        ["热传递", "传热"],
        ["比热容", "比热"],
        ["电路", "回路"],
    ],
    # ---------------- 化学（24 组） ----------------
    "化学": [
        ["摩尔", "物质的量单位"],
        ["氧化还原", "氧化还原反应"],
        ["催化剂", "触媒"],
        ["共价键", "原子间共用电子对"],
        ["化学方程式", "化学反应方程式"],
        ["中和反应", "酸碱中和"],
        ["化合反应", "合成反应"],
        ["分解反应", "分解"],
        ["原子量", "相对原子质量"],
        ["分子量", "相对分子质量"],
        ["溶解度", "溶解能力"],
        ["沉淀", "沉淀物"],
        ["蒸馏", "蒸馏法"],
        ["配平", "方程式配平"],
        ["化学键", "原子间作用力"],
        ["氧化剂", "氧化性物质"],
        ["还原剂", "还原性物质"],
        ["元素周期表", "周期表"],
        ["指示剂", "酸碱指示剂"],
        ["质量守恒定律", "物质不灭定律"],
        ["金属活动性", "金属活泼性"],
        ["化学式", "分子式"],
        ["燃烧反应", "燃烧"],
        ["摩尔浓度", "物质的量浓度"],
    ],
}

# 不指定学科时的默认值（等价于全部学科）
_DEFAULT_SUBJECT = "all"


def _select_groups(subject: str) -> List[List[str]]:
    """按学科筛选同义词组；subject 为 all/空 时返回全部学科的组"""
    if not subject or subject == _DEFAULT_SUBJECT:
        return [g for groups in SYNONYM_GROUPS.values() for g in groups]
    return SYNONYM_GROUPS.get(subject, [])


def expand_query(query: str, subject: str = "all") -> List[str]:
    """
    对查询文本做同义词扩展。

    若 query 包含某同义词组的任一成员，则把该组全部成员追加进结果
    （同义词 OR 关系，多组命中时合并去重）；不命中任何组时返回 [query]。

    参数:
        query:   原始查询文本
        subject: 学科过滤，如 "数学"/"物理"/"化学"；"all" 表示全部学科
    返回:
        扩展后的查询词列表，首个元素始终为原始 query
    """
    if not query or not query.strip():
        return [query]
    expanded: List[str] = [query]
    for group in _select_groups(subject):
        if any(member in query for member in group):
            for member in group:
                if member not in expanded:
                    expanded.append(member)
    return expanded


def get_synonyms(term: str, subject: str = "all") -> List[str]:
    """
    返回某个词的同义词列表（不含自身）；未命中返回 []。
    """
    for group in _select_groups(subject):
        if term in group:
            return [m for m in group if m != term]
    return []


def get_synonym_stats() -> Dict:
    """返回各学科同义词组数统计（含 total）"""
    stats = {k: len(v) for k, v in SYNONYM_GROUPS.items()}
    stats["total"] = sum(stats.values())
    return stats
