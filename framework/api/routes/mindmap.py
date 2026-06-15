# -*- coding: utf-8 -*-
"""
LumiLearn - Mind Map API 路由
提供思维导图数据生成端点

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-09
"""

import json
import logging
import sys
import re
from pathlib import Path
from flask import Blueprint, request, jsonify

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

logger = logging.getLogger("lumilearn.routes.mindmap")

mindmap_bp = Blueprint("mindmap", __name__)


def _extract_topic_keywords(topic: str, slides_content: str = "") -> list:
    """从主题和幻灯片内容中提取关键词"""
    # 尝试从 slides_content 中提取标题
    titles = re.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>', slides_content) if slides_content else []
    titles = [t.strip() for t in titles if t.strip()]

    # 尝试从内容中提取加粗文字
    bolds = re.findall(r'<strong>(.*?)</strong>', slides_content) if slides_content else []
    bolds = [b.strip() for b in bolds if b.strip() and len(b.strip()) > 2]

    # 提取所有列表项
    list_items = re.findall(r'<li>(.*?)</li>', slides_content) if slides_content else []
    list_items = [li.strip() for li in list_items if li.strip()]

    return {
        "topic": topic,
        "titles": titles[:6],
        "bold_words": list(set(bolds))[:8],
        "list_items": list_items[:10],
    }


def _build_mindmap_from_llm(topic: str, slides_content: str = "") -> dict:
    """
    尝试用 LLM 生成思维导图结构
    返回 {nodes: [...], edges: [...]}
    """
    try:
        import requests
        from smart_reply_engine import DEFAULT_API_BASE, is_gibberish

        prompt = f"""你是一位教育思维导图专家。请为主题「{topic}」生成一个层次化的思维导图结构。

幻灯片内容参考：
{slides_content[:1500] if slides_content else '无额外内容'}

请输出严格的 JSON 格式（不要包含任何其他文字），结构如下：
{{
  "nodes": [
    {{"id": "root", "label": "{topic}"}},
    {{"id": "n1", "label": "子节点标签"}},
    {{"id": "n2", "label": "子节点标签"}}
  ],
  "edges": [
    {{"from": "root", "to": "n1"}},
    {{"from": "root", "to": "n2"}}
  ]
}}

要求：
- 根节点 id 必须为 "root"，标签为主题名
- 第一层子节点 3-5 个
- 第二层子节点在每个第一层节点下 2-4 个
- 节点标签简洁（8字以内）
- 层次结构合理，由浅入深

直接输出 JSON："""

        resp = requests.post(
            f"{DEFAULT_API_BASE}/api/generate",
            json={
                "model": "lumilearn-v5",
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 2048, "temperature": 0.5}
            },
            timeout=60
        )

        if resp.status_code == 200:
            data = resp.json()
            text = data.get("response", "").strip()
            if text and not is_gibberish(text):
                # 尝试提取 JSON
                json_match = re.search(r'\{[\s\S]*\}', text)
                if json_match:
                    result = json.loads(json_match.group(0))
                    if "nodes" in result and "edges" in result:
                        return result
    except Exception as e:
        logger.warning(f"LLM 思维导图生成失败，回退到模板: {e}")

    return None


def _build_template_mindmap(topic: str, slides_content: str = "") -> dict:
    """
    基于模板生成思维导图（LLM不可用时的回退方案）
    """
    keywords = _extract_topic_keywords(topic, slides_content)

    # 第一层子节点：根据提取的内容构建
    first_level = []
    node_idx = 1

    # 添加核心概念相关节点
    first_level.append({"id": f"n{node_idx}", "label": "基本概念"})
    node_idx += 1
    first_level.append({"id": f"n{node_idx}", "label": "核心原理"})
    node_idx += 1
    first_level.append({"id": f"n{node_idx}", "label": "公式推导"})
    node_idx += 1
    first_level.append({"id": f"n{node_idx}", "label": "实际应用"})
    node_idx += 1
    first_level.append({"id": f"n{node_idx}", "label": "常见误区"})
    node_idx += 1

    nodes = [{"id": "root", "label": topic}]
    edges = []

    for parent in first_level:
        nodes.append(parent)
        edges.append({"from": "root", "to": parent["id"]})

        # 第二层子节点
        child_count = 2
        for c in range(child_count):
            child_id = f"n{node_idx}"
            child_labels = {
                "基本概念": ["定义", "背景由来"],
                "核心原理": ["关键要素", "推导逻辑"],
                "公式推导": ["符号解释", "计算示例"],
                "实际应用": ["生活案例", "工程应用"],
                "常见误区": ["易错提醒", "辨析要点"],
            }
            child_list = child_labels.get(parent["label"], ["要点一", "要点二"])
            child_label = child_list[c] if c < len(child_list) else f"子节点{c+1}"

            nodes.append({"id": child_id, "label": child_label})
            edges.append({"from": parent["id"], "to": child_id})
            node_idx += 1

    return {"nodes": nodes, "edges": edges}


@mindmap_bp.route("/api/mindmap/generate", methods=["POST", "OPTIONS"])
def mindmap_generate():
    """
    思维导图生成 API 端点

    请求体（JSON）：
        {
            "topic": "勾股定理",
            "slides_content": "幻灯片内容的文本..."
        }

    响应：
        {
            "nodes": [
                {"id": "root", "label": "勾股定理"},
                {"id": "n1", "label": "基本概念"},
                ...
            ],
            "edges": [
                {"from": "root", "to": "n1"},
                ...
            ]
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json(force=True)
    topic = data.get("topic", "")
    slides_content = data.get("slides_content", "")

    if not topic:
        return jsonify({"error": "缺少 topic 字段"}), 400

    try:
        # 1. 尝试 LLM 生成
        result = _build_mindmap_from_llm(topic, slides_content)

        # 2. LLM 不可用则回退到模板
        if result is None:
            logger.info(f"LLM 不可用，使用模板生成思维导图: {topic}")
            result = _build_template_mindmap(topic, slides_content)

        return jsonify(result)
    except Exception as e:
        logger.error(f"思维导图生成失败: {e}")
        return jsonify({"error": f"思维导图生成失败: {str(e)}"}), 500