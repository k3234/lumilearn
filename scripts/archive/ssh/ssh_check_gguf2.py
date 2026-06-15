import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

cmd = """python3 -c "
import gguf
from gguf import GGUFWriter
w = GGUFWriter('/tmp/_t.gguf', 'gpt2')
# Check ALL methods
methods = [m for m in dir(w) if not m.startswith('_')]
print('All public methods:', sorted(methods))
import os; os.unlink('/tmp/_t.gguf')
" 2>&1
"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
print(stdout.read().decode().strip())

print()
print("=== pip show gguf ===")
stdin, stdout, stderr = ssh.exec_command("pip3 show gguf 2>&1", timeout=10)
print(stdout.read().decode().strip())

ssh.close()