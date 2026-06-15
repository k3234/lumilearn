# -*- coding: utf-8 -*-
"""
使用 deepseek-r1:1.5b 生成测试题目，然后送入系统流水线进行端到端测试
"""
import json
import requests
import time
import re
from datetime import datetime

OLLAMA_BASE_URL = "http://192.168.2.63:11434"
MODEL = "deepseek-r1:1.5b"
TODAY = datetime.now().strftime("%Y-%m-%d")

# 生成题目的prompt
PROMPT = """请为高中数学人教A版生成5道测试题目，要求覆盖不同章节和难度。
严格按以下JSON数组格式输出，不要输出其他内容：
[
  {
    "subject": "数学",
    "grade": "高一",
    "version": "人教A版",
    "chapter": "章节名",
    "section": "小节名",
    "title": "题目标题",
    "content": "题目完整内容（包含题目描述和详细解答，至少100字）",
    "type": "练习题",
    "difficulty": "基础/中等/较难",
    "source": "deepseek-r1:1.5b生成",
    "tags": "标签1,标签2"
  }
]

章节建议：从以下中选择至少3个不同章节
- 第一章 集合与常用逻辑用语
- 第二章 一元二次函数、方程和不等式
- 第三章 函数的概念与性质
- 第四章 指数函数与对数函数
- 第五章 三角函数
- 第六章 平面向量及其应用
- 第七章 复数
- 第八章 立体几何初步
- 第九章 统计
- 第十章 概率
"""

def call_deepseek_r1(prompt, timeout=120):
    """调用 deepseek-r1:1.5b 生成内容"""
    print(f"  调用 {MODEL} 中（可能需要较长时间）...")
    start = time.time()
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            },
            timeout=timeout
        )
        elapsed = time.time() - start
        if resp.status_code == 200:
            content = resp.json().get("message", {}).get("content", "")
            print(f"  模型响应耗时: {elapsed:.1f}s, 内容长度: {len(content)} 字符")
            return content, elapsed
        else:
            print(f"  请求失败: HTTP {resp.status_code}")
            return None, elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"  请求异常: {e}")
        return None, elapsed

def extract_json(text):
    """从模型输出中提取JSON数组"""
    # 尝试直接解析
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except:
        pass

    # 提取JSON代码块
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'\[\s*\{[\s\S]*\}\s*\]'
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            try:
                data = json.loads(match.group(1) if '```' in pat else match.group(0))
                if isinstance(data, list):
                    return data
            except:
                continue
    return None

def main():
    print("=" * 70)
    print("deepseek-r1:1.5b 系统测试")
    print(f"时间: {TODAY}")
    print("=" * 70)

    # Step 1: 调用模型生成题目
    print("\n[Step 1] 调用 deepseek-r1:1.5b 生成测试题目...")
    raw_output, gen_time = call_deepseek_r1(PROMPT)

    if not raw_output:
        print("  ❌ 模型调用失败，终止测试")
        return

    # 打印原始输出（截取前500字符）
    print(f"\n  原始输出预览（前500字符）:")
    print(f"  {'-' * 50}")
    preview = raw_output[:500].replace('\n', '\n  ')
    print(f"  {preview}")
    if len(raw_output) > 500:
        print(f"  ... (共 {len(raw_output)} 字符)")
    print(f"  {'-' * 50}")

    # Step 2: 解析JSON
    print("\n[Step 2] 解析模型输出...")
    questions = extract_json(raw_output)

    if not questions:
        print("  ❌ 未能从模型输出中解析出有效JSON")
        # 保存原始输出供调试
        debug_path = f"e:\\学习LLM\\duoduoedu\\debug_deepseek_r1_{TODAY}.txt"
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(raw_output)
        print(f"  原始输出已保存到: {debug_path}")
        return

    print(f"  ✅ 成功解析 {len(questions)} 道题目")

    # Step 3: 展示题目详情
    print("\n[Step 3] 题目详情:")
    for i, q in enumerate(questions):
        print(f"\n  题目 {i+1}:")
        print(f"    章节: {q.get('chapter', 'N/A')} > {q.get('section', 'N/A')}")
        print(f"    标题: {q.get('title', 'N/A')}")
        print(f"    难度: {q.get('difficulty', 'N/A')}")
        content = q.get('content', '')
        print(f"    内容: {content[:80]}..." if len(content) > 80 else f"    内容: {content}")
        print(f"    标签: {q.get('tags', 'N/A')}")

    # Step 4: 保存结果
    output_path = f"e:\\学习LLM\\duoduoedu\\deepseek_r1_test_{TODAY}.json"
    result = {
        "test_date": TODAY,
        "model": MODEL,
        "generation_time": f"{gen_time:.1f}s",
        "raw_output_length": len(raw_output),
        "parsed_count": len(questions),
        "questions": questions
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n[Step 4] 测试结果已保存: {output_path}")

    # Step 5: 汇总
    print("\n" + "=" * 70)
    print("📊 deepseek-r1:1.5b 测试报告")
    print("=" * 70)
    print(f"  模型: {MODEL}")
    print(f"  生成耗时: {gen_time:.1f}s")
    print(f"  原始输出: {len(raw_output)} 字符")
    print(f"  成功解析: {len(questions)} 道题目")
    chapters = set(q.get('chapter', '') for q in questions)
    difficulties = set(q.get('difficulty', '') for q in questions)
    print(f"  覆盖章节: {len(chapters)} 个 ({', '.join(chapters)})")
    print(f"  难度分布: {', '.join(difficulties)}")
    print("=" * 70)
    print("✅ 测试完成！")

if __name__ == "__main__":
    main()
