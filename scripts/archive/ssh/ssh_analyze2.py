import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

# Get full Docker logs for the error
stdin, stdout, stderr = ssh.exec_command('docker logs ollama 2>&1 | tail -50', timeout=10)
full_logs = stdout.read().decode().strip()
print('=== Full Docker logs ===')
print(full_logs[-3000:])

print()
print('=== Tensor names check ===')
# Check tensor naming
remote_script = """from gguf import GGUFReader
r = GGUFReader('/home/kai/lumilearn/deploy_gguf/lumilearn-v5-f32.gguf')
for t in r.tensors:
    print(t.name)
"""
stdin, stdout, stderr = ssh.exec_command(
    "cat > /tmp/list_tensors.py << 'PYEOF'\n" + remote_script + "\nPYEOF\npython3 /tmp/list_tensors.py 2>&1",
    timeout=30
)
print(stdout.read().decode().strip())

ssh.close()