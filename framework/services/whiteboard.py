# -*- coding: utf-8 -*-
"""
白板推导引擎
生成公式推导 SVG、几何图形 SVG 和推导动画数据
"""
import math
import re
from typing import Dict, List, Optional


SVG_NS = "http://www.w3.org/2000/svg"
VIEWBOX = "0 0 800 400"
FONT_FAMILY = "monospace"
FONT_SIZE = 22


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _svg_attr(key: str, value: str) -> str:
    return f'{key}="{value}"'


def _parse_formula(text: str) -> str:
    result = []
    i = 0
    while i < len(text):
        if text[i] == '\\':
            if i + 1 < len(text):
                if text[i + 1] in (' ', '\t'):
                    result.append(' ')
                    i += 2
                    continue
                elif text[i + 1] == 'n':
                    result.append('&nbsp;')
                    i += 2
                    continue
        result.append(text[i])
        i += 1
    return ''.join(result)


def _render_sup_sub(raw: str) -> str:
    result = []
    i = 0
    while i < len(raw):
        if raw[i] == '^' and i + 1 < len(raw):
            superscript = raw[i + 1]
            if superscript == '{' and i + 2 < len(raw) and raw[i + 2] == '}':
                superscript = raw[i + 2]
            i += 1
            result.append(f'<tspan {_svg_attr("baseline-shift", "super")} {_svg_attr("font-size", "16")}>{_escape(superscript)}</tspan>')
        elif raw[i] == '_' and i + 1 < len(raw):
            subscript = raw[i + 1]
            if subscript == '{' and i + 2 < len(raw) and raw[i + 2] == '}':
                subscript = raw[i + 2]
            i += 1
            result.append(f'<tspan {_svg_attr("baseline-shift", "sub")} {_svg_attr("font-size", "16")}>{_escape(subscript)}</tspan>')
        else:
            result.append(_escape(raw[i]))
        i += 1
    return ''.join(result)


def _render_sup_sub_unescaped(raw: str) -> str:
    """与 _render_sup_sub 相同，但不转义 HTML 标签（用于 regex 替换后的最终步骤）"""
    result = []
    i = 0
    while i < len(raw):
        if raw[i] == '^' and i + 1 < len(raw):
            superscript = raw[i + 1]
            if superscript == '{' and i + 2 < len(raw) and raw[i + 2] == '}':
                superscript = raw[i + 2]
            i += 1
            result.append(f'<tspan {_svg_attr("baseline-shift", "super")} {_svg_attr("font-size", "16")}>{_escape(superscript)}</tspan>')
        elif raw[i] == '_' and i + 1 < len(raw):
            subscript = raw[i + 1]
            if subscript == '{' and i + 2 < len(raw) and raw[i + 2] == '}':
                subscript = raw[i + 2]
            i += 1
            result.append(f'<tspan {_svg_attr("baseline-shift", "sub")} {_svg_attr("font-size", "16")}>{_escape(subscript)}</tspan>')
        else:
            result.append(raw[i])
        i += 1
    return ''.join(result)


def _render_formula_line(formula: str) -> str:
    processed = _parse_formula(formula)
    processed = _render_sup_sub(processed)
    processed = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'<mfrac>\1</mfrac>', processed)
    processed = re.sub(r'\\lim_?\{?([^}]*)\}?\{?([^}]*)\}?', r'<mi>lim</mi>\1', processed)
    processed = re.sub(r'\\sqrt\{([^}]*)\}', r'<msqrt>\1</msqrt>', processed)
    processed = re.sub(r'\\rightarrow', r'→', processed)
    processed = re.sub(r'\\Left柄le', r'⇐', processed)
    processed = re.sub(r'\\Rightarrow', r'⇒', processed)
    processed = re.sub(r'\\pm', r'±', processed)
    processed = re.sub(r'\\times', r'×', processed)
    processed = re.sub(r'\\cdot', r'·', processed)
    processed = re.sub(r'\\neq', r'≠', processed)
    processed = re.sub(r'\\leq', r'≤', processed)
    processed = re.sub(r'\\geq', r'≥', processed)
    processed = re.sub(r'\\infty', r'∞', processed)
    processed = re.sub(r'\\pi', r'π', processed)
    processed = re.sub(r'\\theta', r'θ', processed)
    processed = re.sub(r'\\alpha', r'α', processed)
    processed = re.sub(r'\\beta', r'β', processed)
    processed = re.sub(r'\\gamma', r'γ', processed)
    processed = re.sub(r'\\Delta', r'Δ', processed)
    processed = re.sub(r'\\delta', r'δ', processed)
    processed = re.sub(r'\\epsilon', r'ε', processed)
    processed = re.sub(r'\\int', r'∫', processed)
    processed = re.sub(r'\\sum', r'∑', processed)
    processed = re.sub(r'\\prod', r'∏', processed)
    processed = re.sub(r'\\partial', r'∂', processed)
    processed = re.sub(r'\\nabla', r'∇', processed)
    processed = re.sub(r'\\log', r'log', processed)
    processed = re.sub(r'\\ln', r'ln', processed)
    processed = re.sub(r'\\sin', r'sin', processed)
    processed = re.sub(r'\\cos', r'cos', processed)
    processed = re.sub(r'\\tan', r'tan', processed)
    processed = re.sub(r'\\csc', r'csc', processed)
    processed = re.sub(r'\\sec', r'sec', processed)
    processed = re.sub(r'\\cot', r'cot', processed)
    processed = re.sub(r'\\arcsin', r'arcsin', processed)
    processed = re.sub(r'\\arccos', r'arccos', processed)
    processed = re.sub(r'\\arctan', r'arctan', processed)
    processed = re.sub(r'\\langle', r'⟨', processed)
    processed = re.sub(r'\\rangle', r'⟩', processed)
    processed = re.sub(r'\\left', r'', processed)
    processed = re.sub(r'\\right', r'', processed)
    processed = re.sub(r'\\ ', r' ', processed)
    processed = re.sub(r'\\text\{([^}]*)\}', r'\1', processed)
    processed = re.sub(r'\\mathrm\{([^}]*)\}', r'\1', processed)
    processed = re.sub(r'\\mathbf\{([^}]*)\}', r'\1', processed)
    processed = re.sub(r'\\mathit\{([^}]*)\}', r'\1', processed)
    processed = re.sub(r'\\quad', r'    ', processed)
    processed = re.sub(r'\\qquad', r'        ', processed)
    processed = re.sub(r'\\,', r' ', processed)
    processed = re.sub(r'\\;', r'  ', processed)
    processed = re.sub(r'\\!', r'', processed)
    processed = re.sub(r'\\\|', r'|', processed)
    processed = re.sub(r'\\[{}]$', '', processed)
    processed = re.sub(r'\\[{}]', '', processed)
    # 最终只处理剩余的 ^ 和 _，不转义已有的 HTML 标签
    processed = _render_sup_sub_unescaped(processed)
    return processed


def _calc_text_width(text: str, font_size: int = FONT_SIZE) -> float:
    avg_char_width = font_size * 0.55
    plain = re.sub(r'<[^>]+>', '', text)
    return len(plain) * avg_char_width


def _center_x(text: str) -> float:
    return (800 - _calc_text_width(text)) / 2


def _svg(text: str, x: float, y: float, font_size: int = FONT_SIZE, color: str = "#000000") -> str:
    escaped_text = _escape(text)
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" '
        f'font-family="{FONT_FAMILY}" font-size="{font_size}" '
        f'fill="{color}">{escaped_text}</text>'
    )


def _svg_text(html_content: str, x: float, y: float, font_size: int = FONT_SIZE, color: str = "#000000") -> str:
    """Render text with inline SVG markup (tspan, etc.) - does NOT escape the markup."""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" '
        f'font-family="{FONT_FAMILY}" font-size="{font_size}" '
        f'fill="{color}">{html_content}</text>'
    )


def _svg_elem(tag: str, attrs: dict, content: str = "", self_closing: bool = True) -> str:
    attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
    if self_closing:
        return f'<{tag} {attr_str}/>'
    return f'<{tag} {attr_str}>{content}</{tag}>'


def _line(x1: float, y1: float, x2: float, y2: float, color: str = "#000000", width: float = 2) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" '
        f'x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="{width}" '
        f'stroke-linecap="round"/>'
    )


class WhiteboardEngine:
    """白板推导引擎，生成数学公式和几何图形的 SVG 可视化"""

    def __init__(self, width: int = 800, height: int = 400):
        self.width = width
        self.height = height

    def _svg_header(self) -> str:
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="{SVG_NS}" viewBox="0 0 {self.width} {self.height}" '
            f'width="{self.width}" height="{self.height}">\n'
            f'  <rect width="{self.width}" height="{self.height}" fill="white"/>\n'
        )

    def _svg_footer(self) -> str:
        return '</svg>'

    def generate_formula_svg(self, formula: str, steps: List[str]) -> str:
        """
        生成公式推导 SVG。

        Args:
            formula: 最终公式
            steps: 推导步骤列表

        Returns:
            SVG 字符串
        """
        elements: List[str] = []
        elements.append(self._svg_header())

        max_steps = len(steps) + 1
        header_height = 50
        step_area = self.height - header_height - 20
        step_height = step_area / max_steps
        line_color = "#CCCCCC"

        for i in range(max_steps):
            y = header_height + i * step_height + step_height / 2
            elements.append(_line(40, y, 760, y, line_color, 1))

        elements.append(_svg("推导过程", 40, 35, 20, "#333333"))

        for idx, step_text in enumerate(steps):
            rendered = _render_formula_line(step_text)
            cx = _center_x(rendered)
            y = header_height + (idx + 0.5) * step_height + 8
            step_label = f'<tspan fill="#888888">{idx + 1}.</tspan> '
            elements.append(_svg(step_label + rendered, cx, y, FONT_SIZE))

        final_rendered = _render_formula_line(formula)
        final_y = header_height + max_steps * step_height - 12
        final_cx = _center_x(final_rendered)
        elements.append(_svg_text(final_rendered, final_cx, final_y, FONT_SIZE + 2, "#000000"))
        elements.append(self._svg_footer())
        return ''.join(elements)

    def generate_geometry_svg(self, shape: str, params: dict = None) -> str:
        """
        生成几何图形 SVG。

        Args:
            shape: 图形类型，支持 right_triangle / circle / coordinate_system / sine_wave
            params: 图形参数

        Returns:
            SVG 字符串
        """
        if params is None:
            params = {}
        elements: List[str] = []
        elements.append(self._svg_header())

        if shape == "right_triangle":
            elements.extend(self._render_right_triangle(params))
        elif shape == "circle":
            elements.extend(self._render_circle(params))
        elif shape == "coordinate_system":
            elements.extend(self._render_coordinate_system(params))
        elif shape == "sine_wave":
            elements.extend(self._render_sine_wave(params))
        else:
            elements.append(_svg(f"不支持的图形: {shape}", 300, 200))

        elements.append(self._svg_footer())
        return ''.join(elements)

    def _render_right_triangle(self, params: dict) -> List[str]:
        cx, cy = 400, 220
        adj = params.get("adjacent", 160)
        opp = params.get("opposite", 120)
        tol = params.get("hypotenuse", (adj ** 2 + opp ** 2) ** 0.5)

        bl = (cx - adj, cy + opp)
        br = (cx + adj, cy + opp)
        tl = (cx - adj, cy - opp * 0.1)

        elements: List[str] = []
        elements.append(_line(bl[0], bl[1], br[0], br[1], "#000000", 2))
        elements.append(_line(bl[0], bl[1], tl[0], tl[1], "#000000", 2))
        elements.append(_line(tl[0], tl[1], br[0], br[1], "#000000", 2))

        elements.append(_line(tl[0] + 25, tl[1], tl[0] + 25, tl[1] + 25, "#666666", 1.5))
        elements.append(_line(tl[0] + 25, tl[1] + 25, tl[0] + 25 + 25, tl[1] + 25, "#666666", 1.5))

        a_label = _svg("a", br[0] + 10, br[1] + 28, 18, "#0066CC")
        b_label = _svg("b", bl[0] - 30, bl[1] - 5, 18, "#0066CC")
        c_label = _svg("c", (tl[0] + br[0]) / 2 + 10, (tl[1] + br[1]) / 2 - 10, 18, "#0066CC")
        elements.extend([a_label, b_label, c_label])

        hyp_label = _svg(f"√({adj}²+{opp}²)={tol:.1f}", cx, cy + opp + 50, 16, "#888888")
        elements.append(hyp_label)

        formula = _svg("a² + b² = c²", cx, self.height - 30, 20, "#000000")
        elements.append(formula)
        return elements

    def _render_circle(self, params: dict) -> List[str]:
        cx = params.get("center_x", 400)
        cy = params.get("center_y", 200)
        r = params.get("radius", 120)

        elements: List[str] = []
        elements.append(_svg_elem("circle", {"cx": cx, "cy": cy, "r": r, "fill": "none", "stroke": "#000000", "stroke-width": 2}))
        elements.append(_line(cx, cy, cx + r, cy, "#0066CC", 1.5))
        elements.append(_svg("O", cx - 15, cy + 8, 16, "#000000"))
        elements.append(_svg("r", (cx + cx + r) / 2 - 5, cy - 10, 16, "#0066CC"))

        area_label = _svg("S = πr²", cx, cy + r + 40, 20, "#000000")
        elements.append(area_label)
        circum_label = _svg("C = 2πr", cx, cy + r + 70, 20, "#000000")
        elements.append(circum_label)
        return elements

    def _render_coordinate_system(self, params: dict) -> List[str]:
        cx = params.get("origin_x", 400)
        cy = params.get("origin_y", 200)
        scale = params.get("scale", 40)
        xlim = params.get("x_range", 8)
        ylim = params.get("y_range", 6)

        elements: List[str] = []

        elements.append(_line(cx - xlim * scale, cy, cx + xlim * scale, cy, "#000000", 2))
        elements.append(_line(cx, cy - ylim * scale, cx, cy + ylim * scale, "#000000", 2))

        elements.append(_svg_elem("polygon", {
            "points": f'{cx + xlim * scale},{cy} {cx + xlim * scale - 8},{cy - 4} {cx + xlim * scale - 8},{cy + 4}',
            "fill": "#000000"
        }))
        elements.append(_svg_elem("polygon", {
            "points": f'{cx},{cy - ylim * scale} {cx - 4},{cy - ylim * scale + 8} {cx + 4},{cy - ylim * scale + 8}',
            "fill": "#000000"
        }))

        for i in range(-xlim, xlim + 1):
            if i == 0:
                continue
            x = cx + i * scale
            elements.append(_line(x, cy - 5, x, cy + 5, "#000000", 1.5))
            if abs(i) <= xlim - 1:
                label = _svg(str(i), x - 5, cy + 20, 14, "#555555")
                elements.append(label)

        for i in range(-ylim, ylim + 1):
            if i == 0:
                continue
            y = cy - i * scale
            elements.append(_line(cx - 5, y, cx + 5, y, "#000000", 1.5))
            label = _svg(str(i), cx + 10, y + 5, 14, "#555555")
            elements.append(label)

        elements.append(_svg("x", cx + xlim * scale + 10, cy + 5, 18, "#000000"))
        elements.append(_svg("y", cx, cy - ylim * scale - 15, 18, "#000000"))
        elements.append(_svg("O", cx - 15, cy + 20, 16, "#000000"))
        return elements

    def _render_sine_wave(self, params: dict) -> List[str]:
        cx = params.get("origin_x", 400)
        cy = params.get("origin_y", 200)
        scale = params.get("scale", 40)
        xlim = params.get("x_range", 8)
        amplitude = params.get("amplitude", 1.5)

        elements: List[str] = []
        elements.extend(self._render_coordinate_system({
            "origin_x": cx, "origin_y": cy, "scale": scale,
            "x_range": xlim, "y_range": int(amplitude) + 2
        }))

        points: List[str] = []
        steps = 200
        for i in range(steps + 1):
            x_val = -xlim + (2 * xlim * i / steps)
            y_val = amplitude * math.sin(x_val)
            px = cx + x_val * scale
            py = cy - y_val * scale
            points.append(f"{px:.1f},{py:.1f}")

        points_str = " ".join(points)
        elements.append(_svg_elem("polyline", {
            "points": points_str, "fill": "none", "stroke": "#0066CC",
            "stroke-width": 2, "stroke-linejoin": "round"
        }))
        elements.append(_svg("y = sin(x)", cx + xlim * scale - 80, cy - amplitude * scale - 20, 16, "#0066CC"))
        return elements

    def animate_derivation(self, formula: str, steps: List[str]) -> List[dict]:
        """
        生成分步推导动画数据。

        Args:
            formula: 最终公式
            steps: 推导步骤列表

        Returns:
            动画帧数据列表，每项包含 step、content 和 delay
        """
        animation_data: List[dict] = []
        base_delay = 500

        for idx, step in enumerate(steps):
            animation_data.append({
                "step": idx + 1,
                "content": step,
                "delay": base_delay * (idx + 1)
            })

        animation_data.append({
            "step": len(steps) + 1,
            "content": formula,
            "delay": base_delay * (len(steps) + 1)
        })
        return animation_data
