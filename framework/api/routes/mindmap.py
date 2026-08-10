#!/usr/bin/env python3
"""
灵学 lumilearn - 思维导图 API 路由
思维导图生成端点（基于本地 Ollama 模型真实生成）
"""
import logging
import re
from flask import Blueprint, request, jsonify

from framework.models.ollama_provider import get_ollama_provider

logger = logging.getLogger("lumilearn.routes.mindmap")

mindmap_bp = Blueprint("mindmap", __name__)

MINDMAP_MODEL = "lumilearn-v2:latest"


def _build_prompt(topic: str) -> str:
    """构建思维导图生成提示词"""
    return (
        f"你是 LumiLearn 的思维导图生成助手。请为学习主题「{topic}」生成一份思维导图，"
        f"包含主题下的 3-5 个一级分支，每个一级分支下 2-3 个子分支。\n\n"
        f"必须严格按以下格式输出（用缩进表示层级，每行一个节点）：\n"
        f"MINDMAP|{topic}\n"
        f"- 一级分支1\n"
        f"  - 子分支1.1\n"
        f"  - 子分支1.2\n"
        f"- 一级分支2\n"
        f"  - 子分支2.1\n"
        f"  - 子分支2.2\n"
        f"...\n\n"
        f"不要输出任何其他文字。"
    )


def _parse_mindmap(text: str, topic: str) -> dict:
    """解析模型输出为 nodes/edges 结构"""
    nodes = [{"id": "root", "label": topic}]
    edges = []
    counter = [1]
    current_parents = {}  # 层级 -> 节点id

    def add_node(label, depth):
        nid = "n" + str(counter[0])
        counter[0] += 1
        nodes.append({"id": nid, "label": label.strip()})
        parent = current_parents.get(depth - 1, "root")
        edges.append({"from": parent, "to": nid})
        current_parents[depth] = nid

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        # 跳过格式标记行（如 MINDMAP|主题）
        if re.match(r"^MINDMAP\|", stripped, re.IGNORECASE):
            continue
        # 计算缩进层级（2 空格 = 1 级）
        indent = (len(line) - len(line.lstrip(" \t•-*")))
        depth = max(1, round(indent / 2) + (1 if indent % 2 else 0))
        label = re.sub(r"^[•\-*]\s*", "", stripped)
        if not label:
            continue
        add_node(label, depth)

    if not edges:
        # 解析失败时兜底：通用教学分支
        for i, label in enumerate(["基本概念", "核心原理", "方法步骤", "实际应用", "总结要点"]):
            nid = "n" + str(counter[0])
            counter[0] += 1
            nodes.append({"id": nid, "label": label})
            edges.append({"from": "root", "to": nid})

    return {"topic": topic, "nodes": nodes, "edges": edges}


@mindmap_bp.route("/api/mindmap/generate", methods=["POST", "OPTIONS"])
def generate_mindmap():
    """
    生成思维导图端点

    请求体（JSON）:
        {
            "topic": "主题",
            "content": "内容（可选）",
            "depth": 3
        }

    响应（JSON）:
        {
            "status": "success",
            "mindmap": {
                "topic": "主题",
                "nodes": [{"id": "root", "label": "主题"}, ...],
                "edges": [{"from": "root", "to": "n1"}, ...]
            },
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

    provider = get_ollama_provider()
    messages = [
        {"role": "system", "content": "你是思维导图生成助手，严格按指定格式输出。"},
        {"role": "user", "content": _build_prompt(topic)},
    ]

    try:
        result = provider.chat_sync(
            messages, model=MINDMAP_MODEL, temperature=0.6, max_tokens=1200
        )
        if "error" in result:
            logger.warning(f"思维导图模型错误，使用兜底: {result['error']}")
            mindmap = _parse_mindmap("", topic)
            model_used = "fallback"
        else:
            text = result.get("message", {}).get("content", "")
            mindmap = _parse_mindmap(text, topic)
            model_used = result.get("model", MINDMAP_MODEL)
    except Exception as e:
        logger.error(f"思维导图生成失败: {e}")
        mindmap = _parse_mindmap("", topic)
        model_used = "fallback"

    return jsonify({
        "status": "success",
        "mindmap": mindmap,
        "model_used": model_used,
    })


@mindmap_bp.route("/api/mindmap/<mindmap_id>", methods=["GET", "OPTIONS"])
def get_mindmap(mindmap_id):
    """
    获取思维导图
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    return jsonify({
        "status": "success",
        "mindmap": None
    })


@mindmap_bp.route("/api/mindmap/export", methods=["POST", "OPTIONS"])
def export_mindmap():
    """
    导出思维导图

    请求体（JSON）:
        {
            "mindmap_id": "mindmap_123",
            "format": "png/svg/pdf"
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
