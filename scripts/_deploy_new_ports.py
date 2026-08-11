# -*- coding: utf-8 -*-
"""部署学生端学习平台(5010) + 学习分析仪表盘(18090)到天虹服务器

上传新服务 + 前端双模式改造 + 端口配置，启动两个新服务并重启 framework 服务。
敏感信息从环境变量读取（REMOTE_HOST / REMOTE_USER / REMOTE_PASSWORD）。

用法:
    $env:REMOTE_HOST='服务器IP'; $env:REMOTE_USER='用户名'; $env:REMOTE_PASSWORD='密码'
    python scripts/_deploy_new_ports.py
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

FILES = [
    ("student_portal.py", f"{REMOTE_BASE}/student_portal.py"),
    ("analytics_dashboard.py", f"{REMOTE_BASE}/analytics_dashboard.py"),
    ("framework/services/provider_service.py", f"{REMOTE_BASE}/framework/services/provider_service.py"),
    ("config/framework.yaml", f"{REMOTE_BASE}/config/framework.yaml"),
    ("scripts/remote_start_all.sh", f"{REMOTE_BASE}/scripts/remote_start_all.sh"),
    ("prototypes/student-learning-platform/api.js", f"{REMOTE_BASE}/prototypes/student-learning-platform/api.js"),
    ("prototypes/student-learning-platform/index.html", f"{REMOTE_BASE}/prototypes/student-learning-platform/index.html"),
    ("prototypes/student-learning-platform/pages.css", f"{REMOTE_BASE}/prototypes/student-learning-platform/pages.css"),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=15)
print(f"已连接 {host}")

sftp = ssh.open_sftp()
for local, remote in FILES:
    sftp.put(local, remote)
    size = sftp.stat(remote).st_size
    print(f"  ✅ 上传 {local} ({size} bytes)")
sftp.close()
print("上传全部完成")


def run(cmd, t=90):
    _, o, e = ssh.exec_command(cmd, timeout=t)
    out = o.read().decode("utf-8", "ignore")
    err = e.read().decode("utf-8", "ignore")
    return out or err


# 1. 重启 framework 服务（provider_service 新增端口配置生效，Admin 端口管理可见新端口）
print("\n重启 lumilearn-api ...")
out = run("systemctl --user restart lumilearn-api 2>&1; echo RC=$?")
print(out.strip()[-200:] or "(无输出)")

# 2. 启动学生端学习平台（5010）
print("启动学生端学习平台 ...")
out = run("curl -s -o /dev/null -w '%{http_code}' http://localhost:5010/api/status 2>/dev/null")
if out == "200":
    print("  已在运行")
else:
    run("pkill -9 -f student_portal.py 2>/dev/null; sleep 1")
    out = run("cd /home/kai/lumilearn && STUDENT_PORT=5010 setsid nohup python3 student_portal.py > logs/student_portal.log 2>&1 & echo started")
    print("  " + out.strip())

# 3. 启动学习分析仪表盘（18090）
print("启动学习分析仪表盘 ...")
out = run("curl -s -o /dev/null -w '%{http_code}' http://localhost:18090/api/dashboard/overview 2>/dev/null")
if out == "200":
    print("  已在运行")
else:
    run("pkill -9 -f analytics_dashboard.py 2>/dev/null; sleep 1")
    out = run("cd /home/kai/lumilearn && ANALYTICS_PORT=18090 setsid nohup python3 analytics_dashboard.py > logs/analytics_dashboard.log 2>&1 & echo started")
    print("  " + out.strip())

# 4. 等待并就绪验证
print("\n等待服务就绪 ...")
time.sleep(5)
for name, url in [("学生端 /api/status", "http://localhost:5010/api/status"),
                  ("学生端页面 /", "http://localhost:5010/"),
                  ("仪表盘 /api/dashboard/overview", "http://localhost:18090/api/dashboard/overview"),
                  ("仪表盘页面 /", "http://localhost:18090/")]:
    out = run(f"curl -s -m 6 -o /dev/null -w '%{{http_code}}' {url}")
    print(f"  {name}: HTTP {out or '无响应'}")

ssh.close()
print("\n部署完成")
