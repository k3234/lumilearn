#!/usr/bin/env python3
"""深入分析 lumilearn_master.csv 内容质量"""
import sys, csv
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

rows = []
with open(r"e:\学习LLM\lumilearn_clone\lumilearn_master.csv", encoding='utf-8', errors='replace') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)
print(f"总行数: {len(rows)}")
types = Counter(r.get('type','') for r in rows)
print(f"type 分布: {dict(types)}")
subs = Counter(r.get('subject','') for r in rows)
print(f"subject 分布: {dict(subs)}")
lens = [len(r.get('content','')) for r in rows]
print(f"content 长度: min={min(lens)} max={max(lens)} avg={sum(lens)//max(len(lens),1)}")

# 检查其他字段（deepseek_r1_15b 等可能含模型生成回复）
for col in ['deepseek_r1_15b', 'qwen2_5_7b_p2', 'qwen2_5_7b_p3', 'errors', 'source_type', 'content_format']:
    vals = [r.get(col,'') for r in rows if r.get(col,'')]
    if vals:
        print(f"\n[{col}] 非空 {len(vals)} 条, 平均长度 {sum(len(v) for v in vals)//len(vals)}")
        print(f"  样例: {vals[0][:200]!r}")

print("\n===== 长内容样例 =====")
shown = set()
for r in rows:
    c = r.get('content','')
    if len(c) > 300 and r.get('subject') not in shown:
        shown.add(r.get('subject'))
        print(f"\n[{r.get('subject')}] {r.get('title')} ({r.get('chapter')}) len={len(c)}")
        print(f"  {c[:350]}")
    if len(shown) >= 5:
        break
