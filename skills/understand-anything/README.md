# Understand-Anything - 代码库理解技能

## 简介
把 AI 生成的"屎山"代码库和文档变成知识图谱（文件/概念/问题节点关系），辅助 Claude Code/Cursor/Copilot 等 AI 编程工具。

## 来源
[Understand-Anything GitHub](https://github.com/)（20.1K Star，CodeGraph 姊妹项目）

## 文件
- `SKILL.md` - 技能详细说明
- `config.json` - 配置文件
- `graph_builder.py` - Python 实现
  - `UnderstandAnything` - 知识图谱构建器
  - 3 种节点类型：FileNode（文件）、ConceptNode（概念）、QuestionNode（问题）
  - 自动从代码库提取概念、挖掘问题
  - 提供 `ask`, `navigate`, `get_concept` 等查询接口

## 与 CodeGraph 的对比

| 维度 | CodeGraph | Understand-Anything |
|------|-----------|---------------------|
| 核心 | 函数/调用关系 | 概念/问题/文件 |
| 粒度 | 细（符号级） | 粗（概念级） |
| AI 焦点 | 定位代码位置 | 理解代码意图 |
| 适用 | 重构、检索 | 学习、onboarding、答疑 |

> **推荐组合使用**：CodeGraph 定位具体代码，UA 理解设计意图

## 快速使用

```python
from skills.understand-anything.graph_builder import UnderstandAnything

ua = UnderstandAnything(project_root="./")
stats = ua.build()
print(stats)  # {'file_nodes': 89, 'concept_nodes': 67, 'question_nodes': 78, ...}

# 回答问题
result = ua.ask("BPE tokenizer 是如何训练的？")
print(result['sources'])

# 导航到概念
info = ua.navigate("BPE")
print(info)

# 获取概念详情
concept = ua.get_concept("tokenizer")
print(concept.definition)
```

## 兼容 AI 工具
通过 MCP 协议支持：Claude Code, Cursor, Codex, GitHub Copilot, Gemini CLI, Windsurf, Continue.dev
