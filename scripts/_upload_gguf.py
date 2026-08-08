#!/usr/bin/env python3
"""上传 GGUF 模型文件到天虹服务器 (192.168.2.xx)"""
import paramiko
import os
import sys
import time

HOST = "192.168.2.xx"
USER = "kai"
PWD = "********"
REMOTE_DIR = "~/lumilearn/models/distil"
LOCAL_DIR = r"e:\学习LLM\lumilearn\models\distil"

files = [
    "lumilearn-v2-q8_0.gguf",
    "lumilearn-v2-f16.gguf",
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PWD, timeout=15)
print(f"[OK] 已连接 {USER}@{HOST}")

sftp = ssh.open_sftp()
try:
    sftp.stat(REMOTE_DIR)
except FileNotFoundError:
    sftp.mkdir(REMOTE_DIR)
    print(f"[OK] 创建目录 {REMOTE_DIR}")

for name in files:
    local_path = os.path.join(LOCAL_DIR, name)
    remote_path = f"{REMOTE_DIR}/{name}"
    if not os.path.exists(local_path):
        print(f"[SKIP] 本地不存在: {name}")
        continue
    size = os.path.getsize(local_path)
    # 若远端已有同大小文件则跳过
    try:
        r_size = sftp.stat(remote_path).st_size
        if r_size == size:
            print(f"[SKIP] 远端已存在同大小: {name} ({size/1e9:.2f} GB)")
            continue
    except FileNotFoundError:
        pass
    print(f"[上传] {name} ({size/1e9:.2f} GB) ...")
    t0 = time.time()
    sftp.put(local_path, remote_path)
    dt = time.time() - t0
    print(f"[完成] {name} 用时 {dt:.0f}s, 平均 {size/dt/1e6:.1f} MB/s")

sftp.close()
ssh.close()
print("[全部完成]")
