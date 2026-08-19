# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — 成本追踪与优化（Phase 4）

实现 Route 层成本监控，满足 Roadmap Phase 4 交付物：

  - 单次请求成本记录
  - 每日成本趋势（按天聚合）
  - 各 Agent / 各模型成本占比
  - 成本异常检测（单次超阈值 / 日成本突增）
  - 优化建议（超支 Agent 推荐降级路径）

设计：
  - 内存按天/按 Agent 聚合（轻量，无 DB 依赖）
  - 复用 observability.MODEL_COST_PER_1K 单价表（单一事实源）
  - 线程安全，单例模式
  - 与 AgentTelemetry 协同：telemetry 记录调用细节，CostTracker 做聚合分析
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 确保直接运行脚本时能导入 agent_core 子模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.observability import MODEL_COST_PER_1K, DEFAULT_COST

logger = logging.getLogger("lumilearn.agent.cost")


class CostTracker:
    """
    成本追踪与优化分析。

    用法：
        tracker = get_cost_tracker()
        tracker.record(agent_id="feynman", model="qwen2.5:7b",
                       input_tokens=300, output_tokens=900)
        summary = tracker.get_summary()
        anomalies = tracker.detect_anomalies()
        report = tracker.generate_report()
    """

    def __init__(
        self,
        anomaly_cost_threshold: float = 0.05,     # 单次调用成本异常阈值（元）
        daily_spike_ratio: float = 2.0,           # 日成本突增倍数阈值
        history_days: int = 7,                    # 趋势统计窗口
    ):
        # 使用可重入锁：detect_anomalies 持锁时调用 get_daily_trend 会再次加锁，
        # 普通 Lock 会导致嵌套加锁死锁。
        self._lock = threading.RLock()
        # 原始调用记录（环形，最多 20000 条）
        self._records: List[Dict] = []
        self._max_records = 20000
        # 聚合索引：{date: {agent_id: {model: {"calls", "cost", "tokens"}}}}
        self._daily: Dict[str, Dict[str, Dict[str, Dict]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(
                lambda: {"calls": 0, "cost": 0.0, "tokens": 0})))
        self.anomaly_cost_threshold = anomaly_cost_threshold
        self.daily_spike_ratio = daily_spike_ratio
        self.history_days = history_days

    # ============================================================
    # 记录
    # ============================================================
    def record(
        self,
        agent_id: str = "",
        model: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int = 0,
        success: bool = True,
        date: str = "",
    ) -> Dict:
        """
        记录一次调用成本。

        参数：
            agent_id: Agent 标识
            model: 模型 ID
            input_tokens / output_tokens: token 计数
            latency_ms: 耗时
            success: 是否成功
            date: 日期（默认今天，格式 YYYY-MM-DD）

        返回：
            成本记录（含计算出的 cost）
        """
        cost = self.calc_cost(model, input_tokens, output_tokens)
        date = date or datetime.now().strftime("%Y-%m-%d")
        record = {
            "agent_id": agent_id or "unknown",
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "tokens": input_tokens + output_tokens,
            "cost": cost,
            "latency_ms": latency_ms,
            "success": success,
            "date": date,
            "timestamp": datetime.now().isoformat(),
        }
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]
            cell = self._daily[date][record["agent_id"]][model]
            cell["calls"] += 1
            cell["cost"] += cost
            cell["tokens"] += record["tokens"]
        return record

    def calc_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """按模型单价估算成本（元），与 telemetry 保持同一口径"""
        price = MODEL_COST_PER_1K.get(model, DEFAULT_COST)
        return round((input_tokens + output_tokens) * price / 1000, 6)

    def estimate_request_cost(self, model: str, prompt_tokens: int) -> float:
        """预估一次请求的成本（用于路由决策前的成本预算）"""
        return self.calc_cost(model, prompt_tokens, prompt_tokens)

    # ============================================================
    # 聚合分析
    # ============================================================
    def get_summary(self, date: str = "") -> Dict:
        """
        成本汇总。

        参数：
            date: 指定日期（空=全部历史）

        返回：
            {total_calls, total_cost, total_tokens,
             by_agent: {agent: {calls, cost}}, by_model: {...}}
        """
        with self._lock:
            if date:
                daily = {date: self._daily.get(date, {})}
            else:
                daily = dict(self._daily)

            by_agent: Dict[str, Dict] = {}
            by_model: Dict[str, Dict] = {}
            total_calls = total_cost = total_tokens = 0
            for day, agents in daily.items():
                for agent, models in agents.items():
                    by_agent.setdefault(agent, {"calls": 0, "cost": 0.0})
                    for model, cell in models.items():
                        by_agent[agent]["calls"] += cell["calls"]
                        by_agent[agent]["cost"] += cell["cost"]
                        by_model.setdefault(model, {"calls": 0, "cost": 0.0})
                        by_model[model]["calls"] += cell["calls"]
                        by_model[model]["cost"] += cell["cost"]
                        total_calls += cell["calls"]
                        total_cost += cell["cost"]
                        total_tokens += cell["tokens"]

            return {
                "total_calls": total_calls,
                "total_cost": round(total_cost, 6),
                "total_tokens": total_tokens,
                "avg_cost_per_call": round(total_cost / total_calls, 6) if total_calls else 0.0,
                "by_agent": by_agent,
                "by_model": by_model,
            }

    def get_daily_trend(self, days: int = 7) -> List[Dict]:
        """近 N 天每日成本趋势（含缺失日补零）"""
        days = days or self.history_days
        with self._lock:
            result = []
            today = datetime.now()
            for i in range(days - 1, -1, -1):
                d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                day_total = {"calls": 0, "cost": 0.0, "tokens": 0}
                for agent in self._daily.get(d, {}).values():
                    for cell in agent.values():
                        day_total["calls"] += cell["calls"]
                        day_total["cost"] += cell["cost"]
                        day_total["tokens"] += cell["tokens"]
                result.append({
                    "date": d,
                    "calls": day_total["calls"],
                    "cost": round(day_total["cost"], 6),
                    "tokens": day_total["tokens"],
                })
            return result

    def get_cost_by_agent(self, date: str = "") -> Dict[str, Dict]:
        """各 Agent 成本占比"""
        summary = self.get_summary(date)
        total = summary["total_cost"] or 1.0
        result = {}
        for agent, data in summary["by_agent"].items():
            result[agent] = {
                "calls": data["calls"],
                "cost": round(data["cost"], 6),
                "share": round(data["cost"] / total, 4),
            }
        return result

    # ============================================================
    # 异常检测与优化建议
    # ============================================================
    def detect_anomalies(self, date: str = "") -> List[Dict]:
        """
        成本异常检测：
          - 单次调用成本超阈值
          - 日成本相对前日突增（> daily_spike_ratio 倍）
        """
        anomalies: List[Dict] = []
        with self._lock:
            # 1. 单次调用超阈值
            for r in self._records:
                if r["cost"] > self.anomaly_cost_threshold:
                    anomalies.append({
                        "type": "single_cost_high",
                        "agent_id": r["agent_id"],
                        "model": r["model"],
                        "cost": r["cost"],
                        "date": r["date"],
                        "detail": f"单次调用成本 {r['cost']} 元超过阈值 "
                                  f"{self.anomaly_cost_threshold} 元",
                    })

            # 2. 日成本突增（对比前一日）
            trend = self.get_daily_trend(self.history_days + 1)
            for i in range(1, len(trend)):
                prev = trend[i - 1]["cost"]
                cur = trend[i]["cost"]
                if prev > 0 and cur > prev * self.daily_spike_ratio:
                    anomalies.append({
                        "type": "daily_spike",
                        "date": trend[i]["date"],
                        "cost": cur,
                        "detail": f"{trend[i]['date']} 成本 {cur} 元较前日 {prev} 元"
                                  f" 突增 {round(cur / prev, 1)} 倍",
                    })
        return anomalies[:50]

    def generate_report(self) -> Dict:
        """生成成本优化报告（管理面板展示）"""
        summary = self.get_summary()
        anomalies = self.detect_anomalies()

        # 按成本占比排序的 Agent 排名（用于降级建议）
        by_agent = self.get_cost_by_agent()
        ranking = sorted(by_agent.items(), key=lambda kv: kv[1]["cost"], reverse=True)

        suggestions = []
        for agent, data in ranking[:5]:
            if data["share"] > 0.3 and data["calls"] > 0:
                suggestions.append({
                    "agent_id": agent,
                    "cost": data["cost"],
                    "share": data["share"],
                    "suggestion": (
                        f"Agent「{agent}」成本占比 {round(data['share']*100,1)}%，"
                        f"建议评估其任务是否可降级到低成本模型或走缓存"),
                })

        return {
            "summary": summary,
            "daily_trend": self.get_daily_trend(self.history_days),
            "by_agent": by_agent,
            "anomalies": anomalies,
            "suggestions": suggestions,
            "generated_at": datetime.now().isoformat(),
        }

    def reset(self):
        """重置全部数据（测试用）"""
        with self._lock:
            self._records.clear()
            self._daily.clear()


# ================================================================
# 单例
# ================================================================
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker(**kwargs) -> CostTracker:
    """获取成本追踪单例"""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker(**kwargs)
    return _cost_tracker


def reset_cost_tracker():
    """重置成本追踪（测试用）"""
    global _cost_tracker
    _cost_tracker = None


if __name__ == "__main__":
    tracker = get_cost_tracker()
    print("=== CostTracker 成本追踪测试 ===")

    # 1. 记录几次调用
    tracker.record("feynman", "qwen2.5:7b", 300, 900)
    tracker.record("feynman", "qwen2.5:7b", 200, 800)
    tracker.record("verifier", "qwen2.5:7b", 100, 50)
    tracker.record("coach", "GLM-5", 500, 500, success=False)

    # 2. 汇总
    summary = tracker.get_summary()
    print(f"总调用: {summary['total_calls']} 次 | 总成本: {summary['total_cost']} 元")
    print(f"各Agent: {tracker.get_cost_by_agent()}")

    # 3. 趋势
    print(f"近3天趋势: {tracker.get_daily_trend(3)}")

    # 4. 异常检测
    print(f"异常: {tracker.detect_anomalies()}")

    # 5. 优化报告
    report = tracker.generate_report()
    print(f"优化建议: {report['suggestions']}")
