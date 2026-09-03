# -*- coding: utf-8 -*-
"""
tests/test_interactive_scene.py
InteractiveSceneGenerator 单元测试
覆盖：勾股定理、三角函数、直线方程 HTML 生成及交互元素验证
"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from framework.services.interactive_scene import InteractiveSceneGenerator


@pytest.fixture
def generator():
    return InteractiveSceneGenerator()


# ========== 核心方法测试 ==========

class TestGeneratePythagoreanTheorem:
    """测试 generate_pythagorean_theorem 方法"""

    def test_returns_string(self, generator):
        result = generator.generate_pythagorean_theorem()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_canvas(self, generator):
        html = generator.generate_pythagorean_theorem()
        assert '<canvas' in html

    def test_contains_formula_verification(self, generator):
        html = generator.generate_pythagorean_theorem()
        assert 'a² + b² = c²' in html or 'a&#178;' in html or 'a2' in html.lower()


class TestGenerateTrigFunction:
    """测试 generate_trig_function 方法"""

    def test_returns_string(self, generator):
        result = generator.generate_trig_function()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_canvas(self, generator):
        html = generator.generate_trig_function()
        assert '<canvas' in html

    def test_contains_sliders(self, generator):
        html = generator.generate_trig_function()
        assert '<input type="range"' in html

    def test_contains_formula_display(self, generator):
        html = generator.generate_trig_function()
        assert 'formula' in html or 'formula-box' in html


class TestGenerateLineEquation:
    """测试 generate_line_equation 方法"""

    def test_returns_string(self, generator):
        result = generator.generate_line_equation()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_canvas(self, generator):
        html = generator.generate_line_equation()
        assert '<canvas' in html

    def test_contains_sliders(self, generator):
        html = generator.generate_line_equation()
        assert '<input type="range"' in html

    def test_contains_formula_display(self, generator):
        html = generator.generate_line_equation()
        assert 'formula' in html or 'formula-box' in html


# ========== 通用结构测试 ==========

class TestHTMLStructure:
    """测试生成的 HTML 基本结构"""

    def test_html_contains_canvas_all_scenes(self, generator):
        for method_name in ['generate_pythagorean_theorem', 'generate_trig_function', 'generate_line_equation']:
            html = getattr(generator, method_name)()
            assert '<canvas' in html, f"{method_name} 应包含 canvas 元素"

    def test_html_contains_sliders_all_scenes(self, generator):
        for method_name in ['generate_trig_function', 'generate_line_equation']:
            html = getattr(generator, method_name)()
            assert '<input type="range"' in html, f"{method_name} 应包含滑块控件"

    def test_html_contains_formula_display_all_scenes(self, generator):
        for method_name in ['generate_pythagorean_theorem', 'generate_trig_function', 'generate_line_equation']:
            html = getattr(generator, method_name)()
            assert 'formula' in html, f"{method_name} 应包含公式显示区域"

    def test_html_is_valid_structure(self, generator):
        html = generator.generate_pythagorean_theorem()
        assert '<!DOCTYPE html>' in html
        assert '<html' in html
        assert '</html>' in html
        assert '<head>' in html
        assert '<body>' in html
