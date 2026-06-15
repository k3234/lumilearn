import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

# Check GGUF file hash
stdin, stdout, stderr = ssh.exec_command('sha256sum /home/kai/lumilearn/deploy_gguf/lumilearn-v5-f32.gguf', timeout=10)
print('GGUF hash:', stdout.read().decode().strip())

# Check Ollama cached blobs
stdin, stdout, stderr = ssh.exec_command('ls -la /root/.ollama/models/blobs/ 2>&1 | head -20', timeout=10)
print('Blobs:', stdout.read().decode().strip()[:500])

# Remove model and clear cache
stdin, stdout, stderr = ssh.exec_command('ollama rm lumilearn-v5:real 2>&1', timeout=30)
print('Remove:', stdout.read().decode().strip())

# Find and delete the GGUF blob
stdin, stdout, stderr = ssh.exec_command(
    'cd /home/kai/lumilearn/deploy_gguf && '
    'HASH=$(sha256sum lumilearn-v5-f32.gguf | cut -d" " -f1) && '
    'echo "GGUF hash: $HASH" && '
    'rm -f /root/.ollama/models/blobs/sha256-$HASH && '
    'echo "Blob deleted"',
    timeout=10
)
print('Blob cleanup:', stdout.read().decode().strip())

# Re-deploy
stdin, stdout, stderr = ssh.exec_command(
    'cd /home/kai/lumilearn/deploy_gguf && ollama create lumilearn-v5:real -f Modelfile 2>&1',
    timeout=120
)
print('Deploy:', stdout.read().decode().strip())

# Test
stdin, stdout, stderr = ssh.exec_command(
    "curl -s -X POST http://localhost:11434/api/generate "
    "-H 'Content-Type: application/json' "
    "-d '{\"model\":\"lumilearn-v5:real\",\"prompt\":\"hello\",\"stream\":false}' "
    "--max-time 60",
    timeout=120
)
print('Test:', stdout.read().decode().strip()[:500])

ssh.close()
print("\nDone!")