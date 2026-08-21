#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KnowledgePipeline 单元测试

覆盖：文档章节切分 / 启发式知识点提取 / 空输入 / 去重 / 冲突检测 / 落库
完全离线运行，不依赖 Ollama / 网络。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.knowledge_pipeline import KnowledgePipeline


class TestKnowledgePipeline(unittest.TestCase):
    """知识分层拆解引擎测试"""

    def setUp(self):
        self.pipeline = KnowledgePipeline()

    def test_parse_document_splits_chapters(self):
        """含 # ## ### 的文本应按标题切分为独立章节"""
        text = (
            "# 第一章 基础概念\n"
            "这是第一章的内容。\n"
            "## 1.1 定义\n"
            "定义了某个概念。\n"
            "### 1.1.1 公式\n"
            "包含公式的内容。\n"
            "## 1.2 性质\n"
            "第二条的内容。\n"
        )
        chapters = self.pipeline.parse_document(text)

        self.assertEqual(len(chapters), 4)
        self.assertEqual(chapters[0]["title"], "第一章 基础概念")
        self.assertIn("这是第一章的内容", chapters[0]["content"])
        self.assertNotIn("# 第一章", chapters[0]["content"])  # 标题行不进 content
        self.assertEqual(chapters[1]["title"], "1.1 定义")
        self.assertIn("定义了某个概念", chapters[1]["content"])
        self.assertEqual(chapters[2]["title"], "1.1.1 公式")
        self.assertEqual(chapters[3]["title"], "1.2 性质")

    def test_extract_knowledge_points_heuristic(self):
        """含 定义/公式 关键词的文本应提取出知识点"""
        chapter = (
            "勾股定理的定义：直角三角形两条直角边的平方和等于斜边的平方。\n"
            "相关公式：a² + b² = c²。\n"
            "这是没有关键词命中的普通描述文本。\n"
        )
        points = self.pipeline.extract_knowledge_points(chapter)

        self.assertGreaterEqual(len(points), 1)
        names = [p["name"] for p in points]
        self.assertTrue(any("勾股定理" in n for n in names))
        types = {p["type"] for p in points}
        self.assertTrue(types & {"concept", "definition", "formula", "example"})
        for p in points:
            self.assertIn("name", p)
            self.assertIn("description", p)
            self.assertIn("type", p)

    def test_extract_empty_returns_empty(self):
        """空文本应返回空列表"""
        self.assertEqual(self.pipeline.extract_knowledge_points(""), [])
        self.assertEqual(self.pipeline.extract_knowledge_points("   \n  "), [])
        self.assertEqual(self.pipeline.extract_knowledge_points(None), [])

    def test_deduplicate_removes_duplicates(self):
        """同名知识点应去重，保留首次出现"""
        points = [
            {"name": "勾股定理", "description": "描述A", "type": "definition"},
            {"name": "勾股定理", "description": "描述A", "type": "definition"},
            {"name": "牛顿定律", "description": "描述B", "type": "concept"},
        ]
        result = self.pipeline.deduplicate(points)

        self.assertEqual(len(result), 2)
        self.assertEqual([p["name"] for p in result], ["勾股定理", "牛顿定律"])
        self.assertEqual(result[0]["description"], "描述A")

    def test_detect_conflicts_marks(self):
        """同名但描述不一致的知识点应标记 conflict=True"""
        points = [
            {"name": "勾股定理", "description": "描述A", "type": "definition"},
            {"name": "勾股定理", "description": "描述B", "type": "concept"},
            {"name": "牛顿定律", "description": "描述C", "type": "concept"},
        ]
        result = self.pipeline.detect_conflicts(points)

        self.assertTrue(result[0].get("conflict", False))
        self.assertTrue(result[1].get("conflict", False))
        self.assertNotIn("conflict", result[2])
        # 不修改原输入
        self.assertNotIn("conflict", points[0])

    def test_save_to_db(self):
        """知识点应逐条写入真实数据库并返回写入条数"""
        from framework.database import db

        db.init()  # conftest 已指向临时库（LUMILEARN_DB_PATH），无参 init 安全
        points = [
            {
                "name": "勾股定理",
                "description": "直角三角形两条直角边的平方和等于斜边的平方",
                "type": "definition",
            },
            {
                "name": "牛顿第二定律",
                "description": "F = ma",
                "type": "formula",
            },
        ]
        count = self.pipeline.save_to_db("test_doc_001", points, subject="数学")
        self.assertGreater(count, 0)
        self.assertEqual(count, len(points))

        rows = db.conn.execute(
            "SELECT * FROM knowledge_decomposition WHERE doc_id = ?",
            ("test_doc_001",),
        ).fetchall()
        self.assertEqual(len(rows), len(points))
        names = {row["knowledge_point"] for row in rows}
        self.assertEqual(names, {"勾股定理", "牛顿第二定律"})


if __name__ == "__main__":
    unittest.main()
