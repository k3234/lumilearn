# -*- coding: utf-8 -*-
"""
LumiLearn 认知状态推断（CognitiveState）
========================================
由行为信号（答题行为）推断学生的隐性认知状态，供教学代理在上课前调整策略。

基于轻量规则分类（不经大模型），信号来源：
    - 正确率（is_correct / 最近 N 题）
    - 用时（time_spent，与同难度中位用时对比）
    - 放弃（gave_up）
    - 依赖提示（hints_used）

状态集：
    engaged    投入（快且准）
    confused   困惑（长时+低正确）
    frustrated 挫败（连续错+放弃/求帮助）
    distracted 分心（激短用时+低正确，或长时间无操作）
"""
import logging
import time

from framework.database import db

logger = logging.getLogger("lumilearn.knowledge.cognitive")

# 认知状态集合
STATES = ("engaged", "confused", "frustrated", "distracted")
# 默认判定阈值（秒）
TIME_LONG = 120
TIME_SHORT = 8
RECENT_N = 5


def _recent_answers(user_id, limit=RECENT_N):
    """取用户最近 N 条答题记录。"""
    try:
        return list(db._query(
            "SELECT is_correct, hints_used, time_spent, gave_up "
            "FROM answers WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, int(limit)),
        ))
    except Exception:
        return []


def infer(user_id, latest_evidence=None):
    """推断当前认知状态。

    latest_evidence（可选）: 最新一条答题证据 dict，
    用以覆盖可能还没落库的当前题。
    """
    rows = _recent_answers(user_id)
    if latest_evidence:
        rows.insert(0, {
            "is_correct": latest_evidence.get("is_correct"),
            "hints_used": latest_evidence.get("hints_used"),
            "time_spent": latest_evidence.get("time_spent"),
            "gave_up": latest_evidence.get("gave_up"),
        })

    if not rows:
        return {"state": "unknown", "confidence": 0.0, "signals": {}}

    correct = sum(1 for r in rows if r.get("is_correct"))
    gave_up = sum(1 for r in rows if r.get("gave_up"))
    hints = sum(1 for r in rows if (r.get("hints_used") or 0) > 0)
    times = [float(r.get("time_spent") or 0) for r in rows]
    avg_time = sum(times) / len(times) if times else 0
    n = len(rows)

    signals = {
        "correctness": round(correct / n, 2),
        "gave_up": round(gave_up / n, 2),
        "hint_dependency": round(hints / n, 2),
        "avg_time": round(avg_time, 1),
        "n": n,
    }

    # 规则分类（优先级从强信号到弱）
    state = "engaged"
    if gave_up >= 2 or (correct == 0 and n >= 3 and hints >= 1):
        state = "frustrated"
    elif avg_time > TIME_LONG and correct / n < 0.5:
        state = "confused"
    elif avg_time < TIME_SHORT and (correct / n < 0.4 or n >= RECENT_N):
        state = "distracted"
    elif correct / n >= 0.8 and avg_time <= TIME_LONG:
        state = "engaged"

    confidence = round(min(0.9, 0.4 + 0.1 * n), 2)
    return {"state": state, "confidence": confidence, "signals": signals}


def record(user_id, state_info):
    """将认知状态写入 student_thoughts（若表存在则写入，否则静默跳过）。"""
    try:
        db._execute(
            "INSERT INTO student_thoughts (user_id, content, created_at) "
            "VALUES (?, ?, ?)",
            (user_id,
             "[cognitive_state] %s (%.2f)" % (state_info.get("state", "unknown"),
                                              state_info.get("confidence", 0)),
             time.strftime("%Y-%m-%d %H:%M:%S")),
        )
    except Exception as e:
        logger.debug("student_thoughts 写入跳过: %s", e)