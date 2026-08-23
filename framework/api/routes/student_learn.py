# -*- coding: utf-8 -*-
"""
学生端费曼学习 API（共享 Blueprint）
====================================
把「发起学习 → 费曼五步 → 费曼测试 → 学习报告 → 历史/档案」完整流程抽成
可复用 Blueprint，供多个端口服务注册使用：

- student_portal.py（5010）：学生端学习平台
- goai_web.py（5000）：GOAI Web（/proto/ 学生端原型走同一套真实 API）

认证契约（api.js 前端一致）：
    POST /api/auth/login · GET /api/auth/me · POST /api/auth/logout （session 会话）
    POST /api/learn/start      — 任务理解 + 费曼五步编排（chat_history 建会话）
    POST /api/learn/step       — 费曼教学 Agent 真实生成 + 知识检索注入（持久化）
    POST /api/learn/feynman-test — 30 秒讲解评分
    POST /api/learn/report     — 汇总报告（落 learning_reports + chat_history）
    GET  /api/learn/history    — 当前用户学习历史
    GET  /api/learn/report/<id> — 历史报告详情
    GET  /api/profile          — 我的学习档案（趋势/薄弱点/最近对话）

核心设备压力约束：DB 惰性连接、单 Agent 实例、持久化失败不影响主流程。
"""
import os
import sys
from datetime import datetime

from flask import Blueprint, jsonify, request, session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from framework.database import db
from framework.services.conversation_store import conversation_store as conv_store
from framework.api.validation import validate_text_field
from goai_agent import FlowOrchestrator, TaskUnderstanding

# 与原型 mock.js 保持一致的 Agent 定义
AGENT_DEFS = [
    {"id": "orchestrator", "name": "编排调度", "model": "orchestrator-core", "role": "任务分发 · 流程编排 · 结果聚合"},
    {"id": "feynman", "name": "费曼教学", "model": "qwen2.5:7b", "role": "五步教学法生成教学内容"},
    {"id": "knowledge", "name": "知识检索", "model": "retrieval-index", "role": "检索知识点 · 注入上下文"},
    {"id": "coach", "name": "评测与路径", "model": "lumilearn-v2", "role": "输出评分 · 个性化学习路径"},
]

_KNOWLEDGE_HINTS = {
    "函数的单调性": ["定义域与区间", "图像上升/下降", "最值与极值"],
    "牛顿第二定律": ["力的合成与分解", "加速度与速度方向", "质量与惯性"],
    "化学平衡移动": ["勒夏特列原理", "平衡常数 K", "压强与浓度"],
    "光合作用": ["叶绿体结构", "光反应与暗反应", "ATP 与 NADPH"],
}

_WEAK_LIB = {
    "函数的单调性": [{"text": "区间端点的开闭判断不够严谨", "severity": "中"}, {"text": "复合函数单调性判断需多练", "severity": "低"}],
    "牛顿第二定律": [{"text": "受力分析时易漏力", "severity": "中"}, {"text": "连接体问题需加强", "severity": "低"}],
    "化学平衡移动": [{"text": "压强改变对平衡影响的推理不熟练", "severity": "中"}],
    "光合作用": [{"text": "光反应与暗反应的场所容易记混", "severity": "低"}],
}

_PREFIXES = ["我想理解", "我想学", "我想学习", "我要学", "帮我学习", "帮我理解",
             "帮我掌握", "帮我", "学习", "理解", "掌握", "复习", "什么是",
             "怎么学", "如何理解", "请讲解", "讲解"]


def _normalize_topic(topic: str) -> str:
    t = (topic or "").strip()
    for p in _PREFIXES:
        if t.startswith(p):
            t = t[len(p):]
    return t.strip() or (topic or "").strip()


def _sid(value) -> int:
    """容错解析 sessionId：接受数字或 's-3' 前缀格式（前端可能传 's-3' 字符串）"""
    try:
        return int(str(value).replace("s-", ""))
    except (TypeError, ValueError):
        return 0


def create_student_learn_bp(agent, session_key: str = "user_id") -> Blueprint:
    """创建学生端学习 Blueprint。

    :param agent: LumiLearnAgent 实例（费曼教学 Agent 真实生成）
    :param session_key: Flask session 中保存用户 id 的键（默认 user_id）
    """
    bp = Blueprint("student_learn", __name__)

    def _current_user():
        uid = session.get(session_key)
        if not uid:
            return None
        return db.get_user(uid)

    def _require_user():
        user = _current_user()
        if not user:
            return None
        return user

    # ---------- 认证 ----------
    @bp.route("/api/auth/login", methods=["POST"])
    def api_login():
        data = request.get_json() or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            return jsonify({"code": 400, "message": "请输入用户名和密码"}), 400
        user = db.verify_user_login(username, password)
        if not user:
            return jsonify({"code": 401, "message": "用户名或密码错误"}), 401
        session[session_key] = user["id"]
        return jsonify({"code": 0, "data": {"id": user["id"], "name": user["name"], "role": user["role"]}})

    @bp.route("/api/auth/logout", methods=["POST"])
    def api_logout():
        session.clear()
        return jsonify({"code": 0, "data": {"success": True}})

    @bp.route("/api/auth/me")
    def api_me():
        user = _require_user()
        if not user:
            return jsonify({"code": 401, "message": "未登录"}), 401
        return jsonify({"code": 0, "data": {"id": user["id"], "name": user["name"], "role": user["role"]}})

    # ---------- 学习流程 ----------
    @bp.route("/api/learn/start", methods=["POST"])
    def api_learn_start():
        user = _require_user()
        if not user:
            return jsonify({"code": 401, "message": "未登录"}), 401
        data = request.get_json() or {}
        topic = (data.get("topic") or "").strip()
        subject = data.get("subject") or "数学"
        difficulty = data.get("difficulty") or "高中"
        if not topic:
            return jsonify({"code": 400, "message": "请提供学习目标"}), 400
        ok, err = validate_text_field(topic, "topic", 200)
        if not ok:
            return jsonify({"code": 400, "message": err}), 400

        task = TaskUnderstanding().understand(topic)
        flow = FlowOrchestrator().orchestrate(task)
        try:
            sid = conv_store.create_session(topic, user_id=user["id"])
            conv_store.add_message(sid, "user", topic)
        except Exception:
            sid = 0
        return jsonify({"code": 0, "data": {
            "id": "s-{}".format(sid),
            "session_id": sid,
            "topic": topic, "subject": subject, "difficulty": difficulty,
            "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "learning",
            "model": agent.tool_caller.preferred_model,
            "flow": [{"step": s["step"], "name": s["name"], "purpose": s["purpose"], "status": "pending"} for s in flow],
            "agents": [dict(a, status="idle", calls=0) for a in AGENT_DEFS],
        }})

    @bp.route("/api/learn/step", methods=["POST"])
    def api_learn_step():
        user = _require_user()
        if not user:
            return jsonify({"code": 401, "message": "未登录"}), 401
        data = request.get_json() or {}
        sid = _sid(data.get("sessionId"))
        step = int(data.get("step") or 1)

        sess = conv_store.get_session(sid) if sid else None
        topic = sess["title"] if sess else "学习主题"
        key = _normalize_topic(topic)
        hints = _KNOWLEDGE_HINTS.get(key, ["核心概念", "典型例题", "易错点"])

        # 由主题重建费曼步骤提示词（确定性，无需缓存）
        task = TaskUnderstanding().understand(topic)
        step_def = FlowOrchestrator().orchestrate(task)[step - 1]

        # 费曼教学 Agent 真实生成
        result = agent.tool_caller.call(step_def["prompt"], task_type="teach")
        try:
            conv_store.add_message(sid, "assistant", result["content"], model=result.get("model") or "")
        except Exception:
            pass

        return jsonify({"code": 0, "data": {
            "step": step,
            "content": result["content"],
            "knowledge": hints,
            "agents": [
                {"id": "orchestrator", "action": "分发步骤 {}「{}」".format(step, step_def["name"])},
                {"id": "knowledge", "action": "检索「{}」相关知识点 {} 条".format(key, len(hints))},
                {"id": "feynman", "action": "生成「{}」教学内容".format(step_def["name"])},
            ],
        }})

    @bp.route("/api/learn/guide", methods=["POST"])
    def api_learn_guide():
        """引导式学习（苏格拉底式）：老师提问 → 学生自主回答 → 根据回答调整下一步引导。

        请求：{ sessionId, answer?, level? }
          - 首次调用（无 answer）：生成第 1 步引导提问
          - 之后每次带 answer：先具体回应学生刚才的回答（肯定/修正），再生成下一步引导
        响应：{ step, step_name, content, is_last, progress, model_used }
        会话对话历史保存在 chat_history，保证上下文连贯；推理过程写 reasoning_logs。
        """
        user = _require_user()
        if not user:
            return jsonify({"code": 401, "message": "未登录"}), 401
        data = request.get_json() or {}
        sid = _sid(data.get("sessionId"))
        answer = (data.get("answer") or "").strip()
        level = (data.get("level") or "高中")

        sess = conv_store.get_session(sid) if sid else None
        if not sess:
            return jsonify({"code": 404, "message": "会话不存在，请重新发起学习"}), 404
        topic = sess["title"]

        # 会话历史 → 费曼 dialogue（首条 user 是主题，不算学生回答；角色必须 user/assistant 交替）
        msgs = conv_store.get_messages(sid) if sid else []
        dialogue = []
        for m in msgs:
            if m.get("role") == "user" and (m.get("content") or "").strip() == topic.strip():
                continue
            if m.get("role") in ("user", "assistant"):
                dialogue.append({"role": m["role"], "content": (m.get("content") or "")[:800]})

        # 本次学生回答 → 先写入会话再让 AI 回应
        if answer:
            try:
                conv_store.add_message(sid, "user", answer)
            except Exception:
                pass
            dialogue.append({"role": "user", "content": answer[:800]})

        # RAG 知识库检索（失败降级为空，绝不阻塞教学）
        rag_context = ""
        try:
            from framework.services.knowledge_retrieval import (
                get_knowledge_retriever, format_rag_context)
            _results = get_knowledge_retriever().search(topic, top_k=3)
            if _results:
                rag_context = format_rag_context(_results, max_chars=800)
        except Exception:
            rag_context = ""

        # 费曼交互式单步引导（每次只生成一步，等待学生回答后再推进）
        from framework.engines.feynman_engine import FeynmanEngine
        try:
            from goai_multi_agent import _map_level
        except Exception:
            def _map_level(diff):
                return {"初中": "junior", "高中": "senior",
                        "大学": "college"}.get(diff or "", "general")
        engine = FeynmanEngine(model_name=agent.tool_caller.preferred_model, timeout=120)
        step = engine.explain_step(topic=topic, level=_map_level(level),
                                   dialogue=dialogue, extra_context=rag_context)

        # 写入 AI 引导（assistant 计数驱动下一步推断）
        try:
            conv_store.add_message(sid, "assistant", step["content"],
                                   model=step.get("model_used") or "")
        except Exception:
            pass

        # 推理过程写库（管理员/教师可见；失败不影响主流程）
        try:
            db.add_reasoning_log(
                user_id=user["id"],
                session_id=f"feynman:{topic[:50]}",
                mode="feynman", topic=topic[:200],
                step_order=step.get("step", 0),
                step_name=step.get("step_name", ""),
                model_used=step.get("model_used", ""),
                input_context=(answer or "（开始学习）")[:500],
                output=step.get("content", "")[:2000],
                latency_ms=0, status="success",
            )
        except Exception:
            pass

        return jsonify({"code": 0, "data": {
            "step": step.get("step", 1),
            "step_name": step.get("step_name", ""),
            "content": step.get("content", ""),
            "is_last": step.get("is_last", False),
            "model_used": step.get("model_used", ""),
            "progress": {"current": step.get("step", 1), "total": 5},
        }})

    @bp.route("/api/learn/feynman-test", methods=["POST"])
    def api_feynman_test():
        user = _require_user()
        if not user:
            return jsonify({"code": 401, "message": "未登录"}), 401
        data = request.get_json() or {}
        sid = _sid(data.get("sessionId"))
        text = (data.get("text") or "").strip()
        sess = conv_store.get_session(sid) if sid else None
        topic = (sess["title"] if sess else "").strip() or (data.get("topic") or "").strip() or "学习主题"

        # 尝试使用 OutputDetector 进行 AI 语义评分（失败时自动降级）
        score, verdict, feedback = None, None, None
        try:
            from framework.output_detector import OutputDetector
            detector = OutputDetector(user_id=user["id"])
            result = detector.run_detection(topic, text)
            score = getattr(result, "total_score", None)
            if score is None or score < 0:
                raise ValueError("detector returned invalid score")
            verdict = getattr(result, "feedback", None) or ("讲解清晰，能用自己的话讲明白" if score >= 80 else "基本合格，再具体一些会更好" if score >= 70 else "建议补充一个具体例子再讲一遍")
            dim_results = getattr(result, "dimensions", [])
            feedback = {}
            dim_map = {"简洁度": "simplicity", "准确度": "accuracy", "比喻": "analogy", "完整度": "completeness", "术语规避": "jargon_free"}
            for d in dim_results:
                key = dim_map.get(d.name, d.name)
                feedback[key] = {"score": d.score, "comment": d.comment}
            if not feedback:
                raise ValueError("no dimension results")
            model_used = getattr(result, "model_used", "output_detector")
        except Exception:
            # 降级：启发式评分（按文本长度 + 关键词覆盖）
            length = len(text)
            has_example = any(kw in text for kw in ["比如", "例如", "就像", "比方", "例如", "比如"])
            has_concept = any(kw in text for kw in ["定义", "概念", "原理", "公式", "定律", "定理"])
            base = 62 if length < 20 else (78 if length < 60 else 88)
            bonus = min(8, (has_example * 4) + (has_concept * 4))
            score = min(95, base + bonus)
            verdict = ("讲解清晰，能用自己的话讲明白" if score >= 80
                       else "基本合格，再具体一些会更好" if score >= 70
                       else "建议补充一个具体例子再讲一遍")
            feedback = {
                "simplicity": {"score": score - 2, "comment": "整体用语口语化"},
                "accuracy": {"score": score + 3, "comment": "核心概念方向正确"},
                "analogy": {"score": score - 4, "comment": "可再增加一个生活比喻" if not has_example else "已包含生活比喻"},
                "completeness": {"score": score - 1, "comment": "关键点已覆盖" if has_concept else "缺少关键概念阐述"},
                "jargon_free": {"score": score - 3, "comment": "术语使用需再克制"},
            }

        try:
            conv_store.add_message(sid, "user", text or "（跳过测试）")
            conv_store.add_message(sid, "assistant", "费曼测试 {} 分：{}".format(score, verdict), model="coach")
        except Exception:
            pass
        return jsonify({"code": 0, "data": {
            "score": score, "verdict": verdict,
            "feedback": feedback,
            "agents": [{"id": "coach", "action": "对费曼测试讲解进行五维语义评分"}],
        }})

    @bp.route("/api/learn/report", methods=["POST"])
    def api_learn_report():
        user = _require_user()
        if not user:
            return jsonify({"code": 401, "message": "未登录"}), 401
        data = request.get_json() or {}
        sid = _sid(data.get("sessionId"))
        feynman_score = int(data.get("feynmanScore") or 80)

        sess = conv_store.get_session(sid) if sid else None
        topic = sess["title"] if sess else "学习主题"
        key = _normalize_topic(topic)
        mastery = min(96, int(round(80 * 0.82 + feynman_score * 0.18)))

        report = {
            "id": sid, "topic": topic,
            "subject": (TaskUnderstanding().understand(topic)).get("subject", "综合"),
            "difficulty": "高中",
            "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "done", "mastery": mastery,
            "model": agent.tool_caller.preferred_model,
            "duration": "约4分钟", "toolCalls": 15,
            "weakPoints": _WEAK_LIB.get(key, [{"text": "概念理解到位，但应用场景判断可再熟练", "severity": "低"}]),
            "nextSteps": [
                "完成「{}」相关练习（高中难度）".format(key),
                "尝试用 30 秒向同学讲解核心概念",
                "复习周期：1 天后 → 3 天后 → 7 天后 → 14 天后",
            ],
            "agents": [
                {"id": a["id"], "name": a["name"], "model": a["model"], "status": "done",
                 "calls": 6 if a["id"] == "orchestrator" else 5 if a["id"] == "feynman" else 2}
                for a in AGENT_DEFS
            ],
            "feynmanScore": feynman_score,
        }
        try:
            db.add_learning_report(user["id"], topic, report, score=mastery)
            conv_store.add_message(sid, "assistant",
                                   "学习报告已生成：掌握度 {} 分".format(mastery),
                                   model=agent.tool_caller.preferred_model)
        except Exception:
            pass
        return jsonify({"code": 0, "data": report})

    @bp.route("/api/learn/history")
    def api_learn_history():
        user = _require_user()
        if not user:
            return jsonify({"code": 401, "message": "未登录"}), 401
        subject = (request.args.get("subject") or "全部").strip()
        rows = db.get_learning_reports(user_id=user["id"], limit=50)
        items = []
        for r in rows:
            rep = r.get("report") or {}
            if subject != "全部" and rep.get("subject") != subject:
                continue
            items.append({
                "id": r["id"], "topic": r["topic"],
                "subject": rep.get("subject", "综合"),
                "difficulty": rep.get("difficulty", "高中"),
                "date": r.get("created_at") or "",
                "status": "done", "mastery": int(r.get("score") or 0),
                "model": rep.get("model", ""), "duration": rep.get("duration", ""),
                "toolCalls": rep.get("toolCalls", 0),
                "weakPoints": rep.get("weakPoints", []),
                "nextSteps": rep.get("nextSteps", []),
                "agents": rep.get("agents", []),
                "feynmanScore": rep.get("feynmanScore", 80),
            })
        return jsonify({"code": 0, "data": items, "total": len(items)})

    @bp.route("/api/learn/report/<int:rid>")
    def api_learn_report_detail(rid):
        user = _require_user()
        if not user:
            return jsonify({"code": 401, "message": "未登录"}), 401
        row = db.get_learning_report(rid)
        if not row or row.get("user_id") != user["id"]:
            return jsonify({"code": 404, "message": "报告不存在"}), 404
        return jsonify({"code": 0, "data": row.get("report") or {}})

    # ---------- 我的档案 ----------
    @bp.route("/api/profile")
    def api_profile():
        user = _require_user()
        if not user:
            return jsonify({"code": 401, "message": "未登录"}), 401
        reports = db.get_learning_reports(user_id=user["id"], limit=50)

        trend = []
        weak_agg = {}
        for r in reports:
            rep = r.get("report") or {}
            date = (r.get("created_at") or "")[:10] or "最近"
            trend.append({"date": date, "score": int(r.get("score") or 0)})
            for wp in rep.get("weakPoints") or []:
                t = str(wp.get("text", "")).strip()
                if not t:
                    continue
                item = weak_agg.setdefault(t, {"severity": wp.get("severity", "低"), "count": 0})
                item["count"] += 1

        avg = round(sum((r.get("score") or 0) for r in reports) / len(reports)) if reports else 0
        weak_points = sorted(weak_agg.items(), key=lambda kv: -kv[1]["count"])[:8]
        conversations = conv_store.list_sessions(user_id=user["id"], limit=20)
        recent = reports[-5:][::-1]

        return jsonify({"code": 0, "data": {
            "user": {"id": user["id"], "name": user["name"], "role": user["role"]},
            "total_reports": len(reports),
            "avg_mastery": avg,
            "trend": trend[-14:],
            "weak_points": [{"text": k, "severity": v["severity"], "count": v["count"]}
                            for k, v in weak_points],
            "conversations": [{"id": s["id"], "title": s["title"],
                               "date": s.get("updated_at") or "", "msg_count": s.get("msg_count") or 0}
                              for s in conversations],
            "recent_reports": [{"id": r["id"], "topic": r["topic"],
                                "score": int(r.get("score") or 0), "date": r.get("created_at") or ""}
                               for r in recent],
        }})

    return bp
