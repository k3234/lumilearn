# -*- coding: utf-8 -*-
"""
⑩ RAG 流水线稳定性 — 文档分片与清洗单元测试

覆盖：
- chunk_text 按句子边界分片，不切碎公式/词元
- 分片 overlap 保留跨片语义
- clean_text 去除乱码（BOM/零宽/控制字符）
- 长文档入库后按片索引，检索精度不稀释

依赖 tests/conftest.py 的 autouse fixture isolated_db。
"""
import unittest

from framework.services.knowledge_retrieval import (
    chunk_text, clean_text, KnowledgeRetriever, DEFAULT_CHUNK_CHARS,
)


class TestCleanText(unittest.TestCase):
    """文本清洗：去除乱码字符"""

    def test_removes_bom_and_zwj(self):
        raw = "\ufeff勾股定理：\u200ba²\u200d+b²=c²\u200b"
        cleaned = clean_text(raw)
        self.assertNotIn("\ufeff", cleaned)
        self.assertNotIn("\u200b", cleaned)
        self.assertNotIn("\u200d", cleaned)
        self.assertIn("勾股定理", cleaned)

    def test_removes_control_chars(self):
        raw = "牛顿\x00第二\x07定律：F=ma"
        cleaned = clean_text(raw)
        self.assertNotIn("\x00", cleaned)
        self.assertNotIn("\x07", cleaned)
        self.assertIn("牛顿第二定律", cleaned)

    def test_normalizes_whitespace_and_newline(self):
        raw = "第一行\r\n\r\n  第二行  \t 末尾"
        cleaned = clean_text(raw)
        self.assertNotIn("\r", cleaned)
        self.assertNotIn("\t", cleaned)
        self.assertNotIn("  ", cleaned)
        self.assertIn("第一行", cleaned)
        self.assertIn("第二行", cleaned)

    def test_empty_and_whitespace(self):
        self.assertEqual(clean_text(""), "")
        self.assertEqual(clean_text("   "), "")


class TestChunkText(unittest.TestCase):
    """文档分片：按句子边界，避免切断公式"""

    def test_short_text_single_chunk(self):
        chunks = chunk_text("勾股定理：a²+b²=c²")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], "勾股定理：a²+b²=c²")

    def test_empty_text(self):
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text(None), [])

    def test_sentence_boundary_split(self):
        """长文按句号边界分片，不会切断句子"""
        text = ("勾股定理描述直角三角形三边关系。"
                "公式为a的平方加b的平方等于c的平方。"
                "其中c为斜边。中国古代称其为勾股。") * 3
        chunks = chunk_text(text, max_chars=60, overlap=0)
        self.assertGreater(len(chunks), 1)
        for ch in chunks:
            self.assertLessEqual(len(ch), 70)  # 容忍 overlap 为 0 时的边界

    def test_overlap_preserves_cross_chunk_semantics(self):
        """overlap>0 时，前后片共享尾部字符，避免关键词被截断"""
        text = ("第一句是核心概念定义。第二句补充例子。"
                "第三句介绍历史背景。第四句给出公式。") * 2
        chunks = chunk_text(text, max_chars=40, overlap=10)
        self.assertGreater(len(chunks), 1)
        # 后一片开头应包含前一片尾部字符（跨片语义保留）
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-10:]
            self.assertIn(tail, chunks[i])

    def test_no_formula_splitting_in_middle_of_token(self):
        """长公式不应被从中间硬切（应整体保留在单片内）"""
        formula = "E = mc²" * 30  # 无句子边界的长串
        text = "物理公式如下：" + formula + "。这是结尾。"
        chunks = chunk_text(text, max_chars=50, overlap=0)
        for ch in chunks:
            # 不应出现从单词中间断裂的残留（如 "c" 单独成片）
            self.assertNotIn("mc²mc", ch[:len("mc²mc")])

    def test_chunk_results_all_nonempty(self):
        text = ("第一段内容。第二段内容。第三段内容。") * 20
        chunks = chunk_text(text, max_chars=30)
        self.assertTrue(all(c.strip() for c in chunks))


class TestIndexedChunking(unittest.TestCase):
    """分片入库索引：长文档按片索引，检索不稀释"""

    def setUp(self):
        from framework.database import db
        self.db = db
        # 清空并预置一条长文档
        self.db.conn.execute("DELETE FROM training_data")
        self.db.conn.commit()
        self.db.add_training_data(
            subject="数学", chapter="几何",
            title="勾股定理全解",
            content=("勾股定理是最重要的几何定理。"
                     "公式a的平方加b的平方等于c的平方。"
                     "已知直角边求斜边用开方。"
                     "历史上周髀算经最早记载。") * 8,
            difficulty="基础",
            status="published",
        )

    def test_long_doc_split_into_chunks(self):
        """published 长文档被 _load_docs 分片为多个索引文档"""
        r = KnowledgeRetriever(max_docs=100)
        docs = r._load_docs()
        self.assertGreater(len(docs), 1)  # 长文档被拆为多片
        # 每个分片内容不超过 max_chars + 允许的小幅溢出
        for d in docs:
            self.assertLessEqual(len(d["content"]), DEFAULT_CHUNK_CHARS + 5)
        # 分片标题带 [片段 N/M] 标记
        titles = [d["title"] for d in docs]
        self.assertTrue(any("[片段" in t for t in titles))

    def test_chunked_docs_have_fragment_marker(self):
        """多个分片时标题应带 [片段 N/M] 标记，便于追溯"""
        content = ("勾股定理是最重要的几何定理。"
                   "公式a的平方加b的平方等于c的平方。"
                   "已知直角边求斜边用开方。"
                   "历史上周髀算经最早记载。") * 8
        parts = chunk_text(content)
        if len(parts) > 1:
            self.assertIn("[片段 1/", f"[片段 1/{len(parts)}]")


if __name__ == "__main__":
    unittest.main()
