#!/usr/bin/env python3
"""检查核心数据源结构"""
import json, sys, csv
sys.stdout.reconfigure(encoding='utf-8')

print("===== 汕头高一九科期中复习资料_标准JSON.json 结构 =====")
try:
    with open(r"e:\学习LLM\开发者学习\06-题库与考试\汕头高一九科期中复习资料_标准JSON.json", encoding='utf-8') as f:
        content = f.read()
    print(f"文件前 100 字符: {content[:100]!r}")
    # 判断是 JSON array 还是 jsonl
    if content.strip().startswith('['):
        d = json.loads(content)
        print(f"JSON Array, 共 {len(d)} 条")
        if d:
            print(f"第一条 keys: {list(d[0].keys())}")
            print(f"第一条: {json.dumps(d[0], ensure_ascii=False)[:300]}")
    else:
        lines = [l for l in content.split('\n') if l.strip()]
        print(f"非数组 JSON 或逐行 JSON, {len(lines)} 行")
        for l in lines[:3]:
            try:
                d = json.loads(l)
                print(f"  keys={list(d.keys())}: {str(d)[:200]}")
            except:
                print(f"  非JSON: {l[:150]}")
except Exception as e:
    print(f"失败: {e}")

print("\n===== lumilearn_master.csv 结构 =====")
try:
    with open(r"e:\学习LLM\lumilearn_clone\lumilearn_master.csv", encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        rows = list(reader)
    print(f"总行数: {len(rows)}")
    print(f"表头: {rows[0] if rows else '无'}")
    for r in rows[1:4]:
        print(f"  {[str(x)[:80] for x in r]}")
except Exception as e:
    print(f"失败: {e}")
