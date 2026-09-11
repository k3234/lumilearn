# -*- coding: utf-8 -*-
"""
LumiLearn 自适应学习路径引擎（PathEngine）
==========================================
在学生认知模型之上，根据掌握度 + 前置依赖生成个性化学习路径：

    1. 找到学生所有薄弱知识点（mastery < WEAK）
    2. 按前置依赖关系拓扑排序（缺前置先修前置）
    3. 输出有序学习任务序列

复用 StudentModel.get_path 的拓扑逻辑，本模块提供更友好的单函数入口
与推荐「下一个学习点」。
"""
import logging

from framework.database import db
from .student_model import KnowledgeEngine, WEAK

logger = logging.getLogger("lumilearn.knowledge.path")


class PathEngine:
    def __init__(self, model=None):
        self.model = model or KnowledgeEngine()

    def build(self, user_id, subject=None):
        """生成完整个性路径（前置优先）。"""
        ordered = self.model.get_path(user_id, subject)
        # 附上每步的掌握度快照
        path = []
        for step in ordered:
            mastery = self.model.estimate_mastery(user_id, step["node_id"])
            path.append({**step, "mastery": round(mastery, 3)})
        return path

    def next(self, user_id, subject=None, limit=5):
        """推荐接下来应该学习的知识点（已排序，取前 limit）。"""
        return self.build(user_id, subject)[:limit]

    def weak_points(self, user_id, subject=None):
        return self.model.get_weak_points(user_id, subject)

    def overall_progress(self, user_id):
        """总体掌握度概览。"""
        try:
            return db.get_progress(user_id)
        except Exception:
            return {"total_nodes": 0, "studied": 0, "mastered": 0, "overall_progress": 0, "nodes": []}