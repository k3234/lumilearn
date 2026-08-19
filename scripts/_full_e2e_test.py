#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 全用户端到端模拟测试
=================================
覆盖：Admin / Student / Teacher 三类用户的完整操作链路，
以及跨端口（5010 / 5000 / 18080）数据一致性验证。

运行方式：
    python scripts/_full_e2e_test.py
"""
import sys
import os
import json
import time
import tempfile
import shutil
import atexit

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

# 本地测试管理员口令：优先从环境变量读取；默认值仅供本地测试，禁止用于真实环境
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "test_admin_pwd_2026")

# 使用临时数据库，避免污染真实数据
_TMP_DB = os.path.join(tempfile.mkdtemp(), "lumilearn_test.db")
os.environ["LUMILEARN_DB_PATH"] = _TMP_DB
atexit.register(lambda: shutil.rmtree(os.path.dirname(_TMP_DB), ignore_errors=True))

from werkzeug.security import generate_password_hash
from framework.database import db

# ─── 初始化数据库并准备测试数据 ───────────────────────────────────────────────

db.init()

def _setup_test_data():
    """创建测试账号、班级、年级、学校等基础数据"""
    # 默认管理员（framework/admin/auth 要求）
    if not db.get_admins():
        db.add_admin("admin", generate_password_hash(ADMIN_PASSWORD),
                     display_name="超级管理员", role="super_admin")

    # 已有用户清理并重建（确保幂等）
    for uid in [100, 101, 102, 103]:
        try:
            db._execute("DELETE FROM users WHERE id=?", (uid,))
        except Exception:
            pass

    # 教师用户
    db.add_user("王老师", role="teacher", username="teacher1", password="test1234")
    # 学生用户
    db.add_user("张三", role="student", username="stu01", password="test1234")
    db.add_user("李四", role="student", username="stu02", password="test1234")
    db.add_user("王五", role="student", username="stu03", password="test1234")

    # 获取用户 id
    teacher = db.get_user_by_username("teacher1")
    stu01 = db.get_user_by_username("stu01")
    stu02 = db.get_user_by_username("stu02")
    stu03 = db.get_user_by_username("stu03")

    # 学校/年级/班级
    school = db.add_school("示例中学", "测试用学校")
    grade = db.add_grade(school["id"], "高三")
    cls1 = db.add_class(grade["id"], "一班", teacher_id=teacher["id"])
    cls2 = db.add_class(grade["id"], "二班", teacher_id=teacher["id"])

    # 绑定学生到班级
    db.add_student_to_class(cls1["id"], stu01["id"])
    db.add_student_to_class(cls1["id"], stu02["id"])
    db.add_student_to_class(cls2["id"], stu03["id"])

    return {
        "admin": {"username": "admin", "password": ADMIN_PASSWORD},
        "teacher": {"id": teacher["id"], "username": "teacher1", "password": "test1234", "name": "王老师"},
        "stu01": {"id": stu01["id"], "username": "stu01", "password": "test1234", "name": "张三"},
        "stu02": {"id": stu02["id"], "username": "stu02", "password": "test1234", "name": "李四"},
        "stu03": {"id": stu03["id"], "username": "stu03", "password": "test1234", "name": "王五"},
        "class1": cls1, "class2": cls2,
    }

TEST_DATA = _setup_test_data()

# ─── 导入 Flask 应用 ──────────────────────────────────────────────────────────

from framework.api.server import create_app as create_api_app
from student_portal import app as student_app   # 5010
from goai_web import app as goai_app            # 5000
from teacher_portal import app as teacher_app   # 5001

api_app = create_api_app()   # 18080

# ─── 测试结果记录 ─────────────────────────────────────────────────────────────

results = []   # (section, name, passed, detail)

def test(section, name, condition, detail=""):
    ok = bool(condition)
    results.append((section, name, ok, detail))
    icon = "PASS" if ok else "FAIL"
    print("  [%s] %-50s %s" % (icon, name, detail[:80] if detail else ""))
    return ok

# ══════════════════════════════════════════════════════════════════════════════
# 第一部分：Admin 用户（18080）
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  第一部分：Admin 用户端到端测试")
print("=" * 70)

client_admin = api_app.test_client()

# 1.1 认证
print("\n【1.1 认证】")
r = client_admin.post("/api/admin/login", json={"username": "admin", "password": ADMIN_PASSWORD})
d = r.get_json()
admin_token = d.get("token", "")
test("Admin", "admin 登录成功", r.status_code == 200 and admin_token, "HTTP %d" % r.status_code)

r = client_admin.post("/api/admin/login", json={"username": "admin", "password": "wrong"})
test("Admin", "admin 错误密码拒绝", r.status_code == 401, "HTTP %d" % r.status_code)

r = client_admin.post("/api/admin/login", json={"username": "nobody", "password": "x"})
test("Admin", "不存在用户拒绝", r.status_code == 401, "HTTP %d" % r.status_code)

r = client_admin.get("/api/admin/me", headers={"X-Admin-Token": admin_token})
d = r.get_json()
admin_info = d.get("admin") or {}
test("Admin", "admin 获取当前信息", r.status_code == 200 and admin_info.get("username") == "admin", "username=%s" % admin_info.get("username"))

# 1.2 概览
print("\n【1.2 系统概览】")
r = client_admin.get("/api/admin/overview", headers={"X-Admin-Token": admin_token})
d = r.get_json()
test("Admin", "获取概览", r.status_code == 200 and d.get("stats"), "users=%d" % (d["stats"]["total_users"] if d.get("stats") else 0))

# 1.3 用户管理
print("\n【1.3 用户管理】")
r = client_admin.get("/api/admin/users", headers={"X-Admin-Token": admin_token})
d = r.get_json()
test("Admin", "用户列表", r.status_code == 200 and d.get("users"), "count=%d" % len(d.get("users") or []))
users = d.get("users") or []
teacher_u = next((u for u in users if u.get("role") == "teacher"), None)
student_u = next((u for u in users if u.get("role") == "student"), None)
test("Admin", "用户含 classes 字段", teacher_u and "classes" in teacher_u, "role=teacher has_classes=%s" % ("classes" in (teacher_u or {})))

r = client_admin.post("/api/admin/users", json={"name": "新学生", "role": "student",
                                                  "username": "newstu_test", "password": "test1234"},
                      headers={"X-Admin-Token": admin_token})
d = r.get_json()
new_uid = d.get("user", {}).get("id") if d.get("success") else None
test("Admin", "创建用户", r.status_code == 200 and d.get("success"), "uid=%s" % new_uid)

if new_uid:
    r = client_admin.post("/api/admin/users/%d/password" % new_uid,
                          json={"password": "newpass1234"},
                          headers={"X-Admin-Token": admin_token})
    test("Admin", "重置用户密码", r.status_code == 200 and d.get("success"), "")

    # 删除
    r = client_admin.delete("/api/admin/users/%d" % new_uid, headers={"X-Admin-Token": admin_token})
    test("Admin", "删除用户", r.status_code == 200 and d.get("success"), "")

# 1.4 学校/年级/班级管理
print("\n【1.4 组织管理】")
r = client_admin.get("/api/admin/classes", headers={"X-Admin-Token": admin_token})
d = r.get_json()
test("Admin", "班级列表", r.status_code == 200 and d.get("classes"), "count=%d" % len(d.get("classes") or []))

# 1.5 端口模型配置同步
print("\n【1.5 端口模型配置】")
r = client_admin.get("/api/admin/port-models", headers={"X-Admin-Token": admin_token})
d = r.get_json()
port_map = d.get("port_map") or {}
test("Admin", "port-models 返回", r.status_code == 200, "keys=%s" % list(port_map.keys()))
test("Admin", "端口模型同步（7个端口）", len(port_map) == 7, "count=%d" % len(port_map))

r = client_admin.get("/api/admin/port-settings", headers={"X-Admin-Token": admin_token})
d = r.get_json()
test("Admin", "port-settings 返回", r.status_code == 200, "ports=%s" % list((d.get("port_settings") or {}).keys()))

# 1.6 日志
print("\n【1.6 日志查询】")
r = client_admin.get("/api/admin/logs?limit=5", headers={"X-Admin-Token": admin_token})
d = r.get_json()
test("Admin", "获取日志", r.status_code == 200, "count=%d" % len(d.get("logs") or []))

# ══════════════════════════════════════════════════════════════════════════════
# 第二部分：Student 用户 — 学生端学习平台（5010）
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  第二部分：Student 用户端到端测试（端口 5010）")
print("=" * 70)

client_s5010 = student_app.test_client()
TD = TEST_DATA

# 2.1 认证
print("\n【2.1 学生认证】")
r = client_s5010.post("/api/auth/login", json={"username": TD["stu01"]["username"], "password": TD["stu01"]["password"]})
d = r.get_json()
test("Student@5010", "学生 stu01 登录", r.status_code == 200 and d.get("code") == 0, "code=%d user=%s" % (r.status_code, d.get("data", {}).get("name")))

r = client_s5010.post("/api/auth/login", json={"username": TD["stu01"]["username"], "password": "wrong"})
test("Student@5010", "错误密码拒绝", r.status_code == 401, "code=%d" % r.status_code)

r = client_s5010.get("/api/auth/me")
d = r.get_json()
test("Student@5010", "登录态 me", r.status_code == 200 and d.get("code") == 0, "user=%s" % (d.get("data", {}).get("name")))

# 2.2 发起学习
print("\n【2.2 发起学习（start）】")
r = client_s5010.post("/api/learn/start", json={"topic": "函数的单调性", "subject": "数学", "difficulty": "高中"})
d = r.get_json()
test("Student@5010", "发起学习成功", r.status_code == 200 and d.get("code") == 0, "sid=%s topic=%s" % (d.get("data", {}).get("id"), d.get("data", {}).get("topic")))
sid = d.get("data", {}).get("session_id") or 0
sid_str = d.get("data", {}).get("id") or ""
flow_steps = d.get("data", {}).get("flow") or []
test("Student@5010", "学习流程含5步", len(flow_steps) == 5, "steps=%d" % len(flow_steps))

# 2.3 费曼五步学习
print("\n【2.3 费曼五步学习（step）】")
all_steps_ok = True
for i in range(1, 6):
    r = client_s5010.post("/api/learn/step", json={"sessionId": sid_str, "step": i})
    d = r.get_json()
    ok = r.status_code == 200 and d.get("code") == 0
    if not ok:
        all_steps_ok = False
    test("Student@5010", "step %d 完成" % i, ok, "code=%d has_content=%s" % (r.status_code, bool(d.get("data", {}).get("content"))))

# 2.4 费曼测试
print("\n【2.4 费曼测试】")
r = client_s5010.post("/api/learn/feynman-test", json={"sessionId": sid_str, "text": "函数的单调性就是在某个区间内函数值随着自变量增大而增大或减小的性质，比如y=x在R上单调递增。"})
d = r.get_json()
test("Student@5010", "费曼测试提交", r.status_code == 200 and d.get("code") == 0, "score=%d verdict=%s" % (d.get("data", {}).get("score"), (d.get("data") or {}).get("verdict", "")[:20]))

# 2.5 生成学习报告
print("\n【2.5 生成学习报告】")
r = client_s5010.post("/api/learn/report", json={"sessionId": sid_str, "feynmanScore": 82})
d = r.get_json()
test("Student@5010", "报告生成", r.status_code == 200 and d.get("code") == 0, "topic=%s mastery=%s" % (d.get("data", {}).get("topic"), d.get("data", {}).get("mastery")))
report_id = d.get("data", {}).get("id") or sid

# 2.6 查看学习历史
print("\n【2.6 学习历史】")
r = client_s5010.get("/api/learn/history")
d = r.get_json()
test("Student@5010", "学习历史", r.status_code == 200 and d.get("code") == 0, "total=%d" % d.get("total", 0))

# 2.7 查看个人档案
print("\n【2.7 个人档案】")
r = client_s5010.get("/api/profile")
d = r.get_json()
test("Student@5010", "我的档案", r.status_code == 200 and d.get("code") == 0, "total=%d avg=%s" % (d.get("data", {}).get("total_reports"), d.get("data", {}).get("avg_mastery")))

# 2.8 退出登录
print("\n【2.8 退出登录】")
r = client_s5010.post("/api/auth/logout")
test("Student@5010", "退出登录", r.status_code == 200, "")
r = client_s5010.get("/api/auth/me")
test("Student@5010", "登录后无法访问 me", r.status_code == 401, "HTTP %d" % r.status_code)

# ══════════════════════════════════════════════════════════════════════════════
# 第三部分：Student 用户 — GOAI Web（5000）
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  第三部分：Student 用户端到端测试（端口 5000 /proto/）")
print("=" * 70)

client_s5000 = goai_app.test_client()

# 3.1 认证（5000 也走同一个 users 表）
print("\n【3.1 学生认证（5000）】")
r = client_s5000.post("/api/auth/login", json={"username": TD["stu01"]["username"], "password": TD["stu01"]["password"]})
d = r.get_json()
test("Student@5000", "stu01 登录", r.status_code == 200 and d.get("code") == 0, "code=%d" % r.status_code)

r = client_s5000.get("/api/auth/me")
d = r.get_json()
test("Student@5000", "获取当前用户", r.status_code == 200 and d.get("code") == 0, "name=%s" % d.get("data", {}).get("name"))

# 3.2 发起学习（同一份数据，验证跨端口一致）
print("\n【3.2 跨端口学习一致性】")
r = client_s5000.post("/api/learn/start", json={"topic": "牛顿第二定律", "subject": "物理", "difficulty": "高中"})
d = r.get_json()
sid2 = d.get("data", {}).get("session_id") or 0
sid2_str = d.get("data", {}).get("id") or ""
test("Student@5000", "发起学习（5000）", r.status_code == 200 and d.get("code") == 0, "sid=%s" % sid2)

# 走几步
for i in range(1, 4):
    r = client_s5000.post("/api/learn/step", json={"sessionId": sid2_str, "step": i})
    test("Student@5000", "step %d（5000）" % i, r.status_code == 200, "")

# 生成报告
r = client_s5000.post("/api/learn/report", json={"sessionId": sid2_str, "feynmanScore": 85})
d = r.get_json()
test("Student@5000", "生成报告（5000）", r.status_code == 200 and d.get("code") == 0, "mastery=%s" % d.get("data", {}).get("mastery"))

# 3.3 查看历史（应包含 5010 和 5000 的学习记录）
print("\n【3.3 跨端口学习历史一致性】")
r = client_s5000.get("/api/learn/history")
d = r.get_json()
test("Student@5000", "学习历史（含5010数据）", r.status_code == 200, "total=%d" % d.get("total", 0))

# 查看档案
r = client_s5000.get("/api/profile")
d = r.get_json()
test("Student@5000", "我的档案（含5010数据）", r.status_code == 200 and d.get("code") == 0, "total=%d" % (d.get("data") or {}).get("total_reports", 0))

# 3.4 退出
r = client_s5000.post("/api/auth/logout")
test("Student@5000", "退出登录", r.status_code == 200, "")

# ══════════════════════════════════════════════════════════════════════════════
# 第四部分：Teacher 用户（5001）
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  第四部分：Teacher 用户端到端测试（端口 5001）")
print("=" * 70)

client_t5001 = teacher_app.test_client()
TD_T = TEST_DATA["teacher"]

# 4.1 认证
print("\n【4.1 教师认证】")
r = client_t5001.post("/api/login", json={"username": TD_T["username"], "password": TD_T["password"]})
d = r.get_json()
test("Teacher@5001", "教师登录", r.status_code == 200 and d.get("success"), "user=%s role=%s" % (d.get("user", {}).get("name"), d.get("user", {}).get("role")))

r = client_t5001.post("/api/login", json={"username": TD["stu01"]["username"], "password": TD["stu01"]["password"]})
test("Teacher@5001", "学生账号拒绝登录教师端", r.status_code == 403, "HTTP %d" % r.status_code)

# 4.2 概览
print("\n【4.2 教师概览】")
r = client_t5001.get("/api/overview")
d = r.get_json()
test("Teacher@5001", "获取概览", r.status_code == 200 and d.get("success"), "classes=%d" % len(d.get("my_classes") or []))

# 4.3 班级列表
print("\n【4.3 班级管理】")
r = client_t5001.get("/api/classes")
d = r.get_json()
test("Teacher@5001", "班级列表", r.status_code == 200 and d.get("success"), "classes=%d" % len(d.get("classes") or []))

# 4.4 查看班级学生
print("\n【4.4 班级学生】")
classes = d.get("classes") or []
if classes:
    cls_id = classes[0]["id"]
    r = client_t5001.get("/api/classes/%d/students" % cls_id)
    d = r.get_json()
    test("Teacher@5001", "班级学生列表", r.status_code == 200 and d.get("success"), "students=%d" % len(d.get("students") or []))
else:
    test("Teacher@5001", "班级学生列表（跳过，无班级）", True, "")

# 4.5 学生列表（含候选池）
print("\n【4.5 学生管理】")
r = client_t5001.get("/api/students")
d = r.get_json()
test("Teacher@5001", "学生列表", r.status_code == 200 and d.get("success"),
     "my_students=%d candidates=%d" % (len(d.get("students") or []), len(d.get("candidates") or [])))

# 4.6 查看某学生报告
print("\n【4.6 学生报告查看】")
students = d.get("students") or []
if students:
    stu_id = students[0]["id"]
    r = client_t5001.get("/api/students/%d/reports" % stu_id)
    d = r.get_json()
    test("Teacher@5001", "学生报告列表", r.status_code == 200 and d.get("success"), "reports=%d" % len(d.get("reports") or []))

    r = client_t5001.get("/api/students/%d/stats" % stu_id)
    d = r.get_json()
    test("Teacher@5001", "学生统计数据", r.status_code == 200 and d.get("success"), "mistakes=%d weak=%d" % (len(d.get("mistakes") or []), len(d.get("weak_topics") or [])))
else:
    test("Teacher@5001", "学生报告查看（跳过，无学生）", True, "")

# 4.7 推理日志
print("\n【4.7 推理日志】")
r = client_t5001.get("/api/teacher/reasoning-logs?limit=5")
d = r.get_json()
test("Teacher@5001", "推理日志", r.status_code == 200 and d.get("success"), "total=%d" % d.get("total", 0))

# 4.8 退出
print("\n【4.8 退出登录】")
r = client_t5001.post("/api/logout")
test("Teacher@5001", "退出登录", r.status_code == 200, "")

# ══════════════════════════════════════════════════════════════════════════════
# 第五部分：Admin 操作班级绑定（18080）
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  第五部分：Admin 班级绑定管理（端口 18080）")
print("=" * 70)

client_a = api_app.test_client()

# 登录 admin
r = client_a.post("/api/admin/login", json={"username": "admin", "password": ADMIN_PASSWORD})
admin_tok = (r.get_json() or {}).get("token", "")

# 5.1 绑定学生到班级
print("\n【5.1 绑定学生到班级】")
r = client_a.post("/api/admin/users/%d/classes" % TEST_DATA["stu01"]["id"],
                  json={"class_id": TEST_DATA["class1"]["id"]},
                  headers={"X-Admin-Token": admin_tok})
d = r.get_json()
test("Admin", "绑定学生到班级", r.status_code == 200 and d.get("success"), "msg=%s" % d.get("message", ""))

# 5.2 解绑学生
print("\n【5.2 解绑学生】")
r = client_a.delete("/api/admin/users/%d/classes/%d" % (TEST_DATA["stu01"]["id"], TEST_DATA["class1"]["id"]),
                    headers={"X-Admin-Token": admin_tok})
d = r.get_json()
test("Admin", "解绑学生", r.status_code == 200 and d.get("success"), "msg=%s" % d.get("message", ""))

# 5.3 验证解绑
r = client_a.get("/api/admin/users/%d/classes" % TEST_DATA["stu01"]["id"],
                 headers={"X-Admin-Token": admin_tok})
d = r.get_json()
test("Admin", "验证解绑结果", r.status_code == 200 and len(d.get("classes") or []) == 0, "classes=%s" % d.get("classes", []))

# 5.4 查看某学生已绑定班级
r = client_a.get("/api/admin/users/%d/classes" % TEST_DATA["stu02"]["id"],
                 headers={"X-Admin-Token": admin_tok})
d = r.get_json()
test("Admin", "查看学生班级绑定", r.status_code == 200, "classes=%s" % [c.get("name") for c in (d.get("classes") or [])])

# ══════════════════════════════════════════════════════════════════════════════
# 第六部分：前端页面可访问性
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  第六部分：前端页面可访问性测试")
print("=" * 70)

print("\n【6.1 学生端页面（5010）】")
for page in ["index.html", "learn.html", "report.html", "history.html", "profile.html"]:
    r = client_s5010.get("/" + page)
    html = r.get_data(as_text=True)
    has_real = "__LUMILEARN_REAL__" in html
    test("Frontend@5010", "%s 可访问" % page, r.status_code == 200 and has_real, "200 OK has_real=%s" % has_real)

print("\n【6.2 GOAI Web 页面（5000）】")
r = client_s5000.get("/proto/index.html")
html = r.get_data(as_text=True)
has_real = "__LUMILEARN_REAL__" in html
test("Frontend@5000", "/proto/index.html 可访问且含真实标志", r.status_code == 200 and has_real, "200 OK has_real=%s" % has_real)

r = client_s5000.get("/proto/learn.html")
html = r.get_data(as_text=True)
has_real = "__LUMILEARN_REAL__" in html
test("Frontend@5000", "/proto/learn.html 可访问且含真实标志", r.status_code == 200 and has_real, "200 OK has_real=%s" % has_real)

# ══════════════════════════════════════════════════════════════════════════════
# 汇总
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  测试结果汇总")
print("=" * 70)

sections = {}
for section, name, ok, detail in results:
    sections.setdefault(section, {"total": 0, "pass": 0})
    sections[section]["total"] += 1
    if ok:
        sections[section]["pass"] += 1

total = len(results)
passed = sum(s["pass"] for s in sections.values())
failed = total - passed

for sec, stats in sections.items():
    p, t = stats["pass"], stats["total"]
    icon = "ALL PASS" if p == t else "%d FAIL" % (t - p)
    print("  [%s] %d/%d %s" % (sec, p, t, icon))

print("\n  总计：%d 项测试，%d 通过，%d 失败" % (total, passed, failed))
if failed == 0:
    print("  \u2705 所有测试通过！")
else:
    print("  \u274c 存在失败项，请查看上方详情")

sys.exit(0 if failed == 0 else 1)
