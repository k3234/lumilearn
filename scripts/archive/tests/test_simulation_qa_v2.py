# -*- coding: utf-8 -*-
"""
模拟学习提问测试 V2 - 简化版，减少API调用次数
AI模拟不同水平的学生，在学习过程中提出问题
"""
import json
import requests
import time
import re
import os
from datetime import datetime

OLLAMA_BASE_URL = "http://192.168.2.63:11434"
MODEL = "qwen2.5:7b"
TODAY = datetime.now().strftime("%Y-%m-%d")
DUODUOEDU_DIR = r"e:\学习LLM\duoduoedu"

# 学生角色配置
STUDENT_PROFILES = {
    "beginner": {
        "name": "基础薄弱学生",
        "description": "基础较弱，需要更多基础概念解释",
        "question_style": "直接、基础"
    },
    "average": {
        "name": "普通学生",
        "description": "中等水平，能跟上正常教学进度",
        "question_style": "思考型、应用型"
    },
    "advanced": {
        "name": "优秀学生",
        "description": "学有余力，喜欢深入探究",
        "question_style": "拓展、深度"
    }
}

# 测试用教学内容
TEST_CONTENT = {
    "id": "SIM001",
    "title": "向量的数量积",
    "subject": "数学",
    "grade": "高一",
    "content": """向量的数量积（点积）是两个向量之间的一种运算。

定义：对于两个向量a和b，它们的数量积定义为 a·b = |a||b|cosθ，其中θ是两向量之间的夹角。

几何意义：数量积等于一个向量的模与另一个向量在该向量方向上投影的乘积。

性质：
1. a·b = b·a （交换律）
2. (λa)·b = λ(a·b) （数乘结合律）
3. (a+b)·c = a·c + b·c （分配律）

坐标表示：若a=(x1,y1)，b=(x2,y2)，则a·b = x1x2 + y1y2"""
}


def call_ollama(prompt, model=MODEL, timeout=90):
    """调用Ollama模型"""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.6}},
            timeout=timeout
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"      异常: {e}")
    return None


def simulate_all_questions(content, title, subject):
    """一次性为所有学生类型生成问题"""
    prompt = f"""模拟3种不同水平的学生学习以下内容，每种学生提出2个问题：

教学内容:
标题: {title}
学科: {subject}
内容: {content}

学生类型：
1. 基础薄弱学生 - 基础较弱，提问风格直接、基础
2. 普通学生 - 中等水平，提问风格思考型、应用型  
3. 优秀学生 - 学有余力，提问风格拓展、深度

请为每种学生生成2个问题，返回JSON格式：
{{
  "beginner": [
    {{"question": "问题内容", "question_type": "概念理解/计算过程/应用场景", "student_thinking": "学生思考过程"}}
  ],
  "average": [...],
  "advanced": [...]
}}"""

    result = call_ollama(prompt, timeout=120)
    if result:
        try:
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if isinstance(data, dict):
                    return data
        except Exception as e:
            print(f"    解析错误: {e}")
    return {}


def generate_answers_batch(questions, content, subject):
    """批量生成教师回答"""
    qa_list = []
    for i, q in enumerate(questions):
        prompt = f"""作为{subject}教师，简洁回答学生问题：

问题: {q.get('question', '')}
教学内容: {content[:200]}

返回JSON：{{"direct_answer": "直接回答(50字内)", "detailed_explanation": "详细解释(100字内)"}}"""

        result = call_ollama(prompt, timeout=60)
        answer = {"direct_answer": "请参考教材", "detailed_explanation": "需要进一步学习"}
        
        if result:
            try:
                match = re.search(r'\{.*\}', result, re.DOTALL)
                if match:
                    answer = json.loads(match.group())
            except:
                pass
        
        qa_list.append({
            "question": q.get("question", ""),
            "question_type": q.get("question_type", "概念理解"),
            "student_thinking": q.get("student_thinking", ""),
            "direct_answer": answer.get("direct_answer", ""),
            "detailed_explanation": answer.get("detailed_explanation", "")
        })
        
        print(f"      回答 {i+1}/{len(questions)} 生成完成")
    
    return qa_list


def main():
    print("=" * 70)
    print("模拟学习提问测试 V2")
    print(f"时间: {TODAY}")
    print(f"模型: {MODEL}")
    print("=" * 70)
    
    t0 = time.time()
    content = TEST_CONTENT["content"]
    title = TEST_CONTENT["title"]
    subject = TEST_CONTENT["subject"]
    
    print(f"\n学习内容: {title}")
    print(f"内容长度: {len(content)} 字符")
    
    # Step 1: 生成所有问题
    print(f"\n[Step 1] 生成学生问题...")
    all_questions = simulate_all_questions(content, title, subject)
    
    if not all_questions:
        print("  ❌ 未能生成问题")
        return
    
    total_questions = sum(len(v) for v in all_questions.values() if isinstance(v, list))
    print(f"  ✅ 生成 {total_questions} 个问题")
    
    # Step 2: 生成回答
    print(f"\n[Step 2] 生成教师回答...")
    all_qa = []
    
    for student_type, questions in all_questions.items():
        if not isinstance(questions, list):
            continue
        
        profile = STUDENT_PROFILES.get(student_type, {})
        print(f"\n  ┌─ {profile.get('name', student_type)} ─┐")
        print(f"  │ 问题数: {len(questions)}")
        
        for i, q in enumerate(questions, 1):
            print(f"  │ [{i}] {q.get('question', '')[:45]}{'...' if len(q.get('question',''))>45 else ''}")
        
        # 批量生成回答
        qa_with_answers = generate_answers_batch(questions, content, subject)
        
        for qa in qa_with_answers:
            qa["student_type"] = student_type
            qa["student_type_name"] = profile.get("name", student_type)
            qa["qa_id"] = f"QA_{TODAY.replace('-','')}_{len(all_qa):04d}"
            qa["source_id"] = TEST_CONTENT["id"]
            qa["subject"] = subject
            qa["grade"] = TEST_CONTENT["grade"]
            qa["title"] = title
            qa["create_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            all_qa.append(qa)
        
        print(f"  └────────────────────────┘")
    
    total_time = time.time() - t0
    
    # 保存结果
    output_file = os.path.join(DUODUOEDU_DIR, f"simulation_qa_test_{TODAY}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_date": TODAY,
            "model": MODEL,
            "total_time": f"{total_time:.1f}s",
            "total_qa": len(all_qa),
            "content_title": title,
            "qa_pairs": all_qa
        }, f, ensure_ascii=False, indent=2)
    
    # 输出报告
    print(f"\n{'='*70}")
    print("📊 模拟学习提问测试报告")
    print(f"{'='*70}")
    print(f"  模型:         {MODEL}")
    print(f"  总耗时:       {total_time:.1f}s")
    print(f"  学习内容:     {title}")
    print(f"  ─────────────────────────────")
    print(f"  生成问答对:   {len(all_qa)} 个")
    
    # 按学生类型统计
    type_stats = {}
    for qa in all_qa:
        st = qa.get("student_type", "unknown")
        type_stats[st] = type_stats.get(st, 0) + 1
    
    print(f"\n  按学生类型分布:")
    for st, count in type_stats.items():
        name = STUDENT_PROFILES.get(st, {}).get("name", st)
        print(f"    • {name}: {count} 个")
    
    # 展示完整问答示例
    print(f"\n  ─────────────────────────────")
    print(f"  完整问答示例:")
    for i, qa in enumerate(all_qa[:3], 1):
        print(f"\n  【示例 {i}】{qa.get('student_type_name', 'N/A')}")
        print(f"    Q: {qa.get('question', 'N/A')}")
        print(f"    A: {qa.get('direct_answer', 'N/A')}")
        if qa.get('detailed_explanation'):
            print(f"    详解: {qa.get('detailed_explanation', '')[:80]}{'...' if len(qa.get('detailed_explanation',''))>80 else ''}")
    
    print(f"\n  ─────────────────────────────")
    print(f"  📄 测试报告: {output_file}")
    print(f"{'='*70}")
    print("✅ 模拟学习提问测试完成！")


if __name__ == "__main__":
    main()
