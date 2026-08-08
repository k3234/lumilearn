#!/usr/bin/env python3
"""上传 agent_core.py 到天虹服务器"""
import paramiko

HOST = "192.168.2.137"
USER = "kai"
PASS = "WWw2021x"
PORT = 22

LOCAL_FILE = r"E:\学习LLM\air-agent\agent_core.py"
REMOTE_DIR = "/home/kai/lumilearn"
REMOTE_FILE = f"{REMOTE_DIR}/agent_core.py"

print(f"连接 {USER}@{HOST}:{PORT} ...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, PORT, USER, PASS)
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