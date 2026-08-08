#!/usr/bin/env python3
"""从天虹下载 v2 合并模型到本地"""
import paramiko
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _tianhong_config import get_config

HOST = "192.168.2.xx"
USER = "kai"
cfg = get_config(host=HOST, user=USER)
REMOTE_BASE = "~/lumilearn/models/distil/merged_model_15b_v2"
LOCAL_BASE = r"e:\学习LLM\lumilearn\models\distil\merged_model_15b_v2"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=cfg["password"], timeout=15)
sftp = ssh.open_sftp()
print(f"[OK] 已连接 {USER}@{HOST}")

stdin, stdout, stderr = ssh.exec_command(f"ls {REMOTE_BASE}/", timeout=15)
files = [l.strip() for l in stdout.read().decode().strip().split("\n") if l.strip()]
print(f"远程文件: {files}")

os.makedirs(LOCAL_BASE, exist_ok=True)

total = 0
for fn in files:
    remote = f"{REMOTE_BASE}/{fn}"
    local = os.path.join(LOCAL_BASE, fn)
    try:
        st = sftp.stat(remote)
    except Exception:
        continue
    if st.st_mode & 0o40000:  # 目录跳过
        continue
    print(f"下载 {fn} ({st.st_size/1024/1024:.0f}MB)...", flush=True)
    sftp.get(remote, local)
    total += st.st_size
    print(f"  OK ({os.path.getsize(local)/1024/1024:.0f}MB)")

sftp.close()
ssh.close()
print(f"\n[完成] 共下载 {total/1024/1024/1024:.2f}GB 到 {LOCAL_BASE}")
