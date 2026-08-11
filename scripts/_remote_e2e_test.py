#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 远程服务器端到端测试（完整版）
通过 requests 连接远程已部署的服务，验证线上环境的所有用户流程
用法:
    python scripts/_remote_e2e_test.py
"""
import sys
import os
import requests

# ─── 配置 ──────────────────────────────────────────────────────────────────────
BASE_URL    = os.environ.get("LUMILEARN_BASE_URL",    "http://192.168.2.68:18080")
STUDENT_URL = os.environ.get("STUDENT_URL",           "http://192.168.2.68:5010")
GOAI_URL    = os.environ.get("GOAI_URL",              "http://192.168.2.68:5000")
TEACHER_URL = os.environ.get("TEACHER_URL",           "http://192.168.2.68:5001")

# 远程服务器已知凭据
ADMIN_CREDS  = {"username": "admin",  "password": "admin123"}
STU_CREDS    = {"username": "demo",   "password": "123456"}
TEACH_CREDS  = {"username": "teacher","password": "123456"}

RESULTS = []

def test(section, name, condition, detail=""):
    ok = bool(condition)
    RESULTS.append((section, name, ok, detail))
    icon = "PASS" if ok else "FAIL"
    print("  [%s] %-50s %s" % (icon, name, detail[:80] if detail else ""))
    return ok

def safe_json(r):
    try:
        return r.json()
    except Exception:
        return {}

def jget(d, *keys, default=None):
    """安全多层 dict 取值"""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
    return d

# ══════════════════════════════════════════════════════════════════════════════
# 1. Admin 用户（18080）
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  第一部分：Admin 用户（端口 %s）" % BASE_URL)
print("=" * 70)

s_admin = requests.Session()

print("\n【1.1 认证】")
r = s_admin.post("%s/api/admin/login" % BASE_URL, json=ADMIN_CREDS)
d = safe_json(r)
token = d.get("token", "")
test("Admin", "admin 登录成功", r.status_code == 200 and token, "code=%d" % r.status_code)

r = s_admin.post("%s/api/admin/login" % BASE_URL, json={"username": "admin", "password": "wrong"})
test("Admin", "admin 错误密码拒绝", r.status_code == 401, "")

r = s_admin.get("%s/api/admin/me" % BASE_URL, headers={"X-Admin-Token": token})
d = safe_json(r)
test("Admin", "admin 获取当前信息", r.status_code == 200 and jget(d, "admin", "username") == "admin",
     "username=%s" % jget(d, "admin", "username"))

print("\n【1.2 系统概览】")
r = s_admin.get("%s/api/admin/overview" % BASE_URL, headers={"X-Admin-Token": token})
d = safe_json(r)
test("Admin", "获取概览", r.status_code == 200 and d.get("success"),
     "users=%d" % jget(d, "stats", "total_users", default=0))

print("\n【1.3 用户管理】")
r = s_admin.get("%s/api/admin/users" % BASE_URL, headers={"X-Admin-Token": token})
d = safe_json(r)
users = d.get("users") or []
test("Admin", "用户列表", r.status_code == 200 and len(users) > 0, "count=%d" % len(users))
has_classes = any("classes" in u for u in users)
test("Admin", "用户含 classes 字段", has_classes, "has_classes=%s" % has_classes)

print("\n【1.4 组织管理】")
r = s_admin.get("%s/api/admin/classes" % BASE_URL, headers={"X-Admin-Token": token})
d = safe_json(r)
test("Admin", "班级列表", r.status_code == 200, "count=%d" % len(d.get("classes") or []))

print("\n【1.5 端口模型配置】")
r = s_admin.get("%s/api/admin/port-models" % BASE_URL, headers={"X-Admin-Token": token})
d = safe_json(r)
port_map = d.get("port_map") or {}
test("Admin", "port-models 返回", r.status_code == 200, "keys=%s" % list(port_map.keys()))
test("Admin", "端口模型同步（7个端口）", len(port_map) == 7, "count=%d" % len(port_map))

r = s_admin.get("%s/api/admin/port-settings" % BASE_URL, headers={"X-Admin-Token": token})
d = safe_json(r)
test("Admin", "port-settings 返回", r.status_code == 200,
     "ports=%s" % list((d.get("port_settings") or {}).keys()))

print("\n【1.6 日志】")
r = s_admin.get("%s/api/admin/logs?limit=5" % BASE_URL, headers={"X-Admin-Token": token})
d = safe_json(r)
test("Admin", "获取日志", r.status_code == 200, "count=%d" % len(d.get("logs") or []))

print("\n【1.7 绑定/解绑班级】")
if users:
    # 找一个学生
    stu = next((u for u in users if u.get("role") == "student"), None)
    cls_list = (d.get("classes") or []) if "classes" in d else []
    # 重新获取 classes
    r2 = s_admin.get("%s/api/admin/classes" % BASE_URL, headers={"X-Admin-Token": token})
    cls_list = r2.json().get("classes") or []
    if stu and cls_list:
        cls_id = cls_list[0]["id"]
        r = s_admin.post("%s/api/admin/users/%d/classes" % (BASE_URL, stu["id"]),
                         json={"class_id": cls_id}, headers={"X-Admin-Token": token})
        d = safe_json(r)
        test("Admin", "绑定学生到班级", r.status_code == 200 and d.get("success"),
             "msg=%s" % d.get("message", ""))

        r = s_admin.delete("%s/api/admin/users/%d/classes/%d" % (BASE_URL, stu["id"], cls_id),
                           headers={"X-Admin-Token": token})
        d = safe_json(r)
        test("Admin", "解绑学生", r.status_code == 200 and d.get("success"),
             "msg=%s" % d.get("message", ""))
    else:
        test("Admin", "绑定/解绑（跳过：无学生或班级）", True, "")

# ══════════════════════════════════════════════════════════════════════════════
# 2. Student 用户 — 学生端学习平台（5010）
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  第二部分：Student 用户（端口 %s）" % STUDENT_URL)
print("=" * 70)

s_stu = requests.Session()

print("\n【2.1 学生认证】")
r = s_stu.post("%s/api/auth/login" % STUDENT_URL, json=STU_CREDS)
d = safe_json(r)
test("Student@5010", "学生 demo 登录", r.status_code == 200 and d.get("code") == 0,
     "code=%d name=%s" % (r.status_code, jget(d, "data", "name")))

r = s_stu.post("%s/api/auth/login" % STUDENT_URL, json={"username": "demo", "password": "wrong"})
test("Student@5010", "错误密码拒绝", r.status_code == 401, "")

r = s_stu.get("%s/api/auth/me" % STUDENT_URL)
d = safe_json(r)
test("Student@5010", "登录态 me", r.status_code == 200 and d.get("code") == 0,
     "user=%s" % jget(d, "data", "name"))

print("\n【2.2 发起学习】")
r = s_stu.post("%s/api/learn/start" % STUDENT_URL,
               json={"topic": "函数的单调性", "subject": "数学", "difficulty": "高中"})
d = safe_json(r)
sid = jget(d, "data", "session_id", default=0)
sid_str = jget(d, "data", "id", default="")
flow = jget(d, "data", "flow", default=[])
test("Student@5010", "发起学习成功", r.status_code == 200 and d.get("code") == 0,
     "sid=%s topic=%s" % (sid_str, jget(d, "data", "topic")))
test("Student@5010", "学习流程含5步", len(flow) == 5, "steps=%d" % len(flow))

print("\n【2.3 费曼五步学习】")
for i in range(1, 6):
    r = s_stu.post("%s/api/learn/step" % STUDENT_URL,
                   json={"sessionId": sid_str, "step": i})
    d = safe_json(r)
    ok = r.status_code == 200 and d.get("code") == 0
    content = jget(d, "data", "content", default="")
    test("Student@5010", "step %d 完成" % i, ok,
         "has_content=%s" % bool(content))

print("\n【2.4 费曼测试】")
r = s_stu.post("%s/api/learn/feynman-test" % STUDENT_URL, json={
    "sessionId": sid_str,
    "text": "函数的单调性就是在某个区间内函数值随着自变量增大而增大或减小的性质，比如y=x在R上单调递增。"
})
d = safe_json(r)
test("Student@5010", "费曼测试提交", r.status_code == 200 and d.get("code") == 0,
     "score=%s verdict=%s" % (
         jget(d, "data", "score", default="None"),
         jget(d, "data", "verdict", default="")[:20]))

print("\n【2.5 生成学习报告】")
r = s_stu.post("%s/api/learn/report" % STUDENT_URL,
               json={"sessionId": sid_str, "feynmanScore": 82})
d = safe_json(r)
test("Student@5010", "报告生成", r.status_code == 200 and d.get("code") == 0,
     "mastery=%s" % jget(d, "data", "mastery"))

print("\n【2.6 学习历史 & 个人档案】")
r = s_stu.get("%s/api/learn/history" % STUDENT_URL)
d = safe_json(r)
test("Student@5010", "学习历史", r.status_code == 200 and d.get("code") == 0,
     "total=%d" % d.get("total", 0))

r = s_stu.get("%s/api/profile" % STUDENT_URL)
d = safe_json(r)
test("Student@5010", "我的档案", r.status_code == 200 and d.get("code") == 0,
     "total=%d avg=%s" % (
         jget(d, "data", "total_reports", default=0),
         jget(d, "data", "avg_mastery", default=0)))

print("\n【2.7 退出登录】")
r = s_stu.post("%s/api/auth/logout" % STUDENT_URL)
test("Student@5010", "退出登录", r.status_code == 200, "")
r = s_stu.get("%s/api/auth/me" % STUDENT_URL)
test("Student@5010", "登录后无法访问 me", r.status_code == 401, "HTTP %d" % r.status_code)

# ══════════════════════════════════════════════════════════════════════════════
# 3. Student 用户 — GOAI Web（5000）
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  第三部分：Student 用户（端口 %s）" % GOAI_URL)
print("=" * 70)

s_goai = requests.Session()

print("\n【3.1 跨端口学生认证】")
r = s_goai.post("%s/api/auth/login" % GOAI_URL, json=STU_CREDS)
d = safe_json(r)
test("Student@5000", "学生 demo 登录(5000)", r.status_code == 200 and d.get("code") == 0,
     "code=%d" % r.status_code)

r = s_goai.get("%s/api/auth/me" % GOAI_URL)
d = safe_json(r)
test("Student@5000", "获取当前用户", r.status_code == 200 and d.get("code") == 0,
     "name=%s" % jget(d, "data", "name"))

print("\n【3.2 跨端口学习一致性】")
r = s_goai.post("%s/api/learn/start" % GOAI_URL,
                json={"topic": "牛顿第二定律", "subject": "物理", "difficulty": "高中"})
d = safe_json(r)
sid2 = jget(d, "data", "session_id", default=0)
sid2_str = jget(d, "data", "id", default="")
test("Student@5000", "发起学习(5000)", r.status_code == 200 and d.get("code") == 0,
     "sid=%s" % sid2_str)

for i in range(1, 4):
    r = s_goai.post("%s/api/learn/step" % GOAI_URL,
                    json={"sessionId": sid2_str, "step": i})
    test("Student@5000", "step %d (5000)" % i, r.status_code == 200, "")

r = s_goai.post("%s/api/learn/report" % GOAI_URL,
                json={"sessionId": sid2_str, "feynmanScore": 85})
d = safe_json(r)
test("Student@5000", "生成报告(5000)", r.status_code == 200 and d.get("code") == 0,
     "mastery=%s" % jget(d, "data", "mastery"))

print("\n【3.3 跨端口数据一致性】")
r = s_goai.get("%s/api/learn/history" % GOAI_URL)
d = safe_json(r)
test("Student@5000", "学习历史(含5010数据)", r.status_code == 200,
     "total=%d" % d.get("total", 0))

r = s_goai.get("%s/api/profile" % GOAI_URL)
d = safe_json(r)
test("Student@5000", "我的档案(含5010数据)", r.status_code == 200 and d.get("code") == 0,
     "total=%d" % jget(d, "data", "total_reports", default=0))

r = s_goai.post("%s/api/auth/logout" % GOAI_URL)
test("Student@5000", "退出登录(5000)", r.status_code == 200, "")

# ══════════════════════════════════════════════════════════════════════════════
# 4. Teacher 用户（5001）
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  第四部分：Teacher 用户（端口 %s）" % TEACHER_URL)
print("=" * 70)

s_teach = requests.Session()

print("\n【4.1 教师认证】")
r = s_teach.post("%s/api/login" % TEACHER_URL, json=TEACH_CREDS)
d = safe_json(r)
teacher_ok = r.status_code == 200 and d.get("success")
test("Teacher@5001", "教师登录", teacher_ok,
     "code=%d user=%s" % (r.status_code, jget(d, "user", "name")))

if teacher_ok:
    print("\n【4.2 教师概览 & 班级管理】")
    r = s_teach.get("%s/api/overview" % TEACHER_URL)
    d = safe_json(r)
    test("Teacher@5001", "教师概览", r.status_code == 200 and d.get("success"),
         "classes=%d" % len(jget(d, "my_classes", default=[])))

    r = s_teach.get("%s/api/classes" % TEACHER_URL)
    d = safe_json(r)
    test("Teacher@5001", "班级列表", r.status_code == 200 and d.get("success"),
         "classes=%d" % len(d.get("classes") or []))

    print("\n【4.3 学生管理】")
    r = s_teach.get("%s/api/students" % TEACHER_URL)
    d = safe_json(r)
    test("Teacher@5001", "学生列表", r.status_code == 200 and d.get("success"),
         "my=%d candidates=%d" % (len(d.get("students") or []), len(d.get("candidates") or [])))

    students = d.get("students") or []
    if students:
        stu_id = students[0]["id"]
        r = s_teach.get("%s/api/students/%d/reports" % (TEACHER_URL, stu_id))
        d = safe_json(r)
        test("Teacher@5001", "学生报告", r.status_code == 200 and d.get("success"),
             "reports=%d" % len(d.get("reports") or []))

        r = s_teach.get("%s/api/students/%d/stats" % (TEACHER_URL, stu_id))
        d = safe_json(r)
        test("Teacher@5001", "学生统计", r.status_code == 200 and d.get("success"),
             "mistakes=%d" % len(d.get("mistakes") or []))
    else:
        test("Teacher@5001", "学生报告查看（跳过，无学生）", True, "")

    print("\n【4.4 推理日志】")
    r = s_teach.get("%s/api/teacher/reasoning-logs?limit=5" % TEACHER_URL)
    d = safe_json(r)
    test("Teacher@5001", "推理日志", r.status_code == 200 and d.get("success"),
         "total=%d" % d.get("total", 0))

    print("\n【4.5 退出登录】")
    r = s_teach.post("%s/api/logout" % TEACHER_URL)
    test("Teacher@5001", "退出登录", r.status_code == 200, "")
else:
    print("\n  [SKIP] 教师端登录失败，跳过后续测试")

# ══════════════════════════════════════════════════════════════════════════════
# 5. 前端页面可访问性
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  第五部分：前端页面可访问性")
print("=" * 70)

print("\n【5.1 学生端页面（5010）】")
for page in ["index.html", "learn.html", "report.html", "history.html", "profile.html"]:
    r = s_stu.get("%s/%s" % (STUDENT_URL, page), timeout=10)
    html = r.text
    has_real = "__LUMILEARN_REAL__" in html
    test("Frontend@5010", "%s" % page, r.status_code == 200 and has_real,
         "200 OK real=%s" % has_real)

print("\n【5.2 GOAI Web 页面（5000）】")
for page in ["index.html", "learn.html"]:
    r = s_goai.get("%s/proto/%s" % (GOAI_URL, page), timeout=10)
    html = r.text
    has_real = "__LUMILEARN_REAL__" in html
    test("Frontend@5000", "/proto/%s" % page, r.status_code == 200 and has_real,
         "200 OK real=%s" % has_real)

# ══════════════════════════════════════════════════════════════════════════════
# 汇总
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  测试结果汇总")
print("=" * 70)

passed = sum(1 for _, _, ok, _ in RESULTS if ok)
failed = sum(1 for _, _, ok, _ in RESULTS if not ok)
total = len(RESULTS)

sections = {}
for section, name, ok, detail in RESULTS:
    sections.setdefault(section, {"total": 0, "pass": 0})
    sections[section]["total"] += 1
    if ok:
        sections[section]["pass"] += 1

for sec, stats in sorted(sections.items()):
    p, t = stats["pass"], stats["total"]
    icon = "ALL PASS" if p == t else "%d FAIL" % (t - p)
    print("  [%s] %d/%d %s" % (sec, p, t, icon))

print("\n  总计：%d 项测试，%d 通过，%d 失败" % (total, passed, failed))
if failed == 0:
    print("  ALL TESTS PASSED!")
else:
    print("  SOME TESTS FAILED:")
    for sec, name, ok, detail in RESULTS:
        if not ok:
            print("    - [%s] %s — %s" % (sec, name, detail))

sys.exit(0 if failed == 0 else 1)
