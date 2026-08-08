#!/usr/bin/env python3
"""API 压力测试"""
import sys, os, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

print("=" * 70)
print("  API 压力测试")
print("=" * 70)

results = []
lock = threading.Lock()

def make_request(student_id, topic):
    start = time.time()
    try:
        r = requests.post(
            "http://localhost:5000/api/learn",
            json={"topic": topic, "user_id": student_id},
            timeout=300
        )
        elapsed = time.time() - start
        with lock:
            results.append({"student_id": student_id, "status": r.status_code, "elapsed": elapsed, "success": r.status_code == 200})
    except Exception as e:
        elapsed = time.time() - start
        with lock:
            results.append({"student_id": student_id, "error": str(e), "elapsed": elapsed, "success": False})

num_students = 3
topics = ["用费曼五步法讲解勾股定理", "解释共价键的形成过程", "牛顿第二定律的应用例子"]

print(f"\n启动 {num_students} 个并发学生...")
print("-" * 70)

threads = []
start_time = time.time()

for i in range(num_students):
    t = threading.Thread(target=make_request, args=(i + 1, topics[i]))
    threads.append(t)
    t.start()

for t in threads:
    t.join(timeout=360)

total_time = time.time() - start_time

success_count = sum(1 for r in results if r.get("success"))
print(f"\n   成功率: {success_count}/{num_students}")
print(f"   总耗时: {total_time:.1f}s")
print(f"   平均响应: {total_time/num_students:.1f}s/请求")

if success_count == num_students:
    print("\n   🎉 API 压力测试通过")
else:
    print("\n   ⚠️ 部分请求失败")
