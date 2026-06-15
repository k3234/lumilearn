# -*- coding: utf-8 -*-
"""
公式动画生成器
生成数学公式推导动画
"""
from .base import AnimationGenerator
from typing import Dict


class FormulaAnimationGenerator(AnimationGenerator):
    """公式动画生成器"""

    TEMPLATES = {
        "求根公式": {
            "code": '''from manim import *

class QuadraticFormula(Scene):
    """一元二次方程求根公式"""

    def construct(self):
        # 标题
        title = Text("一元二次方程求根公式", font_size=40, color=BLUE)
        title.to_edge(UP)
        self.play(Write(title))

        # 一般形式
        general = MathTex("ax^2 + bx + c = 0", font_size=48)
        general.shift(UP * 1.5)
        self.play(Write(general))

        # 推导步骤
        step1 = MathTex("x^2 + \\frac{b}{a}x = -\\frac{c}{a}", font_size=36)
        step2 = MathTex("x^2 + \\frac{b}{a}x + (\\frac{b}{2a})^2 = -\\frac{c}{a} + (\\frac{b}{2a})^2", font_size=28)
        step3 = MathTex("(x + \\frac{b}{2a})^2 = \\frac{b^2 - 4ac}{4a^2}", font_size=28)

        self.play(Write(step1))
        self.wait(1)
        self.play(ReplacementTransform(step1, step2))
        self.wait(1)
        self.play(ReplacementTransform(step2, step3))
        self.wait(1)

        # 最终公式
        formula = MathTex("x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}", font_size=56, color=RED)
        formula.to_edge(DOWN)
        self.play(Write(formula))

        # 说明
        note = Text("判别式 Δ = b² - 4ac 决定根的性质", font_size=20)
        note.next_to(formula, DOWN)
        self.play(Write(note))

        self.wait(2)
''',
            "narration": "一元二次方程 ax² + bx + c = 0 的求根公式是 x = (-b ± √(b²-4ac)) / 2a。这个公式通过配方法推导得出。"
        },

        "配方法": {
            "code": '''from manim import *

class CompletingSquare(Scene):
    """配方法动画"""

    def construct(self):
        title = Text("配方法", font_size=48, color=BLUE)
        title.to_edge(UP)
        self.play(Write(title))

        # 示例方程
        eq = MathTex("x^2 + 4x - 5 = 0", font_size=48)
        eq.shift(UP * 1.5)
        self.play(Write(eq))

        # 移项
        step1 = MathTex("x^2 + 4x = 5", font_size=40)
        self.play(Write(step1))
        self.wait(1)

        # 配方
        step2 = MathTex("x^2 + 4x + 4 = 5 + 4", font_size=36)
        self.play(ReplacementTransform(step1, step2))
        self.wait(1)

        # 写成完全平方
        step3 = MathTex("(x + 2)^2 = 9", font_size=40, color=GREEN)
        self.play(ReplacementTransform(step2, step3))
        self.wait(1)

        # 解
        solution = MathTex("x + 2 = \\pm 3", font_size=40)
        result = MathTex("x = 1 \\text{ 或 } x = -5", font_size=48, color=RED)
        result.to_edge(DOWN)

        self.play(Write(solution))
        self.wait(0.5)
        self.play(ReplacementTransform(solution, result))

        self.wait(2)
''',
            "narration": "配方法是将二次方程转化为完全平方形式来求解的方法。通过在两边同时加上一次项系数一半的平方，我们可以解出方程。"
        }
    }

    def generate(self, topic: str, **kwargs) -> Dict[str, str]:
        """生成公式动画"""
        for key, template in self.TEMPLATES.items():
            if key in topic:
                return {
                    "manim_code": template["code"],
                    "narration": template["narration"],
                    "scene_type": "formula"
                }

        return self._default_animation(topic)

    def _default_animation(self, topic: str) -> Dict[str, str]:
        """默认公式动画"""
        code = f'''from manim import *

class FormulaScene(Scene):
    """公式动画"""

    def construct(self):
        title = Text("{topic}", font_size=48, color=BLUE)
        title.to_edge(UP)
        self.play(Write(title))

        formula = MathTex("{topic}", font_size=60)
        self.play(Write(formula))

        self.wait(2)
'''
        return {
            "manim_code": code,
            "narration": f"现在我们来学习{topic}的推导过程。",
            "scene_type": "formula"
        }
