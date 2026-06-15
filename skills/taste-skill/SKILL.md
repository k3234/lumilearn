# Taste-Skill - 前端审美注入系统

## 元信息

- **名称**: taste-skill
- **版本**: 2.2.0
- **来源**: [leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) (22K+ Stars)
- **作者**: Leonxlnx & CursorAgent
- **类型**: AI Coding Agent 审美增强
- **标签**: frontend, design, ui, ux, aesthetics

## 核心价值

**问题**: AI 生成的界面总是"AI味"太重，土味配色、千篇一律的布局

**解决方案**: 给 AI 注入顶级设计师和前端工程师的审美经验、落地规则

## 核心能力

### 1. 配色系统

**约束规则**:
```
1. 禁止使用纯黑 (#000000) 和纯白 (#FFFFFF)
2. 主色调使用深色背景 + 高对比度强调色
3. 遵循 60-30-10 法则（主色60%、次色30%、强调色10%）
4. 使用专业配色方案而非随机组合
```

**推荐配色方案**:
- **现代科技风**: 深灰 #1a1a2e + 科技蓝 #0075ff + 亮白 #f5f5f5
- **温暖亲和风**: 米白 #faf8f5 + 暖橙 #ff6b35 + 深棕 #2d2d2d
- **极简纯净风**: 纯白 #ffffff + 极黑 #000000 + 一点亮色
- **商务专业风**: 深蓝 #0f172a + 商务蓝 #3b82f6 + 浅灰 #f1f5f9

### 2. 字体层级

**约束规则**:
```
1. 标题必须使用专业字体族（Inter, SF Pro, Roboto）
2. 正文字号最小 14px，行高 1.5-1.7
3. 层级对比要明显（标题 2xl-3xl, 正文 base-lg）
4. 禁止使用系统默认字体或 emoji 字体
```

**字体规范**:
```css
/* 推荐 */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;

/* 层级 */
h1: 2.5rem (40px), font-weight: 700
h2: 2rem (32px), font-weight: 600
h3: 1.5rem (24px), font-weight: 600
body: 1rem (16px), font-weight: 400
caption: 0.875rem (14px), font-weight: 400
```

### 3. 间距系统

**约束规则**:
```
1. 使用 4px 或 8px 基准网格
2. 组件内间距: 8px, 12px, 16px, 24px, 32px
3. 组件间间距: 16px, 24px, 32px, 48px, 64px
4. 禁止使用奇数值间距（5px, 7px, 13px）
```

**间距层级**:
```css
/* 8px 基准 */
space-1: 4px   /* 紧凑 */
space-2: 8px   /* 基础 */
space-3: 16px  /* 舒适 */
space-4: 24px  /* 宽松 */
space-5: 32px  /* 分隔 */
space-6: 48px  /* 章节 */
space-7: 64px  /* 大区块 */
```

### 4. 动效原则

**约束规则**:
```
1. 所有交互必须有反馈（hover, active, focus）
2. 过渡时间 150-300ms，使用 ease-out 或 ease-in-out
3. 禁止使用 linear 动画
4. 微妙动效优于夸张动效
```

**动效模板**:
```css
/* 推荐 */
transition: all 200ms ease-out;
transform: translateY(-2px);

/* 禁止 */
transition: all 1s linear;
animation: bounce 2s infinite;
```

### 5. 布局原则

**约束规则**:
```
1. 使用栅格系统（12列或8列）
2. 卡片式布局，阴影柔和（0 4px 6px rgba(0,0,0,0.1)）
3. 圆角统一（4px, 8px, 12px, 16px）
4. 避免过多的边框和分割线
```

**布局模板**:
```css
/* 卡片 */
.card {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  padding: 24px;
}

/* 容器 */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}
```

## 使用方式

### 作为系统提示词注入

将以下内容添加到 AI 的系统提示词中：

```
【前端审美规范 - Taste-Skill】
你是一位拥有10年经验的高级前端工程师和UI设计师。在生成任何前端代码时，必须遵循以下审美规范：

1. **配色**: 禁止纯黑纯白，使用专业配色方案
2. **字体**: 使用 Inter/SF Pro 等专业字体，设置清晰的层级
3. **间距**: 基于 8px 网格，使用标准间距层级
4. **动效**: 所有交互有反馈，过渡 150-300ms
5. **布局**: 卡片式设计，柔和阴影，统一圆角

每行代码都要问自己："这看起来像认真设计的吗？"
```

### 实践检查清单

生成前端代码后，逐项检查：

- [ ] 配色不是纯黑/纯白
- [ ] 使用了专业字体族
- [ ] 间距基于 8px 网格
- [ ] 所有交互有动效反馈
- [ ] 布局使用卡片或栅格
- [ ] 阴影柔和自然
- [ ] 圆角风格统一
- [ ] 没有过度装饰

## 与 LumiLearn 集成

### 应用场景

1. **动画生成器**: 生成的教学动画需要专业UI
2. **网页部署**: 生成的 landing page 需要高颜值
3. **用户界面**: Agent 的交互界面需要设计感

### 集成方式

在 `animation/generators/base.py` 或相关UI生成代码中注入审美规则：

```python
TASTE_SYSTEM_PROMPT = """
你生成的所有前端代码必须遵循 Taste-Skill 审美规范...
"""
```

## 参考资源

- GitHub: https://github.com/Leonxlnx/taste-skill
- 官方文档: 配色系统、字体层级、间距规范、动效库
- 示例项目: examples/ 目录

---

*版本: 2.2.0 | 更新: 2026-06-05*
