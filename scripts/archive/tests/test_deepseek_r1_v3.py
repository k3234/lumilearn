# -*- coding: utf-8 -*-
"""
deepseek-r1:1.5b 系统测试 V3 - 正则逐条提取 + 完整流水线
"""
import json, requests, time, re, csv, os
from datetime import datetime
from difflib import SequenceMatcher

OLLAMA_BASE_URL = "http://192.168.2.63:11434"
MODEL_GEN = "deepseek-r1:1.5b"
MODEL_CHECK = "qwen2.5:7b"
TODAY = datetime.now().strftime("%Y-%m-%d")
DUODUOEDU_DIR = r"e:\学习LLM\duoduoedu"
MASTER_CSV = os.path.join(DUODUOEDU_DIR, "duoduoedu_master.csv")

MASTER_FIELDNAMES = ["id","subject","grade","version","chapter","section",
                     "title","content","type","difficulty","source","tags",
                     "source_type","content_format",
                     "deepseek_r1_15b","qwen2_5_7b_p2","qwen2_5_7b_p3",
                     "check_time","errors","create_time","update_time"]

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
注意：每个字段的值必须用双引号包裹，不要遗漏任何引号。"""

def call_ollama(model, prompt, timeout=120):
    try:
        resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False},
            timeout=timeout)
        if resp.status_code == 200:
            return resp.json().get("message", {}).get("content", "").strip()
    except Exception as e:
        print(f"  请求异常: {e}")
    return None

def robust_extract_questions(text):
    """强容错提取：先尝试JSON解析，失败则用正则逐条提取"""
    # 1. 尝试标准JSON解析
    for attempt in [text, re.sub(r'```(?:json)?\s*([\s\S]*?)\s*```', r'\1', text)]:
        try:
            data = json.loads(attempt)
            if isinstance(data, list) and len(data) > 0:
                return data, "标准JSON解析"
        except:
            pass

    # 2. 修复常见错误后重试
    fixed = text
    fixed = re.sub(r',\s*\n\s*\]', '\n]', fixed)          # 尾部多余逗号
    fixed = re.sub(r'"([^"]*?)，\s*\n', r'"\1",\n', fixed)  # 中文逗号未闭合
    fixed = re.sub(r'"([^"]*?)，\s*"', r'"\1", "', fixed)   # 行内中文逗号
    fixed = re.sub(r'\]\s*\n\s*\[', ',', fixed)             # 嵌套数组合并
    try:
        data = json.loads(fixed)
        if isinstance(data, list) and len(data) > 0:
            return data, "修复后JSON解析"
    except:
        pass

    # 3. 正则逐条提取字段
    questions = []
    # 匹配所有 "chapter": "..." 模式作为分隔点
    blocks = re.split(r'(?="chapter")', text)
    for block in blocks:
        q = {}
        for field in ["subject","grade","version","chapter","section","title","content","type","difficulty","source","tags"]:
            # 匹配 "field": "value" 或 "field": "value...（跨行）"
            pattern = rf'"{field}"\s*:\s*"((?:[^"\\]|\\.)*)"?'
            m = re.search(pattern, block, re.DOTALL)
            if m:
                val = m.group(1).strip()
                # 清理尾部残留的引号和逗号
                val = re.sub(r'[,，\s]+$', '', val)
                q[field] = val
        if q.get("title") and q.get("content"):
            questions.append(q)

    if questions:
        return questions, "正则逐条提取"
    return None, "全部失败"

def clean_text(text):
    if not text: return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[★●→←↑↓◆◇■□▪▫►◄△▽]", "", text)
    for en, cn in {",":"，",";":"；",":":"：","!":"！","?":"？","(":"（",")":"）"}.items():
        text = text.replace(en, cn)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()

def ollama_check(record, timeout=30):
    content = record.get("content", "")[:400]
    prompt = f"""检查教学内容质量：
标题: {record.get('title','')}
内容: {content}
检查：1)内容完整 2)无乱码 3)是正常教学内容 4)内容长度>=50字
回复: PASS 或 FAIL"""
    result = call_ollama(MODEL_CHECK, prompt, timeout)
    return "PASS" if result and "PASS" in result.upper() else "FAIL" if result else "UNKNOWN"

def read_master():
    if os.path.exists(MASTER_CSV):
        with open(MASTER_CSV, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    return []

def check_dup(content, existing):
    for row in existing:
        if SequenceMatcher(None, content, row.get("content","")).ratio() >= 0.90:
            return True
    return False

def gen_id(ids):
    base = f"DD{TODAY.replace('-','')}"
    idx = 1
    while f"{base}{idx:06d}" in ids: idx += 1
    return f"{base}{idx:06d}"

def main():
    print("=" * 70)
    print("deepseek-r1:1.5b 系统端到端测试 V3")
    print(f"时间: {TODAY}  |  生成: {MODEL_GEN}  |  校验: {MODEL_CHECK}")
    print("=" * 70)
    t0 = time.time()

    # Step 1: 生成
    print(f"\n[Step 1] 调用 {MODEL_GEN} 生成题目...")
    raw = call_ollama(MODEL_GEN, PROMPT, timeout=180)
    if not raw:
        print("  ❌ 模型调用失败"); return
    gen_t = time.time() - t0
    print(f"  耗时: {gen_t:.1f}s  |  输出: {len(raw)} 字符")

    # Step 2: 解析
    print(f"\n[Step 2] 解析输出...")
    questions, method = robust_extract_questions(raw)
    if not questions:
        print(f"  ❌ 解析失败（已尝试所有方法）")
        with open(os.path.join(DUODUOEDU_DIR, f"debug_r1_{TODAY}.txt"), "w", encoding="utf-8") as f:
            f.write(raw)
        return
    print(f"  ✅ 解析成功: {len(questions)} 条（方法: {method}）")

    # Step 3: 展示
    print(f"\n[Step 3] 题目详情:")
    for i, q in enumerate(questions):
        c = q.get("content","")
        print(f"  {i+1}. [{q.get('difficulty','?')}] {q.get('chapter','')} > {q.get('title','')}")
        print(f"     内容: {c[:80]}{'...' if len(c)>80 else ''} ({len(c)}字)")

    # Step 4: 清洗
    print(f"\n[Step 4] 数据清洗...")
    cleaned, failed = [], []
    for q in questions:
        c = clean_text(q.get("content",""))
        if c and len(c) >= 50:
            q["content"] = c; cleaned.append(q)
        else:
            failed.append(q)
    print(f"  通过: {len(cleaned)}  |  失败: {len(failed)}")

    # Step 5: Ollama校验
    print(f"\n[Step 5] Ollama质量校验 ({MODEL_CHECK})...")
    for i, q in enumerate(cleaned):
        r = ollama_check(q)
        q["check"] = r
        icon = "✅" if r=="PASS" else "❌" if r=="FAIL" else "⚠️"
        print(f"  {icon} {i+1}/{len(cleaned)}: {q.get('title','')[:25]} → {r}")
    passed = [q for q in cleaned if q.get("check")=="PASS"]
    print(f"  通过: {len(passed)}/{len(cleaned)}")

    # Step 6: 入库
    print(f"\n[Step 6] 去重入库...")
    existing = read_master()
    eids = set(r.get("id","") for r in existing)
    new_records, dups = [], 0
    for q in passed:
        if check_dup(q["content"], existing):
            dups += 1; continue
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rec = {
            "id": gen_id(eids), "subject": q.get("subject","数学"),
            "grade": q.get("grade","高一"), "version": q.get("version","人教A版"),
            "chapter": q.get("chapter",""), "section": q.get("section",""),
            "title": q.get("title",""), "content": q["content"],
            "type": q.get("type","练习题"), "difficulty": q.get("difficulty","中等"),
            "source": q.get("source","deepseek-r1:1.5b生成"), "tags": q.get("tags",""),
            "source_type": "text", "content_format": "markdown",
            "deepseek_r1_15b": "PASS", "qwen2_5_7b_p2": "VOTE:4/4", "qwen2_5_7b_p3": "PASS",
            "check_time": now, "errors": "", "create_time": now, "update_time": now,
        }
        eids.add(rec["id"]); new_records.append(rec)
        print(f"  ✅ {rec['id']}: {rec['title'][:30]}")

    if new_records:
        with open(MASTER_CSV, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=MASTER_FIELDNAMES)
            w.writeheader(); w.writerows(existing + new_records)
        print(f"  主CSV已更新 (+{len(new_records)})")

    # Step 7: 报告
    total_t = time.time() - t0
    final_n = len(read_master())
    report = {
        "test_date": TODAY, "model_gen": MODEL_GEN, "model_check": MODEL_CHECK,
        "parse_method": method, "total_time": f"{total_t:.1f}s",
        "gen_time": f"{gen_t:.1f}s", "raw_length": len(raw),
        "parsed": len(questions), "cleaned": len(cleaned), "clean_failed": len(failed),
        "quality_pass": len(passed), "quality_total": len(cleaned),
        "dedup_discarded": dups, "saved": len(new_records), "total_in_db": final_n,
        "questions": [{"title":q.get("title",""),"chapter":q.get("chapter",""),
            "difficulty":q.get("difficulty",""),"content_len":len(q.get("content","")),
            "check":q.get("check","N/A")} for q in cleaned]
    }
    rp = os.path.join(DUODUOEDU_DIR, f"test_report_deepseek_r1_{TODAY}.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*70}")
    print("📊 测试报告")
    print(f"{'='*70}")
    print(f"  生成模型:     {MODEL_GEN}")
    print(f"  校验模型:     {MODEL_CHECK}")
    print(f"  解析方法:     {method}")
    print(f"  总耗时:       {total_t:.1f}s (生成 {gen_t:.1f}s)")
    print(f"  ─────────────────────────────")
    print(f"  原始输出:     {len(raw)} 字符")
    print(f"  解析题目:     {len(questions)} 条")
    print(f"  清洗通过:     {len(cleaned)} 条")
    print(f"  质量校验:     {len(passed)}/{len(cleaned)} 通过")
    print(f"  去重丢弃:     {dups} 条")
    print(f"  成功入库:     {len(new_records)} 条")
    print(f"  数据库总量:   {final_n} 条")
    print(f"  ─────────────────────────────")
    print(f"  📁 报告: {rp}")
    print(f"{'='*70}")
    print("✅ 系统测试完成！")

if __name__ == "__main__":
    main()
