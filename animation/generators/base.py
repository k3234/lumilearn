# -*- coding: utf-8 -*-
"""
动画生成器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List


class AnimationGenerator(ABC):
    """动画生成器基类"""

    # 主题到动画类型的映射
    SCENE_KEYWORDS = {
        "geometry": ["几何", "三角形", "圆形", "四边形", "勾股", "面积", "角度", "圆周率", "多边形"],
        "formula": ["公式", "方程", "求根", "推导", "证明", "配方法", "因式分解"],
        "physics": ["力", "运动", "速度", "加速度", "能量", "动能", "重力", "光学", "折射", "反射"],
        "functions": ["函数", "图像", "坐标系", "一次函数", "二次函数", "指数函数", "对数函数"],
        "statistics": ["概率", "统计", "平均数", "方差", "正态分布"],
    }

    def __init__(self, model_client: Optional[object] = None):
        self.model_client = model_client

    @abstractmethod
    def generate(self, topic: str, **kwargs) -> Dict[str, str]:
        """
        生成动画

        Returns:
            {
                "manim_code": "from manim import *\nclass...",
                "narration": "首先，画一个直角三角形...",
                "scene_type": "geometry"
            }
        """
        pass

    def build_prompt(self, topic: str, scene_type: str) -> str:
        """构建 AI 生成提示"""
        return f"""你是一位专业的数学动画制作师，擅长用 Manim 制作 3Blue1Brown 风格的动画。

【任务】
为"{topic}"生成一个 Manim 动画代码。

【要求】
1. 代码必须是完整可运行的 Python 代码
2. 使用英文变量名，注释用中文
3. 动画时长控制在 30-60 秒
4. 包含完整的 construct 方法
5. 使用 LaTeX 显示数学公式（如 MathTex）

【动画类型】
{scene_type}

【输出格式】
请生成以下内容：
1. 完整的 Manim Python 代码（必须包含 from manim import *）
2. 旁白文案（用于 TTS 配音，每段不超过 50 字）

代码格式：
```python
from manim import *

class SceneName(Scene):
    def construct(self):
        # 你的动画代码
```
"""

    def detect_scene_type(self, topic: str) -> str:
        """根据 topic 自动判断动画类型"""
        for scene_type, keywords in self.SCENE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in topic:
                    return scene_type
        return "geometry"  # 默认几何

    def estimate_duration(self, topic: str, scene_type: str) -> int:
        """估算动画时长"""
        # 根据主题复杂度估算
        base_duration = 30
        if len(topic) > 10:
            base_duration += 15
        if scene_type == "physics":
            base_duration += 10
        return min(base_duration, 90)  # 最大 90 秒
