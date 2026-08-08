#!/usr/bin/env python3
"""盘点本地所有可用的真实教学数据源"""
import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')

def count_lines(path):
    try:
        with open(path, encoding='utf-8') as f:
            return sum(1 for l in f if l.strip())
    except Exception:
        return -1

def inspect(path, label):
    if not os.path.exists(path):
        print(f"  {label}: 不存在")
        return 0
    size = os.path.getsize(path)
    n = count_lines(path)
    print(f"  {label}: {size/1024:.0f}KB, {n} 行")
    return n

targets = [
    (r"e:\学习LLM\开发者学习\06-题库与考试", ["teaching_data_final.json", "某市高一九科期中复习资料_标准JSON.json", "某市高一下学期期中九科专项训练_考试难度版.md", "某市高一九科期中复习资料_自学版.md", "某市高一第二学期期中复习资料_难度分级优化版.md"]),
    (r"e:\学习LLM\data", ["math_corpus.jsonl", "schema_v1.0.json"]),
    (r"e:\学习LLM\lumilearn\data", ["training_corpus.jsonl", "merged_corpus.jsonl", "db_export.jsonl"]),
    (r"e:\学习LLM\lumilearn_clone", ["lumilearn_master.csv", "lumilearn_training_corpus.csv", "lumilearn_training_merged.csv", "learning_experience.json"]),
    (r"e:\学习LLM\开发者学习\13-教学演示\study-dev\教学演示系统", ["知识点深度解析.md"]),
]

for dirp, fns in targets:
    print(f"===== {dirp} =====")
    for fn in fns:
        inspect(os.path.join(dirp, fn), fn)

# 查看数学语料样例
print("\n===== math_corpus.jsonl 样例 =====")
try:
    with open(r"e:\学习LLM\data\math_corpus.jsonl", encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 3: break
            d = json.loads(line)
            print(f"  keys={list(d.keys())} | 内容: {str(d)[:200]}")
except Exception as e:
    print(f"  读取失败: {e}")

# 查看 db_export 样例
print("\n===== db_export.jsonl 样例 =====")
try:
    with open(r"e:\学习LLM\lumilearn\data\db_export.jsonl", encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 3: break
            d = json.loads(line)
            c = d.get('content','')
            print(f"  subject={d.get('subject')} | 长度={len(c)} | 内容: {c[:150]}")
except Exception as e:
    print(f"  读取失败: {e}")
