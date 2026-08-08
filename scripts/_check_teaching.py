#!/usr/bin/env python3
"""检查 teaching_data_final.json 为何解析失败"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

path = r"e:\学习LLM\开发者学习\06-题库与考试\teaching_data_final.json"
with open(path, 'rb') as f:
    raw = f.read()

# 检查编码
print(f"文件大小: {len(raw)} 字节")
print(f"前3字节(BOM检测): {raw[:3].hex()}")

# 尝试不同编码读取前几行
for enc in ['utf-8', 'utf-8-sig', 'gbk', 'gb18030']:
    try:
        text = raw.decode(enc)
        lines = text.split('\n')
        json_count = sum(1 for l in lines if l.strip().startswith('{'))
        print(f"{enc}: 解码OK, {len(lines)} 行, JSON开头行: {json_count}")
        if json_count > 0:
            # 尝试解析第一个 JSON
            for l in lines:
                l = l.strip()
                if l.startswith('{'):
                    try:
                        d = json.loads(l)
                        print(f"  首条解析OK: keys={list(d.keys())}")
                    except Exception as e:
                        print(f"  首条解析失败: {e}")
                        print(f"  内容: {l[:200]!r}")
                    break
        break
    except Exception as e:
        print(f"{enc}: 解码失败 {e}")
