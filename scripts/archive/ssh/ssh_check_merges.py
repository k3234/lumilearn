import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

# Check how to get merges from tokenizer
remote_script = """import sys
sys.path.insert(0, '/home/kai/lumilearn')
from framework.tokenizer import LumiLearnTokenizer

tokenizer = LumiLearnTokenizer(vocab_size=8000)
t = tokenizer._tokenizer

print('Tokenizer type:', type(t))
print('Model type:', type(t.model))

# Check available attributes
attrs = [a for a in dir(t.model) if not a.startswith('_')]
print('Model attrs:', attrs[:20])

# Check if model has merges
model = t.model
if hasattr(model, 'merges'):
    merges = model.merges
    print(f'Merges type: {type(merges)}')
    if hasattr(merges, '__len__'):
        print(f'Merges count: {len(merges)}')
    print('First 3 merges:', list(merges)[:3] if hasattr(merges, '__iter__') else merges[:3])
else:
    print('No merges attribute on model')

# Try get_merges if available
if hasattr(t, 'get_merges'):
    print('get_merges() available')

# Check the model's specific type
print(f'Model class: {type(model).__name__}')
print(f'Model module: {type(model).__module__}')

# Try to extract merges through the model
import tokenizers as tk
bpe = model
# BPE models store merges as a list of (str, str) tuples
if isinstance(bpe, tk.models.BPE):
    print('It is a BPE model')
    merges = bpe.merges
    print(f'Merges: {len(merges)}')
    print('First 3:', merges[:3])
"""
stdin, stdout, stderr = ssh.exec_command(
    "cat > /tmp/check_merges.py << 'PYEOF'\n" + remote_script + "\nPYEOF\npython3 /tmp/check_merges.py 2>&1",
    timeout=30
)
print(stdout.read().decode().strip())

ssh.close()