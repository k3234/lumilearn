#!/usr/bin/env python3
"""
灵学 lumilearn - 幻灯片 API 路由
幻灯片生成端点（基于本地 Ollama 模型真实生成）
"""
import html
import logging
import re
from flask import Blueprint, request, jsonify

from framework.models.ollama_provider import get_ollama_provider

logger = logging.getLogger("lumilearn.routes.slides")

slides_bp = Blueprint("slides", __name__)

SLIDES_MODEL = "lumilearn-v2:latest"
MAX_SLIDES = 12


def _build_prompt(topic: str, slide_count: int, style: str) -> str:
    """构建幻灯片生成提示词"""
    style_hint = {
        "detailed": "内容详细，每页给出关键要点",
        "concise": "内容精炼，突出重点",
        "default": "内容条理清晰",
    }.get(style, "内容条理清晰")
    return (
        f"你是 LumiLearn 的教学幻灯片生成助手。请为学习主题「{topic}」生成 {slide_count} 页教学幻灯片。\n"
        f"要求：{style_hint}；内容面向高中生，准确、有条理；"
        f"第 1 页介绍概念，中间页讲原理/推导/应用，最后一页总结与思考。\n\n"
        f"必须严格按以下格式输出（每页固定两行，用 PAGE| 开头）：\n"
        f"PAGE|标题|副标题\n"
        f"第一行内容\n"
        f"第二行内容\n"
        f"PAGE|标题2|副标题2\n"
        f"...\n\n"
        f"不要输出任何其他文字或代码块标记。"
    )


def _clean_md(text: str) -> str:
    """清理内容行中的 markdown 符号，转义 HTML"""
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", text)   # **加粗**
    t = re.sub(r"\*([^*]+)\*", r"\1", t)         # *斜体*
    t = re.sub(r"`([^`]+)`", r"\1", t)           # `代码`
    t = re.sub(r"^#{1,6}\s*", "", t)             # 标题符
    t = re.sub(r"^\s*[-•]\s+", "", t)            # 列表符
    t = re.sub(r"^\s*\d+[\.、)]\s*", "", t)      # 数字序号
    return html.escape(t).strip()


def _build_slide(title: str, subtitle: str, content_lines: list) -> dict:
    """将标题+内容行构建为前端 slides 结构"""
    paragraphs = []
    for line in content_lines:
        clean = _clean_md(line)
        if not clean:
            continue
        paragraphs.append(
            f'<p style="font-size:15px;line-height:1.8;margin:4px 0;">'
            f'<span style="color:var(--accent);font-weight:600;">●</span> {clean}</p>'
        )
    return {
        "title": title,
        "subtitle": subtitle,
        "content": "".join(paragraphs),
        "katex": "",
    }


def _parse_slides(text: str, topic: str, slide_count: int) -> list:
    """解析模型输出为前端 slides 结构（title/subtitle/content/katex）

    优先解析 PAGE| 严格格式；模型不遵守时回退到 markdown 标题结构。
    """
    slides = _parse_page_format(text, topic, slide_count)
    if slides:
        return slides
    return _parse_markdown(text, topic, slide_count)


def _parse_page_format(text: str, topic: str, slide_count: int) -> list:
    """严格格式解析：PAGE|标题|副标题 + 内容行"""
    slides = []
    pages = re.split(r"(?m)^\s*PAGE\|", text)
    for page in pages[1:]:
        lines = [l.strip() for l in page.strip().splitlines() if l.strip()]
        if not lines:
            continue
        parts = lines[0].split("|", 2)
        title = parts[0].strip() if parts[0].strip() else topic
        subtitle = parts[1].strip() if len(parts) > 1 else ""
        content_lines = [re.sub(r"^PAGE\|\s*", "", l) for l in lines[1:]]
        if not content_lines:
            continue
        slides.append(_build_slide(title, subtitle, content_lines))
        if len(slides) >= slide_count:
            break
    return slides


def _parse_markdown(text: str, topic: str, slide_count: int) -> list:
    """宽松解析：按 markdown 标题（##/###/**标题**）切页；无标题时整段均分"""
    slides = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title_re = re.compile(r"^(#{1,4})\s+(.+?)\s*$|^\*\*(.+?)\*\*\s*$")

    current_title, current_sub, current_lines = None, "", []
    for line in lines:
        m = title_re.match(line)
        if m:
            if current_title and current_lines:
                slides.append(_build_slide(current_title, current_sub, current_lines))
                current_lines = []
            current_title = (m.group(2) or m.group(3) or "").strip() or topic
            current_sub = ""
        else:
            if current_title is None:
                current_title = topic
            current_lines.append(line)

    if current_title and current_lines:
        slides.append(_build_slide(current_title, current_sub, current_lines))

    # 无标题结构：把全部内容均分为 slide_count 页
    if not slides and lines:
        total = len(lines)
        per = max(1, round(total / slide_count))
        for i in range(0, total, per):
            chunk = lines[i:i + per]
            page_title = f"{topic}（{i // per + 1}/{max(1, (total + per - 1) // per)}）"
            slides.append(_build_slide(page_title, "", chunk))
        slides = slides[:slide_count]

    return slides


def _fallback_slides(topic: str, slide_count: int) -> list:
    """模型不可用/解析失败时的结构化兜底内容，保证前端可用"""
    sections = [
        ("{} 简介".format(topic), "Introduction", ["{} 是本节课的学习主题。".format(topic), "先了解它的定义和基本概念。", "明确学习目标：掌握核心知识并能实际运用。"]),
        ("核心概念", "Key Concepts", ["梳理与 {} 相关的关键定义与术语。".format(topic), "对比易混淆概念，建立清晰认知。", "结合例子理解抽象内容。"]),
        ("原理与方法", "Principles & Methods", ["分析 {} 背后的核心原理。".format(topic), "拆解推导或求解的一般步骤。", "总结方法与技巧，注意常见错误。"]),
        ("实际应用", "Applications", ["在生活中寻找 {} 的实际应用场景。".format(topic), "尝试用所学知识解决具体问题。", "跨学科联系，加深理解。"]),
        ("总结与练习", "Summary & Practice", ["回顾本节课核心知识点。", "完成针对性练习，检验掌握程度。", "提出疑问，带着问题进入下节课。"]),
    ]
    slides = []
    for title, subtitle, points in sections[:slide_count]:
        paras = "".join(
            f'<p style="font-size:15px;line-height:1.8;margin:4px 0;"><span style="color:var(--accent);font-weight:600;">●</span> {html.escape(p)}</p>'
            for p in points
        )
        slides.append({"title": title, "subtitle": subtitle, "content": paras, "katex": ""})
    return slides


@slides_bp.route("/api/slides/generate", methods=["POST", "OPTIONS"])
def generate_slides():
    """
    生成幻灯片端点

    请求体（JSON）:
        {
            "topic": "主题",
            "content": "内容大纲（可选）",
            "style": "default",
            "slide_count": 5
        }

    响应（JSON）:
        {
            "status": "success",
            "slides": [
                {"title": "...", "subtitle": "...", "content": "<p>...</p>", "katex": ""},
                ...
            ],
            "model_used": "lumilearn-v2:latest"
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "请求体为空"}), 400

    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "缺少 topic 字段"}), 400

    slide_count = int(data.get("slide_count") or data.get("slides_count") or 5)
    slide_count = max(3, min(slide_count, MAX_SLIDES))
    style = data.get("style", "detailed")

    provider = get_ollama_provider()
    messages = [
        {"role": "system", "content": "你是教学幻灯片生成助手，严格按指定格式输出。"},
        {"role": "user", "content": _build_prompt(topic, slide_count, style)},
    ]

    try:
        result = provider.chat_sync(
            messages, model=SLIDES_MODEL, temperature=0.7, max_tokens=2048
        )
        if "error" in result:
            logger.warning(f"幻灯片生成模型错误，使用兜底: {result['error']}")
            slides = _fallback_slides(topic, slide_count)
            model_used = "fallback"
        else:
            text = result.get("message", {}).get("content", "")
            slides = _parse_slides(text, topic, slide_count)
            model_used = result.get("model", SLIDES_MODEL)
            if not slides:
                logger.warning("幻灯片生成解析为空，使用兜底")
                slides = _fallback_slides(topic, slide_count)
                model_used = "fallback"
    except Exception as e:
        logger.error(f"幻灯片生成失败: {e}")
        slides = _fallback_slides(topic, slide_count)
        model_used = "fallback"

    return jsonify({
        "status": "success",
        "slides": slides,
        "model_used": model_used,
        "count": len(slides),
    })


@slides_bp.route("/api/slides/<slide_id>", methods=["GET", "OPTIONS"])
def get_slide(slide_id):
    """
    获取单个幻灯片
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    return jsonify({
        "status": "success",
        "slide": None
    })


@slides_bp.route("/api/slides/export", methods=["POST", "OPTIONS"])
def export_slides():
    """
    导出幻灯片

    请求体（JSON）:
        {
            "slide_ids": ["slide1", "slide2"],
            "format": "pptx/pdf"
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "请求体为空"}), 400

    # TODO: 实现导出逻辑
    return jsonify({
        "status": "success",
        "message": "导出功能开发中"
    })
