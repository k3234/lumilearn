import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.2.63', username='kai', password='WWw2021x', timeout=10)

# Test lumilearn-v5:fixed (should work)
print("=== Test lumilearn-v5:fixed ===")
stdin, stdout, stderr = ssh.exec_command(
    "curl -s -X POST http://localhost:11434/api/generate "
    "-H 'Content-Type: application/json' "
    "-d '{\"model\":\"lumilearn-v5:fixed\",\"prompt\":\"hello\",\"stream\":false}' "
    "--max-time 60",
    timeout=120
)
print(stdout.read().decode().strip()[:500])

# Check Ollama logs for the real model error
print()
print("=== Ollama logs (last 20 lines) ===")
stdin, stdout, stderr = ssh.exec_command('journalctl -u ollama --no-pager -n 20 2>&1 || docker logs ollama --tail 20 2>&1 || tail -20 /var/log/ollama.log 2>&1 || echo "No logs found"', timeout=10)
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print(out[:1000])
if err: print("STDERR:", err[:500])

# Check GGUF metadata details
print()
print("=== GGUF metadata ===")
stdin, stdout, stderr = ssh.exec_command(
    "python3 -c \""
    "from gguf import GGUFReader; "
    "r = GGUFReader('/home/kai/lumilearn/deploy_gguf/lumilearn-v5-f32.gguf'); "
    "for k in sorted(r.fields.keys()): "
    "    print(f'{k}: {r.fields[k].parts[r.fields[k].types[0]]}')"
    "\" 2>&1 | head -40",
    timeout=30
)
print(stdout.read().decode().strip())

ssh.close()