# -*- coding: utf-8 -*-
"""执行远程启动脚本并验证端口"""
import os
import sys
import time
import paramiko

REMOTE_BASE = "~/lumilearn"
host = os.environ.get("REMOTE_HOST", "192.168.2.xx")
user = os.environ.get("REMOTE_USER", "kai")
password = os.environ.get("REMOTE_PASSWORD", "")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=15)

# 上传启动脚本
sftp = ssh.open_sftp()
sftp.put("scripts/_teacher_start.sh", f"{REMOTE_BASE}/_teacher_start.sh")
sftp.close()

# 执行
stdin, stdout, stderr = ssh.exec_command(f"bash {REMOTE_BASE}/_teacher_start.sh")
out = stdout.read().decode("utf-8", "ignore").strip()
err = stderr.read().decode("utf-8", "ignore").strip()
print(f"启动输出: {out}")
if err:
    print(f"[stderr] {err[:300]}")
if "COMPILE_FAIL" in out:
    print("❌ 编译失败")
    sys.exit(1)

# 轮询端口
print("等待服务启动...")
ok = False
for i in range(20):
    time.sleep(1.5)
    stdin, stdout, stderr = ssh.exec_command("ss -tln | grep 5001 || true")
    if "5001" in stdout.read().decode("utf-8", "ignore"):
        print(f"✅ 端口 5001 已监听（{i * 1.5:.0f}s）")
        ok = True
        break
if not ok:
    stdin, stdout, stderr = ssh.exec_command(f"tail -30 {REMOTE_BASE}/logs/teacher_portal.log")
    print("⚠️ 端口未监听，日志：")
    print(stdout.read().decode("utf-8", "ignore"))
    sys.exit(1)

# HTTP 验证
time.sleep(1)
stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5001/")
print(f"首页 HTTP 状态: {stdout.read().decode('utf-8', 'ignore').strip()}")
stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:5001/api/me")
print(f"API 验证: {stdout.read().decode('utf-8', 'ignore').strip()[:200]}")
ssh.close()
print("✅ 部署验证完成")
