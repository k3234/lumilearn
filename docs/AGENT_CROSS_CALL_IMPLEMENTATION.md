# LumiLearn Agent 跨调用与自积累架构 — 实现报告

> 完成日期：2026-08-17  
> 状态：Phase 1 数据库层 + 核心模块已实现  
> 测试：188 个测试全部通过

---

## 一、已完成内容

### 1. 数据库新增表（3 张）

| 表名 | 行数 | 说明 |
|------|------|------|
| `agent_call_log` | 2 | Agent 调用日志（caller/target/topic/latency/success） |
| `agent_weight_config` | 2 | Agent 权重配置（base_weight/dynamic_weight/统计） |
| `knowledge_accumulation` | 1 | 自积累知识库（topic/type/content/quality_score） |

### 2. 现有表扩展

| 表 | 新增列 | 说明 |
|----|--------|------|
| `agents` | `base_weight`, `call_count`, `success_count`, `fail_count`, `dynamic_weight`, `last_call_at` | 权重与统计 |
| `reasoning_logs` | `agent_id`, `call_chain`, `context_injected` | 跨调用追踪 |

### 3. 新增 Python 模块（3 个）

| 模块 | 功能 |
|------|------|
| [weight_manager.py](file:///e:/学习LLM/lumilearn/agent_core/weight_manager.py) | Agent 动态权重计算与管理 |
| [knowledge_cache.py](file:///e:/学习LLM/lumilearn/agent_core/knowledge_cache.py) | 自积累知识库读写 |
| [cross_caller.py](file:///e:/学习LLM/lumilearn/agent_core/cross_caller.py) | Agent 跨调用管理器 |

---

## 二、核心机制

### 2.1 权重计算公式

```
dynamic_weight = base_weight × success_rate × latency_factor

success_rate = success_count / (success_count + fail_count)
latency_factor = 1.0 / (1.0 + log1p(avg_latency_ms / 1000))
```

- 基础权重：管理员可配（0.0-2.0），默认 1.0
- 动态权重：实时计算，自动衰减（失败/延迟高则权重下降）
- 权重更新时机：每次 Agent 调用完成后

### 2.2 自积累机制

```
Agent 执行 → 结果 → KnowledgeCache.save()
                   → topic + type 生成唯一 ID
                   → 质量评分 0-100
                   → 下次同类请求先查缓存，命中则直接返回
```

**知识类型**：
- `concept` — 概念定义
- `explanation` — 教学内容（5 步费曼）
- `test` — 测试题目与评分
- `solution` — 解题方案
- `pattern` — 学习模式与推荐

### 2.3 跨调用流程

```
1. Agent A 需要 Agent B 的结果
2. CrossCaller.call_agent(target_agent, payload)
   ├─ 查 KnowledgeCache（命中 → 直接返回）
   └─ 未命中 → 调 Agent B.run()
                ├─ 成功 → 写入 KnowledgeCache
                └─ 失败 → 更新权重 -1
3. 记录 agent_call_log
4. 更新 Agent B 的动态权重
```

### 2.4 调用链追踪

```
call_chain: ["router", "feynman_teacher", "output_detector"]
              ↑ 发起      ↑ 教学生成    ↑ 质量校验
```

---

## 三、数据库完整结构

```
┌─────────────────────────────────────────────────────────────┐
│ 数据层                                                        │
├─────────────────────────────────────────────────────────────┤
│ 用户/账号                                                     │
│   users (10) / admins (1) / api_keys (0)                    │
├─────────────────────────────────────────────────────────────┤
│ 知识/学科                                                     │
│   subjects (12) / knowledge_nodes (13) / training_data (1)  │
├─────────────────────────────────────────────────────────────┤
│ Agent 系统（新增）                                             │
│   agents (6)     ← 含 base_weight/dynamic_weight            │
│   agent_call_log (2)   ← 调用历史                           │
│   agent_weight_config (2)  ← 权重配置                       │
│   knowledge_accumulation (1) ← 自积累知识                    │
├─────────────────────────────────────────────────────────────┤
│ 学习流程                                                      │
│   sessions (1) / reasoning_logs (34) / learning_reports (2) │
│   concept_understanding (1)                                 │
├─────────────────────────────────────────────────────────────┤
│ 教师/班级管理                                                  │
│   classes (0) / class_students (0) / task_assignments (2)   │
│   questions (1) / submissions (0)                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、使用示例

### 4.1 查询积累知识

```python
from agent_core import get_knowledge_cache

kc = get_knowledge_cache()
# 查询"勾股定理"相关的积累知识
results = kc.query(topic="勾股定理", subject="数学", min_quality=60)
for item in results:
    print(f"[{item['knowledge_type']}] {item['summary']}")
```

### 4.2 跨调用 Agent

```python
from agent_core import get_cross_caller

cc = get_cross_caller()
# 让 feynman_teacher 调用 output_detector 做质量校验
result = cc.call_agent(
    target_agent_id="output_detector",
    payload={"topic": "勾股定理", "content": "..."},
    caller_agent_id="feynman_teacher",
)
```

### 4.3 查看 Agent 权重

```python
from agent_core import get_weight_manager

wm = get_weight_manager()
weights = wm.get_weights()
for w in weights:
    print(f"{w['agent_id']}: base={w['base_weight']} dynamic={w['dynamic_weight']:.4f}")
# 输出:
# feynman_teacher: base=1.0 dynamic=0.8774
# output_detector: base=1.0 dynamic=0.8458
```

### 4.4 设置 Agent 权重

```python
# 管理员提高某 Agent 权重
wm.set_base_weight("router_task", base_weight=1.5)
# 系统自动重新计算 dynamic_weight
```

---

## 五、后续接入点

| 模块 | 待接入位置 | 说明 |
|------|-----------|------|
| KnowledgeCache | `feynman_engine.py:explain()` | 5步教学完成后自动积累 |
| CrossCaller | `orchestrator.py:run()` | Router 路由时先查跨Agent缓存 |
| WeightManager | `agent_call_log` 写入后 | 自动触发权重更新 |
| admin API | `routes/admin.py` | 新增 Agent 权重配置接口 |

---

## 六、测试验证

```
✅ 数据库迁移：3 张新表创建成功
✅ Agent 列扩展：agents + reasoning_logs 新增列成功
✅ 模块导入：weight_manager / knowledge_cache / cross_caller
✅ 权重计算：dynamic_weight = base × success_rate × latency_factor
✅ 知识积累：save() + query() + usage_count 递增
✅ 跨调用日志：record_agent_call() + 权重级联更新
✅ 全量测试：188 passed (0 failed)
```
