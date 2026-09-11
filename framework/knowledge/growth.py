# -*- coding: utf-8 -*-
"""
LumiLearn 数据「成长」积累（Growth）
=====================================
让数据库在学习中不断「长大」，沉淀为：
- knowledge_accumulation：新知识 / 复用频次累计（供资料共享与后续本地训练语料）
- layered_memory：短期→中期→长期分层记忆（掌握度驱动升级）
- 每次学习/答题由知识引擎 observe 后回调，与 BKT 联动。

设计原则：轻量、失败不影响主流程（写库异常仅记录 warning），纯数据驱动。
"""
import logging

from framework.database import db

logger = logging.getLogger("lumilearn.knowledge.growth")

# 分层记忆阈值
LONG_LAYER = 0.8   # ≥ 升入长期记忆
MID_LAYER = 0.5    # ≥ 中期记忆，否则待复习短期层


def accumulate(user_id, node_id=None, is_correct=0, subject="", evidence=None,
               topic="", knowledge_type="学习片段", quality_score=0.0):
    """写/更新 knowledge_accumulation：学习一次知识即累积一次，正确多次提质量。

    返回 dict（ok + echo 信息）；异常静默兜底。
    """
    evidence = evidence or {}
    if not node_id:
        node_id = topic or "topic:" + str(int(is_correct))
    try:
        db.save_knowledge(
            knowledge_id=str(node_id),  # 去重用 knowledge_id
            topic=node_id if isinstance(node_id, str) and len(node_id) < 100 else str(node_id),
            subject=subject or evidence.get("subject") or "综合",
            knowledge_type=knowledge_type,
            content=(evidence.get("summary") or "")[:2000],
            summary=(evidence.get("summary") or ""),
            source_agent=evidence.get("source_agent") or "lumi-studyloop",
            quality_score=quality_score,
        )
        # 复用频次累计
        db.increment_knowledge_usage(str(node_id))
        return {"ok": True}
    except Exception as e:
        logger.warning("accumulate 失败 user=%s node=%s: %s", user_id, node_id, e)
        return {"ok": False, "error": str(e)}


def memory_layer(user_id, node_id=None, mastery=0.0, topic="", content="",
                 is_wrong_answer=0, session_id=None):
    """按掌握度写入分层记忆（short 待复习 / mid 短期 / long 长期）。

    mastery ≥ LONG_LAYER  → long
    mastery ≥ MID_LAYER   → mid
    否则                    → short（待复习）
    """
    try:
        memory_type = "long" if mastery >= LONG_LAYER else ("mid" if mastery >= MID_LAYER else "short")
        display = topic or node_id or "综合"
        db.save_memory(
            user_id=str(user_id), memory_type=memory_type, session_id=session_id,
            chapter=display, topic=display, content=content or display,
            is_wrong_answer=is_wrong_answer,
        )
        return {"ok": True, "layer": memory_type}
    except Exception as e:
        logger.warning("memory_layer 失败 user=%s node=%s: %s", user_id, node_id, e)
        return {"ok": False, "error": str(e)}


def observe_and_grow(user_id, node_id, mastery, evidence=None, is_correct=0, subject=""):
    """BKT observe 后的成长回调：积累知识 + 分层记忆。

    由知识引擎 / 学习流程在掌握度更新后调用一次。
    """
    result_acc = accumulate(user_id, node_id=node_id, is_correct=is_correct,
                            subject=subject, evidence=evidence)
    result_mem = memory_layer(user_id, node_id=node_id, mastery=mastery,
                              topic=evidence.get("topic") if evidence else None,
                              is_wrong_answer=0 if is_correct else 1,
                              session_id=evidence.get("session_id") if evidence else None)
    return {"accumulate": result_acc, "memory": result_mem}