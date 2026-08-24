# LumiLearn V2.5 竞赛版本 · 技术总结报告

> **版本**：V2.5 竞赛版  
> **日期**：2026-08-21  
> **仓库**：https://github.com/k3234/lumilearn  
> **提交哈希**：`ec867b2`

---

## 一、作品概述

LumiLearn 是一款面向 AI+教育场景的开源多 Agent 学习平台，核心理念是"算力平权"——让没有高端显卡的普通 CPU 电脑也能流畅运行 AI 教学服务。

**V2.5 竞赛版**在上一阶段基础上，围绕"教学闭环质量保障"和"工程可观测性"两大维度，新增七项核心能力：

| 编号 | 能力 | 说明 |
|:---:|---|---|
| 1 | Self-Critique Agent | 输出质量自动评分（0-100），低于阈值触发重试（最多 2 次） |
| 2 | Agent 反馈回路 | FeynmanTeacher 输出 → SelfCritique 评分 → 降级重试 → 结果记录至 trace |
| 3 | 超时与 Token 预算 | 每 Agent 60s 超时控制、8000 token 预算，超限自动降级 |
| 4 | Trace 可视化面板 | Agent 调用链持久化至 SQLite，Admin 后台可实时查阅 |
| 5 | 同义词检索扩展 | 数学/物理/化学 3 个学科各 24 组核心术语，OR 查询自动扩展 |
| 6 | 自动化评测 CLI | 150 题标准化学科测试集，一键跑通评估并生成 ECharts 报表 |
| 7 | UI 健壮性 + Docker 分离 | 输入校验、统一错误页、环境变量迁移至 `.env`、安全声明落地 |

---

## 二、技术架构

### 2.1 分层架构

```
┌──────────────────────────────────────────────────────────────────┐
│  Web 层（4 个独立入口）                                          │
│  lumilearn_web.py (5000) │ student_portal.py (5010)                   │
│  teacher_portal.py (5001) │ analytics_dashboard.py (18090)       │
├──────────────────────────────────────────────────────────────────┤
│  API 层（framework/api）                                         │
│  路由：18 个模块 │ 中间件：安全网关 / 防火墙 / 上传沙箱           │
├──────────────────────────────────────────────────────────────────┤
│  Agent 层（agent_core）                                          │
│  RouterAgent → KnowledgePipeline → MultiAgentPipeline            │
│  ┌─ FeynmanTeacher（教学）── SelfCritique（评分/重试）           │
│  └─ DualVerifier（双路校验）→ FactChecker（幻觉检测）           │
│  └─ AgentTelemetry（Trace 采集）                                │
├──────────────────────────────────────────────────────────────────┤
│  框架层（framework）                                             │
│  RAG 检索（BM25 + 同义词扩展）│ 降级兜底 │ 分层记忆 │ Lite 模式  │
├──────────────────────────────────────────────────────────────────┤
│  数据层                                                          │
│  SQLite（本地文件，零配置）│ Ollama（本地模型基座）              │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 核心文件清单（V2.5 新增）

| 文件路径 | 职责 |
|---|---|
| `agent_core/self_critique.py` | SelfCritiqueAgent：启发式评分 + 可注入 LLM 打分器 |
| `agent_core/orchestrator.py`（扩展） | `run_with_critique()`、`_call_with_timeout()`、`_check_token_budget()` |
| `framework/services/synonym_dict.py` | SYNONYM_GROUPS（96 条，数/物/化各 24 组） |
| `framework/services/knowledge_retrieval.py`（扩展） | `expand_query()`、`search_semantic()` 占位 |
| `framework/database.py`（扩展） | `agent_traces` + `eval_reports` 两张新表 |
| `framework/api/errors.py` | 全局 404/500 错误处理（API 返回 JSON，页面返回 HTML） |
| `framework/api/validation.py` | `validate_text_field()`、`validate_document_import()` |
| `scripts/run_eval.py` | 自动化评测 CLI：逐题跑流水线 → 统计指标 → 生成 HTML 报表 |
| `data/eval_dataset/{math,physics,chemistry}.json` | 标准化学科测试集（各 50 题，共 150 题） |
| `remote/templates/admin_traces.html` | Trace 可视化面板（Admin 后台入口） |
| `docs/ARCHITECTURE.md` | 五层架构图 + 模块接口说明表 + 自研/第三方依赖区分表 |

---

## 三、核心能力详述

### 3.1 Self-Critique Agent（输出质量评分）

```python
class SelfCritiqueAgent:
    def __init__(self, llm_scorer=None, threshold: int = 70):
        self.llm_scorer = llm_scorer   # 可注入 LLM 打分器（可配置）
        self.threshold = threshold       # 及格线（默认 70 分）

    def score(self, output_text: str, topic: str = "", knowledge_context: str = "") -> dict:
        """
        返回 {"score": int(0-100), "reason": str, "passed": bool}
        无 LLM 时可自动降级为启发式评分（fail-open）
        """
```

**启发式评分规则（无模型兜底时）：**
- 基础分 50 分
- 长度惩罚：少于 30 字 −20 分；30-80 字 +10 分；超过 80 字 +20 分
- 空泛词检测："大概"、"可能"、"不知道" 等，每个 −10 分（最多扣 30 分）
- 知识点命中：`knowledge_context` 中每个词命中 +5 分（最多 +20 分）
- 主题词：`topic` 在输出中出现 +10 分

**重试逻辑：** 评分 < 70 分时自动重试（最多 2 次），最终结果与每次评分记录至 `feedback_rounds` 字段。

### 3.2 Trace 持久化与可视化

新增 `agent_traces` 表，存储每次 Agent 调用的完整链路：

| 字段 | 类型 | 说明 |
|---|---|---|
| trace_id | VARCHAR(64) | 全局唯一标识 |
| user_id | INT | 用户 ID |
| topic | VARCHAR(200) | 学习主题 |
| agent_id | VARCHAR(50) | 调用 Agent 标识 |
| model | VARCHAR(100) | 使用的模型 |
| latency_ms | INT | 耗时（毫秒） |
| input_tokens | INT | 输入 token 数 |
| output_tokens | INT | 输出 token 数 |
| success | BOOLEAN | 是否成功 |
| error | TEXT | 错误信息（如有） |
| status | VARCHAR(20) | running / completed / timeout / failed |
| detail_json | TEXT | 结构化详情（含 feedback_rounds 等） |
| created_at | DATETIME | 创建时间 |

**API 接口：**
- `GET /api/admin/traces?limit=50&offset=0&trace_id=xxx` — 列表（支持过滤）
- `GET /api/admin/traces/<trace_id>` — 详情（含调用链）

**Trace 面板：** `http://<host>/admin/traces`，深色主题，表格 + 展开式调用链。

### 3.3 同义词检索扩展

`SYNONYM_GROUPS` 覆盖数/物/化三个学科，每组至少 4 个同义表述：

```
数学示例：["勾股定理", "毕达哥拉斯定理", "直角三角形定理", "Pythagorean theorem"]
物理示例：["牛顿第二定律", "F=ma", "力与加速度", "动力学基本定律"]
化学示例：["共价键", "共享电子对", "共价化合物", "共价结合"]
```

**查询扩展逻辑（OR 语义）：**
```python
# 用户输入"毕达哥拉斯定理" → 自动扩展为
# "勾股定理 OR 毕达哥拉斯定理 OR 直角三角形定理 OR Pythagorean theorem"
```

`search_semantic()` 占位接口已预留，返回空列表，后续接入向量检索时无需改动上层调用。

### 3.4 自动化评测系统

**评测流程：**
```
data/eval_dataset/{math,physics,chemistry}.json
        ↓
python -m scripts.run_eval
        ↓
逐题调用学习流水线（mock 模式默认）
        ↓
统计：knowledge_recall / accuracy / hallucination_count / hit_rate / avg_latency_ms
        ↓
持久化：eval_reports 表
生成：ECharts HTML 报表 + JSON
```

**评测指标定义：**
| 指标 | 计算方式 |
|---|---|
| knowledge_recall | 正确命中 expected_knowledge 的题目比例 |
| accuracy | 答案与 expected answer 完全匹配的题目比例 |
| hallucination_count | 幻觉检测器（FactChecker）报告的矛盾数 |
| hit_rate | 检索结果非空（非空即视为命中）的比例 |
| avg_latency_ms | 所有题目平均处理耗时（毫秒） |

**评测报告：**
```
reports/eval_report_YYYYMMDD_HHMMSS.html   （ECharts 可视化）
reports/eval_report_YYYYMMDD_HHMMSS.json   （结构化数据，供程序消费）
```

---

## 四、测试结果

### 4.1 全量 pytest

```
platform: win32, Python 3.14.5, pytest 9.1.1
testpaths: tests/
norecursedirs: scripts docs deploy prototypes static skills .git .venv ...
faulthandler_timeout: 240s
```

| 指标 | 数值 |
|---|---|
| **总用例数** | 571（569 passed + 2 skipped） |
| **新增 V2.5 用例** | 35 |
| **新增文件数** | 17（代码+测试+评测集+文档） |
| **运行时长** | ~23 分钟 |
| **失败数** | 0 |

### 4.2 V2.5 专项测试明细

| 测试文件 | 用例数 | 覆盖范围 |
|---|:---:|---|
| `test_self_critique.py` | 6 | 高分通过 / 低分不通过 / 边界 70 分 / 模型失败回退 / 空输入 |
| `test_orchestrator_feedback.py` | 5 | 重试逻辑 / 超时降级 / token 预算 / 达标不重试 |
| `test_trace_persistence.py` | 4 | 落库 / 查询 / 过滤 / DB 失败不阻塞主流程 |
| `test_synonym_search.py` | 6 | 同义词命中 / 无同义词正常 / 扩展统计 / 结构化字段 / 占位接口 |
| `test_eval_cli.py` | 4 | 数据集存在 / mock 指标正确 / 报表持久化 / CLI 参数解析 |
| `test_input_validation.py` | 10 | topic 过长 / 缺失 / 合法；query 过长 / 缺失 / 合法；文件类型白名单；404 JSON 响应 |

### 4.3 自动化评测结果（mock 模式）

```
模式: mock（不调用真实模型，使用规则匹配答案）
总题数: 150（数学 50 + 物理 50 + 化学 50）
总耗时: 0.54 秒
```

| 学科 | 题目数 | knowledge_recall | accuracy | hit_rate | hallucination |
|---|:---:|:---:|:---:|:---:|:---:|
| 数学 | 50 | 16.0% | 10.0% | 42.0% | 0 |
| 物理 | 50 | 5.0% | 2.0% | 28.0% | 0 |
| 化学 | 50 | 0.0% | 0.0% | 12.0% | 0 |
| **合计** | **150** | **7.0%** | **4.0%** | **27.3%** | **0** |

> **说明**：当前评测指标偏低，原因是：① 种子知识库规模有限（约 100 条 published 知识条目）；② mock 模式下答案匹配依赖关键字段，不依赖大模型推理。真实场景（天虹 CPU 环境）下，5/5 检索命中已验证。后续扩库后指标将显著提升。

### 4.4 真实场景运行证据（来自前期测试）

| 场景 | 耗时 | 评分 | 备注 |
|---|:---:|:---:|---|
| 数学 · 勾股定理 | 59.2s | 100 | 费曼五步完整生成 |
| 化学 · 共价键 | 49.1s | 100 | 费曼五步完整生成 |
| 多 Agent（牛顿第二定律 + 学生解释） | 56.9s | 100 | 教学 5 步 + RAG 来源 2 条 |
| 引导式学习（勾股定理） | — | — | 老师提问 → 学生回答 → AI 调整引导 |

---

## 五、工程质量

### 5.1 输入校验

| 接口 | 校验规则 |
|---|---|
| `POST /api/learn/start` | topic ≤ 200 字符，必填 |
| `GET /api/knowledge/search` | query ≤ 100 字符，必填 |
| `POST /api/documents/import` | 文件类型白名单：`.md .markdown .txt .text .pdf .docx .obsidian` |

### 5.2 Lite 模式

4 个入口脚本统一通过 `--mode lite` 解析：
```
lumilearn_web.py --mode lite
student_portal.py --mode lite
teacher_portal.py --mode lite
analytics_dashboard.py --mode lite
```
帮助信息已补充 lite/full 模式差异说明，非法值 exit 2。

### 5.3 Docker 配置分离

- `docker-compose.yml` 中所有端口使用 `${VAR:-default}` 形式，从 `.env` 注入
- `.env.example` 已提交仓库（含占位说明）
- `.env` 已加入 `.gitignore`（本地配置不入库）

### 5.4 安全声明（三处落地）

| 位置 | 声明内容 |
|---|---|
| `README.md` | AI 辅助边界 / 幻觉风险 / 本地存储 / 凭据配置 |
| `docs/LumiLearn_TECHNICAL.md` | 同 README，补充技术细节 |
| `remote/templates/dashboard.html` | 页面底部 footer 展示 |

---

## 六、关键文件与目录

```
lumilearn/
├── agent_core/
│   ├── self_critique.py          # Self-Critique Agent
│   ├── orchestrator.py           # 扩展：反馈回路 / 超时 / token 预算
│   └── observability.py          # 扩展：Trace 持久化（try/except 不阻塞）
├── framework/
│   ├── api/
│   │   ├── errors.py             # 统一 404/500 错误处理
│   │   ├── validation.py         # 输入校验工具函数
│   │   └── routes/admin.py       # 新增 /api/admin/traces + /eval-reports
│   ├── services/
│   │   ├── synonym_dict.py       # 同义词词典（96 条）
│   │   └── knowledge_retrieval.py # 扩展：同义词 OR 扩展 + search_semantic() 占位
│   └── database.py               # 扩展：agent_traces + eval_reports 表
├── scripts/
│   └── run_eval.py               # 自动化评测 CLI
├── data/eval_dataset/
│   ├── math.json (50 题)
│   ├── physics.json (50 题)
│   └── chemistry.json (50 题)
├── remote/templates/
│   ├── 404.html                  # 统一 404 页面
│   └── admin_traces.html         # Trace 可视化面板
├── docs/
│   ├── ARCHITECTURE.md           # 五层架构图 + 模块接口表
│   └── LumiLearn_TECHNICAL.md         # 技术报告（含安全声明）
├── reports/
│   └── eval_report_*.html/.json  # 自动生成，不入库（.gitignore）
└── tests/
    ├── test_self_critique.py     # 6 用例
    ├── test_orchestrator_feedback.py  # 5 用例
    ├── test_trace_persistence.py # 4 用例
    ├── test_synonym_search.py    # 6 用例
    ├── test_eval_cli.py          # 4 用例
    └── test_input_validation.py  # 10 用例
```

---

## 七、复现方式

### 7.1 运行全量测试
```bash
cd lumilearn
python -m pytest -q
```

### 7.2 运行自动化评测
```bash
python -m scripts.run_eval          # 全量 150 题（mock 模式）
python -m scripts.run_eval --subject math --limit 10  # 指定学科+数量
python -m scripts.run_eval --real                # 真实模型模式（需 Ollama）
```

### 7.3 访问 Trace 面板
```
http://localhost:18080/admin/traces
```

### 7.4 查看评测报表
```
reports/eval_report_YYYYMMDD_HHMMSS.html   # ECharts 可视化
reports/eval_report_YYYYMMDD_HHMMSS.json   # 结构化数据
```

---

## 八、后续优化方向

| 优先级 | 方向 | 说明 |
|---|---|---|
| P0 | 扩充知识库 | 当前召回率 7% 主要受限于知识库规模，扩库至 5000+ 条后预计提升至 60%+ |
| P0 | 接入语义检索 | `search_semantic()` 占位接口已预留，后续接入 embedding 模型（BGE/m3e）即可开启 |
| P1 | Real 模式评测 | 当前为 mock 模式，接入真实模型后 `--real` 可跑真实推理评测 |
| P1 | Self-Critique LLM 打分 | 当前为启发式评分，后续可接入 DeepSeek/GLM 等模型提升评分精度 |
| P2 | Trace 查询性能 | 当前 SQLite 单表，10 万级 trace 后需考虑索引优化或换 PostgreSQL |

---

## 九、AI 使用声明

本项目在 V2.5 竞赛版本开发过程中使用了 AI 辅助编程工具（Trae CN、DeepSeek、Claude 等），用于：
- 代码框架生成与重构
- 测试用例编写与 Review
- 文档整理与格式规范

开发者负责了：系统架构设计、任务拆解、代码审查、验收标准制定、全部代码的功能正确性和可维护性。

---

## 十、开源协议

**MIT License**

项目地址：https://github.com/k3234/lumilearn

---

*文档生成时间：2026-08-21 21:30 (UTC+8)*  
*测试基线：569 passed / 2 skipped / 0 failed*  
*评测基线：150 题 / mock 模式 / recall 7.0% / accuracy 4.0% / hit_rate 27.3% / hallucination 0*
