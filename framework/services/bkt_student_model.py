# -*- coding: utf-8 -*-
"""
L4 知识追踪引擎 — BKT 贝叶斯知识追踪 + 学生模型
Khan Academy 验证有效：知识历史 → 正确率 +3.4%；前置知识点告知 → +2.7%

核心算法：贝叶斯知识追踪 (Bayesian Knowledge Tracing, BKT)
- guess (G)：学生未掌握却答对的概率（瞎猜），默认 0.1
- slip (S)：学生已掌握却答错的概率（失误），默认 0.1
- learn (T)：由未掌握转为已掌握的概率（学习转移），默认 0.2
- p：当前知识点掌握度的后验概率

更新公式：
  答对：p' = (p × 1) / (p × 1 + (1-p) × G)
  答错：p' = (p × S) / (p × S + (1-p) × 1)

作者：lumilearn AI自动化专家
日期：2026-09-07
"""

import json
import math
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any


# ============================================================
# 常量
# ============================================================
BKT_DEFAULT_GUESS = 0.1      # 猜对概率
BKT_DEFAULT_SLIP = 0.1       # 失误概率
BKT_DEFAULT_LEARN = 0.2      # 学习转移概率
BKT_DEFAULT_PRIOR = 0.35     # 先验掌握度（新用户）
PROGRESS_DIR = os.environ.get(
    "LUMILEARN_PROGRESS_DIR",
    str(Path(__file__).resolve().parent.parent.parent.parent / "data" / "bkt_progress"),
)


# ============================================================
# 数据结构
# ============================================================
@dataclass
class BKTNodeParams:
    """单个知识节点的 BKT 参数"""
    guess: float = BKT_DEFAULT_GUESS
    slip: float = BKT_DEFAULT_SLIP
    learn: float = BKT_DEFAULT_LEARN
    prior: float = BKT_DEFAULT_PRIOR

    def to_dict(self) -> dict:
        return {"guess": self.guess, "slip": self.slip, "learn": self.learn, "prior": self.prior}

    @classmethod
    def from_dict(cls, d: dict) -> "BKTNodeParams":
        return cls(
            guess=d.get("guess", BKT_DEFAULT_GUESS),
            slip=d.get("slip", BKT_DEFAULT_SLIP),
            learn=d.get("learn", BKT_DEFAULT_LEARN),
            prior=d.get("prior", BKT_DEFAULT_PRIOR),
        )


@dataclass
class BKTStudentState:
    """单个学生、单个知识点的 BKT 状态"""
    p: float = BKT_DEFAULT_PRIOR        # 当前掌握度后验概率 [0,1]
    prev_p: float = BKT_DEFAULT_PRIOR   # 上一次的 p（用于检测变化）
    total_correct: int = 0              # 累计答对次数
    total_wrong: int = 0                # 累计答错次数
    last_updated: float = 0.0           # 最后更新时间戳
    history: List[Dict] = field(default_factory=list)  # 最近 50 条交互记录

    def to_dict(self) -> dict:
        return {
            "p": round(self.p, 4),
            "prev_p": round(self.prev_p, 4),
            "p_change": round(self.p - self.prev_p, 4),
            "total_correct": self.total_correct,
            "total_wrong": self.total_wrong,
            "total_attempts": self.total_correct + self.total_wrong,
            "accuracy": round(
                self.total_correct / max(self.total_correct + self.total_wrong, 1), 2
            ),
            "last_updated": self.last_updated,
            "recent_history": self.history[-20:],
        }


@dataclass
class CognitiveState:
    """学生认知状态（推断自答题行为）"""
    state: str = "unknown"   # confident | fluent | confused | frustrated | novice
    confidence: float = 0.0  # [0,1] 自信度
    reasoning: str = ""      # 推断理由
    detected_at: float = 0.0

    def to_dict(self) -> dict:
        return {"state": self.state, "confidence": round(self.confidence, 2),
                "reasoning": self.reasoning, "detected_at": self.detected_at}


# ============================================================
# BKT 核心算法
# ============================================================
class BKTTracker:
    """
    贝叶斯知识追踪引擎

    每次交互（答题）后，用贝叶斯公式更新知识点的掌握度后验概率 p。

    公式推导：
      P(正确|θ_t=1) = 1 - slip      （已掌握却答错 = slip）
      P(正确|θ_t=0) = guess         （未掌握却答对 = guess）
      P(θ_t=1) = p                  （当前掌握度）

      答对：p' = P(θ_t=1|正确) = p×(1-slip) / [p×(1-slip) + (1-p)×guess]
      答错：p' = P(θ_t=1|错误) = p×slip  / [p×slip  + (1-p)×1]
    """

    def __init__(self, node_params: Optional[BKTNodeParams] = None):
        self.params = node_params or BKTNodeParams()
        self.state = BKTStudentState(p=self.params.prior)

    def update(self, observed_correct: bool) -> Dict:
        """
        执行一次 BKT 更新，返回更新后的状态摘要。

        参数:
            observed_correct: True=学生答对，False=学生答错

        返回:
            dict 包含: p (新掌握度), p_change (变化量), correct (本次是否正确)
        """
        g = self.params.guess
        s = self.params.slip
        old_p = self.state.p

        if observed_correct:
            # 贝叶斯更新：答对
            numerator = old_p * (1 - s)
            denominator = numerator + (1 - old_p) * g
            new_p = numerator / denominator if denominator > 0 else old_p
        else:
            # 贝叶斯更新：答错
            numerator = old_p * s
            denominator = numerator + (1 - old_p) * 1
            new_p = numerator / denominator if denominator > 0 else old_p

        # 防数值异常：确保 [0, 1] 区间内
        new_p = max(0.001, min(0.999, new_p))

        self.state.prev_p = old_p
        self.state.p = new_p
        self.state.last_updated = time.time()

        if observed_correct:
            self.state.total_correct += 1
        else:
            self.state.total_wrong += 1

        # 记录交互历史
        self.state.history.append({
            "correct": observed_correct,
            "p_before": round(old_p, 4),
            "p_after": round(new_p, 4),
            "p_change": round(new_p - old_p, 4),
            "ts": self.state.last_updated,
        })
        if len(self.state.history) > 50:
            self.state.history = self.state.history[-50:]

        return {
            "p": round(new_p, 4),
            "p_change": round(new_p - old_p, 4),
            "correct": observed_correct,
            "guess": g,
            "slip": s,
            "learn": self.params.learn,
        }

    def predict_next_accuracy(self) -> float:
        """预测下一次答题的正确概率 = p×(1-slip) + (1-p)×guess"""
        p = self.state.p
        return p * (1 - self.params.slip) + (1 - p) * self.params.guess

    def infer_cognitive_state(self) -> CognitiveState:
        """
        根据 BKT 状态推断认知状态。

        规则：
          confident:    p ≥ 0.85 且 最近5题正确率 ≥ 80%
          fluent:       p ≥ 0.6  且  无连续错误
          confused:     p < 0.4  且  连续2次以上错误
          frustrated:   p < 0.3  且  连续3次以上错误
          novice:       总尝试次数 < 3
        """
        history = self.state.history[-10:]
        total_attempts = self.state.total_correct + self.state.total_wrong
        p = self.state.p

        if total_attempts < 3:
            return CognitiveState(
                state="novice", confidence=p,
                reasoning=f"仅尝试 {total_attempts} 次，不足以判断",
                detected_at=time.time(),
            )

        recent_correct = sum(1 for h in history if h["correct"])
        recent_total = len(history)
        recent_acc = recent_correct / max(recent_total, 1)

        # 连续错误计数
        consecutive_wrong = 0
        for h in reversed(history):
            if h["correct"]:
                break
            consecutive_wrong += 1

        if p >= 0.85 and recent_acc >= 0.8:
            return CognitiveState(
                state="confident", confidence=p,
                reasoning=f"掌握度 {p:.2f}，近10题正确率 {recent_acc:.0%}",
                detected_at=time.time(),
            )
        elif p >= 0.6 and consecutive_wrong < 2:
            return CognitiveState(
                state="fluent", confidence=p,
                reasoning=f"掌握度 {p:.2f}，连续错误 {consecutive_wrong} 次",
                detected_at=time.time(),
            )
        elif p < 0.4 and consecutive_wrong >= 2:
            state_name = "frustrated" if consecutive_wrong >= 3 else "confused"
            return CognitiveState(
                state=state_name, confidence=1 - p,
                reasoning=f"掌握度 {p:.2f}，连续错误 {consecutive_wrong} 次，需要调整教学策略",
                detected_at=time.time(),
            )
        else:
            return CognitiveState(
                state="fluent", confidence=p,
                reasoning=f"掌握度 {p:.2f}，近10题正确率 {recent_acc:.0%}",
                detected_at=time.time(),
            )


# ============================================================
# 学生模型
# ============================================================
class StudentModel:
    """
    L4 级学生模型

    每个学生的每个知识点维护独立的 BKT 追踪状态。
    支持持久化到本地 JSON 文件。
    """

    def __init__(self, student_id: str, bkt_params: Optional[Dict[str, Dict]] = None):
        """
        初始化学生模型

        参数:
            student_id: 学生唯一标识
            bkt_params: 可选，为特定知识点设置自定义 BKT 参数
                        格式: {"pythagorean": {"guess": 0.15, "slip": 0.08, "learn": 0.25}}
        """
        self.student_id = student_id
        self._trackers: Dict[str, BKTTracker] = {}
        self._bkt_params_override = bkt_params or {}
        self._cognitive_state: Optional[CognitiveState] = None
        self._created_at = time.time()
        self._load_state()

    def _state_file(self) -> Path:
        p = Path(PROGRESS_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p / f"{self.student_id}.json"

    def _load_state(self):
        """从文件加载学生状态"""
        f = self._state_file()
        if not f.exists():
            return
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for node_id, state_dict in data.get("trackers", {}).items():
                params = BKTNodeParams.from_dict(
                    self._bkt_params_override.get(node_id, {})
                )
                tracker = BKTTracker(params)
                tracker.state.p = state_dict.get("p", params.prior)
                tracker.state.prev_p = state_dict.get("prev_p", params.prior)
                tracker.state.total_correct = state_dict.get("total_correct", 0)
                tracker.state.total_wrong = state_dict.get("total_wrong", 0)
                tracker.state.last_updated = state_dict.get("last_updated", 0.0)
                tracker.state.history = state_dict.get("history", [])
                self._trackers[node_id] = tracker
        except (json.JSONDecodeError, IOError):
            self._trackers = {}

    def _save_state(self):
        """持久化学生状态到文件"""
        data = {
            "student_id": self.student_id,
            "created_at": self._created_at,
            "trackers": {
                nid: s.state.to_dict() for nid, s in self._trackers.items()
            },
        }
        f = self._state_file()
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ----------------------------------------------------------
    # 核心 API
    # ----------------------------------------------------------
    def record_attempt(self, node_id: str, correct: bool,
                       time_spent: float = 0.0,
                       question_type: str = "") -> Dict:
        """
        记录一次答题交互，更新 BKT 状态。

        参数:
            node_id: 知识点 ID
            correct: 是否答对
            time_spent: 答题用时（秒）
            question_type: 题型分类

        返回:
            {node_id, p, p_change, correct, cognitive_state, predicted_accuracy}
        """
        if node_id not in self._trackers:
            params = BKTNodeParams.from_dict(
                self._bkt_params_override.get(node_id, {})
            )
            self._trackers[node_id] = BKTTracker(params)

        tracker = self._trackers[node_id]
        bkt_result = tracker.update(correct)

        # 记录时间（用于学习曲线分析）
        if time_spent > 0:
            tracker.state.history[-1]["time_spent"] = time_spent
            tracker.state.history[-1]["question_type"] = question_type

        # 推断认知状态
        cog = tracker.infer_cognitive_state()
        self._cognitive_state = cog
        bkt_result["cognitive_state"] = cog.to_dict()
        bkt_result["predicted_accuracy"] = round(tracker.predict_next_accuracy(), 4)

        self._save_state()
        return bkt_result

    def get_mastery(self, node_id: str) -> float:
        """获取单个知识点的掌握度 (0-1)"""
        t = self._trackers.get(node_id)
        return t.state.p if t else BKT_DEFAULT_PRIOR

    def get_all_mastery(self) -> Dict[str, float]:
        """获取所有知识点的掌握度"""
        return {nid: t.state.p for nid, t in self._trackers.items()}

    def get_cognitive_state(self) -> Dict:
        """获取当前认知状态"""
        if self._cognitive_state is None:
            return CognitiveState().to_dict()
        return self._cognitive_state.to_dict()

    def get_summary(self) -> Dict:
        """获取学生模型汇总信息"""
        total = len(self._trackers)
        mastered = sum(1 for t in self._trackers.values() if t.state.p >= 0.8)
        learning = sum(1 for t in self._trackers.values()
                       if 0.3 <= t.state.p < 0.8)
        not_started = sum(1 for t in self._trackers.values() if t.state.p < 0.05)

        total_attempts = sum(t.state.total_correct + t.state.total_wrong
                             for t in self._trackers.values())
        total_correct = sum(t.state.total_correct for t in self._trackers.values())

        return {
            "student_id": self.student_id,
            "total_knowledge_nodes": total,
            "mastered_nodes": mastered,
            "learning_nodes": learning,
            "not_started": not_started,
            "overall_mastery": round(
                sum(t.state.p for t in self._trackers.values()) / max(total, 1), 3
            ),
            "total_attempts": total_attempts,
            "overall_accuracy": round(
                total_correct / max(total_attempts, 1), 3
            ),
            "cognitive_state": self.get_cognitive_state(),
            "created_at": self._created_at,
            "last_updated": max(
                (t.state.last_updated for t in self._trackers.values()), default=0
            ),
        }

    def get_node_detail(self, node_id: str) -> Optional[Dict]:
        """获取单个知识点的详细追踪状态"""
        t = self._trackers.get(node_id)
        if not t:
            return None
        return {
            "node_id": node_id,
            **t.state.to_dict(),
            "predicted_accuracy": round(t.predict_next_accuracy(), 4),
            "cognitive_state": t.infer_cognitive_state().to_dict(),
        }

    def reset_node(self, node_id: str):
        """重置单个知识点的追踪状态（教师可操作）"""
        if node_id in self._trackers:
            params = BKTNodeParams.from_dict(
                self._bkt_params_override.get(node_id, {})
            )
            self._trackers[node_id] = BKTTracker(params)
            self._save_state()


# ============================================================
# 全局管理
# ============================================================
_student_cache: Dict[str, StudentModel] = {}


def get_student(student_id: str,
                bkt_params: Optional[Dict[str, Dict]] = None) -> StudentModel:
    """获取或创建学生模型（内存缓存，避免重复加载文件）"""
    if student_id not in _student_cache:
        _student_cache[student_id] = StudentModel(student_id, bkt_params)
    return _student_cache[student_id]


def clear_student_cache(student_id: Optional[str] = None):
    """清除学生缓存（同时删除持久化文件，确保彻底重置）"""
    if student_id:
        _student_cache.pop(student_id, None)
        # 删除对应的持久化文件
        f = Path(PROGRESS_DIR) / f"{student_id}.json"
        if f.exists():
            try:
                f.unlink()
            except OSError:
                pass
    else:
        _student_cache.clear()
        # 删除所有持久化文件
        p = Path(PROGRESS_DIR)
        if p.exists():
            for f in p.glob("*.json"):
                try:
                    f.unlink()
                except OSError:
                    pass
