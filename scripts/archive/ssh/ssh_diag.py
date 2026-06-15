import paramiko

def run_ssh(cmd):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    ssh.close()
    return out, err

print('=== 1. 项目目录 ===')
out, err = run_ssh('ls -la /home/kai/lumilearn/ 2>/dev/null || echo DIR_NOT_FOUND')
print(out[:800])
if err: print('STDERR:', err[:200])

print()
print('=== 2. Ollama Models ===')
out, err = run_ssh('ollama list 2>/dev/null || echo OLLAMA_NOT_FOUND')
print(out[:800])
if err: print('STDERR:', err[:200])

print()
print('=== 3. Python ===')
out, err = run_ssh('python3 --version 2>/dev/null; pip3 --version 2>/dev/null')
print(out[:800])

print()
print('=== 4. Ports ===')
out, err = run_ssh("ss -tlnp 2>/dev/null | grep -E '11434|18080' || echo PORTS_CLEAN")
print(out[:800])

print()
print('=== 5. Checkpoints ===')
out, err = run_ssh('ls -laR /home/kai/lumilearn/outputs/ 2>/dev/null || echo NO_OUTPUTS')
print(out[:1000])

print()
print('=== 6. Disk Space ===')
out, err = run_ssh('df -h /home/kai/')
print(out[:500])