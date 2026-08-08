#!/usr/bin/env python3
"""在天虹服务器 (192.168.2.68) 上安装 Ollama 并注册 LumiLearn V2 模型"""
import paramiko
import time

HOST = "192.168.2.68"
USER = "kai"
PWD = "WWw2021x"
REMOTE = "/home/kai/lumilearn"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PWD, timeout=15)
print(f"[OK] 已连接 {USER}@{HOST}")

def run(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return out, err

# 1. 检查 ollama 是否已安装
out, err = run("which ollama && ollama --version || echo NOT_INSTALLED")
if "NOT_INSTALLED" in out or "not found" in err:
    print("[1/4] 安装 Ollama ...")
    out, err = run("curl -fsSL https://ollama.com/install.sh | sh", timeout=300)
    print(out[-500:] if out else "")
    if err:
        print("stderr:", err[-500:])
    out, err = run("which ollama && ollama --version")
    print("[OK] Ollama 安装:", out.strip())
else:
    print("[1/4] Ollama 已安装:", out.strip())

# 2. 写 Modelfile
print("[2/4] 创建 Modelfile ...")
modelfile = f"""FROM {REMOTE}/models/distil/lumilearn-v2-q8_0.gguf

TEMPLATE \"\"\"{{{{- if .System }}}}<|im_start|>system
{{{{ .System }}}}<|im_end|>
{{{{- end }}}}
<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
<|im_start|>assistant
\"\"\"

PARAMETER temperature 0.7
PARAMETER top_p 0.8
PARAMETER num_ctx 4096
"""
with ssh.open_sftp().open(f"{REMOTE}/Modelfile.lumilearn-v2", "w") as f:
    f.write(modelfile)
print("[OK] Modelfile 已写入")

# 3. 创建模型
print("[3/4] ollama create lumilearn-v2 ...")
out, err = run(f"ollama create lumilearn-v2 -f {REMOTE}/Modelfile.lumilearn-v2", timeout=300)
print(out[-800:] if out else "")
if err:
    print("stderr:", err[-500:])

# 4. 测试推理
print("[4/4] 推理测试 ...")
test_prompt = "用费曼五步法讲解勾股定理"
out, err = run(
    f"ollama run lumilearn-v2 '{test_prompt}' --nowordwrap 2>/dev/null | head -60 || echo FAIL",
    timeout=300,
)
print("测试输出:")
print(out[:2000] if out else "(空)")
print("stderr:", err[-500:] if err else "(无)")

ssh.close()
print("\n[完成] 天虹 Ollama 部署流程结束")
