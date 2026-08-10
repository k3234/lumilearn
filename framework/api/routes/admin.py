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
    # 隐藏密码哈希
    for u in users:
        u["has_password"] = bool(u.get("password_hash", ""))
        u.pop("password_hash", None)
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
