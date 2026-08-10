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
TEMPLATE_DIR = BASE_DIR / "remote" / "templates"

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
