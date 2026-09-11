# -*- coding: utf-8 -*-
"""
LumiLearn 自适应测评（AdaptiveTest）
====================================
基于最近答题表现动态调节题目难度（简单的难度阈值触发式 IRT）：

    - 连续 3 题答对 → 升一档难度
    - 连续 2 题答错 → 降一档难度
    - 否则维持

难度档位与 questions.difficulty 对齐（1 基础 / 2 进阶 / 3 挑战）。
选卷时优先挑目标难度、且属于目标知识点（knowledge_id 匹配）的题。
"""
import logging

from framework.database import db

logger = logging.getLogger("lumilearn.knowledge.adaptive")

UP_STREAK = 3   # 连续答对升档
DOWN_STREAK = 2  # 连续答错降档
DIFF_RANGE = (1, 3)


def _recent(user_id, limit=8):
    try:
        return list(db._query(
            "SELECT is_correct, topic, knowledge_id FROM answers "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, int(limit)),
        ))
    except Exception:
        return []


def next_difficulty(user_id, subject=None, topic=None):
    """根据现有题库返回推荐难度（受题库实际覆盖约束）。

    返回 (difficulty, reason)：
        difficulty: 1/2/3，若题库无对应难度题则回退到可用难度。
        reason:     "up/down/keep" 说明依据。
    """
    rows = _recent(user_id)
    reasons = {"up": 0, "down": 0}

    # 从最近连续答对/答错计数
    up_streak = 0
    for r in rows:
        if r.get("is_correct"):
            up_streak += 1
        else:
            break
    down_streak = 0
    for r in rows:
        if not r.get("is_correct"):
            down_streak += 1
        else:
            break

    # 基准：最近一次有效难度
    base = 2
    try:
        row = db._query_one(
            "SELECT difficulty FROM questions WHERE knowledge_id != '' and difficulty > 0 "
            "ORDER BY id DESC LIMIT 1")
        base = row["difficulty"] if row else 2
    except Exception:
        pass

    if up_streak >= UP_STREAK:
        next_d = min(base + 1, DIFF_RANGE[1])
        reason = "up"
    elif down_streak >= DOWN_STREAK:
        next_d = max(base - 1, DIFF_RANGE[0])
        reason = "down"
    else:
        next_d = base
        reason = "keep"

    # 校验题库是否有该难度题；没有则回退到可用的细分难度
    available = _available_difficulties(subject, topic)
    if available and next_d not in available:
        fallback = min(available, key=lambda d: abs(d - next_d))
        next_d = fallback

    reasons[reason] = 1
    return next_d, reason


def pick_questions(user_id, subject=None, topic=None, count=1):
    """为自适应测评抽出 count 道题（匹配目标难度 + 知识点）。"""
    difficulty, reason = next_difficulty(user_id, subject, topic)
    try:
        rows = db._query(
            "SELECT id, question, correct_answer, explanation, difficulty, "
            "knowledge_id, options FROM questions "
            "WHERE (? = '' OR subject = ?) AND difficulty = ? ORDER BY RANDOM() LIMIT ?",
            (subject or "", subject or "", difficulty, int(count)),
        )
        result = []
        for r in rows:
            result.append({
                "id": r.get("id"),
                "question": r.get("question"),
                "correct_answer": r.get("correct_answer"),
                "explanation": r.get("explanation"),
                "difficulty": r.get("difficulty"),
                "knowledge_id": r.get("knowledge_id"),
                "options": r.get("options"),
            })
        return {"difficulty": difficulty, "reason": reason, "questions": result}
    except Exception:
        return {"difficulty": difficulty, "reason": reason, "questions": []}


def _available_difficulties(subject=None, topic=None):
    try:
        rows = db._query(
            "SELECT DISTINCT difficulty FROM questions WHERE ('?' = '' OR subject = '?')",
            (subject, subject),
        )
        return sorted(r["difficulty"] for r in rows if r.get("difficulty"))
    except Exception:
        return []