# -*- coding: utf-8 -*-
"""
Agent 跨调用管理器

实现 Agent 之间的互相调用：
  - 先查 KnowledgeCache（命中则直接返回）
  - 未命中则调用目标 Agent
  - 结果写入 KnowledgeCache 供后续复用
  - 记录调用链和权重使用
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Dict, List, Optional

logger = logging.getLogger("lumilearn.agent.cross_call")


class CrossCaller:
    """Agent 跨调用管理器"""

    def __init__(self):
        self._call_log: List[Dict] = []
        self._max_log_size = 1000

    def call_agent(
        self,
        target_agent_id: str,
        payload: Dict,
        caller_agent_id: str = "unknown",
        call_chain: List[str] = None,
    ) -> Dict:
        """
        调用指定 Agent（带跨调用追踪）

        参数：
            target_agent_id: 目标 Agent ID
            payload: 调用参数
            caller_agent_id: 调用方 Agent ID
            call_chain: 当前调用链（用于追踪）

        返回：
            Agent 执行结果
        """
        from framework.database import db
        from framework.admin.agents import get_agent_registry

        call_id = f"call_{uuid.uuid4().hex[:8]}"
        topic = payload.get("topic", "")
        subject = payload.get("subject", "")
        t0 = time.time()
        chain = list(call_chain or []) + [caller_agent_id]

        # 1. 先查 KnowledgeCache
        from agent_core.knowledge_cache import get_knowledge_cache
        kc = get_knowledge_cache()
        cached = kc.query(topic=topic, subject=subject, min_quality=60.0, limit=1)
        if cached:
            logger.info(f"[CrossCaller] 命中缓存: {call_id} | {topic} | agent={target_agent_id}")
            result = {
                "success": True,
                "agent_id": target_agent_id,
                "source": "cache_hit",
                "cached_result": cached[0],
                "topic": topic,
            }
            latency_ms = int((time.time() - t0) * 1000)
            db.record_agent_call(
                call_id=call_id,
                caller_agent=caller_agent_id,
                target_agent=target_agent_id,
                topic=topic,
                subject=subject,
                call_type="cross_call",
                payload=payload,
                result=result,
                latency_ms=latency_ms,
                success=True,
                call_chain=chain,
            )
            # 更新权重
            from agent_core.weight_manager import get_weight_manager
            wm = get_weight_manager()
            wm.update_weight(target_agent_id, latency_ms=latency_ms, success=True)
            return result

        # 2. 未命中缓存，调用 Agent
        try:
            registry = get_agent_registry()
            result = registry.run_agent(target_agent_id, payload)
            latency_ms = int((time.time() - t0) * 1000)
            success = result.get("success", False)

            # 3. 写入 KnowledgeCache（仅对成功调用）
            if success and topic:
                self._save_to_knowledge(topic, subject, result, target_agent_id, call_id)

            # 4. 记录调用日志
            db.record_agent_call(
                call_id=call_id,
                caller_agent=caller_agent_id,
                target_agent=target_agent_id,
                topic=topic,
                subject=subject,
                call_type="cross_call",
                payload=payload,
                result={"success": success, "topic": topic},
                latency_ms=latency_ms,
                success=success,
                call_chain=chain,
            )

            # 5. 更新权重
            from agent_core.weight_manager import get_weight_manager
            wm = get_weight_manager()
            wm.update_weight(target_agent_id, latency_ms=latency_ms, success=success)

            # 6. 在结果中标注来源
            result["cross_call_id"] = call_id
            result["call_chain"] = chain
            result["cached"] = False
            return result

        except Exception as e:
            latency_ms = int((time.time() - t0) * 1000)
            logger.error(f"[CrossCaller] Agent {target_agent_id} 调用失败: {e}")
            db.record_agent_call(
                call_id=call_id,
                caller_agent=caller_agent_id,
                target_agent=target_agent_id,
                topic=topic,
                subject=subject,
                call_type="cross_call",
                payload=payload,
                result={"error": str(e)},
                latency_ms=latency_ms,
                success=False,
                call_chain=chain,
            )
            from agent_core.weight_manager import get_weight_manager
            wm = get_weight_manager()
            wm.update_weight(target_agent_id, latency_ms=latency_ms, success=False)
            return {
                "success": False,
                "agent_id": target_agent_id,
                "error": str(e),
                "call_id": call_id,
            }

    def _save_to_knowledge(
        self,
        topic: str,
        subject: str,
        result: Dict,
        source_agent: str,
        source_call_id: int,
    ):
        """将 Agent 结果保存到知识库"""
        from agent_core.knowledge_cache import get_knowledge_cache

        kc = get_knowledge_cache()

        # 判断结果类型
        if "steps" in result and isinstance(result["steps"], list):
            knowledge_type = "explanation"
            content = "\n\n".join(
                f"### 步骤{step.get('order', i+1)}: {step.get('step_name', '')}\n{step.get('content', '')}"
                for i, step in enumerate(result["steps"])
            )
            summary = content[:200]
            quality_score = result.get("score", 70.0)
        elif "reply" in result:
            knowledge_type = "concept"
            content = result.get("reply", "")
            summary = content[:200]
            quality_score = 60.0
        elif "content" in result:
            knowledge_type = "explanation"
            content = result["content"]
            summary = content[:200]
            quality_score = result.get("quality_score", 65.0)
        elif "recommendation" in result:
            knowledge_type = "pattern"
            content = str(result.get("recommendation", ""))
            summary = content[:200]
            quality_score = 50.0
        else:
            # 通用兜底
            knowledge_type = "explanation"
            content = str(result)[:2000]
            summary = content[:200]
            quality_score = 55.0

        kc.save(
            topic=topic,
            knowledge_type=knowledge_type,
            content=content,
            source_agent=source_agent,
            subject=subject,
            summary=summary,
            quality_score=quality_score,
            # call_id 为文本标识，非 agent_call_log.id（INTEGER）；
            # 仅当外部传入整数 ID 时才关联，否则置 None 以通过 FK 约束
            source_call_id=source_call_id if isinstance(source_call_id, int) else None,
        )

    def get_context_for_agent(
        self,
        topic: str,
        subject: str = "",
        caller_agent: str = "",
    ) -> str:
        """
        为 Agent 生成上下文（从知识库中检索相关积累知识）

        参数：
            topic: 学习主题
            subject: 学科
            caller_agent: 调用方 Agent

        返回：
            上下文文本（可注入到 prompt）
        """
        from agent_core.knowledge_cache import get_knowledge_cache
        kc = get_knowledge_cache()
        context = kc.get_context(topic=topic, subject=subject, max_tokens=800)
        if context:
            return f"【已有知识积累】\n{context}\n\n请基于以上积累知识进行回答。\n"
        return ""

    def get_call_history(self, agent_id: str = None, limit: int = 20) -> List[Dict]:
        """获取 Agent 调用历史"""
        from framework.database import db
        return db.get_agent_call_log(agent_id=agent_id, limit=limit)

    def get_call_stats(self) -> Dict:
        """获取跨调用统计"""
        from framework.database import db
        logs = db.get_agent_call_log(limit=1000)
        total = len(logs)
        cross_calls = sum(1 for l in logs if l.get("call_type") == "cross_call")
        cache_hits = 0
        for l in logs:
            r = l.get("result")
            if isinstance(r, str):
                try:
                    import json
                    r = json.loads(r)
                except Exception:
                    r = {}
            if r.get("source") == "cache_hit":
                cache_hits += 1
        errors = sum(1 for l in logs if not l.get("success", True))

        # 按目标 Agent 统计
        by_target = {}
        for l in logs:
            tid = l.get("target_agent", "standalone")
            if not tid:
                tid = "standalone"
            if tid not in by_target:
                by_target[tid] = {"total": 0, "success": 0, "errors": 0}
            by_target[tid]["total"] += 1
            if l.get("success", True):
                by_target[tid]["success"] += 1
            else:
                by_target[tid]["errors"] += 1

        return {
            "total_calls": total,
            "cross_calls": cross_calls,
            "cache_hits": cache_hits,
            "errors": errors,
            "by_target_agent": by_target,
        }


# 单例
_cross_caller: Optional[CrossCaller] = None


def get_cross_caller() -> CrossCaller:
    global _cross_caller
    if _cross_caller is None:
        _cross_caller = CrossCaller()
    return _cross_caller
