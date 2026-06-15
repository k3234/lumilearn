# -*- coding: utf-8 -*-
"""
模拟学习提问测试 - 增强随机性版本
模拟各种突发情况：无关问题、重新讲解请求、内容变更、打断提问等
"""
import json
import requests
import time
import re
import os
import random
from datetime import datetime
from enum import Enum

OLLAMA_BASE_URL = "http://192.168.2.63:11434"
MODEL = "qwen2.5:7b"
TODAY = datetime.now().strftime("%Y-%m-%d")
DUODUOEDU_DIR = r"e:\学习LLM\duoduoedu"


class EventType(Enum):
    """随机事件类型"""
    NORMAL_QUESTION = "正常提问"          # 与当前内容相关的问题
    UNRELATED_QUESTION = "无关问题"       # 与当前内容无关的问题
    REEXPLAIN_REQUEST = "重新讲解请求"    # 要求重新讲解
    CONTENT_CHANGE = "内容变更请求"       # 要求更换学习内容
    INTERRUPTION = "打断提问"             # 中途打断提问
    CONFIRMATION = "确认理解"             # 确认是否理解正确
    DISTRACTION = "走神恢复"              # 走神后重新聚焦
    EMOTIONAL = "情绪表达"                # 表达困惑/焦虑/兴奋等情绪


# 随机事件配置：事件类型 -> (概率权重, 描述)
EVENT_CONFIG = {
    EventType.NORMAL_QUESTION: (50, "正常与内容相关的问题"),
    EventType.UNRELATED_QUESTION: (10, "突然问与当前内容无关的问题"),
    EventType.REEXPLAIN_REQUEST: (12, "要求用不同方式重新讲解"),
    EventType.CONTENT_CHANGE: (5, "要求更换学习内容"),
    EventType.INTERRUPTION: (8, "中途打断并提出问题"),
    EventType.CONFIRMATION: (8, "确认自己的理解是否正确"),
    EventType.DISTRACTION: (4, "承认走神请求重复"),
    EventType.EMOTIONAL: (3, "表达学习情绪"),
}

# 学生角色配置
STUDENT_PROFILES = {
    "beginner": {
        "name": "基础薄弱学生",
        "description": "基础较弱，容易走神，经常要求重复讲解",
        "reexplain_prob": 0.25,  # 更高的重新讲解概率
        "distraction_prob": 0.15,
    },
    "average": {
        "name": "普通学生",
        "description": "正常学习，偶尔走神或打断",
        "reexplain_prob": 0.15,
        "distraction_prob": 0.08,
    },
    "advanced": {
        "name": "优秀学生",
        "description": "学得快，容易问拓展问题或要求换内容",
        "reexplain_prob": 0.05,
        "distraction_prob": 0.03,
    },
    "restless": {
        "name": "好动学生",
        "description": "注意力分散，经常打断和问无关问题",
        "reexplain_prob": 0.20,
        "distraction_prob": 0.20,
    }
}

# 测试用教学内容
TEST_CONTENTS = [
    {
        "id": "RAND001",
        "title": "三角函数的诱导公式",
        "subject": "数学",
        "grade": "高一",
        "content": """诱导公式是利用单位圆的对称性推导出的三角函数关系式。

基本诱导公式：
1. sin(π+α) = -sinα, cos(π+α) = -cosα
2. sin(-α) = -sinα, cos(-α) = cosα  
3. sin(π/2-α) = cosα, cos(π/2-α) = sinα
4. sin(π/2+α) = cosα, cos(π/2+α) = -sinα

记忆口诀：奇变偶不变，符号看象限。"""
    },
    {
        "id": "RAND002",
        "title": "直线与圆的位置关系",
        "subject": "数学",
        "grade": "高一",
        "content": """直线与圆的位置关系可以通过圆心到直线的距离d与圆的半径r的大小关系来判断。

位置关系：
1. d > r：直线与圆相离，没有交点
2. d = r：直线与圆相切，有一个交点
3. d < r：直线与圆相交，有两个交点

距离公式：d = |Ax₀+By₀+C|/√(A²+B²)"""
    }
]


def call_ollama(prompt, model=MODEL, timeout=90):
    """调用Ollama模型"""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, 
                  "options": {"temperature": 0.8}},  # 提高温度增加随机性
            timeout=timeout
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"      异常: {e}")
    return None


def select_random_event(student_type="average") -> EventType:
    """根据学生类型和权重选择随机事件"""
    profile = STUDENT_PROFILES.get(student_type, STUDENT_PROFILES["average"])
    
    # 根据学生特性调整概率
    weights = []
    events = []
    for event, (weight, desc) in EVENT_CONFIG.items():
        adjusted_weight = weight
        
        # 基础薄弱学生更容易请求重新讲解
        if event == EventType.REEXPLAIN_REQUEST:
            adjusted_weight = int(weight * (1 + profile["reexplain_prob"] * 2))
        
        # 好动学生更容易走神或打断
        if event in [EventType.INTERRUPTION, EventType.DISTRACTION]:
            adjusted_weight = int(weight * (1 + profile["distraction_prob"]))
        
        # 优秀学生更可能问无关拓展问题或要求换内容
        if student_type == "advanced" and event in [EventType.UNRELATED_QUESTION, EventType.CONTENT_CHANGE]:
            adjusted_weight = int(weight * 1.5)
        
        weights.append(adjusted_weight)
        events.append(event)
    
    return random.choices(events, weights=weights, k=1)[0]


def generate_event_content(event_type: EventType, content, title, subject, student_type) -> dict:
    """生成特定事件类型的内容"""
    
    if event_type == EventType.NORMAL_QUESTION:
        prompt = f"""作为{STUDENT_PROFILES[student_type]['name']}，学习"{title}"时提出一个与内容相关的问题。

学习内容: {content[:300]}

返回JSON: {{"question": "问题", "question_type": "概念理解/计算过程/应用场景", "student_thinking": "思考过程"}}"""
    
    elif event_type == EventType.UNRELATED_QUESTION:
        unrelated_topics = ["老师今天天气怎么样", "这个和物理的牛顿定律有关系吗", "我昨天打游戏通关了", 
                          "数学学这个有什么用", "老师你能推荐几本课外书吗", "这个公式能用来算彩票吗"]
        topic = random.choice(unrelated_topics)
        prompt = f"""作为{STUDENT_PROFILES[student_type]['name']}，在学习"{title}"时，突然想到一个完全无关的问题："{topic}"。

用学生的口吻表达这个突然冒出来的想法，返回JSON: {{"question": "突然想到的问题", "context": "为什么会想到这个", "student_thinking": "当时的心理活动"}}"""
    
    elif event_type == EventType.REEXPLAIN_REQUEST:
        styles = ["用更简单的方式", "举个例子", "画个图解释", "说慢一点", "再讲一遍"]
        style = random.choice(styles)
        prompt = f"""作为{STUDENT_PROFILES[student_type]['name']}，学习"{title}"时没听懂，请求老师{style}重新讲解。

返回JSON: {{"request": "重新讲解的请求", "reason": "为什么没听懂", "preferred_way": "希望怎么讲解"}}"""
    
    elif event_type == EventType.CONTENT_CHANGE:
        alternatives = ["能不能换个例子", "这个太难了讲个简单的", "我想学后面的内容", "这个我学过讲别的吧"]
        alt = random.choice(alternatives)
        prompt = f"""作为{STUDENT_PROFILES[student_type]['name']}，在学习"{title}"时，想{alt}。

返回JSON: {{"request": "变更请求", "reason": "原因", "suggested_alternative": "建议的替代内容"}}"""
    
    elif event_type == EventType.INTERRUPTION:
        prompt = f"""作为{STUDENT_PROFILES[student_type]['name']}，老师正在讲解"{title}"时，突然打断并提出问题。

学习内容: {content[:200]}

返回JSON: {{"interruption": "打断时说的话", "question": "打断后的问题", "urgency": "紧急程度(高/中/低)"}}"""
    
    elif event_type == EventType.CONFIRMATION:
        prompt = f"""作为{STUDENT_PROFILES[student_type]['name']}，学习"{title}"后，想确认自己的理解是否正确。

学习内容: {content[:200]}

返回JSON: {{"confirmation": "确认理解的说法", "my_understanding": "我自己的理解", "is_correct": "是否正确(是/否/不确定)"}}"""
    
    elif event_type == EventType.DISTRACTION:
        distractions = ["刚才走神了", "在想别的事情", "没注意听", "被窗外的事情吸引了"]
        d = random.choice(distractions)
        prompt = f"""作为{STUDENT_PROFILES[student_type]['name']}，{d}，现在想重新跟上学习。

返回JSON: {{"admission": "承认走神的表述", "last_heard": "最后听到的内容", "request": "请求"}}"""
    
    elif event_type == EventType.EMOTIONAL:
        emotions = ["困惑", "焦虑", "兴奋", "沮丧", "好奇", "无聊"]
        emotion = random.choice(emotions)
        prompt = f"""作为{STUDENT_PROFILES[student_type]['name']}，学习"{title}"时感到{emotion}，表达这种情绪。

返回JSON: {{"expression": "情绪表达", "trigger": "触发情绪的原因", "need": "需要什么帮助"}}"""
    
    else:
        return {"question": "默认问题"}
    
    result = call_ollama(prompt, timeout=60)
    if result:
        try:
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
    
    # 默认返回
    defaults = {
        EventType.NORMAL_QUESTION: {"question": "这个是什么意思？", "question_type": "概念理解"},
        EventType.UNRELATED_QUESTION: {"question": "老师，我突然想到一个问题...", "context": "走神了"},
        EventType.REEXPLAIN_REQUEST: {"request": "能再讲一遍吗？", "reason": "没听懂"},
        EventType.CONTENT_CHANGE: {"request": "能不能换个内容？", "reason": "这个太难了"},
        EventType.INTERRUPTION: {"interruption": "等等！", "question": "我有个问题！"},
        EventType.CONFIRMATION: {"confirmation": "我理解对了吗？", "my_understanding": "大概是这样..."},
        EventType.DISTRACTION: {"admission": "刚才走神了", "request": "能重复一下吗？"},
        EventType.EMOTIONAL: {"expression": "我有点困惑", "trigger": "内容太难"},
    }
    return defaults.get(event_type, {"content": "默认内容"})


def generate_teacher_response(event_type, event_content, content, subject):
    """生成教师对随机事件的回应"""
    
    if event_type == EventType.NORMAL_QUESTION:
        prompt = f"""作为{subject}教师，回答学生问题：

问题: {event_content.get('question', '')}
相关内容: {content[:200]}

返回JSON: {{"response": "回答", "encouragement": "鼓励的话"}}"""
    
    elif event_type == EventType.UNRELATED_QUESTION:
        prompt = f"""作为教师，学生突然问了一个无关问题："{event_content.get('question', '')}"。

礼貌地回应，然后引导回正题。返回JSON: {{"acknowledgment": "回应", "transition": "引导回正题的话"}}"""
    
    elif event_type == EventType.REEXPLAIN_REQUEST:
        prompt = f"""作为{subject}教师，学生请求重新讲解，用不同方式解释：

请求: {event_content.get('request', '')}
内容: {content[:200]}

返回JSON: {{"reexplanation": "重新讲解的内容", "check": "确认学生是否理解的话"}}"""
    
    elif event_type == EventType.CONTENT_CHANGE:
        prompt = f"""作为教师，学生想换内容："{event_content.get('request', '')}"。

返回JSON: {{"response": "回应", "decision": "是否同意", "alternative": "如果同意，建议的替代内容"}}"""
    
    elif event_type == EventType.INTERRUPTION:
        prompt = f"""作为教师，学生突然打断："{event_content.get('interruption', '')}"。

返回JSON: {{"immediate_response": "即时回应", "address_question": "回答问题", "resume": "如何继续"}}"""
    
    elif event_type == EventType.CONFIRMATION:
        is_correct = event_content.get('is_correct', '不确定')
        if is_correct == "是":
            prompt = f"""作为教师，确认学生的理解是正确的："{event_content.get('my_understanding', '')}"。

返回JSON: {{"validation": "确认", "praise": "表扬", "next_step": "下一步建议"}}"""
        else:
            prompt = f"""作为教师，纠正学生的误解："{event_content.get('my_understanding', '')}"。

返回JSON: {{"correction": "纠正", "clarification": "澄清", "encouragement": "鼓励"}}"""
    
    elif event_type == EventType.DISTRACTION:
        prompt = f"""作为教师，学生承认走神："{event_content.get('admission', '')}"。

返回JSON: {{"acceptance": "接纳", "brief_repeat": "简要重复", "re_engagement": "重新吸引注意"}}"""
    
    elif event_type == EventType.EMOTIONAL:
        prompt = f"""作为教师，回应学生的情绪表达："{event_content.get('expression', '')}"。

返回JSON: {{"empathy": "共情回应", "support": "支持", "guidance": "引导"}}"""
    
    else:
        return {"response": "好的，我们继续。"}
    
    result = call_ollama(prompt, timeout=60)
    if result:
        try:
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
    
    return {"response": "好的，我们继续学习。"}


def simulate_random_learning_session(record, student_type="average"):
    """模拟带有随机事件的完整学习会话"""
    content = record.get("content", "")
    title = record.get("title", "")
    subject = record.get("subject", "数学")
    
    print(f"\n  学习内容: {title}")
    print(f"  学生类型: {STUDENT_PROFILES[student_type]['name']}")
    print(f"  内容长度: {len(content)} 字符")
    print(f"\n  开始模拟学习会话...")
    
    session_events = []
    num_interactions = random.randint(4, 7)  # 4-7个交互
    
    for i in range(num_interactions):
        print(f"\n    ┌─ 交互 {i+1}/{num_interactions} ─┐")
        
        # 选择随机事件
        event_type = select_random_event(student_type)
        print(f"    │ 事件类型: {event_type.value}")
        
        # 生成事件内容
        event_content = generate_event_content(event_type, content, title, subject, student_type)
        
        # 显示学生行为
        if event_type == EventType.NORMAL_QUESTION:
            print(f"    │ 学生: {event_content.get('question', '')[:50]}")
        elif event_type == EventType.UNRELATED_QUESTION:
            print(f"    │ [突然转移话题]")
            print(f"    │ 学生: {event_content.get('question', '')[:50]}")
        elif event_type == EventType.REEXPLAIN_REQUEST:
            print(f"    │ [请求重新讲解]")
            print(f"    │ 学生: {event_content.get('request', '')[:50]}")
        elif event_type == EventType.INTERRUPTION:
            print(f"    │ [突然打断]")
            print(f"    │ 学生: {event_content.get('interruption', '')} {event_content.get('question', '')[:40]}")
        elif event_type == EventType.DISTRACTION:
            print(f"    │ [走神后恢复]")
            print(f"    │ 学生: {event_content.get('admission', '')[:50]}")
        elif event_type == EventType.EMOTIONAL:
            print(f"    │ [情绪表达]")
            print(f"    │ 学生: {event_content.get('expression', '')[:50]}")
        else:
            print(f"    │ 学生: {str(event_content)[:50]}")
        
        # 生成教师回应
        teacher_response = generate_teacher_response(event_type, event_content, content, subject)
        response_text = str(teacher_response)
        print(f"    │ 教师: {response_text[:60]}{'...' if len(response_text)>60 else ''}")
        
        # 记录事件
        session_events.append({
            "interaction_num": i + 1,
            "event_type": event_type.value,
            "event_type_code": event_type.name,
            "student_content": event_content,
            "teacher_response": teacher_response,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        
        print(f"    └────────────────────────┘")
        time.sleep(0.3)  # 模拟对话间隔
    
    return session_events


def main():
    print("=" * 70)
    print("模拟学习提问测试 - 增强随机性版本")
    print(f"时间: {TODAY}")
    print(f"模型: {MODEL}")
    print(f"随机事件类型: {len(EventType)} 种")
    print("=" * 70)
    
    # 显示事件配置
    print("\n  随机事件配置:")
    for event, (weight, desc) in EVENT_CONFIG.items():
        print(f"    • {event.value}: 权重{weight} - {desc}")
    
    t0 = time.time()
    all_sessions = []
    
    # 为每种学生类型测试一个内容
    student_types = ["beginner", "average", "advanced", "restless"]
    
    for i, student_type in enumerate(student_types):
        content = TEST_CONTENTS[i % len(TEST_CONTENTS)]
        
        print(f"\n{'='*60}")
        print(f"测试 {i+1}/{len(student_types)}: {STUDENT_PROFILES[student_type]['name']}")
        print(f"{'='*60}")
        
        session = simulate_random_learning_session(content, student_type)
        all_sessions.append({
            "student_type": student_type,
            "student_name": STUDENT_PROFILES[student_type]['name'],
            "content_title": content['title'],
            "events": session,
            "event_count": len(session)
        })
    
    total_time = time.time() - t0
    
    # 统计事件分布
    event_stats = {}
    for session in all_sessions:
        for event in session['events']:
            et = event['event_type']
            event_stats[et] = event_stats.get(et, 0) + 1
    
    # 保存结果
    output_file = os.path.join(DUODUOEDU_DIR, f"simulation_random_test_{TODAY}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_date": TODAY,
            "model": MODEL,
            "total_time": f"{total_time:.1f}s",
            "total_sessions": len(all_sessions),
            "total_interactions": sum(s['event_count'] for s in all_sessions),
            "event_config": {k.value: v for k, v in EVENT_CONFIG.items()},
            "event_statistics": event_stats,
            "sessions": all_sessions
        }, f, ensure_ascii=False, indent=2)
    
    # 输出报告
    print(f"\n{'='*70}")
    print("📊 随机性模拟学习测试报告")
    print(f"{'='*70}")
    print(f"  模型:         {MODEL}")
    print(f"  总耗时:       {total_time:.1f}s")
    print(f"  测试会话:     {len(all_sessions)} 个")
    print(f"  总交互数:     {sum(s['event_count'] for s in all_sessions)} 个")
    
    print(f"\n  按学生类型统计:")
    for session in all_sessions:
        print(f"    • {session['student_name']}: {session['event_count']} 个交互")
    
    print(f"\n  事件类型分布:")
    for et, count in sorted(event_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"    • {et}: {count} 次")
    
    print(f"\n  ─────────────────────────────")
    print(f"  📄 测试报告: {output_file}")
    print(f"{'='*70}")
    print("✅ 随机性模拟学习测试完成！")


if __name__ == "__main__":
    main()
