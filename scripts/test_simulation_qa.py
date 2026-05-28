# -*- coding: utf-8 -*-
"""
模拟学习提问测试
AI模拟不同水平的学生，在学习过程中提出问题并生成教师回答
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
        "question_style": "直接、基础",
        "difficulty": "简单"
    },
    "average": {
        "name": "普通学生",
        "description": "中等水平，能跟上正常教学进度",
        "question_style": "思考型、应用型",
        "difficulty": "中等"
    },
    "advanced": {
        "name": "优秀学生",
        "description": "学有余力，喜欢深入探究",
        "question_style": "拓展、深度",
        "difficulty": "困难"
    }
}

# 测试用教学内容
TEST_CONTENTS = [
    {
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
    },
    {
        "id": "SIM002",
        "title": "等差数列的通项公式",
        "subject": "数学",
        "grade": "高一",
        "content": """等差数列是指从第二项起，每一项与它的前一项的差等于同一个常数的数列。

定义：如果一个数列{aₙ}满足 aₙ - aₙ₋₁ = d（d为常数，n≥2），则称{aₙ}为等差数列，d称为公差。

通项公式：aₙ = a₁ + (n-1)d

其中：
- a₁为首项
- d为公差
- n为项数

推导过程：
a₂ = a₁ + d
a₃ = a₂ + d = a₁ + 2d
a₄ = a₃ + d = a₁ + 3d
...
aₙ = a₁ + (n-1)d"""
    }
]


def call_ollama(prompt, model=MODEL, timeout=60, temperature=0.6):
    """调用Ollama模型"""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": temperature}},
            timeout=timeout
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"      调用异常: {e}")
    return None


def simulate_student_questions(content, title, subject, student_type):
    """模拟特定类型学生提出问题"""
    profile = STUDENT_PROFILES.get(student_type, STUDENT_PROFILES["average"])
    
    prompt = f"""模拟一位{profile['name']}学习以下教学内容，提出3-4个问题：

学生特点: {profile['description']}
提问风格: {profile['question_style']}

教学内容:
标题: {title}
学科: {subject}
内容: {content[:400]}

请生成学习过程中的问题，包括：
1. 看到标题时的预期问题
2. 学习过程中的疑惑
3. 学完后的总结性问题
4. 拓展应用问题

返回JSON数组格式：
[{{"question_type": "概念理解/计算过程/应用场景/拓展思考", "question": "学生的问题", "context": "提问时的学习上下文", "expected_difficulty": "简单/中等/困难", "student_thinking": "学生的思考过程"}}]"""

    result = call_ollama(prompt, temperature=0.6, timeout=45)
    if result:
        try:
            match = re.search(r'\[.*\]', result, re.DOTALL)
            if match:
                questions = json.loads(match.group())
                if isinstance(questions, list):
                    return questions
        except:
            pass
    return []


def generate_teacher_answer(question, content, subject):
    """生成教师回答"""
    prompt = f"""作为{subject}教师，回答学生问题：

学生问题: {question}

相关教学内容: {content[:250]}

请提供：
1. 直接回答（简洁明了）
2. 详细解释（深入说明）
3. 示例说明（具体例子）
4. 常见误区提醒

返回JSON格式：
{{"direct_answer": "直接回答", "detailed_explanation": "详细解释", "example": "示例", "common_pitfalls": "常见误区"}}"""

    result = call_ollama(prompt, temperature=0.4, timeout=45)
    if result:
        try:
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
    
    return {
        "direct_answer": "请参考教材相关内容",
        "detailed_explanation": "需要进一步学习",
        "example": "暂无示例",
        "common_pitfalls": "注意概念理解"
    }


def simulate_learning_session(record):
    """模拟完整的学习会话（多轮问答）"""
    content = record.get("content", "")
    title = record.get("title", "")
    subject = record.get("subject", "数学")
    record_id = record.get("id", "")
    
    print(f"\n  学习内容: {title}")
    print(f"  内容长度: {len(content)} 字符")
    
    session_qa = []
    
    # 为每种学生类型生成问题
    for student_type in ["beginner", "average", "advanced"]:
        profile = STUDENT_PROFILES[student_type]
        print(f"\n    ┌─ {profile['name']} ({profile['question_style']}) ─┐")
        
        questions = simulate_student_questions(content, title, subject, student_type)
        
        if not questions:
            print(f"    │ 未能生成问题")
            continue
        
        print(f"    │ 生成 {len(questions)} 个问题")
        
        for i, q_item in enumerate(questions, 1):
            question = q_item.get("question", "")
            if not question:
                continue
            
            print(f"    │  [{i}] {question[:40]}{'...' if len(question)>40 else ''}")
            
            # 生成教师回答
            answer = generate_teacher_answer(question, content, subject)
            
            qa_id = f"QA_{TODAY.replace('-','')}_{int(time.time())%100000:05d}_{len(session_qa):03d}"
            
            qa_record = {
                "qa_id": qa_id,
                "source_id": record_id,
                "subject": subject,
                "grade": record.get("grade", "高一"),
                "title": title,
                "student_type": student_type,
                "student_type_name": profile["name"],
                "question_type": q_item.get("question_type", "概念理解"),
                "question": question,
                "student_thinking": q_item.get("student_thinking", ""),
                "context": q_item.get("context", ""),
                "direct_answer": answer.get("direct_answer", ""),
                "detailed_explanation": answer.get("detailed_explanation", ""),
                "example": answer.get("example", ""),
                "common_pitfalls": answer.get("common_pitfalls", ""),
                "difficulty": q_item.get("expected_difficulty", "中等"),
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            session_qa.append(qa_record)
        
        print(f"    └────────────────────────────┘")
    
    return session_qa


def main():
    print("=" * 70)
    print("模拟学习提问测试")
    print(f"时间: {TODAY}")
    print(f"模型: {MODEL}")
    print(f"学生角色: {len(STUDENT_PROFILES)} 种")
    print(f"测试内容: {len(TEST_CONTENTS)} 个")
    print("=" * 70)
    
    t0 = time.time()
    all_qa = []
    
    for i, record in enumerate(TEST_CONTENTS, 1):
        print(f"\n{'='*50}")
        print(f"[{i}/{len(TEST_CONTENTS)}] 模拟学习会话")
        print(f"{'='*50}")
        
        session_qa = simulate_learning_session(record)
        all_qa.extend(session_qa)
        
        print(f"\n  本次会话生成: {len(session_qa)} 个问答对")
    
    total_time = time.time() - t0
    
    # 保存结果
    output_file = os.path.join(DUODUOEDU_DIR, f"simulation_qa_test_{TODAY}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_date": TODAY,
            "model": MODEL,
            "total_time": f"{total_time:.1f}s",
            "total_qa": len(all_qa),
            "student_profiles": list(STUDENT_PROFILES.keys()),
            "qa_pairs": all_qa
        }, f, ensure_ascii=False, indent=2)
    
    # 输出报告
    print(f"\n{'='*70}")
    print("📊 模拟学习提问测试报告")
    print(f"{'='*70}")
    print(f"  模型:         {MODEL}")
    print(f"  总耗时:       {total_time:.1f}s")
    print(f"  测试内容:     {len(TEST_CONTENTS)} 个")
    print(f"  学生角色:     {len(STUDENT_PROFILES)} 种")
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
    
    # 按问题类型统计
    qtype_stats = {}
    for qa in all_qa:
        qt = qa.get("question_type", "未知")
        qtype_stats[qt] = qtype_stats.get(qt, 0) + 1
    
    print(f"\n  按问题类型分布:")
    for qt, count in qtype_stats.items():
        print(f"    • {qt}: {count} 个")
    
    # 展示部分问答示例
    print(f"\n  ─────────────────────────────")
    print(f"  问答示例:")
    for i, qa in enumerate(all_qa[:3], 1):
        print(f"\n  【示例 {i}】")
        print(f"    学生类型: {qa.get('student_type_name', 'N/A')}")
        print(f"    问题类型: {qa.get('question_type', 'N/A')}")
        print(f"    Q: {qa.get('question', 'N/A')[:60]}{'...' if len(qa.get('question',''))>60 else ''}")
        print(f"    A: {qa.get('direct_answer', 'N/A')[:60]}{'...' if len(qa.get('direct_answer',''))>60 else ''}")
    
    print(f"\n  ─────────────────────────────")
    print(f"  📄 测试报告: {output_file}")
    print(f"{'='*70}")
    print("✅ 模拟学习提问测试完成！")


if __name__ == "__main__":
    main()
