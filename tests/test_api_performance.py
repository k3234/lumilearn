#!/usr/bin/env python3
"""API 顺序性能测试（替代并发测试）"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

print("=" * 70)
print("  API 性能测试（顺序执行）")
print("=" * 70)

topics = [
    "用费曼五步法讲解勾股定理",
    "解释共价键的形成过程",
    "牛顿第二定律的应用例子",
]

results = []
start_time = time.time()

print(f"\n顺序提交 {len(topics)} 个请求...")
print("-" * 70)

for i, topic in enumerate(topics, 1):
    print(f"\n  [{i}/{len(topics)}] {topic}")
    try:
        t0 = time.time()
        r = requests.post(
            "http://localhost:5000/api/learn",
            json={"topic": topic, "user_id": i},
            timeout=300
        )
        elapsed = time.time() - t0
        if r.status_code == 200:
            data = r.json()
            steps = data.get("teaching_flow", {})
            completed = steps.get("completed_steps", 0)
            mastery = data.get("mastery_assessment", {}).get("level", "N/A")
            results.append({
                "topic": topic,
                "success": completed == steps.get("total_steps", 0),
                "elapsed": elapsed,
                "mastery": mastery,
            })
            print(f"    ✅ {elapsed:.1f}s, 掌握度 {mastery}")
        else:
            results.append({"topic": topic, "success": False, "error": f"HTTP {r.status_code}"})
            print(f"    ❌ HTTP {r.status_code}")
    except Exception as e:
        results.append({"topic": topic, "success": False, "error": str(e)})
        print(f"    ❌ {e}")

total_time = time.time() - start_time

print("\n" + "=" * 70)
print("  API 性能测试汇总")
print("=" * 70)
passed = sum(1 for r in results if r.get("success"))
print(f"   总请求: {len(results)}")
print(f"   成功: {passed}")
print(f"   失败: {len(results) - passed}")
print(f"   总耗时: {total_time:.1f}s")
print(f"   平均耗时: {sum(r['elapsed'] for r in results if 'elapsed' in r) / passed:.1f}s/请求")
print(f"   成功率: {passed / len(results) * 100:.0f}%")

if passed == len(results):
    print("\n   🎉 API 性能测试通过")
else:
    print("\n   ⚠️ 部分请求失败")
