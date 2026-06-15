import paramiko
import base64
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

# Read local file and encode as base64
with open('e:/学习LLM/lumilearn/export_gguf_v6.py', 'rb') as f:
    b64_content = base64.b64encode(f.read()).decode()

print("=== Step 1: Upload fixed export_gguf_v6.py via base64 ===")
# Write in chunks to avoid command length limits
chunk_size = 50000
chunks = [b64_content[i:i+chunk_size] for i in range(0, len(b64_content), chunk_size)]

# First, clear the file
stdin, stdout, stderr = ssh.exec_command('rm -f /home/kai/lumilearn/export_gguf_v6.py.b64', timeout=10)
stdout.read()

# Write each chunk
for i, chunk in enumerate(chunks):
    cmd = f"echo '{chunk}' >> /home/kai/lumilearn/export_gguf_v6.py.b64"
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
    stdout.read()
    if i % 10 == 0:
        print(f"  Chunk {i+1}/{len(chunks)}...")

# Decode and save
stdin, stdout, stderr = ssh.exec_command(
    'cd /home/kai/lumilearn && base64 -d export_gguf_v6.py.b64 > export_gguf_v6.py && rm export_gguf_v6.py.b64 && echo "Upload OK" && wc -c export_gguf_v6.py',
    timeout=10
)
print(stdout.read().decode().strip())

print()
print("=== Step 2: Run export with fixed API ===")
start = time.time()
stdin, stdout, stderr = ssh.exec_command('cd /home/kai/lumilearn && python3 -u export_gguf_v6.py 2>&1', timeout=300)
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print(out)
if err:
    print("STDERR:", err[:500])
print(f"Time: {int(time.time() - start)}s")

print()
print("=== Step 3: Verify tokenizer ===")
cmd = """python3 -c "
from gguf import GGUFReader
r = GGUFReader('/home/kai/lumilearn/deploy_gguf/lumilearn-v5-f32.gguf')
t = r.fields.get('tokenizer.ggml.tokens')
if t:
    vals = t.parts[t.types[0]]
    print(f'Tokens: {len(vals)}')
    print(f'  [0]: {repr(vals[0])}')
    print(f'  [1]: {repr(vals[1])}')
    print(f'  [2]: {repr(vals[2])}')
    print(f'  [7999]: {repr(vals[7999]) if len(vals) >= 8000 else repr(vals[-1])}')
else:
    print('NOT FOUND')
" 2>&1
"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
print(stdout.read().decode().strip())

ssh.close()
print("\nDone!")