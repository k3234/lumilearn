# -*- coding: utf-8 -*-
"""
几何动画生成器
生成三角形、圆、多边形等几何动画
"""
from .base import AnimationGenerator
from typing import Dict


class GeometryAnimationGenerator(AnimationGenerator):
    """几何动画生成器"""

    TEMPLATES = {
        "勾股定理": {
            "code": '''from manim import *
import numpy as np

class PythagoreanTheorem(Scene):
    """勾股定理动画"""

    def construct(self):
        # 标题
        title = Text("勾股定理", font_size=48, color=BLUE)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # 创建直角三角形
        vertices = [LEFT * 2 + DOWN * 1.5, RIGHT * 2 + DOWN * 1.5, LEFT * 2 + UP * 1.5]
        triangle = Polygon(*vertices, color=BLUE, stroke_width=3)
        self.play(Create(triangle))

        # 标注顶点
        labels = []
        for v, pos in zip(vertices, ["DL", "DR", "UL"]):
            label = Text({"DL": "A", "DR": "B", "UL": "C"}[pos], font_size=24, color=WHITE)
            label.next_to(v, {"DL": DOWN + LEFT, "DR": DOWN, "UL": LEFT}[pos], buff=0.2)
            labels.append(label)
        self.play(*[Write(l) for l in labels])
        self.wait(0.5)

        # 标注直角
        right_angle = RightAngle(
            Line(LEFT * 2 + DOWN * 1.5, RIGHT * 2 + DOWN * 1.5),
            Line(LEFT * 2 + DOWN * 1.5, LEFT * 2 + UP * 1.5),
            length=0.25, color=YELLOW
        )
        self.play(Create(right_angle))
        self.wait(0.3)

        # 标注边长
        side_a = MathTex("a", font_size=36, color=GREEN).shift(DOWN * 2.5)
        side_b = MathTex("b", font_size=36, color=ORANGE).shift(LEFT * 3.2)
        side_c = MathTex("c", font_size=36, color=RED).shift(RIGHT * 1.2 + UP * 0.8)
        self.play(Write(side_a), Write(side_b), Write(side_c))
        self.wait(0.5)

        # 公式
        formula = MathTex("a^2 + b^2 = c^2", font_size=60, color=BLUE)
        formula.to_edge(DOWN)
        self.play(Write(formula))

        # 解释
        explanation = Text("在直角三角形中，两直角边的平方和等于斜边的平方", font_size=24)
        explanation.to_edge(DOWN).shift(DOWN * 0.8)
        self.play(Write(explanation))

        self.wait(2)
''',
            "narration": "首先，我们画出一个直角三角形，标注三个顶点 A、B、C，直角位于 A 点。接着标注三条边的长度。勾股定理告诉我们：直角三角形的两条直角边平方和等于斜边平方。这就是著名的 a² + b² = c²。"
        },

        "余弦定理": {
            "code": '''from manim import *
import numpy as np

class CosineRule(Scene):
    """余弦定理动画"""

    def construct(self):
        # 标题
        title = Text("余弦定理", font_size=48, color=BLUE)
        title.to_edge(UP)
        self.play(Write(title))

        # 创建任意三角形
        vertices = [LEFT * 2 + DOWN, RIGHT * 1.5 + DOWN, UP * 1.5]
        triangle = Polygon(*vertices, color=BLUE, stroke_width=3)
        self.play(Create(triangle))

        # 标注顶点
        labels = ["A", "B", "C"]
        for v, l in zip(vertices, labels):
            label = Text(l, font_size=28).next_to(v, DOWN + LEFT if v[1] < 0 else UP + RIGHT, buff=0.15)
            self.play(Write(label))

        # 标注边长
        side_a = MathTex("a", font_size=36).next_to(midpoint(vertices[1], vertices[2]), RIGHT)
        side_b = MathTex("b", font_size=36).next_to(midpoint(vertices[0], vertices[2]), LEFT)
        side_c = MathTex("c", font_size=36).next_to(midpoint(vertices[0], vertices[1]), DOWN)
        self.play(Write(side_a), Write(side_b), Write(side_c))

        # 标注角度
        angle_c = MathTex(r"\\angle C", font_size=24).next_to(vertices[0], DOWN, buff=0.3)
        self.play(Write(angle_c))

        # 公式
        formula = MathTex("c^2 = a^2 + b^2 - 2ab\\cos C", font_size=48)
        formula.to_edge(DOWN)
        self.play(Write(formula))

        # 说明
        note = Text("适用于任意三角形", font_size=20, color=GRAY)
        note.next_to(formula, DOWN)
        self.play(Write(note))

        self.wait(2)

def midpoint(p1, p2):
    return (p1 + p2) / 2
''',
            "narration": "余弦定理是勾股定理的推广，适用于任意三角形。公式为 c² = a² + b² - 2ab·cos C，其中 C 是边 c 的对角。"
        },

        "圆面积": {
            "code": '''from manim import *

class CircleArea(Scene):
    """圆的面积推导动画"""

    def construct(self):
        # 标题
        title = Text("圆的面积", font_size=48, color=BLUE)
        title.to_edge(UP)
        self.play(Write(title))

        # 画圆
        circle = Circle(radius=2, color=BLUE, fill_opacity=0.3)
        self.play(Create(circle))

        # 标注半径
        radius = Line(ORIGIN, RIGHT * 2, color=YELLOW)
        r_label = MathTex("r", font_size=36, color=YELLOW).shift(RIGHT * 1)
        self.play(Create(radius), Write(r_label))

        # 公式
        formula = MathTex("S = \\\\pi r^2", font_size=60)
        formula.to_edge(DOWN)
        self.play(Write(formula))

        # 说明
        note = Text("圆的面积等于圆周率乘以半径的平方", font_size=20)
        note.next_to(formula, DOWN)
        self.play(Write(note))

        self.wait(2)
''',
            "narration": "圆是一种特殊的曲线图形。它的面积公式是 S = πr²，其中 r 是圆的半径，π 是圆周率，约等于 3.14159。"
        }
    }

    def generate(self, topic: str, **kwargs) -> Dict[str, str]:
        """生成几何动画"""
        # 查找模板
        for key, template in self.TEMPLATES.items():
            if key in topic:
                return {
                    "manim_code": template["code"],
                    "narration": template["narration"],
                    "scene_type": "geometry"
                }

        # 默认几何动画
        return self._default_animation(topic)

    def _default_animation(self, topic: str) -> Dict[str, str]:
        """生成默认几何动画"""
        code = f'''from manim import *

class GeometryScene(Scene):
    """几何动画"""

    def construct(self):
        # 标题
        title = Text("{topic}", font_size=48, color=BLUE)
        title.to_edge(UP)
        self.play(Write(title))

        # 创建几何图形
        shape = Circle(radius=2, color=BLUE, fill_opacity=0.3)
        self.play(Create(shape))

        # 标注
        formula = MathTex("{topic}", font_size=48)
        formula.to_edge(DOWN)
        self.play(Write(formula))

        self.wait(2)
'''
        return {
            "manim_code": code,
            "narration": f"现在我们来学习{topic}。让我们通过动画来理解这个概念。",
            "scene_type": "geometry"
        }
