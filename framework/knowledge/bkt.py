# -*- coding: utf-8 -*-
"""
LumiLearn 贝叶斯知识追踪（BKT）
==============================
Khan Academy 验证有效的知识追踪算法：根据单次答题结果更新知识点的
掌握度后验概率。

标准 BKT 参数：
    guess  — 未掌握但猜对概率 (0.1)
    slip   — 已掌握但失误概率 (0.1)
    learn  — 单次机会学习转移概率 (0.2)

本实现与 student_model 的 StudentModel.observe 形成互补：
- observe 计算「综合分」供进度展示；
- bkt.observe  更新「掌握度后验」，更贴近认知状态。
两者都写回 progress 表（mastery 列），BKT 作为掌握度更新主口径。
"""
import logging

from framework.database import db

logger = logging.getLogger("lumilearn.knowledge.bkt")

# 默认 BKT 参数（L4 路线图建议值）
DEFAULT_PARAMS = {"guess": 0.1, "slip": 0.1, "learn": 0.2}
# 掌握度阈值：超过视为已掌握
MASTERED_THRESHOLD = 0.8


class BKT:
    """贝叶斯知识追踪引擎"""

    def __init__(self, guess=None, slip=None, learn=None):
        p = dict(DEFAULT_PARAMS)
        p.update({
            "guess": DEFAULT_PARAMS["guess"] if guess is None else guess,
            "slip": DEFAULT_PARAMS["slip"] if slip is None else slip,
            "learn": DEFAULT_PARAMS["learn"] if learn is None else learn,
        })
        self.guess, self.slip, self.learn = p["guess"], p["slip"], p["learn"]

    def observe(self, user_id, node_id, is_correct, gap_seconds=None, validate=False):
        """更新知识点掌握度后验，写回 progress 表。

        is_correct: 0/1
        返回更新后的掌握度 [0,1]。
        """
        mastery = self._current_mastery(user_id, node_id)

        if is_correct:
            # 答对：掌握度上升（排除猜对），并叠加学习转移
            p1 = mastery * (1 - self.slip) + (1 - mastery) * self.guess
            p_learn = p1 + (1 - p1) * self.learn
            new_mastery = min(1.0, p_learn)
        else:
            # 答错：掌握度下降（排除失误）
            new_mastery = mastery * self.slip + (1 - mastery) * (1 - self.guess)
            new_mastery = max(0.0, new_mastery)

        db.record_progress(user_id, node_id, score=new_mastery, time_spent=0)
        return new_mastery

    def mastered(self, user_id, node_id):
        """该知识点是否已掌握（mastery ≥ 阈值）"""
        return self._current_mastery(user_id, node_id) >= MASTERED_THRESHOLD

    def _current_mastery(self, user_id, node_id):
        try:
            row = db._query_one(
                "SELECT mastery FROM progress WHERE user_id = ? AND node_id = ?",
                (user_id, node_id),
            )
            return row["mastery"] if row else 0.0
        except Exception:
            return 0.0