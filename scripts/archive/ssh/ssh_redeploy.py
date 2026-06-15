import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

# Step 1: Remove old model and re-deploy
print("=== Step 1: Remove old lumilearn-v5:real ===")
stdin, stdout, stderr = ssh.exec_command('ollama rm lumilearn-v5:real 2>&1', timeout=30)
print(stdout.read().decode().strip())

# Step 2: Re-deploy with fixed GGUF
print()
print("=== Step 2: Create lumilearn-v5:real ===")
stdin, stdout, stderr = ssh.exec_command('cd /home/kai/lumilearn/deploy_gguf && ollama create lumilearn-v5:real -f Modelfile 2>&1', timeout=120)
print(stdout.read().decode().strip())

# Step 3: Verify model list
print()
print("=== Step 3: Model list ===")
stdin, stdout, stderr = ssh.exec_command('ollama list | grep lumilearn', timeout=10)
print(stdout.read().decode().strip())

# Step 4: Test API
print()
print("=== Step 4: Test API ===")
stdin, stdout, stderr = ssh.exec_command(
    'curl -s -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d \'{"model":"lumilearn-v5:real","prompt":"hello","stream":false}\' --max-time 60 2>&1',
    timeout=120
)
print(stdout.read().decode().strip()[:500])

ssh.close()
print("\nDone!")