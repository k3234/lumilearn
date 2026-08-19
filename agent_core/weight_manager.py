# -*- coding: utf-8 -*-
"""
Agent 权重管理器

负责 Agent 动态权重的计算与维护：
  - 基础权重（管理员配置）
  - 动态权重 = base_weight × success_rate × latency_factor
  - 调用限制（每分钟最大调用次数）
  - 权重实时更新与批量计算
"""

from __future__ import annotations

import math
import threading
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("lumilearn.agent.weight")


class WeightManager:
    """Agent 权重管理器"""

    def __init__(self):
        self._lock = threading.Lock()
        self._weight_cache: Dict[str, Dict] = {}
        self._cache_updated_at: Dict[str, float] = {}
        self._cache_ttl = 30.0  # 缓存 30 秒

    def get_weight(self, agent_id: str) -> float:
        """获取 Agent 当前动态权重"""
        from framework.database import db
        with self._lock:
            now = __import__("time").time()
            cached = self._weight_cache.get(agent_id)
            if cached and (now - self._cache_updated_at.get(agent_id, 0)) < self._cache_ttl:
                return cached.get("dynamic_weight", 1.0)

            row = db.get_agent_weight(agent_id)
            if not row:
                return 1.0

            weight = row.get("dynamic_weight", 1.0)
            self._weight_cache[agent_id] = row
            self._cache_updated_at[agent_id] = now
            return weight

    def get_weights(self) -> List[Dict]:
        """获取所有 Agent 权重信息"""
        from framework.database import db
        return db.get_all_agent_weights()

    def calculate_dynamic_weight(
        self,
        agent_id: str,
        base_weight: float,
        call_count: int,
        success_count: int,
        fail_count: int,
        avg_latency_ms: float,
    ) -> float:
        """
        计算动态权重

        公式：
          dynamic_weight = base_weight × success_rate × latency_factor

        其中：
          success_rate = success_count / (success_count + fail_count)
                       若无调用记录则取 1.0
          latency_factor = 1.0 / (1.0 + log1p(avg_latency_ms / 1000))
                       延迟越短，因子越接近 1.0
        """
        total_calls = success_count + fail_count
        if total_calls == 0:
            success_rate = 1.0
        else:
            success_rate = success_count / total_calls

        # 延迟因子：延迟越高，权重越低（下限 0.1）
        latency_factor = 1.0 / (1.0 + math.log1p(avg_latency_ms / 1000.0))
        latency_factor = max(0.1, min(1.0, latency_factor))

        dynamic_weight = base_weight * success_rate * latency_factor
        return round(dynamic_weight, 4)

    def update_weight(
        self,
        agent_id: str,
        latency_ms: int = 0,
        success: bool = True,
    ) -> Dict:
        """
        更新单个 Agent 的权重统计

        参数：
            agent_id: Agent 标识
            latency_ms: 本次调用延迟（毫秒）
            success: 是否成功
        """
        from framework.database import db

        with self._lock:
            row = db.get_agent_weight(agent_id)
            if not row:
                # 首次调用，创建默认配置
                db.upsert_agent_weight(agent_id, base_weight=1.0)
                row = db.get_agent_weight(agent_id)

            call_count = row["call_count"] + 1
            success_count = row["success_count"] + (1 if success else 0)
            fail_count = row["fail_count"] + (1 if not success else 0)
            avg_latency = row["avg_latency_ms"]
            if call_count == 1:
                avg_latency = float(latency_ms)
            else:
                # 指数移动平均
                alpha = 0.1
                avg_latency = avg_latency * (1 - alpha) + latency_ms * alpha

            base_weight = row["base_weight"]
            dynamic_weight = self.calculate_dynamic_weight(
                agent_id=agent_id,
                base_weight=base_weight,
                call_count=call_count,
                success_count=success_count,
                fail_count=fail_count,
                avg_latency_ms=avg_latency,
            )

            db.update_agent_weight_stats(
                agent_id=agent_id,
                call_count=call_count,
                success_count=success_count,
                fail_count=fail_count,
                avg_latency_ms=round(avg_latency, 1),
                dynamic_weight=dynamic_weight,
            )

            # 清除缓存
            self._weight_cache.pop(agent_id, None)

            return {
                "agent_id": agent_id,
                "call_count": call_count,
                "success_count": success_count,
                "fail_count": fail_count,
                "avg_latency_ms": round(avg_latency, 1),
                "dynamic_weight": dynamic_weight,
            }

    def batch_update_weights(self) -> List[Dict]:
        """批量重新计算所有 Agent 的动态权重"""
        from framework.database import db
        results = []
        for row in db.get_all_agent_weights():
            dynamic_weight = self.calculate_dynamic_weight(
                agent_id=row["agent_id"],
                base_weight=row["base_weight"],
                call_count=row["call_count"],
                success_count=row["success_count"],
                fail_count=row["fail_count"],
                avg_latency_ms=row["avg_latency_ms"],
            )
            db.update_agent_weight_stats(
                agent_id=row["agent_id"],
                call_count=row["call_count"],
                success_count=row["success_count"],
                fail_count=row["fail_count"],
                avg_latency_ms=row["avg_latency_ms"],
                dynamic_weight=dynamic_weight,
            )
            results.append({
                "agent_id": row["agent_id"],
                "dynamic_weight": dynamic_weight,
            })
            self._weight_cache.pop(row["agent_id"], None)
        return results

    def set_base_weight(self, agent_id: str, base_weight: float) -> bool:
        """设置 Agent 基础权重（管理员操作）"""
        from framework.database import db
        db.upsert_agent_weight(agent_id, base_weight=base_weight)
        self._weight_cache.pop(agent_id, None)
        return True

    def get_priority_agents(self, subject: str = "", min_weight: float = 0.0) -> List[Dict]:
        """
        获取按权重排序的 Agent 列表

        参数：
            subject: 按学科筛选（可选）
            min_weight: 最小动态权重阈值

        返回：
            按 dynamic_weight 降序排列的 Agent 列表
        """
        weights = self.get_weights()
        if min_weight > 0:
            weights = [w for w in weights if w.get("dynamic_weight", 0) >= min_weight]
        weights.sort(key=lambda x: x.get("dynamic_weight", 0), reverse=True)
        return weights


# 单例
_weight_manager: Optional[WeightManager] = None


def get_weight_manager() -> WeightManager:
    global _weight_manager
    if _weight_manager is None:
        _weight_manager = WeightManager()
    return _weight_manager
