# -*- coding: utf-8 -*-
"""
LumiLearn 学生端学习平台 Blueprint（Student Platform 前端）
============================================================
将原独立 student_portal.py 的「前端原型静态服务」抽为 Blueprint，
供统一管理门户 server.py 以 url_prefix="/student" 注册（http://<host>:18080/student）。

- 前端：prototypes/student-learning-platform/ 静态原型（注入 __LUMILEARN_REAL__ 走真实 API）
- 后端 API 复用框架统一路由：/api/auth/*（统一认证）+ /api/learn/*（student_learn，include_auth=False）
  由 server.py 单独注册，本 Blueprint 只负责静态页面服务。

注意：前端 api.js 使用绝对路径 /api/*，页面间导航使用相对路径（如 learn.html），
因此本 Blueprint 挂在 /student 前缀下时，相对资源/导航均能正确解析到 /student/*。
"""
import os
from pathlib import Path

from flask import Blueprint, abort, render_template_string, send_from_directory

# 项目根目录（framework/api/routes -> parents[3] = 项目根）
BASE_DIR = Path(__file__).resolve().parents[3]
PROTO_DIR = BASE_DIR / "prototypes" / "student-learning-platform"

_REAL_FLAG = "<script>window.__LUMILEARN_REAL__ = true;</script>"


def _serve(html_file: str, path_prefix: str = ""):
    """服务原型文件：HTML 注入真实 API 标志；其余文件直接返回。"""
    full = PROTO_DIR / html_file
    if not full.is_file():
        abort(404)
    if html_file.endswith(".html"):
        html = full.read_text(encoding="utf-8")
        # 相对资源引用需带前缀：<head> 注入标志 + <base> 保证相对路径解析到 /student/
        prefix = path_prefix.rstrip("/")
        base_tag = '<base href="{}/">'.format(prefix) if prefix else ""
        html = html.replace("<head>", "<head>" + _REAL_FLAG + base_tag, 1)
        return render_template_string(html)
    return send_from_directory(str(PROTO_DIR), html_file)


def create_student_platform_bp(path_prefix: str = "/student") -> Blueprint:
    """创建学生端前端静态服务 Blueprint（挂 url_prefix="/student" 时相对资源正确解析）。"""
    bp = Blueprint("student_platform", __name__)

    @bp.route("/")
    def index_page():
        return _serve("index.html", path_prefix)

    @bp.route("/<path:filename>")
    def static_proto(filename):
        safe = os.path.normpath(filename).lstrip("/\\")
        if ".." in safe.split(os.sep) or not (PROTO_DIR / safe).is_file():
            abort(404)
        return _serve(safe, path_prefix)

    return bp