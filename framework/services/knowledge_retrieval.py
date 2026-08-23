# -*- coding: utf-8 -*-
"""
LumiLearn RAG 知识库检索服务（关键词倒排索引版）
====================================================
设计目标（遵循 GOAI 行动规划 Day3）：
  - 不引入向量数据库 / 外部依赖，纯 Python 关键词倒排索引
  - 数据源：training_data 表（published 教学内容）+ knowledge_nodes 表（知识点）
  - 轻量中文分词：领域词典精确匹配 + 2-gram 补充 + 停用词过滤
  - BM25 简化打分：tf + idf + 文档长度归一化

用法：
    from framework.services.knowledge_retrieval import get_knowledge_retriever
    retriever = get_knowledge_retriever()
    results = retriever.search("函数的单调性", top_k=5)

说明：
  - 索引惰性构建 + 内存缓存；数据库变更后调用 refresh() 重建
  - 任何检索失败都降级返回空列表，绝不阻塞教学主流程

作者：LumiLearn
版本：1.0.0
日期：2026-08-12
"""

import math
import re
import time
from typing import Dict, List, Optional

# 学科同义词词典：查询扩展（同义词 OR 关系），提升召回率
from framework.services.synonym_dict import expand_query

# 领域词典（与 feynman_engine 的学科/主题关键词保持一致，保证检索一致性）
DOMAIN_TERMS = [
    # 数学
    "数学", "代数", "几何", "函数", "概率", "方程", "公式", "计算", "面积", "体积",
    "三角形", "圆", "数", "加减乘除", "勾股", "坐标", "数列", "向量", "矩阵",
    "不等式", "多项式", "因式分解", "未知数", "移项", "定义域", "值域", "单调",
    "奇偶", "指数", "对数", "映射", "统计", "频率", "随机", "期望", "组合", "排列",
    "相似", "全等", "角度", "斜率", "导数", "积分", "等差", "等比",
    # 物理
    "物理", "力学", "电", "磁", "光", "热", "声", "力", "速度", "加速度",
    "牛顿", "欧姆", "焦耳", "能量", "功率", "电压", "电流", "电阻", "磁场",
    "运动", "功", "动量", "摩擦", "杠杆", "电磁", "电路", "安培", "温度",
    "热量", "熵", "热力学", "内能", "卡诺", "传导", "反射", "折射", "透镜",
    "镜", "光谱", "波长", "色散", "成像", "自由落体", "重力", "浮力", "压强",
    # 化学
    "化学", "元素", "周期", "反应", "分子", "原子", "离子", "化合", "分解",
    "酸", "碱", "盐", "氧化", "还原", "催化剂", "配平", "方程式", "键",
    "离子键", "共价键", "电子", "结构", "摩尔", "溶液", "沉淀", "气体",
    # 生物
    "生物", "细胞", "光合作用", "呼吸作用", "遗传", "基因", "蛋白质", "酶",
    "神经", "血液", "免疫", "生态", "进化", "DNA", "染色体", "新陈代谢",
    # 英语
    "英语", "英文", "语法", "单词", "词汇", "写作", "阅读", "翻译", "时态",
    "口语", "听力", "发音", "从句", "短语", "主谓", "语态", "句型", "固定搭配",
    "词根", "词缀", "同义词", "文章", "段落", "结构",
    # 通用教学
    "概念", "定义", "原理", "定律", "定理", "证明", "推导", "例题", "练习",
    "掌握", "理解", "应用", "分析", "综合", "评价",
]

STOPWORDS = {
    "的", "了", "和", "是", "在", "我", "你", "他", "她", "它", "有", "就", "不",
    "都", "一", "一个", "一种", "什么", "怎么", "为什么", "如何", "吗", "呢", "啊",
    "吧", "请", "帮", "讲", "教", "学", "给", "the", "a", "an", "is", "of", "to",
    "and", "or", "for", "with", "on", "at", "in",
}

_SPLIT_RE = re.compile(r"[^\w\u4e00-\u9fff]+")
# 不可见/控制字符（零宽字符、乱码 BOM 残留等）
_INVISIBLE_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\u200b\u200c\u200d\u2060\ufeff]")
# 中文句子边界（句号/问号/感叹号/分号 + 换行）
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？；\n])\s*")
# 分片默认参数
DEFAULT_CHUNK_CHARS = 260        # 每片目标字符数（与 LLM 上下文友好）
DEFAULT_CHUNK_OVERLAP = 40       # 相邻片重叠字符数（保留跨片语义）


def clean_text(text: str) -> str:
    """清洗文本：去除不可见字符/控制字符、压缩空白，减少解析乱码。

    - 移除零宽字符、BOM、控制字符（乱码常见来源）
    - \r\n / \r → \n
    - 连续空白压缩为单个空格
    """
    if not text:
        return ""
    text = _INVISIBLE_RE.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def chunk_text(text: str, max_chars: int = DEFAULT_CHUNK_CHARS,
               overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
    """将长文本按句子边界智能分片，避免在公式/单词中间切断产生乱码碎片。

    策略：
    - 优先按句子边界（。！？；换行）切分
    - 句子过长时按空白/逗号回退切分，仍保留完整词元
    - 相邻片带 overlap 重叠字符，保留跨片语义，避免关键词被截断
    - 空串返回空列表

    返回：分片后的文本列表（已清洗）
    """
    text = clean_text(text)
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    # 1) 按句子边界切分，再合并为不超 max_chars 的片
    sentences = [s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    chunks: List[str] = []
    cur = ""
    for sent in sentences:
        # 单句超长：内部按逗号/分号/空格回退切分
        if len(sent) > max_chars:
            if cur:
                chunks.append(cur.strip())
                cur = ""
            for piece in re.split(r"(?<=[，、,;；])\s*", sent):
                if len(piece) > max_chars:
                    # 最后兜底：硬切但保留完整词（避免切进 URL/公式中间）
                    while len(piece) > max_chars:
                        chunks.append(piece[:max_chars].strip())
                        piece = piece[max_chars:]
                    if piece.strip():
                        cur = piece.strip()
                elif len(cur) + len(piece) > max_chars:
                    if cur:
                        chunks.append(cur.strip())
                    cur = piece.strip()
                else:
                    cur = (cur + piece).strip()
            continue
        if len(cur) + len(sent) > max_chars:
            if cur:
                chunks.append(cur.strip())
            cur = sent
        else:
            cur = (cur + sent).strip()
    if cur:
        chunks.append(cur.strip())

    # 2) 应用 overlap：前一个片尾部 overlap 字符并入后一片开头
    if overlap > 0 and len(chunks) > 1:
        overlapped: List[str] = []
        prev_tail = ""
        for i, ch in enumerate(chunks):
            if prev_tail:
                ch = prev_tail + ch
            overlapped.append(ch)
            prev_tail = ch[-overlap:] if len(ch) >= overlap else ch
        chunks = overlapped

    return chunks


def tokenize(text: str, max_terms: int = 32) -> List[str]:
    """轻量中文分词：领域词典精确匹配 + 2-gram 补充 + 停用词过滤"""
    if not text:
        return []
    terms = []
    # 1) 领域词典命中
    for term in DOMAIN_TERMS:
        if term and term in text and term not in terms:
            terms.append(term)
    # 2) 字母数字连续段（英文/数字）
    for seg in _SPLIT_RE.split(text.lower()):
        if seg and len(seg) <= 24 and seg not in STOPWORDS:
            terms.append(seg)
    # 3) 中文 2-gram
    han = re.sub(r"[^\u4e00-\u9fff]", "", text)
    for i in range(len(han) - 1):
        gram = han[i:i + 2]
        if gram not in STOPWORDS and gram not in terms:
            terms.append(gram)
    # 4) 整体短语（如"单调性""勾股定理"整词，词典未覆盖时的兜底）
    if len(text) <= 8 and text not in STOPWORDS and text not in terms:
        terms.append(text)
    # 去掉过短无意义项，并限制数量
    cleaned = [t for t in terms if len(t) >= 2 or t.isascii()]
    return cleaned[:max_terms]


class KnowledgeRetriever:
    """基于 training_data + knowledge_nodes 的关键词倒排索引检索器"""

    def __init__(self, max_docs: int = 5000):
        self.max_docs = max_docs
        self.docs: List[Dict] = []          # 文档列表
        self.postings: Dict[str, Dict[int, int]] = {}  # term -> {doc_idx: tf}
        self.doc_len: List[int] = []         # 每文档 token 数
        self.df: Dict[str, int] = {}         # term -> 文档频率
        self._built_at = 0.0
        self._built = False

    # ---------------- 索引构建 ----------------

    def _load_docs(self) -> List[Dict]:
        """从数据库加载训练数据 + 知识点，长文档按句子边界分片索引。

        分片策略（RAG 稳定性优化）：
        - 长 content 按 chunk_text 切分为多片，每片作为独立检索文档
        - 分片避免关键词被长文档稀释，提升召回精度；清洗去除乱码字符
        - 每片标题标注 [片段 N/M]，便于追溯来源
        """
        docs = []
        try:
            from framework.database import db
            records = db.get_training_data(status="published", limit=self.max_docs)
            for r in records:
                content_raw = r.get("content", "") or ""
                content_parts = chunk_text(content_raw)
                n = len(content_parts)
                for idx, part in enumerate(content_parts):
                    part_title = r.get("title") or r.get("chapter") or ""
                    if n > 1:
                        part_title = f"{part_title} [片段 {idx + 1}/{n}]"
                    text = " ".join(filter(None, [
                        r.get("subject", ""), r.get("chapter", ""),
                        part_title, r.get("keywords", ""),
                        part,
                    ]))
                    docs.append({
                        "source": "training_data",
                        "id": r.get("id"),
                        "title": part_title,
                        "subject": r.get("subject", ""),
                        "grade": r.get("grade", ""),
                        "difficulty": r.get("difficulty", ""),
                        "content": part[:1000],
                        "keywords": r.get("keywords", ""),
                        "_text": text,
                    })
        except Exception:
            pass

        try:
            from framework.database import db
            nodes = db.get_knowledge_nodes()
            for n in nodes:
                desc = clean_text(n.get("description", "") or "")
                text = " ".join(filter(None, [
                    n.get("category", ""), n.get("name", ""), desc,
                ]))
                docs.append({
                    "source": "knowledge_node",
                    "id": n.get("id"),
                    "title": n.get("name", ""),
                    "subject": n.get("category", ""),
                    "grade": "",
                    "difficulty": n.get("difficulty", ""),
                    "content": desc,
                    "keywords": "",
                    "_text": text,
                })
        except Exception:
            pass
        return docs

    def build_index(self, force: bool = False):
        """构建倒排索引（惰性；force=True 强制重建）"""
        if self._built and not force:
            return
        docs = self._load_docs()
        self.docs = docs
        self.postings = {}
        self.doc_len = []
        self.df = {}
        for idx, doc in enumerate(docs):
            tokens = tokenize(doc["_text"])
            self.doc_len.append(len(tokens))
            seen = set()
            for t in tokens:
                if t not in self.postings:
                    self.postings[t] = {}
                self.postings[t][idx] = self.postings[t].get(idx, 0) + 1
                if t not in seen:
                    self.df[t] = self.df.get(t, 0) + 1
                    seen.add(t)
        self._built = True
        self._built_at = time.time()

    def refresh(self):
        """数据库变更后强制重建索引"""
        self._built = False
        self.build_index(force=True)

    # ---------------- 检索 ----------------

    def _idf(self, term: str) -> float:
        n = len(self.docs)
        df = self.df.get(term, 0)
        return math.log((n - df + 0.5) / (df + 0.5) + 1.0)

    def search(self, query: str, top_k: int = 5,
               subject: Optional[str] = None) -> List[Dict]:
        """
        关键词检索（含同义词扩展），返回按相关度排序的文档列表。

        参数:
            query:   查询文本（如教学主题）
            top_k:   返回条数
            subject: 可选学科过滤（同时用于限定同义词扩展的学科范围）
        返回:
            [{source, id, title, subject, grade, difficulty, content,
              keywords, snippet, score}, ...]
        """
        if not query or not query.strip():
            return []
        try:
            self.build_index()
        except Exception:
            return []
        if not self.docs:
            return []

        # 同义词扩展：对每个扩展词分别分词并合并打分（同义词 OR 关系）
        expand_subject = subject if subject else "all"
        q_tokens: List[str] = []
        for q in expand_query(query.strip(), expand_subject):
            for t in tokenize(q):
                if t not in q_tokens:
                    q_tokens.append(t)
        if not q_tokens:
            return []

        # 打分（简化 BM25：tf 归一 + idf）
        scores: Dict[int, float] = {}
        matched: Dict[int, int] = {}
        for t in q_tokens:
            post = self.postings.get(t)
            if not post:
                continue
            idf = self._idf(t)
            for doc_idx, tf in post.items():
                doc = self.docs[doc_idx]
                if subject and subject != "all" and doc.get("subject") != subject:
                    continue
                dl = max(self.doc_len[doc_idx], 1)
                scores[doc_idx] = scores.get(doc_idx, 0.0) + idf * (tf / (tf + 0.75))
                matched[doc_idx] = matched.get(doc_idx, 0) + 1

        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], -matched.get(kv[0], 0)))
        results = []
        for doc_idx, score in ranked[:top_k]:
            doc = dict(self.docs[doc_idx])
            doc["score"] = round(score, 4)
            doc["snippet"] = (doc.get("content") or "")[:200]
            doc.pop("_text", None)
            results.append(doc)
        return results

    def search_semantic(self, query: str, top_k: int = 5,
                        subject: Optional[str] = None) -> List[Dict]:
        """
        预留语义检索接口，未来接入 embedding 向量检索。
        当前返回空列表，不参与召回。
        """
        return []

    def status(self) -> Dict:
        """索引状态（供管理/调试）"""
        return {
            "built": self._built,
            "doc_count": len(self.docs),
            "term_count": len(self.postings),
            "built_at": round(self._built_at, 2) if self._built else 0,
        }


# 单例
_retriever_instance: Optional[KnowledgeRetriever] = None


def get_knowledge_retriever() -> KnowledgeRetriever:
    """获取全局检索器单例"""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = KnowledgeRetriever()
    return _retriever_instance


def format_rag_context(results: List[Dict], max_chars: int = 800) -> str:
    """将检索结果格式化为注入 prompt 的参考资料文本"""
    if not results:
        return ""
    parts = []
    used = 0
    for r in results:
        title = r.get("title") or ""
        content = (r.get("content") or "").strip()
        if not content:
            continue
        snippet = content[:max_chars - used]
        parts.append(f"[{r.get('subject', '知识')}·{title}]\n{snippet}")
        used += len(snippet)
        if used >= max_chars:
            break
    return "\n\n".join(parts)


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    r = get_knowledge_retriever()
    r.build_index()
    print("索引状态:", r.status())
    for q in ["勾股定理", "牛顿第二定律", "光合作用", "共价键", "函数单调性"]:
        res = r.search(q, top_k=3)
        print("\n查询「%s」→ %d 条" % (q, len(res)))
        for item in res:
            print("  [%.3f] %s | %s | %s" % (
                item["score"], item["source"], item.get("subject"), item.get("title")))
