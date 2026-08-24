#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 学生端学习平台（Student Portal）
============================================
独立端口服务（默认 5010），将学生端原型前端接入真实后端：

- 前端：prototypes/student-learning-platform/ 静态原型（注入 __LUMILEARN_REAL__ 标志走真实 API）
- 后端：共享费曼学习 Blueprint（framework/api/routes/student_learn.py）
    POST /api/auth/login · GET /api/auth/me · POST /api/auth/logout   （users 表登录）
    POST /api/learn/start      — 任务理解 + 费曼五步编排（chat_history 建会话）
    POST /api/learn/step       — 费曼教学 Agent 真实生成 + 知识检索注入（持久化）
    POST /api/learn/feynman-test — 30 秒讲解评分
    POST /api/learn/report     — 汇总报告（落 learning_reports + chat_history）
    GET  /api/learn/history    — 当前用户学习历史
    GET  /api/learn/report/<id> — 历史报告详情
    GET  /api/profile          — 我的学习档案
    GET  /api/status           — Agent 状态

核心设备压力约束：惰性 DB 连接（conversation_store）、单 Agent 实例、
报告/会话持久化失败不影响主流程（try/except 兜底）。
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import (Flask, abort, jsonify, render_template_string,
                   request, send_from_directory)

from lumilearn_agent import LumiLearnAgent
from framework.api.routes.student_learn import create_student_learn_bp
from framework.core.config import get_app_secret_key, register_csrf_guard
from framework.database import db

db.init()

BASE_DIR = Path(__file__).resolve().parent
PROTO_DIR = BASE_DIR / "prototypes" / "student-learning-platform"

app = Flask(__name__)
app.secret_key = get_app_secret_key("STUDENT_SECRET_KEY", "Student Portal")
# Cookie 安全属性 + CSRF（cookie 会话认证端口）
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("LUMILEARN_COOKIE_SECURE", "").lower() == "true",
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # 10MB 上传上限
)
register_csrf_guard(app)

# 统一 404 / 500 错误处理
from framework.api.errors import register_error_handlers
register_error_handlers(app)


@app.after_request
def _student_security_headers(response):
    """全局安全响应头（防御 XSS / 点击劫持 / MIME 嗅探）"""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
    if "text/html" in response.headers.get("Content-Type", ""):
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
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response

# 全局 Agent 实例（Ollama 地址由 OLLAMA_URL 环境变量配置）
agent = LumiLearnAgent()

# 共享费曼学习 Blueprint（认证 + 学习流程 + 档案）
app.register_blueprint(create_student_learn_bp(agent, session_key="user_id"))


@app.route("/api/status")
def api_status():
    return jsonify(agent.get_status())


# ============================================================
# 前端：服务原型静态页（注入真实 API 标志）
# ============================================================
_REAL_FLAG = "<script>window.__LUMILEARN_REAL__ = true;</script>"


def _serve(html_file: str):
    full = PROTO_DIR / html_file
    if not full.is_file():
        abort(404)
    if html_file.endswith(".html"):
        html = full.read_text(encoding="utf-8")
        return render_template_string(html.replace("<head>", "<head>" + _REAL_FLAG, 1))
    return send_from_directory(str(PROTO_DIR), html_file)


@app.route("/")
def index_page():
    return _serve("index.html")


@app.route("/<path:filename>")
def static_proto(filename):
    safe = os.path.normpath(filename).lstrip("/\\")
    if ".." in safe.split(os.sep) or not (PROTO_DIR / safe).is_file():
        abort(404)
    return _serve(safe)


# ============================================================
# 启动
# ============================================================
def _get_student_port() -> int:
    """从 port_settings 读取学生端端口（可被环境变量 STUDENT_PORT 覆盖）"""
    env_port = os.environ.get("STUDENT_PORT", "")
    if env_port.isdigit():
        return int(env_port)
    try:
        from framework.services.provider_service import get_provider_service
        cfg = get_provider_service().get_port_settings().get("student_portal", {})
        if cfg.get("port"):
            return int(cfg["port"])
    except Exception:
        pass
    return 5010


def main():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"

    port = _get_student_port()
    print("\n" + "=" * 60)
    print("  🎓 LumiLearn 学生端学习平台 (Student Portal)")
    print("=" * 60)
    print("  📍 访问地址: http://{}:{}".format(ip, port))
    print("  👤 登录账号: users 表中的账号（学生/教师均可）")
    print("  💾 共享数据库: " + db.db_path)
    print("=" * 60 + "\n")

    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    # lite 模式（轻量自学）：解析 --mode lite，启用后跳过演示模块加载
    from framework.lite_mode import LiteModeManager
    if LiteModeManager().parse_args() == "lite":
        app.config["LITE_MODE"] = True
        print("[LiteMode] 轻量自学模式已启用：跳过演示模块加载")
    main()
