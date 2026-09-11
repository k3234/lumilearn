# -*- coding: utf-8 -*-
"""
灵学 lumilearn - 主API服务器
整合所有API端点，支持多端口，配置从 framework.core.config 加载

架构：两端口模式
- 18080: 管理门户（统一入口 index.html + /admin /teacher /student /analytics + 所有API端点）
- 18081: REST API服务（纯API，无前端）

作者：lumilearn AI自动化专家
版本：0.2.0
日期：2026-06-02
"""

import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Tuple

from flask import Flask, jsonify, redirect, request, send_from_directory, session

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# 静态资源目录（本地化 CDN 库：KaTeX/Chart.js/highlight.js/reveal.js）
# 本地：项目根 static/；远程：tianhong/static/（与模板双目录保持一致）
STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.exists():
    STATIC_DIR = BASE_DIR / "tianhong" / "static"
if not STATIC_DIR.exists():
    STATIC_DIR = BASE_DIR / "remote" / "static"


def _template_path(name: str):
    """兼容两种部署目录：本地 remote/templates 与远程 tianhong/templates"""
    for base in (BASE_DIR / "remote" / "templates", BASE_DIR / "tianhong" / "templates"):
        p = base / name
        if p.exists():
            return p
    return BASE_DIR / "remote" / "templates" / name  # 兜底：保持 .exists() 调用安全

from framework.api.routes import (
    admin_bp,
    animation_bp,
    auth_bp,
    chat_bp,
    feynman_bp,
    learn_bp,
    mindmap_bp,
    models_bp,
    ocr_bp,
    payment_bp,
    providers_bp,
    review_bp,
    security_bp,
    slides_bp,
    speech_bp,
    voicebox_bp,
    create_analytics_bp,
    create_student_learn_bp,
    create_student_platform_bp,
    create_teacher_portal_bp,
)
from framework.core.config import get_config, get_app_secret_key, register_csrf_guard
from framework.database import db
from framework.models.ollama_provider import get_ollama_provider
from framework.models.registry import get_registry
from framework.services.chat_service import get_chat_service

# 学生端费曼学习 Agent（轻量包装，惰性单例）
_agent = None


def _get_student_agent():
    """获取/创建学生端学习 Agent 单例（LumiLearnAgent 为轻量包装，无重依赖）。"""
    global _agent
    if _agent is None:
        from lumilearn_agent import LumiLearnAgent
        _agent = LumiLearnAgent()
    return _agent


def _local_hosts() -> set:
    """本机可访问的主机名集合：localhost + 127.0.0.1 + 服务器局域网 IP。

    演示环境通常以局域网 IP（如 http://192.168.x.x:18080）访问页面，前端跨端口
    调用 API 时 Origin 即该 IP，因此必须动态纳入 CORS/CSRF 白名单，否则功能被拦截。
    """
    hosts = {"localhost", "127.0.0.1"}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip:
            hosts.add(ip)
    except Exception:
        pass
    return hosts


def _get_cors_origins() -> list:
    """CORS 白名单来源。

    - 优先读取环境变量 CORS_ALLOWED_ORIGINS（逗号分隔的完整 Origin，如
      `http://localhost:18080,https://learn.example.com`）；
    - 默认放行本机各端口（localhost/127.0.0.1 + 服务器局域网 IP）；
    - 不再使用 `*` 通配：避免任意恶意网站跨域调用本服务 API。
    """
    raw = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    # 端口整合后仅保留两端口：18080 管理门户 + 18081 REST API 服务
    local_ports = (18080, 18081)
    return [f"http://{h}:{p}" for h in sorted(_local_hosts()) for p in local_ports]


def _origin_allowed(origin: str) -> bool:
    """Origin 是否在白名单内（无 Origin 视为同源请求，放行）。"""
    if not origin:
        return True
    return origin in _get_cors_origins()


def create_app(debug: bool = None, template_dir: str = None, homepage: str = "terminal") -> Flask:
    """
    创建Flask应用

    参数：
        debug: 是否调试模式，None则从配置读取
        template_dir: 模板目录路径，None则自动检测
        homepage: 首页类型：terminal(终端) / api(REST API概览) / models(模型管理面板)

    返回：
        配置好的Flask应用
    """
    config = get_config()

    if debug is None:
        debug = config.get("debug", False)

    if template_dir is None:
        template_dir = str(BASE_DIR / "remote" / "templates")
        if not os.path.isdir(template_dir):
            template_dir = str(BASE_DIR / "tianhong" / "templates")

    app = Flask(__name__, template_folder=template_dir,
                static_folder=str(STATIC_DIR), static_url_path="/static")
    app.debug = debug

    # 会话密钥 + CSRF 防护（端口整合后：管理员/教师/学生共用同一 cookie 会话）
    app.secret_key = get_app_secret_key("LUMILEARN_SECRET_KEY", "LumiLearn Portal")
    register_csrf_guard(app)

    # 请求体上限 + 可信 Host（防止大体积上传/ Host 头注入）
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB
    # 可信 Host 仅在显式配置 LUMILEARN_TRUSTED_HOSTS 时启用（逗号分隔）：
    # 禁止在仓库中硬编码任何真实内网 IP / 主机地址，部署方按需注入。
    _trusted_hosts = [
        h.strip() for h in os.environ.get("LUMILEARN_TRUSTED_HOSTS", "").split(",") if h.strip()
    ]
    if _trusted_hosts:
        app.config["TRUSTED_HOSTS"] = _trusted_hosts
    # 反向代理部署时启用 ProxyFix（生产通过 LUMILEARN_PROXY_ENABLED=true 开启）
    if os.environ.get("LUMILEARN_PROXY_ENABLED", "").lower() == "true":
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    @app.before_request
    def handle_options():
        """全局OPTIONS处理（CORS 预检：仅放行白名单 Origin）"""
        from flask import request as req
        if req.method == "OPTIONS":
            resp = app.make_default_options_response()
            origin = req.headers.get("Origin", "")
            if _origin_allowed(origin):
                resp.headers["Access-Control-Allow-Origin"] = origin
                resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
                resp.headers["Access-Control-Max-Age"] = "3600"
            return resp

    @app.after_request
    def add_security_headers(response):
        """全局 CORS + 安全响应头（防御 XSS/点击劫持/MIME 嗅探）"""
        origin = request.headers.get("Origin", "")
        if _origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        response.headers["X-Framework"] = "LumiLearn"
        response.headers["X-Version"] = config.get("version", "1.0.0")
        # HTML 页面禁用缓存：前端模板每次部署后必须立即生效（否则浏览器缓存旧版面板）
        if "Content-Type" in response.headers and "text/html" in response.headers["Content-Type"]:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        # CSP：页面为单文件 HTML + 内联 JS + jsdelivr CDN，需放行内联脚本与 CDN 资源
        if "Content-Type" in response.headers and "text/html" in response.headers["Content-Type"]:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "img-src 'self' data: blob:; "
                "connect-src 'self' http://localhost:* http://127.0.0.1:*; "
                "font-src 'self' data: https://cdn.jsdelivr.net https://fonts.gstatic.com; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "object-src 'none'"
            )
        return response

    app.register_blueprint(chat_bp)
    app.register_blueprint(speech_bp)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(feynman_bp)
    app.register_blueprint(voicebox_bp)
    app.register_blueprint(animation_bp)
    app.register_blueprint(providers_bp)
    app.register_blueprint(slides_bp)
    app.register_blueprint(mindmap_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(security_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(learn_bp)

    # 端口整合：教师端 / 分析仪表盘 / 学生端（API 复用统一认证 + 前端静态挂 /student）
    app.register_blueprint(create_teacher_portal_bp())
    app.register_blueprint(create_analytics_bp())
    app.register_blueprint(create_student_learn_bp(_get_student_agent(), include_auth=False))
    app.register_blueprint(create_student_platform_bp(), url_prefix="/student")

    # 挂载 output 静态目录（动画生成视频）
    @app.route('/output/<path:filename>')
    def serve_output(filename):
        output_dir = BASE_DIR / "output"
        return send_from_directory(str(output_dir), filename)

    @app.route("/")
    def index():
        """首页：统一入口门户（index.html）或按应用类型返回对应页面"""
        # REST API 端口：返回服务状态与端点概览
        if homepage == "api":
            endpoints = sorted(str(r) for r in app.url_map.iter_rules() if str(r).startswith("/api/"))
            return jsonify({
                "framework": "LumiLearn",
                "service": "REST API",
                "version": config.get("version", "1.0.0"),
                "api_endpoints": endpoints,
                "usage": "访问 /api/status 查看服务健康状态；支持费曼教学(feynman)、对话(chat)、推理记录(reasoning-logs)等接口"
            })
        # 模型管理端口：重定向到 Admin 面板（模型管理页）
        if homepage == "models":
            return redirect("/admin")
        # 统一入口门户（优先）
        idx_path = _template_path("index.html")
        if idx_path.exists():
            content = idx_path.read_text(encoding="utf-8")
            resp = app.make_response(content)
            resp.headers["Content-Type"] = "text/html; charset=utf-8"
            return resp
        # 回退：终端页面
        html_path = _template_path("lumiterm.html")
        if html_path.exists():
            content = html_path.read_text(encoding="utf-8")
            response = app.make_response(content)
            response.headers["Content-Type"] = "text/html; charset=utf-8"
            return response
        return "<h1>LumiLearn API Server</h1><p>index.html not found</p>", 404

    def _render_template(html_path, not_found):
        """渲染模板；缺文件返回 404 str。"""
        if html_path.exists():
            content = html_path.read_text(encoding="utf-8")
            response = app.make_response(content)
            response.headers["Content-Type"] = "text/html; charset=utf-8"
            return response
        return not_found, 404

    def _page_role(*roles):
        """页面级角色守卫：会话中未登录或角色不符 → 重定向首页。"""
        role = session.get("role") or session.get("user_role") or ""
        # 无会话凭据时尝试 token（页面直链偶发仅带 token 头）
        if not role:
            r = session.get("user_id")
            user = (db.get_user(r) if r else None) or {}
            role = user.get("role", "") if isinstance(user, dict) else ""
        if role in roles:
            return True
        return False

    @app.route("/admin")
    def admin_page():
        """管理员管理面板（v0.2.0 新版控制台；仅 admin/super_admin）"""
        if not _page_role("admin", "super_admin"):
            return redirect("/")
        return _render_template(_template_path("admin_dashboard.html"),
                                "<h1>LumiLearn Admin</h1><p>admin_dashboard.html not found</p>")

    @app.route("/admin/org")
    def admin_org_page():
        """管理端 · 用户与组织管理（v0.2.0；仅 admin/super_admin）"""
        if not _page_role("admin", "super_admin"):
            return redirect("/")
        return _render_template(_template_path("admin_org.html"),
                                "<h1>LumiLearn Admin</h1><p>admin_org.html not found</p>")

    @app.route("/admin/ops")
    def admin_ops_page():
        """管理端 · 容量与并发配置（v0.2.0；仅 admin/super_admin）"""
        if not _page_role("admin", "super_admin"):
            return redirect("/")
        return _render_template(_template_path("admin_ops.html"),
                                "<h1>LumiLearn Admin</h1><p>admin_ops.html not found</p>")

    @app.route("/admin/console")
    def admin_console_page():
        """管理端 · 深度控制台（旧全功能管理面板，保留）"""
        if not _page_role("admin", "super_admin"):
            return redirect("/")
        return _render_template(_template_path("admin.html"),
                                "<h1>LumiLearn Admin</h1><p>admin.html not found</p>")

    @app.route("/admin/traces")
    def admin_traces_page():
        """Agent 调用链追踪面板（仅 admin/super_admin）"""
        if not _page_role("admin", "super_admin"):
            return redirect("/")
        return _render_template(_template_path("admin_traces.html"),
                                "<h1>LumiLearn Traces</h1><p>admin_traces.html not found</p>")

    def _serve_html(template_name: str, not_found: str, roles=None):
        """渲染统一门户模板页；指定 roles 时做页面级角色守卫。"""
        if roles and not _page_role(*roles):
            return redirect("/")
        return _render_template(_template_path(template_name), not_found)

    @app.route("/teacher")
    def teacher_page():
        """教师端入口（v0.2.0 新版仪表盘；仅 teacher/admin）"""
        return _serve_html("teacher_dashboard.html",
                           "<h1>LumiLearn Teacher</h1><p>teacher_dashboard.html not found</p>",
                           roles=("teacher", "admin", "super_admin"))

    @app.route("/teacher/class")
    def teacher_class_page():
        """教师端 · 班级与学生管理（v0.2.0）"""
        return _serve_html("teacher_class.html",
                           "<h1>LumiLearn Teacher</h1><p>teacher_class.html not found</p>",
                           roles=("teacher", "admin", "super_admin"))

    @app.route("/teacher/tasks")
    def teacher_tasks_page():
        """教师端 · 任务与教学资源（v0.2.0）"""
        return _serve_html("teacher_tasks.html",
                           "<h1>LumiLearn Teacher</h1><p>teacher_tasks.html not found</p>",
                           roles=("teacher", "admin", "super_admin"))

    @app.route("/teacher/console")
    def teacher_console_page():
        """教师端 · 深度控制台（旧全功能面板，保留）"""
        return _serve_html("teacher.html",
                           "<h1>LumiLearn Teacher</h1><p>teacher.html not found</p>",
                           roles=("teacher", "admin", "super_admin"))

    @app.route("/analytics")
    def analytics_page():
        """学习分析仪表盘入口（原 analytics_dashboard.py:18090 整合进统一门户；teacher/admin 可见）"""
        return _serve_html("analytics_dashboard.html",
                           "<h1>LumiLearn Analytics</h1><p>analytics_dashboard.html not found</p>",
                           roles=("teacher", "admin", "super_admin"))

    @app.route("/learn")
    def learn_page():
        """学习页面：重定向到互动课堂"""
        html_path = _template_path("classroom.html")
        if html_path.exists():
            content = html_path.read_text(encoding="utf-8")
            response = app.make_response(content)
            response.headers["Content-Type"] = "text/html; charset=utf-8"
            return response
        # 回退到动画学习页面
        html_path = _template_path("animation_learn.html")
        if html_path.exists():
            content = html_path.read_text(encoding="utf-8")
            response = app.make_response(content)
            response.headers["Content-Type"] = "text/html; charset=utf-8"
            return response
        return "<h1>LumiLearn Classroom</h1><p>课堂界面加载中...</p>", 404

    @app.route("/classroom")
    def classroom():
        """互动课堂页面（OpenMAIC 风格）"""
        html_path = _template_path("classroom.html")
        if html_path.exists():
            content = html_path.read_text(encoding="utf-8")
            response = app.make_response(content)
            response.headers["Content-Type"] = "text/html; charset=utf-8"
            return response
        return "<h1>LumiLearn Classroom</h1><p>课堂界面加载中...</p>", 404

    @app.route("/test/video")
    def test_video_page():
        """视频播放诊断测试页面"""
        html_path = _template_path("test_video.html")
        if html_path.exists():
            content = html_path.read_text(encoding="utf-8")
            response = app.make_response(content)
            response.headers["Content-Type"] = "text/html; charset=utf-8"
            return response
        return "<h1>Video Test</h1><p>测试页面未找到</p>", 404

    @app.route("/chat")
    def chat_page():
        """终端聊天页面（高级模式）"""
        html_path = _template_path("lumiterm.html")
        if html_path.exists():
            content = html_path.read_text(encoding="utf-8")
            response = app.make_response(content)
            response.headers["Content-Type"] = "text/html; charset=utf-8"
            return response
        return "<h1>LumiTerminal</h1><p>终端界面加载中...</p>", 404

    @app.route("/health")
    def health():
        """健康检查端点"""
        try:
            chat_service = get_chat_service()
            result = chat_service.health_check()
            result["version"] = config.get("version", "1.0.0")
            result["framework"] = "LumiLearn"
            return jsonify(result)
        except Exception as e:
            return jsonify({
                "status": "error",
                "version": config.get("version", "1.0.0"),
                "framework": "LumiLearn",
                "error": str(e)
            }), 500

    @app.route("/api/status")
    def api_status():
        """服务器状态"""
        try:
            chat_service = get_chat_service()
            health = chat_service.health_check()
            version = config.get("version", "1.0.0")

            # 自定义模型统计
            custom_models = chat_service.list_custom_models()
            custom_models_count = len(custom_models)

            # 当前活跃模型版本
            active_model_version = chat_service.get_model_version()

            # 训练中任务
            from framework.api.routes.models import training_tasks
            training_in_progress = any(
                t.get("status") == "running" for t in training_tasks.values()
            )

            return jsonify({
                "version": version,
                "mode": "framework",
                "default_model": health.get("default_model"),
                "gateway": "online" if health.get("status") == "healthy" else "offline",
                "feynman_available": health.get("feynman_available"),
                "models_count": health.get("models", 0),
                "custom_models_count": custom_models_count,
                "active_model_version": active_model_version,
                "training_in_progress": training_in_progress,
            })
        except Exception as e:
            return jsonify({
                "version": config.get("version", "1.0.0"),
                "mode": "framework",
                "gateway": "offline",
                "error": str(e)
            })

    # 统一 404 / 500 错误处理（API 请求返回友好 JSON，页面请求渲染 404.html）
    from framework.api.errors import register_error_handlers
    register_error_handlers(app)

    return app


def get_server_ports() -> Dict[str, int]:
    """从配置获取端口配置，默认两端口；port_settings（Admin 端口管理）优先"""
    config = get_config()
    # config 为 dict：从 server 配置节读取端口，缺失时回退默认两端口
    server_conf = config.get("server", {})
    ports = {
        "portal": server_conf.get("terminal_port", 18080),
        "api": server_conf.get("api_port", 18081),
    }
    if not ports.get("portal"):
        ports = {
            "portal": 18080,
            "api": 18081,
        }
    # Admin 端口管理保存的 port_settings 优先（用户可自定义端口号）
    try:
        from framework.services.provider_service import get_provider_service
        ps = get_provider_service().get_port_settings()
        mapping = {"portal": "terminal", "api": "api"}
        for key, port_key in mapping.items():
            cfg = ps.get(port_key, {})
            if cfg.get("port"):
                ports[key] = int(cfg["port"])
    except Exception:
        pass
    return ports


def init_model_registry():
    """初始化模型注册中心"""
    config = get_config()
    registry = get_registry()

    ollama = get_ollama_provider()
    registry.register(
        name="ollama_local",
        provider=ollama,
        alias="ollama",
        metadata={
            "default": True,
            "type": "ollama",
            "base_url": ollama.base_url
        }
    )

    logger = __import__("logging").getLogger("lumilearn.server")
    logger.info(f"[Server] 模型注册中心已初始化: {registry}")

    return registry


def print_endpoints(app: Flask) -> None:
    """打印所有已注册的端点"""
    print("\n" + "=" * 60)
    print("📋 已注册API端点:")
    print("-" * 60)
    routes: List[Tuple[str, str]] = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        routes.append((str(rule), methods))

    routes.sort(key=lambda x: x[0])
    for path, methods in routes:
        if methods:
            print(f"  {methods:<20} {path}")
    print("=" * 60 + "\n")


def run_server(port: int = None, host: str = "0.0.0.0", multi_port: bool = False):
    """
    启动服务器

    参数：
        port: 端口，None则使用配置中的 portal 端口
        host: 监听地址
        multi_port: 是否启动两端口（portal + api）
    """
    # 全新环境首次启动：先建库建表，避免蓝图初始化阶段查询尚不存在的表
    db.init()
    app = create_app()
    ports = get_server_ports()

    if port is None:
        port = ports.get("portal", 18080)

    config = get_config()
    version = config.get("version", "1.0.0")

    init_model_registry()

    print("\n" + "=" * 60)
    print("🚀 LumiLearn API Server (Framework Mode)")
    print("=" * 60)
    print(f"  Version: {version}")
    print(f"  Debug: {app.debug}")
    print(f"  Host: {host}")
    print(f"  Base: {BASE_DIR}")
    print("-" * 60)
    print("  Port 配置（两端口模式）:")
    print(f"    portal: {ports.get('portal', 18080)}  (管理门户：总入口 + 教师/学生/仪表盘)")
    print(f"    api:    {ports.get('api', 18081)}  (REST API 服务)")
    print("-" * 60)
    print(f"  UI: http://localhost:{port}/")
    print(f"  API: http://localhost:{port}/api/status")
    print("-" * 60)

    print_endpoints(app)

    if multi_port:
        _start_multi_port(host, ports, app)
    else:
        print(f"▶  启动单端口服务: http://{host}:{port}")
        app.run(host=host, port=port, threaded=True, debug=app.debug)


def _start_multi_port(host: str, ports: Dict[str, int], app: Flask):
    """启动两端口服务（管理门户 + REST API）"""
    portal_port = ports.get("portal", 18080)
    api_port = ports.get("api", 18081)

    print("▶  启动两端口服务:")
    print(f"   管理门户: http://{host}:{portal_port}")
    print(f"   REST API: http://{host}:{api_port}")

    api_app = create_app(homepage="api")

    def run_app(flask_app, port, name):
        print(f"  [{name}] 启动端口 {port}...")
        try:
            flask_app.run(host=host, port=port, threaded=True,
                          debug=flask_app.debug, use_reloader=False)
        except Exception as e:
            print(f"  [{name}] 端口 {port} 启动失败: {e}")

    threads = []
    for flask_app, port, name in [
        (app, portal_port, "Portal"),
        (api_app, api_port, "API")
    ]:
        t = threading.Thread(target=run_app, args=(flask_app, port, name),
                             daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.5)

    print("\n  两端口服务已启动。按 Ctrl+C 停止所有服务。\n")

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n  正在停止所有服务...")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LumiLearn API Server")
    parser.add_argument("--port", type=int, default=None,
                        help="端口（默认: 从config/framework.yaml读取，回退到18080）")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="监听地址（默认: 0.0.0.0）")
    parser.add_argument("--multi-port", action="store_true",
                        help="启动两端口服务（18080 管理门户 / 18081 REST API）")
    parser.add_argument("--debug", action="store_true",
                        help="调试模式")
    args = parser.parse_args()

    run_server(port=args.port, host=args.host, multi_port=args.multi_port)
