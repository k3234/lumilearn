# LumiLearn Agent 跨调用与自积累架构设计方案

## 一、现状分析

### 当前问题
1. **Agent 孤岛**：6个Agent互不知晓，各自独立运行
2. **数据不共享**：feynman_teacher生成的教学内容不会被detector/adaptive复用
3. **无权重机制**：Router无法基于历史表现选择最优Agent
4. **知识不积累**：推理日志仅记录，不被后续Agent利用

### 数据流现状
```
用户输入 → Router → [feynman_teacher | multi_agent | parallel_models] → 输出
                  ↓
            推理日志（只写不读）
```

### 目标数据流
```
用户输入 → Router → 查KnowledgeCache（已有积累）→ 决定是否调用其他Agent
                  ↓
            Agent调用链 → 写KnowledgeCache → 更新Agent权重
                  ↓
            其他Agent可查询结果 → 形成知识积累闭环
```

---

## 二、数据库新增表结构

### 2.1 agent_call_log — Agent调用日志
记录每次Agent调用，用于权重计算和追溯。

```sql
CREATE TABLE IF NOT EXISTS agent_call_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id         TEXT UNIQUE NOT NULL,         -- UUID调用ID
    caller_agent    TEXT NOT NULL,                -- 调用方Agent ID
    target_agent    TEXT,                         -- 被调用方Agent ID（NULL=未跨Agent调用）
    topic           TEXT NOT NULL,                -- 学习主题
    subject         TEXT DEFAULT '',              -- 学科
    call_type       TEXT DEFAULT 'standalone',    -- standalone/cross_call/system
    payload         TEXT DEFAULT '{}',            -- 调用参数（JSON）
    result          TEXT DEFAULT '{}',            -- 调用结果摘要（JSON）
    latency_ms      INTEGER DEFAULT 0,            -- 调用耗时
    success         INTEGER DEFAULT 1,            -- 1=成功 0=失败
    weight_used     REAL DEFAULT 0.0,             -- 调用时使用的Agent权重
    call_chain      TEXT DEFAULT '[]',            -- JSON数组：调用链 [caller, target1, target2]
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (caller_agent) REFERENCES agents(agent_id),
    FOREIGN KEY (target_agent) REFERENCES agents(agent_id)
);
CREATE INDEX IF NOT EXISTS idx_agent_call_caller ON agent_call_log(caller_agent);
CREATE INDEX IF NOT EXISTS idx_agent_call_target ON agent_call_log(target_agent);
CREATE INDEX IF NOT EXISTS idx_agent_call_topic ON agent_call_log(topic);
CREATE INDEX IF NOT EXISTS idx_agent_call_created ON agent_call_log(created_at);
```

### 2.2 agent_weight_config — Agent权重配置
管理员可配置的Agent权重基准 + 系统计算的动态权重。

```sql
CREATE TABLE IF NOT EXISTS agent_weight_config (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id        TEXT UNIQUE NOT NULL,         -- 关联agents表
    -- 静态配置（管理员可调整）
    base_weight     REAL DEFAULT 1.0,             -- 基础权重 0.0-2.0
    max_calls_per_min INTEGER DEFAULT 10,         -- 每分钟最大调用次数
    priority        INTEGER DEFAULT 5,            -- 优先级 1-10（越小越优先）
    -- 动态统计（系统自动更新）
    call_count      INTEGER DEFAULT 0,            -- 总调用次数
    success_count   INTEGER DEFAULT 0,            -- 成功次数
    fail_count      INTEGER DEFAULT 0,            -- 失败次数
    avg_latency_ms  REAL DEFAULT 0.0,             -- 平均延迟
    -- 动态权重（系统计算：base_weight × success_rate × latency_bonus）
    dynamic_weight  REAL DEFAULT 1.0,             -- 当前动态权重
    last_calculated TEXT,                         -- 最后计算时间
    -- 元信息
    config_json     TEXT DEFAULT '{}',            -- 扩展配置
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_agent_weight_agent ON agent_weight_config(agent_id);
```

### 2.3 knowledge_accumulation — 自积累知识库
Agent产出的可复用知识，供其他Agent查询。

```sql
CREATE TABLE IF NOT EXISTS knowledge_accumulation (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    -- 知识标识
    knowledge_id    TEXT UNIQUE NOT NULL,         -- 知识唯一ID（topic+agent组合）
    topic           TEXT NOT NULL,                -- 关联主题
    subject         TEXT DEFAULT '',              -- 学科
    knowledge_type  TEXT NOT NULL,                -- concept/explanation/test/solution/pattern
    -- 知识内容
    content         TEXT NOT NULL,                -- 知识正文
    summary         TEXT DEFAULT '',              -- 摘要（供快速检索）
    -- 来源信息
    source_agent    TEXT NOT NULL,                -- 产出Agent
    source_call_id  TEXT,                         -- 关联agent_call_log.id
    -- 质量评估
    quality_score   REAL DEFAULT 0.0,             -- 0-100 质量评分
    usage_count     INTEGER DEFAULT 0,            -- 被引用次数
    -- 元数据
    tags            TEXT DEFAULT '[]',            -- JSON数组：标签
    related_nodes   TEXT DEFAULT '[]',            -- JSON数组：关联knowledge_nodes
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (source_agent) REFERENCES agents(agent_id),
    FOREIGN KEY (source_call_id) REFERENCES agent_call_log(id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_topic ON knowledge_accumulation(topic);
CREATE INDEX IF NOT EXISTS idx_knowledge_subject ON knowledge_accumulation(subject);
CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_accumulation(knowledge_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_quality ON knowledge_accumulation(quality_score);
CREATE INDEX IF NOT EXISTS idx_knowledge_source ON knowledge_accumulation(source_agent);
```

### 2.4 agents 表扩展字段
在现有agents表基础上添加权重相关字段（通过迁移实现）。

```sql
-- 以下列通过 ALTER TABLE 添加，不修改原SCHEMA
ALTER TABLE agents ADD COLUMN base_weight REAL DEFAULT 1.0;
ALTER TABLE agents ADD COLUMN call_count INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN success_count INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN fail_count INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN dynamic_weight REAL DEFAULT 1.0;
ALTER TABLE agents ADD COLUMN last_call_at TEXT;
```

### 2.5 reasoning_logs 表扩展
```sql
-- 通过迁移添加以下列
ALTER TABLE reasoning_logs ADD COLUMN agent_id TEXT DEFAULT '';
ALTER TABLE reasoning_logs ADD COLUMN call_chain TEXT DEFAULT '[]';
ALTER TABLE reasoning_logs ADD COLUMN context_injected TEXT DEFAULT '';
```

---

## 三、架构设计

### 3.1 模块结构
```
agent_core/
  models.py           # 现有：AgentState, ToolCall, AgentResult, TaskProfile
  router.py           # 现有：RouterAgent
  model_registry.py   # 现有：8个模型注册
  langgraph_engine.py # 现有：并行编排引擎
  orchestrator.py     # 现有：统一编排器
  ─────────────────── 新增 ───────────────────
  weight_manager.py   # Agent权重管理器
  knowledge_cache.py  # 自积累知识库服务
  cross_caller.py     # Agent跨调用管理器
  pipeline.py         # Agent调用链编排器
```

### 3.2 核心流程

#### 流程1：学习请求处理
```
1. 用户输入 topic
2. RouterAgent.analyze() → TaskProfile
3. KnowledgeCache.query(topic, subject)
   → 若找到高质量积累知识 → 直接返回（不走LLM）
4. 否则 → Router 路由到对应Agent
5. Agent执行 → 写入knowledge_accumulation
6. 更新agent_weight_config统计
7. 返回结果
```

#### 流程2：Agent跨调用
```
1. Agent A 执行中需要Agent B的结果
2. CrossCaller.get_agent_result(agent_id, topic)
   → 先查KnowledgeCache（命中则返回）
   → 未命中则调用Agent B.run()
   → 写入KnowledgeCache
3. 记录到agent_call_log
4. 更新Agent B的动态权重
```

#### 流程3：权重计算
```
dynamic_weight = base_weight × success_rate × latency_factor

success_rate = success_count / (success_count + fail_count)
latency_factor = 1.0 / (1.0 + log1p(avg_latency_ms / 1000))
                # 延迟越短，因子越接近1.0

权重更新时机：
- 每次Agent调用完成后
- 每分钟定时批量更新
```

---

## 四、实现计划

### Phase 1：数据库迁移（本次）
- [x] 新增4张表（agent_call_log, agent_weight_config, knowledge_accumulation）
- [x] 扩展agents表和reasoning_logs表
- [ ] 填充初始权重数据

### Phase 2：核心模块（下一步）
- [ ] weight_manager.py — 权重计算与管理
- [ ] knowledge_cache.py — 知识库读写
- [ ] cross_caller.py — 跨Agent调用

### Phase 3：集成（后续）
- [ ] 更新orchestrator.py接入新机制
- [ ] 更新feynman_engine写入KnowledgeCache
- [ ] 更新admin API暴露权重配置接口

---

## 五、数据流图

```
                    ┌─────────────────────────────┐
                    │     KnowledgeCache           │
                    │  (knowledge_accumulation)    │
                    │  可复用的Agent产出知识        │
                    └──────────┬──────────────────┘
                               │ 查询/写入
                    ┌──────────▼──────────────────┐
                    │     CrossCaller              │
                    │  Agent跨调用管理器            │
                    │  先查缓存 → 未命中调Agent      │
                    └──────────┬──────────────────┘
                               │ 调用
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
  ┌──────▼──────┐      ┌──────▼──────┐      ┌──────▼──────┐
  │feynman      │      │detector     │      │adaptive     │
  │_teacher     │      │             │      │_path       │
  └──────┬──────┘      └──────┬──────┘      └──────┬──────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │     WeightManager            │
                    │  动态权重计算                 │
                    │  base × success_rate × latency│
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │   agent_call_log             │
                    │   调用历史 → 权重计算来源     │
                    └─────────────────────────────┘
```

---

## 六、预期效果

| 指标 | 当前 | 预期 |
|------|------|------|
| 相同主题重复调用LLM | 100% | <20%（有积累命中时直接返回） |
| Agent调用选择 | Router关键词 | 关键词+权重综合 |
| 跨Agent数据复用 | 0 | 100%（自动） |
| 权重自我调节 | 无 | 实时（基于成功率和延迟） |
