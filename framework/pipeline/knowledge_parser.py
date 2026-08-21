# -*- coding: utf-8 -*-
"""
文档导入格式解析器

支持 Markdown / Obsidian / PDF / 纯文本 的清洗与文本提取：
- parse_markdown: 清洗乱码（BOM、多余空白、统一换行符）
- parse_obsidian: 丢弃 YAML frontmatter、转换 [[wikilink]]
- parse_pdf:     优先 pdfplumber，其次 PyPDF2 提取文本
- detect_format: 按扩展名识别文档格式

完全离线运行，PDF 解析库（pdfplumber/PyPDF2）缺失时抛 ImportError 由调用方处理。
"""

from __future__ import annotations

import os
import re

# Obsidian wikilink：[[链接|显示名]] → 显示名；[[链接]] → 链接
_ALIAS_LINK_RE = re.compile(r"\[\[([^\]|]+)\|([^\]]+)\]\]")
_LINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")

# 扩展名 → 文档格式
_EXT_FORMAT_MAP = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".obsidian": "obsidian",
    ".canvas": "obsidian",
    ".pdf": "pdf",
    ".txt": "text",
    ".text": "text",
}


class KnowledgeParser:
    """文档导入格式解析器"""

    # ------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------
    def parse_markdown(self, text: str) -> str:
        """
        清洗 Markdown 文本：替换 BOM 乱码、统一换行符、压缩多余空白

        处理规则：
        - 去掉 \ufeff（UTF-8 BOM）
        - \r\n / \r → \n
        - 行内连续空格/制表符压缩为单个空格
        - 去除行尾空白
        - 连续空行压缩为最多一个空行

        返回：干净文本（首尾无多余空行）
        """
        if not text:
            return ""
        text = text.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
        lines = [re.sub(r"[ \t]{2,}", " ", line).rstrip() for line in text.split("\n")]

        cleaned = []
        blank_run = 0
        for line in lines:
            if not line.strip():
                blank_run += 1
                if blank_run > 1:
                    continue
            else:
                blank_run = 0
            cleaned.append(line)
        return "\n".join(cleaned).strip()

    # ------------------------------------------------------------
    # Obsidian
    # ------------------------------------------------------------
    def parse_obsidian(self, text: str) -> str:
        """
        处理 Obsidian 笔记文本：
        - 丢弃文件开头的 YAML frontmatter（--- 与 --- 之间的内容）
        - [[wikilink]] → wikilink 纯文本（含别名 [[链接|显示名]] → 显示名）
        - 保留正文内容

        返回：处理后的正文文本
        """
        if not text:
            return ""
        text = text.replace("\ufeff", "").replace("\r\n", "\n")
        lines = text.split("\n")

        # 丢弃 YAML frontmatter：首行为 ---，直到下一个 --- 结束
        if lines and lines[0].strip() == "---":
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    lines = lines[i + 1:]
                    break

        body = "\n".join(lines)
        # 带别名的 wikilink 优先（[[目标|显示名]] → 显示名）
        body = _ALIAS_LINK_RE.sub(r"\2", body)
        # 普通 wikilink（[[链接]] → 链接）
        body = _LINK_RE.sub(r"\1", body)
        return body.strip()

    # ------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------
    def parse_pdf(self, file_path: str) -> str:
        """
        提取 PDF 文本：优先 pdfplumber，失败/缺失时降级 PyPDF2

        - 文件不存在：返回空字符串
        - pdfplumber 与 PyPDF2 均未安装：抛 ImportError（由调用方转为友好提示）
        - pdfplumber 提取失败：自动降级 PyPDF2 重试

        返回：提取到的文本（可能为空字符串）
        """
        if not file_path or not os.path.isfile(file_path):
            return ""

        # 1) 优先 pdfplumber
        try:
            import pdfplumber
        except ImportError:
            pdfplumber = None
        if pdfplumber is not None:
            try:
                with pdfplumber.open(file_path) as pdf:
                    pages = [page.extract_text() or "" for page in pdf.pages]
                return "\n".join(pages).strip()
            except Exception:  # noqa: BLE001 - 提取失败降级 PyPDF2
                pass

        # 2) 其次 PyPDF2
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            raise ImportError(
                "未安装 PDF 解析库（pdfplumber / PyPDF2），无法解析 PDF 文件"
            ) from None
        reader = PdfReader(file_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()

    # ------------------------------------------------------------
    # 格式识别
    # ------------------------------------------------------------
    def detect_format(self, filename: str) -> str:
        """
        按扩展名识别文档格式：markdown / obsidian / pdf / text

        未知扩展名（或无扩展名）返回 "text"。
        """
        if not filename:
            return "text"
        ext = os.path.splitext(filename)[1].lower()
        return _EXT_FORMAT_MAP.get(ext, "text")
