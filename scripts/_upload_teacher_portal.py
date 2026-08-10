# -*- coding: utf-8 -*-
"""分步部署教师端：仅上传文件并验证"""
import os
import sys
import time
import paramiko

REMOTE_BASE = "~/lumilearn"
host = os.environ.get("REMOTE_HOST", "192.168.2.xx")
user = os.environ.get("REMOTE_USER", "kai")
password = os.environ.get("REMOTE_PASSWORD", "")

if not password:
    print("缺少 REMOTE_PASSWORD")
    sys.exit(1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=15)
print("已连接")

sftp = ssh.open_sftp()
files = [
    ("framework/database.py", f"{REMOTE_BASE}/framework/database.py"),
    ("teacher_portal.py", f"{REMOTE_BASE}/teacher_portal.py"),
    ("remote/templates/teacher.html", f"{REMOTE_BASE}/remote/templates/teacher.html"),
]
for local, remote in files:
    print(f"上传 {local} ...")
    sftp.put(local, remote)
    size = sftp.stat(remote).st_size
    print(f"  ✅ 完成 ({size} bytes)")
sftp.close()
print("上传全部完成")
ssh.close()
