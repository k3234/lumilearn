#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 教师端 (Teacher Portal)
====================================
独立 Flask 应用，端口 5001。
共享 lumilearn.db，教师账号登录（users 表 role=teacher）。

功能模块：
  1. 班级管理   — 学校库 / 年级库 / 班级库三级组织 + 学生入班/出班
  2. 学生管理   — 查看学生、创建学生账号、重置密码
  3. 学习监控   — 学习报告、知识掌握度、答题统计、薄弱点
  4. 任务管理   — 创建任务、分配给全班/个人、查看完成情况
  5. 教学资源   — 查看教学内容库与题目库

运行方式：
  python teacher_portal.py
  浏览器打开 http://<ip>:5001
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, session, send_file

from framework.database import db

db.init()

BASE_DIR = Path(__file__).resolve().parent
# 兼容两种部署目录：本地 remote/templates 与远程 tianhong/templates
TEMPLATE_DIR = BASE_DIR / "remote" / "templates"
if not TEMPLATE_DIR.exists():
    TEMPLATE_DIR = BASE_DIR / "tianhong" / "templates"

app = Flask(__name__)
app.secret_key = os.environ.get("TEACHER_SECRET_KEY", "lumilearn-teacher-portal-secret")


# ============================================================
# 认证辅助
# ============================================================

def _current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db.get_user(uid)


def _require_teacher():
    """校验当前会话为教师，返回 (user, error_response)"""
    user = _current_user()
    if not user:
        return None, (jsonify({"success": False, "error": "未登录，请先登录"}), 401)
    if user["role"] != "teacher":
        return None, (jsonify({"success": False, "error": "仅教师账号可访问教师端"}), 403)
    return user, None


def _class_belongs_to_teacher(class_id, teacher_id):
    """检查班级是否为该教师名下"""
    cls = db.get_class(class_id)
    return cls and cls.get("teacher_id") == teacher_id


# ============================================================
# 页面
# ============================================================

@app.route("/")
def index():
    html_path = TEMPLATE_DIR / "teacher.html"
    if html_path.exists():
        return send_file(str(html_path))
    return "<h1>LumiLearn Teacher Portal</h1><p>teacher.html not found</p>", 404


# ============================================================
# 认证 API
# ============================================================

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"success": False, "error": "请输入用户名和密码"}), 400
    user = db.verify_user_login(username, password)
    if not user:
        return jsonify({"success": False, "error": "用户名或密码错误"}), 401
    if user["role"] != "teacher":
        return jsonify({"success": False, "error": "该账号不是教师账号，请使用教师账号登录"}), 403
    session["user_id"] = user["id"]
    return jsonify({"success": True, "user": {
        "id": user["id"], "name": user["name"], "role": user["role"],
    }})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/me")
def api_me():
    user = _current_user()
    if not user:
        return jsonify({"success": False, "error": "未登录"}), 401
    return jsonify({"success": True, "user": {
        "id": user["id"], "name": user["name"], "role": user["role"],
        "username": user.get("username", ""),
    }})


# ============================================================
# 总览
# ============================================================

@app.route("/api/overview")
def api_overview():
    teacher, err = _require_teacher()
    if err:
        return err
    overview = db.get_teacher_overview(teacher["id"])
    overview["success"] = True
    return jsonify(overview)


# ============================================================
# 组织架构 API（学校/年级/班级）
# ============================================================

@app.route("/api/schools", methods=["GET"])
def api_list_schools():
    return jsonify({"success": True, "schools": db.get_schools()})


@app.route("/api/schools", methods=["POST"])
def api_create_school():
    teacher, err = _require_teacher()
    if err:
        return err
    data = request.get_json(force=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "error": "请输入学校名称"}), 400
    result = db.add_school(name, data.get("description", ""))
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 400
    return jsonify({"success": True, "school": result})


@app.route("/api/schools/<int:school_id>", methods=["DELETE"])
def api_delete_school(school_id):
    teacher, err = _require_teacher()
    if err:
        return err
    ok = db.delete_school(school_id)
    if not ok:
        return jsonify({"success": False, "error": "学校不存在"}), 404
    return jsonify({"success": True})


@app.route("/api/grades", methods=["GET"])
def api_list_grades():
    school_id = request.args.get("school_id", type=int)
    return jsonify({"success": True, "grades": db.get_grades(school_id=school_id)})


@app.route("/api/grades", methods=["POST"])
def api_create_grade():
    teacher, err = _require_teacher()
    if err:
        return err
    data = request.get_json(force=True) or {}
    school_id = data.get("school_id")
    name = data.get("name", "").strip()
    if not school_id or not name:
        return jsonify({"success": False, "error": "请选择学校并输入年级名称"}), 400
    result = db.add_grade(school_id, name)
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 400
    return jsonify({"success": True, "grade": result})


@app.route("/api/grades/<int:grade_id>", methods=["DELETE"])
def api_delete_grade(grade_id):
    teacher, err = _require_teacher()
    if err:
        return err
    ok = db.delete_grade(grade_id)
    if not ok:
        return jsonify({"success": False, "error": "年级不存在"}), 404
    return jsonify({"success": True})


@app.route("/api/classes", methods=["GET"])
def api_list_classes():
    """教师只看到自己名下的班级"""
    teacher, err = _require_teacher()
    if err:
        return err
    classes = db.get_classes(teacher_id=teacher["id"])
    return jsonify({"success": True, "classes": classes})


@app.route("/api/classes", methods=["POST"])
def api_create_class():
    teacher, err = _require_teacher()
    if err:
        return err
    data = request.get_json(force=True) or {}
    grade_id = data.get("grade_id")
    name = data.get("name", "").strip()
    if not grade_id or not name:
        return jsonify({"success": False, "error": "请选择年级并输入班级名称"}), 400
    result = db.add_class(grade_id, name, teacher_id=teacher["id"])
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 400
    return jsonify({"success": True, "class": result})


@app.route("/api/classes/<int:class_id>", methods=["DELETE"])
def api_delete_class(class_id):
    teacher, err = _require_teacher()
    if err:
        return err
    if not _class_belongs_to_teacher(class_id, teacher["id"]):
        return jsonify({"success": False, "error": "无权操作该班级"}), 403
    ok = db.delete_class(class_id)
    if not ok:
        return jsonify({"success": False, "error": "班级不存在"}), 404
    return jsonify({"success": True})


@app.route("/api/classes/<int:class_id>/students", methods=["GET"])
def api_class_students(class_id):
    teacher, err = _require_teacher()
    if err:
        return err
    if not _class_belongs_to_teacher(class_id, teacher["id"]):
        return jsonify({"success": False, "error": "无权查看该班级"}), 403
    return jsonify({"success": True, "students": db.get_class_students(class_id)})


@app.route("/api/classes/<int:class_id>/students", methods=["POST"])
def api_add_student_to_class(class_id):
    teacher, err = _require_teacher()
    if err:
        return err
    if not _class_belongs_to_teacher(class_id, teacher["id"]):
        return jsonify({"success": False, "error": "无权操作该班级"}), 403
    data = request.get_json(force=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "缺少 user_id"}), 400
    result = db.add_student_to_class(class_id, user_id)
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 400
    return jsonify({"success": True, **result})


@app.route("/api/classes/<int:class_id>/students/<int:user_id>", methods=["DELETE"])
def api_remove_student_from_class(class_id, user_id):
    teacher, err = _require_teacher()
    if err:
        return err
    if not _class_belongs_to_teacher(class_id, teacher["id"]):
        return jsonify({"success": False, "error": "无权操作该班级"}), 403
    ok = db.remove_student_from_class(class_id, user_id)
    if not ok:
        return jsonify({"success": False, "error": "该学生不在班级中"}), 404
    return jsonify({"success": True})


# ============================================================
# 学生管理 API
# ============================================================

@app.route("/api/students", methods=["GET"])
def api_list_students():
    """我的班级的学生（含所有可加入的候选学生）"""
    teacher, err = _require_teacher()
    if err:
        return err
    students = db.get_students(teacher_id=teacher["id"])
    # 候选池：所有学生中尚未在我班里的
    my_ids = {s["id"] for s in students}
    candidates = [s for s in db.get_students() if s["id"] not in my_ids]
    return jsonify({"success": True, "students": students, "candidates": candidates})


@app.route("/api/students", methods=["POST"])
def api_create_student():
    teacher, err = _require_teacher()
    if err:
        return err
    data = request.get_json(force=True) or {}
    name = data.get("name", "").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    if not name:
        return jsonify({"success": False, "error": "请输入学生姓名"}), 400
    if not password or len(password) < 4:
        return jsonify({"success": False, "error": "密码不能为空且至少4位"}), 400
    if db.get_user_by_username(username or name):
        return jsonify({"success": False, "error": f"用户名 '{username or name}' 已存在"}), 400
    user = db.add_user(name, role="student", username=username, password=password)
    return jsonify({"success": True, "user": user})


@app.route("/api/students/<int:user_id>/password", methods=["POST"])
def api_reset_student_password(user_id):
    teacher, err = _require_teacher()
    if err:
        return err
    data = request.get_json(force=True) or {}
    new_password = data.get("password", "").strip()
    if not new_password or len(new_password) < 4:
        return jsonify({"success": False, "error": "密码不能为空且至少4位"}), 400
    user = db.get_user(user_id)
    if not user:
        return jsonify({"success": False, "error": "用户不存在"}), 404
    db.update_user_password(user_id, new_password)
    return jsonify({"success": True, "message": f"学生 {user['name']} 密码已重置"})


@app.route("/api/students/<int:user_id>/reports", methods=["GET"])
def api_student_reports(user_id):
    teacher, err = _require_teacher()
    if err:
        return err
    reports = db.get_learning_reports(user_id=user_id, limit=30)
    for r in reports:
        rep = r.get("report", {})
        r["summary"] = {
            "title": rep.get("title", ""),
            "generated_at": rep.get("generated_at", ""),
            "core_topic": (rep.get("task_understanding") or {}).get("core_topic", r["topic"]),
            "subject": (rep.get("task_understanding") or {}).get("subject", ""),
            "score": (rep.get("mastery_assessment") or {}).get("score", 0),
            "level": (rep.get("mastery_assessment") or {}).get("level", ""),
        }
        r.pop("report", None)
    return jsonify({"success": True, "reports": reports})


@app.route("/api/students/<int:user_id>/report/<int:report_id>", methods=["GET"])
def api_student_report_detail(user_id, report_id):
    teacher, err = _require_teacher()
    if err:
        return err
    r = db.get_learning_report(report_id)
    if not r or r["user_id"] != user_id:
        return jsonify({"success": False, "error": "报告不存在"}), 404
    return jsonify({"success": True, "report": r})


@app.route("/api/students/<int:user_id>/progress", methods=["GET"])
def api_student_progress(user_id):
    teacher, err = _require_teacher()
    if err:
        return err
    progress = db.get_concept_progress(user_id)
    progress["success"] = True
    return jsonify(progress)


@app.route("/api/students/<int:user_id>/stats", methods=["GET"])
def api_student_stats(user_id):
    teacher, err = _require_teacher()
    if err:
        return err
    stats = db.get_stats(user_id)
    mistakes = db.get_mistakes(user_id, limit=20)
    weak = db.get_weak_topics(user_id, min_errors=1)
    stats["mistakes"] = mistakes
    stats["weak_topics"] = weak
    stats["success"] = True
    return jsonify(stats)


# ============================================================
# 推理记录 API（模型推理过程，仅限本班学生）
# ============================================================

def _visible_student_ids(teacher_id):
    """获取当前教师可见的学生 id 列表（仅自己班级的学生），失败时返回空列表"""
    try:
        students = db.get_students(teacher_id=teacher_id)
        return sorted({s["id"] for s in students})
    except Exception:
        return []


def _query_reasoning_logs_by_users(user_ids, limit=100, offset=0):
    """按学生 id 集合查询推理记录（字段与 db.get_reasoning_logs 保持一致），返回 (items, total)"""
    if not user_ids:
        return [], 0
    placeholders = ",".join("?" * len(user_ids))
    cond = f"r.user_id IN ({placeholders})"
    items = db._query(
        f"""SELECT r.*, COALESCE(u.name, '') AS student_name
            FROM reasoning_logs r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE {cond}
            ORDER BY r.created_at DESC, r.id DESC
            LIMIT ? OFFSET ?""",
        tuple(user_ids) + (limit, offset)
    )
    total = db._query_one(
        f"SELECT COUNT(*) AS n FROM reasoning_logs r WHERE {cond}",
        tuple(user_ids)
    )["n"]
    return items, total


@app.route("/api/teacher/reasoning-logs", methods=["GET"])
def api_teacher_reasoning_logs():
    """教师查看本班学生的推理记录（权限隔离：user_id 不在本班学生列表时返回空结果）"""
    teacher, err = _require_teacher()
    if err:
        return err
    user_ids = _visible_student_ids(teacher["id"])
    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 200)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        limit, offset = 50, 0
    uid = request.args.get("user_id", type=int)
    if uid is not None:
        # 权限隔离：仅可查看自己班级的学生，其余一律返回空
        if uid not in user_ids:
            return jsonify({"success": True, "items": [], "total": 0})
        user_ids = [uid]
    items, total = _query_reasoning_logs_by_users(user_ids, limit=limit, offset=offset)
    return jsonify({"success": True, "items": items, "total": total})


@app.route("/api/teacher/reasoning-logs/stats", methods=["GET"])
def api_teacher_reasoning_stats():
    """教师可见范围内（仅本班学生）的推理记录统计（db.get_reasoning_stats 不支持按学生过滤，故在 API 层聚合）"""
    teacher, err = _require_teacher()
    if err:
        return err
    user_ids = _visible_student_ids(teacher["id"])
    days = request.args.get("days", 7, type=int) or 0
    stats = {"total": 0, "by_model": {}, "by_step": {}, "avg_latency_ms": 0, "error_count": 0}
    if not user_ids:
        return jsonify({"success": True, **stats})
    placeholders = ",".join("?" * len(user_ids))
    params = list(user_ids)
    cond = f"r.user_id IN ({placeholders})"
    if days > 0:
        cond += " AND r.created_at >= datetime('now', ?)"
        params.append(f"-{days} days")
    rows = db._query(
        f"""SELECT r.mode, r.step_name, r.model_used, r.latency_ms, r.status
            FROM reasoning_logs r WHERE {cond}""",
        tuple(params)
    )
    latency_sum = 0
    for row in rows:
        model = (row.get("model_used") or "").strip()
        step = (row.get("step_name") or "").strip()
        if model:
            stats["by_model"][model] = stats["by_model"].get(model, 0) + 1
        if step:
            stats["by_step"][step] = stats["by_step"].get(step, 0) + 1
        if row.get("status") == "error":
            stats["error_count"] += 1
        latency_sum += row.get("latency_ms") or 0
    stats["total"] = len(rows)
    stats["avg_latency_ms"] = round(latency_sum / len(rows), 1) if rows else 0
    return jsonify({"success": True, **stats})


# ============================================================
# 任务管理 API
# ============================================================

@app.route("/api/tasks", methods=["GET"])
def api_list_tasks():
    teacher, err = _require_teacher()
    if err:
        return err
    tasks = db.get_tasks(limit=100)
    # 只显示自己创建的任务
    tasks = [t for t in tasks if t["created_by"] == teacher["id"]]
    for t in tasks:
        t["assignment_count"] = len(db.get_task_assignments(task_id=t["id"]))
    return jsonify({"success": True, "tasks": tasks})


@app.route("/api/tasks", methods=["POST"])
def api_create_task():
    teacher, err = _require_teacher()
    if err:
        return err
    data = request.get_json(force=True) or {}
    title = data.get("title", "").strip()
    subject = data.get("subject", "").strip()
    if not title or not subject:
        return jsonify({"success": False, "error": "请输入任务标题和学科"}), 400
    task = db.create_task(
        title=title,
        subject=subject,
        description=data.get("description", ""),
        task_type=data.get("task_type", "learn"),
        difficulty=data.get("difficulty", "基础"),
        grade=data.get("grade", "高中"),
        target_score=int(data.get("target_score", 60)),
        time_limit=int(data.get("time_limit", 30)),
        source="teacher",
        source_detail=f"教师 {teacher['name']} 创建",
        created_by=teacher["id"],
    )
    return jsonify({"success": True, "task": task})


@app.route("/api/tasks/generate", methods=["POST"])
def api_generate_task():
    """根据知识点自动生成任务"""
    teacher, err = _require_teacher()
    if err:
        return err
    data = request.get_json(force=True) or {}
    node_id = data.get("node_id", "")
    subject = data.get("subject", "")
    if not node_id:
        return jsonify({"success": False, "error": "缺少 node_id"}), 400
    result = db.generate_task_from_knowledge(node_id, subject)
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 400
    # 更新创建者为当前教师
    db.update_task(result["task_id"], source_detail=f"教师 {teacher['name']} 从知识点生成")
    return jsonify({"success": True, **result})


@app.route("/api/tasks/<int:task_id>/assign", methods=["POST"])
def api_assign_task(task_id):
    teacher, err = _require_teacher()
    if err:
        return err
    data = request.get_json(force=True) or {}
    task = db.get_task(task_id)
    if not task or task["created_by"] != teacher["id"]:
        return jsonify({"success": False, "error": "任务不存在或无权操作"}), 404
    result = {"task_id": task_id, "assigned_count": 0, "details": []}
    class_id = data.get("class_id")
    user_ids = data.get("user_ids") or []
    if class_id:
        if not _class_belongs_to_teacher(class_id, teacher["id"]):
            return jsonify({"success": False, "error": "无权操作该班级"}), 403
        res = db.assign_task_to_class(task_id, class_id)
        result["assigned_count"] += res["assigned_count"]
        result["details"].append({"mode": f"全班({class_id})", "count": res["assigned_count"]})
    for uid in user_ids:
        # 已分配过的学生跳过，避免重复计数
        if db.get_task_assignments(task_id=task_id, user_id=int(uid)):
            continue
        res = db.assign_task(task_id, int(uid))
        if res.get("assignment_id"):
            result["assigned_count"] += 1
            result["details"].append({"mode": f"个人({uid})", "count": 1})
    return jsonify({"success": True, **result})


@app.route("/api/tasks/<int:task_id>/assignments", methods=["GET"])
def api_task_assignments(task_id):
    teacher, err = _require_teacher()
    if err:
        return err
    task = db.get_task(task_id)
    if not task or task["created_by"] != teacher["id"]:
        return jsonify({"success": False, "error": "任务不存在或无权查看"}), 404
    rows = db.get_task_assignments_with_names(task_id)
    return jsonify({"success": True, "assignments": rows})


# ============================================================
# 教学资源 API
# ============================================================

@app.route("/api/resources", methods=["GET"])
def api_resources():
    teacher, err = _require_teacher()
    if err:
        return err
    subject = request.args.get("subject")
    limit = int(request.args.get("limit", 50))
    contents = db.get_training_data(subject=subject, status="published", limit=limit)
    for c in contents:
        c.pop("content", None)  # 列表页不返回大段正文
    return jsonify({"success": True, "resources": contents})


@app.route("/api/resources/<int:record_id>", methods=["GET"])
def api_resource_detail(record_id):
    teacher, err = _require_teacher()
    if err:
        return err
    rec = db.get_training_record(record_id)
    if not rec:
        return jsonify({"success": False, "error": "资源不存在"}), 404
    return jsonify({"success": True, "resource": rec})


@app.route("/api/questions", methods=["GET"])
def api_questions():
    teacher, err = _require_teacher()
    if err:
        return err
    subject = request.args.get("subject")
    questions = db.get_questions(subject=subject, limit=50)
    return jsonify({"success": True, "questions": questions})


@app.route("/api/knowledge-nodes", methods=["GET"])
def api_knowledge_nodes():
    teacher, err = _require_teacher()
    if err:
        return err
    nodes = db.get_knowledge_nodes()
    return jsonify({"success": True, "nodes": nodes})


# ============================================================
# 学习数据分析（仅本班学生范围，纯 SVG 图表数据源）
# ============================================================

def _visible_student_ids_safe(teacher_id):
    """获取教师可见学生 id 列表（仅本班），失败返回空"""
    try:
        return _visible_student_ids(teacher_id)
    except Exception:
        return []


@app.route("/api/analytics/overview")
def api_analytics_overview():
    """本班学生总量概览"""
    teacher, err = _require_teacher()
    if err:
        return err
    user_ids = _visible_student_ids_safe(teacher["id"])
    return jsonify({"success": True, "data": db.get_analytics_overview(user_ids or None)})


@app.route("/api/analytics/trend")
def api_analytics_trend():
    """本班学生掌握度趋势"""
    teacher, err = _require_teacher()
    if err:
        return err
    user_ids = _visible_student_ids_safe(teacher["id"])
    limit = min(int(request.args.get("limit", 14)), 90)
    return jsonify({"success": True, "data": db.get_analytics_trend(user_ids or None, limit=limit)})


@app.route("/api/analytics/subjects")
def api_analytics_subjects():
    """本班学生学科掌握度"""
    teacher, err = _require_teacher()
    if err:
        return err
    user_ids = _visible_student_ids_safe(teacher["id"])
    return jsonify({"success": True, "data": db.get_analytics_subjects(user_ids or None)})


@app.route("/api/analytics/weakpoints")
def api_analytics_weakpoints():
    """本班学生薄弱点排行"""
    teacher, err = _require_teacher()
    if err:
        return err
    user_ids = _visible_student_ids_safe(teacher["id"])
    limit = min(int(request.args.get("limit", 8)), 30)
    return jsonify({"success": True, "data": db.get_analytics_weakpoints(user_ids or None, limit=limit)})


@app.route("/api/analytics/concepts")
def api_analytics_concepts():
    """本班学生知识点掌握度"""
    teacher, err = _require_teacher()
    if err:
        return err
    user_ids = _visible_student_ids_safe(teacher["id"])
    limit = min(int(request.args.get("limit", 24)), 60)
    return jsonify({"success": True, "data": db.get_analytics_concepts(user_ids or None, limit=limit)})


@app.route("/api/analytics/users")
def api_analytics_users():
    """本班学生个体排行"""
    teacher, err = _require_teacher()
    if err:
        return err
    user_ids = _visible_student_ids_safe(teacher["id"])
    return jsonify({"success": True, "data": db.get_analytics_users(user_ids or None)})


@app.route("/api/analytics/reasoning")
def api_analytics_reasoning():
    """本班学生模型推理统计"""
    teacher, err = _require_teacher()
    if err:
        return err
    user_ids = _visible_student_ids_safe(teacher["id"])
    days = int(request.args.get("days", 7))
    return jsonify({"success": True, "data": db.get_analytics_reasoning(user_ids or None, days=days)})


# ============================================================
# 数据合规导出（教师申请 → 管理员审批 → 下载）
# ============================================================

@app.route("/api/exports", methods=["GET"])
def api_my_exports():
    """我的导出申请列表"""
    teacher, err = _require_teacher()
    if err:
        return err
    exports = db.list_data_exports(requester_id=teacher["id"], requester_type="teacher", limit=50)
    for e in exports:
        e["can_download"] = bool(e["status"] == "approved" and e.get("file_path"))
    return jsonify({"success": True, "exports": exports})


@app.route("/api/exports", methods=["POST"])
def api_request_export():
    """教师发起导出申请（数据范围=本班，需管理员审批）"""
    teacher, err = _require_teacher()
    if err:
        return err
    data = request.get_json(force=True) or {}
    export_type = data.get("export_type", "")
    fmt = data.get("format", "json")
    class_id = int(data.get("class_id") or 0)
    if export_type not in ("reports", "reasoning", "answers", "users", "concepts"):
        return jsonify({"success": False, "error": "不支持的导出类型"}), 400
    if fmt not in ("json", "csv"):
        return jsonify({"success": False, "error": "格式只能是 json 或 csv"}), 400
    if class_id and not _class_belongs_to_teacher(class_id, teacher["id"]):
        return jsonify({"success": False, "error": "无权导出该班级数据"}), 403
    rec = db.add_data_export(
        requester_id=teacher["id"], requester_type="teacher",
        requester_name=teacher["name"],
        export_type=export_type, format=fmt,
        scope="class" if class_id else "all", class_id=class_id,
        reason=data.get("reason", ""))
    return jsonify({"success": True, "export_id": rec["id"],
                    "message": "导出申请已提交，等待管理员审批"})


@app.route("/api/exports/<int:export_id>/download")
def api_download_export(export_id):
    """下载已批准的导出文件（仅限本人申请）"""
    from flask import send_from_directory
    teacher, err = _require_teacher()
    if err:
        return err
    exp = db.get_data_export(export_id)
    if not exp:
        return jsonify({"success": False, "error": "导出申请不存在"}), 404
    # 权限校验：仅本人可下载
    if exp["requester_id"] != teacher["id"] or exp["requester_type"] != "teacher":
        return jsonify({"success": False, "error": "无权下载该导出文件"}), 403
    if exp["status"] != "approved" or not exp.get("file_path"):
        return jsonify({"success": False, "error": "该导出尚未批准或文件不存在"}), 400
    export_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "export_data")
    fpath = os.path.join(export_dir, exp["file_path"])
    if not os.path.isfile(fpath):
        return jsonify({"success": False, "error": "导出文件已不存在"}), 404
    db.add_system_log("info", "export", f"教师下载导出文件 #{export_id} ({exp['file_path']})")
    return send_from_directory(export_dir, exp["file_path"], as_attachment=True)


# ============================================================
# 启动
# ============================================================

def _get_teacher_port() -> int:
    """从 port_settings 读取教师端端口（可被环境变量覆盖）"""
    env_port = os.environ.get("TEACHER_PORT", "")
    if env_port.isdigit():
        return int(env_port)
    try:
        from framework.services.provider_service import get_provider_service
        cfg = get_provider_service().get_port_settings().get("teacher_portal", {})
        if cfg.get("port"):
            return int(cfg["port"])
    except Exception:
        pass
    return 5001


def main():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"

    port = _get_teacher_port()
    print("\n" + "=" * 60)
    print("  🧑‍🏫 LumiLearn 教师端 (Teacher Portal)")
    print("=" * 60)
    print(f"  📍 访问地址: http://{ip}:{port}")
    print("  👤 登录账号: users 表中 role=teacher 的用户（如 123）")
    print("  💾 共享数据库: " + db.db_path)
    print("=" * 60 + "\n")

    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
