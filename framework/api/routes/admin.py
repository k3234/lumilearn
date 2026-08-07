# -*- coding: utf-8 -*-
"""
LumiLearn 管理员 API 路由
认证 / 用户管理 / 模型管理 / Agent管理 / 系统监控
"""
import json
import logging
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

@admin_bp.route("/api/admin/overview", methods=["GET", "OPTIONS"])
@require_admin
def admin_overview():
    """系统总览：用户数、工作流数、检测数、模型状态、Agent 状态、日志数"""
    users = db.get_users()

    # 说明：get_user_workflows/get_user_detections 的 user_id 为必填参数，
    # 传 None 会导致 WHERE user_id = NULL 恒空（结果恒为 0），
    # 因此这里直接用 COUNT 查询全表行数，保证 overview 在真实数据库上可用。
    workflows_row = db._query_one("SELECT COUNT(*) as c FROM learning_workflows") if hasattr(db, "get_user_workflows") else None
    detections_row = db._query_one("SELECT COUNT(*) as c FROM output_detections") if hasattr(db, "get_user_detections") else None
    total_workflows = workflows_row["c"] if workflows_row else 0
    total_detections = detections_row["c"] if detections_row else 0

    agents = db.get_agents()
    logs = db.get_system_logs(limit=5)

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
        "recent_logs": logs,
    })


# ---------------------------------------------------------------------------
# 用户管理
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/users", methods=["GET", "OPTIONS"])
@require_admin
def admin_list_users():
    role = request.args.get("role")
    users = db.get_users(role=role)
    return jsonify({"success": True, "users": users})


@admin_bp.route("/api/admin/users", methods=["POST", "OPTIONS"])
@require_admin
def admin_create_user():
    data = request.get_json(force=True) or {}
    name = data.get("name", "")
    role = data.get("role", "student")
    if not name:
        return jsonify({"error": "缺少 name 字段"}), 400
    user = db.add_user(name, role=role)
    db.add_system_log("info", "admin", f"管理员创建用户: {name} ({role})")
    return jsonify({"success": True, "user": user})


@admin_bp.route("/api/admin/users/<int:user_id>", methods=["DELETE", "OPTIONS"])
@require_admin
def admin_delete_user(user_id):
    ok = db.delete_user(user_id)
    if not ok:
        return jsonify({"error": "用户不存在"}), 404
    db.add_system_log("info", "admin", f"管理员删除用户 id={user_id}")
    return jsonify({"success": True, "message": "用户已删除"})


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
