# -*- coding: utf-8 -*-
"""
LumiLearn 管理员 API 路由
认证 / 用户管理 / 模型管理 / Agent管理 / 系统监控
"""
import json
import logging
import os
import time
from typing import Dict
from flask import Blueprint, request, jsonify

from framework.database import db
from framework.admin.auth import get_admin_auth, require_admin
from framework.admin.agents import get_agent_registry
from framework.core.config import get_config
from framework.models.ollama_provider import get_ollama_provider

logger = logging.getLogger("lumilearn.routes.admin")

admin_bp = Blueprint("admin", __name__)


# ---------------------------------------------------------------------------
# 认证
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/login", methods=["POST", "OPTIONS"])
def admin_login():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    data = request.get_json(force=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    result = get_admin_auth().login(username, password)
    if not result["success"]:
        return jsonify(result), 401
    return jsonify(result)


@admin_bp.route("/api/admin/logout", methods=["POST", "OPTIONS"])
@require_admin
def admin_logout():
    token = request.headers.get("X-Admin-Token", "")
    get_admin_auth().logout(token)
    return jsonify({"success": True, "message": "已退出登录"})


@admin_bp.route("/api/admin/me", methods=["GET", "OPTIONS"])
@require_admin
def admin_me():
    admin = request.admin
    return jsonify({
        "success": True,
        "admin": {
            "id": admin["id"],
            "username": admin["username"],
            "display_name": admin["display_name"],
            "role": admin["role"],
            "last_login_at": admin["last_login_at"],
        },
    })


@admin_bp.route("/api/admin/password", methods=["POST", "OPTIONS"])
@require_admin
def admin_change_password():
    data = request.get_json(force=True) or {}
    result = get_admin_auth().change_password(
        request.admin["id"],
        data.get("old_password", ""),
        data.get("new_password", ""),
    )
    return jsonify(result)


# ---------------------------------------------------------------------------
# 系统概览
# ---------------------------------------------------------------------------

def _collect_activity_logs(source: str = "all", limit: int = 200) -> list:
    """统一活动日志采集：系统操作 + 学生推理 + 学习报告，按时间倒序合并。

    :param source: all / system / reasoning / report
    :param limit: 返回条数上限（合并前各源各取 limit 条，合并后截断）
    """
    source = (source or "all").strip().lower()
    limit = min(int(limit), 500)

    entries = []
    if source in ("all", "system"):
        for l in db.get_system_logs(limit=limit):
            entries.append({
                "source": "system",
                "id": l.get("id"),
                "level": l.get("level", "info"),
                "module": l.get("module", ""),
                "message": l.get("message", ""),
                "detail": (l.get("detail") or "")[:500],
                "created_at": l.get("created_at", ""),
                "user_name": None, "topic": None, "model_used": None,
            })
    if source in ("all", "reasoning"):
        for r in db.get_reasoning_logs(limit=limit):
            entries.append({
                "source": "reasoning",
                "id": r.get("id"),
                "level": "error" if r.get("status") == "error" else "info",
                "module": "推理-" + (r.get("mode") or ""),
                "message": "{} · {}".format(
                    r.get("student_name") or ("#" + str(r.get("user_id") or 0)),
                    r.get("topic") or "(无主题)"
                ) + ((" · " + r.get("step_name")) if r.get("step_name") else ""),
                "detail": (r.get("output") or "")[:500],
                "created_at": r.get("created_at", ""),
                "user_name": r.get("student_name"),
                "topic": r.get("topic"),
                "model_used": r.get("model_used"),
            })
    if source in ("all", "report"):
        for rep in db.get_learning_reports(limit=limit):
            score = rep.get("score")
            entries.append({
                "source": "report",
                "id": rep.get("id"),
                "level": "info",
                "module": "学习报告",
                "message": "#{} · {}".format(rep.get("user_id") or 0, rep.get("topic") or "(无主题)"),
                "detail": "",
                "created_at": rep.get("created_at", ""),
                "user_name": None,
                "topic": rep.get("topic"),
                "model_used": None,
                "score": score,
            })

    entries.sort(key=lambda x: x["created_at"] or "", reverse=True)
    return entries[:limit]


@admin_bp.route("/api/admin/overview", methods=["GET", "OPTIONS"])
@require_admin
def admin_overview():
    """系统总览：用户数、工作流数、检测数、模型状态、Agent 状态、最近活动"""
    users = db.get_users()

    # 说明：get_user_workflows/get_user_detections 的 user_id 为必填参数，
    # 传 None 会导致 WHERE user_id = NULL 恒空（结果恒为 0），
    # 因此这里直接用 COUNT 查询全表行数，保证 overview 在真实数据库上可用。
    workflows_row = db._query_one("SELECT COUNT(*) as c FROM learning_workflows") if hasattr(db, "get_user_workflows") else None
    detections_row = db._query_one("SELECT COUNT(*) as c FROM output_detections") if hasattr(db, "get_user_detections") else None
    total_workflows = workflows_row["c"] if workflows_row else 0
    total_detections = detections_row["c"] if detections_row else 0

    agents = db.get_agents()
    # 最近活动：合并系统操作 + 学生推理 + 学习报告（不再只有管理操作）
    recent_logs = _collect_activity_logs("all", 6)

    ollama = get_ollama_provider()
    model_status = ollama.health_check()

    return jsonify({
        "success": True,
        "stats": {
            "total_users": len(users),
            "total_teachers": len([u for u in users if u["role"] == "teacher"]),
            "total_students": len([u for u in users if u["role"] == "student"]),
            "total_workflows": total_workflows,
            "total_detections": total_detections,
            "total_agents": len(agents),
            "running_agents": len([a for a in agents if a["status"] == "running"]),
        },
        "model_status": model_status,
        "recent_logs": recent_logs,
    })


# ---------------------------------------------------------------------------
# 用户管理
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/users", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_users():
    role = request.args.get("role")
    users = db.get_users(role=role)
    # 隐藏密码哈希
    for u in users:
        u["has_password"] = bool(u.get("password_hash", ""))
        u.pop("password_hash", None)
        try:
            u["classes"] = db.get_student_classes(u["id"])
        except Exception:
            u["classes"] = []
    return jsonify({"success": True, "users": users})


@admin_bp.route("/api/admin/users", methods=["POST", "OPTIONS"])
@require_admin
def admin_create_user():
    data = request.get_json(force=True) or {}
    name = data.get("name", "")
    role = data.get("role", "student")
    username = data.get("username", "")
    password = data.get("password", "")
    if not name:
        return jsonify({"error": "缺少 name 字段"}), 400
    if not password or len(password) < 4:
        return jsonify({"error": "密码不能为空且至少4位"}), 400
    # 检查用户名是否已存在
    if db.get_user_by_username(username or name):
        return jsonify({"error": f"用户名 '{username or name}' 已存在"}), 400
    user = db.add_user(name, role=role, username=username, password=password)
    db.add_system_log("info", "admin", f"管理员创建用户: {name} ({role})")
    return jsonify({"success": True, "user": user})


@admin_bp.route("/api/admin/users/<int:user_id>/password", methods=["POST", "OPTIONS"])
@require_admin
def admin_reset_user_password(user_id):
    """重置学生/教师用户密码"""
    data = request.get_json(force=True) or {}
    new_password = data.get("password", "")
    if not new_password or len(new_password) < 4:
        return jsonify({"error": "密码不能为空且至少4位"}), 400
    user = db.get_user(user_id)
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    db.update_user_password(user_id, new_password)
    db.add_system_log("info", "admin", f"重置用户 #{user_id} 密码")
    return jsonify({"success": True, "message": f"用户 {user['name']} 密码已重置"})


@admin_bp.route("/api/admin/users/<int:user_id>", methods=["DELETE", "OPTIONS"])
@require_admin
def admin_delete_user(user_id):
    ok = db.delete_user(user_id)
    if not ok:
        return jsonify({"error": "用户不存在"}), 404
    db.add_system_log("info", "admin", f"管理员删除用户 id={user_id}")
    return jsonify({"success": True, "message": "用户已删除"})


# ---------- 账号与班级绑定管理 ----------
@admin_bp.route("/api/admin/classes", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_all_classes():
    """全部班级（含学校/年级/班主任/学生数），供管理员绑定账号"""
    return jsonify({"success": True, "classes": db.get_classes()})


@admin_bp.route("/api/admin/users/<int:user_id>/classes", methods=["GET", "OPTIONS"])
@require_admin
def admin_user_classes(user_id):
    """查看某账号已绑定的班级"""
    return jsonify({"success": True, "classes": db.get_student_classes(user_id)})


@admin_bp.route("/api/admin/users/<int:user_id>/classes", methods=["POST", "OPTIONS"])
@require_admin
def admin_bind_user_class(user_id):
    """管理员把账号绑定到班级"""
    data = request.get_json(force=True) or {}
    try:
        class_id = int(data.get("class_id") or 0)
    except (TypeError, ValueError):
        class_id = 0
    if class_id <= 0:
        return jsonify({"error": "缺少 class_id"}), 400
    user = db.get_user(user_id)
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    result = db.add_student_to_class(class_id, user_id)
    db.add_system_log("info", "admin", f"管理员将用户 #{user_id}({user['name']}) 绑定到班级 #{class_id}")
    return jsonify({"success": True, "message": f"已绑定 {user['name']}", "result": result})


@admin_bp.route("/api/admin/users/<int:user_id>/classes/<int:class_id>", methods=["DELETE", "OPTIONS"])
@require_admin
def admin_unbind_user_class(user_id, class_id):
    """管理员解除账号与班级的绑定"""
    ok = db.remove_student_from_class(class_id, user_id)
    db.add_system_log("info", "admin", f"管理员解除用户 #{user_id} 与班级 #{class_id} 绑定")
    return jsonify({"success": ok, "message": "已解除绑定" if ok else "解除失败（可能未绑定）"})


@admin_bp.route("/api/admin/learning-reports", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_learning_reports():
    """获取所有学生的学习报告（可筛选用户）"""
    user_id = request.args.get("user_id", type=int)
    limit = min(int(request.args.get("limit", 50)), 200)
    reports = db.get_learning_reports(user_id=user_id, limit=limit)
    # 关联用户姓名
    user_cache = {}
    for r in reports:
        uid = r["user_id"]
        if uid not in user_cache:
            u = db.get_user(uid)
            user_cache[uid] = u["name"] if u else f"#{uid}"
        r["user_name"] = user_cache[uid]
        # 精简 report 字段（只返回摘要，避免过大）
        rep = r.get("report", {})
        r["summary"] = {
            "title": rep.get("title", ""),
            "generated_at": rep.get("generated_at", ""),
            "subject": (rep.get("task_understanding") or {}).get("subject", ""),
            "core_topic": (rep.get("task_understanding") or {}).get("core_topic", ""),
            "score": (rep.get("mastery_assessment") or {}).get("score", 0),
            "level": (rep.get("mastery_assessment") or {}).get("level", ""),
        }
        r.pop("report", None)
    return jsonify({"success": True, "reports": reports})


@admin_bp.route("/api/admin/learning-reports/<int:report_id>", methods=["GET", "OPTIONS"])
@require_admin
def admin_get_learning_report(report_id):
    """获取单份学习报告详情"""
    r = db.get_learning_report(report_id)
    if not r:
        return jsonify({"error": "报告不存在"}), 404
    u = db.get_user(r["user_id"])
    r["user_name"] = u["name"] if u else f"#{r['user_id']}"
    return jsonify({"success": True, "report": r})


# ---------------------------------------------------------------------------
# 推理过程日志
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/reasoning-logs", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_reasoning_logs():
    """获取模型推理过程日志列表（可按学生/模型/主题/模式/日期筛选，分页）"""
    user_id = request.args.get("user_id", type=int)
    model = request.args.get("model") or None
    topic = request.args.get("topic") or None
    mode = request.args.get("mode") or None
    session_id = request.args.get("session_id") or None
    start_date = request.args.get("start_date") or None
    end_date = request.args.get("end_date") or None
    limit = min(int(request.args.get("limit", 20)), 200)
    offset = max(int(request.args.get("offset", 0)), 0)
    # 结束日期只传日期时默认补到当天 23:59:59，便于按天筛选
    if end_date and len(end_date) <= 10:
        end_date = end_date + " 23:59:59"
    items = db.get_reasoning_logs(
        user_id=user_id, model=model, topic=topic, mode=mode,
        session_id=session_id, start_date=start_date, end_date=end_date,
        limit=limit, offset=offset,
    )
    # 统计总数（与 get_reasoning_logs 相同的筛选条件，用于分页）
    conds, params = [], []
    if user_id is not None:
        conds.append("user_id = ?")
        params.append(user_id)
    if model:
        conds.append("model_used = ?")
        params.append(model)
    if topic:
        conds.append("topic = ?")
        params.append(topic)
    if mode:
        conds.append("mode = ?")
        params.append(mode)
    if session_id:
        conds.append("session_id = ?")
        params.append(session_id)
    if start_date:
        conds.append("created_at >= ?")
        params.append(start_date)
    if end_date:
        conds.append("created_at <= ?")
        params.append(end_date)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    total = db._query_one(
        f"SELECT COUNT(*) AS n FROM reasoning_logs {where}", tuple(params)
    )["n"]
    return jsonify({
        "success": True,
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@admin_bp.route("/api/admin/reasoning-logs/<int:log_id>", methods=["GET", "OPTIONS"])
@require_admin
def admin_get_reasoning_log(log_id):
    """获取单条推理过程日志详情"""
    log = db.get_reasoning_log_by_id(log_id)
    if not log:
        return jsonify({"error": "日志不存在"}), 404
    return jsonify({"success": True, "log": log})


@admin_bp.route("/api/admin/reasoning-logs/stats", methods=["GET", "OPTIONS"])
@require_admin
def admin_reasoning_logs_stats():
    """推理过程日志统计（days=0 表示不按时间过滤，取全部）"""
    days = int(request.args.get("days", 7))
    stats = db.get_reasoning_stats(days=days)
    return jsonify({"success": True, "days": days, **stats})


# ---------------------------------------------------------------------------
# 模型管理
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/models", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_models():
    ollama = get_ollama_provider()
    models = ollama.list_models()
    health = ollama.health_check()
    return jsonify({"success": True, "models": models, "health": health})


@admin_bp.route("/api/admin/models/pull", methods=["POST", "OPTIONS"])
@require_admin
def admin_pull_model():
    """拉取新模型到 Ollama"""
    data = request.get_json(force=True) or {}
    model_name = data.get("model", "")
    if not model_name:
        return jsonify({"error": "缺少 model 字段"}), 400
    ollama = get_ollama_provider()
    result = ollama.pull_model(model_name) if hasattr(ollama, "pull_model") else {"error": "当前 Ollama 版本不支持拉取模型"}
    db.add_system_log("info", "models", f"拉取模型: {model_name}", json.dumps(result, ensure_ascii=False))
    return jsonify({"success": "error" not in result, **result})


@admin_bp.route("/api/admin/models/delete", methods=["POST", "OPTIONS"])
@require_admin
def admin_delete_model():
    data = request.get_json(force=True) or {}
    model_name = data.get("model", "")
    if not model_name:
        return jsonify({"error": "缺少 model 字段"}), 400
    ollama = get_ollama_provider()
    result = ollama.delete_model(model_name) if hasattr(ollama, "delete_model") else {"error": "当前 Ollama 版本不支持删除模型"}
    db.add_system_log("info", "models", f"删除模型: {model_name}", json.dumps(result, ensure_ascii=False))
    return jsonify({"success": "error" not in result, **result})


@admin_bp.route("/api/admin/models/default", methods=["POST", "OPTIONS"])
@require_admin
def admin_set_default_model():
    data = request.get_json(force=True) or {}
    model_name = data.get("model", "")
    if not model_name:
        return jsonify({"error": "缺少 model 字段"}), 400
    config = get_config()
    config["ollama"]["default_model"] = model_name
    db.add_system_log("info", "models", f"设置默认模型: {model_name}")
    return jsonify({"success": True, "message": f"默认模型已设置为 {model_name}"})


# ---------------------------------------------------------------------------
# Agent 管理
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/agents", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_agents():
    registry = get_agent_registry()
    agent_type = request.args.get("type")
    return jsonify({"success": True, "agents": registry.list_agents(agent_type)})


@admin_bp.route("/api/admin/agents", methods=["POST", "OPTIONS"])
@require_admin
def admin_register_agent():
    data = request.get_json(force=True) or {}
    agent_id = data.get("agent_id", "")
    name = data.get("name", "")
    agent_type = data.get("type", "custom")
    if not agent_id or not name:
        return jsonify({"error": "缺少 agent_id 或 name 字段"}), 400
    registry = get_agent_registry()
    result = registry.register(agent_id, name, agent_type,
                               description=data.get("description", ""),
                               config=data.get("config", {}))
    return jsonify({"success": True, **result})


@admin_bp.route("/api/admin/agents/<agent_id>/start", methods=["POST", "OPTIONS"])
@require_admin
def admin_start_agent(agent_id):
    try:
        result = get_agent_registry().start(agent_id)
    except KeyError:
        return jsonify({"error": "Agent 不存在"}), 404
    return jsonify(result)


@admin_bp.route("/api/admin/agents/<agent_id>/stop", methods=["POST", "OPTIONS"])
@require_admin
def admin_stop_agent(agent_id):
    result = get_agent_registry().stop(agent_id)
    return jsonify(result)


@admin_bp.route("/api/admin/agents/<agent_id>/run", methods=["POST", "OPTIONS"])
@require_admin
def admin_run_agent(agent_id):
    """手动触发 Agent 执行（测试用）"""
    data = request.get_json(force=True) or {}
    result = get_agent_registry().run_agent(agent_id, data)
    return jsonify(result)


@admin_bp.route("/api/admin/agents/<agent_id>", methods=["DELETE", "OPTIONS"])
@require_admin
def admin_delete_agent(agent_id):
    result = get_agent_registry().delete(agent_id)
    return jsonify(result)


@admin_bp.route("/api/admin/agents/health", methods=["GET", "OPTIONS"])
@require_admin
def admin_agents_health():
    return jsonify(get_agent_registry().health())


# ---------------------------------------------------------------------------
# 系统监控
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/logs", methods=["GET", "OPTIONS"])
@require_admin
def admin_logs():
    level = request.args.get("level")
    limit = int(request.args.get("limit", 100))
    logs = db.get_system_logs(level=level, limit=limit)
    return jsonify({"success": True, "logs": logs})


@admin_bp.route("/api/admin/activity-logs", methods=["GET", "OPTIONS"])
@require_admin
def admin_activity_logs():
    """统一活动日志：系统操作 + 学生推理 + 学习报告，按时间倒序合并。

    让管理员在「系统日志」页也能直接看到学生实际使用产生的数据
    （课堂聊天 / 五步学习 / GOAI 学习报告），不再只有管理操作。
    """
    source = request.args.get("source") or "all"
    limit = int(request.args.get("limit", 200))
    logs = _collect_activity_logs(source, limit)
    return jsonify({"success": True, "logs": logs, "total": len(logs)})


@admin_bp.route("/api/admin/logs/clear", methods=["POST", "OPTIONS"])
@require_admin
def admin_clear_logs():
    days = int(request.json.get("older_than_days", 7) if request.json else 7)
    count = db.clear_system_logs(older_than_days=days)
    return jsonify({"success": True, "cleared": count})


@admin_bp.route("/api/admin/api-keys", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_api_keys():
    return jsonify({"success": True, "api_keys": db.get_api_keys()})


@admin_bp.route("/api/admin/api-keys", methods=["POST", "OPTIONS"])
@require_admin
def admin_create_api_key():
    import secrets
    data = request.get_json(force=True) or {}
    key_name = data.get("key_name", "")
    scope = data.get("scope", "read")
    if not key_name:
        return jsonify({"error": "缺少 key_name 字段"}), 400
    api_key = secrets.token_hex(24)
    result = db.add_api_key(key_name, api_key, scope)
    db.add_system_log("info", "admin", f"创建API密钥: {key_name} ({scope})")
    return jsonify({"success": True, **result})


@admin_bp.route("/api/admin/api-keys/<path:api_key>", methods=["DELETE", "OPTIONS"])
@require_admin
def admin_delete_api_key(api_key):
    ok = db.delete_api_key(api_key)
    if not ok:
        return jsonify({"error": "密钥不存在"}), 404
    return jsonify({"success": True, "message": "密钥已删除"})


# ---------------------------------------------------------------------------
# 模型提供者管理（API Key 配置）
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/providers", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_providers():
    """获取所有已配置的模型提供者列表"""
    from framework.services.provider_service import get_provider_service
    ps = get_provider_service()
    providers = ps.list_providers()
    templates = ps.get_available_templates()
    return jsonify({"success": True, "providers": providers, "templates": templates})


@admin_bp.route("/api/admin/providers", methods=["POST", "OPTIONS"])
@require_admin
def admin_add_provider():
    """添加或更新模型提供者"""
    from framework.services.provider_service import get_provider_service
    data = request.get_json(force=True) or {}
    key = data.get("key", "")
    name = data.get("name", "")
    base_url = data.get("base_url", "")
    api_key = data.get("api_key", "")
    enabled = data.get("enabled", True)
    models = data.get("models")

    # 更新时如果 api_key 为空字符串，保留原有 Key（前端传空表示不修改）
    if not api_key:
        existing = get_provider_service().get_provider(key)
        if existing and existing.get("has_api_key"):
            api_key = get_provider_service().get_provider_api_key(key)

    result = get_provider_service().add_or_update_provider(
        key, name, base_url, api_key, enabled=enabled, models=models
    )
    if not result["success"]:
        return jsonify(result), 400
    db.add_system_log("info", "providers", f"保存提供者: {name} ({key})")
    return jsonify(result)


@admin_bp.route("/api/admin/providers/<provider_key>", methods=["DELETE", "OPTIONS"])
@require_admin
def admin_delete_provider(provider_key):
    """删除模型提供者"""
    from framework.services.provider_service import get_provider_service
    result = get_provider_service().delete_provider(provider_key)
    if not result["success"]:
        return jsonify(result), 404
    return jsonify(result)


# ---------------------------------------------------------------------------
# 端口-模型映射管理
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/port-models", methods=["GET", "OPTIONS"])
@require_admin
def admin_get_port_models():
    """获取各端口使用的模型配置"""
    from framework.services.provider_service import get_provider_service
    ps = get_provider_service()
    port_map = ps.get_port_model_map()
    all_models = ps.get_all_available_models()
    return jsonify({"success": True, "port_map": port_map, "all_models": all_models})


@admin_bp.route("/api/admin/port-models", methods=["POST", "OPTIONS"])
@require_admin
def admin_set_port_model():
    """设置某个端口使用的模型"""
    from framework.services.provider_service import get_provider_service
    data = request.get_json(force=True) or {}
    port_key = data.get("port_key", "")
    provider = data.get("provider", "ollama")
    model = data.get("model", "")
    if not port_key or not model:
        return jsonify({"error": "缺少 port_key 或 model 字段"}), 400
    result = get_provider_service().set_port_model(port_key, provider, model)
    if not result["success"]:
        return jsonify(result), 400
    db.add_system_log("info", "port_models", f"端口 {port_key} 模型设置为 {provider}/{model}")
    return jsonify(result)


# ---------------------------------------------------------------------------
# 端口服务选择性配置管理
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/port-settings", methods=["GET", "OPTIONS"])
@require_admin
def admin_get_port_settings():
    """获取所有端口服务的启用/端口配置与监听状态"""
    from framework.services.provider_service import get_provider_service
    ps = get_provider_service()
    settings = ps.get_port_settings()
    return jsonify({"success": True, "port_settings": settings})


@admin_bp.route("/api/admin/port-settings", methods=["POST", "OPTIONS"])
@require_admin
def admin_set_port_settings():
    """保存端口服务配置（启用开关 + 端口号）"""
    from framework.services.provider_service import get_provider_service
    data = request.get_json(force=True) or {}
    settings = data.get("port_settings") or {}
    if not settings:
        return jsonify({"error": "缺少 port_settings 字段"}), 400
    result = get_provider_service().set_port_settings(settings)
    if not result["success"]:
        return jsonify(result), 400
    db.add_system_log("info", "ports", "更新端口服务配置", str(settings))
    return jsonify(result)


# ---------------------------------------------------------------------------
# 数据可视化（纯 SVG 图表数据源，Admin 全量范围）
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/analytics/overview", methods=["GET", "OPTIONS"])
@require_admin
def admin_analytics_overview():
    """数据可视化：总量概览"""
    return jsonify({"success": True, "data": db.get_analytics_overview()})


@admin_bp.route("/api/admin/analytics/trend", methods=["GET", "OPTIONS"])
@require_admin
def admin_analytics_trend():
    """数据可视化：掌握度趋势（按日）"""
    limit = min(int(request.args.get("limit", 14)), 90)
    return jsonify({"success": True, "data": db.get_analytics_trend(limit=limit)})


@admin_bp.route("/api/admin/analytics/subjects", methods=["GET", "OPTIONS"])
@require_admin
def admin_analytics_subjects():
    """数据可视化：学科掌握度对比"""
    return jsonify({"success": True, "data": db.get_analytics_subjects()})


@admin_bp.route("/api/admin/analytics/weakpoints", methods=["GET", "OPTIONS"])
@require_admin
def admin_analytics_weakpoints():
    """数据可视化：薄弱点排行"""
    limit = min(int(request.args.get("limit", 8)), 30)
    return jsonify({"success": True, "data": db.get_analytics_weakpoints(limit=limit)})


@admin_bp.route("/api/admin/analytics/concepts", methods=["GET", "OPTIONS"])
@require_admin
def admin_analytics_concepts():
    """数据可视化：知识点掌握度热力"""
    limit = min(int(request.args.get("limit", 24)), 60)
    return jsonify({"success": True, "data": db.get_analytics_concepts(limit=limit)})


@admin_bp.route("/api/admin/analytics/reasoning", methods=["GET", "OPTIONS"])
@require_admin
def admin_analytics_reasoning():
    """数据可视化：模型推理统计"""
    days = int(request.args.get("days", 7))
    return jsonify({"success": True, "data": db.get_analytics_reasoning(days=days)})


@admin_bp.route("/api/admin/analytics/users", methods=["GET", "OPTIONS"])
@require_admin
def admin_analytics_users():
    """数据可视化：学生掌握度排行"""
    return jsonify({"success": True, "data": db.get_analytics_users()})


# ---------------------------------------------------------------------------
# 管理员账号管理（super_admin / operator 分级）
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/admins", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_admins():
    """管理员账号列表（不含密码哈希）"""
    admins = db.get_admins()
    for a in admins:
        a.pop("password_hash", None)
        a["has_password"] = bool(a.get("password_hash", ""))
    return jsonify({"success": True, "admins": admins})


@admin_bp.route("/api/admin/admins", methods=["POST", "OPTIONS"])
@require_admin
def admin_create_admin():
    """创建管理员（super_admin 才能创建）"""
    if request.admin.get("role") != "super_admin":
        return jsonify({"error": "仅超级管理员可创建管理员账号"}), 403
    from werkzeug.security import generate_password_hash
    data = request.get_json(force=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    display_name = data.get("display_name", "").strip()
    role = data.get("role", "operator")
    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400
    if len(password) < 6:
        return jsonify({"error": "密码至少 6 位"}), 400
    if role not in ("super_admin", "operator"):
        return jsonify({"error": "角色只能是 super_admin 或 operator"}), 400
    if db.get_admin_by_username(username):
        return jsonify({"error": f"管理员 '{username}' 已存在"}), 400
    admin = db.add_admin(username, generate_password_hash(password),
                         display_name=display_name, role=role)
    db.add_system_log("info", "admin", f"创建管理员账号: {username} ({role})")
    return jsonify({"success": True, "admin": admin})


@admin_bp.route("/api/admin/admins/<int:admin_id>/toggle", methods=["POST", "OPTIONS"])
@require_admin
def admin_toggle_admin(admin_id):
    """启用/禁用管理员账号"""
    if request.admin.get("role") != "super_admin":
        return jsonify({"error": "仅超级管理员可启停管理员账号"}), 403
    target = db.get_admin(admin_id)
    if not target:
        return jsonify({"error": "管理员不存在"}), 404
    if target["id"] == request.admin["id"]:
        return jsonify({"error": "不能禁用自己"}), 400
    new_state = 0 if target["is_active"] else 1
    ok = db.set_admin_active(admin_id, new_state)
    if not ok:
        return jsonify({"error": "操作失败"}), 400
    db.add_system_log("info", "admin",
                      f"{'禁用' if new_state == 0 else '启用'}管理员 {target['username']}")
    return jsonify({"success": True, "is_active": new_state})


@admin_bp.route("/api/admin/admins/<int:admin_id>/role", methods=["POST", "OPTIONS"])
@require_admin
def admin_set_admin_role(admin_id):
    """修改管理员角色"""
    if request.admin.get("role") != "super_admin":
        return jsonify({"error": "仅超级管理员可修改角色"}), 403
    data = request.get_json(force=True) or {}
    role = data.get("role", "")
    target = db.get_admin(admin_id)
    if not target:
        return jsonify({"error": "管理员不存在"}), 404
    if target["id"] == request.admin["id"] and role != "super_admin":
        return jsonify({"error": "不能降级自己"}), 400
    ok = db.set_admin_role(admin_id, role)
    if not ok:
        return jsonify({"error": "角色只能是 super_admin 或 operator"}), 400
    db.add_system_log("info", "admin", f"修改管理员 {target['username']} 角色为 {role}")
    return jsonify({"success": True, "role": role})


@admin_bp.route("/api/admin/admins/<int:admin_id>", methods=["DELETE", "OPTIONS"])
@require_admin
def admin_delete_admin(admin_id):
    """删除管理员（super_admin 才能删除，且不能删自己/超管）"""
    if request.admin.get("role") != "super_admin":
        return jsonify({"error": "仅超级管理员可删除管理员账号"}), 403
    target = db.get_admin(admin_id)
    if not target:
        return jsonify({"error": "管理员不存在"}), 404
    if target["id"] == request.admin["id"]:
        return jsonify({"error": "不能删除自己"}), 400
    ok = db.delete_admin(admin_id)
    if not ok:
        return jsonify({"error": "超级管理员不可删除"}), 400
    db.add_system_log("info", "admin", f"删除管理员账号: {target['username']}")
    return jsonify({"success": True, "message": "已删除"})


# ---------------------------------------------------------------------------
# 用户账号权限管理（启停用 / 角色变更）
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/users/<int:user_id>/active", methods=["POST", "OPTIONS"])
@require_admin
def admin_set_user_active(user_id):
    """启用/禁用用户账号"""
    data = request.get_json(force=True) or {}
    is_active = 1 if data.get("is_active") else 0
    user = db.get_user(user_id)
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    db.set_user_active(user_id, is_active)
    db.add_system_log("info", "admin",
                      f"{'启用' if is_active else '禁用'}用户账号 #{user_id} ({user['name']})")
    return jsonify({"success": True, "is_active": is_active,
                    "message": f"{'已启用' if is_active else '已禁用'} {user['name']}"})


@admin_bp.route("/api/admin/users/<int:user_id>/role", methods=["POST", "OPTIONS"])
@require_admin
def admin_set_user_role(user_id):
    """修改用户角色（teacher / student）"""
    data = request.get_json(force=True) or {}
    role = data.get("role", "")
    user = db.get_user(user_id)
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    if role not in ("teacher", "student"):
        return jsonify({"error": "角色只能是 teacher 或 student"}), 400
    db.set_user_role(user_id, role)
    db.add_system_log("info", "admin",
                      f"修改用户 #{user_id} ({user['name']}) 角色为 {role}")
    return jsonify({"success": True, "role": role})


# ---------------------------------------------------------------------------
# 数据合规导出（管理员审批：pending → approved / rejected）
# ---------------------------------------------------------------------------

_EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))), "export_data")


def _collect_export_payload(export_type: str, user_ids=None, class_id: int = 0):
    """按类型收集导出数据（reports/reasoning/answers/users/concepts）"""
    user_cond, user_params = "", ()
    if user_ids:
        ph = ",".join("?" * len(user_ids))
        user_cond = f" WHERE user_id IN ({ph})"
        user_params = tuple(user_ids)

    if export_type == "reports":
        rows = db._query(
            f"SELECT * FROM learning_reports{user_cond} ORDER BY id DESC LIMIT 1000",
            user_params)
        data = []
        for r in rows:
            try:
                rep = json.loads(r.get("report_json") or "{}")
            except Exception:
                rep = {}
            data.append({
                "id": r["id"], "user_id": r["user_id"], "topic": r["topic"],
                "score": r.get("score", 0), "created_at": r.get("created_at", ""),
                "subject": (rep.get("task_understanding") or {}).get("subject", ""),
                "core_topic": (rep.get("task_understanding") or {}).get("core_topic", ""),
                "mastery_level": (rep.get("mastery_assessment") or {}).get("level", ""),
            })
        return data
    if export_type == "reasoning":
        rows = db._query(
            f"SELECT * FROM reasoning_logs{user_cond} ORDER BY id DESC LIMIT 1000",
            user_params)
        return [{k: r.get(k) for k in ("id", "user_id", "mode", "topic", "step_name",
                                       "model_used", "latency_ms", "status", "created_at")}
                for r in rows]
    if export_type == "answers":
        rows = db._query(
            f"SELECT * FROM answers{user_cond} ORDER BY id DESC LIMIT 1000",
            user_params)
        return [{k: r.get(k) for k in ("id", "user_id", "question", "user_answer",
                                       "correct_answer", "is_correct", "topic",
                                       "subject", "time_spent", "timestamp")}
                for r in rows]
    if export_type == "users":
        rows = db.get_users()
        return [{k: u.get(k) for k in ("id", "name", "role", "username", "is_active", "created_at")}
                for u in rows]
    if export_type == "concepts":
        rows = db._query(
            f"SELECT * FROM concept_understanding{user_cond} ORDER BY id DESC LIMIT 1000",
            user_params)
        return [{k: c.get(k) for k in ("id", "user_id", "node_id", "understanding",
                                       "state", "attempts", "correct_attempts",
                                       "wrong_attempts", "created_at")}
                for c in rows]
    return []


def _dump_export_file(export_type: str, fmt: str, data: list, export_id: int) -> str:
    """把数据写入 export_data/ 目录，返回相对路径"""
    os.makedirs(_EXPORT_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    fname = f"{export_type}_{export_id}_{ts}.{fmt}"
    fpath = os.path.join(_EXPORT_DIR, fname)
    if fmt == "csv":
        import csv
        keys = list(data[0].keys()) if data else ["id"]
        with open(fpath, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for row in data:
                w.writerow({k: row.get(k, "") for k in keys})
    else:
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return fname


@admin_bp.route("/api/admin/exports", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_exports():
    """导出申请列表（含教师发起的申请）"""
    status = request.args.get("status")
    limit = min(int(request.args.get("limit", 50)), 200)
    exports = db.list_data_exports(status=status, limit=limit)
    for e in exports:
        e["can_download"] = bool(e["status"] == "approved" and e.get("file_path"))
    return jsonify({"success": True, "exports": exports})


@admin_bp.route("/api/admin/exports", methods=["POST", "OPTIONS"])
@require_admin
def admin_create_export():
    """管理员直接发起导出（立即生成文件，无需审批——管理员即审批人）"""
    data = request.get_json(force=True) or {}
    export_type = data.get("export_type", "")
    fmt = data.get("format", "json")
    if export_type not in ("reports", "reasoning", "answers", "users", "concepts"):
        return jsonify({"error": "不支持的导出类型"}), 400
    if fmt not in ("json", "csv"):
        return jsonify({"error": "格式只能是 json 或 csv"}), 400
    payload = _collect_export_payload(export_type)
    rec = db.add_data_export(
        requester_id=request.admin["id"], requester_type="admin",
        requester_name=request.admin.get("display_name") or request.admin["username"],
        export_type=export_type, format=fmt, scope="all",
        reason=data.get("reason", ""))
    fname = _dump_export_file(export_type, fmt, payload, rec["id"])
    db.update_data_export_status(rec["id"], "approved",
                                 approver_id=request.admin["id"],
                                 approver_name=request.admin.get("display_name") or request.admin["username"],
                                 file_path=fname)
    return jsonify({"success": True, "export_id": rec["id"],
                    "file_path": fname, "rows": len(payload)})


@admin_bp.route("/api/admin/exports/<int:export_id>/approve", methods=["POST", "OPTIONS"])
@require_admin
def admin_approve_export(export_id):
    """审批导出申请：approve（生成文件）/ reject"""
    data = request.get_json(force=True) or {}
    action = data.get("action", "approve")
    exp = db.get_data_export(export_id)
    if not exp:
        return jsonify({"error": "导出申请不存在"}), 404
    if exp["status"] != "pending":
        return jsonify({"error": "该申请已处理"}), 400
    if action == "approve":
        user_ids = None
        # 教师发起的申请：数据范围=其本班学生（数据权限隔离）
        if exp["requester_type"] == "teacher":
            try:
                students = db.get_students(teacher_id=exp["requester_id"])
                user_ids = [s["id"] for s in students] or None
            except Exception:
                user_ids = None
            if exp.get("class_id"):
                try:
                    class_students = db.get_class_students(exp["class_id"])
                    user_ids = [s["id"] for s in class_students] or None
                except Exception:
                    pass
        elif exp["scope"] == "class" and exp.get("class_id"):
            students = db.get_class_students(exp["class_id"])
            user_ids = [s["id"] for s in students] or None
        payload = _collect_export_payload(exp["export_type"], user_ids=user_ids,
                                          class_id=exp.get("class_id") or 0)
        fname = _dump_export_file(exp["export_type"], exp["format"], payload, export_id)
        db.update_data_export_status(export_id, "approved",
                                     approver_id=request.admin["id"],
                                     approver_name=request.admin.get("display_name") or request.admin["username"],
                                     file_path=fname)
        return jsonify({"success": True, "message": "已批准并生成导出文件",
                        "file_path": fname, "rows": len(payload)})
    db.update_data_export_status(export_id, "rejected",
                                 approver_id=request.admin["id"],
                                 approver_name=request.admin.get("display_name") or request.admin["username"])
    return jsonify({"success": True, "message": "已拒绝"})


@admin_bp.route("/api/admin/exports/<int:export_id>/download", methods=["GET", "OPTIONS"])
@require_admin
def admin_download_export(export_id):
    """下载已批准的导出文件"""
    from flask import send_from_directory
    exp = db.get_data_export(export_id)
    if not exp:
        return jsonify({"error": "导出申请不存在"}), 404
    if exp["status"] != "approved" or not exp.get("file_path"):
        return jsonify({"error": "该导出尚未批准或文件不存在"}), 400
    fpath = os.path.join(_EXPORT_DIR, exp["file_path"])
    if not os.path.isfile(fpath):
        return jsonify({"error": "导出文件已不存在"}), 404
    db.add_system_log("info", "export", f"下载导出文件 #{export_id} ({exp['file_path']})")
    return send_from_directory(_EXPORT_DIR, exp["file_path"], as_attachment=True)


# ---------------------------------------------------------------------------
# P1-4 人工监督：待审批队列（EU AI Act Art.14）
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/interrupts", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_interrupts():
    """待审批中断队列：status=pending / all（含已处理）"""
    from agent_core.observability import get_telemetry
    status = (request.args.get("status") or "pending").lower()
    interrupts = get_telemetry().get_all_interrupts()
    if status == "pending":
        interrupts = [i for i in interrupts if i["status"] == "pending"]
    elif status != "all":
        interrupts = [i for i in interrupts if i["status"] == status]
    # 关联调用链摘要（主题/节点详情）
    for i in interrupts:
        trace = get_telemetry().get_trace(i.get("trace_id", ""))
        i["topic"] = (trace or {}).get("topic", "")
        i["user_id"] = (trace or {}).get("user_id", "")
    return jsonify({"success": True, "interrupts": interrupts,
                     "pending_count": sum(1 for x in interrupts if x["status"] == "pending")})


@admin_bp.route("/api/admin/interrupts/<trace_id>/approve", methods=["POST", "OPTIONS"])
@require_admin
def admin_approve_interrupt(trace_id):
    """审批放行：approved"""
    from agent_core.observability import get_telemetry
    result = get_telemetry().resolve_interrupt(
        trace_id, "approved", request.admin.get("username") or "admin")
    if "error" in result:
        return jsonify(result), 404
    db.add_system_log("info", "interrupt",
                      f"管理员放行人工审核 trace={trace_id}",
                      "审批人: " + str(request.admin.get("username")))
    return jsonify({"success": True, "message": "已放行", **result})


@admin_bp.route("/api/admin/interrupts/<trace_id>/reject", methods=["POST", "OPTIONS"])
@require_admin
def admin_reject_interrupt(trace_id):
    """审批拒绝：rejected"""
    from agent_core.observability import get_telemetry
    result = get_telemetry().resolve_interrupt(
        trace_id, "rejected", request.admin.get("username") or "admin")
    if "error" in result:
        return jsonify(result), 404
    db.add_system_log("info", "interrupt",
                      f"管理员拒绝人工审核 trace={trace_id}",
                      "审批人: " + str(request.admin.get("username")))
    return jsonify({"success": True, "message": "已拒绝", **result})


# ---------------------------------------------------------------------------
# P1-4 成本报告
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/costs", methods=["GET", "OPTIONS"])
@require_admin
def admin_cost_report():
    """成本报告：汇总 + 按模型分布 + 按 Agent 分布 + 趋势"""
    from agent_core.observability import get_telemetry
    from agent_core.cost_tracker import get_cost_tracker
    telemetry = get_telemetry()
    summary = telemetry.get_cost_summary()
    tracker = get_cost_tracker()
    days = int(request.args.get("days", 7))
    try:
        trend = tracker.get_daily_trend(days=days)
        by_agent = tracker.get_cost_by_agent()
        anomalies = tracker.detect_anomalies()
    except Exception:
        trend, by_agent, anomalies = [], {}, []
    # Agent 分布兜底：从 telemetry 缓冲按 agent_id 聚合
    if not by_agent:
        for c in telemetry.get_calls(limit=5000):
            if c.get("type") == "audit" or "cost" not in c:
                continue
            aid = c.get("agent_id", "unknown")
            by_agent.setdefault(aid, {"calls": 0, "cost": 0.0})
            by_agent[aid]["calls"] += 1
            by_agent[aid]["cost"] += c.get("cost", 0)
    return jsonify({
        "success": True,
        "summary": summary,
        "by_agent": by_agent,
        "trend": trend,
        "anomalies": anomalies,
        "days": days,
    })


# ---------------------------------------------------------------------------
# P1-4 权重配置（Agent 动态权重）
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/weights", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_weights():
    """Agent 权重配置列表（base / dynamic / 调用统计）"""
    from agent_core.weight_manager import get_weight_manager
    weights = get_weight_manager().get_weights()
    return jsonify({"success": True, "weights": weights})


@admin_bp.route("/api/admin/weights/<agent_id>", methods=["POST", "OPTIONS"])
@require_admin
def admin_set_weight(agent_id):
    """设置 Agent 基础权重（动态权重 = base × success × latency）"""
    from agent_core.weight_manager import get_weight_manager
    data = request.get_json(force=True) or {}
    try:
        base_weight = float(data.get("base_weight", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "base_weight 必须是数字"}), 400
    if not (0 < base_weight <= 10):
        return jsonify({"error": "base_weight 必须在 (0, 10] 范围"}), 400
    get_weight_manager().set_base_weight(agent_id, base_weight)
    db.add_system_log("info", "weights",
                      f"设置 Agent 权重: {agent_id} → {base_weight}")
    return jsonify({"success": True, "agent_id": agent_id,
                    "base_weight": base_weight,
                    "message": f"{agent_id} 基础权重已更新为 {base_weight}"})


@admin_bp.route("/api/admin/weights/recalculate", methods=["POST", "OPTIONS"])
@require_admin
def admin_recalc_weights():
    """批量重算所有 Agent 动态权重"""
    from agent_core.weight_manager import get_weight_manager
    results = get_weight_manager().batch_update_weights()
    db.add_system_log("info", "weights", "批量重算 Agent 动态权重",
                      str(len(results)))
    return jsonify({"success": True, "updated": len(results), "results": results})


# ---------------------------------------------------------------------------
# P1-5 外部 MCP Server 管理
# ---------------------------------------------------------------------------

def _mcp_config_to_dict(config) -> dict:
    """ExternalMCPServerConfig → dict（enabled 保持 bool，args 保持 list）"""
    return {
        "server_name": config.server_name,
        "transport": config.transport,
        "url": config.url,
        "command": config.command,
        "args": list(config.args or []),
        "enabled": bool(config.enabled),
        "description": config.description,
    }


@admin_bp.route("/api/admin/mcp-servers", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_mcp_servers():
    """外部 MCP 服务器配置列表 + 连接状态概览"""
    from agent_core.mcp_external import get_external_mcp_registry
    registry = get_external_mcp_registry()
    servers = [_mcp_config_to_dict(c) for c in registry.list_servers()]
    return jsonify({"success": True, "servers": servers,
                    "status": registry.get_status()})


@admin_bp.route("/api/admin/mcp-servers", methods=["POST", "OPTIONS"])
@require_admin
def admin_add_mcp_server():
    """注册外部 MCP 服务器（http / stdio）"""
    from agent_core.mcp_external import (
        get_external_mcp_registry, ExternalMCPServerConfig)
    data = request.get_json(force=True) or {}
    server_name = (data.get("server_name") or "").strip()
    if not server_name:
        return jsonify({"error": "缺少 server_name 字段"}), 400
    transport = (data.get("transport") or "http").strip().lower()
    if transport not in ("http", "stdio"):
        return jsonify({"error": "transport 只能是 http 或 stdio"}), 400
    url = (data.get("url") or "").strip()
    command = (data.get("command") or "").strip()
    if transport == "http" and not url:
        return jsonify({"error": "http 传输需提供 url"}), 400
    if transport == "stdio" and not command:
        return jsonify({"error": "stdio 传输需提供 command"}), 400
    args = data.get("args") or []
    if not isinstance(args, list):
        return jsonify({"error": "args 必须是数组"}), 400
    config = ExternalMCPServerConfig(
        server_name=server_name,
        transport=transport,
        url=url,
        command=command,
        args=args,
        enabled=bool(data.get("enabled", True)),
        description=data.get("description") or "",
    )
    registry = get_external_mcp_registry()
    result = registry.add_server(config)
    if "error" in result:
        return jsonify({"error": result["error"]}), 400
    db.add_system_log("info", "mcp", f"注册 MCP Server: {server_name} ({transport})")
    return jsonify({"success": True, "server": _mcp_config_to_dict(config)})


@admin_bp.route("/api/admin/mcp-servers/<server_name>/toggle", methods=["POST", "OPTIONS"])
@require_admin
def admin_toggle_mcp_server(server_name):
    """启用/停用外部 MCP 服务器"""
    current = db.get_mcp_server(server_name)
    if not current:
        return jsonify({"error": "MCP Server 不存在"}), 404
    new_enabled = 0 if current.get("enabled") else 1
    db.update_mcp_server(server_name, enabled=new_enabled)
    return jsonify({"success": True, "enabled": new_enabled})


@admin_bp.route("/api/admin/mcp-servers/<server_name>/test", methods=["POST", "OPTIONS"])
@require_admin
def admin_test_mcp_server(server_name):
    """测试连接外部 MCP 服务器并枚举工具"""
    from agent_core.mcp_external import get_external_mcp_registry
    registry = get_external_mcp_registry()
    client = registry.connect_server(server_name)
    if isinstance(client, dict) and "error" in client:
        return jsonify({"success": False, "error": client["error"]})
    tools = registry.list_tools(server_name)
    if isinstance(tools, dict) and tools.get("isError"):
        content = tools.get("content") or []
        error = "".join(item.get("text", "") for item in content
                        if isinstance(item, dict))
        return jsonify({"success": False, "error": error or "连接失败"})
    return jsonify({"success": True, "tools": tools})


@admin_bp.route("/api/admin/mcp-servers/<server_name>", methods=["DELETE", "OPTIONS"])
@require_admin
def admin_delete_mcp_server(server_name):
    """删除外部 MCP 服务器配置"""
    from agent_core.mcp_external import get_external_mcp_registry
    if not db.get_mcp_server(server_name):
        return jsonify({"error": "MCP Server 不存在"}), 404
    registry = get_external_mcp_registry()
    registry.delete_server(server_name)
    db.add_system_log("info", "mcp", f"删除 MCP Server: {server_name}")
    return jsonify({"success": True, "message": "已删除"})


# ---------------------------------------------------------------------------
# P2-12 分布式任务队列
# ---------------------------------------------------------------------------

def _task_to_api(task: Dict, full: bool = False) -> Dict:
    """任务记录 → API 响应（列表视图截断 payload/result，详情视图返回完整）"""
    if not task:
        return {}
    if not full:
        payload = task.get("payload") or {}
        return {
            "task_id": task.get("task_id"),
            "task_type": task.get("task_type"),
            "status": task.get("status"),
            "priority": task.get("priority"),
            "retries": task.get("retries"),
            "max_retries": task.get("max_retries"),
            "timeout": task.get("timeout"),
            "created_at": task.get("created_at"),
            "finished_at": task.get("finished_at") or "",
            "error": (task.get("error") or "")[:300],
            "topic": payload.get("topic", "") if isinstance(payload, dict) else "",
        }
    return {
        "task_id": task.get("task_id"),
        "task_type": task.get("task_type"),
        "status": task.get("status"),
        "priority": task.get("priority"),
        "retries": task.get("retries"),
        "max_retries": task.get("max_retries"),
        "timeout": task.get("timeout"),
        "created_at": task.get("created_at"),
        "started_at": task.get("started_at") or "",
        "finished_at": task.get("finished_at") or "",
        "error": (task.get("error") or "")[:2000],
        "payload": task.get("payload") or {},
        "result": task.get("result") or {},
    }


@admin_bp.route("/api/admin/tasks", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_tasks():
    """任务队列：列表（按状态/类型筛选）+ 统计 + worker 状态"""
    from agent_core.task_queue import get_task_queue
    q = get_task_queue()
    status = request.args.get("status", "").strip()
    task_type = request.args.get("task_type", "").strip()
    limit = request.args.get("limit", 50)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 50
    tasks = [_task_to_api(t) for t in q.list(
        status=status, task_type=task_type, limit=limit)]
    return jsonify({"success": True, "tasks": tasks, "stats": q.stats()})


@admin_bp.route("/api/admin/tasks", methods=["POST", "OPTIONS"])
@require_admin
def admin_submit_task():
    """提交异步任务"""
    from agent_core.task_queue import get_task_queue
    data = request.get_json(force=True) or {}
    task_type = (data.get("task_type") or "").strip()
    if not task_type:
        return jsonify({"error": "缺少 task_type 字段"}), 400
    payload = data.get("payload") or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "payload 必须是对象"}), 400
    try:
        result = get_task_queue().submit(
            task_type=task_type,
            payload=payload,
            priority=int(data.get("priority", 5)),
            max_retries=int(data.get("max_retries", 1)),
            delay=float(data.get("delay", 0)),
            timeout=int(data.get("timeout", 300)),
        )
    except (TypeError, ValueError) as e:
        return jsonify({"error": f"参数格式错误: {e}"}), 400
    if not result.get("success"):
        return jsonify({"error": result.get("error", "提交失败")}), 400
    db.add_system_log("info", "task_queue",
                      f"提交任务: {task_type} -> {result['task_id']}")
    return jsonify({"success": True, "task": result})


@admin_bp.route("/api/admin/tasks/<task_id>", methods=["GET", "OPTIONS"])
@require_admin
def admin_get_task(task_id):
    """查询任务状态与完整结果"""
    from agent_core.task_queue import get_task_queue
    task = get_task_queue().get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify({"success": True, "task": _task_to_api(task, full=True)})


@admin_bp.route("/api/admin/tasks/<task_id>/cancel", methods=["POST", "OPTIONS"])
@require_admin
def admin_cancel_task(task_id):
    """取消 pending 任务"""
    from agent_core.task_queue import get_task_queue
    result = get_task_queue().cancel(task_id)
    if not result.get("success"):
        return jsonify({"error": result.get("error", "取消失败")}), 400
    return jsonify(result)


@admin_bp.route("/api/admin/tasks/process", methods=["POST", "OPTIONS"])
@require_admin
def admin_process_tasks():
    """手动消费队列：同步执行当前所有到期任务（未启动后台 worker 时使用）"""
    from agent_core.task_queue import get_task_queue
    q = get_task_queue()
    processed = q.run_pending_now()
    return jsonify({"success": True, "processed": processed, "stats": q.stats()})
