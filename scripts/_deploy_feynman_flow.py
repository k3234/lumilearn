# -*- coding: utf-8 -*-
"""部署费曼全流程接入 + Admin 端口同步到天虹服务器

上传内容：
- framework/api/routes/student_learn.py（新增：共享费曼学习 Blueprint）
- student_portal.py（改用共享 blueprint，step 修复）
- goai_web.py（注册共享 blueprint + /proto/ 注入真实标志）
- framework/services/provider_service.py（DEFAULT_PORT_MODEL_MAP 扩到 7 端口）

敏感信息从环境变量读取（REMOTE_HOST / REMOTE_USER / REMOTE_PASSWORD）。
用法:
    $env:REMOTE_HOST='服务器IP'; $env:REMOTE_USER='用户名'; $env:REMOTE_PASSWORD='密码'
    python scripts/_deploy_feynman_flow.py
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

LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES = [
    ("framework/api/routes/student_learn.py", f"{REMOTE_BASE}/framework/api/routes/student_learn.py"),
    ("student_portal.py", f"{REMOTE_BASE}/student_portal.py"),
    ("goai_web.py", f"{REMOTE_BASE}/goai_web.py"),
    ("framework/services/provider_service.py", f"{REMOTE_BASE}/framework/services/provider_service.py"),
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


# 1. 重启 framework 服务（provider_service 端口模型映射 7 端口生效）
print("\n重启 lumilearn-api ...")
out = run("systemctl --user restart lumilearn-api 2>&1; echo RC=$?")
print(out.strip()[-200:] or "(无输出)")

# 2. 重启学生端学习平台（5010，共享 blueprint + step 修复）
print("重启学生端学习平台 ...")
run("pkill -9 -f student_portal.py 2>/dev/null; sleep 1")
out = run("cd /home/kai/lumilearn && (STUDENT_PORT=5010 setsid nohup python3 student_portal.py > logs/student_portal.log 2>&1 </dev/null &) ; sleep 1; echo ok")
print("  " + out.strip())

# 3. 重启 GOAI Web（5000，注册共享 blueprint + /proto/ 注入）
print("重启 GOAI Web ...")
run("pkill -9 -f goai_web.py 2>/dev/null; sleep 1")
out = run("cd /home/kai/lumilearn && (GOAI_PORT=5000 setsid nohup python3 goai_web.py > logs/goai_web.log 2>&1 </dev/null &) ; sleep 1; echo ok")
print("  " + out.strip())

# 4. 等待并就绪验证
print("\n等待服务就绪 ...")
time.sleep(6)
checks = [
    ("5010 页面", "http://localhost:5010/"),
    ("5010 auth me", "http://localhost:5010/api/auth/me"),
    ("5000 /proto/", "http://localhost:5000/proto/"),
    ("5000 auth me", "http://localhost:5000/api/auth/me"),
    ("18082 port-models", "http://localhost:18082/api/admin/port-models"),
]
for name, url in checks:
    out = run(f"curl -s -m 8 -o /dev/null -w '%{{http_code}}' {url}")
    print(f"  {name}: HTTP {out or '无响应'}")

# 5. 18082 port-models 端口数验证
login = run("curl -s -m 8 -X POST http://localhost:18082/api/admin/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin123\"}'")
try:
    token = __import__("json").loads(login).get("token", "")
    out = run(f"curl -s -m 8 -H 'X-Admin-Token: {token}' http://localhost:18082/api/admin/port-models")
    import json
    pm = json.loads(out)
    print(f"  port-models 端口数: {len(pm.get('port_map', {}))} -> {list(pm.get('port_map', {}).keys())}")
except Exception as e:
    print("  port-models 解析失败:", e)

ssh.close()
print("\n部署完成")
