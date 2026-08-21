# -*- coding: utf-8 -*-
"""
知识分层拆解引擎

将文档按 Markdown 标题层级（# / ## / ###）粗切为章节，
再从章节中用启发式规则（不调用真实 LLM）提取知识点，
支持去重、同名冲突检测与逐条落库。

完全离线运行，不依赖 Ollama / 网络。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger("lumilearn.agent.knowledge_pipeline")

# Markdown 标题（一级 ~ 三级）
_HEADING_RE = re.compile(r"^#{1,3}\s+(.+?)\s*$")

# 中文分句分隔符
_SENTENCE_SPLIT_RE = re.compile(r"[。！？!?；;\n]+")

# 知识点触发关键词（启发式规则命中即认为该句包含知识点）
_KEYWORDS = [
    "定义", "公式", "概念", "定律", "定理", "性质",
    "原理", "法则", "公理", "推论", "规则", "方法",
    "特征", "特点", "结论",
]

# 名称最大长度
_NAME_MAX_LEN = 20

# 知识主体提取：匹配「XXX的定义/公式/概念是…」结构，
# 提取出知识主体（如「勾股定理」「搭配不当」），用于生成结构化名称与冲突分组
_TOPIC_RE = re.compile(
    r"^([^，。！？；:：、\s]{2,12})(?:的)?(定义|公式|概念|定律|定理|性质|"
    r"法则|公理|原理|规则|方法|特征|特点|推论|结论)"
)


class KnowledgePipeline:
    """知识分层拆解引擎"""

    # ------------------------------------------------------------
    # 1. 文档 → 章节
    # ------------------------------------------------------------
    def parse_document(self, text: str, subject: str = "") -> List[Dict]:
        """
        按 Markdown 标题层级（# / ## / ###）粗切章节

        参数：
            text:    原始文档文本
            subject: 学科（用于无标题文本时的默认章节名）

        返回：
            [{"title": "第一章", "content": "..."}, ...]
        """
        if not text or not text.strip():
            return []

        chapters: List[Dict] = []
        current_title = None
        current_lines: List[str] = []

        for line in text.splitlines():
            m = _HEADING_RE.match(line)
            if m:
                # 收尾上一章节（或第一个标题前的"前言"）
                if current_title is None:
                    if any(l.strip() for l in current_lines):
                        chapters.append({
                            "title": "前言",
                            "content": "\n".join(current_lines).strip(),
                        })
                else:
                    chapters.append({
                        "title": current_title,
                        "content": "\n".join(current_lines).strip(),
                    })
                current_title = m.group(1).strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_title is not None:
            chapters.append({
                "title": current_title,
                "content": "\n".join(current_lines).strip(),
            })
        elif any(l.strip() for l in current_lines):
            # 全文没有任何标题：整体作为一章
            chapters.append({
                "title": subject or "未命名章节",
                "content": "\n".join(current_lines).strip(),
            })

        # 过滤空内容章节（仅有标题无正文的章节不产出知识点）
        return [c for c in chapters if c["content"].strip()]

    # ------------------------------------------------------------
    # 2. 章节 → 知识点
    # ------------------------------------------------------------
    def extract_knowledge_points(self, chapter: str) -> List[Dict]:
        """
        用启发式规则从章节文本中提取知识点（不调真实 LLM）

        规则：按句切分后，命中关键词（定义/公式/概念/定律/定理/性质等）
        的句子即为一条知识点；无任何命中时兜底为一条概念知识点。

        返回：
            [{"name": str, "description": str, "type": "concept|definition|formula|example"}, ...]
            至少 1 条；输入为空返回 []
        """
        if not chapter or not chapter.strip():
            return []

        points: List[Dict] = []
        for sent in _SENTENCE_SPLIT_RE.split(chapter):
            sent = sent.strip()
            if not sent:
                continue
            keyword = next((kw for kw in _KEYWORDS if kw in sent), None)
            if keyword is not None:
                points.append({
                    "name": self._make_name(sent),
                    "description": sent,
                    "type": self._classify(keyword, sent),
                })

        # 兜底：确保非空输入至少提取 1 条
        if not points:
            body = chapter.strip()
            points.append({
                "name": self._make_name(body),
                "description": body,
                "type": "concept",
            })

        return points

    @staticmethod
    def _extract_topic(text: str) -> Optional[str]:
        """从句子中提取知识主体（如「勾股定理」「搭配不当」）"""
        if not text:
            return None
        m = _TOPIC_RE.match(text.strip())
        return m.group(1).strip() if m else None

    @staticmethod
    def _make_name(sent: str) -> str:
        """由句子生成知识点名称：
        优先提取「主体+类型」结构（如「勾股定理的定义」「搭配不当的概念」），
        无法匹配时回退为截断整句（最长 _NAME_MAX_LEN 字）。
        """
        sent = sent.strip()
        m = _TOPIC_RE.match(sent)
        if m:
            topic = m.group(1).strip()
            kind = m.group(2).strip()
            # 原始句子已含"的"，不重复添加
            if "的" in sent[: len(topic) + 2]:
                return f"{topic}{kind}"
            return f"{topic}的{kind}"
        if len(sent) > _NAME_MAX_LEN:
            return sent[:_NAME_MAX_LEN] + "..."
        return sent

    @staticmethod
    def _classify(keyword: str, sent: str) -> str:
        """根据关键词与句子内容判定知识点类型"""
        if keyword == "定义":
            return "definition"
        if keyword == "公式":
            return "formula"
        if "例" in sent or "如" in sent:
            return "example"
        return "concept"

    # ------------------------------------------------------------
    # 3. 去重
    # ------------------------------------------------------------
    def deduplicate(self, points: List[Dict]) -> List[Dict]:
        """
        按 name 去重，保留首次出现

        返回：
            去重后的知识点列表（保持原顺序）
        """
        result: List[Dict] = []
        seen = set()
        for p in points:
            name = p.get("name", "")
            if name in seen:
                continue
            seen.add(name)
            result.append(p)
        return result

    # ------------------------------------------------------------
    # 4. 冲突检测
    # ------------------------------------------------------------
    def detect_conflicts(self, points: List[Dict]) -> List[Dict]:
        """
        检测同名知识点冲突：按「知识主体」（如「搭配不当」「勾股定理」）
        分组，同一主体存在不同描述时，给相关条目加 "conflict": true。

        返回：
            带 conflict 标记的知识点列表（不修改原输入）
        """
        topic_map: Dict[str, set] = {}
        for p in points:
            topic = self._extract_topic(p.get("description", "")) or p.get("name", "")
            topic_map.setdefault(topic, set()).add(p.get("description", ""))

        result: List[Dict] = []
        for p in points:
            topic = self._extract_topic(p.get("description", "")) or p.get("name", "")
            item = dict(p)
            if len(topic_map.get(topic, set())) > 1:
                item["conflict"] = True
            result.append(item)
        return result

    # ------------------------------------------------------------
    # 5. 落库
    # ------------------------------------------------------------
    def save_to_db(
        self,
        doc_id: str,
        points: List[Dict],
        subject: str = "",
        status: str = "ok",
    ) -> int:
        """
        将知识点逐条写入 knowledge_decomposition 表

        参数：
            doc_id:  来源文档 ID
            points:  知识点列表
            subject: 学科（条目自身无 subject 时使用）
            status:  写入状态（默认 ok）

        返回：
            成功写入的条数；单条异常时以 status="failed" 重试一次，
            仍失败则跳过继续下一条
        """
        from framework.database import db

        saved = 0
        for p in points:
            kwargs = dict(
                doc_id=doc_id,
                chapter=p.get("chapter", ""),
                knowledge_point=p.get("name", ""),
                subject=p.get("subject", subject),
                source_text=p.get("description", ""),
                raw_json=json.dumps(p, ensure_ascii=False),
            )
            try:
                db.add_knowledge_decomposition(**kwargs, status=status)
                saved += 1
            except Exception as exc:  # noqa: BLE001 - 单条失败不阻断整体
                logger.warning("知识点写入失败，标记 status=failed 重试: %s", exc)
                try:
                    db.add_knowledge_decomposition(**kwargs, status="failed")
                    saved += 1
                except Exception as exc2:  # noqa: BLE001
                    logger.error("知识点写入失败且重试失败，跳过: %s", exc2)

        return saved
