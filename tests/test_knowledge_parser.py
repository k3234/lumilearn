#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KnowledgeParser 单元测试

覆盖：Markdown 清洗 / Obsidian frontmatter 与 wikilink / 格式识别 / PDF 缺文件
完全离线运行，不依赖 pdfplumber / PyPDF2 / Ollama / 网络。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.pipeline.knowledge_parser import KnowledgeParser


class TestKnowledgeParser(unittest.TestCase):
    """文档导入格式解析器测试"""

    def setUp(self):
        self.parser = KnowledgeParser()

    def test_parse_markdown_cleans(self):
        """含 \ufeff 与多余空白的文本应被清洗干净"""
        text = (
            "\ufeff# 标题\r\n"
            "\r\n"
            "\r\n"
            "正文  内容。  \r\n"
            "  \r\n"
            "结尾\t\t  "
        )
        result = self.parser.parse_markdown(text)

        self.assertNotIn("\ufeff", result)
        self.assertNotIn("\r", result)
        self.assertIn("# 标题", result)
        self.assertIn("正文 内容。", result)
        self.assertIn("结尾", result)
        # 行内多余空白被压缩、行尾无空白、连续空行被压缩为最多一个空行
        self.assertNotIn("  ", result)
        self.assertNotRegex(result, r"[ \t]+\n")
        self.assertNotRegex(result, r"\n{3,}")

    def test_parse_obsidian_frontmatter(self):
        """YAML frontmatter（--- 之间）应被丢弃，正文保留"""
        text = (
            "---\n"
            "title: 三角学笔记\n"
            "tags: [数学, 高中]\n"
            "created: 2026-08-21\n"
            "---\n"
            "# 三角学\n"
            "正文内容。\n"
        )
        result = self.parser.parse_obsidian(text)

        self.assertNotIn("title:", result)
        self.assertNotIn("tags:", result)
        self.assertNotIn("created:", result)
        self.assertIn("# 三角学", result)
        self.assertIn("正文内容", result)

    def test_parse_obsidian_wikilink(self):
        """[[wikilink]] 应转换为纯文本"""
        text = "参见 [[勾股定理]] 与 [[正弦定理]]。"
        result = self.parser.parse_obsidian(text)

        self.assertIn("参见 勾股定理 与 正弦定理。", result)
        self.assertNotIn("[[", result)
        self.assertNotIn("]]", result)

    def test_detect_format(self):
        """markdown / obsidian / pdf / txt 扩展名应正确识别"""
        self.assertEqual(self.parser.detect_format("note.md"), "markdown")
        self.assertEqual(self.parser.detect_format("note.markdown"), "markdown")
        self.assertEqual(self.parser.detect_format("note.obsidian"), "obsidian")
        self.assertEqual(self.parser.detect_format("note.pdf"), "pdf")
        self.assertEqual(self.parser.detect_format("note.txt"), "text")
        # 未知扩展名兜底为 text
        self.assertEqual(self.parser.detect_format("note.docx"), "text")
        self.assertEqual(self.parser.detect_format(""), "text")

    def test_parse_pdf_missing_file(self):
        """不存在的 PDF 文件应返回空字符串（不抛异常）"""
        missing = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "no_such_file_12345.pdf",
        )
        self.assertFalse(os.path.exists(missing))
        self.assertEqual(self.parser.parse_pdf(missing), "")
        # 空路径同样返回空字符串
        self.assertEqual(self.parser.parse_pdf(""), "")


if __name__ == "__main__":
    unittest.main()
