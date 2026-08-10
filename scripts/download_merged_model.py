#!/usr/bin/env python3
"""从远程下载综合训练后的模型回本地"""
import paramiko
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _remote_config import get_config

HOST = os.environ.get("REMOTE_HOST", "")
USER = os.environ.get("REMOTE_USER", "")
cfg = get_config(host=HOST, user=USER)
REMOTE_BASE = "~/lumilearn"
LOCAL_BASE = r"<project-root>"

REMOTE_EXP = "outputs/cpu_small/LumiLearn-CPU-Small_20260807_135643"
LOCAL_EXP = os.path.join(LOCAL_BASE, "outputs", "cpu_small", "merged_gpu_train")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=cfg["password"], timeout=15)
sftp = ssh.open_sftp()

# 下载 model/ 目录 (config.json + model.pt)
os.makedirs(os.path.join(LOCAL_EXP, "model"), exist_ok=True)
for fn in ["config.json", "model.pt"]:
    remote = f"{REMOTE_BASE}/{REMOTE_EXP}/model/{fn}"
    local = os.path.join(LOCAL_EXP, "model", fn)
    try:
        sftp.get(remote, local)
        print(f"OK {fn} ({os.path.getsize(local)/1024/1024:.1f}MB)")
    except FileNotFoundError:
        print(f"SKIP {fn} 不存在")

# 下载其他文件
for fn in ["tokenizer.json", "training_metrics.json", "config.json"]:
    remote = f"{REMOTE_BASE}/{REMOTE_EXP}/{fn}"
    local = os.path.join(LOCAL_EXP, fn)
    try:
        sftp.get(remote, local)
        print(f"OK {fn} ({os.path.getsize(local)/1024:.0f}KB)")
    except FileNotFoundError:
        print(f"SKIP {fn} 不存在")

sftp.close()
ssh.close()
print("\n下载完成!")
