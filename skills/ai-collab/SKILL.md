---
name: ai-collab
version: "1.0.0"
description: AI-Collab 多智能体协作技能 - 让多个AI Agent协调工作，自动化复杂任务流程
tags:
  - multi-agent
  - coordination
  - automation
  - workflow
  - ai-orchestration
author: LumiLearn Team
license: Apache-2.0
---

# AI-Collab - 多智能体协作技能

## 概述

本技能将 ai-collab 多智能体协作架构集成到 LumiLearn，实现多个AI Agent的协调工作。通过任务分解、角色分配、并行执行和结果整合，自动化完成复杂的教育内容生成任务。

## 核心概念

### 多智能体协作架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI-Collab 协调器                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ 任务分解器   │  │ 角色分配器   │  │ 结果整合器   │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         └─────────────────┼─────────────────┘                  │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Agent 工作池                          │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │Agent-内容│ │Agent-动画│ │Agent-问答│ │Agent-评估│       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Agent 类型定义

| Agent 类型 | 职责 | 输入 | 输出 |
|-----------|------|------|------|
| **ContentAgent** | 生成教学内容 | 知识点描述 | 讲解文本、公式 |
| **AnimationAgent** | 创建动画脚本 | 教学内容 | Manim/HyperFrames 代码 |
| **QuestionAgent** | 生成问答对 | 知识点 | 问题、答案、解析 |
| **EvaluationAgent** | 评估内容质量 | 生成内容 | 质量评分、改进建议 |
| **TranslationAgent** | 多语言翻译 | 原文 | 译文 |
| **OptimizationAgent** | 优化内容结构 | 原始内容 | 优化后内容 |

## 适用场景

- **复杂内容生成** - 需要多步骤、多角色的内容创作
- **并行任务处理** - 同时生成文章、动画、问答
- **质量保障流程** - 自动生成+自动评估+自动优化
- **多语言内容** - 生成中文内容并自动翻译
- **批量内容生产** - 自动化批量生成教学资源

## 核心功能

### 1. 任务分解与规划

自动将复杂任务分解为可并行执行的子任务：

```python
{
  "task_id": "task_001",
  "task_type": "完整知识点生成",
  "input": {
    "subject": "数学",
    "topic": "勾股定理",
    "grade": "初二"
  },
  "subtasks": [
    {
      "id": "subtask_1",
      "agent_type": "ContentAgent",
      "action": "生成知识点讲解",
      "dependencies": [],
      "estimated_time": 30
    },
    {
      "id": "subtask_2",
      "agent_type": "AnimationAgent",
      "action": "创建证明动画",
      "dependencies": ["subtask_1"],
      "estimated_time": 60
    },
    {
      "id": "subtask_3",
      "agent_type": "QuestionAgent",
      "action": "生成练习题",
      "dependencies": ["subtask_1"],
      "estimated_time": 20
    },
    {
      "id": "subtask_4",
      "agent_type": "EvaluationAgent",
      "action": "质量评估",
      "dependencies": ["subtask_1", "subtask_2", "subtask_3"],
      "estimated_time": 15
    }
  ],
  "parallel_groups": [
    ["subtask_1"],
    ["subtask_2", "subtask_3"],
    ["subtask_4"]
  ]
}
```

### 2. Agent 协调执行

```python
# 协调器核心逻辑
class AICollabOrchestrator:
    """
    AI-Collab 协调器
    管理多个AI Agent的协作执行
    """
    
    def __init__(self):
        self.agents = {}
        self.task_queue = PriorityQueue()
        self.results = {}
    
    def register_agent(self, agent_type, agent_instance):
        """注册Agent"""
        self.agents[agent_type] = agent_instance
    
    async def execute_task(self, task_plan):
        """执行任务计划"""
        # 按并行组执行
        for group in task_plan["parallel_groups"]:
            # 并行执行组内任务
            tasks = [self.execute_subtask(tid) for tid in group]
            await asyncio.gather(*tasks)
        
        # 整合结果
        return self.integrate_results(task_plan)
    
    async def execute_subtask(self, subtask_id):
        """执行子任务"""
        subtask = self.get_subtask(subtask_id)
        agent = self.agents[subtask["agent_type"]]
        
        # 获取依赖结果
        dependencies = self.get_dependency_results(subtask)
        
        # 执行
        result = await agent.execute(subtask, dependencies)
        self.results[subtask_id] = result
        
        return result
```

### 3. 智能任务分配

基于Agent能力和负载动态分配任务：

```python
{
  "allocation_strategy": "智能分配",
  "rules": [
    {
      "condition": "任务类型 == '数学公式'",
      "priority_agent": "ContentAgent",
      "capabilities_required": ["latex", "math_reasoning"]
    },
    {
      "condition": "任务类型 == '动画生成'",
      "priority_agent": "AnimationAgent",
      "capabilities_required": ["manim", "hyperframes"]
    },
    {
      "condition": "需要质量检查",
      "priority_agent": "EvaluationAgent",
      "capabilities_required": ["content_evaluation"]
    }
  ],
  "load_balancing": {
    "enabled": true,
    "max_concurrent_per_agent": 3,
    "queue_strategy": "priority"
  }
}
```

### 4. 结果整合与优化

```python
{
  "integration_strategy": "智能整合",
  "steps": [
    {
      "step": "内容合并",
      "action": "将各Agent输出按结构合并",
      "output_format": "统一JSON"
    },
    {
      "step": "一致性检查",
      "action": "检查各部分内容的一致性",
      "conflict_resolution": "自动修正或标记"
    },
    {
      "step": "质量评估",
      "action": "整体质量评分",
      "threshold": 0.85
    },
    {
      "step": "优化建议",
      "action": "生成改进建议",
      "auto_optimize": true
    }
  ],
  "final_output": {
    "content": "整合后的完整内容",
    "metadata": {
      "agents_involved": ["Agent列表"],
      "execution_time": "总耗时",
      "quality_score": "质量评分",
      "iterations": "优化轮数"
    }
  }
}
```

## 工作流模板

### 模板 1: 完整知识点生成工作流

```yaml
workflow:
  name: "完整知识点生成"
  description: "从概念到练习的完整内容生成"
  
  steps:
    - step: 1
      name: "内容生成"
      agent: ContentAgent
      action: "生成知识点讲解"
      output: ["讲解文本", "核心公式", "示例"]
    
    - step: 2
      name: "并行生成"
      parallel: true
      sub_steps:
        - agent: AnimationAgent
          action: "生成动画脚本"
          input: "步骤1的输出"
        - agent: QuestionAgent
          action: "生成练习题"
          input: "步骤1的输出"
        - agent: QuestionAgent
          action: "生成记忆卡片"
          input: "步骤1的输出"
    
    - step: 3
      name: "质量评估"
      agent: EvaluationAgent
      action: "评估所有生成内容"
      input: "所有前置输出"
      
    - step: 4
      name: "优化迭代"
      agent: OptimizationAgent
      action: "根据评估结果优化"
      condition: "质量评分 < 0.85"
      loop: "最多3次"
    
    - step: 5
      name: "结果整合"
      agent: IntegrationAgent
      action: "整合所有内容为标准格式"
      output: "最终教学资源包"
```

### 模板 2: 批量内容生产工作流

```yaml
workflow:
  name: "批量内容生产"
  description: "批量生成多个知识点的教学资源"
  
  batch_config:
    input_source: "知识点列表CSV"
    parallel_batches: 5
    max_concurrent: 10
  
  steps:
    - step: 1
      name: "批量分发"
      action: "将知识点分发给多个工作流实例"
      
    - step: 2
      name: "并行执行"
      action: "每个知识点执行'完整知识点生成'工作流"
      
    - step: 3
      name: "结果收集"
      action: "收集所有结果"
      
    - step: 4
      name: "去重与整合"
      action: "去除重复内容，整合为统一格式"
      
    - step: 5
      name: "批量导出"
      action: "导出为CSV/JSON/Anki等格式"
```

### 模板 3: 多语言内容生成工作流

```yaml
workflow:
  name: "多语言内容生成"
  description: "生成中文内容并自动翻译为多语言"
  
  steps:
    - step: 1
      name: "中文内容生成"
      agent: ContentAgent
      action: "生成中文教学内容"
      
    - step: 2
      name: "并行翻译"
      parallel: true
      sub_steps:
        - agent: TranslationAgent
          action: "翻译为英文"
        - agent: TranslationAgent
          action: "翻译为日文"
        - agent: TranslationAgent
          action: "翻译为韩文"
      
    - step: 3
      name: "翻译质量检查"
      agent: EvaluationAgent
      action: "检查翻译质量"
      
    - step: 4
      name: "多语言整合"
      action: "整合为多语言资源包"
```

## 集成到 LumiLearn

### API 端点

```
POST /api/skills/ai-collab/orchestrate
{
  "workflow": "完整知识点生成",
  "input": {
    "subject": "数学",
    "topic": "二次函数",
    "grade": "高一",
    "requirements": ["动画", "练习题", "记忆卡片"]
  },
  "options": {
    "parallel": true,
    "quality_threshold": 0.85,
    "max_iterations": 3
  }
}
```

### 响应格式

```json
{
  "task_id": "task_001",
  "status": "completed",
  "execution_time": 125.5,
  "agents_involved": [
    {"type": "ContentAgent", "time": 30.2},
    {"type": "AnimationAgent", "time": 60.5},
    {"type": "QuestionAgent", "time": 20.1},
    {"type": "EvaluationAgent", "time": 14.7}
  ],
  "results": {
    "content": "知识点讲解文本",
    "animation": "Manim代码",
    "questions": ["问题1", "问题2", "问题3"],
    "flashcards": ["卡片1", "卡片2"]
  },
  "quality": {
    "overall_score": 0.92,
    "content_score": 0.95,
    "animation_score": 0.88,
    "questions_score": 0.93
  },
  "iterations": 1,
  "output_files": {
    "json": "./output/task_001.json",
    "csv": "./output/task_001.csv",
    "anki": "./output/task_001.apkg"
  }
}
```

### Python SDK 使用

```python
from lumilearn.skills import AICollab

# 初始化协调器
orchestrator = AICollab.Orchestrator()

# 注册Agent
orchestrator.register_agent("ContentAgent", ContentAgent())
orchestrator.register_agent("AnimationAgent", AnimationAgent())
orchestrator.register_agent("QuestionAgent", QuestionAgent())

# 执行工作流
result = await orchestrator.execute({
    "workflow": "完整知识点生成",
    "input": {
        "subject": "物理",
        "topic": "牛顿第一定律",
        "grade": "高一"
    }
})

# 获取结果
print(result["content"])
print(result["animation"])
print(result["quality"]["overall_score"])
```

## 配置说明

### 基础配置

```python
# config/ai_collab.json
{
  "orchestrator": {
    "max_concurrent_tasks": 10,
    "task_timeout": 300,
    "retry_attempts": 3,
    "quality_threshold": 0.85
  },
  "agents": {
    "ContentAgent": {
      "model": "qwen2.5:7b",
      "temperature": 0.7,
      "max_tokens": 2000
    },
    "AnimationAgent": {
      "model": "deepseek-r1:1.5b",
      "temperature": 0.5,
      "max_tokens": 3000
    },
    "QuestionAgent": {
      "model": "qwen2.5:7b",
      "temperature": 0.8,
      "max_tokens": 1500
    },
    "EvaluationAgent": {
      "model": "Doubao-Seed-2.0",
      "temperature": 0.3,
      "max_tokens": 1000
    }
  },
  "workflows": {
    "default": "完整知识点生成",
    "templates_path": "./workflows"
  }
}
```

### Agent 能力配置

```python
# 定义Agent能力
AGENT_CAPABILITIES = {
    "ContentAgent": {
        "skills": ["content_generation", "latex", "markdown"],
        "subjects": ["math", "physics", "chemistry", "english", "chinese"],
        "max_length": 5000,
        "languages": ["zh", "en"]
    },
    "AnimationAgent": {
        "skills": ["manim", "hyperframes", "animation_design"],
        "animation_types": ["formula", "concept", "process", "comparison"],
        "max_duration": 120
    },
    "QuestionAgent": {
        "skills": ["question_generation", "answer_validation"],
        "question_types": ["choice", "fill_blank", "essay", "calculation"],
        "difficulty_range": [0.3, 0.9]
    },
    "EvaluationAgent": {
        "skills": ["content_evaluation", "quality_scoring", "error_detection"],
        "metrics": ["accuracy", "completeness", "clarity", "difficulty"]
    }
}
```

## 使用示例

### 示例 1: 生成完整数学知识点

```
用户: 为"三角函数诱导公式"生成完整的教学资源

AI-Collab 协调器:
1. 任务分解:
   - 子任务1: ContentAgent 生成公式讲解
   - 子任务2: AnimationAgent 生成推导动画
   - 子任务3: QuestionAgent 生成练习题
   - 子任务4: EvaluationAgent 质量评估

2. 并行执行:
   - 阶段1: 内容生成 (30s)
   - 阶段2: 动画+题目并行 (60s)
   - 阶段3: 质量评估 (15s)

3. 结果整合:
   - 讲解文本: 诱导公式的完整推导
   - 动画代码: Manim动画脚本
   - 练习题: 5道选择题+2道计算题
   - 质量评分: 0.94

4. 输出:
   [提供完整的教学资源包]
```

### 示例 2: 批量生成英语阅读材料

```
用户: 批量生成10篇英语阅读理解，主题：科技

AI-Collab 协调器:
1. 批量分发: 创建10个并行工作流
2. 每个工作流:
   - ContentAgent: 生成文章
   - QuestionAgent: 生成5道题目
   - EvaluationAgent: 评估难度和质量
3. 结果整合:
   - 去重检查
   - 难度分级
   - 统一格式
4. 批量导出:
   - CSV格式
   - JSON格式
   - Anki卡片包
```

### 示例 3: 智能质量优化

```
用户: 生成"化学方程式配平"讲解，要求质量>0.9

AI-Collab 协调器:
第1轮生成:
- 内容生成 → 动画生成 → 评估
- 质量评分: 0.82 (低于阈值)

第2轮优化:
- OptimizationAgent 分析不足
- 内容补充 → 动画优化 → 重新评估
- 质量评分: 0.91 (通过)

最终输出:
- 高质量教学内容
- 优化过程记录
- 质量报告
```

## 性能优化

### 并行执行优化

```python
{
  "parallel_optimization": {
    "strategy": "依赖分析",
    "max_parallel": 10,
    "batch_size": 5,
    "techniques": [
      "任务依赖图分析",
      "关键路径优化",
      "动态负载均衡",
      "结果缓存复用"
    ]
  }
}
```

### 资源管理

```python
{
  "resource_management": {
    "agent_pool": {
      "min_instances": 2,
      "max_instances": 10,
      "scale_strategy": "根据队列长度自动扩容"
    },
    "memory_management": {
      "max_results_cache": 100,
      "cleanup_interval": 3600
    },
    "rate_limiting": {
      "requests_per_minute": 60,
      "burst_allowance": 10
    }
  }
}
```

## 监控与日志

### 执行监控

```python
{
  "monitoring": {
    "metrics": [
      "任务执行时间",
      "Agent利用率",
      "成功率",
      "平均质量分",
      "队列长度"
    ],
    "alerts": {
      "task_failure_rate": "> 5%",
      "avg_execution_time": "> 300s",
      "queue_backlog": "> 50"
    }
  }
}
```

### 执行日志

```python
{
  "logging": {
    "level": "INFO",
    "format": "json",
    "fields": [
      "timestamp",
      "task_id",
      "agent_type",
      "action",
      "duration",
      "status",
      "input_hash",
      "output_hash"
    ],
    "retention": "30天"
  }
}
```

## 与现有系统集成

### 与 LumiLearn 数据层集成

```python
# 自动保存到主数据库
async def save_to_database(result):
    record = {
        "id": generate_id(),
        "content": result["content"],
        "animation": result["animation"],
        "questions": result["questions"],
        "quality_score": result["quality"]["overall_score"],
        "agents": result["agents_involved"],
        "create_time": datetime.now()
    }
    await lumilearn_db.insert(record)
```

### 与现有技能集成

```python
# 调用 HyperFrames 技能生成动画
animation_agent = HyperFramesAgent()
orchestrator.register_agent("AnimationAgent", animation_agent)

# 调用 RTK 技能生成前端代码
frontend_agent = RTKAgent()
orchestrator.register_agent("FrontendAgent", frontend_agent)
```

## 故障处理

### 重试机制

```python
{
  "retry_policy": {
    "max_attempts": 3,
    "backoff_strategy": "exponential",
    "initial_delay": 1,
    "max_delay": 60,
    "retryable_errors": [
      "TimeoutError",
      "ConnectionError",
      "RateLimitError"
    ]
  }
}
```

### 降级策略

```python
{
  "fallback_strategy": {
    "agent_unavailable": "使用备用Agent",
    "quality_below_threshold": "人工审核",
    "timeout": "返回部分结果",
    "complete_failure": "记录错误并通知"
  }
}
```

## 相关资源

- [Multi-Agent Systems](https://www.microsoft.com/en-us/research/research-area/artificial-intelligence/)
- [LangGraph Multi-Agent](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
- [AutoGen Framework](https://microsoft.github.io/autogen/)
- [CrewAI](https://docs.crewai.com/)

## 更新日志

### v1.0.0 (2026-05-28)
- 初始版本
- 支持4种Agent类型
- 3种预设工作流模板
- 并行执行优化
- 质量评估与自动优化
- 集成到 LumiLearn API
