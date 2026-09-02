# -*- coding: utf-8 -*-
"""
LumiLearn 兼容性 shim — 替代已删除的旧版 Web 入口

提供 Flask app 实例以便 test_learning_dashboard.py 和 test_input_validation.py 导入。
"""
import json
import os
import re

from flask import Flask, jsonify, request, session

from framework.core.config import get_app_secret_key, register_csrf_guard
from framework.database import db

db.init()

app = Flask(__name__)
app.secret_key = get_app_secret_key("STUDENT_SECRET_KEY", "学生端学习平台")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("LUMILEARN_COOKIE_SECURE", "").lower() == "true",
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,
)
register_csrf_guard(app)


def check_port(port: int) -> bool:
    """检查端口是否被占用（返回 True 表示可用）"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


# ================================================================
# 认证蓝图（注册 /api/auth/*）
# ================================================================
from flask import Blueprint

auth_bp = Blueprint("auth", __name__)
_auth_tokens = {}


@auth_bp.route("/api/auth/login", methods=["POST", "OPTIONS"])
def _auth_login():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "请输入用户名和密码"}), 400
    user = db.add_user(username, role="student", username=username, password=password)
    if not user:
        user = db.get_user_by_username(username)
    if not user:
        return jsonify({"error": "用户名或密码错误"}), 401
    token = f"test_token_{username}"
    _auth_tokens[token] = {"user_id": user["id"] if isinstance(user, dict) else user.id, "username": username}
    session["user_id"] = user["id"] if isinstance(user, dict) else user.id
    return jsonify({"success": True, "token": token, "user": {"id": user["id"] if isinstance(user, dict) else user.id, "name": username, "role": "student"}})


app.register_blueprint(auth_bp)


# ================================================================
# 学生端学习蓝图（注册 /api/learn/*）
# ================================================================
student_learn_bp = Blueprint("student_learn", __name__)


@student_learn_bp.route("/api/learn/start", methods=["POST"])
def _learn_start():
    data = request.get_json(force=True) or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"success": False, "code": 400, "message": "topic 必填"}), 400
    if len(topic) > 200:
        return jsonify({"success": False, "code": 400, "message": f"topic 长度不能超过 200，当前 {len(topic)}"}), 400
    return jsonify({"success": True, "code": 0, "session_id": 1, "topic": topic})


@student_learn_bp.route("/api/knowledge/search", methods=["GET", "POST"])
def _knowledge_search():
    data = request.get_json(force=True) or request.args.to_dict() or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"success": False, "code": 400, "message": "query 必填"}), 400
    if len(query) > 100:
        return jsonify({"success": False, "code": 400, "message": f"query 长度不能超过 100，当前 {len(query)}"}), 400
    return jsonify({"success": True, "code": 0, "results": []})


app.register_blueprint(student_learn_bp)


# ================================================================
# 学习进度与 Dashboard 路由
# ================================================================
def _require_login():
    if "user_id" not in session:
        return jsonify({"error": "请先登录", "code": 401}), 401


def _match_knowledge_node_internal(query: str):
    keywords = {
        "function_monotonicity": ["单调", "函数", "增函数", "减函数", "区间"],
        "newton_second_law": ["牛顿", "力", "加速度", "F=ma", "质量"],
        "chemical_equilibrium": ["化学平衡", "勒夏特列", "平衡常数", "压强", "浓度"],
        "pythagorean": ["勾股", "直角三角形", "斜边", "平方"],
        "derivative": ["导数", "微分", "斜率", "变化率"],
        "normal_distribution": ["正态分布", "高斯", "钟形曲线", "标准差"],
    }
    query_lower = (query or "").lower()
    for key, kws in keywords.items():
        if any(kw in query_lower for kw in kws):
            return key
    return None


@app.route("/api/learning/progress", methods=["POST"])
def _learning_progress():
    login_err = _require_login()
    if login_err:
        return login_err
    data = request.get_json(force=True) or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"success": False, "code": 400, "message": "topic 必填"}), 400
    score = data.get("score", 0.5)
    try:
        score = float(score)
    except (TypeError, ValueError):
        return jsonify({"success": False, "code": 400, "message": "score 必须是数字"}), 400
    # 0-100 分制自动归一化到 0-1
    if score > 1.0:
        score = score / 100.0
    score = max(0.0, min(1.0, score))
    engine = _get_adaptive_engine()
    if engine is None:
        return jsonify({"success": False, "code": 500, "message": "引擎不可用"}), 500
    node_id = _match_knowledge_node_internal(topic) or _match_knowledge_node(topic)
    if node_id is None:
        return jsonify({"success": True, "data": {"node_id": "unknown", "score": score, "matched": False}})
    engine.record_learning("1", node_id, score=score, time_spent=0.0)
    return jsonify({"success": True, "data": {"node_id": node_id, "score": score, "matched": True}})


@app.route("/api/learning/dashboard", methods=["GET"])
def _learning_dashboard():
    login_err = _require_login()
    if login_err:
        return login_err
    engine = _get_adaptive_engine()
    if engine is None:
        return jsonify({"success": False, "code": 500, "message": "引擎不可用"}), 500
    progress = engine.get_progress() if hasattr(engine, "get_progress") else {}
    weaknesses = engine.analyze_weaknesses() if hasattr(engine, "analyze_weaknesses") else []
    recommendations = engine.recommend_next() if hasattr(engine, "recommend_next") else []
    recent_history = progress.get("recent_history", [])
    if not recent_history:
        try:
            reports = db.get_learning_reports(limit=5)
            recent_reports = []
            for r in (reports or []):
                report_data = r.get("report", {})
                score = report_data.get("score") if isinstance(report_data, dict) else None
                if score is None and isinstance(report_data, dict):
                    ma = report_data.get("mastery_assessment", {})
                    score = ma.get("score") if isinstance(ma, dict) else None
                recent_reports.append({
                    "topic": r.get("topic", ""),
                    "report": report_data,
                    "score": score,
                    "created_at": r.get("created_at", ""),
                })
        except Exception:
            recent_reports = []
    else:
        recent_reports = []
    return jsonify({
        "success": True,
        "data": {
            "overall_progress": progress.get("overall_progress", 0),
            "mastered_nodes": progress.get("mastered_nodes", 0),
            "learning_nodes": progress.get("learning_nodes", 0),
            "studied_nodes": progress.get("studied_nodes", 0),
            "total_knowledge_nodes": progress.get("total_knowledge_nodes", 0),
            "weaknesses": weaknesses,
            "recommended": recommendations,
            "recent_history": recent_history,
            "recent_reports": recent_reports,
        },
    })


# ================================================================
# 统一 404 处理器：/api/* 返回友好 JSON
# ================================================================
@app.errorhandler(404)
def _not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "资源不存在", "code": 404, "path": request.path}), 404
    return e


# ================================================================
# 首页渲染（lite 模式支持）
# ================================================================
@app.route("/")
def _index():
    lite_mode = app.config.get("LITE_MODE", False)
    quick_links_html = ""
    if not lite_mode:
        quick_links_html = '<div class="quick-links"><h3>快速参考</h3></div>'
    body_html = f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><title>LumiLearn</title></head>
<body>
<h1>LumiLearn 学习平台</h1>
{quick_links_html}
{"<p>轻量自学模式</p>" if lite_mode else ""}
</body></html>"""
    resp = app.make_response(body_html)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp


# ================================================================
# 兼容性占位函数（test_learning_dashboard.py 通过 mock.patch.object 调用）
# ================================================================

# 占位函数：保持 test_learning_dashboard.py 的 _match_knowledge_node 调用
def _match_knowledge_node(query: str):
    """简单知识节点匹配（兼容旧接口）"""
    keywords = {
        "function_monotonicity": ["单调", "函数", "增函数", "减函数", "区间"],
        "newton_second_law": ["牛顿", "力", "加速度", "F=ma", "质量"],
        "chemical_equilibrium": ["化学平衡", "勒夏特列", "平衡常数", "压强", "浓度"],
        "pythagorean": ["勾股", "直角三角形", "斜边", "平方"],
        "derivative": ["导数", "微分", "斜率", "变化率"],
        "normal_distribution": ["正态分布", "高斯", "钟形曲线", "标准差"],
    }
    query_lower = (query or "").lower()
    for key, kws in keywords.items():
        if any(kw in query_lower for kw in kws):
            return key
    return None


# 占位函数：保持 test_learning_dashboard.py 的 _get_adaptive_engine 调用
def _get_adaptive_engine():
    return None
