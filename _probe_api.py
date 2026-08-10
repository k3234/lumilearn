# -*- coding: utf-8 -*-
"""批量检测 Framework 各功能 API 是否为占位实现"""
import requests, json

BASE = "http://192.168.2.xx:18080"

tests = [
    ("/api/slides/generate", "POST", {"topic": "光合作用", "slide_count": 5, "style": "detailed"}),
    ("/api/mindmap/generate", "POST", {"topic": "光合作用"}),
    ("/api/chat", "POST", {"messages": [{"role": "user", "content": "什么是光合作用"}]}),
    ("/api/feynman/explain", "POST", {"topic": "光合作用", "model": "lumilearn-v2:latest"}),
    ("/api/animation/health", "GET", None),
    ("/api/animation/generate", "POST", {"topic": "光合作用"}),
]

for path, method, body in tests:
    try:
        if method == "POST":
            r = requests.post(BASE + path, json=body, timeout=120)
        else:
            r = requests.get(BASE + path, timeout=30)
        text = r.text[:300].replace("\n", " ")
        print(f"[{r.status_code}] {method} {path}")
        print(f"    {text}")
    except Exception as e:
        print(f"[ERR] {method} {path}: {type(e).__name__} {str(e)[:150]}")
    print()
