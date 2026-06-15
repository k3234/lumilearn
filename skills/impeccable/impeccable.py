# -*- coding: utf-8 -*-
"""
Impeccable Python 实现
大厂级响应式设计技能包

作者：LumiLearn
版本：1.0.0
日期：2026-06-05
"""

# 系统提示词
IMPECCABLE_SYSTEM_PROMPT = """
【响应式设计规范 - Impeccable】
你是一位拥有10年经验的高级前端工程师，专注于响应式设计。在生成任何前端代码时，必须遵循 Impeccable 规范：

## 1. 标准断点系统
- sm: 640px   (大手机)
- md: 768px   (平板)
- lg: 1024px  (小笔记本)
- xl: 1280px  (桌面)
- 2xl: 1536px (大屏)

## 2. 触摸友好设计
- 所有可点击元素最小 44x44px
- 移动端内边距至少 12px
- 触摸目标之间至少 8px 间距

## 3. 反模式 (DO NOT)
❌ 禁止: overflow-x: hidden (会破坏布局)
✅ 推荐: overflow-x: clip

❌ 禁止: box-sizing: content-box
✅ 推荐: box-sizing: border-box

❌ 禁止: width: 100vw (会产生滚动条)
✅ 推荐: width: 100% + padding

## 4. 栅格系统
使用 12 列 Grid:
- grid-template-columns: repeat(12, 1fr)
- gap: 24px

常用列宽:
- 1/4: span 3
- 1/3: span 4
- 1/2: span 6
- 2/3: span 8
- 全宽: span 12

## 5. 无障碍设计
- 所有交互元素有 focus-visible 样式
- 使用语义化 HTML
- ARIA 属性正确使用

开始生成前先检查是否符合以上规范。
"""

# Slash 命令列表
SLASH_COMMANDS = {
    # 布局命令
    "impeccable-layout": "审计并优化整体布局结构",
    "impeccable-grid": "应用专业栅格系统（12列）",
    "impeccable-stack": "创建垂直堆叠布局",
    "impeccable-split": "创建水平分割布局",
    "impeccable-center": "完美居中任何内容",

    # 响应式命令
    "impeccable-responsive": "添加完整的响应式断点",
    "impeccable-breakpoints": "定义标准断点（sm/md/lg/xl/2xl）",
    "impeccable-fluid": "流体 typography 和 spacing",
    "impeccable-mobile": "优化移动端体验",
    "impeccable-touch": "添加触摸友好交互",

    # 视觉命令
    "impeccable-typography": "优化字体层级和可读性",
    "impeccable-spacing": "应用一致的间距系统",
    "impeccable-colors": "优化配色方案",
    "impeccable-shadows": "添加柔和自然的阴影",
    "impeccable-borders": "优化边框和分割线",
    "impeccable-radii": "应用统一的圆角风格",

    # 交互命令
    "impeccable-animation": "添加流畅的微交互动效",
    "impeccable-hover": "优化悬停状态反馈",
    "impeccable-focus": "优化焦点状态（无障碍）",
    "impeccable-loading": "添加优雅的加载状态",
}

# 断点常量
BREAKPOINTS = {
    "sm": "640px",
    "md": "768px",
    "lg": "1024px",
    "xl": "1280px",
    "2xl": "1536px",
}

# 反模式检查
ANTI_PATTERNS = {
    "overflow_hidden": {
        "pattern": r"overflow-x:\s*hidden",
        "issue": "overflow-x: hidden 会破坏布局",
        "suggestion": "使用 overflow-x: clip 或移除",
        "severity": "high",
    },
    "content_box": {
        "pattern": r"box-sizing:\s*content-box",
        "issue": "应该使用 border-box 盒模型",
        "suggestion": "改为 box-sizing: border-box",
        "severity": "high",
    },
    "viewport_width": {
        "pattern": r"width:\s*100vw",
        "issue": "100vw 会包含滚动条宽度，产生水平滚动",
        "suggestion": "使用 width: 100% 或添加 overflow-x: clip",
        "severity": "medium",
    },
    "linear_animation": {
        "pattern": r"transition:.*linear",
        "issue": "linear 动画不自然",
        "suggestion": "使用 ease, ease-in, ease-out, 或 ease-in-out",
        "severity": "low",
    },
}


class ImpeccableChecker:
    """Impeccable 规范检查器"""

    @staticmethod
    def check_responsive(html: str) -> dict:
        """检查响应式设计"""
        issues = []

        # 检查是否定义了断点
        has_breakpoints = any(bp in html for bp in ["@media", "min-width", "max-width"])

        if not has_breakpoints:
            issues.append({
                "type": "no_responsive",
                "message": "未找到响应式断点定义",
                "suggestion": "添加 @media 查询实现响应式布局",
            })

        # 检查触摸友好
        has_touch_targets = "min-height" in html or "min-width" in html

        if not has_touch_targets:
            issues.append({
                "type": "no_touch_friendly",
                "message": "未设置触摸友好尺寸",
                "suggestion": "可点击元素建议 min-height: 44px",
            })

        return {
            "passed": len(issues) == 0,
            "issues": issues,
        }

    @staticmethod
    def check_anti_patterns(css: str) -> dict:
        """检查反模式"""
        import re

        issues = []

        for pattern_name, pattern_info in ANTI_PATTERNS.items():
            if re.search(pattern_info["pattern"], css, re.IGNORECASE):
                issues.append({
                    "type": pattern_name,
                    "message": pattern_info["issue"],
                    "suggestion": pattern_info["suggestion"],
                    "severity": pattern_info["severity"],
                })

        return {
            "passed": len(issues) == 0,
            "issues": issues,
        }

    @staticmethod
    def check_accessibility(html: str) -> dict:
        """检查无障碍设计"""
        issues = []

        # 检查焦点状态
        has_focus = "focus" in html.lower()

        if not has_focus:
            issues.append({
                "type": "no_focus_style",
                "message": "未找到焦点状态样式",
                "suggestion": "添加 :focus-visible 或 :focus 样式",
            })

        # 检查语义化标签
        has_semantic = any(tag in html for tag in ["<header", "<nav", "<main", "<article", "<section", "<footer"])

        if not has_semantic:
            issues.append({
                "type": "no_semantic_html",
                "message": "未使用语义化 HTML 标签",
                "suggestion": "使用 <header>, <nav>, <main>, <article> 等语义标签",
            })

        return {
            "passed": len(issues) == 0,
            "issues": issues,
        }

    @staticmethod
    def check_all(html: str, css: str = "") -> dict:
        """综合检查"""
        results = {
            "responsive": ImpeccableChecker.check_responsive(html),
            "accessibility": ImpeccableChecker.check_accessibility(html),
        }

        if css:
            results["anti_patterns"] = ImpeccableChecker.check_anti_patterns(css)

        all_passed = all(r["passed"] for r in results.values())

        return {
            "passed": all_passed,
            "results": results,
            "summary": f"通过 {sum(1 for r in results.values() if r['passed'])}/{len(results)} 项检查"
        }


def generate_responsive_grid(columns: int = 12, gap: str = "24px") -> str:
    """
    生成响应式栅格 CSS

    Args:
        columns: 列数，默认12
        gap: 间距，默认24px

    Returns:
        栅格 CSS 字符串
    """
    return f"""
.grid {{
    display: grid;
    grid-template-columns: repeat({columns}, 1fr);
    gap: {gap};
}}

/* 响应式 */
@media (max-width: 768px) {{
    .grid {{
        grid-template-columns: 1fr;
    }}
}}

/* 常用列宽 */
.col-1 {{ grid-column: span 1; }}
.col-2 {{ grid-column: span 2; }}
.col-3 {{ grid-column: span 3; }}
.col-4 {{ grid-column: span 4; }}
.col-6 {{ grid-column: span 6; }}
.col-8 {{ grid-column: span 8; }}
.col-12 {{ grid-column: span 12; }}

@media (max-width: 768px) {{
    [class*="col-"] {{
        grid-column: span 12;
    }}
}}
"""


def generate_touch_friendly_button() -> str:
    """生成触摸友好的按钮"""
    return """
.touch-target {
    min-height: 44px;
    min-width: 44px;
    padding: 12px 24px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: all 200ms ease-out;
}

.touch-target:hover {
    transform: translateY(-2px);
}

.touch-target:focus-visible {
    outline: 2px solid #3b82f6;
    outline-offset: 2px;
}

/* 移动端优化 */
@media (hover: none) and (pointer: coarse) {
    .touch-target {
        padding: 16px 24px;
    }
}
"""


# 测试
if __name__ == "__main__":
    print("=" * 60)
    print("Impeccable - 响应式设计检查器")
    print("=" * 60)

    print("\n可用 Slash 命令:")
    for cmd, desc in SLASH_COMMANDS.items():
        print(f"  /{cmd}: {desc}")

    print("\n标准断点:")
    for bp, size in BREAKPOINTS.items():
        print(f"  {bp}: {size}")

    # 测试 HTML
    test_html = """
<div class="grid">
    <div class="col-4">列1</div>
    <div class="col-4">列2</div>
    <div class="col-4">列3</div>
</div>

<style>
.grid {
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: 24px;
}

button {
    min-height: 44px;
    transition: all 200ms ease-out;
}

button:focus-visible {
    outline: 2px solid blue;
}
</style>
    """

    print("\n检查 HTML/CSS:")
    result = ImpeccableChecker.check_all(test_html, """
.grid { display: grid; }
button { min-height: 44px; }
    """)
    print(f"检查结果: {result['summary']}")
    print(f"通过: {'✅' if result['passed'] else '❌'}")
