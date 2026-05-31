#!/usr/bin/env python3
"""
LumiLearn 学习数据分析与错题追踪模块
- 错题记录与统计
- 个性化难度自适应
- 弱项检测与复习推荐
"""
import json
import os
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class MistakeRecord:
    question: str
    user_answer: str
    correct_answer: str = ""
    topic: str = ""
    subject: str = ""
    hints_used: int = 0
    attempts: int = 1
    timestamp: float = field(default_factory=time.time)


class LearningTracker:
    """
    学习追踪器：记录错题、分析弱项、自适应难度
    用法：
        tracker = LearningTracker()
        tracker.record_attempt("3×7=?", "18", "21", topic="乘法", subject="数学")
        weak = tracker.get_weak_topics()
        next_diff = tracker.get_next_difficulty("乘法")
    """

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "learning_records.json"
            )
        self.storage_path = storage_path
        self.records: List[MistakeRecord] = []
        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.records = [
                    MistakeRecord(**r) for r in data.get("records", [])
                ]

    def save(self):
        data = {
            "records": [
                {
                    "question": r.question,
                    "user_answer": r.user_answer,
                    "correct_answer": r.correct_answer,
                    "topic": r.topic,
                    "subject": r.subject,
                    "hints_used": r.hints_used,
                    "attempts": r.attempts,
                    "timestamp": r.timestamp,
                }
                for r in self.records
            ],
            "updated_at": time.time(),
        }
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def record_attempt(
        self,
        question: str,
        user_answer: str,
        correct_answer: str = "",
        topic: str = "",
        subject: str = "",
        hints_used: int = 0,
    ):
        """记录一次答题尝试"""
        record = MistakeRecord(
            question=question,
            user_answer=user_answer.strip(),
            correct_answer=str(correct_answer).strip(),
            topic=topic,
            subject=subject,
            hints_used=hints_used,
        )

        user_clean = record.user_answer.lower().replace(" ", "")
        correct_clean = record.correct_answer.lower().replace(" ", "")

        if user_clean == correct_clean:
            self.records.append(record)
            return True, "🎉 回答正确！你是怎么想到的？"

        self.records.append(record)
        hint = self._generate_hint(record)
        return False, hint

    def _generate_hint(self, record: MistakeRecord) -> str:
        """根据错题生成引导提示"""
        topic_lower = record.topic.lower()

        if "面积" in topic_lower:
            return "🤔 再想想：面积公式是底×高÷2，你有没有用到这个公式？"
        elif any(k in topic_lower for k in ["乘法", "乘", "×"]):
            return "💡 提示：可以用乘法口诀或者分解计算，比如7×8可以拆成7×4+7×4"
        elif any(k in topic_lower for k in ["除法", "除", "÷"]):
            return "🔍 检查一下：被除数÷除数=商，你确定没有弄混位置吗？"
        elif "方程" in topic_lower:
            return "⚖️ 回忆一下：移项的时候要变号哦！把含x的移到左边，常数移到右边"
        elif "分数" in topic_lower:
            return "🍕 分数计算的关键：分母相同才能加减，不同的话要先通分！"
        elif any(k in topic_lower for k in ["加法", "减法"]):
            return "🧮 检查一下进位/借位有没有漏掉？可以再算一遍"
        return "🤔 差一点！再仔细想想推理过程，看看哪一步可能出了错"

    def get_weak_topics(self, min_errors: int = 2) -> List[Dict]:
        """获取薄弱知识点（出错次数>=min_errors）"""
        topic_stats: Dict[str, Dict] = {}
        for r in self.records:
            if r.topic not in topic_stats:
                topic_stats[r.topic] = {"total": 0, "wrong": 0, "correct": 0}
            topic_stats[r.topic]["total"] += 1
            if r.user_answer.strip().lower().replace(" ", "") != r.correct_answer.strip().lower().replace(" ", ""):
                topic_stats[r.topic]["wrong"] += 1
            else:
                topic_stats[r.topic]["correct"] += 1

        weak = []
        for topic, stats in topic_stats.items():
            if stats["wrong"] >= min_errors:
                rate = stats["wrong"] / max(stats["total"], 1)
                weak.append({
                    "topic": topic,
                    "wrong": stats["wrong"],
                    "correct": stats["correct"],
                    "total": stats["total"],
                    "error_rate": rate,
                })
        weak.sort(key=lambda x: x["error_rate"], reverse=True)
        return weak

    def get_next_difficulty(self, topic: str) -> int:
        """根据该主题的答题情况，返回推荐难度级别 (1=基础, 2=进阶, 3=挑战)"""
        correct = sum(1 for r in self.records
                      if r.topic == topic
                      and r.user_answer.strip().lower().replace(" ", "")
                      == r.correct_answer.strip().lower().replace(" ", ""))

        wrong = sum(1 for r in self.records
                    if r.topic == topic
                    and r.user_answer.strip().lower().replace(" ", "")
                    != r.correct_answer.strip().lower().replace(" ", ""))

        total = correct + wrong
        if total == 0:
            return 2

        accuracy = correct / total

        if accuracy >= 0.8 and total >= 3:
            return 3
        elif accuracy >= 0.6:
            return 2
        else:
            return 1

    def suggest_review(self) -> List[str]:
        """生成复习建议"""
        weak = self.get_weak_topics(min_errors=1)
        if not weak:
            return ["目前没有明显的薄弱点，继续保持！💪"]

        suggestions = []
        for w in weak[:3]:
            if w["error_rate"] >= 0.5:
                suggestions.append(
                    f'🔴 {w["topic"]}：{w["wrong"]}次错误/{w["total"]}次答题 '
                    f'(错误率{int(w["error_rate"]*100)}%)，建议重点复习基础概念'
                )
            elif w["error_rate"] >= 0.3:
                suggestions.append(
                    f'🟡 {w["topic"]}：{w["wrong"]}次错误/{w["total"]}次答题 '
                    f'(错误率{int(w["error_rate"]*100)}%)，建议多做练习题巩固'
                )
            else:
                suggestions.append(
                    f'🟢 {w["topic"]}：{w["wrong"]}次错误/{w["total"]}次答题 '
                    f'(错误率{int(w["error_rate"]*100)}%)，再练几道就能完全掌握了'
                )
        return suggestions

    def get_stats(self) -> Dict:
        """获取全局学习统计"""
        total = len(self.records)
        if total == 0:
            return {"total": 0, "correct": 0, "wrong": 0, "accuracy": 0}

        correct = sum(
            1 for r in self.records
            if r.user_answer.strip().lower().replace(" ", "")
            == r.correct_answer.strip().lower().replace(" ", "")
        )
        return {
            "total": total,
            "correct": correct,
            "wrong": total - correct,
            "accuracy": round(correct / total * 100, 1),
            "total_hints_used": sum(r.hints_used for r in self.records),
        }


if __name__ == "__main__":
    print("=" * 50)
    print("LumiLearn 学习追踪器测试")
    print("=" * 50)

    tracker = LearningTracker()

    tests = [
        ("3×7=?", "18", "21", "乘法", "数学"),
        ("三角形面积=底6高4", "12", "12", "三角形面积", "数学"),
        ("5×8=?", "35", "40", "乘法", "数学"),
        ("x+5=12, x=?", "8", "7", "方程", "数学"),
        ("1/4+1/4=?", "1/2", "1/2", "分数", "数学"),
        ("6×9=?", "52", "54", "乘法", "数学"),
        ("x-3=10, x=?", "13", "13", "方程", "数学"),
    ]

    for q, ans, correct, topic, subject in tests:
        ok, msg = tracker.record_attempt(q, ans, correct, topic, subject)
        print(f"{'✅' if ok else '❌'} {q} → {msg[:40]}")

    tracker.save()

    print("\n📊 学习统计:", tracker.get_stats())
    print("\n🔍 薄弱点:", tracker.get_weak_topics())
    print("\n📝 复习建议:", tracker.suggest_review())
    print("\n🎯 乘法难度:", tracker.get_next_difficulty("乘法"))
    print("🎯 方程难度:", tracker.get_next_difficulty("方程"))