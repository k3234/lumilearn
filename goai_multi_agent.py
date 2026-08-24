# -*- coding: utf-8 -*-
"""
LumiLearn 兼容性 shim — 替代已删除的 goai_multi_agent.py

提供 _map_level 等旧接口以便 student_learn.py 等代码平滑运行。
"""


def _map_level(diff: str) -> str:
    """难度映射：兼容旧 goai_multi_agent.py _map_level 接口"""
    return {"初中": "junior", "高中": "senior",
            "大学": "college"}.get(diff or "", "general")
