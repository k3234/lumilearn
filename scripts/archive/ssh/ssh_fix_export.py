import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

# Fix the export_gguf_v6.py on Tianhong
fix_script = [
    'cd /home/kai/lumilearn',
    'sed -i \'s|writer.add_string("tokenizer.ggml.model", "gpt2")|writer.add_tokenizer_model("gpt2")|\' export_gguf_v6.py',
    'sed -i \'s|writer.add_array("tokenizer.ggml.tokens", tokens)|writer.add_token_list(tokens)|\' export_gguf_v6.py',
    'sed -i \'s|writer.add_array("tokenizer.ggml.scores", scores)|writer.add_token_scores(scores)|\' export_gguf_v6.py',
    'sed -i \'s|writer.add_array("tokenizer.ggml.token_type", toktypes)|writer.add_token_types(toktypes)|\' export_gguf_v6.py',
    'sed -i \'s|writer.add_uint32("tokenizer.ggml.eos_token_id", 1)|writer.add_eos_token_id(1)|\' export_gguf_v6.py',
    'sed -i \'s|writer.add_uint32("tokenizer.ggml.bos_token_id", 2)|writer.add_bos_token_id(2)|\' export_gguf_v6.py',
    'sed -i \'s|writer.add_uint32("tokenizer.ggml.padding_token_id", 0)|writer.add_pad_token_id(0)|\' export_gguf_v6.py',
    'echo "Fix applied"',
    'grep -n "add_token" export_gguf_v6.py',
]

cmd = ' && '.join(fix_script)
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print("Fix result:", out)
if err: print("STDERR:", err[:500])

# Run export
print()
print("Running export_gguf_v6.py...")
start = time.time()
stdin, stdout, stderr = ssh.exec_command('cd /home/kai/lumilearn && python3 -u export_gguf_v6.py 2>&1', timeout=300)
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print(out)
if err: print("STDERR:", err[:500])
print(f"Time: {int(time.time()-start)}s")

# Verify tokenizer using a Python script on remote
print()
print("Verifying tokenizer...")
verify_script = """from gguf import GGUFReader
r = GGUFReader("/home/kai/lumilearn/deploy_gguf/lumilearn-v5-f32.gguf")
t = r.fields.get("tokenizer.ggml.tokens")
if t:
    vals = t.parts[t.types[0]]
    print(f"tokenizer.ggml.tokens: {len(vals)} tokens")
    print(f"  [0]: {repr(vals[0])}")
    print(f"  [1]: {repr(vals[1])}")
    print(f"  [2]: {repr(vals[2])}")
    print(f"  [3]: {repr(vals[3])}")
    if len(vals) >= 8000:
        print(f"  [7999]: {repr(vals[7999])}")
else:
    print("tokenizer.ggml.tokens: NOT FOUND!")
"""
# Write verify script to remote
stdin, stdout, stderr = ssh.exec_command(f"cat > /tmp/verify_gguf.py << 'PYEOF'\n{verify_script}\nPYEOF\npython3 /tmp/verify_gguf.py", timeout=30)
print(stdout.read().decode().strip())

ssh.close()
print("\nDone!")