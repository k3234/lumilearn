# -*- coding: utf-8 -*-
"""
LumiLearn 学生认知模型（StudentModel）
=====================================
抽象接口 + 轻量默认实现。

接口层即「开放对接外部引擎」的接缝：
- 未来可用 openMAIC 等外部认知引擎实现同一接口（estimate_mastery / observe / get_weak_points）
- 默认实现读写现有 progress 表，供当前 API 直接消费，不绑定外部依赖。

掌握度口径：mastery ∈ [0,1]，默认用「正确率加权 + 时间 + 放弃惩罚」综合分，
由 record_progress 的指数移动平均（EMA）写回 progress 表。
"""
import logging

from framework.database import db

logger = logging.getLogger("lumilearn.knowledge.student_model")

# 掌握度判定阈值
MASTERED = 0.7      # ≥ 视为已掌握
WEAK = 0.6          # < 视为薄弱（待补）

# 外接引擎占位：可注入实现同一接口的对象（如 openMAIC 认知追踪引擎）
_external = None


def set_external_engine(engine_obj):
    """注入外部认知引擎（实现 StudentModel 接口）。传入 None 恢复默认。"""
    global _external
    _external = engine_obj


class StudentModel:
    """学生认知模型接口（所有实现需满足）"""

    def estimate_mastery(self, user_id, node_id):
        """估算某学生对某知识点的掌握度 [0,1]。"""
        raise NotImplementedError

    def observe(self, user_id, node_id, evidence):
        """观察一次答题/学习证据并更新掌握度。evidence: dict。"""
        raise NotImplementedError

    def get_weak_points(self, user_id, subject=None):
        """获取学生薄弱知识点列表（mastery < WEAK）。"""
        raise NotImplementedError


class KnowledgeEngine(StudentModel):
    """轻量默认实现：读写现有 progress / knowledge_nodes 表。"""

    def estimate_mastery(self, user_id, node_id):
        row = self._get_progress(user_id, node_id)
        return row["mastery"] if row else 0.0

    def observe(self, user_id, node_id, evidence=None):
        """根据单条答题证据计算综合分并写回 progress。

        evidence 字段：
            is_correct   0/1 是否正确
            hints_used   int 使用提示次数
            time_spent   float 用时秒
            gave_up      0/1 是否放弃
        综合分 = 正确性(0.7) + 未被提示/放弃的通畅度(0.3)，用时过长微调。
        """
        evidence = evidence or {}
        is_correct = 1 if evidence.get("is_correct") else 0
        gave_up = 1 if evidence.get("gave_up") else 0
        hints = int(evidence.get("hints_used") or 0)
        time_spent = float(evidence.get("time_spent") or 0)

        # 通畅度：未放弃 且 未依赖提示 = 1；否则按提示次数递减
        fluency = 0.0
        if not gave_up:
            fluency = max(0.0, 1.0 - 0.3 * hints)

        score = 0.7 * is_correct + 0.3 * fluency
        # 用时惩罚：异常长用时（> 300s）暗示卡顿，轻微下调
        if time_spent > 300:
            score *= 0.9

        try:
            db.record_progress(user_id, node_id, score=score, time_spent=time_spent)
        except Exception as e:
            logger.warning("record_progress 失败 user=%s node=%s: %s", user_id, node_id, e)

        # 数据「成长」：积累知识 + 分层记忆（失败不影响主流程）
        mastery = self.estimate_mastery(user_id, node_id)
        try:
            from framework.knowledge.growth import observe_and_grow
            observe_and_grow(user_id, node_id, mastery,
                             evidence=evidence, is_correct=is_correct,
                             subject=evidence.get("subject", ""))
        except Exception as e:
            logger.warning("growth 成长回调失败 user=%s node=%s: %s", user_id, node_id, e)
        return mastery

    def get_weak_points(self, user_id, subject=None):
        """返回薄弱知识点列表（mastery < WEAK），含前置依赖信息。"""
        nodes = db.get_knowledge_nodes(subject)
        weak = []
        for n in nodes:
            mastery = self.estimate_mastery(user_id, n["id"])
            if mastery < WEAK:
                weak.append({
                    "node_id": n["id"],
                    "name": n["name"],
                    "category": n.get("category", ""),
                    "difficulty": n.get("difficulty", 1),
                    "mastery": round(mastery, 3),
                    "prereqs": self._parse_prereqs(n),
                })
        return weak

    def get_path(self, user_id, subject=None):
        """生成个性化路径：薄弱知识点按前置依赖拓扑排序。"""
        nodes = {n["id"]: n for n in db.get_knowledge_nodes(subject)}
        weak = self.get_weak_points(user_id, subject)
        # 拓扑排序：前置未掌握的先排（递归收集依赖内薄弱点）
        ordered, visiting = [], set()

        def visit(nid):
            if nid in visiting or nid in {x["node_id"] for x in ordered}:
                return
            visiting.add(nid)
            n = nodes.get(nid)
            if n:
                for pre in self._parse_prereqs(n):
                    if pre in nodes and self.estimate_mastery(user_id, pre) < WEAK:
                        visit(pre)
            visiting.discard(nid)
            ordered.append({"node_id": nid, "name": n.get("name", nid),
                            "category": n.get("category", ""), "difficulty": n.get("difficulty", 1)})

        for item in weak:
            visit(item["node_id"])
        return ordered

    # ── 内部工具 ──
    def _get_progress(self, user_id, node_id):
        try:
            return db._query_one(
                "SELECT * FROM progress WHERE user_id = ? AND node_id = ?",
                (user_id, node_id),
            )
        except Exception:
            return None

    @staticmethod
    def _parse_prereqs(node):
        import json
        raw = node.get("prereqs") or "[]"
        if isinstance(raw, (list, tuple)):
            return list(raw)
        try:
            return json.loads(raw) if raw else []
        except Exception:
            return []