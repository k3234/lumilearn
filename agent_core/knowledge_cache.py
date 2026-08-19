# -*- coding: utf-8 -*-
"""
自积累知识库服务

Agent 产出的可复用知识存入此服务，供其他 Agent 查询。
实现"越用越聪明"：同样的主题，后续请求可直接复用已有知识。
"""

from __future__ import annotations

import hashlib
import logging
import threading
from typing import Dict, List, Optional

logger = logging.getLogger("lumilearn.agent.knowledge")


class KnowledgeCache:
    """自积累知识库"""

    def __init__(self):
        self._lock = threading.Lock()
        self._memory_cache: Dict[str, Dict] = {}
        self._cache_ttl = 60.0  # 内存缓存 60 秒

    def _make_key(self, topic: str, knowledge_type: str, source_agent: str) -> str:
        """生成知识唯一 ID"""
        raw = f"{topic}:{knowledge_type}:{source_agent}"
        return f"know_{hashlib.md5(raw.encode()).hexdigest()[:12]}"

    def query(
        self,
        topic: str,
        knowledge_type: str = "",
        subject: str = "",
        min_quality: float = 0.0,
        limit: int = 3,
    ) -> List[Dict]:
        """
        查询积累知识

        参数：
            topic: 主题（模糊匹配）
            knowledge_type: 知识类型（concept/explanation/test/solution/pattern）
            subject: 学科筛选
            min_quality: 最低质量分数
            limit: 返回条数

        返回：
            知识条目列表
        """
        from framework.database import db
        results = db.get_knowledge(
            topic=topic,
            subject=subject,
            knowledge_type=knowledge_type,
            min_quality=min_quality,
            limit=limit,
        )
        # 增加使用计数
        for item in results:
            db.increment_knowledge_usage(item["knowledge_id"])
        return results

    def query_by_agent(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> List[Dict]:
        """查询某 Agent 产出的所有知识"""
        from framework.database import db
        return db.get_knowledge(source_agent=agent_id, limit=limit)

    def save(
        self,
        topic: str,
        knowledge_type: str,
        content: str,
        source_agent: str,
        subject: str = "",
        summary: str = "",
        quality_score: float = 0.0,
        tags: List[str] = None,
        related_nodes: List[str] = None,
        source_call_id: Optional[int] = None,
    ) -> Dict:
        """
        保存一条积累知识

        参数：
            topic: 学习主题
            knowledge_type: 知识类型
            content: 知识内容
            source_agent: 产出 Agent
            subject: 学科
            summary: 摘要（用于快速检索）
            quality_score: 质量评分 0-100
            tags: 标签列表
            related_nodes: 关联知识点
            source_call_id: 关联的 agent_call_log.id（None 表示不关联，
                            避免 FK 约束引用不存在的调用记录）

        返回：
            知识条目信息
        """
        from framework.database import db

        knowledge_id = self._make_key(topic, knowledge_type, source_agent)

        # 生成摘要
        if not summary:
            summary = content[:200] if len(content) > 200 else content

        row_id = db.save_knowledge(
            knowledge_id=knowledge_id,
            topic=topic,
            subject=subject,
            knowledge_type=knowledge_type,
            content=content,
            summary=summary,
            source_agent=source_agent,
            source_call_id=source_call_id,
            quality_score=quality_score,
            tags=tags,
            related_nodes=related_nodes,
        )

        # 更新内存缓存
        with self._lock:
            self._memory_cache[knowledge_id] = {
                "knowledge_id": knowledge_id,
                "topic": topic,
                "subject": subject,
                "knowledge_type": knowledge_type,
                "content": content,
                "summary": summary,
                "source_agent": source_agent,
                "quality_score": quality_score,
                "created_at": __import__("datetime").datetime.now().isoformat(),
            }

        logger.info(f"知识已积累: {knowledge_id} | topic={topic} | type={knowledge_type} | agent={source_agent}")
        return {
            "knowledge_id": knowledge_id,
            "row_id": row_id,
            "topic": topic,
            "type": knowledge_type,
        }

    def get_context(
        self,
        topic: str,
        subject: str = "",
        max_tokens: int = 1000,
    ) -> str:
        """
        获取与主题相关的积累知识上下文（用于注入到 prompt）

        参数：
            topic: 学习主题
            subject: 学科
            max_tokens: 最大 token 数（粗略估算）

        返回：
            拼接后的上下文文本
        """
        from framework.database import db

        results = db.get_knowledge(topic=topic, subject=subject, min_quality=50.0, limit=5)
        if not results:
            return ""

        parts = []
        total_len = 0
        for item in results:
            text = f"[由 {item['source_agent']} 积累] {item['topic']}: {item['summary']}"
            if total_len + len(text) > max_tokens * 4:  # 粗略估算：1 token ≈ 4 字符
                break
            parts.append(text)
            total_len += len(text)

        return "\n".join(parts) if parts else ""

    def invalidate(self, knowledge_id: str) -> bool:
        """使指定知识失效（从内存缓存中删除）"""
        with self._lock:
            return self._memory_cache.pop(knowledge_id, None) is not None

    def clear_cache(self):
        """清空内存缓存"""
        with self._lock:
            self._memory_cache.clear()


# 单例
_knowledge_cache: Optional[KnowledgeCache] = None


def get_knowledge_cache() -> KnowledgeCache:
    global _knowledge_cache
    if _knowledge_cache is None:
        _knowledge_cache = KnowledgeCache()
    return _knowledge_cache
