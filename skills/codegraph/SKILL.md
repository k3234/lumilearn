---
name: codegraph
version: "1.0.0"
description: CodeGraph 代码知识图谱预索引技能 - 为 AI 编程智能体预扫描项目并构建结构化图谱（函数定义/调用关系/依赖链），减少 AI 检索次数17倍
tags:
  - code-analysis
  - knowledge-graph
  - ai-coding
  - code-search
  - code-intelligence
  - pre-indexing
author: LumiLearn Team
license: Apache-2.0
source: https://github.com/iamgreedy/codegraph
---

# CodeGraph - 代码知识图谱预索引技能

## 概述

本技能将 CodeGraph（GitHub 30K Star）集成到 LumiLearn，**为 AI 编程智能体预扫描整个项目**，将函数定义、变量符号、调用关系和依赖链整理成结构化图谱。让 AI 直接查图谱定位逻辑，无需反复读取文件。

## 核心价值

| 指标 | 传统方式 | 使用 CodeGraph | 提升 |
|------|---------|---------------|------|
| AI 代码检索次数（4000+ 文件项目） | 52 次 | 3 次 | **17×** |
| Token 消耗 | 高 | 低 | 显著减少 |
| 工具调用次数 | 多 | 少 | 显著减少 |
| 上下文窗口占用 | 大 | 小 | 极大优化 |

## 适用场景

- **大型代码库理解** - 快速掌握项目结构、模块依赖
- **AI Agent 辅助编程** - 让 Claude Code / Cursor / OpenCode 直接通过图谱定位
- **代码审查准备** - 快速理解修改涉及的影响范围
- **新人入职培训** - 生成项目知识图谱作为学习资料
- **跨模块重构规划** - 通过依赖图评估重构风险
- **死代码检测** - 通过调用图谱发现未使用代码

## 核心功能

### 1. 项目结构扫描

递归扫描项目目录，识别源代码文件：

```python
{
  "scan_config": {
    "root_path": "./lumilearn",
    "include_patterns": ["**/*.py", "**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx"],
    "exclude_patterns": [
      "**/node_modules/**",
      "**/__pycache__/**",
      "**/outputs/**",
      "**/.git/**",
      "**/dist/**",
      "**/build/**"
    ],
    "max_file_size": "10MB",
    "encoding": "utf-8"
  }
}
```

### 2. 知识图谱构建

提取并构建 4 类核心节点：

```python
{
  "graph_nodes": {
    "function_definitions": [
      {
        "id": "func_001",
        "name": "train_model",
        "file": "framework/trainer.py",
        "line_start": 45,
        "line_end": 120,
        "signature": "def train_model(model, dataset, epochs=10, lr=1e-4)",
        "docstring": "训练 LumiLearn V5 模型...",
        "complexity": "O(n*epochs)"
      }
    ],
    "variable_symbols": [
      {
        "id": "var_001",
        "name": "vocab_size",
        "file": "framework/config.py",
        "line": 12,
        "type": "int",
        "scope": "module",
        "default_value": 8000
      }
    ],
    "call_relationships": [
      {
        "from": "func_001:train_model",
        "to": "func_002:forward_pass",
        "call_type": "direct",
        "file": "framework/trainer.py",
        "line": 67
      }
    ],
    "dependency_chains": [
      {
        "module": "framework.model",
        "imports": ["torch", "framework.tokenizer", "framework.config"],
        "imported_by": ["framework.trainer", "inference_server"]
      }
    ]
  }
}
```

### 3. 图谱查询接口

为 AI Agent 提供高效的图谱查询 API：

```python
class CodeGraph:
    """代码知识图谱"""

    def find_function(self, name: str) -> List[FunctionDef]:
        """按名称查找函数定义"""

    def find_callers(self, function_id: str) -> List[CallRel]:
        """查找调用了某函数的所有位置（反向追溯）"""

    def find_callees(self, function_id: str) -> List[CallRel]:
        """查找某函数调用的所有函数（正向追溯）"""

    def get_dependencies(self, module: str) -> List[str]:
        """获取模块的依赖关系"""

    def trace_impact(self, target: str) -> ImpactAnalysis:
        """修改某函数/变量时的影响分析"""

    def find_unused(self) -> List[str]:
        """查找未被调用的死代码"""
```

### 4. MCP 协议集成

通过 Model Context Protocol 暴露给 AI 助手：

```json
{
  "mcp_server": {
    "name": "codegraph",
    "version": "1.0.0",
    "tools": [
      {
        "name": "search_function",
        "description": "按名称搜索函数定义",
        "inputSchema": {
          "type": "object",
          "properties": {
            "name": {"type": "string", "description": "函数名（支持模糊匹配）"},
            "file_pattern": {"type": "string", "description": "文件路径过滤"}
          }
        }
      },
      {
        "name": "get_callers",
        "description": "获取调用了某函数的所有位置",
        "inputSchema": {
          "type": "object",
          "properties": {
            "function_name": {"type": "string"}
          },
          "required": ["function_name"]
        }
      },
      {
        "name": "get_dependencies",
        "description": "获取模块依赖关系",
        "inputSchema": {
          "type": "object",
          "properties": {
            "module_path": {"type": "string"}
          }
        }
      },
      {
        "name": "trace_impact",
        "description": "分析修改某函数的影响范围",
        "inputSchema": {
          "type": "object",
          "properties": {
            "target": {"type": "string", "description": "函数名或文件路径"}
          }
        }
      }
    ]
  }
}
```

## 集成到 LumiLearn

### API 端点

```
POST /api/skills/codegraph/build
{
  "project_root": "./lumilearn",
  "languages": ["python", "javascript", "typescript"],
  "incremental": true
}

POST /api/skills/codegraph/search
{
  "query": "train_model",
  "type": "function|call|variable|module",
  "limit": 10
}

POST /api/skills/codegraph/impact
{
  "target": "framework.model.LumiLearnModel.forward"
}
```

### 响应格式

```json
{
  "search_results": {
    "matches": [
      {
        "name": "train_model",
        "type": "function",
        "file": "framework/trainer.py",
        "line": 45,
        "snippet": "def train_model(model, dataset, epochs=10, lr=1e-4):\n    \"\"\"训练 LumiLearn V5 模型\"\"\"\n    ...",
        "callers_count": 5,
        "callees_count": 12
      }
    ],
    "total": 1
  },
  "graph_stats": {
    "functions": 234,
    "variables": 567,
    "call_relations": 890,
    "modules": 45
  }
}
```

## 工作流示例

### 示例 1: 理解 lumilearn 项目结构

```
用户: 我是新人，请帮我快速了解 LumiLearn 项目的核心架构

AI 调用 CodeGraph:
1. scan_project(root="./lumilearn")
2. 返回知识图谱统计：
   - 234 个函数
   - 45 个模块
   - 主要入口：framework/__init__.py, inference.py, train.py
3. trace_impact("LumiLearnModel.forward")
   - 被 8 个模块调用
   - 影响范围：训练、推理、API服务

4. 输出结构化报告：
   [项目架构图 + 核心模块说明 + 关键调用链]
```

### 示例 2: 重构影响分析

```
用户: 我想重构 framework.tokenizer 中的 encode 方法，请分析影响范围

AI 调用 CodeGraph:
1. get_callers("LumiLearnTokenizer.encode")
   返回 12 个调用位置：
   - framework/data.py: 数据预处理
   - framework/trainer.py: 训练数据编码
   - inference.py: 推理输入编码
   - ... 其他 9 处
2. trace_impact("encode")
   影响范围：所有依赖 tokenizer 的模块

3. 输出风险评估报告：
   [调用点列表 + 修改建议 + 回归测试要点]
```

### 示例 3: 死代码检测

```
用户: 帮我找出 lumilearn 项目中的未使用函数

AI 调用 CodeGraph:
1. find_unused() 扫描所有函数
2. 返回 23 个未调用函数
3. 按文件分组，标注可能的废弃模块

4. 输出清理建议报告
```

## 兼容 AI 助手

| AI 助手 | 集成方式 | 状态 |
|---------|---------|------|
| **Claude Code** | MCP 协议 | ✅ 已支持 |
| **Cursor** | MCP 协议 | ✅ 已支持 |
| **OpenCode** | MCP 协议 | ✅ 已支持 |
| **Cline** | MCP 协议 | ✅ 已支持 |
| **Windsurf** | MCP 协议 | ✅ 已支持 |
| **Continue.dev** | MCP 协议 | ✅ 已支持 |

## 本地运行 + 数据安全

```python
{
  "deployment": {
    "mode": "local",
    "data_location": "本地文件系统",
    "network_required": false,
    "code_privacy": "100% 本地处理，不上传任何代码到云端"
  }
}
```

## 配置说明

### 基础配置

```python
# config/codegraph.json
{
  "codegraph": {
    "enabled": true,
    "storage": {
      "type": "sqlite",
      "path": "./.codegraph/graph.db"
    },
    "scan": {
      "auto_watch": true,
      "watch_debounce_ms": 1000,
      "max_file_size_mb": 10
    },
    "languages": ["python", "javascript", "typescript", "jsx", "tsx"],
    "ignore_patterns": [
      "**/node_modules/**",
      "**/__pycache__/**",
      "**/outputs/**",
      "**/.git/**",
      "**/dist/**",
      "**/build/**",
      "**/venv/**",
      "**/.venv/**"
    ],
    "mcp_server": {
      "enabled": true,
      "port": 8765,
      "transport": "stdio"
    }
  }
}
```

## 与 LumiLearn 现有技能集成

```python
# skills/codegraph/integration.py

from .graph_builder import CodeGraph
from ..ai_collab.orchestrator import AICollabOrchestrator

class CodeGraphAgent:
    """CodeGraph AI Agent - 集成到 AI-Collab 协调器"""

    def __init__(self, project_root: str = "./"):
        self.graph = CodeGraph(project_root=project_root)
        self.graph.build()

    def answer_code_question(self, question: str) -> str:
        """回答代码相关问题"""
        # 使用图谱定位 + LLM 总结
        results = self.graph.smart_search(question)
        return self._format_answer(results)

    def get_impact_analysis(self, target: str) -> dict:
        """影响分析"""
        return self.graph.trace_impact(target)


# 注册到 AI-Collab
orchestrator.register_agent("CodeGraphAgent", CodeGraphAgent("./lumilearn"))
```

## 使用场景对应表

| 场景 | 调用的 CodeGraph 工具 | 预期收益 |
|------|----------------------|----------|
| "这段代码在做什么？" | search_function + get_callers | 快速定位 |
| "修改 X 会影响什么？" | trace_impact | 风险评估 |
| "X 函数在哪里定义？" | search_function | 1次查询 |
| "这段代码调用了哪些外部库？" | get_dependencies | 依赖梳理 |
| "项目有哪些未使用的代码？" | find_unused | 代码清理 |
| "X 模块被谁依赖？" | get_dependents | 反向分析 |

## 性能基准

| 项目规模 | 文件数 | 扫描耗时 | 图谱大小 | 查询响应 |
|---------|--------|---------|---------|---------|
| 小型 | < 100 | < 5s | < 1MB | < 10ms |
| 中型 | 100-1000 | 5-30s | 1-10MB | < 50ms |
| 大型 | 1000-4000 | 30-120s | 10-50MB | < 100ms |
| 超大型 | 4000+ | 1-5min | 50-200MB | < 200ms |

## 相关资源

- [CodeGraph GitHub](https://github.com/iamgreedy/codegraph)
- [Model Context Protocol 规范](https://modelcontextprotocol.io/)
- [Tree-sitter 解析器](https://tree-sitter.github.io/)
- [Python AST 文档](https://docs.python.org/3/library/ast.html)

## 更新日志

### v1.0.0 (2026-06-01)
- 初始版本
- 支持 Python/JS/TS 代码解析
- 支持 6 个核心查询接口
- 集成 MCP 协议
- 与 AI-Collab 协调器集成
- 本地运行，代码数据安全
