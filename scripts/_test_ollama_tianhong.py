#!/usr/bin/env python3
import os
import sys
import paramiko
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _tianhong_config import get_config

cfg = get_config()
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(cfg["host"], username=cfg["user"], password=cfg["password"], timeout=15)

def run(cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return out, err

# 1. 模型列表
out, err = run("ollama list")
print("=== ollama list ===")
print(out)

# 2. 停掉旧推理进程
run("pkill -f 'ollama run lumilearn-v2' 2>/dev/null; true")

# 3. 用 API 测试推理（非流式）
print("=== API 推理测试 ===")
cmd = (
    "curl -s http://localhost:11434/api/generate "
    "-d '{\"model\":\"lumilearn-v2\",\"prompt\":\"用费曼五步法讲解勾股定理\","
    "\"stream\":false,\"options\":{\"temperature\":0.7,\"num_predict\":300}}' "
    "> /tmp/ollama_test.json 2>&1; "
    "python3 -c \"import json; d=json.load(open('/tmp/ollama_test.json')); "
    "print('回复:', d.get('response','')[:800]); "
    "print('耗时(s):', d.get('total_duration',0)/1e9); "
    "print('tok/s:', d.get('eval_count',0)/max(d.get('eval_duration',1),1)*1e9)\""
)
out, err = run(cmd, timeout=300)
print(out[-2500:])
if err:
    print("stderr:", err[-500:])

ssh.close()
print("\n[完成]")
