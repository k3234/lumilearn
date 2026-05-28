# -*- coding: utf-8 -*-
"""
动画讲解生成器测试
功能：为教学内容自动生成动画分镜脚本和动画描述
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
ANIMATION_OUTPUT_DIR = os.path.join(DUODUOEDU_DIR, "animation_output")

# 动画类型定义
ANIMATION_TYPES = {
    "concept": "概念动画",
    "process": "过程动画",
    "comparison": "对比动画",
    "3d_model": "3D模型动画",
    "chart": "图表动画",
    "formula": "公式动画"
}

# 测试用教学内容
TEST_CONTENTS = [
    {
        "id": "TEST001",
        "title": "向量的加法运算",
        "subject": "数学",
        "grade": "高一",
        "content": """向量的加法遵循平行四边形法则和三角形法则。

平行四边形法则：将两个向量a和b的起点放在一起，以它们为邻边作平行四边形，则从公共起点出发的对角线向量就是a+b。

三角形法则：将向量b的起点放在向量a的终点，则从a的起点指向b的终点的向量就是a+b。

向量加法满足交换律：a+b=b+a
向量加法满足结合律：(a+b)+c=a+(b+c)"""
    },
    {
        "id": "TEST002",
        "title": "函数的单调性",
        "subject": "数学",
        "grade": "高一",
        "content": """函数的单调性描述函数值随自变量变化的趋势。

定义：设函数f(x)在区间D上有定义，如果对于D内任意两点x1<x2：
- 若f(x1)<f(x2)，则f(x)在D上单调递增
- 若f(x1)>f(x2)，则f(x)在D上单调递减

判断方法：
1. 定义法：取x1<x2，比较f(x1)与f(x2)
2. 导数法：若f'(x)>0，则单调递增；若f'(x)<0，则单调递减"""
    },
    {
        "id": "TEST003",
        "title": "二面角的计算",
        "subject": "数学",
        "grade": "高一",
        "content": """二面角是由两个相交平面所成的角。

定义：从二面角的棱上任意一点，在两个半平面内分别作垂直于棱的射线，这两条射线所成的角叫做二面角的平面角。

计算方法：
1. 定义法：直接作出二面角的平面角，利用几何关系求解
2. 向量法：设两个平面的法向量分别为n1和n2，则二面角的余弦值为|cosθ|=|n1·n2|/(|n1||n2|)
3. 面积射影法：cosθ=S射影/S原"""
    }
]


def call_ollama(prompt, model=MODEL, timeout=60):
    """调用Ollama模型"""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.3}},
            timeout=timeout
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"    调用异常: {e}")
    return None


def analyze_animation_type(content, title, subject):
    """分析内容，确定最适合的动画类型"""
    prompt = f"""作为教学动画设计专家，请分析以下教学内容，确定最适合的动画类型：

标题: {title}
学科: {subject}
内容: {content[:400]}

可选动画类型：
1. concept - 概念动画（适合抽象概念可视化）
2. process - 过程动画（适合步骤流程演示）
3. comparison - 对比动画（适合对比分析）
4. 3d_model - 3D模型动画（适合立体结构展示）
5. chart - 图表动画（适合数据可视化）
6. formula - 公式动画（适合公式推导演示）

请分析并返回JSON格式：
{{"animation_type": "类型代码", "reason": "选择理由", "difficulty": "简单/中等/复杂", "estimated_duration": 预计时长秒数}}"""

    result = call_ollama(prompt, timeout=30)
    if result:
        try:
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
    
    return {"animation_type": "concept", "reason": "默认选择", "difficulty": "中等", "estimated_duration": 60}


def generate_storyboard(content, title, anim_type):
    """生成分镜脚本"""
    type_name = ANIMATION_TYPES.get(anim_type, "概念动画")
    prompt = f"""为以下教学内容设计动画分镜脚本：

标题: {title}
动画类型: {type_name}
内容: {content[:500]}

请设计5-8个分镜，每个分镜包含：镜号、时长(秒)、画面描述、旁白文案、视觉元素、转场效果

返回JSON数组格式：
[{{"shot_number": 1, "duration": 5, "scene_description": "画面描述", "narration": "旁白", "visual_elements": ["元素1"], "transition": "淡入"}}]"""

    result = call_ollama(prompt, timeout=60)
    if result:
        try:
            match = re.search(r'\[.*\]', result, re.DOTALL)
            if match:
                storyboard = json.loads(match.group())
                if isinstance(storyboard, list):
                    return storyboard
        except:
            pass
    
    # 默认分镜
    return [
        {"shot_number": 1, "duration": 5, "scene_description": "开场标题展示", "narration": f"今天我们来学习{title}", "visual_elements": ["标题文字", "背景"], "transition": "淡入"},
        {"shot_number": 2, "duration": 15, "scene_description": "核心概念展示", "narration": content[:100], "visual_elements": ["核心图形", "标注"], "transition": "切换"},
        {"shot_number": 3, "duration": 10, "scene_description": "总结回顾", "narration": "以上就是本节内容", "visual_elements": ["总结文字"], "transition": "淡出"}
    ]


def generate_animation_code(storyboard, anim_type, title):
    """生成Manim动画代码框架"""
    prompt = f"""根据以下分镜脚本，生成Manim动画代码框架：

动画类型: {anim_type}
标题: {title}
分镜脚本: {json.dumps(storyboard, ensure_ascii=False)[:600]}

请生成Python/Manim代码框架，包含类定义、场景设置、每个分镜对应的函数。返回可执行代码。"""

    result = call_ollama(prompt, timeout=90)
    if result:
        return result
    
    # 默认代码模板
    return f'''# Manim动画代码 - {title}
from manim import *

class TeachingAnimation(Scene):
    def construct(self):
        self.camera.background_color = "#1a1a2e"
        
        # 分镜1: 开场
        title = Text("{title}", font_size=48)
        self.play(Write(title))
        self.wait(2)
        self.play(FadeOut(title))
        
        # 分镜2: 内容展示
        content = Text("核心内容展示", font_size=36)
        self.play(FadeIn(content))
        self.wait(3)
        
        # 结尾
        self.play(FadeOut(content))
'''


def generate_interactive_elements(content):
    """生成交互式动画元素"""
    prompt = f"""为以下教学内容设计交互式动画元素：

内容: {content[:300]}

请设计：暂停点、互动问题、重点强调标记

返回JSON格式：
{{"pause_points": [{{"time": 10, "reason": "思考时间"}}], "quiz_questions": [{{"time": 25, "question": "问题", "options": ["A","B"], "answer": "A"}}], "highlights": [{{"time": 15, "element": "重点", "effect": "高亮"}}]}}"""

    result = call_ollama(prompt, timeout=30)
    if result:
        try:
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
    
    return {"pause_points": [{"time": 10, "reason": "思考时间"}], "quiz_questions": [], "highlights": []}


def create_animation_for_content(record):
    """为单个内容创建完整动画方案"""
    content = record.get("content", "")
    title = record.get("title", "")
    subject = record.get("subject", "数学")
    
    print(f"\n  处理: {title}")
    
    # 1. 分析动画类型
    print(f"    [1/4] 分析动画类型...")
    anim_analysis = analyze_animation_type(content, title, subject)
    anim_type = anim_analysis.get("animation_type", "concept")
    print(f"    → 类型: {ANIMATION_TYPES.get(anim_type, anim_type)} ({anim_analysis.get('reason', '')[:30]})")
    
    # 2. 生成分镜脚本
    print(f"    [2/4] 生成分镜脚本...")
    storyboard = generate_storyboard(content, title, anim_type)
    print(f"    → 分镜数: {len(storyboard)} 个")
    
    # 3. 生成动画代码
    print(f"    [3/4] 生成动画代码...")
    animation_code = generate_animation_code(storyboard, anim_type, title)
    print(f"    → 代码长度: {len(animation_code)} 字符")
    
    # 4. 生成交互元素
    print(f"    [4/4] 生成交互元素...")
    interactive = generate_interactive_elements(content)
    print(f"    → 暂停点: {len(interactive.get('pause_points', []))} 个")
    
    # 计算总时长
    total_duration = sum(shot.get("duration", 5) for shot in storyboard)
    
    # 生成动画ID
    animation_id = f"ANIM_{TODAY.replace('-','')}_{int(time.time()) % 100000:05d}"
    
    return {
        "animation_id": animation_id,
        "source_id": record.get("id", ""),
        "title": f"[动画]{title}",
        "subject": subject,
        "grade": record.get("grade", "高一"),
        "animation_type": anim_type,
        "animation_type_name": ANIMATION_TYPES.get(anim_type, "概念动画"),
        "difficulty": anim_analysis.get("difficulty", "中等"),
        "estimated_duration": total_duration,
        "storyboard": storyboard,
        "animation_code": animation_code,
        "interactive_elements": interactive,
        "scene_count": len(storyboard),
        "pause_count": len(interactive.get("pause_points", [])),
        "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def main():
    print("=" * 70)
    print("动画讲解生成器测试")
    print(f"时间: {TODAY}")
    print(f"模型: {MODEL}")
    print(f"测试内容: {len(TEST_CONTENTS)} 个")
    print("=" * 70)
    
    t0 = time.time()
    os.makedirs(ANIMATION_OUTPUT_DIR, exist_ok=True)
    
    results = []
    
    for i, record in enumerate(TEST_CONTENTS):
        print(f"\n[{i+1}/{len(TEST_CONTENTS)}] 生成动画方案...")
        anim_record = create_animation_for_content(record)
        results.append(anim_record)
    
    # 保存结果
    output_file = os.path.join(ANIMATION_OUTPUT_DIR, f"animation_test_{TODAY}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_date": TODAY,
            "model": MODEL,
            "total_time": f"{time.time()-t0:.1f}s",
            "total_animations": len(results),
            "animations": results
        }, f, ensure_ascii=False, indent=2)
    
    # 保存单独的动画代码文件
    for anim in results:
        code_file = os.path.join(ANIMATION_OUTPUT_DIR, f"{anim['animation_id']}.py")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(anim["animation_code"])
    
    # 输出报告
    total_t = time.time() - t0
    print(f"\n{'='*70}")
    print("📊 动画测试报告")
    print(f"{'='*70}")
    print(f"  模型:         {MODEL}")
    print(f"  总耗时:       {total_t:.1f}s")
    print(f"  ─────────────────────────────")
    
    for anim in results:
        print(f"\n  【{anim['title']}】")
        print(f"    动画类型:   {anim['animation_type_name']} ({anim['animation_type']})")
        print(f"    分镜数:     {anim['scene_count']} 个")
        print(f"    预计时长:   {anim['estimated_duration']} 秒")
        print(f"    暂停点:     {anim['pause_count']} 个")
        print(f"    代码长度:   {len(anim['animation_code'])} 字符")
        print(f"    分镜预览:")
        for shot in anim['storyboard'][:3]:
            print(f"      镜{shot.get('shot_number',0)}: {shot.get('scene_description','')[:25]} ({shot.get('duration',0)}s)")
    
    print(f"\n  ─────────────────────────────")
    print(f"  📁 输出目录: {ANIMATION_OUTPUT_DIR}")
    print(f"  📄 测试报告: {output_file}")
    print(f"{'='*70}")
    print("✅ 动画测试完成！")


if __name__ == "__main__":
    main()
