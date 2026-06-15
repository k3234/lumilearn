---
name: build-your-own-x
version: "1.0.0"
description: Build-Your-Own-X 手搓开源教程技能 - 提供用 C/C++/Python/JavaScript 等从零构建游戏、操作系统、浏览器、3D 渲染器等热门软件的系统化教程
tags:
  - tutorials
  - from-scratch
  - education
  - low-level
  - c
  - cpp
  - python
  - javascript
  - systems-programming
author: LumiLearn Team
license: Apache-2.0
source: https://github.com/codecrafters-io/build-your-own-x
---

# Build-Your-Own-X - 手搓开源教程技能

## 概述

本技能将 Build-Your-Own-X（GitHub 经典仓库）集成到 LumiLearn，提供**从零开始构建各种热门软件**的系统化教程。涵盖游戏、操作系统、数据库、编译器、浏览器、3D 渲染器等方向，帮助学习者通过"手搓"深入理解底层原理。

## 教学理念

```
┌─────────────────────────────────────────────────────────┐
│           "Don't just learn, BUILD IT!"                  │
│                                                          │
│   使用教程       →  完成项目       →  掌握原理           │
│   按部就班         跑通代码           举一反三           │
└─────────────────────────────────────────────────────────┘
```

## 适用场景

- **系统编程入门** - 通过手搓理解操作系统、编译器原理
- **底层技能提升** - 学习 C/C++/Rust 系统级开发
- **计算机科学深化** - 通过实践巩固理论课程
- **面试准备** - 深入理解常见技术栈的内部实现
- **项目作品集** - 完成可展示的开源项目
- **教学辅助** - 为学生提供分层递进的实践项目

## 教程分类矩阵

### 1. 编程语言

| 方向 | 语言 | 项目示例 | 难度 |
|------|------|---------|------|
| 解释器/VM | Python/C/JS | LISP、Scheme、BASIC 解释器 | ⭐⭐ |
| 编译器 | C/C++/Rust | C编译器、TypeScript 编译器 | ⭐⭐⭐⭐ |
| 字节码 VM | C/Rust | Lua VM、Stack-based VM | ⭐⭐⭐ |

### 2. 操作系统

| 方向 | 语言 | 项目示例 | 难度 |
|------|------|---------|------|
| Bootloader | C/汇编 | 极简 Bootloader | ⭐⭐⭐ |
| 内核 | C/Rust | x86 内核、微内核 | ⭐⭐⭐⭐⭐ |
| 进程调度 | C | 多任务调度器 | ⭐⭐⭐ |
| 虚拟内存 | C | 虚拟内存管理 | ⭐⭐⭐⭐ |

### 3. 网络/数据库

| 方向 | 语言 | 项目示例 | 难度 |
|------|------|---------|------|
| Web 服务器 | C/Python/Go | HTTP Server、Nginx-lite | ⭐⭐ |
| 数据库 | C++/Rust | Redis-lite、SQLite 克隆 | ⭐⭐⭐⭐ |
| 爬虫 | Python/JS | 网页爬虫 | ⭐⭐ |
| P2P 网络 | Go/C++ | BitTorrent 客户端 | ⭐⭐⭐⭐ |

### 4. 图形/游戏

| 方向 | 语言 | 项目示例 | 难度 |
|------|------|---------|------|
| 3D 渲染器 | C++/Rust | 光线追踪、OpenGL 渲染器 | ⭐⭐⭐ |
| 2D 游戏 | C++/Python | Pong、贪吃蛇、平台跳跃 | ⭐⭐ |
| 物理引擎 | C++ | 刚体物理、碰撞检测 | ⭐⭐⭐⭐ |
| GUI 框架 | C++/Rust | 极简 GUI、文本编辑器 | ⭐⭐⭐ |

### 5. 工具链

| 方向 | 语言 | 项目示例 | 难度 |
|------|------|---------|------|
| Git | Python/C | 极简版本控制 | ⭐⭐⭐ |
| Shell | C | Unix Shell | ⭐⭐⭐ |
| 文本编辑器 | C/Rust | Nano 克隆、Vim 简化版 | ⭐⭐⭐⭐ |
| 正则引擎 | C | 正则表达式匹配器 | ⭐⭐⭐⭐ |

### 6. 前端/应用

| 方向 | 语言 | 项目示例 | 难度 |
|------|------|---------|------|
| 浏览器 | Python/Rust | 极简浏览器 | ⭐⭐⭐⭐⭐ |
| 笔记应用 | JS/TS | 本地优先笔记 | ⭐⭐ |
| 聊天机器人 | Python/Node | Slack Bot、Telegram Bot | ⭐⭐ |
| 实时通信 | Go/Node | WebSocket 服务器 | ⭐⭐⭐ |

## 核心功能

### 1. 学习路径推荐

根据用户当前水平推荐合适项目：

```python
{
  "user_profile": {
    "level": "beginner|intermediate|advanced",
    "languages": ["python", "javascript"],
    "interests": ["systems", "graphics", "web"],
    "available_time": "每周5-10小时"
  },
  "recommended_path": [
    {
      "step": 1,
      "project": "用 Python 写一个 LISP 解释器",
      "duration": "2 周",
      "skills_gained": ["AST", "递归", "求值器"],
      "tutorial": "https://..."
    },
    {
      "step": 2,
      "project": "用 C 写一个 HTTP 服务器",
      "duration": "1 周",
      "skills_gained": ["Socket编程", "HTTP协议", "并发"],
      "tutorial": "https://..."
    },
    {
      "step": 3,
      "project": "用 C++ 写一个光线追踪器",
      "duration": "3 周",
      "skills_gained": ["3D数学", "光线求交", "渲染管线"],
      "tutorial": "https://..."
    }
  ]
}
```

### 2. 进度追踪

```python
{
  "learning_progress": {
    "user_id": "user_001",
    "completed_projects": [
      {
        "project": "LISP 解释器",
        "completion_date": "2026-04-15",
        "github_url": "https://github.com/user/lisp-interpreter",
        "code_quality_score": 0.85
      }
    ],
    "current_project": "HTTP 服务器",
    "current_step": "实现 POST 请求处理",
    "next_milestone": "添加并发支持"
  }
}
```

### 3. 项目脚手架生成

为每个教程自动生成项目骨架：

```bash
build-your-own-x init lisp-interpreter --lang python
# 自动创建：
# ├── src/
# │   ├── lexer.py
# │   ├── parser.py
# │   ├── evaluator.py
# │   └── main.py
# ├── tests/
# │   ├── test_lexer.py
# │   ├── test_parser.py
# │   └── test_evaluator.py
# ├── README.md  # 教程步骤
# ├── requirements.txt
# └── .gitignore
```

### 4. 代码质量评估

```python
{
  "code_quality": {
    "structure": {
      "score": 0.90,
      "feedback": "模块化良好，职责清晰"
    },
    "naming": {
      "score": 0.85,
      "feedback": "函数命名规范，少数变量可优化"
    },
    "testing": {
      "score": 0.70,
      "feedback": "建议补充边界情况测试"
    },
    "documentation": {
      "score": 0.60,
      "feedback": "缺少 docstring，建议补充模块说明"
    },
    "suggestions": [
      "为 evaluator.py 添加 docstring",
      "为 divide 函数添加边界检查",
      "补充集成测试"
    ]
  }
}
```

## 集成到 LumiLearn

### API 端点

```
GET /api/skills/build-your-own-x/projects?level=beginner&lang=python

POST /api/skills/build-your-own-x/init
{
  "project": "lisp-interpreter",
  "language": "python",
  "target_dir": "./my-projects/lisp"
}

POST /api/skills/build-your-own-x/evaluate
{
  "project_path": "./my-projects/lisp",
  "language": "python"
}

GET /api/skills/build-your-own-x/recommend?user_id=user_001
```

### 响应格式

```json
{
  "projects": [
    {
      "id": "lisp-interpreter-py",
      "name": "LISP 解释器",
      "language": "python",
      "category": "interpreters",
      "difficulty": "beginner",
      "estimated_hours": 20,
      "skills": ["AST", "递归", "求值器"],
      "tutorial_url": "https://...",
      "github_template": "https://github.com/...",
      "tags": ["interpreter", "lisp", "python"]
    }
  ],
  "total": 1
}
```

## 学习路径模板

### 模板 1: 系统程序员成长路径

```
阶段 1 (入门)        阶段 2 (进阶)         阶段 3 (高级)
─────────────────────────────────────────────────────────
LISP 解释器         HTTP 服务器           操作系统内核
正则引擎            数据库                编译器
Shell               Git 实现              虚拟机

掌握：              掌握：                掌握：
- 递归/AST          - Socket/并发         - 内核/调度
- 模式匹配          - 存储/索引           - 编译原理
- 进程管理          - 网络协议            - 系统设计
```

### 模板 2: 图形学方向路径

```
阶段 1              阶段 2                阶段 3
─────────────────────────────────────────────────────────
2D 游戏 (Pong)      2D 物理引擎           3D 光线追踪器
贪吃蛇              粒子系统              软光栅渲染器
平台跳跃            碰撞检测              GPU Shader

掌握：              掌握：                掌握：
- 游戏循环          - 物理仿真            - 线性代数
- 简单渲染          - 数学库              - 光照模型
- 事件系统          - 性能优化            - 实时渲染
```

### 模板 3: Web 全栈路径

```
阶段 1              阶段 2                阶段 3
─────────────────────────────────────────────────────────
HTTP 服务器         Todo 应用             浏览器引擎
爬虫                实时聊天              数据库
CLI 工具            REST API              Web 框架

掌握：              掌握：                掌握：
- HTTP 协议         - WebSocket           - 渲染引擎
- HTML 解析         - 数据库设计          - JavaScript 引擎
- 网络基础          - 认证授权            - 性能优化
```

## 配套资源

### 推荐教程合集

```python
{
  "tutorials": {
    "lisp_interpreter": {
      "python": "https://www.buildyourownlisp.com/",
      "c": "https://github.com/.../lisp-in-c"
    },
    "http_server": {
      "c": "https://github.com/.../tinyhttpd",
      "python": "https://ruslanspivak.com/lsbasi-part1/",
      "go": "https://github.com/.../http-server"
    },
    "raytracer": {
      "c++": "https://raytracing.github.io/",
      "rust": "https://github.com/.../raytracer"
    },
    "operating_system": {
      "rust": "https://os.phil-opp.com/",
      "c": "https://github.com/cfenollosa/os-tutorial"
    },
    "git": {
      "python": "https://wyag.thb.lt/",
      "go": "https://github.com/.../git-go"
    }
  }
}
```

### 评估工具

```python
{
  "evaluation": {
    "auto_tests": "运行测试套件验证功能",
    "code_review": "静态分析 + LLM 评审",
    "performance_benchmark": "性能指标对比",
    "code_quality_score": "PEP8/ESLint 规范检查"
  }
}
```

## 教学场景示例

### 场景 1: K12 编程教学

```
教师: 为高中生设计 12 周的"手搓软件"课程

LumiLearn Build-Your-Own-X:
1. 第 1-2 周: 用 Python 写 LISP 解释器
2. 第 3-4 周: 用 Python 写 HTTP 服务器
3. 第 5-6 周: 用 JS 写 2D 游戏
4. 第 7-8 周: 用 Python 写爬虫
5. 第 9-10 周: 用 C 写正则引擎
6. 第 11-12 周: 综合项目

每个项目配套：
- 分步教程
- 自动评测
- 代码评审
- 学习证书
```

### 场景 2: 大学生自学

```
学生: 想转码成为系统程序员

LumiLearn Build-Your-Own-X 推荐路径:
1. 评估当前水平：会 Python，了解 C
2. 推荐项目：
   - LISP 解释器（练 AST）
   - HTTP 服务器（练系统调用）
   - 简易 Shell（练进程管理）
   - 数据库（练存储引擎）
3. 每周完成一个项目
4. 4 个月后具备系统编程基础
```

### 场景 3: 面试准备

```
求职者: 准备系统设计面试

LumiLearn Build-Your-Own-X:
1. 推荐做：Redis 简化版、SQLite 简化版
2. 重点练习：
   - 数据结构设计
   - 性能优化
   - 边界情况处理
3. 生成作品集文档
4. 模拟面试问答
```

## 集成到 LumiLearn AI-Collab

```python
# skills/build-your-own-x/integration.py

class BuildYourOwnXAgent:
    """手搓教程推荐 Agent"""

    def recommend_project(self, user_profile: dict) -> list:
        """根据用户画像推荐项目"""
        pass

    def generate_scaffold(self, project: str, lang: str) -> str:
        """生成项目脚手架"""
        pass

    def evaluate_submission(self, project_path: str) -> dict:
        """评估用户提交"""
        pass

# 注册到 AI-Collab
orchestrator.register_agent(
    "BuildXAgent",
    BuildYourOwnXAgent()
)
```

## 配置说明

```python
# config/build_your_own_x.json
{
  "build_your_own_x": {
    "enabled": true,
    "tutorial_cache_dir": "./.tutorials",
    "auto_evaluate": true,
    "github_integration": {
      "enabled": true,
      "default_branch": "main"
    },
    "supported_languages": [
      "python", "javascript", "typescript",
      "c", "cpp", "rust", "go"
    ],
    "recommendation_engine": {
      "strategy": "skill_progression",
      "min_projects_to_advance": 3
    }
  }
}
```

## 相关资源

- [Build-Your-Own-X GitHub](https://github.com/codecrafters-io/build-your-own-x)
- [Writing a Simple Operating System — from Scratch](https://www.cs.bham.ac.uk/~exr/lectures/opsys/10_11/lectures/os-dev.pdf)
- [Ray Tracing in One Weekend](https://raytracing.github.io/)
- [Write a Lisp Interpreter in Python](https://www.buildyourownlisp.com/)

## 更新日志

### v1.0.0 (2026-06-01)
- 初始版本
- 涵盖 6 大类共 30+ 教程项目
- 支持 7 种编程语言
- 集成 AI-Collab 协调器
- 自动项目脚手架生成
- 代码质量评估功能
