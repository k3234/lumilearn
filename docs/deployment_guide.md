# LumiLearn 学生学习成果输出检测系统 - 部署指南

> **版本**: 1.0.0  
> **最后更新**: 2026-08-07  
> **测试状态**: ✅ 全部通过 (60 tests)

---

## 目录

1. [系统概述](#1-系统概述)
2. [环境要求](#2-环境要求)
3. [安装步骤](#3-安装步骤)
4. [数据库初始化](#4-数据库初始化)
5. [运行测试](#5-运行测试)
6. [CLI 命令使用](#6-cli-命令使用)
7. [API 接口](#7-api-接口)
8. [故障排除](#8-故障排除)
9. [附录](#9-附录)

---

## 1. 系统概述

### 1.1 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                       用户交互层                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  CLI 终端    │  │  课堂模式前端 │  │  对话终端前端        │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼─────────────────────┼──────────────┘
          │                 │                     │
┌─────────┼─────────────────┼─────────────────────┼──────────────┐
│         ▼                 ▼                     ▼              │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              核心引擎层                                   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │ Workflow     │  │ Output       │  │ Feynman      │  │  │
│  │  │ Engine       │  │ Detector     │  │ Engine       │  │  │
│  │  │ (五步学习)   │  │ (输出检测)   │  │ (教学讲解)   │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │  │
│  └─────────┼─────────────────┼─────────────────┼──────────┘  │
            │                 │                 │
┌───────────┼─────────────────┼─────────────────┼──────────────┐
│           ▼                 ▼                 ▼              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    数据持久层                             ││
│  │              SQLite 数据库 (SQLite)                      ││
│  │  - users (用户表)                                       ││
│  │  - learning_workflows (学习工作流表)                     ││
│  │  - output_detection (输出检测表)                        ││
│  │  - 其他原有表...                                        ││
│  └─────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### 1.2 核心流程

```
五步学习 → 输出检测 → 引导加强 → 档案记录
    │          │          │          │
    ▼          ▼          ▼          ▼
Feynman    Output     Guided    Archive
 Engine     Detector  Reinforce  Database
```

### 1.3 五步学习法

| 步骤 | 名称 | 说明 |
|:---:|------|------|
| 1 | 现象引入 | 从生活实例引入概念 |
| 2 | 认知冲突 | 提出矛盾激发思考 |
| 3 | 思维模型 | 建立概念框架 |
| 4 | 自主推导 | 学生独立推导验证 |
| 5 | 费曼测试 | 30秒总结检验理解 |

---

## 2. 环境要求

### 2.1 系统要求

| 项目 | 最低要求 | 推荐配置 |
|------|----------|----------|
| 操作系统 | Windows 10+ / Linux / macOS | - |
| Python 版本 | 3.10+ | 3.14 |
| 内存 | 4 GB | 8 GB+ |
| 磁盘空间 | 500 MB | 2 GB+ |
| 网络 | 可选 (用于 Ollama) | 本地 Ollama 服务 |

### 2.2 可选依赖

| 组件 | 用途 | 安装方式 |
|------|------|----------|
| Ollama | AI 模型推理 | `ollama pull qwen2.5:7b` |
| GPU (可选) | 加速训练 | NVIDIA CUDA 12+ |

### 2.3 验证 Python 环境

```bash
python --version
# 应输出: Python 3.10+

python -c "import sys; print(sys.version)"
```

---

## 3. 安装步骤

### 3.1 克隆项目

```bash
git clone https://github.com/your-username/lumilearn.git
cd lumilearn
```

### 3.2 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3.3 安装依赖

```bash
pip install -r requirements.txt
```

### 3.4 验证安装

```bash
python -c "from framework.database import db; print('✅ 数据库模块导入成功')"
python -c "from framework.workflow_engine import LearningWorkflowEngine; print('✅ 工作流引擎导入成功')"
python -c "from framework.output_detector import OutputDetector; print('✅ 输出检测器导入成功')"
```

---

## 4. 数据库初始化

### 4.1 自动初始化

系统会在首次运行时自动创建数据库文件和表结构。

```bash
# 初始化数据库
python -c "from framework.database import db; db.init(); print('✅ 数据库初始化完成')"
```

### 4.2 验证表结构

```bash
python -c "
from framework.database import db
db.init()
print('表列表:', db.get_table_list())
"
```

应包含以下表：
- `users` - 用户表
- `learning_workflows` - 学习工作流表
- `output_detection` - 输出检测表
- 其他原有表...

### 4.3 创建测试用户

```bash
python scripts/db_admin.py user create --name "测试学生" --role student
```

---

## 5. 运行测试

### 5.1 运行所有测试

```bash
# 使用 unittest 运行
python -m unittest tests.test_workflow_engine tests.test_output_detector tests.test_learning_pipeline -v

# 或使用 pytest
python -m pytest tests/test_workflow_engine.py tests/test_output_detector.py tests/test_learning_pipeline.py -v
```

### 5.2 测试覆盖范围

| 测试文件 | 测试数 | 覆盖内容 |
|----------|--------|----------|
| `test_workflow_engine.py` | 16 | 工作流创建、步骤提交、状态跟踪、数据库持久化 |
| `test_output_detector.py` | 27 | 输出检测、评分维度、引导强化、数据库保存 |
| `test_learning_pipeline.py` | 17 | 端到端流程、多用户隔离、错误处理、数据一致性 |
| **合计** | **60** | 全部通过 ✅ |

### 5.3 测试输出示例

```
test_start_workflow (tests.test_workflow_engine.TestWorkflowEngineStart) ... ok
test_submit_step_output (tests.test_workflow_engine.TestWorkflowEngineSubmit) ... ok
test_complete_workflow (tests.test_workflow_engine.TestWorkflowEngineComplete) ... ok
test_detect_output (tests.test_output_detector.TestOutputDetectorRunDetection) ... ok
test_guided_reinforcement (tests.test_output_detector.TestOutputDetectorGuidedReinforcement) ... ok
...
Ran 60 tests in 220.029s
OK
```

---

## 6. CLI 命令使用

### 6.1 工作流管理

```bash
# 查看帮助
python scripts/db_admin.py workflow --help

# 开始学习工作流
python scripts/db_admin.py workflow start --topic "勾股定理" --level junior --user-id 2

# 提交学习输出
python scripts/db_admin.py workflow submit --workflow-id 1 --step 1 --output "直角三角形三边的关系" --user-id 2

# 完成工作流并检测
python scripts/db_admin.py workflow complete --id 1 --user-id 2

# 查看工作流状态
python scripts/db_admin.py workflow status --id 1 --user-id 2

# 列出学习工作流
python scripts/db_admin.py workflow list --user-id 2
```

### 6.2 完整工作流示例

```bash
# 1. 开始学习工作流
python scripts/db_admin.py workflow start --user-id 2 --workflow-id "wf_001" --name "勾股定理学习"

# 输出:
# [OK] Workflow 已创建 #1: workflow_id=wf_001 勾股定理学习

# 2. 提交各步骤学习输出（共5步）
python scripts/db_admin.py workflow submit --id 1
python scripts/db_admin.py workflow submit --id 1
python scripts/db_admin.py workflow submit --id 1
python scripts/db_admin.py workflow submit --id 1
python scripts/db_admin.py workflow submit --id 1

# 输出每步:
# [OK] Workflow #1 步骤推进至 1: True
# [OK] Workflow #1 步骤推进至 2: True
# ...

# 3. 完成并评分
python scripts/db_admin.py workflow complete --id 1 --score 85.0

# 输出:
# [OK] Workflow #1 已标记完成: score=85.0

# 4. 查看工作流状态
python scripts/db_admin.py workflow status --id 1

# 输出:
# Workflow #1:
#   workflow_id: wf_001
#   名称: 勾股定理学习
#   用户ID: 2
#   状态: completed
#   步骤: 5
#   得分: 85.0
#   开始时间: 2026-08-07 10:30:00
#   完成时间: 2026-08-07 10:45:00

# 5. 列出所有工作流
python scripts/db_admin.py workflow list --user-id 2
```

---

## 7. API 接口

### 7.1 Python API 使用

```python
from framework.workflow_engine import LearningWorkflowEngine, run_learning_workflow
from framework.output_detector import OutputDetector, detect_output, run_guided_reinforcement

# 方式一：使用便捷函数（一键完成）
result = run_learning_workflow(
    user_id=2,
    topic="勾股定理",
    level="junior",
)
print(f"检测得分: {result['result']['detection']['detection_score']}")

# 方式二：分步控制
engine = LearningWorkflowEngine(user_id=2)

# 开始学习
start = engine.start_workflow(topic="牛顿第二定律", level="senior")
print(f"工作流ID: {start['workflow_id']}")

# 提交步骤输出
for i in range(1, 6):
    engine.submit_step_output(step_order=i, user_output=f"这是第{i}步的理解")

# 完成并检测
final = engine.complete_workflow()
print(f"最终得分: {final['total_score']}")
```

### 7.2 REST API（可选）

启动 API 服务器：

```bash
python framework/api/server.py --multi-port
```

访问：http://localhost:18080

---

## 8. 故障排除

### 8.1 常见问题

#### 问题 1: FOREIGN KEY constraint failed

**原因**: 使用的 user_id 在数据库的 `users` 表中不存在

**解决**:
```bash
# 先查看现有用户
python scripts/db_admin.py user list

# 使用已存在的 user_id，或创建新用户
python scripts/db_admin.py user create --name "新用户" --role student
```

#### 问题 2: Ollama 连接失败

**症状**: `Ollama调用失败(qwen2.5:7b): HTTPConnectionPool...`

**原因**: Ollama 服务未启动或未运行在 localhost:11434

**解决**:
```bash
# 启动 Ollama
ollama serve

# 拉取模型（首次）
ollama pull qwen2.5:7b

# 验证
ollama list
```

**注意**: 单元测试使用 mock 绕过 Ollama 调用，即使没有 Ollama 也能运行测试。

#### 问题 3: 模块导入失败

**症状**: `ModuleNotFoundError: No module named 'framework'`

**解决**:
```bash
# 确保在项目的根目录下运行
cd e:\学习LLM\lumilearn

# 检查 PYTHONPATH
python -c "import sys; print('\n'.join(sys.path))"
```

### 8.2 错误代码对照表

| 错误信息 | 原因 | 解决方法 |
|----------|------|----------|
| `FOREIGN KEY constraint failed` | user_id 不存在 | 使用 `user list` 查看有效 ID |
| `Ollama调用失败` | Ollama 未运行 | 执行 `ollama serve` |
| `sqlite3.OperationalError: no such table` | 数据库未初始化 | 执行 `db.init()` |
| `KeyError: 'step_completed'` | 字段名不匹配 | 已修复，请确保使用最新代码 |

---

## 9. 附录

### 9.1 文件结构

```
lumilearn/
├── framework/
│   ├── database.py          # 数据库管理（新增 2 张表）
│   ├── workflow_engine.py   # 五步学习工作流引擎（新建）
│   ├── output_detector.py   # 输出检测引擎（新建）
│   └── engines/
│       └── feynman_engine.py # 费曼五步学习法引擎（已有）
├── scripts/
│   └── db_admin.py          # CLI 工具（已扩展 workflow 命令）
├── tests/
│   ├── test_workflow_engine.py    # 工作流引擎测试 (16 cases)
│   ├── test_output_detector.py    # 输出检测测试 (27 cases)
│   └── test_learning_pipeline.py  # 端到端测试 (17 cases)
└── docs/
    └── deployment_guide.md      # 本文档
```

### 9.2 数据库表结构

#### learning_workflows

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| user_id | INTEGER FK | 用户 ID |
| topic | TEXT | 学习主题 |
| level | TEXT | 难度级别 |
| current_step | INTEGER | 当前步骤 (0-5) |
| total_steps | INTEGER | 总步骤数 (固定为5) |
| status | TEXT | 状态 (active/completed) |
| started_at | REAL | 开始时间戳 |
| completed_at | REAL | 完成时间戳 |
| created_at | TEXT | 创建时间 |

#### output_detection

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| user_id | INTEGER FK | 用户 ID |
| workflow_id | INTEGER FK | 工作流 ID |
| detection_type | TEXT | 检测类型 |
| topic | TEXT | 学习主题 |
| prompt | TEXT | 检测提示词 |
| user_output | TEXT | 学生输出 |
| score | REAL | 检测得分 (0-100) |
| feedback | TEXT | 反馈信息 |
| guiding_records | TEXT | 引导记录 (JSON) |
| reinforced | INTEGER | 是否已完成加强 |
| created_at | TEXT | 创建时间 |

### 9.3 评分维度

输出检测使用 5 个维度进行评分：

| 维度 | 权重 | 说明 |
|------|------|------|
| 简洁度 | 20% | 表达是否简洁明了 |
| 准确度 | 20% | 概念理解是否准确 |
| 比喻 | 20% | 是否有生活化比喻 |
| 完整度 | 20% | 是否涵盖核心要点 |
| 术语规避 | 20% | 是否避免过多专业术语 |

### 9.4 等级划分

| 总分范围 | 等级 | 说明 |
|----------|------|------|
| 90-100 | 优秀 | 完全掌握，可进入下一阶段 |
| 70-89 | 良好 | 基本掌握，建议加强薄弱点 |
| 50-69 | 及格 | 理解一般，需要系统复习 |
| 0-49 | 需加强 | 理解度低，建议重新学习 |

### 9.5 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2026-08-07 | 初始版本，包含五步学习工作流、输出检测、引导强化 |

---

**技术支持**: GitHub Issues  
**许可证**: MIT
