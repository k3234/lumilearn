# -*- coding: utf-8 -*-
"""部署 Day 2 改动（goai_multi_agent + goai_web 前端分离重构）到天虹服务器

上传：
  - goai_multi_agent.py（三 Agent 协作编排，新增）
  - goai_web.py（重构：render_template + /api/multi-agent 路由）
  - remote/templates/goai_learn.html    → 远程 tianhong/templates/goai_learn.html
  - remote/templates/goai_dashboard.html → 远程 tianhong/templates/goai_dashboard.html
重启 lumilearn-goai 服务并验证。

敏感信息从环境变量读取，不写入仓库。

用法:
    $env:REMOTE_HOST='IP'; $env:REMOTE_USER='用户名'; $env:REMOTE_PASSWORD='密码'
    python scripts/_deploy_day2.py
"""
import os
import sys
import paramiko

REMOTE_BASE = "/home/kai/lumilearn"
host = os.environ.get("REMOTE_HOST") or os.environ.get("TIANHONG_HOST", "")
user = os.environ.get("REMOTE_USER") or os.environ.get("TIANHONG_USER", "")
password = os.environ.get("REMOTE_PASSWORD") or os.environ.get("TIANHONG_PASSWORD", "")

if not (host and user and password):
    print("错误: 缺少 SSH 连接配置。请先设置环境变量：")
    print("  $env:REMOTE_HOST='IP'; $env:REMOTE_USER='用户名'; $env:REMOTE_PASSWORD='密码'")
    sys.exit(1)

FILES = [
    ("goai_multi_agent.py", f"{REMOTE_BASE}/goai_multi_agent.py"),
    ("goai_web.py", f"{REMOTE_BASE}/goai_web.py"),
    ("remote/templates/goai_learn.html", f"{REMOTE_BASE}/tianhong/templates/goai_learn.html"),
    ("remote/templates/goai_dashboard.html", f"{REMOTE_BASE}/tianhong/templates/goai_dashboard.html"),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=15)
print(f"已连接 {host}")

sftp = ssh.open_sftp()

for local, remote in FILES:
    sftp.put(local, remote)
    size = sftp.stat(remote).st_size
    print(f"  ✅ 上传 {local} -> {remote} ({size} bytes)")

sftp.close()

# 重启 goai 服务（systemd user 服务）
stdin, stdout, stderr = ssh.exec_command("systemctl --user restart lumilearn-goai")
err = stderr.read().decode().strip()
if err:
    print(f"  ⚠️ systemctl 提示: {err}")
print("  ✅ 已重启 lumilearn-goai")

# 稍等后验证
import time
time.sleep(3)
checks = [
    ("GET / (仪表盘)", "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/"),
    ("GET /learn (学习页)", "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/learn"),
    ("GET /api/status", "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/api/status"),
    ("multi-agent 未登录 401", "curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:5000/api/multi-agent -H 'Content-Type: application/json' -d '{\"topic\":\"函数\"}'"),
]
for label, cmd in checks:
    _, out, _ = ssh.exec_command(cmd)
    code = out.read().decode().strip()
    print(f"  {label}: HTTP {code}")

ssh.close()
print("\n部署完成")
