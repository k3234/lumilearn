import paramiko
import time

def run_ssh_script(script_content, description="", timeout=600):
    """Upload and execute a script on Tianhong"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

    sftp = ssh.open_sftp()
    sftp.putfo(__import__('io').StringIO(script_content), "/tmp/deploy_step.sh")
    sftp.close()

    stdin, stdout, stderr = ssh.exec_command("bash /tmp/deploy_step.sh 2>&1", timeout=timeout)
    
    # Read with progress
    channel = stdout.channel
    all_output = []
    start = time.time()
    while not channel.exit_status_ready():
        if channel.recv_ready():
            data = channel.recv(4096).decode(errors='replace')
            all_output.append(data)
            print(data, end='', flush=True)
        if time.time() - start > timeout:
            print("\n[TIMEOUT]")
            break
        time.sleep(0.5)
    
    # Read remaining
    while channel.recv_ready():
        data = channel.recv(4096).decode(errors='replace')
        all_output.append(data)
        print(data, end='', flush=True)

    ssh.close()
    return ''.join(all_output)

# ===== STEP 1: Install dependencies =====
print("=" * 60)
print("STEP 1: Install Python dependencies")
print("=" * 60)

script = """#!/bin/bash
set -e
echo "Installing tokenizers..."
pip3 install tokenizers -q 2>&1 | tail -3
echo "tokenizers installed: $(python3 -c 'import tokenizers; print(tokenizers.__version__)')"

echo "Checking gguf..."
python3 -c "import gguf; print('gguf:', gguf.__version__)" 2>/dev/null || pip3 install gguf -q

echo "Checking torch..."
python3 -c "import torch; print('torch:', torch.__version__)" 2>/dev/null || echo "torch not found (expected for export only)"

echo "DONE: All dependencies installed"
"""
out = run_ssh_script(script, "Installing deps", timeout=300)
print()

# ===== STEP 2: Export GGUF =====
print("=" * 60)
print("STEP 2: Export GGUF from checkpoint")
print("=" * 60)

script = """#!/bin/bash
set -e
cd /home/kai/lumilearn

# List available checkpoints
echo "Available checkpoints:"
ls -lh outputs/LumiLearn-v5_*/checkpoints/ 2>/dev/null || echo "No checkpoints found"

# Run export
echo ""
echo "Running export_gguf_v6.py..."
python3 export_gguf_v6.py 2>&1

echo ""
echo "GGUF output:"
ls -lh deploy_gguf/*.gguf 2>/dev/null || echo "No GGUF files found"
"""
out = run_ssh_script(script, "Exporting GGUF", timeout=300)
print()

# ===== STEP 3: Verify and Deploy =====
print("=" * 60)
print("STEP 3: Verify GGUF and deploy to Ollama")
print("=" * 60)

script = """#!/bin/bash
set -e
cd /home/kai/lumilearn/deploy_gguf

GGUF_FILE="lumilearn-v5-f32.gguf"
if [ ! -f "$GGUF_FILE" ]; then
    echo "ERROR: GGUF file not found"
    exit 1
fi

# Verify tokenizer with gguf lib
echo "Verifying GGUF tokenizer..."
python3 << 'PYEOF'
from gguf import GGUFReader
r = GGUFReader("lumilearn-v5-f32.gguf")
# Check architecture
for key in ["general.architecture", "gpt2.embedding_length", "gpt2.block_count", "gpt2.context_length"]:
    f = r.fields.get(key)
    if f:
        print(f"  {key}: {f.parts[f.types[0]]}")
    else:
        print(f"  {key}: NOT FOUND")

# Check tokenizer
t = r.fields.get("tokenizer.ggml.tokens")
if t:
    vals = t.parts[t.types[0]]
    print(f"  tokenizer.ggml.tokens: {len(vals)} tokens")
    print(f"    [0]: {vals[0]}")
    print(f"    [1]: {vals[1]}")
    print(f"    [2]: {vals[2]}")
    print(f"    [7999]: {vals[7999] if len(vals) > 7999 else vals[-1]}")
else:
    print("  tokenizer.ggml.tokens: NULL - FIX NEEDED!")
PYEOF

echo ""
echo "Creating Modelfile..."
cat > Modelfile << 'MODELEOF'
FROM ./lumilearn-v5-f32.gguf

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 384
PARAMETER num_predict 256
PARAMETER repeat_penalty 1.1
PARAMETER stop "<eos>"
PARAMETER stop "###"

SYSTEM """你是 LumiLearn (灵学) AI教育助手，专注于中国K-12教育领域的知识讲解与答疑。"""

TEMPLATE """{{ .System }}

### 问题
{{ .Prompt }}

### 回答
"""
MODELEOF

echo "Creating lumilearn-v5:real in Ollama..."
ollama create lumilearn-v5:real -f Modelfile

echo ""
echo "Verifying deployment..."
ollama list | grep lumilearn

echo ""
echo "Testing API..."
curl -s -X POST http://localhost:11434/api/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"lumilearn-v5:real","prompt":"你好","stream":false}' \
    --max-time 60 | python3 -c "import sys,json; d=json.load(sys.stdin); print('Response:', d.get('response','ERROR')[:200])" 2>&1

echo ""
echo "DEPLOYMENT COMPLETE!"
"""
out = run_ssh_script(script, "Deploying model", timeout=600)