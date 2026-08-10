#!/usr/bin/env python3
"""上传 agent_core.py 到远程服务器服务器"""
import os
import sys
import paramiko

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _remote_config import get_config

HOST = os.environ.get("REMOTE_HOST", "")
USER = os.environ.get("REMOTE_USER", "")
PORT = 22
cfg = get_config(host=HOST, user=USER)

LOCAL_FILE = r"E:\学习LLM\air-agent\agent_core.py"
REMOTE_DIR = "~/lumilearn"
REMOTE_FILE = f"{REMOTE_DIR}/agent_core.py"

print(f"连接 {USER}@{HOST}:{PORT} ...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, PORT, USER, cfg["password"])
print("SSH 连接成功")

sftp = ssh.open_sftp()
print(f"上传: {LOCAL_FILE} -> {REMOTE_FILE}")
sftp.put(LOCAL_FILE, REMOTE_FILE, confirm=True)
sftp.close()

# 验证上传
stdin, stdout, stderr = ssh.exec_command(f"ls -la {REMOTE_FILE} && echo '---' && wc -l {REMOTE_FILE}")
print("验证结果:")
print(stdout.read().decode())

ssh.close()
print("上传完成")