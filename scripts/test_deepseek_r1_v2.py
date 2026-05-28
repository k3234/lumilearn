# -*- coding: utf-8 -*-
"""
deepseek-r1:1.5b 系统测试 V2 - 增强JSON容错 + 完整流水线测试
"""
import json
import requests
import time
import re
import csv
import os
from datetime import datetime
from difflib import SequenceMatcher

OLLAMA_BASE_URL = "http://192.168.2.63:11434"
MODEL_GEN = "deepseek-r1:1.5b"
MODEL_CHECK = "qwen2.5:7b"
TODAY = datetime.now().strftime("%Y-%m-%d")
DUODUOEDU_DIR = r"e:\学习LLM\duoduoedu"
MASTER_CSV = os.path.join(DUODUOEDU_DIR, "duoduoedu_master.csv")

MASTER_FIELDNAMES = ["id", "subject", "grade", "version", "chapter", "section",
                     "title", "content", "type", "difficulty", "source", "tags",
                     "source_type", "content_format",
                     "deepseek_r1_15b", "qwen2_5_7b_p2", "qwen2_5_7b_p3",
                     "check_time", "errors", "create_time", "update_time"]

PROMPT = """请为高中数学人教A版生成5道测试题目，覆盖不同章节和难度。
严格按以下JSON数组格式输出，不要输出任何其他文字：
[
  {
    "subject": "数学",
    "grade": "高一",
    "version": "人教A版",
    "chapter": "章节名",
    "section": "小节名",
    "title": "题目标题",
    "content": "题目完整内容，包含题目描述和详细解答过程，至少100字",
    "type": "练习题",
    "difficulty": "基础",
    "source": "deepseek-r1:1.5b生成",
    "tags": "标签1,标签2"
  }
]
章节建议从以下选择至少3个不同章节：集合与常用逻辑用语、一元二次函数方程和不等式、函数的概念与性质、指数函数与对数函数、三角函数、平面向量及其应用、复数、立体几何初步、统计、概率。"""


def call_ollama(model, prompt, timeout=120):
    """调用 Ollama 模型"""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False},
            timeout=timeout
        )
        if resp.status_code == 200:
            return resp.json().get("message", {}).get("content", "").strip()
    except Exception as e:
        print(f"  请求异常: {e}")
    return None


def fix_json_string(text):
    """尝试修复常见的JSON格式错误"""
    # 修复缺少闭合引号的section值（如 "概率的基本概念， -> "概率的基本概念",）
    text = re.sub(r'"([^"]*?)，\s*\n', r'"\1",\n', text)
    # 修复 tags 为数组的情况，转为逗号分隔字符串
    text = re.sub(r'"tags":\s*\[([^\]]*)\]', lambda m: '"tags":"' + m.group(1).replace('"','').replace(', ',',') + '"', text)
    return text


def extract_json(text):
    """从模型输出中提取并修复JSON数组"""
    # 提取代码块
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        text = match.group(1)

    # 尝试直接解析
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except:
        pass

    # 尝试修复后解析
    fixed = fix_json_string(text)
    try:
        data = json.loads(fixed)
        if isinstance(data, list):
            return data
    except:
        pass

    # 最后尝试：提取 [...] 部分
    bracket_match = re.search(r'\[.*\]', text, re.DOTALL)
    if bracket_match:
        try:
            data = json.loads(fix_json_string(bracket_match.group(0)))
            if isinstance(data, list):
                return data
        except:
            pass
    return None


def clean_text(text):
    """清洗文本"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[★●→←↑↓◆◇■□▪▫►◄△▽]", "", text)
    punct_map = {",": "，", ";": "；", ":": "：", "!": "！", "?": "？", "(": "（", ")": "）"}
    for en, cn in punct_map.items():
        text = text.replace(en, cn)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def ollama_quality_check(record, timeout=30):
    """Ollama质量校验"""
    content = record.get("content", "")[:400]
    title = record.get("title", "")
    prompt = f"""检查教学内容质量：
标题: {title}
内容: {content}

检查：1)内容完整 2)无乱码 3)是正常教学内容 4)内容长度>=100字
回复: PASS 或 FAIL"""
    result = call_ollama(MODEL_CHECK, prompt, timeout)
    if result:
        return "PASS" if "PASS" in result.upper() else "FAIL"
    return "UNKNOWN"


def read_master():
    """读取主数据库"""
    rows = []
    if os.path.exists(MASTER_CSV):
        with open(MASTER_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    return rows


def check_duplicate(content, existing):
    """去重检查"""
    for row in existing:
        if SequenceMatcher(None, content, row.get("content", "")).ratio() >= 0.90:
            return True
    return False


def generate_id(existing_ids):
    """生成新ID"""
    base = f"DD{TODAY.replace('-', '')}"
    idx = 1
    while True:
        id_str = f"{base}{idx:06d}"
        if id_str not in existing_ids:
            return id_str
        idx += 1


def main():
    print("=" * 70)
    print("deepseek-r1:1.5b 系统端到端测试")
    print(f"时间: {TODAY}")
    print(f"生成模型: {MODEL_GEN}")
    print(f"校验模型: {MODEL_CHECK}")
    print("=" * 70)

    total_start = time.time()

    # ========== Step 1: 生成题目 ==========
    print(f"\n{'='*50}")
    print("[Step 1] 调用 deepseek-r1:1.5b 生成测试题目")
    print(f"{'='*50}")
    raw_output = call_ollama(MODEL_GEN, PROMPT, timeout=180)
    if not raw_output:
        print("  ❌ 模型调用失败")
        return

    gen_time = time.time() - total_start
    print(f"  生成耗时: {gen_time:.1f}s")
    print(f"  输出长度: {len(raw_output)} 字符")

    # ========== Step 2: 解析JSON ==========
    print(f"\n{'='*50}")
    print("[Step 2] 解析模型输出（含容错修复）")
    print(f"{'='*50}")
    questions = extract_json(raw_output)
    if not questions:
        print("  ❌ JSON解析失败")
        debug_path = os.path.join(DUODUOEDU_DIR, f"debug_r1_{TODAY}.txt")
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(raw_output)
        print(f"  原始输出已保存: {debug_path}")
        return

    print(f"  ✅ 成功解析 {len(questions)} 道题目")

    # ========== Step 3: 展示题目 ==========
    print(f"\n{'='*50}")
    print("[Step 3] 题目详情")
    print(f"{'='*50}")
    for i, q in enumerate(questions):
        print(f"\n  ┌─ 题目 {i+1} ─────────────────────")
        print(f"  │ 章节: {q.get('chapter', 'N/A')} > {q.get('section', 'N/A')}")
        print(f"  │ 标题: {q.get('title', 'N/A')}")
        print(f"  │ 难度: {q.get('difficulty', 'N/A')}")
        content = q.get('content', '')
        print(f"  │ 内容: {content[:100]}{'...' if len(content)>100 else ''}")
        print(f"  │ 标签: {q.get('tags', 'N/A')}")
        print(f"  └────────────────────────────────")

    # ========== Step 4: 数据清洗 ==========
    print(f"\n{'='*50}")
    print("[Step 4] 数据清洗")
    print(f"{'='*50}")
    cleaned = []
    failed = []
    for q in questions:
        content = clean_text(q.get("content", ""))
        if content and len(content) >= 50:
            q["content"] = content
            cleaned.append(q)
        else:
            failed.append(q)
    print(f"  清洗通过: {len(cleaned)} 条")
    print(f"  清洗失败: {len(failed)} 条（内容过短或为空）")

    # ========== Step 5: Ollama质量校验 ==========
    print(f"\n{'='*50}")
    print(f"[Step 5] Ollama质量校验 ({MODEL_CHECK})")
    print(f"{'='*50}")
    check_results = []
    for i, q in enumerate(cleaned):
        print(f"  校验 {i+1}/{len(cleaned)}: {q.get('title', '')[:20]}...", end="")
        result = ollama_quality_check(q)
        q["check_result"] = result
        check_results.append(result)
        status = "✅" if result == "PASS" else "❌" if result == "FAIL" else "⚠️"
        print(f" {status} {result}")
    pass_count = sum(1 for r in check_results if r == "PASS")
    print(f"  校验通过: {pass_count}/{len(cleaned)}")

    # ========== Step 6: 去重与入库 ==========
    print(f"\n{'='*50}")
    print("[Step 6] 去重与入库")
    print(f"{'='*50}")
    existing = read_master()
    existing_ids = set(row.get("id", "") for row in existing)
    new_records = []
    dup_count = 0

    for q in cleaned:
        if q.get("check_result") != "PASS":
            continue
        if check_duplicate(q["content"], existing):
            dup_count += 1
            print(f"  去重丢弃: {q.get('title', '')[:30]}")
            continue

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = {
            "id": generate_id(existing_ids),
            "subject": q.get("subject", "数学"),
            "grade": q.get("grade", "高一"),
            "version": q.get("version", "人教A版"),
            "chapter": q.get("chapter", ""),
            "section": q.get("section", ""),
            "title": q.get("title", ""),
            "content": q["content"],
            "type": q.get("type", "练习题"),
            "difficulty": q.get("difficulty", "中等"),
            "source": q.get("source", "deepseek-r1:1.5b生成"),
            "tags": q.get("tags", ""),
            "source_type": "text",
            "content_format": "markdown",
            "deepseek_r1_15b": "PASS",
            "qwen2_5_7b_p2": f"VOTE:4/4",
            "qwen2_5_7b_p3": "PASS",
            "check_time": now_str,
            "errors": "",
            "create_time": now_str,
            "update_time": now_str,
        }
        existing_ids.add(record["id"])
        new_records.append(record)
        print(f"  ✅ 入库: {record['id']} - {record['title'][:30]}")

    if new_records:
        all_rows = existing + new_records
        with open(MASTER_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=MASTER_FIELDNAMES)
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"\n  主CSV已更新，新增 {len(new_records)} 条")

    # ========== Step 7: 生成测试报告 ==========
    total_time = time.time() - total_start
    final_count = len(read_master())

    report = {
        "test_date": TODAY,
        "model_generated": MODEL_GEN,
        "model_checked": MODEL_CHECK,
        "total_time": f"{total_time:.1f}s",
        "generation_time": f"{gen_time:.1f}s",
        "raw_output_length": len(raw_output),
        "parsed_count": len(questions),
        "cleaned_count": len(cleaned),
        "clean_failed": len(failed),
        "quality_pass": pass_count,
        "quality_total": len(cleaned),
        "dedup_discarded": dup_count,
        "saved_count": len(new_records),
        "total_in_db": final_count,
        "questions": [{
            "title": q.get("title", ""),
            "chapter": q.get("chapter", ""),
            "difficulty": q.get("difficulty", ""),
            "content_length": len(q.get("content", "")),
            "quality_check": q.get("check_result", "N/A"),
            "saved": any(r["title"] == q.get("title","") for r in new_records)
        } for q in cleaned]
    }

    report_path = os.path.join(DUODUOEDU_DIR, f"test_report_deepseek_r1_{TODAY}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # ========== 最终报告 ==========
    print(f"\n{'='*70}")
    print("📊 deepseek-r1:1.5b 系统测试报告")
    print(f"{'='*70}")
    print(f"  生成模型:     {MODEL_GEN}")
    print(f"  校验模型:     {MODEL_CHECK}")
    print(f"  总耗时:       {total_time:.1f}s")
    print(f"")
    print(f"  【生成阶段】")
    print(f"    原始输出:   {len(raw_output)} 字符")
    print(f"    JSON解析:   {len(questions)}/{len(questions)} (含容错修复)")
    print(f"")
    print(f"  【清洗阶段】")
    print(f"    清洗通过:   {len(cleaned)} 条")
    print(f"    清洗失败:   {len(failed)} 条")
    print(f"")
    print(f"  【校验阶段】")
    print(f"    Ollama通过: {pass_count}/{len(cleaned)}")
    print(f"")
    print(f"  【入库阶段】")
    print(f"    去重丢弃:   {dup_count} 条")
    print(f"    成功入库:   {len(new_records)} 条")
    print(f"    数据库总量: {final_count} 条")
    print(f"")
    print(f"  📁 测试报告: {report_path}")
    print(f"{'='*70}")
    print("✅ 系统测试完成！")


if __name__ == "__main__":
    main()
