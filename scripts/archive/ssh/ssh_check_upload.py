import paramiko
import base64
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

# Check current content on Tianhong
print("=== Current export_gguf_v6.py (tokenizer section) ===")
stdin, stdout, stderr = ssh.exec_command('grep -n "merges\|add_token_merges\|build_tokenizer" /home/kai/lumilearn/export_gguf_v6.py', timeout=10)
print(stdout.read().decode().strip())

# Check what tokenizer returns for merges
print()
print("=== Check tokenizer merges ===")
remote_script = """import sys, json
sys.path.insert(0, '/home/kai/lumilearn')
from framework.tokenizer import LumiLearnTokenizer

tokenizer = LumiLearnTokenizer(vocab_size=8000)
tok_json = json.loads(tokenizer._tokenizer.to_str())
model = tok_json.get('model', {})
merges = model.get('merges', [])
print(f'Merges count: {len(merges)}')
if len(merges) > 0:
    print(f'First 5: {merges[:5]}')
else:
    print(f'Model keys: {list(model.keys())}')
    # check if it's a BPE model
    print(f'Model type: {model.get("type", "unknown")}')
"""
stdin, stdout, stderr = ssh.exec_command(
    "cat > /tmp/chk_merges.py << 'PYEOF'\n" + remote_script + "\nPYEOF\npython3 /tmp/chk_merges.py 2>&1",
    timeout=30
)
print(stdout.read().decode().strip())

ssh.close()