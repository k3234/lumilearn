import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

print("Checking tokenizers...")
stdin, stdout, stderr = ssh.exec_command('python3 -c "import tokenizers; print(tokenizers.__version__)"', timeout=10)
tok_ver = stdout.read().decode().strip()
print(f"tokenizers: {tok_ver}")

print()
print("=== Running export_gguf_v6.py ===")
stdin, stdout, stderr = ssh.exec_command('cd /home/kai/lumilearn && python3 -u export_gguf_v6.py 2>&1', timeout=120)
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print(out)
if err:
    print("STDERR:", err)

print()
print("=== GGUF files ===")
stdin, stdout, stderr = ssh.exec_command('ls -lh /home/kai/lumilearn/deploy_gguf/*.gguf 2>&1')
print(stdout.read().decode().strip())

ssh.close()
print("\nDone!")