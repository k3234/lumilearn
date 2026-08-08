#!/usr/bin/env python3
"""课堂模式顺序测试（单线程，避免并发超时）"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

print("=" * 70)
print("  课堂模式测试（顺序执行）")
print("=" * 70)

students = [
    {"id": 1, "name": "小明", "topic": "用费曼五步法讲解勾股定理"},
    {"id": 2, "name": "小红", "topic": "解释化学键中的共价键"},
    {"id": 3, "name": "小刚", "topic": "牛顿第二定律 F=ma 怎么用"},
]

results = []
start_time = time.time()

print(f"\n顺序提交 {len(students)} 个学习请求（每请求约 2-4 分钟）...")
print("-" * 70)

for s in students:
    print(f"\n  学生: {s['name']}")
    try:
        t0 = time.time()
        r = requests.post(
            "http://localhost:5000/api/learn",
            json={"topic": s["topic"], "user_id": s["id"]},
            timeout=300
        )
        elapsed = time.time() - t0
        if r.status_code == 200:
            data = r.json()
            steps = data.get("teaching_flow", {})
            completed = steps.get("completed_steps", 0)
            total = steps.get("total_steps", 0)
            mastery = data.get("mastery_assessment", {}).get("level", "N/A")
            results.append({
                "name": s["name"],
                "success": completed == total,
                "steps": f"{completed}/{total}",
                "mastery": mastery,
                "elapsed": elapsed,
            })
            print(f"    ✅ {completed}/{total} 步, 掌握度 {mastery}, {elapsed:.1f}s")
        else:
            results.append({"name": s["name"], "success": False, "error": f"HTTP {r.status_code}"})
            print(f"    ❌ HTTP {r.status_code}")
    except Exception as e:
        results.append({"name": s["name"], "success": False, "error": str(e)})
        print(f"    ❌ {e}")

total_time = time.time() - start_time

print("\n" + "=" * 70)
print("  课堂模式测试汇总")
print("=" * 70)
passed = sum(1 for r in results if r.get("success"))
print(f"   总学生: {len(results)}")
print(f"   成功: {passed}")
print(f"   失败: {len(results) - passed}")
print(f"   总耗时: {total_time:.1f}s (平均 {total_time/len(results):.1f}s/学生)")
print(f"   通过率: {passed / len(results) * 100:.0f}%")

if passed == len(results):
    print("\n   🎉 课堂模式测试通过")
else:
    print("\n   ⚠️ 部分学生请求失败")
