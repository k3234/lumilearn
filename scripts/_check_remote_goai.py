# -*- coding: utf-8 -*-
"""检查天虹 goai 服务状态（paramiko，避免 ssh 密码交互挂起）"""
import os
import sys
import paramiko

host = os.environ.get("REMOTE_HOST") or os.environ.get("TIANHONG_HOST", "")
user = os.environ.get("REMOTE_USER") or os.environ.get("TIANHONG_USER", "")
password = os.environ.get("REMOTE_PASSWORD") or os.environ.get("TIANHONG_PASSWORD", "")

if not (host and user and password):
    print("错误: 缺少 SSH 连接配置，请设置 REMOTE_HOST / REMOTE_USER / REMOTE_PASSWORD")
    sys.exit(1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=15)

def run(cmd, timeout=20):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    o = out.read().decode(errors="replace").strip()
    e = err.read().decode(errors="replace").strip()
    return o, e

# 1. 服务文件定义
print("=== kai 的 user 服务 ===")
o, e = run("cat ~/.config/systemd/user/lumilearn-goai.service 2>&1")
print(o or "(不存在)")

print("\n=== goai 进程 ===")
o, e = run("ps aux | grep -E 'goai_web|goai_multi|5000' | grep -v grep")
print(o or "(无进程)")

print("\n=== 端口 5000 监听 ===")
o, e = run("ss -tlnp | grep 5000")
print(o or "(无监听)")

print("\n=== goai 日志（tail 20）===")
o, e = run("ls -t /home/kai/lumilearn/logs/ 2>/dev/null | head -5")
print("日志文件:", o or "(无 logs 目录)")
o, e = run("tail -20 /home/kai/lumilearn/logs/goai_web.log 2>/dev/null")
print(o or "(goai_web.log 不存在)")

print("\n=== systemd 状态 ===")
o, e = run("systemctl --user status lumilearn-goai --no-pager 2>&1 | head -15")
print(o or e or "(无输出)")

ssh.close()
