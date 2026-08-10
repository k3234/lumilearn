# -*- coding: utf-8 -*-
"""端到端回归验证所有 Framework 功能 API"""
import requests, json, time

BASE = "http://192.168.2.xx:18080"

def t(name, method, path, body=None, timeout=180):
    t0 = time.time()
    try:
        if method == "POST":
            r = requests.post(BASE + path, json=body, timeout=timeout)
        else:
            r = requests.get(BASE + path, timeout=30)
        dt = round(time.time() - t0, 1)
        text = r.text[:220].replace("\n", " ")
        print(f"[{r.status_code}] {name} ({dt}s)")
        print(f"    {text}")
        return r
    except Exception as e:
        print(f"[ERR] {name}: {type(e).__name__} {str(e)[:120]}")
        return None

print("=== 幻灯片生成（任意主题）===")
r = t("生成光合作用幻灯片", "POST", "/api/slides/generate", {"topic": "光合作用", "slide_count": 5, "style": "detailed"})
if r:
    d = r.json()
    print(f"    slides数={d.get('count')} model={d.get('model_used')}")
    for s in d.get("slides", [])[:5]:
        print(f"      - {s.get('title')} | {s.get('subtitle')} | content={len(s.get('content',''))}字符")

print()
print("=== 思维导图生成 ===")
r = t("生成光合作用导图", "POST", "/api/mindmap/generate", {"topic": "光合作用"})
if r:
    d = r.json()
    mm = d.get("mindmap", {})
    print(f"    nodes={len(mm.get('nodes', []))} edges={len(mm.get('edges', []))} model={d.get('model_used')}")

print()
print("=== 聊天（默认模型应为 lumilearn-v2，非流式）===")
r = t("聊天", "POST", "/api/chat", {"messages": [{"role": "user", "content": "一句话介绍光合作用"}], "stream": False}, timeout=120)
if r:
    try:
        d = r.json()
        print(f"    model={d.get('model')} 回复={str(d.get('message', {}).get('content', ''))[:80]}")
    except Exception as e:
        print(f"    解析失败: {e}")

print()
print("=== 费曼（默认模型应为 lumilearn-v2）===")
r = t("费曼讲解", "POST", "/api/feynman/explain", {"topic": "勾股定理", "level": "junior"}, timeout=180)
if r:
    d = r.json()
    print(f"    model_used={d.get('model_used')} steps={len(d.get('steps', []))}")

print()
print("=== 动画 health ===")
r = t("动画健康检查", "GET", "/api/animation/health")
if r:
    print(f"    {r.json()}")

print()
print("=== 管理员登录 ===")
r = t("管理员登录", "POST", "/api/admin/login", {"username": "admin", "password": "admin123"}, timeout=30)
if r:
    d = r.json()
    print(f"    token={'有' if d.get('token') else '无'}")

print()
print("=== 健康检查 ===")
r = t("health", "GET", "/health")
if r:
    d = r.json()
    print(f"    status={d.get('status')} default_model={d.get('default_model')} models={d.get('models')}")
