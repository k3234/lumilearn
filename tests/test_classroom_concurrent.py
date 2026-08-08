#!/usr/bin/env python3
"""课堂模式多学生并发测试"""
import sys, os, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

print("=" * 70)
print("  课堂模式并发测试")
print("=" * 70)

students = [
    {"id": 1, "topic": "用费曼五步法讲解勾股定理"},
    {"id": 2, "topic": "解释化学键中的共价键"},
    {"id": 3, "topic": "牛顿第二定律 F=ma 怎么用"},
]

results = []
lock = threading.Lock()

def make_request(student_id, topic):
    try:
        r = requests.post(
            "http://localhost:5000/api/learn",
            json={"topic": topic, "user_id": student_id},
            timeout=300
        )
        with lock:
            results.append({
                "student_id": student_id,
                "success": r.status_code == 200,
                "elapsed": time.time()
            })
    except Exception as e:
        with lock:
            results.append({"student_id": student_id, "error": str(e), "success": False})

print(f"\n并发提交 {len(students)} 个学习请求...")
print("-" * 70)

threads = []
start_time = time.time()

for s in students:
    t = threading.Thread(target=make_request, args=(s["id"], s["topic"]))
    threads.append(t)
    t.start()

for t in threads:
    t.join(timeout=360)

total_time = time.time() - start_time

print("\n请求结果:")
for r in results:
    status = "✅" if r.get("success") else "❌"
    print(f"   {status} 学生#{r['student_id']}: {r.get('elapsed', 0):.1f}s")

success_count = sum(1 for r in results if r.get("success"))
print(f"\n   成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.0f}%)")
print(f"   总耗时: {total_time:.1f}s")

if success_count == len(results):
    print("\n   🎉 课堂模式并发测试通过")
else:
    print("\n   ⚠️ 部分请求失败")
