import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

print("=== Verify GGUF tokenizer ===")
cmd = """python3 << 'PYEOF'
from gguf import GGUFReader
r = GGUFReader("/home/kai/lumilearn/deploy_gguf/lumilearn-v5-f32.gguf")
t = r.fields.get("tokenizer.ggml.tokens")
if t:
    vals = t.parts[t.types[0]]
    print(f"tokenizer.ggml.tokens: {len(vals)} tokens")
    print(f"  [0]: {repr(vals[0])}")
    print(f"  [1]: {repr(vals[1])}")
    print(f"  [2]: {repr(vals[2])}")
    print(f"  [7999]: {repr(vals[7999] if len(vals) > 7999 else vals[-1])}")
else:
    print("tokenizer.ggml.tokens: NULL!")
PYEOF"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
print(stdout.read().decode().strip()[:500])

print()
print("=== Deploy to Ollama ===")
cmd = """cd /home/kai/lumilearn/deploy_gguf && ollama create lumilearn-v5:real -f Modelfile 2>&1"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
print(stdout.read().decode().strip()[:500])

print()
print("=== Verify Ollama model ===")
stdin, stdout, stderr = ssh.exec_command("ollama list | grep lumilearn", timeout=10)
print(stdout.read().decode().strip())

print()
print("=== Test API ===")
stdin, stdout, stderr = ssh.exec_command(
    """curl -s -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{"model":"lumilearn-v5:real","prompt":"hello","stream":false}' --max-time 60""",
    timeout=120
)
print(stdout.read().decode().strip()[:500])

ssh.close()
print("\nDone!")