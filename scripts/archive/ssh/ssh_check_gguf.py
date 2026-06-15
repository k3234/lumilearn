import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

# Check version and methods
cmd = """python3 -c "
import gguf
print('gguf version:', gguf.__version__)
from gguf import GGUFWriter
w = GGUFWriter('/tmp/_t.gguf', 'gpt2')
methods = [m for m in dir(w) if 'token' in m.lower()]
print('token methods:', methods)
import os; os.unlink('/tmp/_t.gguf')
" 2>&1
"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
print(stdout.read().decode().strip())

ssh.close()