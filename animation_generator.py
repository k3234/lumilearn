# -*- coding: utf-8 -*-
"""
LumiLearn 动画生成器模块
集成到主训练流程，为教学内容生成动画分镜和 Manim 代码
"""

import json
import re
import os
import time
from datetime import datetime
from lumilearn_shared import call_ollama, LUMILEARN_DIR


class AnimationGenerator:
    """动画生成器 - 为教学内容生成动画"""

    def __init__(self, base_url="http://192.168.2.63:11434"):
        self.base_url = base_url
        self.primary_model = "qwen2.5:7b"
        self.fallback_model = "deepseek-r1:1.5b"
        self.animation_types = {
            "concept": "概念动画",
            "process": "过程动画",
            "comparison": "对比动画",
            "formula": "公式动画",
            "chart": "图表动画",
            "3d_model": "3D模型动画"
        }

    def _call_model(self, prompt, timeout=60):
        """调用本地模型"""
        for model in [self.primary_model, self.fallback_model]:
            try:
                result = call_ollama(prompt, model=model, timeout=timeout)
                if result and len(result) > 10:
                    return result, model
            except Exception as e:
                print(f"      [{model}] 失败: {str(e)[:50]}")
                continue
        return None, None

    def analyze_animation_type(self, content, title, subject):
        """分析内容，确定最适合的动画类型"""
        prompt = f"""作为教学动画设计专家，请分析以下教学内容，确定最适合的动画类型：

标题: {title}
学科: {subject}
内容: {content[:400]}

可选动画类型：
1. concept - 概念动画（适合抽象概念可视化）
2. process - 过程动画（适合步骤流程演示）
3. comparison - 对比动画（适合对比分析）
4. formula - 公式动画（适合公式推导演示）
5. chart - 图表动画（适合数据可视化）
6. 3d_model - 3D模型动画（适合立体结构展示）

请只返回JSON，不要其他内容：
{{"animation_type": "类型代码", "reason": "选择理由", "difficulty": "简单/中等/复杂", "estimated_duration": 30}}"""

        result, model = self._call_model(prompt, timeout=30)
        if result:
            try:
                match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    data["model_used"] = model
                    return data
            except:
                pass

        return {
            "animation_type": "concept",
            "reason": "默认选择概念动画",
            "difficulty": "中等",
            "estimated_duration": 30,
            "model_used": "fallback"
        }

    def generate_storyboard(self, content, title, anim_type):
        """生成分镜脚本"""
        type_name = self.animation_types.get(anim_type, "概念动画")
        prompt = f"""为以下教学内容设计动画分镜脚本：

标题: {title}
动画类型: {type_name}
内容: {content[:500]}

请设计5-8个分镜，每个分镜包含：镜号、时长(秒)、画面描述、旁白文案、视觉元素、转场效果

请只返回JSON数组，不要其他内容：
[{{"shot_number": 1, "duration": 5, "scene_description": "画面描述", "narration": "旁白", "visual_elements": ["元素1"], "transition": "淡入"}}]"""

        result, model = self._call_model(prompt, timeout=60)
        if result:
            try:
                match = re.search(r'\[.*\]', result, re.DOTALL)
                if match:
                    storyboard = json.loads(match.group())
                    if isinstance(storyboard, list) and len(storyboard) >= 2:
                        return storyboard, model
            except:
                pass

        # 默认分镜
        return [
            {"shot_number": 1, "duration": 5, "scene_description": "开场标题展示",
             "narration": f"今天我们来学习{title}", "visual_elements": ["标题文字", "背景"], "transition": "淡入"},
            {"shot_number": 2, "duration": 15, "scene_description": "核心概念展示",
             "narration": content[:100], "visual_elements": ["核心图形", "标注"], "transition": "切换"},
            {"shot_number": 3, "duration": 10, "scene_description": "总结回顾",
             "narration": "以上就是本节内容", "visual_elements": ["总结文字"], "transition": "淡出"}
        ], "fallback"

    def generate_animation_code(self, storyboard, anim_type, title, subject):
        """生成 Manim 动画代码"""
        prompt = f"""根据以下分镜脚本，生成完整的 Manim (Python) 动画代码。

动画类型: {self.animation_types.get(anim_type, "概念动画")}
标题: {title}
学科: {subject}
分镜脚本: {json.dumps(storyboard, ensure_ascii=False)[:800]}

要求：
1. 使用 from manim import *
2. 创建 TeachingAnimation(Scene) 类
3. 每个分镜对应一个方法
4. 包含适当的颜色、动画效果
5. 代码完整可运行

只返回Python代码，不要其他内容。"""

        result, model = self._call_model(prompt, timeout=90)
        if result and len(result) > 50:
            # 清理代码块标记
            result = re.sub(r'```python\s*', '', result)
            result = re.sub(r'```\s*', '', result)
            return result.strip(), model

        # 默认代码模板
        code = f'''# Manim动画代码 - {title}
from manim import *

class TeachingAnimation(Scene):
    def construct(self):
        self.camera.background_color = "#1a1a2e"

        # 分镜1: 开场
        title = Text("{title}", font_size=48, color=WHITE)
        self.play(Write(title), run_time=2)
        self.wait(1)
        self.play(FadeOut(title))

        # 分镜2: 内容展示
        content = Text("核心内容展示", font_size=36, color=YELLOW)
        self.play(FadeIn(content), run_time=2)
        self.wait(3)

        # 结尾
        self.play(FadeOut(content))
        self.wait(1)
'''
        return code, "fallback"

    def generate_interactive_elements(self, content, title):
        """生成交互式动画元素"""
        prompt = f"""为以下教学内容设计交互式动画元素：

标题: {title}
内容: {content[:300]}

请设计：暂停点、互动问题、重点强调标记

请只返回JSON，不要其他内容：
{{"pause_points": [{{"time": 10, "reason": "思考时间"}}], "quiz_questions": [{{"time": 25, "question": "问题", "options": ["A","B","C","D"], "answer": "A"}}], "highlights": [{{"time": 15, "element": "重点", "effect": "高亮闪烁"}}]}}"""

        result, model = self._call_model(prompt, timeout=30)
        if result:
            try:
                match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
                if match:
                    return json.loads(match.group()), model
            except:
                pass

        return {
            "pause_points": [{"time": 10, "reason": "思考时间"}],
            "quiz_questions": [],
            "highlights": []
        }, "fallback"

    def create_animation(self, content, title, subject, grade):
        """创建完整动画方案"""
        # 1. 分析动画类型
        anim_analysis = self.analyze_animation_type(content, title, subject)
        anim_type = anim_analysis.get("animation_type", "concept")

        # 2. 生成分镜脚本
        storyboard, sb_model = self.generate_storyboard(content, title, anim_type)

        # 3. 生成动画代码
        animation_code, code_model = self.generate_animation_code(
            storyboard, anim_type, title, subject
        )

        # 4. 生成交互元素
        interactive, int_model = self.generate_interactive_elements(content, title)

        # 计算总时长
        total_duration = sum(shot.get("duration", 5) for shot in storyboard)

        # 生成ID
        animation_id = f"ANIM_{datetime.now().strftime('%Y%m%d')}_{int(time.time()) % 100000:05d}"

        return {
            "animation_id": animation_id,
            "title": f"[动画]{title}",
            "subject": subject,
            "grade": grade,
            "animation_type": anim_type,
            "animation_type_name": self.animation_types.get(anim_type, "概念动画"),
            "difficulty": anim_analysis.get("difficulty", "中等"),
            "estimated_duration": total_duration,
            "storyboard": storyboard,
            "animation_code": animation_code,
            "interactive_elements": interactive,
            "scene_count": len(storyboard),
            "pause_count": len(interactive.get("pause_points", [])),
            "quiz_count": len(interactive.get("quiz_questions", [])),
            "models_used": {
                "analysis": anim_analysis.get("model_used", "?"),
                "storyboard": sb_model,
                "code": code_model,
                "interactive": int_model
            },
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
