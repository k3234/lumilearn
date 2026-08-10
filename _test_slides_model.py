# -*- coding: utf-8 -*-
"""测试天虹 Ollama lumilearn-v2 对 slides prompt 的实际输出"""
import requests, json

BASE = "http://192.168.2.xx:11434"
MODEL = "lumilearn-v2:latest"

prompt = (
    "你是 LumiLearn 的教学幻灯片生成助手。请为学习主题「牛顿第二定律」生成 5 页教学幻灯片。\n"
    "要求：内容详细，每页给出关键要点；内容面向高中生，准确、有条理；"
    "第 1 页介绍概念，中间页讲原理/推导/应用，最后一页总结与思考。\n\n"
    "必须严格按以下格式输出（每页固定两行，用 PAGE| 开头）：\n"
    "PAGE|标题|副标题\n"
    "第一行内容\n"
    "第二行内容\n"
    "PAGE|标题2|副标题2\n"
    "...\n\n"
    "不要输出任何其他文字或代码块标记。"
)

messages = [
    {"role": "system", "content": "你是教学幻灯片生成助手，严格按指定格式输出。"},
    {"role": "user", "content": prompt},
]

resp = requests.post(f"{BASE}/api/chat", json={
    "model": MODEL,
    "messages": messages,
    "stream": False,
    "options": {"temperature": 0.7, "num_predict": 2048}
}, timeout=300)

print("HTTP:", resp.status_code)
if resp.status_code == 200:
    content = resp.json().get("message", {}).get("content", "")
    print("输出长度:", len(content))
    print("--- 输出前 1200 字 ---")
    print(content[:1200])
    print("---")
    print("PAGE| 出现次数:", content.count("PAGE|"))
else:
    print(resp.text[:500])
