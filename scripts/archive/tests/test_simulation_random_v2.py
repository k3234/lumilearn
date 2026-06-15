# -*- coding: utf-8 -*-
"""
模拟学习提问测试 - 增强随机性版本 V2 (简化版)
使用预设模板 + 少量API调用来模拟各种突发情况
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
    NORMAL_QUESTION = "正常提问"
    UNRELATED_QUESTION = "无关问题"
    REEXPLAIN_REQUEST = "重新讲解请求"
    CONTENT_CHANGE = "内容变更请求"
    INTERRUPTION = "打断提问"
    CONFIRMATION = "确认理解"
    DISTRACTION = "走神恢复"
    EMOTIONAL = "情绪表达"


# 事件权重配置
EVENT_WEIGHTS = {
    EventType.NORMAL_QUESTION: 50,
    EventType.UNRELATED_QUESTION: 10,
    EventType.REEXPLAIN_REQUEST: 12,
    EventType.CONTENT_CHANGE: 5,
    EventType.INTERRUPTION: 8,
    EventType.CONFIRMATION: 8,
    EventType.DISTRACTION: 4,
    EventType.EMOTIONAL: 3,
}

# 学生角色配置
STUDENT_PROFILES = {
    "beginner": {"name": "基础薄弱学生", "reexplain_prob": 0.25, "distraction_prob": 0.15},
    "average": {"name": "普通学生", "reexplain_prob": 0.15, "distraction_prob": 0.08},
    "advanced": {"name": "优秀学生", "reexplain_prob": 0.05, "distraction_prob": 0.03},
    "restless": {"name": "好动学生", "reexplain_prob": 0.20, "distraction_prob": 0.20},
}

# 预设模板库
TEMPLATES = {
    EventType.UNRELATED_QUESTION: [
        {"question": "老师，今天天气怎么样？", "context": "突然想到外面好像在下雨"},
        {"question": "这个和物理的牛顿定律有关系吗？", "context": "感觉和之前学的物理有点像"},
        {"question": "老师你玩王者荣耀吗？", "context": "刚才走神想到游戏了"},
        {"question": "数学学这个有什么用啊？", "context": "突然怀疑学习的意义"},
        {"question": "老师你能推荐几本课外书吗？", "context": "想拓展一下知识面"},
        {"question": "这个公式能用来算彩票吗？", "context": "想赚点零花钱"},
        {"question": "我昨天打游戏终于上王者了！", "context": "忍不住想分享喜悦"},
        {"question": "老师，食堂今天有什么好吃的？", "context": "肚子饿了在想午饭"},
    ],
    EventType.REEXPLAIN_REQUEST: [
        {"request": "老师，能再讲一遍吗？刚才没听懂。", "reason": "概念太抽象了", "preferred_way": "希望举个例子"},
        {"request": "能不能说慢一点？", "reason": "跟不上了", "preferred_way": "分步骤讲解"},
        {"request": "可以用更简单的方式讲吗？", "reason": "太复杂了", "preferred_way": "用生活中的例子"},
        {"request": "能画个图解释一下吗？", "reason": "纯文字不好理解", "preferred_way": "图形化展示"},
        {"request": "这个和之前学的有什么联系？", "reason": "感觉孤立的知识点", "preferred_way": "对比联系"},
    ],
    EventType.CONTENT_CHANGE: [
        {"request": "这个太难了，能讲个简单点的吗？", "reason": "基础薄弱跟不上", "suggested_alternative": "更基础的入门内容"},
        {"request": "这个我学过了，能讲后面的吗？", "reason": "已经预习过了", "suggested_alternative": "进阶内容"},
        {"request": "能不能换个例子？这个不太理解。", "reason": "对当前例子无感", "suggested_alternative": "贴近生活的例子"},
        {"request": "我想学另一章的内容可以吗？", "reason": "对当前内容没兴趣", "suggested_alternative": "其他章节"},
    ],
    EventType.INTERRUPTION: [
        {"interruption": "等等！", "question": "这里为什么要这样？", "urgency": "高"},
        {"interruption": "老师等一下！", "question": "上一步是怎么得到的？", "urgency": "中"},
        {"interruption": "停一下！", "question": "这个符号是什么意思？", "urgency": "高"},
        {"interruption": "抱歉打断！", "question": "能回头看一下那个公式吗？", "urgency": "中"},
    ],
    EventType.CONFIRMATION: [
        {"confirmation": "我理解对了吗？", "my_understanding": "就是说两个向量相乘等于它们的模长相乘再乘夹角余弦？", "is_correct": "是"},
        {"confirmation": "这样理解对吗？", "my_understanding": "数量积就是点乘对吧？", "is_correct": "是"},
        {"confirmation": "我是不是想错了？", "my_understanding": "这个公式适用于所有向量吗？", "is_correct": "不确定"},
    ],
    EventType.DISTRACTION: [
        {"admission": "老师对不起，刚才走神了。", "last_heard": "只听到前面一半", "request": "能重复一下吗？"},
        {"admission": "抱歉，刚才在想别的事情。", "last_heard": "完全没听到", "request": "从刚才的地方重新讲可以吗？"},
        {"admission": "我走神了...", "last_heard": "听到一半", "request": "能简要重复一下吗？"},
        {"admission": "对不起，被窗外的事情吸引了。", "last_heard": "断断续续", "request": "再讲一遍这部分"},
    ],
    EventType.EMOTIONAL: [
        {"expression": "我有点困惑...", "trigger": "概念太抽象", "need": "更具体的解释"},
        {"expression": "感觉好难啊，有点焦虑。", "trigger": "跟不上节奏", "need": "放慢速度"},
        {"expression": "哇，原来是这样！", "trigger": "突然理解了", "need": "继续深入"},
        {"expression": "这个挺有意思的！", "trigger": "内容有趣", "need": "更多例子"},
        {"expression": "有点无聊...", "trigger": "内容枯燥", "need": "互动或换种方式"},
        {"expression": "我好沮丧，怎么都听不懂。", "trigger": "多次尝试失败", "need": "鼓励和简化"},
    ],
}

# 测试内容
TEST_CONTENT = {
    "id": "RAND001",
    "title": "三角函数的诱导公式",
    "subject": "数学",
    "grade": "高一",
    "content": """诱导公式是利用单位圆的对称性推导出的三角函数关系式。

基本诱导公式：
1. sin(π+α) = -sinα, cos(π+α) = -cosα
2. sin(-α) = -sinα, cos(-α) = cosα  
3. sin(π/2-α) = cosα, cos(π/2-α) = sinα

记忆口诀：奇变偶不变，符号看象限。"""
}


def call_ollama(prompt, model=MODEL, timeout=60):
    """调用Ollama模型"""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, 
                  "options": {"temperature": 0.7}},
            timeout=timeout
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except:
        pass
    return None


def select_event(student_type):
    """选择随机事件"""
    profile = STUDENT_PROFILES.get(student_type, STUDENT_PROFILES["average"])
    weights = []
    events = []
    
    for event, weight in EVENT_WEIGHTS.items():
        adjusted = weight
        if event == EventType.REEXPLAIN_REQUEST:
            adjusted = int(weight * (1 + profile["reexplain_prob"] * 2))
        elif event in [EventType.INTERRUPTION, EventType.DISTRACTION]:
            adjusted = int(weight * (1 + profile["distraction_prob"]))
        elif student_type == "advanced" and event in [EventType.UNRELATED_QUESTION, EventType.CONTENT_CHANGE]:
            adjusted = int(weight * 1.5)
        
        weights.append(max(adjusted, 1))
        events.append(event)
    
    return random.choices(events, weights=weights, k=1)[0]


def generate_event_content(event_type, content, title, subject, student_type):
    """生成事件内容"""
    
    if event_type in TEMPLATES:
        # 从模板随机选择
        template = random.choice(TEMPLATES[event_type])
        return template.copy()
    
    elif event_type == EventType.NORMAL_QUESTION:
        prompt = f"""作为{STUDENT_PROFILES[student_type]['name']}，学习"{title}"时提出一个简短问题。

内容: {content[:200]}

返回JSON: {{"question": "问题(30字内)", "question_type": "概念理解/计算过程"}}"""
        
        result = call_ollama(prompt, timeout=45)
        if result:
            try:
                match = re.search(r'\{.*\}', result, re.DOTALL)
                if match:
                    return json.loads(match.group())
            except:
                pass
        return {"question": "这个是什么意思？", "question_type": "概念理解"}
    
    return {"content": "默认内容"}


def generate_teacher_response(event_type, event_content, content, subject):
    """生成教师回应"""
    
    if event_type == EventType.NORMAL_QUESTION:
        prompt = f"""作为{subject}教师，简洁回答：{event_content.get('question', '')}

相关内容: {content[:150]}

返回JSON: {{"response": "回答(50字内)", "encouragement": "鼓励(20字内)"}}"""
    elif event_type == EventType.UNRELATED_QUESTION:
        prompt = f"""作为教师，学生突然问："{event_content.get('question', '')}"。礼貌回应并引导回正题。

返回JSON: {{"acknowledgment": "回应(30字内)", "transition": "引导回正题(30字内)"}}"""
    elif event_type == EventType.REEXPLAIN_REQUEST:
        prompt = f"""作为{subject}教师，学生请求："{event_content.get('request', '')}"。简要重新解释。

内容: {content[:150]}

返回JSON: {{"reexplanation": "重新讲解(60字内)", "check": "确认理解的话(20字内)"}}"""
    elif event_type == EventType.INTERRUPTION:
        prompt = f"""作为教师，学生突然打断："{event_content.get('interruption', '')}"并问："{event_content.get('question', '')}"。

返回JSON: {{"immediate_response": "即时回应(20字内)", "address": "回答(40字内)"}}"""
    elif event_type == EventType.CONFIRMATION:
        is_correct = event_content.get('is_correct', '不确定')
        if is_correct == "是":
            prompt = """学生理解正确，给予肯定。返回JSON: {"validation": "确认", "praise": "表扬"}"""
        else:
            prompt = """学生理解有误，温和纠正。返回JSON: {"correction": "纠正", "encouragement": "鼓励"}"""
    elif event_type == EventType.DISTRACTION:
        prompt = f"""学生承认："{event_content.get('admission', '')}"。教师接纳并简要重复。

内容: {content[:100]}

返回JSON: {{"acceptance": "接纳(20字内)", "brief_repeat": "简要重复(50字内)"}}"""
    elif event_type == EventType.EMOTIONAL:
        prompt = f"""回应学生情绪："{event_content.get('expression', '')}"。

返回JSON: {{"empathy": "共情(30字内)", "guidance": "引导(40字内)"}}"""
    elif event_type == EventType.CONTENT_CHANGE:
        prompt = f"""学生请求："{event_content.get('request', '')}"。教师回应。

返回JSON: {{"response": "回应(40字内)", "decision": "是否同意"}}"""
    else:
        return {"response": "好的，我们继续。"}
    
    result = call_ollama(prompt, timeout=45)
    if result:
        try:
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
    
    # 默认回应
    defaults = {
        EventType.NORMAL_QUESTION: {"response": "这是一个很好的问题。", "encouragement": "继续思考！"},
        EventType.UNRELATED_QUESTION: {"acknowledgment": "嗯，这个问题...", "transition": "我们先回到今天的学习内容。"},
        EventType.REEXPLAIN_REQUEST: {"reexplanation": "好的，我再讲一遍。", "check": "这次明白了吗？"},
        EventType.INTERRUPTION: {"immediate_response": "好的，请问。", "address": "关于这个问题..."},
        EventType.CONFIRMATION: {"validation": "对的！", "praise": "理解得很好！"},
        EventType.DISTRACTION: {"acceptance": "没关系。", "brief_repeat": "我们刚才讲到..."},
        EventType.EMOTIONAL: {"empathy": "我理解你的感受。", "guidance": "我们慢慢来。"},
        EventType.CONTENT_CHANGE: {"response": "好的，我们调整一下。", "decision": "同意"},
    }
    return defaults.get(event_type, {"response": "好的。"})


def simulate_session(student_type, content_data):
    """模拟学习会话"""
    content = content_data["content"]
    title = content_data["title"]
    subject = content_data["subject"]
    profile = STUDENT_PROFILES[student_type]
    
    print(f"\n  学生: {profile['name']}")
    print(f"  内容: {title}")
    print(f"  特点: 重讲概率{profile['reexplain_prob']*100:.0f}%, 走神概率{profile['distraction_prob']*100:.0f}%")
    print(f"\n  开始模拟...")
    
    events = []
    num = random.randint(4, 6)
    
    for i in range(num):
        event_type = select_event(student_type)
        event_content = generate_event_content(event_type, content, title, subject, student_type)
        teacher_response = generate_teacher_response(event_type, event_content, content, subject)
        
        print(f"\n    ┌─ [{i+1}] {event_type.value} ─┐")
        
        # 显示学生行为
        if event_type == EventType.NORMAL_QUESTION:
            print(f"    │ 学生: {event_content.get('question', '')}")
        elif event_type == EventType.UNRELATED_QUESTION:
            print(f"    │ [突然转移话题]")
            print(f"    │ 学生: {event_content.get('question', '')}")
        elif event_type == EventType.REEXPLAIN_REQUEST:
            print(f"    │ [请求重新讲解]")
            print(f"    │ 学生: {event_content.get('request', '')}")
        elif event_type == EventType.INTERRUPTION:
            print(f"    │ [突然打断 - 紧急度: {event_content.get('urgency', '中')}]")
            print(f"    │ 学生: {event_content.get('interruption', '')} {event_content.get('question', '')}")
        elif event_type == EventType.CONFIRMATION:
            print(f"    │ [确认理解 - {event_content.get('is_correct', '不确定')}]")
            print(f"    │ 学生: {event_content.get('confirmation', '')}")
            print(f"    │ 我的理解: {event_content.get('my_understanding', '')[:40]}...")
        elif event_type == EventType.DISTRACTION:
            print(f"    │ [走神后恢复]")
            print(f"    │ 学生: {event_content.get('admission', '')}")
        elif event_type == EventType.EMOTIONAL:
            print(f"    │ [情绪: {event_content.get('expression', '')}]")
        elif event_type == EventType.CONTENT_CHANGE:
            print(f"    │ [内容变更请求]")
            print(f"    │ 学生: {event_content.get('request', '')}")
        
        # 显示教师回应
        resp_text = str(teacher_response)
        print(f"    │ 教师: {resp_text[:70]}{'...' if len(resp_text)>70 else ''}")
        print(f"    └────────────────────────┘")
        
        events.append({
            "num": i + 1,
            "event_type": event_type.value,
            "event_code": event_type.name,
            "student": event_content,
            "teacher": teacher_response
        })
        
        time.sleep(0.2)
    
    return events


def main():
    print("=" * 70)
    print("模拟学习提问测试 - 增强随机性 V2")
    print(f"时间: {TODAY}")
    print(f"模型: {MODEL}")
    print("=" * 70)
    
    print("\n  随机事件类型及权重:")
    for et, w in EVENT_WEIGHTS.items():
        print(f"    • {et.value}: {w}")
    
    t0 = time.time()
    all_sessions = []
    
    # 测试4种学生类型
    for i, st in enumerate(STUDENT_PROFILES.keys()):
        print(f"\n{'='*60}")
        print(f"测试 {i+1}/4: {STUDENT_PROFILES[st]['name']}")
        print(f"{'='*60}")
        
        events = simulate_session(st, TEST_CONTENT)
        all_sessions.append({
            "student_type": st,
            "student_name": STUDENT_PROFILES[st]["name"],
            "events": events,
            "count": len(events)
        })
    
    total_time = time.time() - t0
    
    # 统计
    stats = {}
    for s in all_sessions:
        for e in s["events"]:
            et = e["event_type"]
            stats[et] = stats.get(et, 0) + 1
    
    # 保存
    output = os.path.join(DUODUOEDU_DIR, f"simulation_random_v2_{TODAY}.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump({
            "test_date": TODAY,
            "model": MODEL,
            "total_time": f"{total_time:.1f}s",
            "sessions": all_sessions,
            "event_stats": stats
        }, f, ensure_ascii=False, indent=2)
    
    # 报告
    print(f"\n{'='*70}")
    print("📊 随机性模拟测试报告")
    print(f"{'='*70}")
    print(f"  总耗时: {total_time:.1f}s")
    print(f"  测试会话: {len(all_sessions)} 个")
    print(f"  总交互: {sum(s['count'] for s in all_sessions)} 个")
    
    print(f"\n  按学生统计:")
    for s in all_sessions:
        print(f"    • {s['student_name']}: {s['count']} 个交互")
    
    print(f"\n  事件分布:")
    for et, c in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        pct = c / sum(stats.values()) * 100
        print(f"    • {et}: {c} 次 ({pct:.1f}%)")
    
    print(f"\n  📄 报告: {output}")
    print(f"{'='*70}")
    print("✅ 测试完成！")


if __name__ == "__main__":
    main()
