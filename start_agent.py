#!/usr/bin/env python3
"""SSH 交互式启动 agent_core.py"""
import os
import sys
import paramiko
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _tianhong_config import get_config

HOST = "192.168.2.137"
USER = "kai"
PORT = 22
cfg = get_config(host=HOST, user=USER)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, PORT, USER, cfg["password"])

# 使用 invoke_shell 获取交互式终端
channel = ssh.invoke_shell()
print("终端已连接，启动 agent_core.py ...\n")

# 发送命令
channel.send("/usr/bin/python3 /home/kai/lumilearn/agent_core.py\n")
time.sleep(2)

# 读取启动输出
output = ""
while channel.recv_ready():
    output += channel.recv(4096).decode("utf-8", errors="replace")
print(output)

# 发送一个测试问题
channel.send("你好，介绍一下你自己\n")
time.sleep(5)
while channel.recv_ready():
    output = channel.recv(8192).decode("utf-8", errors="replace")
    print(output)

# 发送退出命令
channel.send("exit\n")
time.sleep(1)
while channel.recv_ready():
    output = channel.recv(4096).decode("utf-8", errors="replace")
    print(output)

channel.close()
ssh.close()
print("\nAgent 测试完成")