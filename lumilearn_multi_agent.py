# -*- coding: utf-8 -*-
"""
LumiLearn 兼容性 shim — 多智能体协作与难度映射

提供 _map_level 等旧接口以便 student_learn.py 等代码平滑运行。
"""


def _map_level(diff: str) -> str:
    """难度映射"""
    return {"初中": "junior", "高中": "senior",
            "大学": "college"}.get(diff or "", "general")
