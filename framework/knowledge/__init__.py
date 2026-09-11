# -*- coding: utf-8 -*-
"""
LumiLearn L4 知识引擎包
========================
为「虚拟老师」能力闭环提供轻量、可替换的算法引擎：

- student_model  : 学生认知模型抽象接口 + 默认实现（读写 progress 表）
- bkt            : 贝叶斯知识追踪（答题后更新掌握度后验）
- path_engine    : 自适应学习路径（前置依赖 + 掌握度排序）
- cognitive_state: 认知状态推断（困惑/挫败/投入/分心 规则分类）
- adaptive_test  : 自适应测评（难度阈值触发）

设计原则：全部为纯规则/数据驱动，不依赖外部大模型；接口层后续可整体
替换为 openMAIC 等外部认知引擎（实现同一 StudentModel 接口即可）。
"""
from .student_model import KnowledgeEngine, StudentModel  # noqa: F401
from .bkt import BKT  # noqa: F401
from . import growth  # noqa: F401

engine = KnowledgeEngine()  # 全局知识引擎单例（BKT + StudentModel 默认实现）

__all__ = ["KnowledgeEngine", "StudentModel", "BKT", "growth", "engine"]