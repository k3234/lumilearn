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

from flask import Flask, jsonify, render_template_string, request

from framework.database import db

db.init()

app = Flask(__name__)

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
# 仪表盘页面（内联深色主题 + SVG 图表，无 CDN）
# ============================================================
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LumiLearn · 学习分析</title>
<style>
  :root {
    --bg:#0C1015; --surface:#151B24; --surface2:#1C2431; --border:#26303F;
    --text:#EDF1F6; --sub:#9AA6B7; --faint:#66717F;
    --accent:#E8A33D; --mint:#46C08A; --sky:#5BA8E8; --danger:#EF6C6C;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:-apple-system,"PingFang SC","Microsoft YaHei","Segoe UI",sans-serif; min-height:100vh; }
  body::before { content:""; position:fixed; inset:0; z-index:-1; background:radial-gradient(720px 420px at 88% -4%, rgba(232,163,61,.10), transparent 62%), var(--bg); }
  .wrap { max-width:1180px; margin:0 auto; padding:32px 28px 64px; }
  .kicker { font-family:"SF Mono",Consolas,monospace; font-size:12px; color:var(--accent); letter-spacing:.12em; margin-bottom:6px; }
  h1 { font-size:32px; font-weight:600; font-family:"Noto Serif SC","Songti SC",serif; }
  .sub { color:var(--sub); margin-top:8px; font-size:14px; }
  .stats { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-top:26px; }
  .stat { background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:18px; box-shadow:0 8px 24px rgba(0,0,0,.35); }
  .stat b { display:block; font-size:28px; color:var(--accent); font-family:"SF Mono",Consolas,monospace; }
  .stat span { font-size:12px; color:var(--faint); }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:18px; }
  .card { background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:20px; box-shadow:0 8px 24px rgba(0,0,0,.35); }
  .card h2 { font-size:16px; margin-bottom:14px; display:flex; align-items:center; gap:8px; }
  .card h2 .dot { width:8px; height:8px; border-radius:50%; background:var(--accent); }
  .faint { color:var(--faint); }
  .empty { padding:32px; text-align:center; color:var(--faint); }
  svg text { fill:var(--sub); font-size:11px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { text-align:left; color:var(--faint); font-weight:500; padding:8px 10px; border-bottom:1px solid var(--border); font-size:12px; }
  td { padding:9px 10px; border-bottom:1px solid rgba(38,48,63,.6); }
  tr:hover td { background:var(--surface2); }
  .tag { display:inline-block; padding:2px 9px; border-radius:999px; font-size:11px; }
  .tag.good { background:rgba(70,192,138,.12); color:var(--mint); }
  .tag.mid { background:rgba(232,163,61,.13); color:var(--accent); }
  .tag.bad { background:rgba(239,108,108,.12); color:var(--danger); }
  .weak { display:flex; align-items:center; gap:10px; padding:9px 2px; border-bottom:1px solid rgba(38,48,63,.6); font-size:13px; color:var(--sub); }
  .weak:last-child { border-bottom:none; }
  .weak .c { margin-left:auto; font-family:"SF Mono",Consolas,monospace; color:var(--accent); }
  .heat { display:grid; grid-template-columns:repeat(auto-fill,minmax(118px,1fr)); gap:10px; }
  .cell { border-radius:10px; padding:12px 10px; text-align:center; border:1px solid var(--border); }
  .cell b { font-size:18px; font-family:"SF Mono",Consolas,monospace; }
  .cell span { display:block; font-size:11px; color:var(--sub); margin-top:3px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  @media (max-width:900px){ .grid{grid-template-columns:1fr;} .stats{grid-template-columns:repeat(2,1fr);} }
  @media (max-width:480px){ .stats{grid-template-columns:repeat(2,1fr);} }
</style>
</head>
<body>
<div class="wrap">
  <p class="kicker">LEARNING ANALYTICS · LOCAL-FIRST</p>
  <h1>学习分析仪表盘</h1>
  <p class="sub">基于共享数据库实时统计：掌握度趋势、学科对比、薄弱点与知识点掌握情况。</p>

  <div class="stats" id="stats"></div>

  <div class="grid">
    <div class="card"><h2><span class="dot"></span>掌握度趋势</h2><div id="trend"></div></div>
    <div class="card"><h2><span class="dot"></span>学科掌握度</h2><div id="subjects"></div></div>
    <div class="card"><h2><span class="dot"></span>薄弱点排行</h2><div id="weak"></div></div>
    <div class="card"><h2><span class="dot"></span>知识点掌握度</h2><div id="concepts"></div></div>
  </div>

  <div class="card" style="margin-top:18px">
    <h2><span class="dot"></span>最近学习报告</h2>
    <div style="overflow-x:auto"><table>
      <thead><tr><th>主题</th><th>学生</th><th>时间</th><th>掌握度</th></tr></thead>
      <tbody id="recent"></tbody>
    </table></div>
  </div>
</div>

<script>
function $(id){return document.getElementById(id);}
async function get(p){const r=await fetch(p);const j=await r.json();return j.data||[];}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}

async function loadStats(){
  const d=await get('/api/dashboard/overview');
  const acc=d.answers?Math.round((d.answers-d.wrongAnswers)/d.answers*100):0;
  $('stats').innerHTML=[
    ['学生数',d.students],['学习报告',d.reports],['平均掌握度',d.avgMastery+'%'],['答题正确率',acc+'%']
  ].map(function(x){return '<div class="stat"><b>'+x[1]+'</b><span>'+x[0]+'</span></div>';}).join('');
}

async function loadTrend(){
  const d=await get('/api/dashboard/trend?limit=14');
  const box=$('trend');
  if(!d.length){box.innerHTML='<div class="empty">暂无报告数据</div>';return;}
  const W=520,H=170,pad=30;
  const max=Math.max.apply(null,d.map(function(x){return x.avg;}))||100;
  const min=Math.min.apply(null,d.map(function(x){return x.avg;}))||0;
  const span=(max-min)||1;
  const x=function(i){return pad+(W-pad*2)*i/(d.length-1);};
  const y=function(v){return H-pad-((v-min)/span)*(H-pad*2);};
  const pts=d.map(function(p,i){return x(i)+','+y(p.avg);}).join(' ');
  let poly='<svg viewBox="0 0 '+W+' '+H+'" width="100%" style="max-width:520px">';
  poly+='<polyline fill="none" stroke="#E8A33D" stroke-width="2.5" points="'+pts+'"/>';
  d.forEach(function(p,i){
    if(i%Math.ceil(d.length/7)===0||i===d.length-1){
      poly+='<circle cx="'+x(i)+'" cy="'+y(p.avg)+'" r="3.5" fill="#E8A33D"/>';
      poly+='<text x="'+x(i)+'" y="'+(H-6)+'" text-anchor="middle">'+esc(String(p.date).slice(5))+'</text>';
    }
  });
  poly+='<text x="8" y="'+y(d[d.length-1].avg)+'" fill="#46C08A">'+d[d.length-1].avg+'%</text>';
  poly+='</svg>';
  box.innerHTML=poly;
}

async function loadSubjects(){
  const d=await get('/api/dashboard/subjects');
  const box=$('subjects');
  if(!d.length){box.innerHTML='<div class="empty">暂无数据</div>';return;}
  const max=Math.max.apply(null,d.map(function(x){return x.avg;}))||100;
  let html='<svg viewBox="0 0 520 180" width="100%" style="max-width:520px">';
  const bw=Math.min(64,(520-60)/d.length);
  d.forEach(function(s,i){
    const h=Math.max(4,(s.avg/max)*110);
    const x=40+i*(bw+18), y=150-h;
    html+='<rect x="'+x+'" y="'+y+'" width="'+bw+'" height="'+h+'" rx="6" fill="#E8A33D" opacity="'+(0.55+0.45*i/d.length)+'"/>';
    html+='<text x="'+(x+bw/2)+'" y="'+(y-6)+'" text-anchor="middle" fill="#46C08A">'+s.avg+'%</text>';
    html+='<text x="'+(x+bw/2)+'" y="172" text-anchor="middle">'+esc(s.subject)+'</text>';
    html+='<text x="'+(x+bw/2)+'" y="166" text-anchor="middle" font-size="9" fill="#66717F">'+s.count+'次</text>';
  });
  html+='</svg>';
  box.innerHTML=html;
}

async function loadWeak(){
  const d=await get('/api/dashboard/weakpoints?limit=8');
  const box=$('weak');
  if(!d.length){box.innerHTML='<div class="empty">暂无薄弱点数据</div>';return;}
  box.innerHTML=d.map(function(w){
    const cls=w.severity==='高'?'bad':w.severity==='中'?'mid':'good';
    return '<div class="weak"><span class="tag '+cls+'">'+esc(w.severity)+'</span><span>'+esc(w.text)+'</span><span class="c">×'+w.count+'</span></div>';
  }).join('');
}

async function loadConcepts(){
  const d=await get('/api/dashboard/concepts');
  const box=$('concepts');
  if(!d.length){box.innerHTML='<div class="empty">暂无知识点数据（学习后生成）</div>';return;}
  box.innerHTML='<div class="heat">'+d.map(function(c){
    const col=c.value>=70?'rgba(70,192,138,.16)':c.value>=45?'rgba(232,163,61,.15)':'rgba(239,108,108,.14)';
    const tx=c.value>=70?'#46C08A':c.value>=45?'#E8A33D':'#EF6C6C';
    return '<div class="cell" style="background:'+col+'"><b style="color:'+tx+'">'+c.value+'%</b><span>'+esc(c.name)+'</span></div>';
  }).join('')+'</div>';
}

async function loadRecent(){
  const d=await get('/api/dashboard/recent?limit=10');
  const box=$('recent');
  if(!d.length){box.innerHTML='<tr><td colspan="4" class="empty">暂无学习报告</td></tr>';return;}
  box.innerHTML=d.map(function(r){
    const cls=r.score>=80?'good':r.score>=60?'mid':'bad';
    return '<tr><td>'+esc(r.topic)+'</td><td>'+esc(r.user)+'</td><td class="faint">'+esc(r.date)+'</td>'+
           '<td><span class="tag '+cls+'">'+r.score+'%</span></td></tr>';
  }).join('');
}

loadStats(); loadTrend(); loadSubjects(); loadWeak(); loadConcepts(); loadRecent();
setInterval(function(){loadStats();loadTrend();},30000);
</script>
</body>
</html>
"""


@app.route("/")
def dashboard_page():
    return render_template_string(DASHBOARD_HTML)


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
    main()
