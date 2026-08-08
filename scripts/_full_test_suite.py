#!/usr/bin/env python3
"""完整测试套件：pytest + 端到端 + 手写识别 + API 性能 + 天虹 Ollama"""
import sys, os, time, subprocess, json, requests, paramiko
sys.path.insert(0, r"e:\学习LLM\lumilearn")
os.chdir(r"e:\学习LLM\lumilearn")

print("=" * 70)
print("  LumiLearn 完整测试套件")
print("=" * 70)

all_results = []

# ─── 1. pytest 单元测试 ─────────────────────────────────────────────────────
print("\n【1/6】pytest 单元测试")
print("-" * 70)
r = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-q"],
    capture_output=True, text=True, timeout=600
)
print(r.stdout[-600:])
pytest_ok = r.returncode == 0
all_results.append(("pytest 单元测试", pytest_ok))
print(f"   结果: {'✅ 通过' if pytest_ok else '❌ 失败'}")

# ─── 2. 学生端端到端测试 ────────────────────────────────────────────────────
print("\n【2/6】学生端端到端测试")
print("-" * 70)
r = subprocess.run([sys.executable, "test_student_end.py"], capture_output=True, text=True, timeout=60)
print(r.stdout[-400:])
e2e_ok = "STUDENT END-TO-END TEST PASSED" in r.stdout
all_results.append(("学生端端到端测试", e2e_ok))
print(f"   结果: {'✅ 通过' if e2e_ok else '❌ 失败'}")

# ─── 3. 手写识别流程测试 ────────────────────────────────────────────────────
print("\n【3/6】手写识别流程测试")
print("-" * 70)
r = subprocess.run([sys.executable, "tests/test_handwriting_flow.py"], capture_output=True, text=True, timeout=30)
print(r.stdout[-300:])
hw_ok = "手写识别流程测试通过" in r.stdout
all_results.append(("手写识别流程测试", hw_ok))
print(f"   结果: {'✅ 通过' if hw_ok else '❌ 失败'}")

# ─── 4. goai_agent 集成测试 ─────────────────────────────────────────────────
print("\n【4/6】goai_agent 集成测试")
print("-" * 70)
from goai_agent import LumiLearnAgent
agent = LumiLearnAgent()
status = agent.get_status()
goai_ok = status['ollama_available'] and status['model'] == 'lumilearn-v2'
all_results.append(("goai_agent 集成", goai_ok))
print(f"   模型: {status['model']} | Ollama: {'✅' if status['ollama_available'] else '❌'}")
print(f"   结果: {'✅ 集成正确' if goai_ok else '❌ 集成异常'}")

# ─── 5. Web API 测试 ────────────────────────────────────────────────────────
print("\n【5/6】Web API 测试")
print("-" * 70)
try:
    r = requests.get("http://localhost:5000/api/status", timeout=5)
    web_ok = r.status_code == 200 and r.json().get('ollama_available')
    all_results.append(("Web API 服务", web_ok))
    print(f"   /api/status: {r.status_code} | 会话数: {r.json().get('sessions_completed', 0)}")
    print(f"   结果: {'✅ Web服务运行中' if web_ok else '❌ Web服务异常'}")
except Exception as e:
    all_results.append(("Web API 服务", False))
    print(f"   结果: ❌ 无法连接 ({e})")

# ─── 6. 天虹 Ollama 测试 ─────────────────────────────────────────────────────
print("\n【6/6】天虹 Ollama (192.168.2.68)")
print("-" * 70)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect("192.168.2.68", username="kai", password="WWw2021x", timeout=15)
    def run_ssh(cmd):
        s, out, err = ssh.exec_command(cmd, timeout=30)
        return out.read().decode(errors="replace")
    
    out = run_ssh("ollama list | grep lumilearn-v2")
    model_ok = "lumilearn-v2" in out
    print(f"   模型注册: {'✅' if model_ok else '❌'} {out.strip()}")
    
    # 快速推理测试
    out = run_ssh("curl -s http://localhost:11434/api/generate "
                  "-d '{\"model\":\"lumilearn-v2\",\"prompt\":\"用一句话解释函数\",\"stream\":false,"
                  "\"options\":{\"temperature\":0.3,\"num_predict\":80}}'")
    tianhong_ok = False
    if out:
        try:
            d = json.loads(out)
            resp = d.get("response", "").strip()
            tps = d.get("eval_count", 0) / max(d.get("eval_duration", 1), 1) * 1e9
            tianhong_ok = len(resp) > 10 and tps > 1
            print(f"   推理测试: {'✅' if tianhong_ok else '❌'} {d.get('eval_count',0)}tok, {tps:.1f} tok/s")
        except:
            print("   推理测试: ❌ 解析失败")
    else:
        print("   推理测试: ❌ 无响应")
    
    ssh.close()
except Exception as e:
    tianhong_ok = False
    print(f"   结果: ❌ SSH 连接失败 ({e})")

all_results.append(("天虹 Ollama 推理", tianhong_ok))

# ─── 汇总 ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  📊 完整测试报告")
print("=" * 70)
for name, ok in all_results:
    print(f"   {'✅' if ok else '❌'} {name}")

total = len(all_results)
passed = sum(1 for _, ok in all_results if ok)
print(f"\n   通过率: {passed}/{total} ({passed/total*100:.0f}%)")

print(f"\n{'=' * 70}")
if all(ok for _, ok in all_results):
    print("  🎉 全部测试通过！系统状态健康")
else:
    failed = [name for name, ok in all_results if not ok]
    print(f"  ⚠️ 以下测试失败: {', '.join(failed)}")
print(f"{'=' * 70}")
