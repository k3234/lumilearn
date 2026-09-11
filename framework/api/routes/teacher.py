# -*- coding: utf-8 -*-
"""
LumiLearn 教师端 Blueprint（Teacher Portal）
============================================
将原独立 teacher_portal.py 的路由抽为可复用 Blueprint，供：
- 统一管理门户 server.py 注册（与框架 API 同端口，经账号登录）
- 原 teacher_portal.py 独立运行时的 main() 兜底

认证契约（与原 teacher_portal.py 完全一致）：
    POST /api/login  {username,password} → {success,user}（cookie 会话，role=teacher）
    GET  /api/me · POST /api/logout
权限：所有写操作均 require teacher 角色；资源仅限本人名下班级。
"""
import os
from pathlib import Path

from flask import Blueprint, jsonify, request, send_from_directory, session

from framework.database import db

# 项目根目录（framework/api/routes -> parents[3] = 项目根）
BASE_DIR = Path(__file__).resolve().parents[3]

# ── 学情驱动备课辅助 ──
# 薄弱知识点聚合：按班级（class_students 关联）统计 mastery<0.6 的知识点
_WEAK_SQL = (
    "SELECT p.node_id AS node_id, AVG(p.mastery) AS avg_mastery, "
    "       COUNT(DISTINCT p.user_id) AS students "
    "FROM progress p "
    "JOIN class_students cs ON cs.user_id = p.user_id "
    "WHERE cs.class_id = ? AND p.mastery < 0.6 "
    "GROUP BY p.node_id ORDER BY avg_mastery ASC LIMIT 20"
)
_WEAK_SQL_ALL = (
    "SELECT p.node_id AS node_id, AVG(p.mastery) AS avg_mastery, "
    "       COUNT(DISTINCT p.user_id) AS students "
    "FROM progress p "
    "WHERE p.mastery < 0.6 "
    "GROUP BY p.node_id ORDER BY avg_mastery ASC LIMIT 20"
)


class _BytesReader:
    """内存字节流只读包装（兼容 file_stream.read）。"""

    def __init__(self, data):
        self._data = data

    def read(self, *args):
        if args:
            return self._data[:args[0]]
        return self._data


def _rows_safe(db, sql, args):
    try:
        return [dict(r) for r in db.conn.execute(sql, args).fetchall()]
    except Exception:
        return []


def _classes_safe(db, teacher_id):
    try:
        rows = [dict(r) for r in db.conn.execute(
            "SELECT id, name FROM classes WHERE teacher_id = ? ORDER BY id", (teacher_id,)).fetchall()]
    except Exception:
        rows = []
    if rows:
        return rows
    # 无专属班级时返回全校班级兜底（只读备课不建议绑定班主任，尽量宽松）
    try:
        return [dict(r) for r in db.conn.execute(
            "SELECT id, name FROM classes ORDER BY id LIMIT 200").fetchall()]
    except Exception:
        return []


def create_teacher_portal_bp() -> Blueprint:
    """创建教师端 Blueprint（不注册页面路由，页面由统一门户 server.py 提供）。"""
    bp = Blueprint("teacher_portal", __name__)

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
    # 认证 API
    # ============================================================
    @bp.route("/api/login", methods=["POST"])
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
        session["role"] = user["role"]
        return jsonify({"success": True, "user": {
            "id": user["id"], "name": user["name"], "role": user["role"],
        }})

    @bp.route("/api/logout", methods=["POST"])
    def api_logout():
        session.clear()
        return jsonify({"success": True})

    @bp.route("/api/me")
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
    @bp.route("/api/overview")
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
    @bp.route("/api/schools", methods=["GET"])
    def api_list_schools():
        return jsonify({"success": True, "schools": db.get_schools()})

    @bp.route("/api/schools", methods=["POST"])
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

    @bp.route("/api/schools/<int:school_id>", methods=["DELETE"])
    def api_delete_school(school_id):
        teacher, err = _require_teacher()
        if err:
            return err
        ok = db.delete_school(school_id)
        if not ok:
            return jsonify({"success": False, "error": "学校不存在"}), 404
        return jsonify({"success": True})

    @bp.route("/api/grades", methods=["GET"])
    def api_list_grades():
        school_id = request.args.get("school_id", type=int)
        return jsonify({"success": True, "grades": db.get_grades(school_id=school_id)})

    @bp.route("/api/grades", methods=["POST"])
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

    @bp.route("/api/grades/<int:grade_id>", methods=["DELETE"])
    def api_delete_grade(grade_id):
        teacher, err = _require_teacher()
        if err:
            return err
        ok = db.delete_grade(grade_id)
        if not ok:
            return jsonify({"success": False, "error": "年级不存在"}), 404
        return jsonify({"success": True})

    @bp.route("/api/classes", methods=["GET"])
    def api_list_classes():
        """教师只看到自己名下的班级"""
        teacher, err = _require_teacher()
        if err:
            return err
        classes = db.get_classes(teacher_id=teacher["id"])
        return jsonify({"success": True, "classes": classes})

    @bp.route("/api/classes", methods=["POST"])
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

    @bp.route("/api/classes/<int:class_id>", methods=["DELETE"])
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

    @bp.route("/api/classes/<int:class_id>/students", methods=["GET"])
    def api_class_students(class_id):
        teacher, err = _require_teacher()
        if err:
            return err
        if not _class_belongs_to_teacher(class_id, teacher["id"]):
            return jsonify({"success": False, "error": "无权查看该班级"}), 403
        return jsonify({"success": True, "students": db.get_class_students(class_id)})

    @bp.route("/api/classes/<int:class_id>/students", methods=["POST"])
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

    @bp.route("/api/classes/<int:class_id>/students/<int:user_id>", methods=["DELETE"])
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
    @bp.route("/api/students", methods=["GET"])
    def api_list_students():
        """我的班级的学生（含所有可加入的候选学生）"""
        teacher, err = _require_teacher()
        if err:
            return err
        students = db.get_students(teacher_id=teacher["id"])
        my_ids = {s["id"] for s in students}
        candidates = [s for s in db.get_students() if s["id"] not in my_ids]
        return jsonify({"success": True, "students": students, "candidates": candidates})

    @bp.route("/api/students", methods=["POST"])
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
        if not password or len(password) < 8:
            return jsonify({"success": False, "error": "密码不能为空且至少8位"}), 400
        if not any(c.isupper() for c in password) or not any(c.isdigit() for c in password):
            return jsonify({"success": False, "error": "密码需包含大写字母和数字"}), 400
        if db.get_user_by_username(username or name):
            return jsonify({"success": False, "error": f"用户名 '{username or name}' 已存在"}), 400
        user = db.add_user(name, role="student", username=username, password=password)
        return jsonify({"success": True, "user": user})

    @bp.route("/api/students/<int:user_id>/password", methods=["POST"])
    def api_reset_student_password(user_id):
        teacher, err = _require_teacher()
        if err:
            return err
        data = request.get_json(force=True) or {}
        new_password = data.get("password", "").strip()
        if not new_password or len(new_password) < 8:
            return jsonify({"success": False, "error": "密码不能为空且至少8位"}), 400
        if not any(c.isupper() for c in new_password) or not any(c.isdigit() for c in new_password):
            return jsonify({"success": False, "error": "密码需包含大写字母和数字"}), 400
        user = db.get_user(user_id)
        if not user:
            return jsonify({"success": False, "error": "用户不存在"}), 404
        db.update_user_password(user_id, new_password)
        return jsonify({"success": True, "message": f"学生 {user['name']} 密码已重置"})

    @bp.route("/api/students/<int:user_id>/reports", methods=["GET"])
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

    @bp.route("/api/students/<int:user_id>/report/<int:report_id>", methods=["GET"])
    def api_student_report_detail(user_id, report_id):
        teacher, err = _require_teacher()
        if err:
            return err
        r = db.get_learning_report(report_id)
        if not r or r["user_id"] != user_id:
            return jsonify({"success": False, "error": "报告不存在"}), 404
        return jsonify({"success": True, "report": r})

    @bp.route("/api/students/<int:user_id>/progress", methods=["GET"])
    def api_student_progress(user_id):
        teacher, err = _require_teacher()
        if err:
            return err
        progress = db.get_concept_progress(user_id)
        progress["success"] = True
        return jsonify(progress)

    @bp.route("/api/students/<int:user_id>/stats", methods=["GET"])
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
        try:
            students = db.get_students(teacher_id=teacher_id)
            return sorted({s["id"] for s in students})
        except Exception:
            return []

    def _query_reasoning_logs_by_users(user_ids, limit=100, offset=0):
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

    @bp.route("/api/teacher/reasoning-logs", methods=["GET"])
    def api_teacher_reasoning_logs():
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
            if uid not in user_ids:
                return jsonify({"success": True, "items": [], "total": 0})
            user_ids = [uid]
        items, total = _query_reasoning_logs_by_users(user_ids, limit=limit, offset=offset)
        return jsonify({"success": True, "items": items, "total": total})

    @bp.route("/api/teacher/reasoning-logs/stats", methods=["GET"])
    def api_teacher_reasoning_stats():
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
    @bp.route("/api/tasks", methods=["GET"])
    def api_list_tasks():
        teacher, err = _require_teacher()
        if err:
            return err
        tasks = db.get_tasks(limit=100)
        tasks = [t for t in tasks if t["created_by"] == teacher["id"]]
        for t in tasks:
            t["assignment_count"] = len(db.get_task_assignments(task_id=t["id"]))
        return jsonify({"success": True, "tasks": tasks})

    @bp.route("/api/tasks", methods=["POST"])
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

    @bp.route("/api/tasks/generate", methods=["POST"])
    def api_generate_task():
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
        db.update_task(result["task_id"], source_detail=f"教师 {teacher['name']} 从知识点生成")
        return jsonify({"success": True, **result})

    @bp.route("/api/tasks/<int:task_id>/assign", methods=["POST"])
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
            if db.get_task_assignments(task_id=task_id, user_id=int(uid)):
                continue
            res = db.assign_task(task_id, int(uid))
            if res.get("assignment_id"):
                result["assigned_count"] += 1
                result["details"].append({"mode": f"个人({uid})", "count": 1})
        return jsonify({"success": True, **result})

    @bp.route("/api/tasks/<int:task_id>/assignments", methods=["GET"])
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
    @bp.route("/api/resources", methods=["GET"])
    def api_resources():
        teacher, err = _require_teacher()
        if err:
            return err
        subject = request.args.get("subject")
        limit = int(request.args.get("limit", 50))
        contents = db.get_training_data(subject=subject, status="published", limit=limit)
        for c in contents:
            c.pop("content", None)
        return jsonify({"success": True, "resources": contents})

    @bp.route("/api/resources/<int:record_id>", methods=["GET"])
    def api_resource_detail(record_id):
        teacher, err = _require_teacher()
        if err:
            return err
        rec = db.get_training_record(record_id)
        if not rec:
            return jsonify({"success": False, "error": "资源不存在"}), 404
        return jsonify({"success": True, "resource": rec})

    # ---- 资源导入（写操作，全部 require teacher） ----
    @bp.route("/api/resources/import-text", methods=["POST"])
    def api_resource_import_text():
        """教师粘贴文本入库（status=draft，来源标注）。"""
        teacher, err = _require_teacher()
        if err:
            return err
        data = request.get_json(force=True) or {}
        from framework.resources import importer
        result = importer.import_text(
            subject=(data.get("subject") or "").strip(),
            chapter=(data.get("chapter") or "").strip(),
            title=(data.get("title") or "").strip(),
            content=(data.get("content") or "").strip(),
            content_type=(data.get("content_type") or "知识总结").strip(),
            difficulty=(data.get("difficulty") or "中等").strip(),
            keywords=(data.get("keywords") or "").strip(),
            prerequisites=(data.get("prerequisites") or "").strip(),
            learning_objectives=(data.get("learning_objectives") or "").strip(),
            common_mistakes=(data.get("common_mistakes") or "").strip(),
            source="manual", source_type="manual", status="draft",
        )
        if not result["ok"]:
            return jsonify({"success": False, "error": result.get("error", "导入失败")}), 400
        return jsonify({"success": True, "record_id": result["record_id"]})

    @bp.route("/api/resources/import-web", methods=["POST"])
    def api_resource_import_web():
        """按 URL 采集网络资源（受 resources.web_import_enabled 门控）。"""
        teacher, err = _require_teacher()
        if err:
            return err
        data = request.get_json(force=True) or {}
        url = (data.get("url") or "").strip()
        if not url.startswith(("http://", "https://")):
            return jsonify({"success": False, "error": "URL 必须为 http(s) 地址"}), 400
        from framework.resources import import_web
        got = import_web(url, subject=(data.get("subject") or "").strip(),
                         chapter=(data.get("chapter") or "").strip())
        if not got["ok"]:
            return jsonify({"success": False, "error": got.get("error", "采集失败")}), 400
        from framework.resources import importer
        result = importer.import_text(
            subject=(data.get("subject") or "综合").strip(), chapter=(data.get("chapter") or "").strip(),
            title=got.get("title", "网络资料"), content=got.get("text", ""),
            keywords=(data.get("keywords") or "").strip(),
            source=got.get("source") or url, source_type="web", status="draft",
        )
        if not result["ok"]:
            return jsonify({"success": False, "error": result.get("error", "入库失败")}), 400
        return jsonify({"success": True, "record_id": result["record_id"], "word_count": len(got.get("text", ""))})

    @bp.route("/api/resources/upload", methods=["POST"])
    def api_resource_upload():
        """multipart 上传文件（md/txt/html/ppt/pptx）解析入库。"""
        teacher, err = _require_teacher()
        if err:
            return err
        f = request.files.get("file")
        if not f or not f.filename:
            return jsonify({"success": False, "error": "请选择要上传的文件"}), 400
        from framework.resources import parse_upload_pptx
        try:
            raw = f.stream.read()
        except Exception as e:
            return jsonify({"success": False, "error": f"读取文件失败: {e}"}), 400
        name = f.filename
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext in ("ppt", "pptx"):
            parsed = parse_upload_pptx(raw, name)
        else:
            import framework.resources.importer as _imp
            parsed = _imp.parse_upload(_BytesReader(raw), name)
        if not parsed["ok"]:
            return jsonify({"success": False, "error": parsed.get("error", "解析失败")}), 400
        from framework.resources import importer
        result = importer.import_text(
            subject=(request.form.get("subject") or "综合").strip(),
            chapter=(request.form.get("chapter") or "").strip(),
            title=(request.form.get("title") or parsed.get("title") or name.rsplit(".", 1)[0]).strip(),
            content=parsed.get("text", ""),
            keywords=(request.form.get("keywords") or "").strip(),
            source="upload:" + name, source_type="upload", status="draft",
        )
        if not result["ok"]:
            return jsonify({"success": False, "error": result.get("error", "入库失败")}), 400
        return jsonify({"success": True, "record_id": result["record_id"]})

    @bp.route("/api/resources/drafts", methods=["GET"])
    def api_resource_drafts():
        """列出待评审草稿（draft/reviewed）。"""
        teacher, err = _require_teacher()
        if err:
            return err
        rows = db.get_training_data(status="draft", limit=500)
        rows += db.get_training_data(status="reviewed", limit=500)
        for r in rows:
            r.pop("content", None)
        return jsonify({"success": True, "drafts": rows})

    @bp.route("/api/resources/<int:record_id>/review", methods=["PUT"])
    def api_resource_review(record_id):
        """评审资源：更新 status、补 common_mistakes / prerequisites。"""
        teacher, err = _require_teacher()
        if err:
            return err
        rec = db.get_training_record(record_id)
        if not rec:
            return jsonify({"success": False, "error": "资源不存在"}), 404
        data = request.get_json(force=True) or {}
        status = (data.get("status") or "").strip()
        if status and status not in ("draft", "reviewed", "published"):
            return jsonify({"success": False, "error": "非法状态"}), 400
        fields = {k: v for k, v in {
            "status": status,
            "common_mistakes": (data.get("common_mistakes") or "").strip(),
            "prerequisites": (data.get("prerequisites") or "").strip(),
        }.items() if v}
        db.update_training_data(record_id, **fields)
        return jsonify({"success": True, "resource": db.get_training_record(record_id)})

    @bp.route("/api/resources/<int:record_id>", methods=["PUT"])
    def api_resource_edit(record_id):
        """编辑资源字段（白名单，复用 update_training_data）。"""
        teacher, err = _require_teacher()
        if err:
            return err
        rec = db.get_training_record(record_id)
        if not rec:
            return jsonify({"success": False, "error": "资源不存在"}), 404
        data = request.get_json(force=True) or {}
        allowed = ["subject", "chapter", "title", "content", "grade", "content_type",
                   "difficulty", "keywords", "prerequisites", "learning_objectives",
                   "common_mistakes"]
        fields = {k: v for k, v in data.items() if k in allowed and v not in (None, "")}
        if not fields:
            return jsonify({"success": False, "error": "没有可更新的字段"}), 400
        db.update_training_data(record_id, **fields)
        return jsonify({"success": True, "resource": db.get_training_record(record_id)})

    @bp.route("/api/resources/<int:record_id>", methods=["DELETE"])
    def api_resource_delete(record_id):
        teacher, err = _require_teacher()
        if err:
            return err
        if not db.get_training_record(record_id):
            return jsonify({"success": False, "error": "资源不存在"}), 404
        db.delete_training_data(record_id)
        return jsonify({"success": True})

    @bp.route("/api/lesson/plan", methods=["GET"])
    def api_lesson_plan():
        """学情驱动备课：按班级聚合 progress → 返回薄弱知识点 + 命中 keywords/prerequisites 的素材推荐。"""
        teacher, err = _require_teacher()
        if err:
            return err
        class_id = request.args.get("class_id")
        if class_id and not _class_belongs_to_teacher(int(class_id), teacher["id"]):
            return jsonify({"success": False, "error": "无权查看该班级"}), 403
        try:
            nodes = db.get_knowledge_nodes()
        except Exception:
            nodes = []
        name_map = {n["id"]: n.get("name", n["id"]) for n in nodes}

        # 聚合薄弱知识点（mastery<0.6）
        if class_id:
            rows = _rows_safe(db, _WEAK_SQL, (int(class_id),))
        else:
            rows = _rows_safe(db, _WEAK_SQL_ALL, ())
        weak = [{"node_id": r["node_id"], "name": name_map.get(r["node_id"], r["node_id"]),
                 "avg_mastery": round(r["avg_mastery"], 3), "students": r["students"]}
                for r in rows if r["node_id"]]

        # 素材推荐：匹配关键字/前置
        materials = db.get_training_data(status="published", limit=100)
        recs = []
        for weak_node in weak:
            nid, name = weak_node["node_id"], weak_node["name"]
            hits = []
            for m in materials:
                kw = ("%s %s %s" % (m.get("keywords", ""), m.get("prerequisites", ""), m.get("title", ""))).lower()
                if name.lower() in kw or nid.lower() in kw:
                    hits.append({"id": m["id"], "title": m["title"], "subject": m.get("subject", ""),
                                 "content_type": m.get("content_type", "")})
            recs.append({"node_id": weak_node["node_id"], "name": weak_node["name"],
                         "avg_mastery": weak_node["avg_mastery"], "students": weak_node["students"],
                         "materials": hits[:5]})
        return jsonify({"success": True, "classes": _classes_safe(db, teacher["id"]),
                        "weak_nodes": recs})

    @bp.route("/api/questions", methods=["GET"])
    def api_questions():
        teacher, err = _require_teacher()
        if err:
            return err
        subject = request.args.get("subject")
        questions = db.get_questions(subject=subject, limit=50)
        return jsonify({"success": True, "questions": questions})

    @bp.route("/api/knowledge-nodes", methods=["GET"])
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
        try:
            return _visible_student_ids(teacher_id)
        except Exception:
            return []

    @bp.route("/api/analytics/overview")
    def api_analytics_overview():
        teacher, err = _require_teacher()
        if err:
            return err
        user_ids = _visible_student_ids_safe(teacher["id"])
        return jsonify({"success": True, "data": db.get_analytics_overview(user_ids or None)})

    @bp.route("/api/analytics/trend")
    def api_analytics_trend():
        teacher, err = _require_teacher()
        if err:
            return err
        user_ids = _visible_student_ids_safe(teacher["id"])
        limit = min(int(request.args.get("limit", 14)), 90)
        return jsonify({"success": True, "data": db.get_analytics_trend(user_ids or None, limit=limit)})

    @bp.route("/api/analytics/subjects")
    def api_analytics_subjects():
        teacher, err = _require_teacher()
        if err:
            return err
        user_ids = _visible_student_ids_safe(teacher["id"])
        return jsonify({"success": True, "data": db.get_analytics_subjects(user_ids or None)})

    @bp.route("/api/analytics/weakpoints")
    def api_analytics_weakpoints():
        teacher, err = _require_teacher()
        if err:
            return err
        user_ids = _visible_student_ids_safe(teacher["id"])
        limit = min(int(request.args.get("limit", 8)), 30)
        return jsonify({"success": True, "data": db.get_analytics_weakpoints(user_ids or None, limit=limit)})

    @bp.route("/api/analytics/concepts")
    def api_analytics_concepts():
        teacher, err = _require_teacher()
        if err:
            return err
        user_ids = _visible_student_ids_safe(teacher["id"])
        limit = min(int(request.args.get("limit", 24)), 60)
        return jsonify({"success": True, "data": db.get_analytics_concepts(user_ids or None, limit=limit)})

    @bp.route("/api/analytics/users")
    def api_analytics_users():
        teacher, err = _require_teacher()
        if err:
            return err
        user_ids = _visible_student_ids_safe(teacher["id"])
        return jsonify({"success": True, "data": db.get_analytics_users(user_ids or None)})

    @bp.route("/api/analytics/reasoning")
    def api_analytics_reasoning():
        teacher, err = _require_teacher()
        if err:
            return err
        user_ids = _visible_student_ids_safe(teacher["id"])
        days = int(request.args.get("days", 7))
        return jsonify({"success": True, "data": db.get_analytics_reasoning(user_ids or None, days=days)})

    # ============================================================
    # 数据合规导出（教师申请 → 管理员审批 → 下载）
    # ============================================================
    @bp.route("/api/exports", methods=["GET"])
    def api_my_exports():
        teacher, err = _require_teacher()
        if err:
            return err
        exports = db.list_data_exports(requester_id=teacher["id"], requester_type="teacher", limit=50)
        for e in exports:
            e["can_download"] = bool(e["status"] == "approved" and e.get("file_path"))
        return jsonify({"success": True, "exports": exports})

    @bp.route("/api/exports", methods=["POST"])
    def api_request_export():
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

    @bp.route("/api/exports/<int:export_id>/download")
    def api_download_export(export_id):
        teacher, err = _require_teacher()
        if err:
            return err
        exp = db.get_data_export(export_id)
        if not exp:
            return jsonify({"success": False, "error": "导出申请不存在"}), 404
        if exp["requester_id"] != teacher["id"] or exp["requester_type"] != "teacher":
            return jsonify({"success": False, "error": "无权下载该导出文件"}), 403
        if exp["status"] != "approved" or not exp.get("file_path"):
            return jsonify({"success": False, "error": "该导出尚未批准或文件不存在"}), 400
        export_dir = os.path.join(str(BASE_DIR), "export_data")
        fpath = os.path.join(export_dir, exp["file_path"])
        if not os.path.isfile(fpath):
            return jsonify({"success": False, "error": "导出文件已不存在"}), 404
        db.add_system_log("info", "export", f"教师下载导出文件 #{export_id} ({exp['file_path']})")
        return send_from_directory(export_dir, exp["file_path"], as_attachment=True)

    return bp