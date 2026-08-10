#!/usr/bin/env python3
"""
LumiLearn 综合训练数据合并脚本
将大模型生成的 SFT 数据（DeepSeek/GLM/Qwen）与现有模板数据、真实数据合并，
生成统一的综合训练集。
"""
import json
import os
import random
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent
DATA_DIR = SCRIPT_DIR / "data"
SFT_DIR = Path("<your-data-root>/LMM-Edu-Training-01/data/sft")

# 学科映射：SFT subject -> LumiLearn subject
SUBJECT_MAP = {
    "小学数学": "数学", "初中数学": "数学", "高中数学": "数学", "数学": "数学",
    "初中物理": "物理", "高中物理": "物理", "物理": "物理", "通用常识": "综合",
    "初中化学": "化学", "高中化学": "化学", "化学": "化学",
    "初中生物": "生物", "高中生物": "生物", "生物": "生物",
    "小学语文": "语文", "初中语文": "语文", "高中语文": "语文", "语文": "语文",
    "小学英语": "英语", "初中英语": "英语", "高中英语": "英语", "英语": "英语",
    "初中历史": "历史", "高中历史": "历史", "历史": "历史",
    "代码编程": "编程", "指令跟随": "综合", "逻辑推理": "综合",
}

# 难度映射
DIFF_MAP = {"easy": "基础", "medium": "进阶", "hard": "困难", "困难": "综合"}


def load_sft_records():
    """加载 SFT 数据，转换为 LumiLearn record 格式"""
    records = []
    if not SFT_DIR.exists():
        print(f"[跳过] SFT 目录不存在: {SFT_DIR}")
        return records

    for fn in sorted(SFT_DIR.glob("*.jsonl")):
        if fn.name == "ALL_MERGED.jsonl":
            continue  # ALL_MERGED 是其他文件的汇总，避免重复
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
                subject = SUBJECT_MAP.get(d.get("subject", ""), "综合")
                diff = DIFF_MAP.get(d.get("difficulty", ""), "进阶")
                records.append({
                    "subject": subject,
                    "chapter": d.get("subject", "综合"),
                    "difficulty": diff,
                    "type": "sft",
                    "content": f"问：{prompt}\n答：{answer}",
                    "source": d.get("source_model", "cloud-llm"),
                })
    return records


def load_template_records():
    """加载现有模板数据"""
    records = []
    path = DATA_DIR / "training_corpus.jsonl"
    if not path.exists():
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            d["source"] = d.get("source", "template")
            records.append(d)
    return records


def load_real_records():
    """加载真实数据"""
    records = []
    path = DATA_DIR / "db_export.jsonl"
    if not path.exists():
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            # db_export 格式: subject/chapter/title/content
            title = d.get("title", "")
            content = d.get("content", "")
            records.append({
                "subject": d.get("subject", "综合"),
                "chapter": d.get("chapter", title),
                "difficulty": d.get("difficulty", "进阶"),
                "type": "real",
                "content": content,
                "source": d.get("source", "db"),
            })
    return records


def main():
    random.seed(42)

    sft = load_sft_records()
    tmpl = load_template_records()
    real = load_real_records()

    print(f"SFT 数据: {len(sft)} 条")
    print(f"模板数据: {len(tmpl)} 条")
    print(f"真实数据: {len(real)} 条")

    # 去重（按完整 content，避免模板前缀相同导致的误删）
    seen = set()
    merged = []
    for rec in sft + tmpl + real:
        key = rec["content"]
        if key in seen:
            continue
        seen.add(key)
        merged.append(rec)

    random.shuffle(merged)

    out_path = DATA_DIR / "merged_corpus.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in merged:
            # 去掉内部 source 字段中可能含的敏感信息，保留元数据
            out = {k: v for k, v in rec.items() if k != "source"}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    print(f"\n合并后总计: {len(merged)} 条 (去重后)")
    print(f"保存到: {out_path} ({out_path.stat().st_size/1024:.0f}KB)")

    # 统计学科分布
    dist = {}
    for rec in merged:
        dist[rec["subject"]] = dist.get(rec["subject"], 0) + 1
    print("\n学科分布:")
    for subj, cnt in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"  {subj}: {cnt}")


if __name__ == "__main__":
    main()
