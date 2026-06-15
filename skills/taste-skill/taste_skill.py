# -*- coding: utf-8 -*-
"""
Taste-Skill Python 实现
前端审美注入系统

作者：LumiLearn
版本：2.2.0
日期：2026-06-05
"""

# 系统提示词
TASTE_SYSTEM_PROMPT = """
【前端审美规范 - Taste-Skill】
你是一位拥有10年经验的高级前端工程师和UI设计师。在生成任何前端代码时，必须遵循以下审美规范：

## 1. 配色系统
- 禁止使用纯黑 (#000000) 和纯白 (#FFFFFF)
- 使用专业配色方案（60-30-10法则）
- 推荐方案：
  * 现代科技风: #1a1a2e + #0075ff + #f5f5f5
  * 温暖亲和风: #faf8f5 + #ff6b35 + #2d2d2d
  * 商务专业风: #0f172a + #3b82f6 + #f1f5f9

## 2. 字体层级
- 使用专业字体族: Inter, SF Pro, Roboto, system-ui
- 层级对比要明显:
  * h1: 2.5rem (40px), font-weight: 700
  * h2: 2rem (32px), font-weight: 600
  * h3: 1.5rem (24px), font-weight: 600
  * body: 1rem (16px), font-weight: 400
  * caption: 0.875rem (14px), font-weight: 400

## 3. 间距系统
- 基于 8px 基准网格
- 标准间距层级: 4px, 8px, 16px, 24px, 32px, 48px, 64px
- 禁止使用奇数值间距

## 4. 动效原则
- 所有交互必须有反馈 (hover, active, focus)
- 过渡时间 150-300ms
- 使用 ease-out 或 ease-in-out
- 禁止使用 linear 动画

## 5. 布局原则
- 使用 CSS Grid 或 Flexbox
- 卡片式布局，阴影柔和: 0 4px 6px rgba(0,0,0,0.1)
- 圆角统一: 4px, 8px, 12px, 16px
- 避免过多边框和分割线

每行代码都要问自己："这看起来像认真设计的吗？"
"""

# 配色方案
COLOR_SCHEMES = {
    "modern_tech": {
        "name": "现代科技风",
        "background": "#1a1a2e",
        "primary": "#0075ff",
        "text": "#f5f5f5",
        "secondary": "#64748b",
    },
    "warm_friendly": {
        "name": "温暖亲和风",
        "background": "#faf8f5",
        "primary": "#ff6b35",
        "text": "#2d2d2d",
        "secondary": "#6b7280",
    },
    "business_pro": {
        "name": "商务专业风",
        "background": "#0f172a",
        "primary": "#3b82f6",
        "text": "#f1f5f9",
        "secondary": "#94a3b8",
    },
    "minimal_pure": {
        "name": "极简纯净风",
        "background": "#ffffff",
        "primary": "#000000",
        "text": "#374151",
        "secondary": "#9ca3af",
    },
}

# 间距常量
SPACING = {
    "xs": "4px",   # 紧凑
    "sm": "8px",    # 基础
    "md": "16px",   # 舒适
    "lg": "24px",   # 宽松
    "xl": "32px",   # 分隔
    "2xl": "48px",  # 章节
    "3xl": "64px",  # 大区块
}

# 圆角常量
BORDER_RADIUS = {
    "none": "0px",
    "sm": "4px",
    "md": "8px",
    "lg": "12px",
    "xl": "16px",
    "full": "9999px",
}

# 阴影样式
SHADOWS = {
    "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
    "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
}


class TasteChecker:
    """审美检查器"""

    @staticmethod
    def check_color_scheme(css: str) -> dict:
        """检查配色方案"""
        issues = []

        if "#000000" in css or "#000" in css:
            issues.append("禁止使用纯黑色 (#000000)")

        if "#ffffff" in css or "#fff" in css:
            issues.append("禁止使用纯白色 (#ffffff)")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
        }

    @staticmethod
    def check_spacing(css: str) -> dict:
        """检查间距系统"""
        issues = []

        # 检查是否使用了奇数值间距
        import re
        odd_spacing = re.findall(r'(?:margin|padding|gap|spacing)[\s:]*(\d+)px', css)

        for spacing in odd_spacing:
            spacing_val = int(spacing)
            if spacing_val % 8 != 0 and spacing_val not in [1, 2, 3, 4, 5, 6, 7]:
                issues.append(f"间距 {spacing_val}px 不是 8px 的倍数")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
        }

    @staticmethod
    def check_animation(css: str) -> dict:
        """检查动效"""
        issues = []

        if "linear" in css and "transition" in css:
            issues.append("禁止使用 linear 动画")

        if "transition:" in css or "transition :" in css:
            if "ease" not in css:
                issues.append("过渡动画建议使用 ease-out 或 ease-in-out")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
        }

    @staticmethod
    def check_all(css: str) -> dict:
        """综合检查"""
        results = {
            "color_scheme": TasteChecker.check_color_scheme(css),
            "spacing": TasteChecker.check_spacing(css),
            "animation": TasteChecker.check_animation(css),
        }

        all_passed = all(r["passed"] for r in results.values())

        return {
            "passed": all_passed,
            "results": results,
            "summary": f"通过 {sum(1 for r in results.values() if r['passed'])}/{len(results)} 项检查"
        }


def apply_taste_to_css(custom_css: str, color_scheme: str = "modern_tech") -> str:
    """
    应用 Taste-Skill 审美规范到 CSS

    Args:
        custom_css: 原始 CSS
        color_scheme: 配色方案名称

    Returns:
        应用审美规范后的 CSS
    """
    scheme = COLOR_SCHEMES.get(color_scheme, COLOR_SCHEMES["modern_tech"])

    enhanced_css = custom_css

    # 如果没有设置字体，添加默认字体
    if "font-family" not in enhanced_css:
        enhanced_css = enhanced_css.replace(
            "body {",
            "body {\n  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;"
        )

    # 如果没有设置盒模型，添加 border-box
    if "box-sizing" not in enhanced_css:
        enhanced_css = "* {\n  box-sizing: border-box;\n}\n" + enhanced_css

    return enhanced_css


# 测试
if __name__ == "__main__":
    print("=" * 60)
    print("Taste-Skill - 前端审美检查器")
    print("=" * 60)

    # 测试 CSS
    test_css = """
    .card {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 200ms ease-out;
    }

    .card:hover {
        transform: translateY(-2px);
    }
    """

    print("\n检查 CSS:")
    print(test_css)

    result = TasteChecker.check_all(test_css)
    print(f"\n检查结果: {result['summary']}")
    print(f"通过: {'✅' if result['passed'] else '❌'}")

    if not result['passed']:
        for check_type, check_result in result['results'].items():
            if not check_result['passed']:
                print(f"\n{check_type} 问题:")
                for issue in check_result['issues']:
                    print(f"  - {issue}")

    print("\n配色方案:")
    for name, scheme in COLOR_SCHEMES.items():
        print(f"  {scheme['name']}: {name}")
