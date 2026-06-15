import paramiko
import base64
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

# Upload via SFTP (simple file write)
print("Uploading fixed export_gguf_v6.py...")
with open('e:/学习LLM/lumilearn/export_gguf_v6.py', 'rb') as f:
    content = f.read()

sftp = ssh.open_sftp()
with sftp.file('/home/kai/lumilearn/export_gguf_v6.py', 'wb') as f:
    f.write(content)
sftp.close()
print("Upload done.")

# Run export
print()
print("Running export...")
start = time.time()
stdin, stdout, stderr = ssh.exec_command('cd /home/kai/lumilearn && python3 -u export_gguf_v6.py 2>&1', timeout=300)
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print(out)
if err: print("STDERR:", err[:500])
print(f"Time: {int(time.time()-start)}s")

# Re-deploy
print()
print("Re-deploying to Ollama...")
stdin, stdout, stderr = ssh.exec_command('ollama rm lumilearn-v5:real 2>&1; cd /home/kai/lumilearn/deploy_gguf && ollama create lumilearn-v5:real -f Modelfile 2>&1', timeout=120)
print(stdout.read().decode().strip())

# Test
print()
print("Testing model...")
stdin, stdout, stderr = ssh.exec_command(
    "curl -s -X POST http://localhost:11434/api/generate "
    "-H 'Content-Type: application/json' "
    "-d '{\"model\":\"lumilearn-v5:real\",\"prompt\":\"hello\",\"stream\":false}' "
    "--max-time 60",
    timeout=120
)
print(stdout.read().decode().strip()[:500])

# Check if the model loaded info changed
print()
print("Docker logs (last 10)...")
stdin, stdout, stderr = ssh.exec_command('docker logs ollama 2>&1 | tail -10', timeout=10)
print(stdout.read().decode().strip()[:1000])

ssh.close()
print("\nDone!")