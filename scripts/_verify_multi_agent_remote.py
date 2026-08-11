# -*- coding: utf-8 -*-
"""远程端到端验证：登录 + multi-agent 全流程（真实模型）
服务器地址从环境变量读取（REMOTE_BASE），不硬编码。
"""
import requests
import json
import os

BASE = os.environ.get("REMOTE_BASE", "http://localhost:5000").rstrip("/")
ADMIN_BASE = os.environ.get("ADMIN_BASE", "http://localhost:18080").rstrip("/")
ADMIN_CREDS = {"username": os.environ.get("ADMIN_USER", "admin"),
               "password": os.environ.get("ADMIN_PASSWORD", "admin123")}
s = requests.Session()

# 1. 登录（先尝试常用账号）
users = [("demo", "123456"), ("123", "test123"), ("stu1", "123456")]
logged = False
for u, p in users:
    r = s.post(f"{BASE}/api/login", json={"username": u, "password": p}, timeout=10)
    d = r.json()
    if d.get("success"):
        print(f"登录成功: {u} -> {d['user']['name']} ({d['user']['role']})")
        logged = True
        break
    else:
        print(f"登录失败 {u}: {d.get('error')}")
if not logged:
    print("!!! 无可用账号，尝试 GET /api/me 确认未登录行为")
    r = s.get(f"{BASE}/api/me", timeout=10)
    print("未登录 GET /api/me:", r.status_code, r.json())

# 2. multi-agent 完整流程
print("\n=== /api/multi-agent 完整流程（含学生解释）===")
r = s.post(f"{BASE}/api/multi-agent", json={
    "topic": "牛顿第二定律",
    "subject": "物理",
    "difficulty": "高中",
    "student_explanation": "牛顿第二定律就是物体所受合外力等于质量乘以加速度，力越大加速度越大。",
}, timeout=300)
print("HTTP:", r.status_code)
try:
    d = r.json()
    if d.get("success"):
        data = d["data"]
        print("topic:", data["topic"])
        print("teaching steps:", len(data["teaching"]["steps"]))
        if data["teaching"]["steps"]:
            print("  step1:", data["teaching"]["steps"][0]["step_name"], "-", data["teaching"]["steps"][0]["content"][:60])
        print("assessment score:", data["assessment"]["score"])
        print("assessment dims:", list(data["assessment"]["dimensions"].keys()))
        print("coaching level:", data["coaching"]["mastery_level"])
        print("coaching suggestions:", len(data["coaching"]["suggestions"]))
        print("next_topics:", len(data["coaching"]["next_topics"]))
        print("agent_trace:", {k: v["status"] for k, v in data["agent_trace"].items()})
        print("total_time:", data["total_time"])
    else:
        print("响应:", json.dumps(d, ensure_ascii=False)[:500])
except Exception as e:
    print("解析失败:", e, r.text[:300])

# 3. multi-agent 无学生解释（评分跳过）
print("\n=== /api/multi-agent 无学生解释（评分应跳过）===")
r = s.post(f"{BASE}/api/multi-agent", json={"topic": "化学平衡移动", "subject": "化学"}, timeout=300)
print("HTTP:", r.status_code)
try:
    d = r.json()
    if d.get("success"):
        data = d["data"]
        print("score_status:", data["agent_trace"]["score"]["status"])
        print("teaching steps:", len(data["teaching"]["steps"]))
        print("suggestions:", len(data["coaching"]["suggestions"]))
    else:
        print("响应:", json.dumps(d, ensure_ascii=False)[:300])
except Exception as e:
    print("解析失败:", e)

# 4. 页面检查
print("\n=== 页面检查 ===")
r = requests.get(f"{BASE}/", timeout=10)
html = r.text
print("GET / 200:", r.status_code == 200, "含'多Agent':", "多Agent" in html, "len:", len(html))
r = requests.get(f"{BASE}/learn", timeout=10)
html = r.text
print("GET /learn 200:", r.status_code == 200, "含startLearning:", "startLearning" in html, "len:", len(html))

# 5. 报告落库验证（用 admin 查）
print("\n=== 报告落库（admin 视角）===")
try:
    r = requests.post(f"{ADMIN_BASE}/api/admin/login", json=ADMIN_CREDS, timeout=10)
    token = r.json().get("token", "")
    r = requests.get(f"{ADMIN_BASE}/api/admin/users",
                     headers={"X-Admin-Token": token}, timeout=10)
    users = r.json().get("users", [])
    for u in users:
        if u.get("role") == "student":
            print(f"  学生: {u['name']} (id={u['id']})")
except Exception as e:
    print("  admin 查询跳过:", e)
