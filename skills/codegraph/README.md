# CodeGraph - 代码知识图谱预索引技能

## 简介
为 AI 编程智能体预扫描项目并构建结构化图谱（函数定义/调用关系/依赖链），减少 AI 检索次数17倍。

## 来源
[CodeGraph GitHub](https://github.com/iamgreedy/codegraph)（30K Star）

## 文件
- `SKILL.md` - 技能详细说明
- `config.json` - 配置文件
- `graph_builder.py` - Python 实现
  - `CodeGraphBuilder` - 知识图谱构建器
  - 扫描 Python 文件，提取函数定义、调用关系、模块依赖
  - 提供 `search_function`, `get_callers`, `get_callees`, `get_dependencies`, `find_unused` 等查询接口

## 快速使用

```python
from skills.codegraph.graph_builder import CodeGraphBuilder

builder = CodeGraphBuilder(project_root="./")
stats = builder.scan()
print(stats)  # {'files_scanned': 234, 'functions': 567, ...}

# 搜索函数
results = builder.search_function("train_model")
for f in results:
    print(f"{f.name} @ {f.file}:{f.line_start}")

# 查找未使用函数
unused = builder.find_unused()
```

## 与 AI 助手集成
通过 MCP 协议支持：
- Claude Code, Cursor, OpenCode
- Cline, Windsurf, Continue.dev
