#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 学习分析仪表盘（Learning Analytics Dashboard）
============================================================
独立端口服务（默认 18090），基于共享数据库做可视化分析：

- 数据源：learning_reports（学习报告/掌握度）、answers（答题/错题）、
          concept_understanding（知识点掌握度）、users
- 页面：单页深色仪表盘，SVG 手绘图表（无 CDN，低端设备友好）
- API：
    GET / 等 → 仪表盘页面
    GET /api/dashboard/overview     → 总量卡片
    GET /api/dashboard/trend        → 掌握度趋势（按日）
    GET /api/dashboard/subjects     → 学科掌握度对比
    GET /api/dashboard/weakpoints   → 薄弱点排行
    GET /api/dashboard/concepts     → 知识点掌握度热力
    GET /api/dashboard/recent       → 最近学习报告

只读服务，不做任何写操作；所有数据来自共享 lumilearn.db。
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, render_template, request

from framework.database import db

db.init()

# 模板目录：兼容本地 remote/templates 与远程 tianhong/templates 两种部署结构
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "remote" / "templates"
if not TEMPLATE_DIR.exists():
    TEMPLATE_DIR = BASE_DIR / "tianhong" / "templates"

app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

# ============================================================
# 数据查询
# ============================================================
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
    return {
        "students": users[0]["c"] if users else 0,
        "reports": reports[0]["c"] if reports else 0,
        "avgMastery": round(reports[0]["avg"]) if reports else 0,
        "answers": answers[0]["c"] if answers else 0,
        "wrongAnswers": (answers[0]["c"] - answers[0]["ok"]) if answers else 0,
    }


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
    out = []
    for subj, item in agg.items():
        out.append({"subject": subj, "avg": round(item["sum"] / item["n"]) if item["n"] else 0,
                    "count": item["n"]})
    out.sort(key=lambda x: -x["count"])
    return out


def weakpoints(limit=8):
    # 从报告 weak_points 聚合 + answers 错题补充
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


# ============================================================
# API
# ============================================================
@app.route("/api/dashboard/overview")
def api_overview():
    return jsonify({"code": 0, "data": overview()})


@app.route("/api/dashboard/trend")
def api_trend():
    return jsonify({"code": 0, "data": trend(int(request.args.get("limit", 14)))})


@app.route("/api/dashboard/subjects")
def api_subjects():
    return jsonify({"code": 0, "data": subjects()})


@app.route("/api/dashboard/weakpoints")
def api_weakpoints():
    return jsonify({"code": 0, "data": weakpoints(int(request.args.get("limit", 8)))})


@app.route("/api/dashboard/concepts")
def api_concepts():
    return jsonify({"code": 0, "data": concepts()})


@app.route("/api/dashboard/recent")
def api_recent():
    return jsonify({"code": 0, "data": recent(int(request.args.get("limit", 10)))})


# ============================================================
# 仪表盘页面（独立模板 remote/templates/analytics_dashboard.html）
# ============================================================
@app.route("/")
def dashboard_page():
    return render_template("analytics_dashboard.html")


# ============================================================
# 启动
# ============================================================
def _get_analytics_port() -> int:
    """从 port_settings 读取分析仪表盘端口（可被环境变量 ANALYTICS_PORT 覆盖）"""
    env_port = os.environ.get("ANALYTICS_PORT", "")
    if env_port.isdigit():
        return int(env_port)
    try:
        from framework.services.provider_service import get_provider_service
        cfg = get_provider_service().get_port_settings().get("analytics_dashboard", {})
        if cfg.get("port"):
            return int(cfg["port"])
    except Exception:
        pass
    return 18090


def main():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"

    port = _get_analytics_port()
    print("\n" + "=" * 60)
    print("  📊 LumiLearn 学习分析仪表盘 (Analytics Dashboard)")
    print("=" * 60)
    print("  📍 访问地址: http://{}:{}".format(ip, port))
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
