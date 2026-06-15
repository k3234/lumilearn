# Build-Your-Own-X - 手搓开源教程技能

## 简介
提供用 C/C++/Python/JavaScript 等从零构建游戏、操作系统、浏览器、3D 渲染器等热门软件的系统化教程。

## 来源
[Build-Your-Own-X GitHub](https://github.com/codecrafters-io/build-your-own-x)

## 文件
- `SKILL.md` - 技能详细说明
- `config.json` - 配置文件
- `project_manager.py` - Python 实现
  - `BuildYourOwnXManager` - 项目管理器
  - 10+ 教程项目目录（涵盖 6 大类：解释器/操作系统/网络/图形/工具/前端）
  - 自动生成项目脚手架
  - 智能推荐 + 进度追踪

## 支持的教程项目

| 项目 | 语言 | 难度 | 技能点 |
|------|------|------|--------|
| LISP 解释器 | Python | 入门 | AST, 递归 |
| HTTP 服务器 | C | 中级 | Socket, 并发 |
| 光线追踪器 | C++ | 高级 | 3D数学, 渲染 |
| Unix Shell | C | 中级 | 进程, 系统调用 |
| 字节码 VM | Rust | 高级 | 字节码, 栈式VM |
| Pong 游戏 | C++ | 入门 | 游戏循环, 事件 |
| 正则引擎 | C | 高级 | 状态机, NFA/DFA |
| Git 简化版 | Python | 中级 | 内容寻址, DAG |
| 微型 OS | Rust | 高级 | 内核, 中断, 内存 |
| C 编译器 | C | 高级 | 词法/语法分析 |

## 快速使用

```python
from skills.build-your-own-x.project_manager import BuildYourOwnXManager

manager = BuildYourOwnXManager()

# 列出项目
projects = manager.list_projects(language="python", difficulty="beginner")

# 初始化脚手架
result = manager.init_project("lisp-interpreter-py", "./my-projects/lisp")
print(result)  # {'success': True, 'files_created': [...]}

# 推荐项目
recs = manager.recommend({
    "level": "beginner",
    "languages": ["python"]
})

# 标记完成
manager.mark_completed("lisp-interpreter-py", github_url="https://github.com/...")
```
