# Module 4.3 — Prompt工程：AI讲解内容自我审查

**日期**: 2026-06-01
**状态**: ✅ 完成
**相关模块**: Module 4.1（Whisper语音识别）、Module 4.2（PaddleOCR文字识别）、Module 4（多模态能力）
**难度**: ⭐⭐⭐⭐☆

---

## 📚 学习目标

完成本模块后，你将能够：

1. 理解 Prompt 工程在 AI 质量审查中的应用场景和设计原则
2. 掌握结构化输出 Prompt 的设计方法（JSON 格式约束）
3. 运用学习科学理论（布鲁姆分类法、脚手架理论、最近发展区）指导 Prompt 设计
4. 实现多维度评分体系（准确性、完整性、引导性、难度适合度）
5. 设计可切换的审查模式（quick/full/strict）以适应不同场景
6. 将 Prompt 工程与 Ollama 本地模型调用结合，构建完整的审查流水线

---

## 🧠 Prompt 工程原理简介

### 什么是 Prompt 工程？

Prompt 工程是设计和优化输入提示词（Prompt）以引导 LLM 产生期望输出的技术。在 AI 质量审查场景中，Prompt 工程的核心目标是：

```
                    ┌─────────────────────────────────┐
                    │        Prompt 工程核心要素         │
                    ├──────────────┬────────────────────┤
                    │   角色设定    │   明确模型的身份和职责  │
                    │   任务描述    │   清晰说明要做什么     │
                    │   输出格式    │   约束输出结构（JSON）  │
                    │   评分标准    │   定义评估维度和尺度    │
                    │   理论框架    │   引入学习科学指导     │
                    │   示例引导    │   提供期望的输出模板    │
                    └──────────────┴────────────────────┘
```

### 为什么需要结构化输出？

对于审查任务，结构化输出（JSON）相比自由文本有以下优势：

| 特性 | 自由文本 | 结构化 JSON |
|------|----------|-------------|
| 可解析性 | 需要额外 NLP 处理 | 直接 `json.loads()` |
| 一致性 | 每次格式不同 | 字段固定，可对比 |
| 可统计性 | 难以聚合分析 | 可直接计算平均分、趋势 |
| 下游集成 | 需要人工阅读 | 可自动入库、生成图表 |
| 容错性 | 格式错误难检测 | 字段缺失有默认值 |

### 学习科学理论在 Prompt 中的应用

```
布鲁姆分类法（Bloom's Taxonomy）
  知识层次: 记忆 → 理解 → 应用 → 分析 → 评价 → 创造
  Prompt 映射: 审查内容是否停留在低层次记忆，还是引导了高层次思考
  
脚手架理论（Scaffolding）
  核心思想: 提供适当支持 → 随着能力提升逐步撤除
  Prompt 映射: 审查讲解是否提供了足够但不过度的提示
  
最近发展区（ZPD - Zone of Proximal Development）
  核心思想: 内容难度应在学生现有水平和潜在水平之间
  Prompt 映射: 审查难度是否匹配目标学生水平（难度适合度维度）
```

---

## 🧭 实现步骤（分步详解）

### 步骤 1：设计审查 Prompt 模板

审查 Prompt 是整个系统的核心，需要包含以下要素：

```python
REVIEW_PROMPT_TEMPLATE = """你是一位资深教育质量评估专家，精通学习科学理论。
请对以下AI生成的讲解内容进行多维度质量审查。

【审查维度与评分标准】（每项1-10分）

1. 准确性（Accuracy）：知识点是否准确无误
   - 10分：所有知识点完全正确，引用精准，无任何错误
   - 7-9分：核心知识点正确，偶有表述不够精确
   - 4-6分：存在一些概念模糊或不够准确的地方
   - 1-3分：存在明显知识性错误

2. 完整性（Completeness）：是否覆盖所有关键要点
   ...

3. 引导性（Guidance）：是否引导思考而非直接给答案
   ...

4. 难度适合度（Difficulty Fit）：是否匹配目标学生水平
   ...

【学习科学理论参考】
- 布鲁姆分类法：知识层次从记忆→理解→应用→分析→评价→创造
- 脚手架理论：提供适当支持，随着能力提升逐步撤除
- 最近发展区（ZPD）：内容难度应在学生现有水平和潜在水平之间

【目标学生水平】
{student_level_desc}

【审查模式】
{mode_desc}

【讲解内容】
{content}

请以JSON格式返回审查结果，格式如下：
```json
{output_format}
```

注意事项：
{notes}
"""
```

**Prompt 设计要点**：
1. **角色设定**：`资深教育质量评估专家` — 明确身份，激活相关领域知识
2. **结构化评分**：每个维度 1-10 分，附带详细评分标准（锚定效应）
3. **理论框架**：引入布鲁姆分类法、脚手架理论、ZPD 作为评判依据
4. **输出约束**：JSON 格式，用 `{output_format}` 占位符动态替换
5. **动态参数**：`{student_level_desc}`、`{mode_desc}` 根据请求参数变化

### 步骤 2：实现评分维度体系

系统从 4 个维度对讲解内容进行评分，每个维度 1-10 分：

| 维度 | 英文名 | 考察要点 | 理论基础 |
|------|--------|----------|----------|
| 准确性 | accuracy | 知识点是否正确，引用是否精准 | 学科知识验证 |
| 完整性 | completeness | 是否覆盖所有关键要点，逻辑链条是否完整 | 知识图谱覆盖 |
| 引导性 | guidance | 是否引导思考，是否激发好奇心 | 脚手架理论 |
| 难度适合度 | difficulty_fit | 是否匹配学生水平，是否在最近发展区内 | ZPD 理论 |

**综合评分**：`overall = (accuracy + completeness + guidance + difficulty_fit) / 4`

### 步骤 3：实现三种审查模式

不同场景需要不同的审查深度，通过 `{mode}` 参数控制：

```python
REVIEW_MODES = {
    "quick": "快速审查模式：仅给出各维度评分和总分，不提供详细建议",
    "full": "完整审查模式：给出各维度评分、总分和详细改进建议",
    "strict": "严格审查模式：以更高标准评分，对每个问题零容忍"
}
```

**各模式输出格式对比**：

| 模式 | 评分 | 建议 | 严重问题 | 适用场景 |
|------|------|------|----------|----------|
| quick | ✅ | ❌ | ❌ | 批量快速筛选 |
| full | ✅ | ✅ | ❌ | 日常质量审查 |
| strict | ✅ | ✅ (含severity) | ✅ | 上线前终审 |

### 步骤 4：调用 Ollama 本地模型

```python
from lumilearn_shared import call_ollama, OLLAMA_BASE_URL

DEFAULT_MODEL = "qwen2.5:7b"

def review(self, content, student_level="junior", mode="full"):
    prompt = _build_review_prompt(content, student_level, mode)
    response = call_ollama(self.model_name, prompt, timeout=120)
    result = _parse_review_response(response)
    # ... 处理结果
```

**为什么选择 qwen2.5:7b？**
- 中文理解能力强，适合审查中文教育内容
- 7B 参数规模在本地 CPU 运行可行（约 4-8GB 内存）
- 支持 JSON 格式化输出，结构化返回效果好

### 步骤 5：构建 Flask API 端点

```python
@app.route("/api/review", methods=["POST", "OPTIONS"])
def api_review():
    """讲解内容审查端点"""
    data = request.get_json(force=True)
    
    content = data.get("content", "")
    if not content or not content.strip():
        return jsonify({"error": "缺少 content 字段或内容为空"}), 400
    
    mode = data.get("mode", "full")
    student_level = data.get("student_level", "junior")
    
    # 参数验证
    valid_modes = {"quick", "full", "strict"}
    if mode not in valid_modes:
        return jsonify({"error": f"不支持的审查模式: {mode}"}), 400
    
    # 调用审查引擎
    engine = _get_review_engine()
    result = engine.review(content, student_level=student_level, mode=mode)
    
    return jsonify({
        "scores": {
            "accuracy": result.get("accuracy", 0),
            "completeness": result.get("completeness", 0),
            "guidance": result.get("guidance", 0),
            "difficulty_fit": result.get("difficulty_fit", 0)
        },
        "overall": result.get("overall", 0),
        "suggestions": result.get("suggestions", []),
        "summary": result.get("summary", ""),
        "mode": mode,
        "student_level": student_level
    })
```

---

## 💻 关键代码（带注释）

### 审查 Prompt 构建逻辑

```python
def _build_review_prompt(content, student_level, mode):
    """构建审查Prompt
    
    根据审查模式动态调整输出格式和注意事项：
    - quick模式：只需要评分，不需要建议
    - full模式：评分+建议，标准评估
    - strict模式：评分+建议+严重问题列表，高标准评估
    """
    student_level_desc = STUDENT_LEVELS.get(student_level, STUDENT_LEVELS["general"])
    mode_desc = REVIEW_MODES.get(mode, REVIEW_MODES["full"])

    if mode == "quick":
        # 快速模式：只输出评分和一句话总结
        output_format = (
            '{"accuracy": 8, "completeness": 7, "guidance": 6, '
            '"difficulty_fit": 8, "overall": 7.5, "summary": "一句话总结"}'
        )
        notes = "只返回JSON，不要任何额外文字。summary为一句话总结，不超过30字。"
    elif mode == "strict":
        # 严格模式：增加severity和critical_issues字段
        output_format = (
            '{"accuracy": 8, "completeness": 7, "guidance": 6, '
            '"difficulty_fit": 8, "overall": 7.5, '
            '"suggestions": [{"dimension": "准确性", "issue": "问题", '
            '"fix": "建议", "severity": "高/中/低"}], '
            '"summary": "总体评价", "critical_issues": ["严重问题"]}'
        )
        notes = (
            "以最严格的标准评分，不放过任何小问题。"
            "severity分为高/中/低。critical_issues列出不容忽视的严重问题。"
        )
    else:
        # 完整模式（默认）：评分+建议
        output_format = (
            '{"accuracy": 8, "completeness": 7, "guidance": 6, '
            '"difficulty_fit": 8, "overall": 7.5, '
            '"suggestions": [{"dimension": "准确性", "issue": "问题", '
            '"fix": "建议"}], "summary": "总体评价"}'
        )
        notes = "只返回JSON，不要任何额外文字。summary为总体评价，不超过50字。"

    return REVIEW_PROMPT_TEMPLATE.format(
        content=content,
        student_level_desc=student_level_desc,
        mode_desc=mode_desc,
        output_format=output_format,
        notes=notes
    )
```

### 响应解析与容错

```python
def _parse_review_response(response_text):
    """从模型响应中解析JSON
    
    LLM 的输出可能包含 markdown 代码块标记或其他额外文字，
    所以使用正则提取第一个 { ... } 块。
    """
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if not json_match:
        return None  # 无法提取JSON，返回None让上层处理
    try:
        return json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return None  # JSON格式错误，返回None
```

### 格式化审查结果

```python
def format_review_result(review):
    """格式化审查结果为可读文本
    
    将JSON格式的审查结果转换为终端友好的可视化报告，
    包含进度条、emoji图标和层次化建议列表。
    """
    lines = []
    lines.append("=" * 50)
    lines.append("📊 讲解内容审查报告")
    lines.append("=" * 50)
    
    # 各维度评分（带进度条可视化）
    scores = {
        "准确性": review.get("accuracy", 0),
        "完整性": review.get("completeness", 0),
        "引导性": review.get("guidance", 0),
        "难度适合度": review.get("difficulty_fit", 0)
    }
    
    lines.append("📈 各维度评分：")
    for dim, score in scores.items():
        bar = "█" * int(score) + "░" * (10 - int(score))
        lines.append(f"  {dim}: {score}/10 {bar}")
    
    # 综合评分
    overall = review.get("overall", 0)
    lines.append(f"\n⭐ 综合评分: {overall}/10")
    
    # 改进建议
    suggestions = review.get("suggestions", [])
    if suggestions:
        lines.append(f"\n🔧 改进建议 ({len(suggestions)}条):")
        for i, s in enumerate(suggestions, 1):
            lines.append(f"  {i}. [{s.get('dimension', '')}] {s.get('issue', '')}")
            lines.append(f"     ➜ {s.get('fix', '')}")
    
    return "\n".join(lines)
```

### 统计分析工具

```python
def summary_stats(reviews):
    """统计多次审查的平均分和趋势
    
    用于追踪讲解质量随时间的变化：
    - 计算各维度平均分
    - 识别最佳/最差维度
    - 判断整体趋势（上升/下降/稳定）
    """
    count = len(reviews)
    dims = ["accuracy", "completeness", "guidance", "difficulty_fit"]
    
    # 计算各维度平均分
    avgs = {}
    for dim in dims:
        values = [r.get("scores", r).get(dim, 0) for r in reviews]
        avgs[dim] = round(sum(values) / count, 2)
    
    # 趋势分析：比较首次和末次审查的综合评分
    if count >= 2:
        first = reviews[0].get("overall", 0)
        last = reviews[-1].get("overall", 0)
        diff = last - first
        if diff > 0.5:
            trend = "上升趋势 ↑"
        elif diff < -0.5:
            trend = "下降趋势 ↓"
        else:
            trend = "保持稳定 →"
    
    return {
        "count": count,
        "avg_overall": avg_overall,
        "trend": trend,
        "best_dimension": dim_labels[best_dim],
        "worst_dimension": dim_labels[worst_dim]
    }
```

---

## 🎓 学习要点（核心知识点）

### 1. 布鲁姆分类法在 Prompt 设计中的应用

布鲁姆分类法将认知过程分为 6 个层次，在审查 Prompt 中用于评估内容的思维深度：

```
层次 6: 创造 (Create)    — 设计、构建、发明
层次 5: 评价 (Evaluate)  — 评判、辩护、批判
层次 4: 分析 (Analyze)   — 对比、区分、组织   ← 优质讲解应达到此层次
层次 3: 应用 (Apply)     — 使用、演示、解决
层次 2: 理解 (Understand) — 解释、总结、举例
层次 1: 记忆 (Remember)  — 识别、回忆、列出   ← 低质量讲解停留在此层次
```

**在 Prompt 中的体现**：通过"引导性"维度审查讲解是否停留在低层次记忆（灌输式），还是引导了高层次思考（分析、评价）。

### 2. 脚手架理论（Scaffolding）

脚手架理论是教育心理学中的核心概念，类比建筑中的脚手架：

```
学习过程:
  初始阶段:  ┌─────────────────┐
           │ ████████████████ │ ← 高支持（详细提示、示例、引导问题）
           │ ██████████████   │
  中间阶段:  │ ██████████       │ ← 中支持（减少提示，鼓励自主探索）
           │ ██████           │
  最终阶段:  │ ██               │ ← 低支持（独立解决问题）
           │                   │
           └─────────────────┘
```

**在 Prompt 中的体现**：通过"引导性"维度审查讲解是否提供了恰到好处的支持——既不过度（直接给答案），也不不足（缺乏引导）。

### 3. 最近发展区（ZPD）

ZPD 是维果茨基提出的概念，定义了最有效的学习区间：

```
过易区域: 学生已经掌握的 → 无聊，无学习效果
═══════════════════════════════════════════════════
最近发展区: 学生在帮助下可以达到的 → 最佳学习区间 ✅
═══════════════════════════════════════════════════
过难区域: 学生即使有帮助也无法达到的 → 挫败，无学习效果
```

**在 Prompt 中的体现**：通过"难度适合度"维度审查内容难度是否在学生的最近发展区内。

### 4. Prompt 模板设计模式

本模块使用了以下 Prompt 设计模式：

| 模式 | 说明 | 示例 |
|------|------|------|
| 角色设定 | 定义模型身份和专业领域 | `你是一位资深教育质量评估专家` |
| 锚定评分 | 提供评分锚点，减少主观偏差 | `10分：所有知识点完全正确` |
| 输出约束 | 指定输出格式，确保可解析 | `请以JSON格式返回审查结果` |
| 动态参数 | 使用占位符支持运行时配置 | `{student_level_desc}` |
| 理论注入 | 引入领域理论作为评判依据 | `布鲁姆分类法、脚手架理论、ZPD` |
| 负面约束 | 明确禁止的输出行为 | `只返回JSON，不要任何额外文字` |

### 5. 多模式切换设计

通过 `mode` 参数控制 Prompt 的详细程度，实现"一个引擎，多种输出"：

```
quick 模式:  Prompt简短 → 输出精简 → 速度快（~5-10秒）
full 模式:   Prompt标准 → 输出完整 → 速度中等（~10-20秒）
strict 模式: Prompt详细 → 输出详尽 → 速度慢（~15-30秒）
```

---

## ❓ 常见问题（FAQ）

### Q1: Ollama 模型返回的不是有效 JSON 怎么办？

**A**: 系统内置了容错机制：

1. **正则提取**：`re.search(r'\{[\s\S]*\}', response_text)` 从响应中提取 JSON 块
2. **解析验证**：`json.loads()` 验证 JSON 格式
3. **降级返回**：解析失败时返回包含 `raw_response` 的错误结果，可人工排查

```python
if result is None:
    return {
        "accuracy": 0, ..., "overall": 0,
        "summary": "模型响应解析失败，请重试",
        "raw_response": response[:500]  # 保留原始响应用于调试
    }
```

### Q2: 为什么选择 qwen2.5:7b 而不是其他模型？

**A**: 基于以下考虑：

| 模型 | 中文能力 | JSON输出 | 本地运行 | 推理速度 |
|------|----------|----------|----------|----------|
| qwen2.5:7b | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 4-8GB | ⭐⭐⭐⭐ |
| deepseek-r1:1.5b | ⭐⭐⭐ | ⭐⭐⭐ | 1-2GB | ⭐⭐⭐⭐⭐ |
| llama3:8b | ⭐⭐⭐ | ⭐⭐⭐⭐ | 4-8GB | ⭐⭐⭐ |

qwen2.5:7b 在中文理解、JSON 格式化输出和推理速度之间取得了最佳平衡。

### Q3: 如何提高审查的准确性和一致性？

**A**: 几种策略：

1. **降低温度参数**：`temperature=0.3`（已在 `call_ollama` 中设置），减少随机性
2. **多次采样取平均**：对同一内容运行 3 次审查，取平均分
3. **引入参考答案**：在 Prompt 中提供标准答案，让模型对照评估
4. **使用更大模型**：切换到 `qwen2.5:14b` 或 `qwen2.5:32b` 提升判断力
5. **人工校准**：定期人工复核审查结果，调整 Prompt 中的评分标准

### Q4: strict 模式下的 "severity" 和 "critical_issues" 有什么区别？

**A**:

- **suggestions[].severity**：针对单个改进建议的严重程度标记
  - `高`：需要立即修正的问题
  - `中`：建议修正，但不影响核心理解
  - `低`：可选的优化建议

- **critical_issues**：不容忽视的严重问题列表（如知识性错误、误导性表述）
  - 这些是必须修复的"红线问题"
  - 与 suggestions 不同，critical_issues 只包含最严重的问题

### Q5: 如何处理审查结果中的评分偏差？

**A**: 使用 `summary_stats()` 做统计分析：

```python
# 收集多次审查结果
reviews = [result1, result2, result3, ...]

# 统计分析
stats = summary_stats(reviews)
print(f"审查次数: {stats['count']}")
print(f"平均综合分: {stats['avg_overall']}")
print(f"趋势: {stats['trend']}")
print(f"最佳维度: {stats['best_dimension']}")
print(f"最差维度: {stats['worst_dimension']}")
```

通过多次审查的统计，可以识别系统性的评分偏差（如某个维度始终偏低）。

### Q6: 如何扩展新的审查维度？

**A**: 只需修改三个地方：

1. **Prompt 模板**：在 `REVIEW_PROMPT_TEMPLATE` 中添加新维度的评分标准
2. **输出格式**：在 `_build_review_prompt` 的 `output_format` 中添加新字段
3. **统计函数**：在 `summary_stats` 的 `dims` 列表中添加新维度名

例如添加"趣味性"维度：

```python
# 1. Prompt中添加
"5. 趣味性（Engagement）：是否生动有趣，能吸引学生注意力"

# 2. output_format中添加
"engagement": 8

# 3. summary_stats中添加
dims = ["accuracy", "completeness", "guidance", "difficulty_fit", "engagement"]
```

---

## 🔗 相关资源链接

| 资源 | 说明 |
|------|------|
| [Bloom's Taxonomy](https://cft.vanderbilt.edu/guides-sub-pages/blooms-taxonomy/) | 布鲁姆分类法详解（Vanderbilt大学） |
| [Zone of Proximal Development](https://www.simplypsychology.org/Zone-of-Proximal-Development.html) | 最近发展区理论详解 |
| [Scaffolding in Education](https://www.edutopia.org/blog/scaffolding-lessons-six-strategies-rebecca-alber) | 脚手架理论的教育实践 |
| [Ollama 官方文档](https://github.com/ollama/ollama) | Ollama 本地模型运行框架 |
| [Prompt Engineering Guide](https://www.promptingguide.ai/) | Prompt 工程全面指南 |
| [OpenAI Prompt Engineering](https://platform.openai.com/docs/guides/prompt-engineering) | OpenAI 官方 Prompt 工程指南 |
| [qwen2.5 模型卡片](https://ollama.com/library/qwen2.5) | Ollama 上的 qwen2.5 模型 |
| LumiLearn self_review_engine.py | 本模块审查引擎实现 |
| LumiLearn scripts/lumiterm_local_server.py | 本模块 API 端点实现 |

---

## 📝 总结

通过本模块的学习，我们实现了基于 Prompt 工程的 AI 讲解内容自我审查系统。主要收获：

1. **Prompt 工程设计** — 掌握角色设定、评分锚定、输出约束、动态参数等设计模式
2. **学习科学理论应用** — 将布鲁姆分类法、脚手架理论、ZPD 融入 Prompt 设计
3. **多维度评分体系** — 从准确性、完整性、引导性、难度适合度 4 个维度评估
4. **多模式切换** — quick/full/strict 三种模式适应不同审查场景
5. **结构化输出** — JSON 格式输出确保可解析、可统计、可对比
6. **容错设计** — 正则提取 + JSON 验证 + 降级返回的完整容错链

> **核心理念**：好的 Prompt 不只是"告诉模型做什么"，而是"为模型构建一个专业评估框架"。通过引入学习科学理论，让模型的审查结果不再是主观臆断，而是有理论依据的结构化评估。

---

## 🔜 下一步

- **Module 4.4**：PDF 文档解析 — 使用 PyMuPDF 提取 PDF 中的文字和图片
- **Module 4.5**：图像理解（Vision）— 使用 CLIP 或 LLaVA 实现图片内容理解
- **Module 4.6**：多模态对话 — 将语音识别、OCR 与 LLM 对话结合，实现全模态交互