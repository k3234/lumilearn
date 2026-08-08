#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.2.xx", username="kai", password="********", timeout=15)

cmd = "which ollama 2>&1; ls -la /usr/local/bin/ollama 2>&1; sudo -n true 2>&1 && echo SUDO_OK || echo SUDO_NEED_PWD; ps aux | grep -E 'ollama|curl.*install' | grep -v grep | head -5"
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=20)
print(stdout.read().decode(errors="replace"))
ssh.close()
