"""验证 LUMILEARN_OFFLINE 环境开关对 /health 的影响"""
import requests, time

BASE = "http://127.0.0.1:18081"

# 直接调用 /health，检查返回结果中是否包含 offline_mode 字段
r = requests.get(f"{BASE}/health", timeout=5)
j = r.json()
print(f"STATUS: {r.status_code}")
print(f"BODY: {j}")
print(f"GATEWAY: {j.get('gateway','?')}")
print(f"OFFLINE_MODE: {j.get('offline_mode')}")
