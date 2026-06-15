import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

# Check GGUF metadata
print("=== GGUF Metadata ===")
cmd = """python3 -c "
from gguf import GGUFReader
r = GGUFReader('/home/kai/lumilearn/deploy_gguf/lumilearn-v5-f32.gguf')
keys = sorted(r.fields.keys())
for k in keys:
    f = r.fields[k]
    try:
        val = f.parts[f.types[0]]
        print(f'{k}: {val}')
    except:
        print(f'{k}: <error reading>')
" 2>&1
"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
print(stdout.read().decode().strip())

# Check tensor info
print()
print("=== Tensor Info ===")
cmd = """python3 -c "
from gguf import GGUFReader
r = GGUFReader('/home/kai/lumilearn/deploy_gguf/lumilearn-v5-f32.gguf')
print(f'Tensor count: {len(r.tensors)}')
for i, t in enumerate(r.tensors):
    if i < 5:
        print(f'  {t.name}: shape={t.shape}, type={t.tensor_type}')
    elif i == 5:
        print(f'  ... ({len(r.tensors)} total)')
print(f'  ...')
for i, t in enumerate(r.tensors):
    if i >= len(r.tensors) - 5:
        print(f'  {t.name}: shape={t.shape}, type={t.tensor_type}')
" 2>&1
"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
print(stdout.read().decode().strip())

# Check Ollama server logs for error details
print()
print("=== Ollama error details ===")
cmd = """curl -s -X POST http://localhost:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"model":"lumilearn-v5:real","prompt":"hi","stream":false}' \
  --max-time 60 2>&1
"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
print(stdout.read().decode().strip())

# Check if ollama is a systemd service or docker
print()
print("=== Ollama service check ===")
stdin, stdout, stderr = ssh.exec_command('systemctl status ollama 2>&1 | head -5; echo "---"; docker ps 2>&1 | grep -i ollama', timeout=10)
print(stdout.read().decode().strip())

ssh.close()