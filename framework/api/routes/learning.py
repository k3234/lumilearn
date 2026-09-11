# -*- coding: utf-8 -*-
"""
L4 学习 API 路由 — BKT 知识追踪 + 自适应学习路径
提供学生模型、知识点图谱、答题提交、学习路径等核心端点

端点：
    GET  /api/learn/knowledge-graph        知识图谱（节点 + 边）
    GET  /api/learn/node/<node_id>         知识点详情
    GET  /api/learn/student/<sid>/status   学生整体状态
    GET  /api/learn/student/<sid>/node/<nid>  单知识点状态
    POST /api/learn/student/<sid>/attempt  提交答题（触发 BKT 更新）
    GET  /api/learn/student/<sid>/path     生成学习路径
    POST /api/learn/student/<sid>/reset    重置知识点追踪
    GET  /api/learn/student/<sid>/path/practice  生成练习题集

作者：lumilearn AI自动化专家
日期：2026-09-07
"""

import logging
import time
from functools import wraps

from flask import Blueprint, jsonify, request

from framework.services.adaptive_learning import (
    AdaptiveLearningEngine,
    KNOWLEDGE_GRAPH,
    get_adaptive_engine,
)
from framework.services.bkt_student_model import (
    StudentModel,
    get_student,
    clear_student_cache,
)
from framework.services.learning_path import (
    AdaptivePathEngine,
    get_path_engine,
)

logger = logging.getLogger("lumilearn.routes.learning")

learn_bp = Blueprint("learning", __name__, url_prefix="/api/learn")


# ============================================================
# 访问守卫（安全修复）
# ============================================================
def _student_guard(student_id):
    """BKT 学生数据访问守卫。

    - 未登录 → 401
    - 学生角色只能访问自己的数据 → 越权 403
    - 教师 / 管理员可访问任意学生（便于教学与学情分析）
    返回 None 表示放行，否则返回 (response, status_code)。
    """
    try:
        from framework.api.routes.auth import current_user
        user = current_user()
    except Exception:
        user = None
    if not user:
        return jsonify({"code": 401, "message": "未登录"}), 401
    role = user.get("role", "user")
    if role in ("teacher", "admin", "super_admin"):
        return None
    if str(user.get("id")) != str(student_id):
        return jsonify({"code": 403, "message": "无权访问其他学生的数据"}), 403
    return None


def require_student_access(fn):
    """路由装饰器：对 /student/<student_id>/* 统一做登录 + 越权校验。"""
    @wraps(fn)
    def wrapper(student_id, *args, **kwargs):
        guarded = _student_guard(student_id)
        if guarded:
            return guarded
        return fn(student_id, *args, **kwargs)
    return wrapper


# ============================================================
# 知识图谱
# ============================================================
@learn_bp.route("/knowledge-graph", methods=["GET"])
def knowledge_graph():
    """
    获取完整知识图谱（节点 + 边）

    响应：
    {
      "nodes": [{"id", "name", "category", "difficulty", "animation_type", "description", "common_mistakes"}],
      "edges": [{"from": "node_id", "to": "node_id"}],
      "categories": ["geometry", "algebra", ...]
    }
    """
    engine = get_adaptive_engine()
    graph = engine.get_knowledge_graph()
    return jsonify({"code": 0, "data": graph})


@learn_bp.route("/node/<node_id>", methods=["GET"])
def node_detail(node_id: str):
    """
    获取单个知识点详情

    响应：
    {
      "id": "pythagorean",
      "name": "勾股定理",
      "category": "geometry",
      "difficulty": 2,
      "description": "...",
      "common_mistakes": [...],
      "prerequisites": [{"id", "name"}],
      "dependents": [{"id", "name"}]
    }
    """
    engine = get_adaptive_engine()
    detail = engine.get_node_detail(node_id)
    if not detail:
        return jsonify({"code": 404, "message": f"知识点 {node_id} 不存在"}), 404
    return jsonify({"code": 0, "data": detail})


# ============================================================
# 学生状态
# ============================================================
@learn_bp.route("/student/<student_id>/status", methods=["GET"])
@require_student_access
def student_status(student_id: str):
    """
    获取学生整体学习状态（BKT 汇总）

    参数：
        student_id: 学生唯一标识（如 "user_123" 或 "demo"）

    响应：
    {
      "student_id": "demo",
      "total_knowledge_nodes": 50,
      "mastered_nodes": 12,
      "learning_nodes": 8,
      "not_started": 30,
      "overall_mastery": 0.35,
      "total_attempts": 45,
      "overall_accuracy": 0.72,
      "cognitive_state": {"state": "fluent", "confidence": 0.65, ...},
      "last_updated": 1725000000.0
    }
    """
    student = get_student(student_id)
    summary = student.get_summary()
    return jsonify({"code": 0, "data": summary})


@learn_bp.route("/student/<student_id>/node/<node_id>", methods=["GET"])
@require_student_access
def student_node_status(student_id: str, node_id: str):
    """
    获取学生对单个知识点的 BKT 追踪状态

    响应：
    {
      "node_id": "pythagorean",
      "p": 0.72,
      "prev_p": 0.55,
      "p_change": 0.17,
      "total_correct": 8,
      "total_wrong": 3,
      "total_attempts": 11,
      "accuracy": 0.73,
      "predicted_accuracy": 0.78,
      "cognitive_state": {...},
      "recent_history": [{"correct": true, "p_before": 0.55, "p_after": 0.72, ...}]
    }
    """
    student = get_student(student_id)
    detail = student.get_node_detail(node_id)
    if not detail:
        return jsonify({"code": 404, "message": f"学生 {student_id} 尚无 {node_id} 的学习记录"}), 404
    return jsonify({"code": 0, "data": detail})


# ============================================================
# 提交答题（BKT 核心入口）
# ============================================================
@learn_bp.route("/student/<student_id>/attempt", methods=["POST"])
@require_student_access
def submit_attempt(student_id: str):
    """
    提交一次答题结果，触发 BKT 更新

    请求体：
    {
      "node_id": "pythagorean",
      "correct": true,
      "time_spent": 45.2,
      "question_type": "multiple_choice"
    }

    响应：
    {
      "node_id": "pythagorean",
      "p": 0.72,
      "p_change": 0.17,
      "correct": true,
      "guess": 0.1,
      "slip": 0.1,
      "learn": 0.2,
      "cognitive_state": {"state": "fluent", ...},
      "predicted_accuracy": 0.78
    }
    """
    data = request.get_json(force=True) or {}
    node_id = (data.get("node_id") or "").strip()
    correct = bool(data.get("correct", False))
    time_spent = float(data.get("time_spent") or 0)
    question_type = (data.get("question_type") or "").strip()

    if not node_id:
        return jsonify({"code": 400, "message": "缺少 node_id"}), 400

    if node_id not in KNOWLEDGE_GRAPH:
        return jsonify({"code": 400, "message": f"未知的知识点: {node_id}"}), 400

    student = get_student(student_id)
    result = student.record_attempt(
        node_id=node_id,
        correct=correct,
        time_spent=time_spent,
        question_type=question_type,
    )
    return jsonify({"code": 0, "data": result})


# ============================================================
# 学习路径
# ============================================================
@learn_bp.route("/student/<student_id>/path", methods=["GET"])
@require_student_access
def learning_path(student_id: str):
    """
    生成个性化学习路径

    参数：
        student_id: 学生标识
        target: 目标知识点 ID（可选，不填则自动选择最薄弱环节）
        max_steps: 路径最大步数（默认 10）

    响应：
    {
      "student_id": "demo",
      "path": [
        {
          "node_id": "triangle_basics",
          "name": "三角形基础",
          "category": "geometry",
          "difficulty": 1,
          "mastery": 0.15,
          "reason": "全新知识点...",
          "estimated_time_min": 8,
          "action": "explain",
          "animation_type": "geometry"
        },
        ...
      ],
      "total_steps": 5
    }
    """
    engine = get_path_engine()
    target = request.args.get("target", "").strip() or None
    max_steps = int(request.args.get("max_steps", 10))

    path = engine.get_learning_path(
        student_id=student_id,
        target_node_id=target,
        max_steps=max_steps,
    )

    return jsonify({
        "code": 0,
        "data": {
            "student_id": student_id,
            "path": path,
            "total_steps": len(path),
        }
    })


@learn_bp.route("/student/<student_id>/path/practice", methods=["POST"])
@require_student_access
def practice_set(student_id: str):
    """
    为指定知识点生成练习题集

    请求体：
    {
      "node_id": "pythagorean",
      "count": 5
    }

    响应：
    {
      "node_id": "pythagorean",
      "questions": [
        {"question_id": "...", "difficulty": 2, "hint_mode": "medium", ...}
      ],
      "mastery": 0.72,
      "cognitive_state": {"state": "fluent", ...}
    }
    """
    data = request.get_json(force=True) or {}
    node_id = (data.get("node_id") or "").strip()
    count = min(int(data.get("count") or 5), 10)

    if not node_id:
        return jsonify({"code": 400, "message": "缺少 node_id"}), 400

    if node_id not in KNOWLEDGE_GRAPH:
        return jsonify({"code": 400, "message": f"未知的知识点: {node_id}"}), 400

    engine = get_path_engine()
    student = get_student(student_id)
    questions = engine.generate_practice_set(student_id, node_id, count=count)

    return jsonify({
        "code": 0,
        "data": {
            "node_id": node_id,
            "node_name": KNOWLEDGE_GRAPH[node_id].name,
            "mastery": round(student.get_mastery(node_id), 3),
            "cognitive_state": student.get_cognitive_state(),
            "questions": questions,
        }
    })


# ============================================================
# 重置
# ============================================================
@learn_bp.route("/student/<student_id>/reset", methods=["POST"])
@require_student_access
def reset_student(student_id: str):
    """
    重置学生追踪状态（教师操作）

    请求体：
    {
      "node_id": "pythagorean"   // 可选，不填则重置全部
    }
    """
    data = request.get_json(force=True) or {}
    node_id = (data.get("node_id") or "").strip()

    student = get_student(student_id)
    if node_id:
        if node_id in KNOWLEDGE_GRAPH:
            student.reset_node(node_id)
            return jsonify({"code": 0, "data": {"reset": node_id, "message": "已重置"}})
        return jsonify({"code": 400, "message": f"未知的知识点: {node_id}"}), 400
    else:
        clear_student_cache(student_id)
        return jsonify({"code": 0, "data": {"message": f"学生 {student_id} 所有追踪已重置"}})


# ============================================================
# 批量答题（教师端：一次性提交一组答案）
# ============================================================
@learn_bp.route("/student/<student_id>/batch", methods=["POST"])
@require_student_access
def batch_attempt(student_id: str):
    """
    批量提交答题结果（教师端使用）

    请求体：
    {
      "attempts": [
        {"node_id": "pythagorean", "correct": true, "time_spent": 30},
        {"node_id": "quadratic_formula", "correct": false, "time_spent": 60}
      ]
    }

    响应：
    {
      "results": [
        {"node_id": "pythagorean", "p": 0.72, "p_change": 0.17, ...},
        ...
      ],
      "summary": {"total": 2, "correct": 1, "new_mastery": 0.45}
    }
    """
    data = request.get_json(force=True) or {}
    attempts = data.get("attempts", [])

    if not attempts or not isinstance(attempts, list):
        return jsonify({"code": 400, "message": "attempts 必须是数组"}), 400

    student = get_student(student_id)
    results = []
    valid_count = 0

    for i, item in enumerate(attempts):
        node_id = (item.get("node_id") or "").strip()
        if node_id not in KNOWLEDGE_GRAPH:
            results.append({"node_id": node_id, "error": f"未知知识点: {node_id}"})
            continue
        result = student.record_attempt(
            node_id=node_id,
            correct=bool(item.get("correct", False)),
            time_spent=float(item.get("time_spent") or 0),
            question_type=(item.get("question_type") or "").strip(),
        )
        results.append(result)
        valid_count += 1

    summary = student.get_summary()
    return jsonify({
        "code": 0,
        "data": {
            "results": results,
            "summary": {
                "total": len(attempts),
                "valid": valid_count,
                "correct_count": sum(1 for r in results if r.get("correct")),
                "overall_mastery": summary.get("overall_mastery", 0),
            }
        }
    })
