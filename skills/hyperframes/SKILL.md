---
name: hyperframes
version: "1.0.0"
description: HyperFrames 视频生成技能 - 为 LumiLearn 教学内容生成 HTML 动画视频
tags:
  - video-generation
  - animation
  - html
  - education
  - manim
author: LumiLearn Team
license: Apache-2.0
---

# HyperFrames - 教学内容视频生成技能

## 概述

本技能将 HyperFrames (HeyGen 开源的视频生成框架) 集成到 LumiLearn，为教学内容自动生成高质量的动画视频。支持数学公式动画、概念可视化、过程演示等多种教育场景。

## 适用场景

- **数学公式推导** - 动态展示公式演变过程
- **概念可视化** - 将抽象概念转化为视觉动画
- **实验演示** - 物理/化学实验过程模拟
- **数据图表** - 动态数据可视化
- **时间线展示** - 历史事件或发展过程

## 核心功能

### 1. 教学内容分析

自动分析教学内容，确定最适合的动画类型：

```python
{
  "animation_type": "formula",  # concept|process|comparison|formula|chart|3d_model
  "difficulty": "中等",
  "estimated_duration": 30,
  "scenes": 5,
  "key_points": ["公式推导", "变量说明", "结果展示"]
}
```

### 2. 分镜脚本生成

为每个教学内容生成详细的分镜脚本：

```json
{
  "storyboard": [
    {
      "shot_number": 1,
      "duration": 5,
      "scene_description": "标题展示",
      "narration": "今天我们来学习勾股定理",
      "visual_elements": ["标题文字", "直角三角形图标"],
      "transition": "淡入"
    },
    {
      "shot_number": 2,
      "duration": 15,
      "scene_description": "公式推导动画",
      "narration": "在直角三角形中，a² + b² = c²",
      "visual_elements": ["直角三角形", "边长标注", "公式动画"],
      "transition": "缩放"
    }
  ]
}
```

### 3. HTML/Manim 代码生成

生成可直接渲染的动画代码：

```html
<!-- HyperFrames HTML 格式 -->
<div id="stage" data-composition-id="pythagorean-theorem" 
     data-width="1920" data-height="1080">
  
  <!-- 标题场景 -->
  <div class="scene" data-start="0" data-duration="5">
    <h1 class="title" data-animation="fadeIn">
      勾股定理
    </h1>
  </div>
  
  <!-- 公式动画 -->
  <div class="scene" data-start="5" data-duration="15">
    <svg id="triangle" viewBox="0 0 400 300">
      <!-- 直角三角形动画 -->
      <path d="M 50,250 L 350,250 L 50,50 Z" 
            data-animation="draw" data-duration="3"/>
      <!-- 边长标注 -->
      <text x="200" y="270" data-animation="fadeIn" data-delay="3">a</text>
      <text x="30" y="150" data-animation="fadeIn" data-delay="4">b</text>
      <text x="220" y="130" data-animation="fadeIn" data-delay="5">c</text>
    </svg>
    
    <!-- 公式展示 -->
    <div class="formula" data-animation="typewriter" data-delay="6">
      a² + b² = c²
    </div>
  </div>
</div>
```

### 4. 视频渲染

通过 HyperFrames CLI 渲染为 MP4：

```bash
npx hyperframes render \
  --input ./output/lesson.html \
  --output ./output/lesson.mp4 \
  --fps 30 \
  --quality high
```

## 动画类型支持

| 类型 | 适用场景 | 示例 |
|------|---------|------|
| **formula** | 公式推导 | 数学公式逐步展示 |
| **concept** | 概念可视化 | 抽象概念具象化 |
| **process** | 过程演示 | 实验步骤、算法流程 |
| **comparison** | 对比分析 | 不同方法的优劣对比 |
| **chart** | 数据可视化 | 动态图表、趋势展示 |
| **3d_model** | 立体展示 | 几何体、分子结构 |

## 集成到 LumiLearn

### API 端点

```
POST /api/skills/hyperframes/generate
{
  "content": "勾股定理：在直角三角形中，两条直角边的平方和等于斜边的平方",
  "title": "勾股定理",
  "subject": "数学",
  "duration": 30,
  "style": "educational",
  "resolution": "1920x1080"
}
```

### 响应格式

```json
{
  "storyboard": [...],
  "html_code": "...",
  "render_command": "npx hyperframes render ...",
  "estimated_render_time": "2分钟",
  "preview_url": "http://localhost:3000/preview/...",
  "video_url": "http://localhost:3000/output/..."
}
```

## 使用示例

### 示例 1: 数学公式动画

```
用户: 为"二次函数图像"生成教学视频

AI: 
1. 分析内容 - 确定使用 formula + chart 组合
2. 生成分镜:
   - 场景1: 函数定义 (5s)
   - 场景2: 抛物线绘制动画 (10s)
   - 场景3: 顶点、开口方向说明 (10s)
   - 场景4: 实例演示 (5s)

3. 生成 HTML 代码:
   [包含 GSAP 动画的完整 HTML]

4. 渲染视频:
   npx hyperframes render --input quadratic.html --output quadratic.mp4
```

### 示例 2: 物理实验模拟

```
用户: 生成"自由落体运动"实验视频

AI:
1. 分析 - 使用 process 类型
2. 生成分镜:
   - 场景1: 实验介绍
   - 场景2: 装置展示
   - 场景3: 下落过程慢动作
   - 场景4: 数据记录
   - 场景5: 结论总结

3. 生成代码:
   [包含物理引擎模拟的 HTML]
```

## 技术架构

```
┌─────────────────────────────────────────────────────┐
│                 LumiLearn API                        │
│  ┌──────────────┐        ┌──────────────────────┐  │
│  │ 内容分析模块  │ ─────> │ HyperFrames 生成器   │  │
│  └──────────────┘        └──────────────────────┘  │
│                                   │                 │
│                                   ▼                 │
│  ┌─────────────────────────────────────────────┐   │
│  │           HyperFrames CLI                    │   │
│  │  - HTML 渲染                                 │   │
│  │  - Puppeteer + FFmpeg                        │   │
│  │  - MP4 输出                                  │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## 配置要求

### 系统依赖

```bash
# Node.js >= 22
node --version

# FFmpeg
ffmpeg -version

# HyperFrames CLI
npm install -g hyperframes
```

### LumiLearn 配置

```python
# config.json
{
  "skills": {
    "hyperframes": {
      "enabled": true,
      "cli_path": "npx hyperframes",
      "output_dir": "./videos",
      "default_resolution": "1920x1080",
      "default_fps": 30
    }
  }
}
```

## 性能优化

### 渲染优化

- **分辨率自适应** - 根据内容复杂度调整
- **并行渲染** - 批量生成时并行处理
- **缓存机制** - 相同内容直接返回缓存

### 存储优化

- **视频压缩** - 使用 H.264/H.265 编码
- **分段存储** - 大视频分段存储
- **CDN 分发** - 生产环境使用 CDN

## 与现有动画生成对比

| 功能 | 现有 Manim 生成 | HyperFrames 集成 |
|------|----------------|------------------|
| 输出格式 | Python 代码 | HTML + MP4 |
| 渲染方式 | Manim 引擎 | HyperFrames CLI |
| 预览方式 | 需运行代码 | 浏览器实时预览 |
| 交互性 | 低 | 高 (Web 原生) |
| 学习曲线 | 高 (需学 Manim) | 低 (HTML/CSS) |
| 适用场景 | 数学/科学 | 通用教育内容 |

## 建议集成方案

### 方案 A: 并排使用 (推荐)

- **Manim** - 复杂数学公式、3D 可视化
- **HyperFrames** - 通用教学视频、交互内容

### 方案 B: 完全迁移

逐步将动画生成从 Manim 迁移到 HyperFrames，统一技术栈。

## 相关资源

- [HyperFrames GitHub](https://github.com/heygen-com/hyperframes)
- [HyperFrames 文档](https://hyperframes.heygen.com/)
- [GSAP 动画文档](https://greensock.com/gsap/)
- [教学视频设计指南](https://...)

## 更新日志

### v1.0.0 (2026-05-21)
- 初始版本
- 支持 6 种动画类型
- 集成 HyperFrames CLI
- 支持实时预览和渲染
