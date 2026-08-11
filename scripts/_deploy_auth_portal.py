# -*- coding: utf-8 -*-
"""部署账号体系 + 学生端修复到天虹服务器

上传内容：
- student_portal.py（_sid 容错 + /api/profile）
- framework/api/routes/auth.py（新：users 表 token 登录，18080/18081/18082 共用）
- framework/api/routes/__init__.py + framework/api/server.py（注册 auth_bp）
- remote/templates/admin.html（用户管理班级绑定 UI）
- remote/templates/lumiterm.html（终端登录门）
- prototypes/student-learning-platform/ 全部前端文件（我的档案 + 退出登录 + 防挂护栏）

敏感信息从环境变量读取（REMOTE_HOST / REMOTE_USER / REMOTE_PASSWORD）。
用法:
    $env:REMOTE_HOST='服务器IP'; $env:REMOTE_USER='用户名'; $env:REMOTE_PASSWORD='密码'
    python scripts/_deploy_auth_portal.py
"""
import os
import sys
import time
import paramiko

REMOTE_BASE = "/home/kai/lumilearn"
host = os.environ.get("REMOTE_HOST") or os.environ.get("TIANHONG_HOST", "")
user = os.environ.get("REMOTE_USER") or os.environ.get("TIANHONG_USER", "")
password = os.environ.get("REMOTE_PASSWORD") or os.environ.get("TIANHONG_PASSWORD", "")

if not (host and user and password):
    print("错误: 缺少 SSH 连接配置。请先设置环境变量。")
    sys.exit(1)

LOCAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROTO = "prototypes/student-learning-platform"

FILES = [
    ("student_portal.py", f"{REMOTE_BASE}/student_portal.py"),
    ("framework/api/routes/auth.py", f"{REMOTE_BASE}/framework/api/routes/auth.py"),
    ("framework/api/routes/__init__.py", f"{REMOTE_BASE}/framework/api/routes/__init__.py"),
    ("framework/api/server.py", f"{REMOTE_BASE}/framework/api/server.py"),
    ("remote/templates/admin.html", f"{REMOTE_BASE}/tianhong/templates/admin.html"),
    ("remote/templates/lumiterm.html", f"{REMOTE_BASE}/tianhong/templates/lumiterm.html"),
    # 学生端前端（新增 profile.html/auth.js，更新 api.js 等）
    (f"{PROTO}/api.js", f"{REMOTE_BASE}/{PROTO}/api.js"),
    (f"{PROTO}/auth.js", f"{REMOTE_BASE}/{PROTO}/auth.js"),
    (f"{PROTO}/profile.html", f"{REMOTE_BASE}/{PROTO}/profile.html"),
    (f"{PROTO}/index.html", f"{REMOTE_BASE}/{PROTO}/index.html"),
    (f"{PROTO}/learn.html", f"{REMOTE_BASE}/{PROTO}/learn.html"),
    (f"{PROTO}/report.html", f"{REMOTE_BASE}/{PROTO}/report.html"),
    (f"{PROTO}/history.html", f"{REMOTE_BASE}/{PROTO}/history.html"),
    (f"{PROTO}/pages.css", f"{REMOTE_BASE}/{PROTO}/pages.css"),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=15)
print(f"已连接 {host}")

sftp = ssh.open_sftp()
for local, remote in FILES:
    sftp.put(os.path.join(LOCAL, local), remote)
    size = sftp.stat(remote).st_size
    print(f"  ✅ 上传 {local} ({size} bytes)")
sftp.close()
print("上传全部完成")


def run(cmd, t=90):
    _, o, e = ssh.exec_command(cmd, timeout=t)
    out = o.read().decode("utf-8", "ignore")
    err = e.read().decode("utf-8", "ignore")
    return out or err


# 1. 重启 framework 服务（注册 auth_bp，18080/18081/18082 生效）
print("\n重启 lumilearn-api ...")
out = run("systemctl --user restart lumilearn-api 2>&1; echo RC=$?")
print(out.strip()[-200:] or "(无输出)")

# 2. 重启学生端学习平台（5010，_sid 修复 + /api/profile）
print("重启学生端学习平台 ...")
run("pkill -9 -f student_portal.py 2>/dev/null; sleep 1")
out = run("cd /home/kai/lumilearn && STUDENT_PORT=5010 setsid nohup python3 student_portal.py > logs/student_portal.log 2>&1 & echo started")
print("  " + out.strip())

# 3. 等待并就绪验证
print("\n等待服务就绪 ...")
time.sleep(6)
checks = [
    ("auth login(18080)", "http://localhost:18080/api/auth/me"),
    ("auth login(18081)", "http://localhost:18081/api/auth/me"),
    ("admin classes(18082)", "http://localhost:18082/api/admin/classes"),
    ("student 页面 /", "http://localhost:5010/"),
    ("student profile API", "http://localhost:5010/api/profile"),
]
for name, url in checks:
    out = run(f"curl -s -m 8 -o /dev/null -w '%{{http_code}}' {url}")
    print(f"  {name}: HTTP {out or '无响应'}")

# 4. 终端登录接口实测（用测试账号 123/test123）
print("\n终端账号登录实测(18080) ...")
out = run("curl -s -m 10 -X POST http://localhost:18080/api/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"123\",\"password\":\"test123\"}'")
print("  " + (out[:200] or "(无响应)"))

ssh.close()
print("\n部署完成")
