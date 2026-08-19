#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn GOAI Agent — Web Demo
====================================
Flask后端 + 单页前端，评委通过浏览器直接体验

运行方式：
  python goai_web.py
  浏览器打开 http://localhost:5000

API端点：
  POST /api/learn — 提交学习目标，返回学习报告
  GET  /api/status — Agent状态
  POST /api/chat — 对话式交互
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import (Flask, request, jsonify, render_template, session,
                   redirect, url_for, send_from_directory, abort)
from goai_agent import LumiLearnAgent, TaskUnderstanding, FlowOrchestrator
from goai_multi_agent import get_multi_agent_orchestrator
from framework.api.routes.student_learn import create_student_learn_bp
from framework.core.config import get_app_secret_key, register_csrf_guard

# 连接 Framework 数据库（与 18080 管理端共享 lumilearn.db）
from framework.database import db
db.init()

# 多轮对话持久化（chat_history，惰性连接，共享同一 lumilearn.db）
from framework.services.conversation_store import conversation_store as conv_store

# 模板目录：兼容本地 remote/templates 与远程 tianhong/templates 两种部署结构
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "remote" / "templates"
if not TEMPLATE_DIR.exists():
    TEMPLATE_DIR = BASE_DIR / "tianhong" / "templates"

app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
app.secret_key = get_app_secret_key("GOAI_SECRET_KEY", "GOAI Web")
# Cookie 安全属性 + CSRF（cookie 会话认证端口）
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("LUMILEARN_COOKIE_SECURE", "").lower() == "true",
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # 10MB 上传上限
)
register_csrf_guard(app)


@app.after_request
def _goai_security_headers(response):
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

# 全局Agent实例（Ollama 地址通过环境变量 OLLAMA_URL 配置，见 .env.example）
agent = LumiLearnAgent()

# 多 Agent 协作编排器（单例：FeynmanTeacher → ScoreAgent → CoachAgent）
multi_agent = get_multi_agent_orchestrator()

# 共享费曼学习 Blueprint（/proto/ 学生端原型走同一套真实 API：登录 + 五步 + 档案）
app.register_blueprint(create_student_learn_bp(agent, session_key="user_id"))


# ============================================================
# API路由
# ============================================================
def get_local_ip():
    """获取局域网 IP"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


@app.route('/')
def index():
    """服务仪表盘首页（模板: remote/templates/goai_dashboard.html）"""
    local_ip = get_local_ip()
    current_user = _get_current_user()
    user_badge = f"👤 {current_user['name']} ({'教师' if current_user['role'] == 'teacher' else '学生'})" if current_user else "未登录"

    raw_services = [
        ("🎓 GOAI 学习智能体", "/learn", "5000", "AI 教官问答 + 费曼教学法五步学习 + 多Agent协作", "在线"),
        ("🖥️ 框架终端", f"http://{local_ip}:18080/", "18080", "LumiLearn 全功能终端界面", "在线" if check_port(18080) else "离线"),
        ("🔌 REST API", f"http://{local_ip}:18081/", "18081", "纯 API 服务，供第三方集成", "在线" if check_port(18081) else "离线"),
        ("🤖 模型管理", f"http://{local_ip}:18082/", "18082", "模型列表、切换、健康检查", "在线" if check_port(18082) else "离线"),
    ]

    services = []
    for icon, path, port, desc, status in raw_services:
        services.append({
            "emoji": icon.split()[0],
            "title": " ".join(icon.split()[1:]),
            "port": port,
            "desc": desc,
            "status": status,
            "status_class": "status-online" if status == "在线" else "status-offline",
            "link": path if path.startswith("http") else path,
        })

    return render_template("goai_dashboard.html",
                           local_ip=local_ip,
                           user_badge=user_badge,
                           services=services)


def check_port(port):
    """检查端口是否在监听"""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except:
        return False


@app.route('/learn')
def learn_page():
    """GOAI 学习智能体页面（模板: remote/templates/goai_learn.html）"""
    return render_template("goai_learn.html")


# ---------- 多 Agent 协作 ----------

@app.route('/api/multi-agent', methods=['POST'])
def api_multi_agent():
    """三 Agent 协作：FeynmanTeacher 教学 → ScoreAgent 评分 → CoachAgent 建议"""
    user = _get_current_user()
    if not user:
        return jsonify({'error': '未登录，请先登录'}), 401

    data = request.get_json() or {}
    topic = (data.get('topic') or '').strip()
    if not topic:
        return jsonify({'error': '请提供学习目标'}), 400

    payload = {
        'topic': topic,
        'subject': data.get('subject', ''),
        'difficulty': data.get('difficulty', '高中'),
        'user_id': user['id'],
        'student_explanation': data.get('student_explanation', ''),
        'weak_topics': data.get('weak_topics', []),
        'dialogue': data.get('dialogue'),
    }

    try:
        report = multi_agent.run(payload)
        # 有评分时落库（供 Admin/教师端查看）
        if report['assessment']['score'] > 0:
            db.add_learning_report(user['id'], topic, report,
                                   score=report['assessment']['score'])
        # 自动记录学习进度到自适应引擎（驱动薄弱点/推荐/复习提醒）
        try:
            engine = _get_adaptive_engine()
            if engine is not None:
                node_id = _match_knowledge_node(topic)
                if node_id:
                    engine.record_learning(
                        str(user['id']), node_id,
                        score=report['assessment']['score'] / 100.0,
                        time_spent=float(report.get('total_time') or 0),
                    )
        except Exception:
            pass  # 进度记录失败不影响主流程
        return jsonify({'success': True, 'data': report})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------- RAG 知识库检索 ----------

@app.route('/api/knowledge/search', methods=['GET', 'POST'])
def api_knowledge_search():
    """关键词检索教学知识库（training_data + knowledge_nodes），需登录"""
    user = _get_current_user()
    if not user:
        return jsonify({'error': '未登录，请先登录'}), 401

    if request.method == 'POST':
        data = request.get_json() or {}
        q = (data.get('q') or data.get('query') or '').strip()
        top_k = int(data.get('top_k') or 5)
        subject = data.get('subject') or ''
    else:
        q = (request.args.get('q') or request.args.get('query') or '').strip()
        top_k = int(request.args.get('top_k') or 5)
        subject = request.args.get('subject') or ''

    if not q:
        return jsonify({'success': False, 'error': '缺少查询关键词 q'}), 400
    try:
        from framework.services.knowledge_retrieval import get_knowledge_retriever
        retriever = get_knowledge_retriever()
        results = retriever.search(q, top_k=min(max(top_k, 1), 20),
                                   subject=subject or None)
        return jsonify({'success': True, 'query': q, 'count': len(results),
                        'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/knowledge/status')
def api_knowledge_status():
    """知识库索引状态"""
    user = _get_current_user()
    if not user:
        return jsonify({'error': '未登录，请先登录'}), 401
    try:
        from framework.services.knowledge_retrieval import get_knowledge_retriever
        retriever = get_knowledge_retriever()
        retriever.build_index()
        return jsonify({'success': True, 'data': retriever.status()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------- 用户认证 ----------

@app.route('/api/login', methods=['POST'])
def api_login():
    """用户登录（使用 Framework 数据库账号）"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'success': False, 'error': '请输入用户名和密码'}), 400
    user = db.verify_user_login(username, password)
    if not user:
        return jsonify({'success': False, 'error': '用户名或密码错误'}), 401
    session['user_id'] = user['id']
    return jsonify({
        'success': True,
        'user': {'id': user['id'], 'name': user['name'], 'role': user['role']},
    })


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/api/me')
def api_me():
    """获取当前登录用户"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '未登录'}), 401
    user = db.get_user(user_id)
    if not user:
        session.clear()
        return jsonify({'success': False, 'error': '用户不存在'}), 401
    return jsonify({'success': True, 'user': {
        'id': user['id'], 'name': user['name'], 'role': user['role'],
        'username': user.get('username', ''),
    }})


def _get_current_user():
    """获取当前登录用户，未登录返回 None"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return db.get_user(user_id)


# ============================================================
# 自适应学习引擎接入（A1/A2：学习 dashboard + 进度记录）
# ============================================================
def _get_adaptive_engine():
    """懒加载自适应学习引擎单例（失败返回 None，不阻塞主流程）"""
    try:
        from framework.services.adaptive_learning import get_adaptive_engine
        return get_adaptive_engine()
    except Exception:
        return None


# 主题 → 知识节点匹配表（与 adaptive_learning.KNOWLEDGE_GRAPH 节点名对应）
_NODE_MATCH_KEYWORDS = {
    "pythagorean": ["勾股", "毕达哥拉斯", "直角三角形边长"],
    "triangle_basics": ["三角形", "内角和", "三角"],
    "circle_area": ["圆面积", "圆的面积", "圆"],
    "cosine_rule": ["余弦定理", "余弦"],
    "quadratic_formula": ["求根公式", "一元二次", "二次方程"],
    "completing_square": ["配方", "配方法"],
    "polynomial": ["多项式", "因式分解"],
    "linear_function": ["一次函数", "正比例"],
    "quadratic_function": ["二次函数", "抛物线"],
    "function_monotonicity": ["单调性", "单调递增", "单调递减"],
    "derivative": ["导数", "求导", "微分"],
    "free_fall": ["自由落体", "自由下落"],
    "newton_second_law": ["牛顿第二定律", "F=ma", "牛二"],
    "light_refraction": ["折射", "光的折射", "斯涅尔"],
    "chemical_equilibrium": ["化学平衡", "平衡移动", "勒夏特列"],
    "mole": ["物质的量", "摩尔", "阿伏伽德罗"],
    "mean_median": ["均值", "中位数", "平均数", "众数"],
    "normal_distribution": ["正态分布", "高斯分布"],
}


def _match_knowledge_node(topic: str) -> Optional[str]:
    """根据学习主题匹配知识图谱节点 ID，未命中返回 None（兜底不阻塞）"""
    if not topic:
        return None
    for node_id, keywords in _NODE_MATCH_KEYWORDS.items():
        if any(kw in topic for kw in keywords):
            return node_id
    # 兜底：整词包含节点名
    try:
        from framework.services.adaptive_learning import get_adaptive_engine
        engine = get_adaptive_engine()
        if engine is None:
            return None
        for nid, node in engine.graph.items():
            if node.name and node.name in topic:
                return nid
    except Exception:
        pass
    return None


@app.route('/api/learning/dashboard')
def api_learning_dashboard():
    """学习首页聚合数据：进度总览 + 薄弱点TOP3 + 推荐下一步 + 最近学习"""
    user = _get_current_user()
    if not user:
        return jsonify({'success': False, 'error': '未登录'}), 401
    engine = _get_adaptive_engine()
    if engine is None:
        return jsonify({'success': False, 'error': '自适应引擎不可用'}), 500

    uid = str(user['id'])
    try:
        progress = engine.get_progress(uid)
        weaknesses = engine.analyze_weaknesses(uid)[:3]
        recommended = engine.recommend_next(uid, count=5)
        # 最近学习记录：自适应引擎 history 优先，空则用 learning_reports
        recent = progress.get("recent_history", [])
        recent_reports = []
        if not recent:
            for r in db.get_learning_reports(user_id=user['id'], limit=5):
                rep = r.get('report', {})
                recent_reports.append({
                    "topic": r.get('topic', ''),
                    "score": (rep.get('mastery_assessment') or {}).get('score', 0),
                    "generated_at": rep.get('generated_at', r.get('created_at', '')),
                })
        return jsonify({
            'success': True,
            'data': {
                'overall_progress': progress.get('overall_progress', 0),
                'mastered_nodes': progress.get('mastered_nodes', 0),
                'learning_nodes': progress.get('learning_nodes', 0),
                'studied_nodes': progress.get('studied_nodes', 0),
                'total_knowledge_nodes': progress.get('total_knowledge_nodes', 0),
                'weaknesses': weaknesses,
                'recommended': recommended,
                'recent_history': recent[-10:],
                'recent_reports': recent_reports,
            },
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/learning/progress', methods=['POST'])
def api_learning_progress():
    """记录学习活动到自适应引擎（掌握度指数平滑更新，驱动推荐/薄弱点）"""
    user = _get_current_user()
    if not user:
        return jsonify({'success': False, 'error': '未登录'}), 401
    data = request.get_json() or {}
    topic = (data.get('topic') or '').strip()
    if not topic:
        return jsonify({'success': False, 'error': '缺少 topic'}), 400
    score = float(data.get('score') or 0)
    # 前端可能传 0-100 或 0-1，统一归一化到 0-1
    score = max(0.0, min(score, 1.0)) if score <= 1.0 else max(0.0, min(score / 100.0, 1.0))
    time_spent = float(data.get('time_spent') or 0)

    engine = _get_adaptive_engine()
    if engine is None:
        return jsonify({'success': False, 'error': '自适应引擎不可用'}), 500

    node_id = _match_knowledge_node(topic)
    uid = str(user['id'])
    try:
        if node_id:
            engine.record_learning(uid, node_id, score=score, time_spent=time_spent)
        return jsonify({
            'success': True,
            'data': {
                'node_id': node_id or None,
                'topic': topic,
                'score': round(score, 2),
                'matched': node_id is not None,
            },
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/history')
def api_history():
    """获取当前用户的学习历史"""
    user = _get_current_user()
    if not user:
        return jsonify({'success': False, 'error': '未登录'}), 401
    reports = db.get_learning_reports(user_id=user['id'], limit=30)
    for r in reports:
        rep = r.get('report', {})
        r['summary'] = {
            'core_topic': (rep.get('task_understanding') or {}).get('core_topic', r['topic']),
            'subject': (rep.get('task_understanding') or {}).get('subject', ''),
            'generated_at': rep.get('generated_at', ''),
            'score': (rep.get('mastery_assessment') or {}).get('score', 0),
        }
        # 保留完整 report 供前端查看
    return jsonify({'success': True, 'reports': reports})


@app.route('/api/learn', methods=['POST'])
def api_learn():
    """提交学习目标，返回学习报告（需登录，报告自动保存到数据库）"""
    user = _get_current_user()
    if not user:
        return jsonify({'error': '未登录，请先登录'}), 401

    data = request.get_json()
    topic = data.get('topic', '').strip()

    if not topic:
        return jsonify({'error': '请提供学习目标'}), 400

    try:
        report = agent.run(topic, interactive=False, user_id=user['id'])
        # 保存学习报告到共享数据库（Admin 面板可见）
        score = (report.get('mastery_assessment') or {}).get('score', 0)
        db.add_learning_report(user['id'], topic, report, score=score)
        report['user'] = {'id': user['id'], 'name': user['name']}
        # 多轮对话持久化：学习目标 + 报告摘要写入 chat_history
        try:
            sid = conv_store.create_session(topic, user_id=user['id'])
            conv_store.add_message(sid, "user", topic)
            summary = json.dumps({
                "mastery": score,
                "weak_points": (report.get('weak_points') or [])[:3],
            }, ensure_ascii=False)
            conv_store.add_message(sid, "assistant",
                                   f"学习报告已生成：{summary}",
                                   model=agent.tool_caller.preferred_model)
        except Exception:
            pass  # 持久化失败不影响主流程
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status')
def api_status():
    """获取Agent状态"""
    return jsonify(agent.get_status())


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """对话式交互（多轮消息自动持久化到 chat_history）"""
    user = _get_current_user()
    data = request.get_json()
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': '消息不能为空'}), 400

    tu = TaskUnderstanding()
    task = tu.understand(message)
    reply = f"已识别你的学习目标：{task['core_topic']}（{task['subject']}/{task['difficulty']}）"

    # 多轮对话持久化：登录用户消息 + 回复写入"对话式问答"会话
    try:
        if user:
            sid = _get_or_create_chat_session(user['id'])
            conv_store.add_message(sid, "user", message)
            conv_store.add_message(sid, "assistant", reply, model="task-understanding")
    except Exception:
        pass  # 持久化失败不影响主流程

    return jsonify({'reply': reply, 'task': task})


def _get_or_create_chat_session(user_id: int) -> int:
    """找到该用户最近的"对话式问答"会话，无则新建（保持多轮上下文连贯）。"""
    for s in conv_store.list_sessions(user_id=user_id, limit=20):
        if s["title"] == "对话式问答":
            return s["id"]
    return conv_store.create_session("对话式问答", user_id=user_id)


# ============================================================
# 对话历史（chat_history 多轮持久化查看）
# ============================================================
@app.route('/api/conversations')
def api_conversations():
    """列出当前用户的对话会话（含消息数与末条预览）"""
    user = _get_current_user()
    if not user:
        return jsonify({'error': '未登录，请先登录'}), 401
    return jsonify({'success': True, 'sessions': conv_store.list_sessions(user_id=user['id'], limit=30)})


@app.route('/api/conversations/<int:session_id>')
def api_conversation_detail(session_id):
    """获取某会话的完整多轮消息"""
    user = _get_current_user()
    if not user:
        return jsonify({'error': '未登录，请先登录'}), 401
    s = conv_store.get_session(session_id)
    if not s or s["user_id"] != user["id"]:
        return jsonify({'error': '会话不存在'}), 404
    return jsonify({'success': True, 'session': s,
                    'messages': conv_store.get_messages(session_id)})


# ============================================================
# 学生端原型（静态交付，GOAI Web 内嵌访问）
# ============================================================
PROTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "prototypes", "student-learning-platform")


@app.route('/proto/')
def proto_index():
    return _send_proto("index.html")


@app.route('/proto/<path:filename>')
def proto_file(filename):
    return _send_proto(filename)


def _send_proto(filename):
    """安全发送原型静态文件（防路径穿越）；HTML 注入真实后端标志，走共享费曼学习 API"""
    safe = os.path.normpath(filename).lstrip("/\\")
    if ".." in safe.split(os.sep):
        abort(404)
    full = os.path.join(PROTO_DIR, safe)
    if not os.path.isfile(full):
        abort(404)
    if safe.endswith(".html"):
        html = open(full, encoding="utf-8").read()
        flag = "<script>window.__LUMILEARN_REAL__ = true;</script>"
        html = html.replace("<head>", "<head>" + flag, 1)
        from flask import Response
        return Response(html, mimetype="text/html; charset=utf-8")
    return send_from_directory(PROTO_DIR, safe)


# ============================================================
# 启动
# ============================================================
def _get_goai_port() -> int:
    """从 port_settings 读取 GOAI Web 端口（可被环境变量覆盖）"""
    env_port = os.environ.get("GOAI_PORT", "")
    if env_port.isdigit():
        return int(env_port)
    try:
        from framework.services.provider_service import get_provider_service
        cfg = get_provider_service().get_port_settings().get("goai_web", {})
        if cfg.get("port"):
            return int(cfg["port"])
    except Exception:
        pass
    return 5000


def main():
    local_ip = get_local_ip()
    port = _get_goai_port()
    print("\n" + "=" * 60)
    print("  🎓 LumiLearn AI 教官 — 服务仪表盘")
    print("  GOAI 无界应用赛道参赛作品")
    print("=" * 60)
    print(f"  📊 仪表盘首页:  http://localhost:{port}")
    print(f"  🎓 学习智能体:  http://localhost:{port}/learn")
    print(f"  🖥️ 框架终端:    http://{local_ip}:18080")
    print(f"  🔌 REST API:    http://{local_ip}:18081")
    print(f"  🤖 模型管理:    http://{local_ip}:18082")
    print(f"  📡 API地址:     http://localhost:{port}/api/learn")
    print(f"  🚀 Ollama状态:  {'可用' if agent.tool_caller.available else '不可用（兜底模式）'}")
    print("=" * 60)
    print("  按 Ctrl+C 停止服务\n")

    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    main()
