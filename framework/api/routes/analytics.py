# -*- coding: utf-8 -*-
"""
LumiLearn 学习分析仪表盘 Blueprint（Analytics Dashboard）
==========================================================
将原独立 analytics_dashboard.py 的数据查询与 API 路由抽为可复用 Blueprint，
供统一管理门户 server.py 注册（同端口访问 /api/dashboard/*）。

只读服务，不做任何写操作；所有数据来自共享 lumilearn.db。
页面（analytics_dashboard.html）由统一门户的 /analytics 入口路由提供。
"""
import json

from flask import Blueprint, jsonify, request

from framework.database import db


def _rows(sql, args=()):
    try:
        cur = db.conn.execute(sql, args)
        return [dict(r) for r in cur.fetchall()]
    except Exception:
        return []


def overview():
    users = _rows("SELECT COUNT(*) AS c FROM users WHERE role='student'")
    reports = _rows("SELECT COUNT(*) AS c, COALESCE(AVG(score),0) AS avg FROM learning_reports")
    answers = _rows("SELECT COUNT(*) AS c, COALESCE(SUM(is_correct),0) AS ok FROM answers")
    mastery_row = _rows("SELECT COALESCE(AVG(mastery),0) AS avg FROM progress")
    avg_mastery = mastery_row[0]["avg"] if mastery_row else 0
    return {
        "students": users[0]["c"] if users else 0,
        "reports": reports[0]["c"] if reports else 0,
        "avgMastery": round(avg_mastery, 2) if avg_mastery else round(reports[0]["avg"]) if reports else 0,
        "avgReportScore": round(reports[0]["avg"]) if reports else 0,
        "answers": answers[0]["c"] if answers else 0,
        "wrongAnswers": (answers[0]["c"] - answers[0]["ok"]) if answers else 0,
    }


def mastery_dist():
    """按知识点平均掌握度分布（来自 progress）。"""
    rows = _rows(
        "SELECT p.node_id AS node, COALESCE(k.name, p.node_id) AS name, "
        "AVG(p.mastery) AS avg, COUNT(*) AS attempts "
        "FROM progress p LEFT JOIN knowledge_nodes k ON k.id=p.node_id "
        "GROUP BY p.node_id ORDER BY avg ASC LIMIT 50"
    )
    return [{"node": r["node"], "name": r["name"], "avg": round(r["avg"] or 0, 3),
             "attempts": r["attempts"]} for r in rows]


def weaknodes(limit=10):
    """薄弱知识点 topN：平均掌握度 <0.6，按缺口排序。"""
    rows = _rows(
        "SELECT p.node_id AS node, COALESCE(k.name, p.node_id) AS name, "
        "AVG(p.mastery) AS avg, COUNT(DISTINCT p.user_id) AS students "
        "FROM progress p LEFT JOIN knowledge_nodes k ON k.id=p.node_id "
        "WHERE p.mastery < 0.6 "
        "GROUP BY p.node_id ORDER BY avg ASC LIMIT ?",
        (int(limit),),
    )
    return [{"node": r["node"], "name": r["name"], "avg": round(r["avg"] or 0, 3),
             "students": r["students"]} for r in rows]


def trend(limit=14):
    rows = _rows(
        "SELECT date(created_at) AS d, COUNT(*) AS c, AVG(score) AS avg "
        "FROM learning_reports GROUP BY d ORDER BY d DESC LIMIT ?",
        (int(limit),),
    )
    rows.reverse()
    return [{"date": r["d"] or "", "avg": round(r["avg"] or 0), "count": r["c"]} for r in rows]


def subjects():
    rows = _rows("SELECT id, report_json, score FROM learning_reports ORDER BY id DESC LIMIT 300")
    agg = {}
    for r in rows:
        try:
            rep = json.loads(r.get("report_json") or "{}")
        except Exception:
            rep = {}
        subj = rep.get("subject") or "综合"
        item = agg.setdefault(subj, {"sum": 0, "n": 0})
        item["sum"] += float(r.get("score") or 0)
        item["n"] += 1
    out = [{"subject": subj, "avg": round(item["sum"] / item["n"]) if item["n"] else 0,
            "count": item["n"]} for subj, item in agg.items()]
    out.sort(key=lambda x: -x["count"])
    return out


def weakpoints(limit=8):
    rows = _rows("SELECT report_json FROM learning_reports ORDER BY id DESC LIMIT 300")
    agg = {}
    for r in rows:
        try:
            rep = json.loads(r.get("report_json") or "{}")
        except Exception:
            rep = {}
        for wp in rep.get("weakPoints") or []:
            text = str(wp.get("text", "")).strip()
            if not text:
                continue
            item = agg.setdefault(text, {"severity": wp.get("severity", "低"), "count": 0})
            item["count"] += 1
    wrong = _rows("SELECT topic, COUNT(*) AS c FROM answers WHERE is_correct=0 AND topic<>'' "
                  "GROUP BY topic ORDER BY c DESC LIMIT 5")
    out = [{"text": k, "severity": v["severity"], "count": v["count"]} for k, v in agg.items()]
    out.sort(key=lambda x: -x["count"])
    for w in wrong:
        out.append({"text": "错题专题：「{}」".format(w["topic"]), "severity": "高", "count": w["c"]})
    return out[:limit]


def concepts():
    rows = _rows(
        "SELECT c.user_id, c.node_id, c.understanding, c.state, "
        "COALESCE(k.name, c.node_id) AS name "
        "FROM concept_understanding c LEFT JOIN knowledge_nodes k ON k.id=c.node_id "
        "ORDER BY c.understanding DESC LIMIT 24"
    )
    return [{"name": r["name"], "node": r["node_id"], "value": round((r["understanding"] or 0) * 100),
             "state": r["state"], "user": r["user_id"]} for r in rows]


def recent(limit=10):
    rows = _rows(
        "SELECT r.id, r.topic, r.score, r.created_at, u.name AS uname "
        "FROM learning_reports r LEFT JOIN users u ON u.id=r.user_id "
        "ORDER BY r.id DESC LIMIT ?",
        (int(limit),),
    )
    return [{"id": r["id"], "topic": r["topic"], "score": int(r["score"] or 0),
             "date": r["created_at"] or "", "user": r["uname"] or "—"} for r in rows]


def create_analytics_bp() -> Blueprint:
    """创建学习分析仪表盘 Blueprint（仅 API，页面由统一门户 /analytics 提供）。"""
    bp = Blueprint("analytics_dashboard", __name__)

    @bp.route("/api/dashboard/overview")
    def api_overview():
        return jsonify({"code": 0, "data": overview()})

    @bp.route("/api/dashboard/mastery")
    def api_mastery():
        return jsonify({"code": 0, "data": mastery_dist()})

    @bp.route("/api/dashboard/weaknodes")
    def api_weaknodes():
        return jsonify({"code": 0, "data": weaknodes(int(request.args.get("limit", 10)))})

    @bp.route("/api/dashboard/trend")
    def api_trend():
        return jsonify({"code": 0, "data": trend(int(request.args.get("limit", 14)))})

    @bp.route("/api/dashboard/subjects")
    def api_subjects():
        return jsonify({"code": 0, "data": subjects()})

    @bp.route("/api/dashboard/weakpoints")
    def api_weakpoints():
        return jsonify({"code": 0, "data": weakpoints(int(request.args.get("limit", 8)))})

    @bp.route("/api/dashboard/concepts")
    def api_concepts():
        return jsonify({"code": 0, "data": concepts()})

    @bp.route("/api/dashboard/recent")
    def api_recent():
        return jsonify({"code": 0, "data": recent(int(request.args.get("limit", 10)))})

    return bp