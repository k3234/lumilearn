#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查远程服务器的用户和测试登录（地址从环境变量读取，默认占位符）"""
import os
import requests
import sys

# 远程服务器地址（通过环境变量配置，默认占位符，不包含真实内网 IP）
HOST = os.environ.get("REMOTE_HOST", "192.168.2.xx")
ADMIN_URL = f"http://{HOST}:18080"
STU_URL = f"http://{HOST}:5010"
TEACHER_URL = f"http://{HOST}:5001"
GOAI_URL = f"http://{HOST}:5000"

# 检查远程服务器用户
print("=== 检查远程服务器用户 ===")
try:
    r = requests.get(f"{ADMIN_URL}/api/admin/users",
                     headers={"X-Admin-Token": ""}, timeout=5)
    print("未认证用户列表: HTTP %d" % r.status_code)
except Exception as e:
    print("连接错误: %s" % e)

# 先登录 admin
print("\n=== Admin 登录 ===")
r = requests.post(f"{ADMIN_URL}/api/admin/login",
                  json={"username": "admin", "password": "admin123"}, timeout=5)
d = r.json()
token = d.get("token", "")
print("Admin token: %s (HTTP %d)" % (token[:20] if token else "None", r.status_code))

# 获取用户列表
print("\n=== 用户列表 ===")
r = requests.get(f"{ADMIN_URL}/api/admin/users",
                 headers={"X-Admin-Token": token}, timeout=5)
users = r.json().get("users", [])
for u in users:
    uname = u.get("username") or u.get("name") or "-"
    print("  id=%d name=%s role=%s username=%s has_pw=%s" % (
        u["id"], u["name"], u["role"], uname, u.get("has_password", False)))

# 检查学生端登录
print("\n=== 学生端登录测试 ===")
for u in users:
    if u.get("role") == "student":
        uname = u.get("username") or u.get("name")
        for pw in ["test1234", "123456", "password", "student", "demo", "12345678"]:
            r = requests.post(f"{STU_URL}/api/auth/login",
                              json={"username": uname, "password": pw}, timeout=5)
            d = r.json()
            if d.get("code") == 0:
                print("  找到学生登录成功: username=%s password=%s -> name=%s" % (uname, pw, d.get("data", {}).get("name")))
                # 测试学习流程
                r2 = requests.post(f"{STU_URL}/api/learn/start",
                                   json={"topic": "函数的单调性", "subject": "数学", "difficulty": "高中"},
                                   timeout=10)
                d2 = r2.json()
                print("  start: code=%d sid=%s" % (d2.get("code"), d2.get("data", {}).get("id")))
                if d2.get("code") == 0:
                    sid_str = d2["data"].get("id", "")
                    # 测试 step
                    r3 = requests.post(f"{STU_URL}/api/learn/step",
                                       json={"sessionId": sid_str, "step": 1}, timeout=30)
                    d3 = r3.json()
                    print("  step1: code=%d has_content=%s" % (d3.get("code"), bool((d3.get("data") or {}).get("content"))))
                break
        else:
            print("  学生 %s 所有密码尝试失败" % uname)

# 检查教师端登录
print("\n=== 教师端登录测试 ===")
for u in users:
    if u.get("role") == "teacher":
        uname = u.get("username") or u.get("name")
        for pw in ["test1234", "123456", "password", "teacher", "12345678"]:
            r = requests.post(f"{TEACHER_URL}/api/login",
                              json={"username": uname, "password": pw}, timeout=5)
            d = r.json()
            if d.get("success"):
                print("  找到教师登录成功: username=%s password=%s -> name=%s" % (uname, pw, d.get("user", {}).get("name")))
                break
        else:
            print("  教师 %s 所有密码尝试失败" % uname)

print("\n=== GOAI Web (5000) 测试 ===")
for u in users:
    if u.get("role") == "student":
        uname = u.get("username") or u.get("name")
        for pw in ["test1234", "123456", "password", "student", "demo"]:
            r = requests.post(f"{GOAI_URL}/api/auth/login",
                              json={"username": uname, "password": pw}, timeout=5)
            d = r.json()
            if d.get("code") == 0:
                print("  GOAI 学生登录成功: username=%s password=%s" % (uname, pw))
                # 测试学习
                r2 = requests.post(f"{GOAI_URL}/api/learn/start",
                                   json={"topic": "牛顿第二定律", "subject": "物理", "difficulty": "高中"},
                                   timeout=10)
                d2 = r2.json()
                print("  start: code=%d sid=%s" % (d2.get("code"), d2.get("data", {}).get("id")))
                if d2.get("code") == 0:
                    sid_str = d2["data"].get("id", "")
                    r3 = requests.post(f"{GOAI_URL}/api/learn/step",
                                       json={"sessionId": sid_str, "step": 1}, timeout=30)
                    d3 = r3.json()
                    print("  step1: code=%d has_content=%s" % (d3.get("code"), bool((d3.get("data") or {}).get("content"))))
                break
        break

print("\n=== 前端页面检查 ===")
r = requests.get(f"{STU_URL}/index.html", timeout=5)
print("5010/index.html: HTTP %d has_real=%s" % (r.status_code, "__LUMILEARN_REAL__" in r.text))
r = requests.get(f"{GOAI_URL}/proto/index.html", timeout=5)
print("5000/proto/index.html: HTTP %d has_real=%s" % (r.status_code, "__LUMILEARN_REAL__" in r.text))
