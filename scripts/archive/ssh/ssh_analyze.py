import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

# Docker logs
stdin, stdout, stderr = ssh.exec_command('docker logs ollama 2>&1 | tail -30', timeout=10)
print('=== Docker logs ===')
print(stdout.read().decode().strip()[:2000])

# Write a Python script to remote for GGUF analysis
remote_script = """import sys
sys.path.insert(0, '/home/kai/lumilearn')
from gguf import GGUFReader

path = '/home/kai/lumilearn/deploy_gguf/lumilearn-v5-f32.gguf'
r = GGUFReader(path)

print('Fields:', len(r.fields))
for k in sorted(r.fields.keys()):
    f = r.fields[k]
    try:
        if k.startswith('tokenizer'):
            val = f.parts[f.types[0]]
            if hasattr(val, '__len__'):
                print(f'  {k}: array(len={len(val)}, first={val[0] if len(val) > 0 else None})')
            else:
                print(f'  {k}: {val}')
        else:
            parts = f.parts
            types = f.types
            for pi, pt in enumerate(types):
                v = parts[pi] if pi < len(parts) else '?'
                print(f'  {k}: {v}')
    except Exception as e:
        print(f'  {k}: ERROR: {e}')

print()
print('Tensors:', len(r.tensors))
for t in r.tensors[:3]:
    print(f'  {t.name}: shape={list(t.shape)}, type={t.tensor_type}')
"""

stdin, stdout, stderr = ssh.exec_command("cat > /tmp/analyze_gguf.py << 'PYEOF'\n" + remote_script + "\nPYEOF\npython3 /tmp/analyze_gguf.py 2>&1", timeout=30)
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print()
print('=== GGUF Analysis ===')
print(out)
if err:
    print('STDERR:', err[:500])

ssh.close()