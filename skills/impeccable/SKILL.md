# Impeccable - 大厂级响应式设计技能包

## 元信息

- **名称**: impeccable
- **版本**: 1.0.0
- **来源**: [pbakaus/impeccable](https://github.com/pbakaus/impeccable) (10K+ Stars)
- **作者**: Paul Bakaus (前 Google 开发者布道师)
- **类型**: AI Coding Agent 响应式设计增强
- **标签**: frontend, responsive, design, best-practices, slash-commands

## 核心价值

**问题**: AI 生成的响应式设计经常踩坑，移动端体验差，布局逻辑有死角

**解决方案**: 内置 17-20 个设计命令和反模式库，让 AI 学会大厂级的响应式设计规范

## 核心能力

### 1. 设计命令系统 (Slash Commands)

Impeccable 提供 20 个专门的设计命令，每个命令解决特定设计问题：

#### 布局类命令

```
/impeccable-layout      # 审计并优化整体布局结构
/impeccable-grid        # 应用专业栅格系统（12列/8列）
/impeccable-stack       # 创建垂直堆叠布局
/impeccable-split       # 创建水平分割布局（左右/上下）
/impeccable-center      # 完美居中任何内容
```

#### 响应式命令

```
/impeccable-responsive  # 添加完整的响应式断点
/impeccable-breakpoints # 定义标准断点（sm/md/lg/xl/2xl）
/impeccable-fluid       # 流体 typography 和 spacing
/impeccable-mobile      # 优化移动端体验
/impeccable-touch       # 添加触摸友好交互
```

#### 视觉类命令

```
/impeccable-typography  # 优化字体层级和可读性
/impeccable-spacing     # 应用一致的间距系统
/impeccable-colors      # 优化配色方案
/impeccable-shadows     # 添加柔和自然的阴影
/impeccable-borders     # 优化边框和分割线
/impeccable-radii       # 应用统一的圆角风格
```

#### 交互类命令

```
/impeccable-animation   # 添加流畅的微交互动效
/impeccable-hover       # 优化悬停状态反馈
/impeccable-focus       # 优化焦点状态（无障碍）
/impeccable-loading     # 添加优雅的加载状态
```

### 2. 反模式库 (DO NOT)

#### 绝对禁止的写法

```css
/* ❌ 禁止 */
body {
  overflow-x: hidden;  /* 隐藏溢出，破坏布局 */
}

* {
  box-sizing: content-box;  /* 应该用 border-box */
}

@media (max-width: 768px) {
  .container {
    width: 100vw;  /* 会产生滚动条 */
  }
}
```

#### 推荐替代方案

```css
/* ✅ 推荐 */
body {
  overflow-x: clip;  /* 现代浏览器的解决方案 */
}

* {
  box-sizing: border-box;  /* 统一盒模型 */
}

@media (max-width: 768px) {
  .container {
    width: 100%;
    padding: 0 16px;  /* 使用内边距而非溢出 */
  }
}
```

### 3. 标准断点系统

```css
/* 移动优先断点 */
--breakpoint-sm: 640px;   /* 大手机 */
--breakpoint-md: 768px;   /* 平板 */
--breakpoint-lg: 1024px;  /* 小笔记本 */
--breakpoint-xl: 1280px;  /* 桌面 */
--breakpoint-2xl: 1536px; /* 大屏 */

/* 使用示例 */
.element {
  /* 基础（手机） */
  width: 100%;
  padding: 16px;
  
  /* 平板及以上 */
  @media (min-width: 768px) {
    width: 50%;
    padding: 24px;
  }
  
  /* 桌面及以上 */
  @media (min-width: 1024px) {
    width: 33.333%;
    padding: 32px;
  }
}
```

### 4. 栅格系统

```css
/* 12 列栅格 */
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 24px;
}

/* 常用列宽 */
.col-1 { grid-column: span 1; }
.col-2 { grid-column: span 2; }
.col-3 { grid-column: span 3; }
.col-4 { grid-column: span 4; }  /* 1/3 */
.col-6 { grid-column: span 6; }  /* 1/2 */
.col-8 { grid-column: span 8; } /* 2/3 */
.col-12 { grid-column: span 12; } /* 全宽 */

/* 响应式列 */
@media (max-width: 768px) {
  [class*="col-"] {
    grid-column: span 12;
  }
}
```

### 5. 触摸友好设计

```css
/* 触摸目标最小 44x44px */
.touch-target {
  min-height: 44px;
  min-width: 44px;
  padding: 12px 16px;
}

/* 移动端优化 */
@media (hover: none) and (pointer: coarse) {
  /* 触摸设备特定样式 */
  .button {
    padding: 16px 24px;  /* 更大的触摸区域 */
    font-size: 16px;      /* 防止 iOS 缩放 */
  }
}
```

## 使用方式

### 命令行调用

在 AI 编程助手中直接调用命令：

```
/impeccable-responsive    # 添加响应式支持
/impeccable-mobile        # 优化移动端
/impeccable-layout        # 审计布局
```

### 自动触发

在生成前端代码时，自动应用以下检查：

```javascript
const IMPECCABLE_CHECKLIST = [
  "是否使用了正确的盒模型 (border-box)?",
  "是否定义了标准断点?",
  "是否有触摸友好的交互元素 (≥44px)?",
  "是否避免了 overflow-x: hidden 反模式?",
  "是否使用了流体 typography?",
  "是否添加了焦点状态样式?",
  "是否使用了 CSS Grid 或 Flexbox 布局?",
  "是否避免了固定宽度 (px) 在流式布局中?"
];
```

### 完整示例

```html
<!-- ✅ Impeccable 风格的卡片组件 -->
<div class="card" role="article">
  <div class="card-content">
    <h2 class="card-title">标题</h2>
    <p class="card-description">描述内容</p>
  </div>
  <button class="card-action touch-target">操作</button>
</div>

<style>
.card {
  /* 基础样式 */
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  
  /* 响应式 */
  @media (min-width: 768px) {
    flex-direction: row;
    align-items: center;
  }
}

.card-action {
  /* 触摸友好 */
  min-height: 44px;
  min-width: 44px;
  padding: 12px 24px;
  
  /* 交互反馈 */
  transition: all 200ms ease-out;
}

.card-action:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px -2px rgba(0, 0, 0, 0.15);
}

.card-action:focus-visible {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}
</style>
```

## 与 LumiLearn 集成

### 应用场景

1. **动画播放器**: 生成的播放界面需要响应式设计
2. **教学页面**: 不同设备上的学习体验一致性
3. **管理后台**: 响应式仪表盘和表单
4. **用户界面**: Agent 生成的所有页面

### 集成方式

在响应式设计相关的代码生成器中注入：

```python
IMPECCABLE_SYSTEM_PROMPT = """
你生成的所有响应式前端代码必须遵循 Impeccable 规范：

1. 使用标准断点系统 (sm:640, md:768, lg:1024, xl:1280, 2xl:1536)
2. 触摸目标 ≥ 44x44px
3. 避免 overflow-x: hidden 反模式
4. 使用 CSS Grid 或 Flexbox
5. 所有交互有焦点状态 (无障碍)
6. 流体 typography (clamp())

开始生成前先运行 /impeccable-layout 审计结构。
"""
```

## 参考资源

- GitHub: https://github.com/pbakaus/impeccable
- 安装: npx skills add pbakaus/impeccable
- 作者: Paul Bakaus (前 Google 开发者布道师)

---

*版本: 1.0.0 | 更新: 2026-06-05*
