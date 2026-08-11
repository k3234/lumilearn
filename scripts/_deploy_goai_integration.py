# -*- coding: utf-8 -*-
"""部署 GOAI Web 接入（Day1 + chat_history + 学生端原型）到天虹服务器

上传文件并重启 lumilearn-goai 服务，最后做本地冒烟验证。
敏感信息从环境变量读取（REMOTE_HOST / REMOTE_USER / REMOTE_PASSWORD，
兼容 TIANHONG_HOST / TIANHONG_USER / TIANHONG_PASSWORD），不写入仓库。

用法:
    $env:REMOTE_HOST='服务器IP'; $env:REMOTE_USER='用户名'; $env:REMOTE_PASSWORD='密码'
    python scripts/_deploy_goai_integration.py
"""
import os
import sys
import time
import paramiko

REMOTE_BASE = "/home/kai/lumilearn"  # paramiko SFTP 不展开 ~，必须绝对路径
host = os.environ.get("REMOTE_HOST") or os.environ.get("TIANHONG_HOST", "")
user = os.environ.get("REMOTE_USER") or os.environ.get("TIANHONG_USER", "")
password = os.environ.get("REMOTE_PASSWORD") or os.environ.get("TIANHONG_PASSWORD", "")

if not (host and user and password):
    print("错误: 缺少 SSH 连接配置。请先设置环境变量：")
    print("  $env:REMOTE_HOST='IP'; $env:REMOTE_USER='用户名'; $env:REMOTE_PASSWORD='密码'")
    sys.exit(1)

# 需要上传的本地 -> 远程文件
FILES = [
    ("goai_web.py", f"{REMOTE_BASE}/goai_web.py"),
    ("goai_agent.py", f"{REMOTE_BASE}/goai_agent.py"),
    ("langgraph_engine.py", f"{REMOTE_BASE}/langgraph_engine.py"),
    ("lumilearn_config.py", f"{REMOTE_BASE}/lumilearn_config.py"),
    ("framework/services/conversation_store.py",
     f"{REMOTE_BASE}/framework/services/conversation_store.py"),
]
PROTO_FILES = [
    "index.html", "learn.html", "report.html", "history.html",
    "styles.css", "pages.css", "mock.js", "api.js", "nav.js",
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=15)
print(f"已连接 {host}")

sftp = ssh.open_sftp()

# 1. 上传核心文件
for local, remote in FILES:
    sftp.put(local, remote)
    size = sftp.stat(remote).st_size
    print(f"  ✅ 上传 {local} ({size} bytes)")

# 2. 上传学生端原型（创建目录）
proto_remote_dir = f"{REMOTE_BASE}/prototypes/student-learning-platform"
try:
    sftp.stat(f"{REMOTE_BASE}/prototypes")
except IOError:
    sftp.mkdir(f"{REMOTE_BASE}/prototypes")
try:
    sftp.stat(proto_remote_dir)
except IOError:
    sftp.mkdir(proto_remote_dir)
for f in PROTO_FILES:
    local = os.path.join("prototypes", "student-learning-platform", f)
    sftp.put(local, f"{proto_remote_dir}/{f}")
    size = sftp.stat(f"{proto_remote_dir}/{f}").st_size
    print(f"  ✅ 上传原型 {f} ({size} bytes)")

sftp.close()
print("上传全部完成")

# 3. 重启 GOAI Web 服务（systemd user 服务；失败则回退 pkill + nohup）
def run(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "ignore")
    err = stderr.read().decode("utf-8", "ignore")
    return out, err

print("\n重启 lumilearn-goai 服务 ...")
out, err = run("systemctl --user restart lumilearn-goai 2>&1; echo RC=$?")
print(out.strip()[-400:] or "(无输出)")
if "RC=0" not in out:
    print("systemd 重启失败，回退 nohup 方式 ...")
    run("pkill -9 -f goai_web.py; sleep 1")
    run("cd ~/lumilearn && setsid nohup python3 goai_web.py > logs/goai_web.log 2>&1 & echo started")
    time.sleep(3)

# 4. 等待服务就绪并验证
print("\n等待服务就绪 ...")
time.sleep(4)
for _ in range(5):
    out, err = run("curl -s -m 5 http://localhost:5000/api/status | head -c 200")
    if out.strip():
        break
    time.sleep(3)

print("服务状态:", out.strip()[:200] or "(无响应)")
out, err = run("curl -s -m 5 -o /dev/null -w '%{http_code}' http://localhost:5000/proto/")
print("原型 /proto/ HTTP:", out.strip())
out, err = run("curl -s -m 5 -X POST http://localhost:5000/api/chat -H 'Content-Type: application/json' -d '{\"message\":\"我想理解函数的单调性\"}' | head -c 200")
print("对话 /api/chat:", out.strip()[:200])

ssh.close()
print("\n部署完成")
