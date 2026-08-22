# LumiLearn 教育蒸馏模型：从 rasbt 到自主研发

## 使用 rasbt/LLMs-from-scratch 学习开发的完整指南

> 方案日期：2026-06-03
> 核心理念：**不是追赶大模型，而是让大模型的教育能力蒸馏到每个设备**

---

## 一、rasbt/LLMs-from-scratch 学习注意事项

### 1.1 仓库核心结构

```
LLMs-from-scratch/
├── ch01-ch07/          # 7章核心内容
├── appendix-A-E/        # 附录（PyTorch/LoRA等）
├── pkg/                 # 封装好的 Python 包
│   └── llms_from_scratch/
│       ├── ch02-ch07.py  # 每章代码
│       ├── generate.py     # 生成函数
│       └── utils.py       # 工具函数
├── setup/              # 环境配置
└── bonus/             # 额外内容
```

### 1.2 学习顺序建议

```
正确顺序（推荐）
├── ch01: 背景理解（1天）
├── ch02: Tokenizer（1周）← 当前
├── ch03: Attention（1周）
├── ch04: GPT架构（2周）← 核心
├── ch05: 预训练（2周）
├── ch06: 指令微调（2周）← 教育方向关键
└── ch07: RLHF（1周）

错误顺序
❌ 直接跳到 ch05 预训练（基础不牢）
❌ 跳过 ch06 直接做 ch07（微调很重要）
❌ 只看代码不看 Notebook（理解不深）
```

### 1.3 每章关键注意点

#### ch02: Tokenizer

| 注意点 | 说明 |
|--------|------|
| BPE 原理 | 不是简单的分词，是统计压缩算法 |
| 词汇表大小 | 太小→质量差，太大→效率低 |
| 中文支持 | GPT-2 BPE 对中文需要特殊处理 |
| 训练数据 | 教育领域需要专门的 tokenizer |

```python
# ❌ 常见错误：直接使用英文 tokenizer
tokenizer = tiktoken.get_encoding("gpt2")
tokenizer.encode("三角形")  # 中文效果差

# ✅ 正确：为教育领域训练专门的 tokenizer
from train_bpe_tokenizer import train_education_tokenizer
tokenizer = train_education_tokenizer(education_corpus)
```

#### ch03: Attention

| 注意点 | 说明 |
|--------|------|
| 因果掩码 | 必须！否则训练时信息泄露 |
| 缩放因子 | √d_k 防止梯度消失 |
| 内存优化 | batch_size × seq_len² 是瓶颈 |
| KV Cache | 推理时必须用，否则太慢 |

```python
# ❌ 常见错误：忘记因果掩码
attn_scores = queries @ keys.T  # 全部可见！

# ✅ 正确：添加因果掩码
attn_scores = queries @ keys.T
attn_scores.masked_fill_(mask.bool(), -torch.inf)
```

#### ch04: GPT 架构

| 注意点 | 说明 |
|--------|------|
| 残差连接 | 每个子层都有，缺一不可 |
| LayerNorm 位置 | Pre-LN vs Post-LN（rasbt 用 Post） |
| 参数初始化 | 影响训练稳定性 |
| 位置编码 | 绝对位置 vs 相对位置 vs RoPE |

```python
# ❌ 常见错误：省略残差连接
x = self.attention(x)
x = self.ln2(x)  # 丢失信息！

# ✅ 正确：残差连接
x = x + self.attention(x)
x = x + self.ffn(x)
```

#### ch05: 预训练

| 注意点 | 说明 |
|--------|------|
| 数据质量 | 垃圾数据→垃圾模型 |
| 学习率调度 | Warmup + Cosine 必须 |
| 梯度裁剪 | 防止梯度爆炸 |
| 训练监控 | 关注 loss 是否下降 |

#### ch06: 指令微调 ⭐（教育方向关键）

| 注意点 | 说明 |
|--------|------|
| 数据格式 | 指令+输入+输出格式统一 |
| 数据质量 | > 数据数量（教育场景尤其重要） |
| 领域适配 | 教育专用指令数据 |
| 防止遗忘 | 保留通用能力 |

```python
# 教育指令数据格式示例
instruction_data = [
    {
        "instruction": "解释三角形的面积公式",
        "input": "已知底=6cm，高=4cm",
        "output": "三角形面积 = 底×高÷2 = 6×4÷2 = 12平方厘米"
    },
    {
        "instruction": "引导学生思考分数加法",
        "input": "1/2 + 1/4 = ?",
        "output": "先通分：1/2=2/4，所以2/4+1/4=3/4。你能想想为什么分母不同要先通分吗？"
    }
]
```

#### ch07: RLHF

| 注意点 | 说明 |
|--------|------|
| Reward Model | 训练数据难获取 |
| PPO 复杂度 | 实现难度高，调参难 |
| DPO 替代 | 更简单，效果也不错 |
| 教育场景 | 可以用学生反馈作为 reward |

### 1.4 LumiLearn 代码对齐清单

| rasbt 章节 | 对应 LumiLearn 文件 | 对齐状态 |
|------------|---------------------|----------|
| ch02 | framework/tokenizer.py | ⚠️ 需补充训练功能 |
| ch03 | model.py (Attention) | ✅ 已实现 |
| ch04 | model.py (GPT) | ✅ 需优化 |
| ch05 | train.py | ⚠️ 需补充预训练 |
| ch06 | 微调脚本 | ❌ 未实现 |
| ch07 | 对齐脚本 | ❌ 未实现 |

---

## 二、教育蒸馏技术路线

### 2.1 什么是模型蒸馏？

```
模型蒸馏（Distillation）
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  大模型（Teacher）              小模型（Student）                     │
│  ┌─────────┐                  ┌─────────┐                          │
│  │ DeepSeek │                  │ Qwen2.5  │                          │
│  │  V4-Pro  │ ──蒸馏────→    │   -7B    │                          │
│  │ 1.6T参数 │                  │  7B参数  │                          │
│  └─────────┘                  └─────────┘                          │
│                                                                     │
│  目标：让小模型学会大模型的"教育能力"                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 教育蒸馏 vs 通用蒸馏

| 维度 | 通用蒸馏 | 教育蒸馏 |
|------|----------|----------|
| **Teacher** | GPT-4 / Claude | DeepSeek / Qwen |
| **Student** | 小模型 | 极小模型（1-3B） |
| **目标** | 通用能力 | **教育能力** |
| **Loss** | 预测分布 | 预测分布 + **教育Loss** |
| **评价** | Benchmark | 学生学习效果 |

### 2.3 教育蒸馏三要素

```
教育蒸馏三要素
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  1. 知识蒸馏（Knowledge Distillation）                               │
│  └── 让小模型学习大模型的"解题思路"                                  │
│                                                                     │
│  2. 能力蒸馏（Capability Distillation）                              │
│  └── 让小模型学会"引导学生思考"而不是"直接给答案"                      │
│                                                                     │
│  3. 风格蒸馏（Style Distillation）                                  │
│  └── 让小模型模仿"优秀教师的教学风格"                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.4 教育蒸馏技术实现

```python
class EducationDistillationLoss(nn.Module):
    """教育蒸馏损失函数"""

    def __init__(self, alpha=0.7, beta=0.2, gamma=0.1):
        super().__init__()
        self.alpha = alpha  # 知识蒸馏权重
        self.beta = beta    # 能力蒸馏权重
        self.gamma = gamma   # 风格蒸馏权重

    def forward(self, student_logits, teacher_logits, labels, education_labels):
        # 1. 知识蒸馏损失（KL散度）
        # 让小模型的输出分布接近大模型
        kd_loss = F.kl_div(
            F.log_softmax(student_logits / T, dim=-1),
            F.softmax(teacher_logits / T, dim=-1),
            reduction='batchmean'
        ) * (T * T)

        # 2. 能力蒸馏损失
        # 训练"引导能力"：学生能回答引导性问题
        cap_loss = F.cross_entropy(student_logits, education_labels)

        # 3. 风格蒸馏损失
        # 训练"教学风格"：用优秀教师的输出作为目标
        style_loss = F.mse_loss(student_logits, teacher_logits.detach())

        # 综合损失
        total_loss = self.alpha * kd_loss + self.beta * cap_loss + self.gamma * style_loss

        return total_loss, {
            "knowledge": kd_loss.item(),
            "capability": cap_loss.item(),
            "style": style_loss.item()
        }
```

### 2.5 教育数据蒸馏流程

```python
class EducationDataDistiller:
    """教育数据蒸馏：将大模型输出转为训练数据"""

    def __init__(self, teacher_model):
        self.teacher = teacher_model

    def distill_instruction(self, question, mode="guided"):
        """
        使用大模型生成教育导向的回答
        mode: guided（引导）| direct（直接）| questioning（提问）
        """
        if mode == "guided":
            prompt = f"""你是一位优秀的数学老师。
            学生问：{question}
            请用引导式方法回答，先提出思考问题，不要直接给答案。"""
        elif mode == "questioning":
            prompt = f"""你是一位苏格拉底式的老师。
            学生问：{question}
            请提出3个递进式问题引导学生自己思考。"""

        # 调用大模型生成
        response = self.teacher.generate(prompt)

        return {
            "question": question,
            "response": response,
            "mode": mode
        }

    def create_distillation_dataset(self, questions, mode="guided"):
        """创建蒸馏数据集"""
        dataset = []
        for q in questions:
            data = self.distill_instruction(q, mode)
            dataset.append(data)

        # 保存为训练格式
        return dataset

# 使用示例
distiller = EducationDataDistiller(teacher=deepseek_v4)

# 生成引导式教育数据
questions = [
    "三角形面积怎么算？",
    "分数的加减法怎么做？",
    "一元一次方程怎么解？"
]

education_data = distiller.create_distillation_dataset(questions, mode="guided")

# 保存为训练格式
with open("education_distilled_data.json", "w") as f:
    json.dump(education_data, f, ensure_ascii=False, indent=2)
```

---

## 三、追赶大厂的技术策略

### 3.1 现实差距分析

| 模型 | 参数 | 训练成本 | vs 我们的目标 |
|------|------|----------|---------------|
| DeepSeek V4-Pro | 1.6T | ~$1亿 | 无法追赶 |
| Qwen2.5-72B | 72B | ~$1000万 | 无法追赶 |
| Qwen2.5-7B | 7B | ~$10万 | 短期可达 |
| Qwen2.5-1.5B | 1.5B | ~$1万 | **我们的目标** |

### 3.2 差异化竞争策略

```
传统追赶（不可能）
❌ "我要做和 DeepSeek 一样强的通用模型"

教育专精（现实可行）
✅ "我要做**教育领域可用的轻量小模型**"
   - 7B 参数小模型在低配设备上实现可用的教学辅助能力
   - 1.5B 参数小模型实现轻量教学辅助能力
   - 在教育场景下，用远小于通用大模型的成本获得可用的教学效果
```

### 3.3 技术追赶路线

#### Phase 1: 学习与验证（2026.6-9）

```
rasbt/LLMs-from-scratch 学习路线

Month 1
├── ch02-ch04: 基础架构
├── ch05: 预训练
└── 目标：能独立实现 GPT 训练

Month 2
├── ch06: 指令微调
└── 目标：能微调教育模型

Month 3
├── ch07: RLHF / DPO
└── 目标：实现教育对齐
```

#### Phase 2: 小模型研发（2026.9-12）

```
研发 Qwen2.5-1.5B 教育版

Step 1: 基座选择
├── 选择 Qwen2.5-1.5B 作为基座
├── 或从零训练 tiny-LLM
└── 参数量：1.5B

Step 2: 教育数据构建
├── 使用大模型 API（如 DeepSeek/Qwen）生成教育数据
├── 重点：引导式教学数据
├── 数量：10万条
└── 格式：指令+输入+输出

Step 3: 指令微调
├── 使用教育数据微调基座
├── 目标：学会"当老师"
└── 评测：能否正确引导思考

Step 4: 教育对齐
├── 使用 DPO 优化教学风格
├── 人类反馈：优秀教师的教学数据
└── 目标：教学效果接近大模型
```

#### Phase 3: 极致优化（2027+）

```
让 1.5B 模型在教育场景接近 7B 效果

技术手段：
├── 知识蒸馏：用大模型教小模型
├── 量化压缩：Q4 量化，1GB 可运行
├── KV Cache：推理加速 3x
├── Speculative Decoding：加速 2x
└── 专业微调：专门针对教育优化

结果：
├── 1GB 模型 ≈ 7B 通用模型的教育能力
├── 可以在手机本地运行
└── 完全离线
```

### 3.4 教育能力评测体系

```python
class EducationBenchmark:
    """教育能力评测基准"""

    def evaluate(self, model, dataset):
        """多维度评测教育能力"""

        results = {
            # 1. 知识准确性
            "knowledge_accuracy": self.test_knowledge(model, dataset),

            # 2. 引导有效性
            "guidance_effectiveness": self.test_guidance(model, dataset),

            # 3. 回答质量
            "response_quality": self.test_response_quality(model, dataset),

            # 4. 互动性
            "interactivity": self.test_interactivity(model, dataset),

            # 5. 学生接受度（最重要！）
            "student_acceptance": self.test_student_learning_outcome(model)
        }

        return results

    def test_student_learning_outcome(self, model):
        """
        最重要的指标：学生学习效果

        A/B 测试：
        - A组：用 AI 老师学习
        - B组：用普通教材自学

        比较：
        - 学习效率
        - 知识掌握度
        - 学习兴趣
        - 长期记忆
        """
        # 实施真实的学生实验
        # 这是最终的评价标准
        pass
```

---

## 四、完整技术路线图

### 4.1 三阶段发展

```
阶段一：学习（2026.6-9）
rasbt/LLMs-from-scratch
    ↓
    ch02-ch07 全部学完
    ↓
    能独立实现预训练+微调

阶段二：研发（2026.9-12）
    ↓
    研发 Qwen2.5-1.5B 教育版
    ↓
    1GB 模型可以本地运行

阶段三：优化（2027+）
    ↓
    极致量化 + 蒸馏
    ↓
    1.5B 教育能力 ≈ 7B 通用能力
```

### 4.2 硬件需求

| 阶段 | 硬件 | 成本 | 可完成 |
|------|------|------|--------|
| 学习 | R7-7840HS | 0 | ✅ |
| 预训练（1.5B） | RTX 4060 (8GB) | ¥2500 | ✅ |
| 微调 | RTX 4090 (24GB) | ¥15000 | ✅ |
| 蒸馏 | 云服务器 | ¥500/月 | ✅ |
| 完整训练 | A100 | ¥10万+ | ❌ |

### 4.3 时间投入

```
学习阶段（3个月）
├── 每周六：rasbt 学习（4小时）
├── 晚间：代码实践（2小时/天）
└── 总计：约 300 小时

研发阶段（3个月）
├── 模型微调实验
├── 教育数据生成
└── 评测与优化
```

---

## 五、教育模型 vs 通用模型

### 5.1 能力对比

| 能力 | 通用 GPT-4 | 教育优化 1.5B |
|------|-------------|----------------|
| 数学解题 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 讲解知识点 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 引导思考 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 鼓励学生 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 作业批改 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 因材施教 | ⭐⭐ | ⭐⭐⭐⭐⭐ |

### 5.2 结论

> **在教育场景下，专精的小模型可以用远小于通用大模型的算力成本，获得可用的教学辅助效果**

---

## 六、rasbt 学习实战计划

### 6.1 本周任务（ch02-ch03）

```bash
# 1. 阅读仓库代码
cd <project-root>\learning_llms_from_scratch
notebook ch02/01_main-chapter-code/ch02.ipynb
notebook ch03/01_main-chapter-code/ch03.ipynb

# 2. 对比 LumiLearn 代码
cd <project-root>\lumilearn
# 对比 tokenizer.py 和 ch02
# 对比 model.py 和 ch03

# 3. 实现改进
# 在 framework/tokenizer.py 中补充 BPE 训练功能
```

### 6.2 每月里程碑

| 月份 | 学习内容 | 产出 |
|------|----------|------|
| 6月 | ch02-ch04 | 深入理解架构 |
| 7月 | ch05 预训练 | 尝试小规模预训练 |
| 8月 | ch06 微调 | 开始教育微调实验 |
| 9月 | ch07+附录 | 完成 RLHF/DPO |
| 10月 | 整合优化 | 发布教育模型 v0.1 |

---

## 七、总结

### 7.1 核心理念

```
❌ 追赶 DeepSeek（不可能）

✅ 成为教育领域可用的轻量模型
   - 不是最大，但追求场景专精
   - 不是最贵，主打低成本惠民
   - 不是最通用，但更贴近教学场景
```

### 7.2 行动路线

```
rasbt 学习
    ↓
掌握大模型核心原理
    ↓
使用教育数据微调
    ↓
蒸馏到小模型
    ↓
极致量化优化
    ↓
让每个设备都能运行强大的 AI 教育
```

### 7.3 最终愿景

> **不是让落后地区追赶上发达地区，而是让每个孩子都能获得最优质的教育资源**

---

## 参考资料

- rasbt/LLMs-from-scratch: https://github.com/rasbt/LLMs-from-scratch
- 知识蒸馏: DistilBERT, TinyBERT
- 教育 AI: Koji, Khanmigo
- LumiLearn: <project-root>\lumilearn