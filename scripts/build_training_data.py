#!/usr/bin/env python3
"""
LumiLearn 真实高质量训练数据构建脚本
整合本地所有真实教学数据源，构建高质量 SFT 训练集。

数据源：
1. LMM-Edu-Training-01/data/sft/*.jsonl  — 云端 LLM 生成的高质量问答（题目+详解）
2. lumilearn_clone/lumilearn_master.csv   — 真实高一知识点数据（人教A版）
3. 知识点深度解析.md                        — 数学深度解析（按章节拆分）
4. teaching_data_final.json               — 四段式教学数据

输出：data/distil/train_data_high_quality.jsonl (instruction/response 格式)
"""
import json
import os
import random
import re
import sys
import csv
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(r"<your-data-root>")
OUT_DIR = Path(r"<project-root>\data\distil")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 学科映射（统一到 LumiLearn 学科体系）
SUBJECT_MAP = {
    "数学": "数学", "数学推理": "数学", "初中数学": "数学", "高中数学": "数学",
    "物理": "物理", "初中物理": "物理", "高中物理": "物理",
    "化学": "化学", "初中化学": "化学", "高中化学": "化学",
    "生物": "生物", "初中生物": "生物", "高中生物": "生物",
    "语文": "语文", "初中语文": "语文", "高中语文": "语文",
    "英语": "英语", "初中英语": "英语", "高中英语": "英语",
    "历史": "历史", "初中历史": "历史", "高中历史": "历史",
    "政治": "政治", "地理": "地理",
    "代码编程": "编程", "编程": "编程", "AI模型开发": "编程",
    "通用常识": "综合", "指令跟随": "综合", "逻辑推理": "综合",
    "教育问答": "综合", "知识问答": "综合", "长文本问答": "综合",
}

# CSV 知识点 → 多样化的教学指令模板（同一真实内容，不同问法）
CSV_INSTRUCTION_TEMPLATES = [
    "请讲解一下{title}（{chapter}）的相关知识。",
    "老师你好，请问{title}是什么？请详细解释。",
    "请用通俗易懂的方式介绍{title}这个概念。",
    "考试中遇到{title}的题目应该怎么思考？请讲解这个知识点。",
    "请帮我复习{title}，把它的核心要点讲清楚。",
]

# 深度解析 md 的章节指令
MD_INSTRUCTION_TEMPLATES = [
    "请详细讲解{title}，把重点和难点都说清楚。",
    "帮我梳理{title}的知识点，要全面一些。",
    "请介绍{title}的核心概念和要点。",
]


def load_sft_records():
    """加载 LMM-Edu-Training-01 的高质量 SFT 数据"""
    records = []
    sft_dir = ROOT / "LMM-Edu-Training-01" / "data" / "sft"
    if not sft_dir.exists():
        print(f"[跳过] SFT 目录不存在: {sft_dir}")
        return records

    for fn in sorted(sft_dir.glob("*.jsonl")):
        if fn.name == "ALL_MERGED.jsonl":
            continue  # 汇总文件，避免重复
        n = 0
        with open(fn, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                prompt = d.get("prompt", "").strip()
                answer = d.get("answer", "").strip()
                if not prompt or not answer:
                    continue
                # 过滤过短回答（高质量数据要求有实质内容）
                if len(answer) < 100:
                    continue
                subject = SUBJECT_MAP.get(d.get("subject", ""), "综合")
                records.append({
                    "instruction": prompt,
                    "response": answer,
                    "subject": subject,
                    "topic": d.get("subject", prompt[:20]),
                    "source": f"sft:{fn.stem}",
                })
                n += 1
        if n:
            print(f"  SFT {fn.name}: {n} 条")
    return records


def load_csv_records():
    """加载 lumilearn_master.csv 的真实知识点数据（指令多样化扩充）"""
    records = []
    csv_path = ROOT / "lumilearn_clone" / "lumilearn_master.csv"
    if not csv_path.exists():
        print(f"[跳过] CSV 不存在: {csv_path}")
        return records

    rows = []
    with open(csv_path, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    print(f"  CSV 总行数: {len(rows)}")

    for r in rows:
        title = (r.get("title") or "").strip()
        content = (r.get("content") or "").strip()
        chapter = (r.get("chapter") or "").strip()
        subject_raw = (r.get("subject") or "").strip()
        subject = SUBJECT_MAP.get(subject_raw, "综合")
        if not title or not content or len(content) < 60:
            continue
        # 非教育学科（如 AI 模型开发）只保留 1 种问法，控制比例
        templates = CSV_INSTRUCTION_TEMPLATES
        if subject_raw not in ("数学", "物理", "化学", "生物", "语文", "英语", "历史", "政治", "地理"):
            templates = templates[:1]
        # 同一真实知识点，用不同教学问法构造多条（指令多样化）
        for tpl in templates:
            instruction = tpl.format(title=title, chapter=chapter)
            records.append({
                "instruction": instruction,
                "response": content,
                "subject": subject,
                "topic": title,
                "source": "csv:master",
            })
    print(f"  CSV 知识点（多样化后）: {len(rows)} 主题 -> {len(records)} 条")
    return records


def load_md_records():
    """解析 知识点深度解析.md，按章节拆分"""
    records = []
    md_path = ROOT / "开发者学习" / "13-教学演示" / "study-dev" / "教学演示系统" / "知识点深度解析.md"
    if not md_path.exists():
        print(f"[跳过] md 不存在: {md_path}")
        return records

    text = md_path.read_text(encoding="utf-8")
    # 按 "## " 二级标题分节
    sections = re.split(r"\n## ", text)
    for sec in sections[1:]:
        lines = sec.strip().split("\n")
        title = lines[0].strip().replace("#", "").strip()
        body = "\n".join(lines[1:]).strip()
        if len(body) < 100:
            continue
        for tpl in MD_INSTRUCTION_TEMPLATES:
            records.append({
                "instruction": tpl.format(title=title),
                "response": body,
                "subject": "数学" if "数学" in title else "综合",
                "topic": title,
                "source": "md:deep_dive",
            })
    print(f"  MD 深度解析章节: {len(records)} 条")
    return records


def load_teaching_records():
    """加载 teaching_data_final.json 的四段式教学数据（多行 JSON 对象）"""
    records = []
    path = ROOT / "开发者学习" / "06-题库与考试" / "teaching_data_final.json"
    if not path.exists():
        return records
    text = path.read_text(encoding="utf-8", errors="replace")
    # 用花括号配对提取完整 JSON 对象
    objects = []
    depth = 0
    buf = []
    in_str = False
    for ch in text:
        if ch == '"' and (not buf or buf[-1] != '\\'):
            in_str = not in_str
        if not in_str:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
        buf.append(ch)
        if depth == 0 and buf and buf[0] == '{':
            try:
                objects.append(json.loads("".join(buf)))
            except json.JSONDecodeError:
                pass
            buf = []
    print(f"  teaching_data_final: 提取 {len(objects)} 个 JSON 对象")

    n = 0
    for d in objects:
        query = (d.get("user_query") or "").strip()
        answer = (d.get("deepseek_final") or d.get("claude_raw") or "").strip()
        if not query or not answer:
            continue
        records.append({
            "instruction": f"请讲解这道题：{query}",
            "response": answer,
            "subject": "数学",
            "topic": d.get("knowledge_module", query[:15]),
            "source": "teaching:final",
        })
        n += 1
    print(f"  teaching_data_final: {n} 条有效")
    return records


def main():
    random.seed(42)
    print("=" * 60)
    print("构建真实高质量训练数据")
    print("=" * 60)

    all_records = []
    all_records += load_sft_records()
    all_records += load_csv_records()
    all_records += load_md_records()
    all_records += load_teaching_records()

    print(f"\n原始合计: {len(all_records)} 条")

    # 去重（按 instruction+response 完全去重）
    seen = set()
    merged = []
    for rec in all_records:
        key = rec["instruction"] + "|||" + rec["response"]
        if key in seen:
            continue
        seen.add(key)
        merged.append(rec)

    # 按 subject 统计
    from collections import Counter
    dist = Counter(r["subject"] for r in merged)
    print(f"\n去重后: {len(merged)} 条")
    print("学科分布:")
    for subj, cnt in dist.most_common():
        print(f"  {subj}: {cnt}")

    # 长度统计
    lens = [len(r["response"]) for r in merged]
    print(f"回答长度: min={min(lens)} max={max(lens)} avg={sum(lens)//len(lens)}")

    # 随机打乱（保持学科比例）
    random.shuffle(merged)

    out_path = OUT_DIR / "train_data_high_quality.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in merged:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"\n输出: {out_path} ({out_path.stat().st_size/1024:.0f}KB, {len(merged)} 条)")


if __name__ == "__main__":
    main()
