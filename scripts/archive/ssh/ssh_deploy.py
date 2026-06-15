import paramiko
import time

def run(cmd, timeout=300):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    ssh.close()
    return out, err

print("=== Step 1: Install gguf ===")
out, err = run("pip3 install gguf -q 2>&1 | tail -1")
print(out or "OK")

print()
print("=== Step 2: Check checkpoint files ===")
out, err = run("ls -lh /home/kai/lumilearn/outputs/LumiLearn-v5_20260527_075859/checkpoints/")
print(out)

print()
print("=== Step 3: Run export_gguf_v6.py ===")
out, err = run("cd /home/kai/lumilearn && python3 export_gguf_v6.py 2>&1", timeout=120)
print(out[:2000])
if err: print("STDERR:", err[:500])

print()
print("=== Step 4: Check GGUF output ===")
out, err = run("ls -lh /home/kai/lumilearn/deploy_gguf/")
print(out)

print()
print("=== Step 5: Verify tokenizer ===")
out, err = run('python3 -c "from gguf import GGUFReader; r=GGUFReader(\"/home/kai/lumilearn/deploy_gguf/lumilearn-v5-f32.gguf\"); f=r.fields; tok_keys=[k for k in f if \"token\" in k or \"eos\" in k or \"bos\" in k]; print(\"Tokenizer keys:\", tok_keys); t=f.get(\"tokenizer.ggml.tokens\"); print(\"Tokens type:\", type(t.parts[t.types[0]]) if t else \"NULL\"); vals=t.parts[t.types[0]] if t else None; print(\"Tokens data type:\", type(vals)); print(\"Token count:\", len(vals) if hasattr(vals,\"__len__\") else \"cant_count\")"')
print(out)
if err: print("STDERR:", err[:300])