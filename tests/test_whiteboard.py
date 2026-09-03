# -*- coding: utf-8 -*-
"""
tests/test_whiteboard.py
白板推导引擎单元测试
覆盖：公式 SVG、几何 SVG、动画数据生成
"""
import os
import sys
import re

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from framework.services.whiteboard import WhiteboardEngine


@pytest.fixture
def engine():
    return WhiteboardEngine()


class TestGenerateFormulaSvgBasic:
    """测试 generate_formula_svg 基本功能"""

    def test_generate_formula_svg_basic(self, engine):
        formula = "f'(x) = lim(Δx→0) [f(x+Δx)-f(x)]/Δx"
        steps = [
            "f'(x) = lim(Δx→0) [f(x+Δx)-f(x)]/Δx",
            "f'(x) = [f(x+Δx)-f(x)]/Δx"
        ]
        svg = engine.generate_formula_svg(formula, steps)
        assert isinstance(svg, str)
        assert "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" in svg
        assert 'viewBox="0 0 800 400"' in svg
        assert '<rect width="800" height="400" fill="white"/>' in svg
        assert "<text" in svg
        assert "</svg>" in svg

    def test_generate_formula_svg_limited(self, engine):
        formula = "a² + b² = c²"
        steps = ["已知直角三角形", "由勾股定理得"]
        svg = engine.generate_formula_svg(formula, steps)
        assert len(svg) > 100
        assert "直角三角形" in svg or "勾股定理" in svg
        assert formula in svg

    def test_formula_with_subscripts(self, engine):
        formula = "x_n = x_{n-1} + d"
        steps = ["等差数列定义", "通项公式推导"]
        svg = engine.generate_formula_svg(formula, steps)
        assert "<tspan" in svg
        assert "baseline-shift" in svg


class TestGenerateGeometrySvg:
    """测试 generate_geometry_svg 几何图形功能"""

    def test_generate_geometry_svg_right_triangle(self, engine):
        svg = engine.generate_geometry_svg("right_triangle")
        assert isinstance(svg, str)
        assert "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" in svg
        assert "right_triangle" in svg or "triangle" in svg.lower() or "<line" in svg
        assert "<circle" not in svg or "circle" not in svg
        assert "a² + b² = c²" in svg
        assert 'viewBox="0 0 800 400"' in svg
        assert 'fill="white"' in svg

    def test_generate_geometry_svg_circle(self, engine):
        svg = engine.generate_geometry_svg("circle", {"radius": 100})
        assert isinstance(svg, str)
        assert "<circle" in svg
        assert "S = πr²" in svg
        assert "C = 2πr" in svg

    def test_generate_geometry_svg_coordinate_system(self, engine):
        svg = engine.generate_geometry_svg("coordinate_system")
        assert isinstance(svg, str)
        assert "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" in svg
        assert 'viewBox="0 0 800 400"' in svg
        assert "<line" in svg
        assert "x" in svg.lower()
        assert "y" in svg.lower()
        assert "<text" in svg

    def test_generate_geometry_svg_sine_wave(self, engine):
        svg = engine.generate_geometry_svg("sine_wave")
        assert isinstance(svg, str)
        assert "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" in svg
        assert "<polyline" in svg
        assert "sin(x)" in svg
        assert 'viewBox="0 0 800 400"' in svg


class TestAnimateDerivation:
    """测试 animate_derivation 动画数据生成"""

    def test_animate_derivation(self, engine):
        formula = "x = (-b ± √(b²-4ac)) / 2a"
        steps = [
            "ax² + bx + c = 0",
            "x² + (b/a)x = -c/a",
            "(x + b/2a)² = (b²-4ac)/4a²"
        ]
        result = engine.animate_derivation(formula, steps)
        assert isinstance(result, list)
        assert len(result) == 4
        assert result[0]["step"] == 1
        assert result[0]["content"] == "ax² + bx + c = 0"
        assert result[0]["delay"] == 500
        assert result[-1]["content"] == formula
        assert result[-1]["step"] == 4

    def test_animate_derivation_empty_steps(self, engine):
        formula = "E = mc²"
        result = engine.animate_derivation(formula, [])
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["step"] == 1
        assert result[0]["content"] == formula
        assert result[0]["delay"] == 500


class TestSvgContentValidation:
    """测试 SVG 内容完整性"""

    def test_svg_contains_required_elements(self, engine):
        formula = "a² + b² = c²"
        steps = ["推导步骤"]
        svg = engine.generate_formula_svg(formula, steps)
        assert 'viewBox="0 0 800 400"' in svg
        assert '<rect width="800" height="400" fill="white"/>' in svg
        assert "<text" in svg
        assert "</svg>" in svg
        assert "xmlns=" in svg

    def test_formula_svg_structure(self, engine):
        svg = engine.generate_formula_svg("a² + b² = c²", ["步骤1"])
        # 检查包含 text 元素
        text_matches = re.findall(r'<text[^>]*>.*?</text>', svg)
        assert len(text_matches) > 0
        # 检查包含 line 元素
        line_matches = re.findall(r'<line[^/]*/>', svg)
        assert len(line_matches) > 0

    def test_geometry_svg_structure(self, engine):
        svg = engine.generate_geometry_svg("right_triangle")
        assert '<rect width="800" height="400" fill="white"/>' in svg
        assert "<line" in svg
        assert "</svg>" in svg

    def test_formula_with_latex_superscripts(self, engine):
        formula = "x^2 + y^2 = r^2"
        svg = engine.generate_formula_svg(formula, ["圆的标准方程"])
        assert "baseline-shift" in svg
        assert "super" in svg

    def test_formula_with_latex_subscripts(self, engine):
        formula = "a_1 + a_2 = S_n"
        svg = engine.generate_formula_svg(formula, ["数列求和"])
        assert "baseline-shift" in svg
        assert "sub" in svg

    def test_formula_with_frac(self, engine):
        formula = r"\frac{a}{b}"
        svg = engine.generate_formula_svg(formula, ["分数公式"])
        assert "mfrac" in svg or "frac" in svg.lower()

    def test_animate_derivation_delay_format(self, engine):
        steps = ["step1", "step2", "step3"]
        result = engine.animate_derivation("final", steps)
        for item in result:
            assert "step" in item
            assert "content" in item
            assert "delay" in item
            assert isinstance(item["delay"], int)
            assert item["delay"] > 0


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_formula(self, engine):
        svg = engine.generate_formula_svg("", ["步骤"])
        assert isinstance(svg, str)
        assert "</svg>" in svg

    def test_empty_steps(self, engine):
        svg = engine.generate_formula_svg("E=mc²", [])
        assert isinstance(svg, str)
        assert "E=mc²" in svg

    def test_unknown_geometry_shape(self, engine):
        svg = engine.generate_geometry_svg("unknown_shape")
        assert isinstance(svg, str)
        assert "</svg>" in svg

    def test_sine_wave_with_params(self, engine):
        svg = engine.generate_geometry_svg("sine_wave", {
            "origin_x": 400,
            "origin_y": 200,
            "scale": 50,
            "x_range": 6,
            "amplitude": 2
        })
        assert "<polyline" in svg
        assert "sin(x)" in svg

    def test_coordinate_system_with_params(self, engine):
        svg = engine.generate_geometry_svg("coordinate_system", {
            "origin_x": 400,
            "origin_y": 200,
            "scale": 50
        })
        assert "<line" in svg
        assert "x" in svg.lower()
