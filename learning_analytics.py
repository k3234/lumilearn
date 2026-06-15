#!/usr/bin/env python3
"""
LumiLearn L3增强版：学习数据分析与状态追踪模块
- 错题记录与统计
- 个性化难度自适应
- 弱项检测与复习推荐
- 【新增】学习行为时序记录
- 【新增】专注度估算
- 【新增】疲劳检测
- 【新增】最佳学习时段识别
"""
import json
import os
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import defaultdict


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
    # 【新增】答题时长（秒）
    time_spent: float = 0.0
    # 【新增】是否放弃标记
    gave_up: bool = False


@dataclass
class LearningSession:
    """学习会话记录"""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    subject: str = ""
    questions_answered: int = 0
    correct_count: int = 0
    # 答题时序数据
    response_times: List[float] = field(default_factory=list)
    # 交互频率
    interaction_timestamps: List[float] = field(default_factory=list)


@dataclass
class DailyStats:
    """每日学习统计"""
    date: str
    total_time: float = 0.0
    questions_answered: int = 0
    correct_count: int = 0
    topics_studied: List[str] = field(default_factory=list)
    max_focus_score: float = 0.0


class LearningTracker:
    """
    学习追踪器（L3增强版）：
    - 记录错题、分析弱项、自适应难度
    - 【新增】学习会话管理
    - 【新增】专注度估算
    - 【新增】疲劳检测
    - 【新增】最佳学习时段识别

    用法：
        tracker = LearningTracker()
        session_id = tracker.start_session("数学")
        tracker.record_attempt("3×7=?", "18", "21", topic="乘法", time_spent=15.0)
        focus = tracker.estimate_focus(session_id)
        is_fatigued = tracker.detect_fatigue(session_id)
        best_time = tracker.get_best_learning_time()
    """

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "learning_records.json"
            )
        self.storage_path = storage_path
        self.records: List[MistakeRecord] = []
        self.sessions: Dict[str, LearningSession] = {}
        self.daily_stats: Dict[str, DailyStats] = {}
        self.current_session: Optional[str] = None
        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.records = [
                    MistakeRecord(**r) for r in data.get("records", [])
                ]
                # 加载会话
                self.sessions = {
                    sid: LearningSession(**s)
                    for sid, s in data.get("sessions", {}).items()
                }
                # 加载每日统计
                self.daily_stats = {
                    date: DailyStats(**ds)
                    for date, ds in data.get("daily_stats", {}).items()
                }
                self.current_session = data.get("current_session")

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
                    "time_spent": r.time_spent,
                    "gave_up": r.gave_up,
                }
                for r in self.records
            ],
            "sessions": {
                sid: {
                    "session_id": s.session_id,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "subject": s.subject,
                    "questions_answered": s.questions_answered,
                    "correct_count": s.correct_count,
                    "response_times": s.response_times,
                    "interaction_timestamps": s.interaction_timestamps,
                }
                for sid, s in self.sessions.items()
            },
            "daily_stats": {
                date: {
                    "date": ds.date,
                    "total_time": ds.total_time,
                    "questions_answered": ds.questions_answered,
                    "correct_count": ds.correct_count,
                    "topics_studied": ds.topics_studied,
                    "max_focus_score": ds.max_focus_score,
                }
                for date, ds in self.daily_stats.items()
            },
            "current_session": self.current_session,
            "updated_at": time.time(),
        }
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ========== 【新增】学习会话管理 ==========

    def start_session(self, subject: str = "") -> str:
        """开始一个新的学习会话"""
        session_id = f"session_{int(time.time())}"
        session = LearningSession(
            session_id=session_id,
            start_time=time.time(),
            subject=subject,
        )
        self.sessions[session_id] = session
        self.current_session = session_id
        self.save()
        return session_id

    def end_session(self, session_id: Optional[str] = None) -> Optional[Dict]:
        """结束当前学习会话"""
        sid = session_id or self.current_session
        if not sid or sid not in self.sessions:
            return None

        session = self.sessions[sid]
        session.end_time = time.time()

        # 更新每日统计
        date_str = time.strftime("%Y-%m-%d", time.localtime(session.start_time))
        if date_str not in self.daily_stats:
            self.daily_stats[date_str] = DailyStats(date=date_str)
        daily = self.daily_stats[date_str]

        session_duration = (session.end_time - session.start_time) if session.end_time else 0
        daily.total_time += session_duration
        daily.questions_answered += session.questions_answered
        daily.correct_count += session.correct_count

        # 计算本次会话的专注度并更新每日最大值
        focus = self.estimate_focus(sid)
        if focus > daily.max_focus_score:
            daily.max_focus_score = focus

        self.save()
        self.current_session = None

        return {
            "session_id": sid,
            "duration": round(session_duration / 60, 1),  # 分钟
            "questions": session.questions_answered,
            "correct": session.correct_count,
            "focus_score": round(focus, 2),
        }

    def get_active_session(self) -> Optional[LearningSession]:
        """获取当前活跃的学习会话"""
        if self.current_session and self.current_session in self.sessions:
            return self.sessions[self.current_session]
        return None

    # ========== 【新增】专注度估算 ==========

    def estimate_focus(self, session_id: Optional[str] = None) -> float:
        """
        估算专注度分数 (0-1)
        基于：答题速度稳定性、正确率趋势、交互频率
        """
        sid = session_id or self.current_session
        if not sid or sid not in self.sessions:
            return 0.0

        session = self.sessions[sid]
        if len(session.response_times) < 3:
            return 0.5  # 数据不足，返回中等

        scores = []

        # 1. 答题速度稳定性：波动越小越专注
        times = session.response_times[-10:]  # 最近10题
        if len(times) >= 3:
            avg_time = sum(times) / len(times)
            variance = sum((t - avg_time) ** 2 for t in times) / len(times)
            # 归一化：方差越小分数越高
            stability = max(0, 1 - min(1, variance / (avg_time ** 2 + 1)))
            scores.append(stability)

        # 2. 正确率趋势：稳定或上升说明专注
        if session.questions_answered >= 5:
            recent = self.records[-5:]
            recent_correct = sum(
                1 for r in recent
                if r.user_answer.strip().lower().replace(" ", "") == r.correct_answer.strip().lower().replace(" ", "")
            )
            accuracy_trend = recent_correct / 5
            scores.append(accuracy_trend)

        # 3. 交互频率：连续互动说明专注
        if len(session.interaction_timestamps) >= 3:
            recent_interactions = session.interaction_timestamps[-5:]
            intervals = [recent_interactions[i] - recent_interactions[i-1]
                        for i in range(1, len(recent_interactions))]
            avg_interval = sum(intervals) / len(intervals) if intervals else 60
            # 平均间隔小于5分钟得高分
            interaction_score = max(0, 1 - min(1, avg_interval / 300))
            scores.append(interaction_score)

        if not scores:
            return 0.5

        return sum(scores) / len(scores)

    # ========== 【新增】疲劳检测 ==========

    def detect_fatigue(self, session_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        检测是否疲劳
        返回：(是否疲劳, 建议)
        """
        sid = session_id or self.current_session
        if not sid or sid not in self.sessions:
            return False, ""

        session = self.sessions[sid]
        now = time.time()
        session_duration = (now - session.start_time) / 60  # 分钟

        # 规则1：连续学习超过45分钟
        if session_duration > 45:
            return True, "⏰ 你已经学习了45分钟以上，建议休息5-10分钟！"

        # 规则2：专注度持续下降
        if len(session.response_times) >= 5:
            # 比较前半段和后半段的答题时间
            mid = len(session.response_times) // 2
            first_half_avg = sum(session.response_times[:mid]) / mid
            second_half_avg = sum(session.response_times[mid:]) / (len(session.response_times) - mid)
            # 答题变慢超过30%可能是疲劳
            if second_half_avg > first_half_avg * 1.3:
                return True, "🐌 感觉你的答题速度变慢了，稍微休息一下吧！"

        # 规则3：近期错误率上升
        if len(self.records) >= 6:
            first_half = self.records[-6:-3]
            second_half = self.records[-3:]

            def count_correct(records):
                return sum(
                    1 for r in records
                    if r.user_answer.strip().lower().replace(" ", "") == r.correct_answer.strip().lower().replace(" ", "")
                )

            first_correct = count_correct(first_half)
            second_correct = count_correct(second_half)

            if second_correct < first_correct - 1:
                return True, "📉 近期正确率有所下降，建议休息调整状态！"

        return False, "✨ 状态不错，继续保持！"

    # ========== 【新增】最佳学习时段识别 ==========

    def get_best_learning_time(self) -> List[Dict]:
        """
        分析历史数据，找出最佳学习时段
        返回按效果排序的时段列表
        """
        hour_stats = defaultdict(lambda: {"count": 0, "total_focus": 0.0, "total_accuracy": 0.0})

        for record in self.records:
            hour = time.localtime(record.timestamp).tm_hour
            is_correct = (
                record.user_answer.strip().lower().replace(" ", "")
                == record.correct_answer.strip().lower().replace(" ", "")
            )
            hour_stats[hour]["count"] += 1
            hour_stats[hour]["total_accuracy"] += 1 if is_correct else 0

        # 结合每日统计中的专注度
        for daily in self.daily_stats.values():
            # 简化：假设最高专注度出现在当天学习的中间时段
            # 实际应用可以更精细
            pass

        results = []
        for hour in range(24):
            stats = hour_stats[hour]
            if stats["count"] >= 3:  # 至少有3次记录
                accuracy = stats["total_accuracy"] / stats["count"]
                results.append({
                    "hour": hour,
                    "display": f"{hour:02d}:00-{hour+1:02d}:00",
                    "accuracy": round(accuracy * 100, 1),
                    "sample_count": stats["count"],
                })

        # 按正确率排序
        results.sort(key=lambda x: x["accuracy"], reverse=True)
        return results[:3]  # 返回最好的3个时段

    # ========== 【增强】答题记录 ==========

    def record_attempt(
        self,
        question: str,
        user_answer: str,
        correct_answer: str = "",
        topic: str = "",
        subject: str = "",
        hints_used: int = 0,
        time_spent: float = 0.0,
        gave_up: bool = False,
    ):
        """
        记录一次答题尝试（增强版）
        - 新增：答题时长记录
        - 新增：自动活跃会话更新
        - 新增：疲劳检测提醒
        """
        record = MistakeRecord(
            question=question,
            user_answer=user_answer.strip(),
            correct_answer=str(correct_answer).strip(),
            topic=topic,
            subject=subject,
            hints_used=hints_used,
            time_spent=time_spent,
            gave_up=gave_up,
        )

        # 更新当前会话
        session = self.get_active_session()
        if session:
            session.interaction_timestamps.append(time.time())
            if time_spent > 0:
                session.response_times.append(time_spent)
            session.questions_answered += 1

        user_clean = record.user_answer.lower().replace(" ", "")
        correct_clean = record.correct_answer.lower().replace(" ", "")

        is_correct = user_clean == correct_clean
        if is_correct and session:
            session.correct_count += 1

        self.records.append(record)

        # 检查疲劳状态
        fatigue, fatigue_msg = self.detect_fatigue()

        if is_correct:
            success_msg = "🎉 回答正确！你是怎么想到的？"
            if fatigue:
                return True, f"{success_msg}\n\n{fatigue_msg}"
            return True, success_msg

        hint = self._generate_hint(record)
        if fatigue:
            return False, f"{hint}\n\n{fatigue_msg}"
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
    print("LumiLearn L3增强版 - 学习追踪器测试")
    print("=" * 50)

    tracker = LearningTracker()

    # ========== 测试会话管理 ==========
    print("\n📚 【测试1】开始学习会话")
    session_id = tracker.start_session("数学")
    print(f"   会话ID: {session_id}")

    # ========== 模拟答题记录 ==========
    print("\n✍️  【测试2】记录答题（包含时长）")
    tests = [
        ("3×7=?", "18", "21", "乘法", "数学", 12.5),
        ("三角形面积=底6高4", "12", "12", "三角形面积", "数学", 8.2),
        ("5×8=?", "35", "40", "乘法", "数学", 15.0),
        ("x+5=12, x=?", "8", "7", "方程", "数学", 20.1),
        ("1/4+1/4=?", "1/2", "1/2", "分数", "数学", 11.3),
        ("6×9=?", "52", "54", "乘法", "数学", 18.5),
        ("x-3=10, x=?", "13", "13", "方程", "数学", 9.8),
    ]

    for q, ans, correct, topic, subject, ts in tests:
        ok, msg = tracker.record_attempt(q, ans, correct, topic, subject, time_spent=ts)
        print(f"   {'✅' if ok else '❌'} {q}")
        if len(msg) > 50:
            print(f"      → {msg[:50]}...")
        else:
            print(f"      → {msg}")

    tracker.save()

    # ========== 测试专注度估算 ==========
    print("\n🎯 【测试3】专注度估算")
    focus = tracker.estimate_focus()
    print(f"   当前专注度: {focus:.2%}")

    # ========== 测试疲劳检测 ==========
    print("\n😴 【测试4】疲劳检测")
    is_fatigued, fatigue_msg = tracker.detect_fatigue()
    print(f"   是否疲劳: {'是' if is_fatigued else '否'}")
    print(f"   建议: {fatigue_msg}")

    # ========== 测试结束会话 ==========
    print("\n🔚 【测试5】结束学习会话")
    result = tracker.end_session()
    if result:
        print(f"   会话时长: {result['duration']}分钟")
        print(f"   答题数量: {result['questions']}")
        print(f"   正确数: {result['correct']}")
        print(f"   专注度得分: {result['focus_score']:.2%}")

    # ========== 原有功能测试 ==========
    print("\n📊 【测试6】基础学习统计")
    print("   ", tracker.get_stats())

    print("\n🔍 【测试7】薄弱点分析")
    print("   ", tracker.get_weak_topics())

    print("\n📝 【测试8】复习建议")
    for suggestion in tracker.suggest_review():
        print(f"   - {suggestion}")

    print("\n🎯 【测试9】难度推荐")
    print(f"   乘法难度: {tracker.get_next_difficulty('乘法')}")
    print(f"   方程难度: {tracker.get_next_difficulty('方程')}")

    # ========== 测试最佳时段（需要更多数据） ==========
    print("\n⏰ 【测试10】最佳学习时段")
    best_times = tracker.get_best_learning_time()
    if best_times:
        for i, t in enumerate(best_times, 1):
            print(f"   {i}. {t['display']} - 正确率{t['accuracy']}% ({t['sample_count']}次)")
    else:
        print("   数据不足，继续学习后可以分析最佳时段~")

    print("\n" + "=" * 50)
    print("✨ L3增强版测试完成！")
    print("=" * 50)