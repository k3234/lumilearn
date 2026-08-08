#!/usr/bin/env python3
import os
import sys
import paramiko

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _tianhong_config import get_config

cfg = get_config()
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(cfg["host"], username=cfg["user"], password=cfg["password"], timeout=15)

cmd = "which ollama 2>&1; ls -la /usr/local/bin/ollama 2>&1; sudo -n true 2>&1 && echo SUDO_OK || echo SUDO_NEED_PWD; ps aux | grep -E 'ollama|curl.*install' | grep -v grep | head -5"
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=20)
print(stdout.read().decode(errors="replace"))
ssh.close()
