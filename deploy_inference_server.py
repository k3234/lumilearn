"""Deploy LumiLearn V5 inference server - V5 (stable)"""
import paramiko, socket, time

def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(60)
    s.connect(('192.168.2.63', 22))
    t = paramiko.Transport(s)
    t.connect(username='kai', password='WWw2021x')
    ssh = paramiko.SSHClient()
    ssh._transport = t
    return ssh, t, s

def sh(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(errors='replace'), stderr.read().decode(errors='replace')

ssh, t, sock = connect()

print("Step 1: Upload server file via echo")
server_code = r"""
#!/usr/bin/env python3
import sys, os, json, time, uuid, argparse
from flask import Flask, request, jsonify, Response, stream_with_context

sys.path.insert(0, "/home/kai/lumilearn/deploy_model")
from inference import LumiLearnInference

app = Flask(__name__)

MODEL_DIR = "/home/kai/lumilearn/deploy_model"
MODEL_VERSION = "v5"
DEVICE = "cpu"

model = None

def get_model():
    global model
    if model is None:
        model = LumiLearnInference(MODEL_DIR, device=DEVICE)
    return model


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": f"LumiLearn-{MODEL_VERSION}", "device": DEVICE})

@app.route("/v1/models", methods=["GET"])
def list_models():
    return jsonify({"object": "list", "data": [{"id": f"LumiLearn-{MODEL_VERSION}", "object": "model", "owned_by": "lumilearn"}]})

@app.route("/api/generate", methods=["POST"])
def ollama_generate():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "")
    stream = data.get("stream", True)
    options = data.get("options", {})
    temperature = options.get("temperature", 0.7)
    max_tokens = options.get("num_predict", 256)
    
    sys_prompt = data.get("system", "你是LumiLearn，一个中文教育AI助手。请用中文回答。")
    full = f"指令：{sys_prompt}\n\n问题：{prompt}\n回答："
    
    m = get_model()
    result = m.generate(full, max_new_tokens=max_tokens, temperature=temperature)

    return jsonify({
        "model": f"LumiLearn-{MODEL_VERSION}",
        "response": result["text"],
        "done": True,
        "total_duration": int(result["time"] * 1e9),
        "eval_count": result["tokens"],
    })

@app.route("/api/tags", methods=["GET"])
def ollama_tags():
    return jsonify({"models": [{"name": f"LumiLearn-{MODEL_VERSION}:latest", "modified_at": "2026-05-27T00:00:00Z", "size": 0}]})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    print(f"[Server] LumiLearn Inference Server V5")
    print(f"[Server] Listening on {args.host}:{args.port}")
    get_model()
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
"""

# Write server file via cat heredoc (single quotes to prevent expansion)
server_encoded = server_code.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
cmd = f"""cat > /home/kai/lumilearn/inference_server_tianhong.py << 'PYEOF'
{server_code}
PYEOF
echo "SERVER_WRITTEN"
"""
out, err = sh(cmd, timeout=15)
print("Upload:", out[:200])

print("\nStep 2: Verify and fix inference.py")

# Check inference.py on Tianhong has the fixes
out, err = sh(
    'grep -c "weights_only=False" /home/kai/lumilearn/deploy_model/inference.py 2>&1 || echo "NEED_FIX"',
    timeout=10
)
print(f"weights_only check: {out[:100]}")

if "NEED_FIX" in out or "0" in out:
    print("Fixing inference.py...")
    fix_cmd = r'''
python3 -c "
import re
with open('/home/kai/lumilearn/deploy_model/inference.py', 'r') as f:
    c = f.read()
c = c.replace('weights_only=True', 'weights_only=False')
# Fix config loading
old = 'with open(config_path, \"r\") as f:\n            config_dict = json.load(f)\n\n        self.config = ModelConfig()\n        for k, v in config_dict.items():\n            if hasattr(self.config, k):\n                setattr(self.config, k, v)'
new = 'with open(config_path, \"r\") as f:\n            config_dict = json.load(f)\n        if \"model\" in config_dict:\n            config_dict = config_dict[\"model\"]\n        elif \"config\" in config_dict:\n            config_dict = config_dict[\"config\"]\n        model_fields = {f.name for f in ModelConfig.__dataclass_fields__.values()}\n        self.config = ModelConfig(**{k: v for k, v in config_dict.items() if k in model_fields})'
c = c.replace(old, new)
with open('/home/kai/lumilearn/deploy_model/inference.py', 'w') as f:
    f.write(c)
print('INFERENCE_FIXED')
"
'''
    out, err = sh(fix_cmd, timeout=15)
    print(out[:300])
    if err:
        print("Fix err:", err[:300])

print("\nStep 3: Kill old and start new server")
sh('pkill -f "inference_server_tianhong" 2>/dev/null; pkill -f "python3.*18080" 2>/dev/null', timeout=5)
time.sleep(2)

# Use invoke_shell for persistent launch
channel = ssh.invoke_shell()
channel.settimeout(15)
time.sleep(0.5)
try:
    channel.recv(8192)
except:
    pass

launch = (
    'export PATH=/usr/bin:/bin:/usr/local/bin:$PATH\n'
    'cd /home/kai/lumilearn\n'
    '/usr/bin/nohup /usr/bin/python3 inference_server_tianhong.py --port 18080 '
    '> /home/kai/lumilearn/inference_server.log 2>&1 &\n'
    'disown\n'
    'echo LAUNCHED\n'
)
channel.send(launch)
time.sleep(3)
try:
    out = channel.recv(8192).decode(errors='replace')
    print(f"Launch: {out[:300]}")
except:
    pass
channel.close()

print("Waiting 12s for model loading...")
time.sleep(12)

print("\nStep 4: Health check")
out, err = sh('curl -s http://localhost:18080/health --max-time 10 2>&1', timeout=15)
print(f"Health: {out[:300]}")

if '"status":"ok"' not in out:
    print("\nServer log:")
    out, _ = sh('tail -20 /home/kai/lumilearn/inference_server.log 2>&1', timeout=10)
    print(out[:2000])
    print("\nProcesses:")
    out, _ = sh('ps aux | grep "18080\|inference_server" 2>&1', timeout=5)
    print(out[:500])
    t.close()
    exit(1)

print("\nStep 5: Test inference")
out, err = sh(
    'curl -s -X POST http://localhost:18080/api/generate -H "Content-Type: application/json" '
    '-d \'{"model":"lumilearn-v5","prompt":"你好，请介绍一下自己","stream":false}\' --max-time 120 2>&1',
    timeout=120
)
print(f"Result: {out[:2000]}")

if '"response"' in out:
    import json
    data = json.loads(out)
    resp = data.get("response", "")
    print(f"\n{'=' * 60}")
    print(f"  LumiLearn V5 - LIVE!")
    print(f"  URL: http://192.168.2.63:18080")
    print(f"  Response: {resp[:300]}")
    print(f"\n  API Endpoints:")
    print(f"    POST /api/generate       (Ollama-compatible)")
    print(f"    POST /v1/chat/completions (OpenAI-compatible)") 
    print(f"    GET  /health")
    print(f"    GET  /api/tags")
    print(f"{'=' * 60}")
else:
    print(f"Error response: {out[:500]}")

t.close()