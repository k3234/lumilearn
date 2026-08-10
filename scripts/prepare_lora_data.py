#!/usr/bin/env python3
"""
将综合数据 merged_corpus.jsonl 转换为 LoRA 训练格式 (instruction/response)
适配远程服务器 train_real.py 的输入格式
"""
import json
import random
from pathlib import Path

DATA_DIR = Path("<project-root>/data")
SRC = DATA_DIR / "merged_corpus.jsonl"
OUT = DATA_DIR / "distil" / "train_data_merged.jsonl"

# 教学模板数据的指令模板（无显式问答时构造）
TEACHING_INSTRUCTIONS = [
    "请讲解{topic}的相关知识。",
    "用通俗易懂的方式解释一下{topic}。",
    "请介绍一下{topic}的核心内容。",
    "请用费曼五步法讲解{topic}。",
    "老师你好，请问{topic}是什么？",
]


def split_qa(content):
    """尝试从 content 拆分问/答，返回 (instruction, response) 或 None"""
    if "问：" in content and "答：" in content:
        q_part, a_part = content.split("答：", 1)
        q = q_part.replace("问：", "", 1).strip()
        return q, a_part.strip()
    return None


def main():
    random.seed(42)
    out_records = []
    qa_count = 0
    teaching_count = 0

    with open(SRC, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            content = rec.get("content", "")
            topic = rec.get("chapter", "该知识点")
            subject = rec.get("subject", "综合")

            # 尝试拆分问答对
            qa = split_qa(content)
            if qa:
                instruction, response = qa
                out_records.append({
                    "instruction": instruction,
                    "response": response,
                    "subject": subject,
                    "topic": topic,
                })
                qa_count += 1
            else:
                # 教学陈述内容：构造指令
                instruction = random.choice(TEACHING_INSTRUCTIONS).format(topic=topic)
                out_records.append({
                    "instruction": instruction,
                    "response": content,
                    "subject": subject,
                    "topic": topic,
                })
                teaching_count += 1

    random.shuffle(out_records)
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in out_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"转换完成: {len(out_records)} 条 (问答 {qa_count} + 教学 {teaching_count})")
    print(f"输出: {OUT} ({OUT.stat().st_size/1024:.0f}KB)")

    # 长度统计（用于确定 max_length）
    import re
    lens = []
    for r in out_records:
        lens.append(len(r["instruction"]) + len(r["response"]))
    print(f"内容长度: min={min(lens)} max={max(lens)} avg={sum(lens)//len(lens)}")


if __name__ == "__main__":
    main()
