#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 2 冒烟测试：goai_multi_agent + goai_web 重构验证
核心设备压力约束：mock 掉模型调用（call_ollama），不触网。
"""
import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

_TMP_DB = os.path.join(tempfile.mkdtemp(), "day2_smoke.db")
os.environ["LUMILEARN_DB_PATH"] = _TMP_DB

from unittest import mock

results = []
def test(name, cond, detail=""):
    ok = bool(cond)
    results.append((name, ok, detail))
    print("  [%s] %-55s %s" % ("PASS" if ok else "FAIL", name, detail))
    return ok

# 1. 模块导入
print("\n【1. 模块导入】")
import goai_multi_agent
from goai_multi_agent import FeynmanTeacher, ScoreAgent, CoachAgent, MultiAgentOrchestrator, run_multi_agent
test("goai_multi_agent import OK", True)

# 2. 单元测试各 Agent（mock 模型）
print("\n【2. Agent 单元测试（mock 模型）】")

# CoachAgent 纯逻辑，不触网
c = CoachAgent()
r = c.run({"user_id": 1, "score": 60, "topic": "函数", "weak_topics": ["单调性"]})
test("CoachAgent 建议生成", r["success"] and r["mastery_level"] == "一般" and len(r["suggestions"]) >= 1, "level=%s next=%d" % (r["mastery_level"], len(r["next_topics"])))

# FeynmanTeacher（mock call_ollama → 空 → 模板兜底）
with mock.patch("framework.engines.feynman_engine.call_ollama", return_value=""):
    ft = FeynmanTeacher(model_name="mock-model")
    r = ft.run({"topic": "勾股定理", "difficulty": "初中"})
    test("FeynmanTeacher 五步教学", r["success"] and len(r["steps"]) == 5, "mode=%s steps=%d" % (r.get("mode"), len(r.get("steps", []))))
    test("FeynmanTeacher 交互模式", True, "")
    r2 = ft.run({"topic": "勾股定理", "difficulty": "初中", "dialogue": [{"role": "assistant", "content": "第一步引导"}, {"role": "user", "content": "我理解了"}]})
    test("FeynmanTeacher 交互引导", r2["success"] and r2.get("mode") == "interactive", "mode=%s step=%s" % (r2.get("mode"), r2.get("step", {}).get("step_name")))
    test("FeynmanTeacher 缺 topic 失败", not ft.run({"difficulty": "初中"})["success"], "")

# ScoreAgent（mock）
with mock.patch("framework.engines.feynman_engine.call_ollama", return_value=""):
    sa = ScoreAgent(model_name="mock-model")
    r = sa.run({"topic": "勾股定理", "student_explanation": "直角三角形两条直角边的平方和等于斜边的平方", "user_id": 1})
    test("ScoreAgent 五维评分", r["success"] and 0 <= r["score"] <= 100, "score=%s dims=%s" % (r.get("score"), len(r.get("dimensions", {}))))
    r = sa.run({"topic": "勾股定理"})
    test("ScoreAgent 缺解释失败", not r["success"], "err=%s" % r.get("error", "")[:20])

# 3. MultiAgentOrchestrator 串行编排
print("\n【3. 多 Agent 串行编排】")
with mock.patch("framework.engines.feynman_engine.call_ollama", return_value=""):
    orch = MultiAgentOrchestrator()
    report = orch.run({
        "topic": "函数的单调性", "subject": "数学", "difficulty": "高中",
        "user_id": 1,
        "student_explanation": "函数的单调性就是自变量增大时函数值跟着增大或减小的性质",
    })
    test("编排器完整流程", report["topic"] == "函数的单调性", "")
    test("教学阶段 5 步", len(report["teaching"]["steps"]) == 5, "steps=%d" % len(report["teaching"]["steps"]))
    test("评分阶段有分", 0 <= report["assessment"]["score"] <= 100, "score=%s" % report["assessment"]["score"])
    test("建议阶段有内容", len(report["coaching"]["suggestions"]) >= 1, "suggestions=%d" % len(report["coaching"]["suggestions"]))
    test("Agent 状态追踪", all(report["agent_trace"][k]["status"] in ("ok", "skipped", "failed") for k in ("feynman", "score", "coach")), "trace=%s" % {k: v["status"] for k, v in report["agent_trace"].items()})
    test("总耗时记录", report["total_time"] > 0, "time=%s" % report["total_time"])

# 4. goai_web 重构验证
print("\n【4. goai_web 重构验证】")
with mock.patch("framework.engines.feynman_engine.call_ollama", return_value=""):
    import goai_web
    from goai_web import app as web_app
    from framework.database import db
    db.init()
    # 建测试用户
    from werkzeug.security import generate_password_hash
    if not db.get_user_by_username("smoke_stu"):
        db.add_user("冒烟学生", role="student", username="smoke_stu", password="test1234")

    c = web_app.test_client()

    # 页面可访问
    r = c.get("/")
    test("仪表盘首页 200", r.status_code == 200 and "服务仪表盘" in r.get_data(as_text=True), "len=%d" % len(r.get_data()))
    r = c.get("/learn")
    html = r.get_data(as_text=True)
    test("学习页 200", r.status_code == 200 and "LumiLearn AI 教官" in html, "len=%d" % len(html))
    test("学习页含完整 JS 逻辑", "startLearning" in html and "checkLogin" in html and "renderReport" in html, "")

    # multi-agent 未登录 → 401
    r = c.post("/api/multi-agent", json={"topic": "函数的单调性"})
    test("multi-agent 未登录 401", r.status_code == 401, "HTTP %d" % r.status_code)

    # 登录
    r = c.post("/api/login", json={"username": "smoke_stu", "password": "test1234"})
    test("登录成功", r.status_code == 200 and r.get_json().get("success"), "")

    # multi-agent 全流程
    r = c.post("/api/multi-agent", json={
        "topic": "牛顿第二定律", "subject": "物理", "difficulty": "高中",
        "student_explanation": "牛顿第二定律就是力等于质量乘以加速度",
    })
    d = r.get_json()
    test("multi-agent 路由 200", r.status_code == 200 and d.get("success"), "code=%d" % r.status_code)
    data = d.get("data", {})
    test("multi-agent 返回教学步骤", len(data.get("teaching", {}).get("steps", [])) == 5, "")
    test("multi-agent 返回评分", 0 <= data.get("assessment", {}).get("score", -1) <= 100, "score=%s" % data.get("assessment", {}).get("score"))
    test("multi-agent 返回建议", len(data.get("coaching", {}).get("suggestions", [])) >= 1, "")
    test("multi-agent 无解释时评分跳过", True, "")

    r = c.post("/api/multi-agent", json={"topic": "化学平衡移动"})
    d = r.get_json()
    data = d.get("data", {})
    test("multi-agent 无解释评分跳过", data.get("agent_trace", {}).get("score", {}).get("status") == "skipped",
         "score_status=%s" % data.get("agent_trace", {}).get("score", {}).get("status"))

    # 报告落库
    reports = db.get_learning_reports(limit=10)
    test("multi-agent 报告落库", len(reports) >= 1, "reports=%d" % len(reports))

# 汇总
print("\n" + "=" * 60)
passed = sum(1 for _, ok, _ in results if ok)
failed = len(results) - passed
print("  总计: %d 项, 通过 %d, 失败 %d" % (len(results), passed, failed))
for name, ok, detail in results:
    if not ok:
        print("  FAILED: %s — %s" % (name, detail))
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
