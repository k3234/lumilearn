"""Deploy smart_reply_engine to Tianhong + end-to-end verification"""
import paramiko, socket, io, time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(60)
s.connect(('192.168.2.63', 22))
t = paramiko.Transport(s)
t.connect(username='kai', password='WWw2021x')
ssh = paramiko.SSHClient()
ssh._transport = t

print("Step 1: Upload smart_reply_engine.py to Tianhong")

with open('e:\\学习LLM\\lumilearn\\smart_reply_engine.py', 'r', encoding='utf-8') as f:
    engine_code = f.read()

# Write via cat heredoc
cmd = f"""cat > /home/kai/lumilearn/smart_reply_engine.py << 'PYEOF'
{engine_code}
PYEOF
echo "UPLOADED"
"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
out = stdout.read().decode(errors='replace')
err = stderr.read().decode(errors='replace')
print(f"Upload: {out.strip()}")
if err:
    print(f"Warn: {err[:200]}")

print("\nStep 2: Verify inference server health")
stdin, stdout, _ = ssh.exec_command('curl -s http://localhost:18080/health --max-time 5 2>&1', timeout=10)
health = stdout.read().decode(errors='replace')
print(f"Health: {health[:200]}")

if '"status":"ok"' not in health:
    print("Inference server not running, restarting...")
    # Kill old
    ssh.exec_command('pkill -f "inference_server_tianhong" 2>/dev/null', timeout=5)
    time.sleep(2)

    channel = ssh.invoke_shell()
    channel.settimeout(15)
    time.sleep(0.5)
    try:
        channel.recv(8192)
    except:
        pass
    cmd = (
        'export PATH=/usr/bin:/bin:/usr/local/bin:$PATH\n'
        'cd /home/kai/lumilearn\n'
        '/usr/bin/nohup /usr/bin/python3 inference_server_tianhong.py --port 18080 '
        '> /home/kai/lumilearn/inference_server.log 2>&1 &\n'
        'disown\n'
        'echo RESTARTED\n'
    )
    channel.send(cmd)
    time.sleep(3)
    channel.close()
    time.sleep(12)

    stdin, stdout, _ = ssh.exec_command('curl -s http://localhost:18080/health --max-time 5 2>&1', timeout=10)
    health = stdout.read().decode(errors='replace')
    print(f"After restart: {health[:200]}")

print("\nStep 3: Run smart_reply_engine test on Tianhong")

test_script = r'''
import sys, os
sys.path.insert(0, "/home/kai/lumilearn")
os.chdir("/home/kai/lumilearn")

from smart_reply_engine import LiveTutor, is_gibberish, classify_question

print("=== Smart Reply Engine on Tianhong ===")
tutor = LiveTutor(api_base="http://localhost:18080")

tests = [
    "你好小澍",
    "1加1等于几",
    "三角形面积公式是什么",
    "英语谢谢怎么说",
    "作文怎么写",
    "怎么制定学习计划",
    "记不住单词怎么办",
    "什么是质数",
    "物理题怎么做",
    "加油支持你",
    "推荐几本书",
    "不想学了",
]

ok = 0
for q in tests:
    qtype = classify_question(q)
    reply = tutor.respond(q)
    is_gib = is_gibberish(reply)
    status = "OK" if not is_gib and len(reply) > 5 else "BAD"
    if status == "OK":
        ok += 1
    print(f"[{status}] {q} ({qtype})")
    print(f"  -> {reply[:100]}")

print(f"\nResult: {ok}/{len(tests)} OK")
print("DEPLOY_SUCCESS" if ok >= 10 else "ISSUES_FOUND")
'''

import io
sf = paramiko.SFTPClient.from_transport(t)
sf.putfo(io.BytesIO(test_script.encode()), '/home/kai/lumilearn/test_smart_reply_tianhong.py')
sf.close()

stdin, stdout, stderr = ssh.exec_command(
    '/usr/bin/python3 /home/kai/lumilearn/test_smart_reply_tianhong.py 2>&1',
    timeout=120
)
out = stdout.read().decode(errors='replace')
err = stderr.read().decode(errors='replace')
print(out[:5000])
if err:
    print("STDERR:", err[:1000])

if "DEPLOY_SUCCESS" in out:
    print("\n" + "=" * 60)
    print("  🌿 LumiLearn 直播助手部署成功！")
    print()
    print("  推理服务器: http://192.168.2.63:18080")
    print("  智能引擎:   /home/kai/lumilearn/smart_reply_engine.py")
    print()
    print("  本地启动直播助手:")
    print("    cd e:\\学习LLM\\lumilearn")
    print("    python live_anchor.py --source mock")
    print()
    print("  OBS 叠加层:")
    print("    浏览器源 URL: http://localhost:8765")
    print("    宽高: 460 x 700")
    print("=" * 60)
else:
    print("\nDeploy has issues, but check individual results above")

t.close()