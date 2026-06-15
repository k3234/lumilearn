# Taste-Skill 快速使用指南

## 什么是 Taste-Skill?

Taste-Skill 是一个给 AI Coding Agent 用的前端审美 Skill，让生成出来的界面在布局、字体、动效、间距上更像认真设计的。

**GitHub**: 22K+ Stars ⭐
**来源**: [leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill)

## 核心能力

1. **配色系统** - 禁止土味配色，使用专业配色方案
2. **字体层级** - 清晰的标题-正文-注释层级
3. **间距系统** - 基于 8px 网格的标准间距
4. **动效原则** - 流畅自然的微交互
5. **布局规范** - 卡片式设计，柔和阴影

## 快速开始

### 方法 1: 作为系统提示词注入

在 AI 编程助手（Claude Code, Cursor, Codex等）的系统提示词中添加：

```
你是一位拥有10年经验的高级前端工程师和UI设计师。在生成任何前端代码时，必须遵循 Taste-Skill 审美规范：

1. 禁止使用纯黑 (#000000) 和纯白 (#FFFFFF)
2. 使用 Inter/SF Pro 等专业字体族
3. 基于 8px 网格设置间距
4. 所有交互有过渡动效 (150-300ms)
5. 使用卡片式布局，阴影柔和 (0 4px 6px rgba(0,0,0,0.1))
```

### 方法 2: 加载 skill.md 文件

将 `skill.md` 的内容复制到 AI 工具的项目知识库中。

### 方法 3: 在代码中使用

```python
from lumilearn.skills.taste_skill import TASTE_SYSTEM_PROMPT

# 在调用 AI 生成代码时注入审美规范
response = call_ai_model(prompt + TASTE_SYSTEM_PROMPT)
```

## 审美检查清单

生成代码后，逐项检查：

- [ ] 配色不是纯黑/纯白
- [ ] 使用了专业字体族（Inter, SF Pro）
- [ ] 间距基于 8px 网格（4, 8, 16, 24, 32, 48, 64px）
- [ ] 所有交互有 hover/focus/active 反馈
- [ ] 过渡时间 150-300ms，使用 ease-out
- [ ] 卡片有圆角（8-12px）和柔和阴影
- [ ] 布局使用 Flexbox 或 Grid
- [ ] 没有过度装饰

## 推荐配色方案

### 现代科技风
```css
background: #1a1a2e;
primary: #0075ff;
text: #f5f5f5;
```

### 温暖亲和风
```css
background: #faf8f5;
primary: #ff6b35;
text: #2d2d2d;
```

### 商务专业风
```css
background: #0f172a;
primary: #3b82f6;
text: #f1f5f9;
```

## 在 LumiLearn 中使用

### 动画生成器
```python
# animation/generators/base.py
SYSTEM_PROMPT = TASTE_SYSTEM_PROMPT
```

### 网页部署
```python
# deploy/pages/generator.py
生成landing page时自动注入审美规范
```

### Agent UI
```python
# openmanus/manus_agent.py
所有前端输出遵循Taste-Skill规范
```

## 示例

### ❌ AI 原始生成（土味审美）
```html
<div style="background: black; color: white; padding: 10px;">
  <h1 style="font-size: 30px;">标题</h1>
  <p style="font-size: 12px;">内容</p>
</div>
```

### ✅ Taste-Skill 优化后
```html
<div class="card" style="background: #1a1a2e; border-radius: 12px; padding: 24px;">
  <h1 style="font-family: Inter; font-size: 2.5rem; font-weight: 700; color: #f5f5f5;">
    标题
  </h1>
  <p style="font-size: 1rem; line-height: 1.6; color: #a0aec0;">
    内容
  </p>
</div>
```

---

**版本**: 2.2.0 | **更新**: 2026-06-05
