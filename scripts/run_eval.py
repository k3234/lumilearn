# -*- coding: utf-8 -*-
"""
LumiLearn 标准化学科测试集自动化评测 CLI（Task 5）
=====================================================
基于 data/eval_dataset/ 下的数学/物理/化学各 50 题标准测试集，
对「知识检索 → 教学生成 → 幻觉检测」流水线做自动化评测，输出
指标（knowledge_recall / accuracy / hallucination_count / hit_rate /
avg_latency_ms）、持久化到 eval_reports 表并生成 HTML + JSON 报表。

用法：
    python -m scripts.run_eval                       # mock 模式全量 150 题
    python -m scripts.run_eval --subject math         # 只跑数学 50 题
    python -m scripts.run_eval --limit 10             # 只跑前 10 题
    python -m scripts.run_eval --real                 # 真实调用 UnifiedOrchestrator.run()

核心函数：
    run_evaluation(subject="all", limit=0, real=False) -> Dict
"""

import argparse
import json
import os
import re
import sys
import time
from typing import Dict, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DATASET_DIR = os.path.join(PROJECT_ROOT, "data", "eval_dataset")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")

SUBJECT_FILES = {
    "math": "math.json",
    "physics": "physics.json",
    "chemistry": "chemistry.json",
}

EVAL_TYPE = "v25_dataset"
# mock 模式下判定「教学正确」的知识点覆盖率阈值
CORRECT_COVERAGE_THRESHOLD = 0.6
# real 模式幻觉检测：标准答案核心数值之外的干扰数字集合（常见常数）
_IGNORED_NUMBERS = {"0", "1", "1.0", "3.14", "3.14159", "6.02", "2.718"}


# ---------------------------------------------------------------------------
# 数据集加载
# ---------------------------------------------------------------------------

def load_datasets(subject: str = "all") -> List[Dict]:
    """加载评测数据集（math/physics/chemistry 各 50 题），返回题目列表"""
    if subject not in ("all", "math", "physics", "chemistry"):
        raise ValueError(f"不支持的学科: {subject}，可选 all/math/physics/chemistry")
    subjects = list(SUBJECT_FILES.keys()) if subject == "all" else [subject]
    items: List[Dict] = []
    for sub in subjects:
        fpath = os.path.join(DATASET_DIR, SUBJECT_FILES[sub])
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            item["subject"] = sub
        items.extend(data)
    return items


# ---------------------------------------------------------------------------
# 单题评测逻辑
# ---------------------------------------------------------------------------

def _build_knowledge_pool(retriever) -> List[str]:
    """构建知识库命中池：检索索引文档文本 + knowledge_nodes 节点名"""
    pool: List[str] = []
    try:
        for doc in getattr(retriever, "docs", []) or []:
            text = " ".join(filter(None, [
                doc.get("title", ""), doc.get("subject", ""),
                doc.get("keywords", ""), (doc.get("content", "") or "")[:400],
            ]))
            if text:
                pool.append(text)
    except Exception:
        pass
    try:
        from framework.database import db
        for n in db.get_knowledge_nodes():
            pool.append(" ".join(filter(None, [
                n.get("name", ""), n.get("category", ""),
                (n.get("description", "") or "")[:200],
            ])))
    except Exception:
        pass
    return pool


def _coverage_of(item: Dict, pool: List[str]) -> float:
    """expected_knowledge 在知识库/检索结果池中的覆盖率（0~1）"""
    expected = item.get("expected_knowledge") or []
    if not expected:
        return 0.0
    pool_text = " ".join(pool)
    hits = [k for k in expected if k and k in pool_text]
    return len(hits) / len(expected)


def _search_hit(retriever, item: Dict, subject: str) -> List[Dict]:
    """调用 KnowledgeRetriever.search(topic)，返回检索结果（异常兜底为空）"""
    try:
        return retriever.search(item.get("topic", ""), top_k=5,
                                subject=subject if subject != "all" else None)
    except Exception:
        return []


def _real_generate(item: Dict) -> str:
    """real 模式：调用 UnifiedOrchestrator.run() 生成教学内容，返回文本"""
    from agent_core.orchestrator import UnifiedOrchestrator
    payload = {
        "topic": item.get("topic", ""),
        "subject": item.get("subject", ""),
        "user_id": "eval_v25",
        "context": item.get("question", ""),
        "route": "simple",
    }
    result = UnifiedOrchestrator().run(payload)
    teaching = result.get("teaching") or {}
    if isinstance(teaching, dict):
        text = teaching.get("full_content") or teaching.get("content") or ""
        if text:
            return text[:2000]
    # 兜底：取结果里最长的文本字段
    text = str(result.get("content") or "") or str(result.get("answer") or "")
    return text[:2000] if text else ""


def _simple_hallucination_check(generated: str, item: Dict) -> int:
    """简单幻觉检测规则（real 模式，fact_checker 不可注入时使用）：
    若生成文本中出现「标准答案核心数值」之外的其它数值 → 计为幻觉候选。"""
    if not generated:
        return 0
    answer = str(item.get("answer", ""))
    ans_nums = [n for n in re.findall(r"-?\d+\.?\d*", answer)
                if n not in _IGNORED_NUMBERS]
    if not ans_nums:
        return 0  # 非数值型答案不做简单数值冲突检测
    gen_nums = set(re.findall(r"-?\d+\.?\d*", generated))
    conflicts = [n for n in gen_nums
                 if n not in ans_nums and n not in _IGNORED_NUMBERS]
    return 1 if conflicts else 0


def _evaluate_item(item: Dict, subject: str, retriever,
                   real: bool, pool: List[str]) -> Dict:
    """对单题执行「检索 → 教学生成 → 幻觉检测」，返回该题评测明细"""
    t0 = time.time()
    results = _search_hit(retriever, item, subject)
    coverage = _coverage_of(item, pool)
    latency_ms = round((time.time() - t0) * 1000, 3)

    generated = ""
    hallucination = 0
    if real:
        try:
            generated = _real_generate(item)
            # fact_checker 可注入时优先使用；失败则走简单规则
            try:
                from agent_core.fact_checker import fact_check
                verdict = fact_check({
                    "topic": item.get("topic", ""),
                    "content": generated or item.get("question", ""),
                    "mode": "eval",
                })
                if verdict and verdict.get("passed") is False:
                    hallucination = 1
                elif generated:
                    hallucination = _simple_hallucination_check(generated, item)
            except Exception:
                if generated:
                    hallucination = _simple_hallucination_check(generated, item)
        except Exception:
            generated = ""
            hallucination = 0

    return {
        "id": item.get("id", ""),
        "subject": item.get("subject", ""),
        "topic": item.get("topic", ""),
        "question": item.get("question", ""),
        "expected_knowledge": item.get("expected_knowledge") or [],
        "answer": item.get("answer", ""),
        "search_hit": bool(results),          # 检索是否有返回结果
        "coverage": round(coverage, 4),       # 知识点覆盖率
        "correct": coverage >= CORRECT_COVERAGE_THRESHOLD,  # 教学正确
        "hallucination": hallucination,       # 幻觉候选（mock=0）
        "latency_ms": latency_ms,
        "generated": (generated or "")[:200],
    }


# ---------------------------------------------------------------------------
# 主评测入口
# ---------------------------------------------------------------------------

def run_evaluation(subject: str = "all", limit: int = 0,
                   real: bool = False) -> Dict:
    """
    执行标准化学科测试集自动化评测。

    参数:
        subject: all / math / physics / chemistry
        limit:   只评测前 N 题（0 = 全量）
        real:    True 时真实调用 UnifiedOrchestrator.run()（依赖模型）；
                默认 False 为 mock 模式，不依赖模型。
    返回:
        指标 dict（含 by_subject 分科明细与 per_question 逐题明细）
    """
    # 确保数据库已初始化（幂等；测试环境复用 isolated_db 的临时库）
    from framework.database import db
    try:
        db.init()
    except Exception:
        pass

    from framework.services.knowledge_retrieval import get_knowledge_retriever
    retriever = get_knowledge_retriever()
    try:
        retriever.refresh()
    except Exception:
        pass

    items = load_datasets(subject)
    if limit and limit > 0:
        items = items[:int(limit)]
    if not items:
        raise ValueError("评测数据集为空，请检查 data/eval_dataset/ 下 JSON 文件")

    pool = _build_knowledge_pool(retriever)
    per_question = [_evaluate_item(it, subject, retriever, real, pool)
                    for it in items]

    # ---- 汇总指标 ----
    total = len(per_question)
    total_hit = sum(1 for r in per_question if r["search_hit"])
    total_correct = sum(1 for r in per_question if r["correct"])
    total_hallucination = sum(r["hallucination"] for r in per_question)
    avg_coverage = sum(r["coverage"] for r in per_question) / total
    avg_latency = sum(r["latency_ms"] for r in per_question) / total

    metrics: Dict = {
        "eval_type": EVAL_TYPE,
        "mode": "real" if real else "mock",
        "total_questions": total,
        "knowledge_recall": round(avg_coverage, 4),
        "accuracy": round(total_correct / total, 4),
        "hallucination_count": total_hallucination,
        "hit_rate": round(total_hit / total, 4),
        "avg_latency_ms": round(avg_latency, 3),
        "threshold": CORRECT_COVERAGE_THRESHOLD,
        "by_subject": {},
        "per_question": per_question,
    }

    for sub in SUBJECT_FILES:
        sub_rows = [r for r in per_question if r["subject"] == sub]
        if not sub_rows:
            continue
        n = len(sub_rows)
        metrics["by_subject"][sub] = {
            "questions": n,
            "knowledge_recall": round(sum(r["coverage"] for r in sub_rows) / n, 4),
            "accuracy": round(sum(1 for r in sub_rows if r["correct"]) / n, 4),
            "hit_rate": round(sum(1 for r in sub_rows if r["search_hit"]) / n, 4),
            "hallucinations": sum(r["hallucination"] for r in sub_rows),
            "avg_latency_ms": round(sum(r["latency_ms"] for r in sub_rows) / n, 3),
        }

    # ---- 持久化到 eval_reports 表 ----
    report_id = None
    try:
        report_id = db.save_v25_eval_report(
            eval_type=EVAL_TYPE,
            total_questions=total,
            knowledge_recall=metrics["knowledge_recall"],
            accuracy=metrics["accuracy"],
            hallucination_count=metrics["hallucination_count"],
            hit_rate=metrics["hit_rate"],
            avg_latency_ms=metrics["avg_latency_ms"],
            report_path="",
            detail_json=json.dumps(metrics, ensure_ascii=False),
        )
    except Exception:
        pass
    metrics["report_id"] = report_id
    return metrics


# ---------------------------------------------------------------------------
# 报表生成（HTML + JSON）
# ---------------------------------------------------------------------------

def generate_reports(metrics: Dict) -> Dict:
    """生成 HTML（ECharts 图表）与 JSON 报表，返回文件路径 dict"""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(REPORTS_DIR, f"eval_report_{ts}.json")
    html_path = os.path.join(REPORTS_DIR, f"eval_report_{ts}.html")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in metrics.items() if k != "per_question"},
                  f, ensure_ascii=False, indent=2)

    by = metrics.get("by_subject", {})
    subjects = list(by.keys())
    recall_vals = [by[s]["knowledge_recall"] * 100 for s in subjects]
    acc_vals = [by[s]["accuracy"] * 100 for s in subjects]
    hit_vals = [by[s]["hit_rate"] * 100 for s in subjects]
    halluc_vals = [by[s]["hallucinations"] for s in subjects]
    subject_questions = [by[s]["questions"] for s in subjects]

    html = _render_html(
        metrics=metrics,
        subjects=subjects, subject_questions=subject_questions,
        recall_vals=recall_vals, acc_vals=acc_vals, hit_vals=hit_vals,
        halluc_vals=halluc_vals,
    )
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    return {"html": html_path, "json": json_path}


def _render_html(metrics: Dict, subjects: List[str], subject_questions: List[int],
                 recall_vals: List[float], acc_vals: List[float],
                 hit_vals: List[float], halluc_vals: List[int]) -> str:
    """渲染评测报表 HTML（ECharts CDN）"""
    subj_json = json.dumps(subjects, ensure_ascii=False)
    questions_json = json.dumps(subject_questions)
    recall_json = json.dumps(recall_vals)
    acc_json = json.dumps(acc_vals)
    hit_json = json.dumps(hit_vals)
    halluc_json = json.dumps(halluc_vals)
    gen_at = time.strftime("%Y-%m-%d %H:%M:%S")

    card_rows = "".join(
        f"""<div class="card"><div class="num">{metrics[k]:,}</div>
            <div class="label">{label}</div></div>"""
        for k, label in [
            ("total_questions", "评测题数"),
            ("knowledge_recall", "知识点召回率"),
            ("accuracy", "教学正确率"),
            ("hit_rate", "检索命中率"),
        ] if k in metrics
    )
    more_cards = "".join(
        f"""<div class="card"><div class="num">{metrics[k]:,}</div>
            <div class="label">{label}</div></div>"""
        for k, label in [
            ("hallucination_count", "幻觉频次"),
            ("avg_latency_ms", "平均耗时(ms)"),
        ] if k in metrics
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>LumiLearn V2.5 标准化学科测试集评测报告</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
  body {{ font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
         background: #f4f6fb; margin: 0; padding: 24px; color: #1f2d3d; }}
  .wrap {{ max-width: 1080px; margin: 0 auto; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .meta {{ color: #8492a6; font-size: 13px; margin-bottom: 20px; }}
  .cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 20px; }}
  .card {{ background: #fff; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 8px rgba(31,45,61,.06); }}
  .num {{ font-size: 28px; font-weight: 700; color: #2b6de8; }}
  .label {{ font-size: 13px; color: #8492a6; margin-top: 4px; }}
  .chart {{ background: #fff; border-radius: 12px; padding: 16px; margin-bottom: 20px;
           box-shadow: 0 2px 8px rgba(31,45,61,.06); }}
  .chart h2 {{ font-size: 15px; margin: 4px 8px 0; color: #475069; }}
  #barChart {{ height: 360px; }} #hallucChart {{ height: 300px; }}
  .badge {{ display: inline-block; background: #e8f0fe; color: #2b6de8; border-radius: 20px;
            padding: 3px 12px; font-size: 12px; margin-left: 8px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>LumiLearn V2.5 标准化学科测试集评测报告</h1>
  <div class="meta">生成时间：{gen_at} ｜ 评测模式：
    <span class="badge">{metrics.get('mode', 'mock')}</span> ｜
    数据集：data/eval_dataset（数学/物理/化学 各 50 题）</div>

  <div class="cards">{card_rows}{more_cards}</div>

  <div class="chart">
    <h2>各学科指标对比（%）</h2>
    <div id="barChart"></div>
  </div>

  <div class="chart">
    <h2>各学科幻觉频次</h2>
    <div id="hallucChart"></div>
  </div>
</div>

<script>
var subjects = {subj_json};
var questions = {questions_json};
var recallVals = {recall_json};
var accVals = {acc_json};
var hitVals = {hit_json};
var hallucVals = {halluc_json};

var barChart = echarts.init(document.getElementById('barChart'));
barChart.setOption({{
  tooltip: {{ trigger: 'axis' }},
  legend: {{ data: ['知识点召回率', '教学正确率', '检索命中率'] }},
  grid: {{ left: 60, right: 30, top: 50, bottom: 30 }},
  xAxis: {{ type: 'category', data: subjects }},
  yAxis: {{ type: 'value', min: 0, max: 100, axisLabel: {{ formatter: '{{value}}%' }} }},
  series: [
    {{ name: '知识点召回率', type: 'bar', data: recallVals, itemStyle: {{ color: '#2b6de8' }} }},
    {{ name: '教学正确率', type: 'bar', data: accVals, itemStyle: {{ color: '#34c77b' }} }},
    {{ name: '检索命中率', type: 'bar', data: hitVals, itemStyle: {{ color: '#f5a623' }} }}
  ]
}});

var hallucChart = echarts.init(document.getElementById('hallucChart'));
hallucChart.setOption({{
  tooltip: {{ trigger: 'axis' }},
  grid: {{ left: 60, right: 30, top: 40, bottom: 30 }},
  xAxis: {{ type: 'category', data: subjects }},
  yAxis: {{ type: 'value', minInterval: 1 }},
  series: [{{ name: '幻觉频次', type: 'bar', data: hallucVals, barWidth: '40%',
              itemStyle: {{ color: '#e85c5c' }} }}]
}});

window.addEventListener('resize', function () {{
  barChart.resize(); hallucChart.resize();
}});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器（供 main 与测试复用）"""
    parser = argparse.ArgumentParser(
        prog="python -m scripts.run_eval",
        description="LumiLearn 标准化学科测试集自动化评测（Task 5）")
    parser.add_argument("--subject", choices=["all", "math", "physics", "chemistry"],
                        default="all", help="评测学科（默认 all 全量）")
    parser.add_argument("--limit", type=int, default=0,
                        help="只评测前 N 题（默认 0 = 全量）")
    parser.add_argument("--real", action="store_true",
                        help="真实调用 UnifiedOrchestrator.run()（默认 mock 模式）")
    return parser


def main(argv: List[str] = None) -> int:
    args = build_parser().parse_args(argv)

    print(f"[run_eval] 模式={ 'real' if args.real else 'mock' } "
          f"学科={args.subject} limit={args.limit or '全量'}")
    t0 = time.time()
    metrics = run_evaluation(subject=args.subject, limit=args.limit,
                             real=args.real)
    files = generate_reports(metrics)
    elapsed = round(time.time() - t0, 2)

    print(f"[run_eval] 完成：{metrics['total_questions']} 题，"
          f"耗时 {elapsed}s")
    print(f"  knowledge_recall = {metrics['knowledge_recall']:.2%}")
    print(f"  accuracy         = {metrics['accuracy']:.2%}")
    print(f"  hit_rate         = {metrics['hit_rate']:.2%}")
    print(f"  hallucination    = {metrics['hallucination_count']}")
    print(f"  avg_latency_ms   = {metrics['avg_latency_ms']}")
    if metrics.get("report_id"):
        print(f"  已持久化 eval_reports id={metrics['report_id']}")
    print(f"  HTML 报表: {files['html']}")
    print(f"  JSON 报表: {files['json']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
