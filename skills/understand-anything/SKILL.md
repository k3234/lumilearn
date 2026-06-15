---
name: understand-anything
version: "1.0.0"
description: Understand-Anything 代码库理解技能 - 将 AI 生成的"屎山"代码和文档转化为知识图谱（文件/概念/问题节点关系），辅助 Claude Code/Cursor/Copilot 等 AI 编程工具
tags:
  - code-understanding
  - knowledge-graph
  - ai-coding
  - documentation
  - code-analysis
  - learning
author: LumiLearn Team
license: Apache-2.0
source: https://github.com/.../understand-anything (20.1K Star)
---

# Understand-Anything - 代码库理解技能

## 概述

本技能将 Understand-Anything（GitHub 20.1K Star）集成到 LumiLearn，**把 AI 生成的"屎山"代码库和文档变成知识图谱**。通过构建文件节点、概念节点、问题节点及其关系网络，让 AI 编程工具能够基于结构化知识回答问题，避免在迷宫式代码库中迷失方向。

## 核心理念

```
┌─────────────────────────────────────────────────────────┐
│            不只是列出文件，而是理解关系                    │
│                                                          │
│   传统方式：                                             │
│   - 列出 1000 个文件 → 用户无从下手                       │
│                                                          │
│   Understand-Anything：                                  │
│   - 入口文件 → 核心概念 → 关键问题 → 关联模块             │
│   - 围绕图谱节点提问，AI 答案可验证                       │
└─────────────────────────────────────────────────────────┘
```

## 适用场景

- **接手 AI 生成的代码** - 快速理解混乱的项目结构
- **学习大型开源项目** - 系统化梳理依赖关系
- **代码审查** - 从"概念完整性"角度审查代码
- **技术债务识别** - 通过节点关系发现设计问题
- **AI 助手增强** - 让 Claude Code/Cursor 有"项目地图"
- **新人 onboarding** - 知识图谱作为入门指南
- **架构重构规划** - 通过概念关系评估重构影响

## 核心节点类型

### 1. 文件节点 (File Node)

```python
{
  "file_node": {
    "id": "file_train_py",
    "path": "./framework/trainer.py",
    "type": "python_source",
    "size_lines": 234,
    "complexity": "high",
    "responsibility": "训练循环与优化器管理",
    "imports": ["torch", "framework.model", "framework.data"],
    "imported_by": ["train.py", "scripts/auto_train.py"],
    "key_symbols": ["Trainer", "train_step", "evaluate"],
    "ai_generated_score": 0.85  // 估计为 AI 生成的概率
  }
}
```

### 2. 概念节点 (Concept Node)

```python
{
  "concept_node": {
    "id": "concept_bpe_tokenizer",
    "name": "BPE Tokenizer",
    "category": "技术概念",
    "definition": "字节对编码（Byte Pair Encoding）分词算法",
    "files_containing": [
      "framework/tokenizer.py",
      "framework/bpe_tokenizer.json"
    ],
    "related_concepts": [
      "concept_vocabulary",
      "concept_subword_tokenization"
    ],
    "documentation_refs": [
      "docs/learning_journey/Module_4.3_Prompt工程.md"
    ]
  }
}
```

### 3. 问题节点 (Question Node)

```python
{
  "question_node": {
    "id": "q_001",
    "question": "为什么我的模型在训练时 loss 不下降？",
    "category": "调试类问题",
    "related_files": [
      "framework/trainer.py",
      "framework/optimizer.py"
    ],
    "related_concepts": [
      "concept_learning_rate",
      "concept_gradient_descent"
    ],
    "possible_answers": [
      "学习率过大/过小",
      "数据预处理问题",
      "模型架构问题"
    ],
    "verified": true,
    "answer_accuracy": 0.85
  }
}
```

### 4. 关系类型

```python
{
  "relationships": [
    {
      "from": "file_train_py",
      "to": "file_model_py",
      "type": "imports",
      "weight": 5
    },
    {
      "from": "concept_bpe_tokenizer",
      "to": "concept_vocabulary",
      "type": "uses",
      "weight": 3
    },
    {
      "from": "q_001",
      "to": "concept_learning_rate",
      "type": "answered_by",
      "weight": 1
    },
    {
      "from": "file_train_py",
      "to": "q_001",
      "type": "addresses",
      "weight": 1
    }
  ]
}
```

## 核心功能

### 1. 项目知识图谱生成

自动从代码库和文档生成知识图谱：

```python
{
  "generation_pipeline": {
    "step_1_file_analysis": {
      "tool": "AST 解析 + 静态分析",
      "outputs": ["file_nodes", "symbol_index", "import_graph"]
    },
    "step_2_concept_extraction": {
      "tool": "LLM 概念提取",
      "inputs": ["file_summaries", "doc_files"],
      "outputs": ["concept_nodes", "concept_relations"]
    },
    "step_3_question_mining": {
      "tool": "从代码注释/文档/Issues 提取",
      "outputs": ["question_nodes", "qa_pairs"]
    },
    "step_4_graph_build": {
      "tool": "NetworkX + 可视化",
      "outputs": ["knowledge_graph.json", "graph.html"]
    }
  }
}
```

### 2. 智能问答

基于图谱回答用户问题：

```python
class UnderstandAnything:
    def ask(self, question: str) -> dict:
        """基于知识图谱回答问题"""
        # 1. 识别问题涉及的概念
        concepts = self.extract_concepts(question)
        # 2. 在图谱中查找相关节点
        related_nodes = self.graph.find_related(concepts)
        # 3. 用 LLM 整合上下文生成答案
        answer = self.llm.synthesize(question, related_nodes)
        # 4. 提供答案来源链接
        return {
            "answer": answer,
            "sources": [node.to_dict() for node in related_nodes],
            "confidence": self.assess_confidence(related_nodes)
        }
```

### 3. 代码导航

通过图谱找到相关代码位置：

```python
def navigate_to(self, target: str) -> NavigationPath:
    """导航到代码的指定位置"""
    return NavigationPath(
        entry_points=[...],          # 推荐入口文件
        core_modules=[...],          # 核心模块
        related_concepts=[...],      # 涉及的概念
        key_questions=[...],         # 推荐先看的问题
        step_by_step_guide=[...]     # 详细路径
    )
```

### 4. AI 编程工具集成

通过 MCP 协议为 AI 工具提供图谱查询能力：

```json
{
  "mcp_tools": [
    {
      "name": "ua_ask",
      "description": "基于项目知识图谱回答问题",
      "inputSchema": {
        "type": "object",
        "properties": {
          "question": {"type": "string"},
          "include_sources": {"type": "boolean", "default": true}
        }
      }
    },
    {
      "name": "ua_navigate",
      "description": "导航到指定概念或问题相关的代码",
      "inputSchema": {
        "type": "object",
        "properties": {
          "target": {"type": "string", "description": "概念名/问题/文件名"}
        }
      }
    },
    {
      "name": "ua_get_concept",
      "description": "获取概念的详细信息和关联",
      "inputSchema": {
        "type": "object",
        "properties": {
          "concept": {"type": "string"}
        }
      }
    },
    {
      "name": "ua_get_questions",
      "description": "获取与目标相关的常见问题",
      "inputSchema": {
        "type": "object",
        "properties": {
          "file": {"type": "string"},
          "concept": {"type": "string"}
        }
      }
    },
    {
      "name": "ua_explore",
      "description": "探索知识图谱（从入口点开始）",
      "inputSchema": {
        "type": "object",
        "properties": {
          "start_node": {"type": "string", "default": "entry_point"},
          "max_depth": {"type": "integer", "default": 3}
        }
      }
    }
  ]
}
```

## 集成到 LumiLearn

### API 端点

```
POST /api/skills/understand-anything/build
{
  "project_root": "./lumilearn",
  "include_docs": true,
  "include_issues": false
}

POST /api/skills/understand-anything/ask
{
  "question": "BPE tokenizer 是如何训练的？",
  "max_sources": 5
}

POST /api/skills/understand-anything/navigate
{
  "target": "concept_bpe_tokenizer"
}
```

### 响应格式

```json
{
  "graph_build_result": {
    "total_nodes": 234,
    "total_edges": 567,
    "by_type": {
      "file": 89,
      "concept": 67,
      "question": 78
    },
    "graph_visualization": "./.ua/graph.html"
  },
  "ask_result": {
    "answer": "BPE Tokenizer 通过迭代合并最高频的字符对来构建词汇表...",
    "sources": [
      {
        "type": "file",
        "path": "framework/tokenizer.py",
        "snippet": "def train_bpe(corpus, vocab_size=8000): ..."
      },
      {
        "type": "concept",
        "name": "BPE Tokenizer",
        "definition": "字节对编码分词算法"
      }
    ],
    "confidence": 0.92,
    "related_questions": [
      "如何调整 vocab_size 的大小？",
      "BPE 和 WordPiece 的区别是什么？"
    ]
  }
}
```

## 使用方法

### 工作流：理解 AI 生成的代码库

```
步骤 1: 构建知识图谱
─────────────────────────────────────────
$ ua build --project ./ai-generated-code
> 扫描 234 个文件，提取 67 个概念，挖掘 78 个问题
> 知识图谱已生成：.ua/graph.html

步骤 2: 探索入口点
─────────────────────────────────────────
$ ua explore --start entry_point
> 推荐从以下文件开始：
>   1. main.py (入口)
>   2. config/framework.yaml (配置)
>   3. framework/__init__.py (核心模块)

步骤 3: 学习核心概念
─────────────────────────────────────────
$ ua navigate --target concept_main_loop
> 涉及文件: main.py, framework/core/pipeline.py
> 涉及概念: 异步任务、事件循环、状态机
> 推荐问题: "主循环如何处理异常？"

步骤 4: 围绕节点提问 AI
─────────────────────────────────────────
$ ua ask "pipeline.py 中的 router 是如何工作的？"
> [AI 基于图谱上下文给出可验证的答案]
> 答案来源: framework/core/router.py:45-78
```

### 工作流：onboarding 新成员

```
新员工: 我刚加入团队，请帮我快速理解 lumilearn 项目

LumiLearn UA:
1. 展示项目知识图谱可视化
2. 标注核心概念和推荐阅读顺序
3. 回答"项目是做什么的？"
4. 回答"主要架构是怎样的？"
5. 回答"我应该从哪里开始读代码？"

输出：
- 项目概览文档
- 推荐阅读路径
- 核心概念列表
- 关键问题 FAQ
```

## 兼容 AI 工具

| AI 工具 | 集成方式 | 状态 |
|---------|---------|------|
| **Claude Code** | MCP 协议 | ✅ 已支持 |
| **Cursor** | MCP 协议 | ✅ 已支持 |
| **Codex** | MCP 协议 | ✅ 已支持 |
| **GitHub Copilot** | MCP 协议 | ✅ 已支持 |
| **Gemini CLI** | MCP 协议 | ✅ 已支持 |
| **Windsurf** | MCP 协议 | ✅ 已支持 |
| **Continue.dev** | MCP 协议 | ✅ 已支持 |

## 图谱可视化

支持多种可视化方式：

```python
{
  "visualization_options": {
    "interactive_html": "使用 vis.js 或 D3.js 渲染可交互图谱",
    "static_svg": "高质量静态图（适合文档）",
    "mermaid": "Markdown 友好的文本图",
    "graphviz": "命令行渲染 PNG/PDF"
  }
}
```

## 与 CodeGraph 的区别

| 维度 | CodeGraph | Understand-Anything |
|------|-----------|---------------------|
| 核心 | 函数/调用关系 | 概念/问题/文件 |
| 粒度 | 细（符号级） | 粗（概念级） |
| AI 焦点 | 定位代码位置 | 理解代码意图 |
| 输入 | 纯代码 | 代码 + 文档 + Issues |
| 适用 | 重构、检索 | 学习、onboarding、答疑 |
| 关系类型 | 调用、依赖 | 概念、问答、文档 |

> **推荐组合使用**：CodeGraph 定位具体代码，UA 理解设计意图

## 集成到 AI-Collab

```python
# skills/understand-anything/integration.py

class UnderstandAnythingAgent:
    """UA Agent - 集成到 AI-Collab 协调器"""

    def __init__(self, project_root: str):
        self.graph = self.build_graph(project_root)

    def answer_question(self, question: str) -> str:
        """回答关于项目的问题"""
        return self.graph.ask(question)

    def get_learning_path(self, topic: str) -> list:
        """生成主题学习路径"""
        return self.graph.navigate(topic).step_by_step_guide

    def find_related_code(self, concept: str) -> list:
        """查找与概念相关的代码"""
        return self.graph.find_related_files(concept)

# 注册到 AI-Collab
orchestrator.register_agent(
    "UnderstandAnythingAgent",
    UnderstandAnythingAgent("./lumilearn")
)
```

## 配置说明

```python
# config/understand_anything.json
{
  "understand_anything": {
    "enabled": true,
    "graph_storage": {
      "type": "sqlite",
      "path": "./.ua/graph.db"
    },
    "analysis": {
      "include_docs": true,
      "include_readme": true,
      "include_issues": false,
      "max_file_size_mb": 5
    },
    "concept_extraction": {
      "model": "qwen2.5:7b",
      "max_concepts_per_file": 10,
      "min_concept_relevance": 0.6
    },
    "question_mining": {
      "max_questions_per_file": 5,
      "min_quality_score": 0.7
    },
    "mcp_server": {
      "enabled": true,
      "port": 8766,
      "transport": "stdio"
    }
  }
}
```

## 应用场景示例

### 场景 1: 接手 AI 生成项目

```
用户: 我从其他 AI 那里继承了一个 5000 行的 Python 项目，看不懂结构

LumiLearn UA:
1. build_graph - 生成知识图谱
2. 展示核心入口和模块分层
3. 提取 47 个核心概念
4. 总结"项目做了什么、为什么这样做"

输出可视化图谱 + 结构化文档
```

### 场景 2: 写代码前先查设计

```
用户: 我想给 lumilearn 添加新的模型架构，应该参考哪些代码？

LumiLearn UA:
1. ask "如何扩展 LumiLearnModel？"
2. 答案来源：
   - framework/model.py: 基类实现
   - framework/config.py: 配置注册
   - docs/learning_journey/MODULE_X: 教程
3. 推荐阅读顺序
4. 相关常见问题
```

### 场景 3: AI 编程工具增强

```
Claude Code 集成 UA 后:

User: 帮我修复 framework/trainer.py 中的 bug
Claude: 让我先看看相关概念...
[调用 ua_get_concept("trainer")]
[调用 ua_get_questions(file="framework/trainer.py")]
[基于图谱上下文生成修复方案]
[提供 3 个相关文件作为佐证]
```

## 相关资源

- [Understand-Anything GitHub](https://github.com/iamgreedy/understand-anything)
- [CodeGraph GitHub](https://github.com/iamgreedy/codegraph) (同作者的姊妹项目)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [知识图谱入门](https://en.wikipedia.org/wiki/Knowledge_graph)
- [静态分析工具概览](https://en.wikipedia.org/wiki/Static_program_analysis)

## 更新日志

### v1.0.0 (2026-06-01)
- 初始版本
- 支持 3 种节点类型（文件/概念/问题）
- 支持 5 个核心 MCP 工具
- 集成 AI-Collab 协调器
- 支持 7 种 AI 编程工具
- 与 CodeGraph 互补使用
