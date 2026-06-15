# Impeccable 快速使用指南

## 什么是 Impeccable?

Impeccable 是一款专为 AI 编码助手打造的前端设计技能包，内置 20 个设计命令和反模式库，让 AI 学会大厂级的响应式设计。

**GitHub**: 10K+ Stars ⭐
**来源**: [pbakaus/impeccable](https://github.com/pbakaus/impeccable)
**作者**: Paul Bakaus (前 Google 开发者布道师)

## 核心能力

1. **20 个设计命令** - 每个命令解决特定设计问题
2. **反模式库** - 内置"DO NOT"约束，精准狙击常见错误
3. **标准断点系统** - 专业的响应式断点规范
4. **栅格系统** - 12列专业栅格
5. **触摸友好** - 移动端体验优化

## 快速开始

### 方法 1: 使用 Slash Commands

在 AI 编程助手中直接调用命令：

```
/impeccable-responsive    # 添加完整的响应式支持
/impeccable-mobile        # 优化移动端体验
/impeccable-layout        # 审计并优化布局结构
/impeccable-grid          # 应用专业栅格系统
/impeccable-typography    # 优化字体层级
/impeccable-animation     # 添加流畅动效
/impeccable-hover         # 优化悬停状态
/impeccable-focus         # 优化焦点状态（无障碍）
```

### 方法 2: 自动应用规范

在生成响应式代码时，自动检查以下清单：

- [ ] 使用正确的盒模型 (border-box)
- [ ] 定义标准断点 (sm:640, md:768, lg:1024, xl:1280)
- [ ] 触摸目标 ≥ 44x44px
- [ ] 避免 overflow-x: hidden 反模式
- [ ] 使用 CSS Grid 或 Flexbox
- [ ] 所有交互有焦点状态样式
- [ ] 使用流体 typography (clamp())

### 方法 3: 在 Python 中集成

```python
from lumilearn.skills.impeccable import (
    IMPECCABLE_SYSTEM_PROMPT,
    IMPECCABLE_CHECKLIST,
    get_slash_commands
)

# 在 AI 调用时注入规范
response = call_ai_model(prompt + IMPECCABLE_SYSTEM_PROMPT)

# 生成后检查
if not check_impeccable(code):
    code = await fix_impeccable_issues(code)
```

## 命令详解

### 布局命令
```
/impeccable-layout    # 审计整体布局结构
/impeccable-grid      # 应用 12 列栅格系统
/impeccable-stack     # 垂直堆叠布局
/impeccable-split     # 水平分割布局
/impeccable-center    # 完美居中
```

### 响应式命令
```
/impeccable-responsive  # 完整响应式支持
/impeccable-breakpoints # 标准断点定义
/impeccable-fluid      # 流体 typography
/impeccable-mobile     # 移动端优化
/impeccable-touch      # 触摸友好交互
```

### 视觉命令
```
/impeccable-typography  # 字体层级优化
/impeccable-spacing     # 一致间距系统
/impeccable-colors      # 配色优化
/impeccable-shadows     # 柔和阴影
/impeccable-borders     # 边框优化
/impeccable-radii       # 统一圆角
```

### 交互命令
```
/impeccable-animation   # 微交互动效
/impeccable-hover        # 悬停反馈
/impeccable-focus        # 焦点状态
/impeccable-loading      # 加载状态
```

## 标准断点

```css
/* 移动优先 */
--breakpoint-sm: 640px;   /* 大手机 */
--breakpoint-md: 768px;   /* 平板 */
--breakpoint-lg: 1024px;  /* 小笔记本 */
--breakpoint-xl: 1280px;  /* 桌面 */
--breakpoint-2xl: 1536px; /* 大屏 */
```

## 反模式 (DO NOT)

### ❌ 禁止
```css
body {
  overflow-x: hidden;  /* 破坏布局 */
}

* {
  box-sizing: content-box;  /* 错误 */
}

@media (max-width: 768px) {
  .container {
    width: 100vw;  /* 产生滚动条 */
  }
}
```

### ✅ 推荐
```css
body {
  overflow-x: clip;  /* 现代方案 */
}

* {
  box-sizing: border-box;  /* 正确 */
}

@media (max-width: 768px) {
  .container {
    width: 100%;
    padding: 0 16px;
  }
}
```

## 在 LumiLearn 中使用

### 响应式教学页面
```python
# 生成的课程页面自动响应式
/impeccable-responsive
/impeccable-mobile
```

### 动画播放器
```python
# 播放控制界面响应式设计
/impeccable-touch
/impeccable-animation
```

### 管理后台
```python
# 仪表盘和表单响应式
/impeccable-grid
/impeccable-breakpoints
```

## 示例

### ❌ AI 原始生成（响应式问题）
```html
<div style="width: 1200px; margin: 0 auto;">
  <div style="width: 33%; float: left;">列1</div>
  <div style="width: 33%; float: left;">列2</div>
  <div style="width: 33%; float: left;">列3</div>
</div>
```

### ✅ Impeccable 优化后
```html
<div class="grid" style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 24px;">
  <div class="col-4" style="grid-column: span 4;">
    列1
  </div>
  <div class="col-4" style="grid-column: span 4;">
    列2
  </div>
  <div class="col-4" style="grid-column: span 4;">
    列3
  </div>
</div>

<style>
@media (max-width: 768px) {
  [class*="col-"] {
    grid-column: span 12;
  }
}
</style>
```

---

**版本**: 1.0.0 | **更新**: 2026-06-05
