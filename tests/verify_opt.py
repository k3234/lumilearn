import requests, time, json

BASE = "http://127.0.0.1:18081"

print("=" * 60)
print("验证优化效果")
print("=" * 60)

# 1. 健康检查速度（第一次，无缓存）
t0 = time.time()
r = requests.get(f"{BASE}/health", timeout=5)
latency1 = time.time() - t0
print(f"[1] HEALTH 首次: status={r.status_code} time={latency1:.3f}s")
h1 = r.json()
print(f"    gateway={h1.get('gateway','?')}  offline_mode={h1.get('offline_mode')}  status={h1.get('status','?')}")

# 2. 健康检查速度（第二次，应命中30s缓存）
t0 = time.time()
r2 = requests.get(f"{BASE}/health", timeout=5)
latency2 = time.time() - t0
print(f"[2] HEALTH 缓存: status={r2.status_code} time={latency2:.3f}s  cached={r2.json().get('cached', False)}")

# 3. explain 第一次（无缓存）
t0 = time.time()
r3 = requests.post(f"{BASE}/api/feynman/explain", json={"topic": "勾股定理", "level": "junior"}, timeout=30)
latency3 = time.time() - t0
j3 = r3.json()
print(f"[3] EXPLAIN 首次: status={r3.status_code} time={latency3:.3f}s mode={j3.get('mode','?')} model={j3.get('model_used','?')}")
print(f"    fallback_reason={j3.get('fallback_reason','N/A')}")

# 4. explain 第二次（应命中缓存，< 10ms）
t0 = time.time()
r4 = requests.post(f"{BASE}/api/feynman/explain", json={"topic": "勾股定理", "level": "junior"}, timeout=30)
latency4 = time.time() - t0
j4 = r4.json()
print(f"[4] EXPLAIN 缓存: status={r4.status_code} time={latency4:.3f}s cached={j4.get('cached', False)}")

# 5. classroom 测试
t0 = time.time()
r5 = requests.post(f"{BASE}/api/feynman/classroom", json={"topic": "勾股定理", "level": "junior", "max_turns": 3}, timeout=60)
latency5 = time.time() - t0
j5 = r5.json()
print(f"[5] CLASSROOM:    status={r5.status_code} time={latency5:.3f}s")
if r5.status_code == 200:
    print(f"    dialogue_len={len(j5.get('dialogue',[]))}  math_type={j5.get('math_type','?')}")
    # 第二次调用应命中缓存
    t0b = time.time()
    r5b = requests.post(f"{BASE}/api/feynman/classroom", json={"topic": "勾股定理", "level": "junior", "max_turns": 3}, timeout=30)
    print(f"[6] CLASSROOM缓存: status={r5b.status_code} time={time.time()-t0b:.3f}s cached={r5b.json().get('cached', False)}")

print("=" * 60)
print("验证完成")
