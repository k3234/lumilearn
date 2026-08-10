#!/usr/bin/env python3
"""GitHub 代码拉取 + 完整测试套件"""
import subprocess, sys, os, json, requests, time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.chdir(PROJECT_ROOT)

print("=" * 70)
print("  LumiLearn 完整测试套件")
print("=" * 70)

# 1. 拉取 GitHub 最新代码
print("\n【1/6】Git Pull")
print("-" * 70)
r = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True)
has_remote = "github.com" in r.stdout or "origin" in r.stdout
if has_remote:
    r = subprocess.run(["git", "pull", "origin", "master"], capture_output=True, text=True, timeout=30)
    print(r.stdout.strip() if r.stdout else r.stderr.strip())
    pull_ok = r.returncode == 0
    print(f"   结果: {'✅ 已同步' if pull_ok else '⚠️ 拉取失败'}")
else:
    pull_ok = True
    print("   跳过: 未配置 GitHub remote，本地代码已是最新")

# 2. pytest 单元测试
print("\n【2/6】pytest 单元测试")
print("-" * 70)
r = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-q"],
    capture_output=True, text=True, timeout=600
)
print(r.stdout[-800:])
pytest_ok = r.returncode == 0
passed = r.stdout.count(" passed") > 0
print(f"   结果: {'✅ 全部通过' if pytest_ok else '❌ 有失败'}")

# 3. 学生端端到端测试
print("\n【3/6】学生端端到端测试")
print("-" * 70)
r = subprocess.run([sys.executable, "test_student_end.py"], capture_output=True, text=True, timeout=60)
print(r.stdout[-500:])
e2e_ok = "STUDENT END-TO-END TEST PASSED" in r.stdout
print(f"   结果: {'✅ 通过' if e2e_ok else '❌ 失败'}")

# 4. goai_agent 集成测试
print("\n【4/6】goai_agent 集成测试")
print("-" * 70)
sys.path.insert(0, PROJECT_ROOT)
from goai_agent import LumiLearnAgent
agent = LumiLearnAgent(ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"))
status = agent.get_status()
print(f"   模型: {status['model']}")
print(f"   Ollama可用: {'✅' if status['ollama_available'] else '❌'}")
goai_ok = status['ollama_available'] and status['model'] == 'lumilearn-v2'
print(f"   结果: {'✅ 集成正确' if goai_ok else '❌ 集成异常'}")

# 5. Web API 测试
print("\n【5/6】Web API 测试")
print("-" * 70)
try:
    r = requests.get("http://localhost:5000/api/status", timeout=5)
    web_status = r.json()
    print(f"   /api/status: {r.status_code}")
    print(f"   会话数: {web_status.get('sessions_completed', 0)}")
    web_ok = r.status_code == 200
    print(f"   结果: {'✅ Web服务运行中' if web_ok else '❌ Web服务异常'}")
except Exception as e:
    web_ok = False
    print(f"   结果: ❌ 无法连接 ({e})")

# 6. 远程服务器 Ollama 测试
print("\n【6/6】远程服务器 Ollama")
print("-" * 70)
try:
    remote_ok = False
    ollama_host = os.environ.get("OLLAMA_HOST", "localhost")
    r = requests.post(
        f"http://{ollama_host}:11434/api/generate",
        json={"model": "lumilearn-v2", "prompt": "用一句话解释勾股定理", "stream": False,
              "options": {"temperature": 0.3, "num_predict": 100}},
        timeout=60
    )
    if r.status_code == 200:
        d = r.json()
        resp = d.get("response", "").strip()
        tps = d.get("eval_count", 0) / max(d.get("eval_duration", 1), 1) * 1e9
        remote_ok = len(resp) > 10 and tps > 1
        print(f"   模型注册: ✅ lumilearn-v2 已安装")
        print(f"   推理测试: {'✅' if remote_ok else '❌'} {d.get('eval_count',0)}tok, {tps:.1f} tok/s")
        print(f"   回复预览: {resp[:60]}...")
    else:
        print(f"   HTTP {r.status_code}")
except Exception as e:
    remote_ok = False
    print(f"   结果: ❌ 连接失败 ({e})")

# ─── 汇总 ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  📊 完整测试报告")
print("=" * 70)
results = [
    ("Git Pull", pull_ok),
    ("pytest 单元测试", pytest_ok),
    ("学生端端到端测试", e2e_ok),
    ("goai_agent 集成", goai_ok),
    ("Web API 服务", web_ok),
    ("远程服务器 Ollama 推理", remote_ok),
]

for name, ok in results:
    print(f"   {'✅' if ok else '❌'} {name}")

total = len(results)
passed_count = sum(1 for _, ok in results if ok)
print(f"\n   通过率: {passed_count}/{total} ({passed_count/total*100:.0f}%)")

print(f"\n{'=' * 70}")
if all(ok for _, ok in results):
    print("  🎉 全部测试通过！系统状态健康")
else:
    print("  ⚠️ 部分测试失败，请检查上述结果")
print(f"{'=' * 70}")
