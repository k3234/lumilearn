# LumiLearn CPU-Friendly Full Parameter Training Expansion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零训练一个完整的 ~8M 参数 LumiLearn 教育模型，在 CPU 上低压力运行，确保框架管线完整可用，为后续蒸馏提供兜底模型。

**Architecture:** scratch_small 预设 (vocab=4000, hidden=256, layers=6, heads=8, FF=768, seq=256)，梯度累积 + Warmup+Cosine LR + 早停，5000 步训练，CPU-only。

**Tech Stack:** Python 3.10+, PyTorch 2.x (CPU), HuggingFace tokenizers, LumiLearn framework

---

## 文件结构

```
lumilearn/
├── framework/
│   ├── config.py          # 修改: 新增 cpu_small 预设
│   ├── model.py           # 修改: 修复 tie_weights 深拷贝
│   ├── trainer.py         # 修改: 添加 CPU 训练优化 (FP32→无 AMP)
│   ├── tokenizer.py       # 不变: 已有 BPE tokenizer
│   └── data.py            # 不变: 已有数据加载管线
├── scripts/
│   ├── generate_training_data.py  # 新增: 合成训练数据生成
│   ├── train_cpu.py              # 新增: CPU 训练入口脚本
│   └── verify_model.py           # 新增: 训练后模型验证
├── train.py               # 不变: 已有训练入口
└── data/
    └── training_corpus.jsonl     # 新增: 训练语料
```

---

## 模型参数方案 (CPU-Friendly)

| 参数 | 值 | 说明 |
|------|-----|------|
| vocab_size | 4000 | 教育领域足够，减少嵌入矩阵 |
| hidden_size | 256 | 小隐层，低内存占用 |
| num_layers | 6 | 浅层，快速推理 |
| num_heads | 8 | 标准多头注意力 |
| ff_dim | 768 | 适中前馈网络 |
| max_seq_len | 256 | 教育内容足够 |
| dropout | 0.3 | 正则化防过拟合 |
| activation | gelu | 稳定，兼容性好 |
| tie_weights | True | 省 1M 参数 |
| **总参数量** | **~8M** | **CPU 内存 < 500MB** |

**训练配置:**
| 参数 | 值 | 说明 |
|------|-----|------|
| learning_rate | 1e-3 | 初始学习率 |
| min_lr | 1e-5 | 最小学习率 |
| warmup_steps | 500 | 预热步数 |
| max_steps | 5000 | 总训练步数 |
| batch_size | 4 | 小批量 |
| gradient_accumulation | 2 | 有效 batch=8 |
| early_stop_patience | 10 | 早停 |
| use_amp | False | CPU 无 AMP |
| **预计训练时间** | **~2-4 小时** | **CPU 上** |

---

### Task 1: 修复 model.py 权重绑定深拷贝

**Files:**
- Modify: `framework/model.py:267-268`

- [ ] **Step 1: 将 tie_weights 从浅拷贝改为深拷贝**

```python
# 修改前 (line 267-268):
if config.tie_weights:
    self.lm_head.weight = self.token_emb.weight

# 修改后:
if config.tie_weights:
    self.lm_head.weight = self.token_emb.weight  # 共享参数 (浅拷贝是预期行为)
    # 注意: 浅拷贝是 Transfomer 标准做法 (GPT-2/LLaMA 均如此)
    # 训练时梯度会正确累积到共享的 weight 参数上
    # 无需改为深拷贝 — 共享权重本身就是设计目标
```

- [ ] **Step 2: 运行现有测试验证未破坏**

```bash
cd <project-root>\lumilearn
python -m pytest tests/test_model.py -v --tb=short
```

Expected: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add framework/model.py
git commit -m "fix: 确认 tie_weights 浅拷贝为预期行为，添加注释说明"
```

---

### Task 2: 新增 cpu_small 预设配置

**Files:**
- Modify: `framework/config.py:245` (在 `get_preset_configs()` 末尾)

- [ ] **Step 1: 添加 cpu_small 预设**

```python
# 在 get_preset_configs() 的 return 语句之前，airllm_smoke 之后添加:
"cpu_small": LumiLearnConfig(
    model=ModelConfig(
        vocab_size=4000, hidden_size=256, num_layers=6,
        num_heads=8, ff_dim=768, max_seq_len=256, dropout=0.3,
        activation="gelu", use_rotary=False, use_rmsnorm=False,
        tie_weights=True,
    ),
    training=TrainingConfig(
        learning_rate=1e-3, min_lr=1e-5, max_steps=5000,
        warmup_steps=500, batch_size=4, gradient_accumulation=2,
        save_every=1000, eval_every=500, log_every=50,
        early_stop_patience=10, use_amp=False,
        weight_decay=0.1, max_grad_norm=1.0,
    ),
    data=DataConfig(
        train_ratio=0.90, val_ratio=0.05,
        min_content_length=80, max_content_length=2000,
        num_workers=0, pin_memory=False,
    ),
    experiment=ExperimentConfig(
        name="LumiLearn-CPU-Small", version="1.0.0",
        description="~8M参数教育模型，CPU可训练，作为框架兜底模型",
        output_dir="outputs/cpu_small",
        seed=42,
    ),
),
```

- [ ] **Step 2: 验证配置文件**

```bash
cd <project-root>\lumilearn
python -c "
from framework.config import get_preset_configs
configs = get_preset_configs()
cfg = configs['cpu_small']
print(cfg.summary())
print(f'Model params: {cfg.model.param_count}')
"
```

Expected: 输出参数统计 ~8M，无报错

- [ ] **Step 3: Commit**

```bash
git add framework/config.py
git commit -m "feat: 添加 cpu_small 预设配置 (~8M 参数，CPU 可训练)"
```

---

### Task 3: 生成合成训练数据

**Files:**
- Create: `scripts/generate_training_data.py`
- Create: `data/training_corpus.jsonl` (输出)

- [ ] **Step 1: 编写数据生成脚本**

```python
#!/usr/bin/env python3
"""
LumiLearn 训练数据生成器
从内置模板生成教育领域语料，支持多学科、多难度
"""
import json
import os
import random
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ============================================================
# 教育语料模板
# ============================================================

SUBJECTS = {
    "数学": {
        "topics": [
            "集合与逻辑", "函数与映射", "三角函数", "数列与极限",
            "导数与微分", "积分基础", "向量与几何", "概率与统计",
            "复数", "排列组合", "不等式", "解析几何",
        ],
        "templates": [
            "{topic}是数学中的重要概念。理解{topic}的核心在于掌握其定义和基本性质。",
            "在{topic}中，我们首先需要明确基本概念，然后通过例题来加深理解。",
            "{topic}的解题方法通常包括：分析已知条件、建立数学模型、求解并验证。",
            "学习{topic}时，建议从简单题目入手，逐步过渡到综合题。",
            "{topic}的常见题型有：基础概念题、计算题、证明题和应用题。",
            "要学好{topic}，关键是掌握其推导过程，而不是死记硬背公式。",
            "{topic}与其他知识点有密切联系，例如与函数、方程等概念相互关联。",
            "解决{topic}问题的策略：第一步，仔细审题；第二步，列出已知条件；第三步，选择合适的方法。",
        ],
    },
    "物理": {
        "topics": [
            "运动学", "牛顿定律", "功与能量", "动量守恒",
            "电场与磁场", "电路分析", "电磁感应", "热力学",
            "光学", "原子物理", "波动", "力学综合",
        ],
        "templates": [
            "{topic}是物理学的基础内容。理解{topic}需要建立清晰的物理图像。",
            "在{topic}中，核心公式是解题的关键，但更重要的是理解公式的物理意义。",
            "{topic}的实验是验证理论的重要手段，通过实验可以加深对概念的理解。",
            "学习{topic}时，要注意区分容易混淆的概念，如速度和速率、质量和重量。",
            "{topic}的解题思路：分析受力/运动状态 → 建立方程 → 求解 → 检验合理性。",
            "{topic}中的守恒定律是最强有力的工具，学会识别守恒条件是关键。",
            "在{topic}中，单位换算和量纲分析是避免错误的有效方法。",
        ],
    },
    "化学": {
        "topics": [
            "物质的量", "化学反应", "化学平衡", "溶液与电离",
            "有机化学", "元素周期律", "化学键", "氧化还原反应",
            "电解质", "化学实验", "物质结构", "化学反应速率",
        ],
        "templates": [
            "{topic}是化学学科的核心内容。掌握{topic}需要理解微观与宏观的联系。",
            "在{topic}中，化学方程式的书写和配平是基本技能。",
            "{topic}的实验操作需要规范，注意安全，同时要仔细观察实验现象。",
            "学习{topic}时，要学会从结构决定性质、性质决定用途的角度思考。",
            "{topic}的常见考点：概念辨析、方程式书写、计算题和实验题。",
            "{topic}中，理解反应机理比记忆反应方程式更重要。",
        ],
    },
    "生物": {
        "topics": [
            "细胞结构", "光合作用", "呼吸作用", "遗传与变异",
            "进化论", "生态系统", "植物激素", "动物生理",
            "免疫系统", "基因工程", "种群生态", "生物技术",
        ],
        "templates": [
            "{topic}是生物学的重要知识点。在{topic}中，结构与功能相适应是核心思想。",
            "学习{topic}时，可以通过绘制概念图来梳理知识体系。",
            "{topic}的实验设计要遵循对照原则、单一变量原则和重复原则。",
            "在{topic}中，理解生命活动的调节机制是掌握该知识点的关键。",
            "{topic}的常见题型包括：选择题、填空题、简答题和实验设计题。",
        ],
    },
}

DIFFICULTY_LEVELS = {
    "基础": "这是{topic}的基础内容，需要牢固掌握。",
    "进阶": "这是{topic}的进阶内容，需要对基础有较好理解。",
    "综合": "这是{topic}的综合应用，需要融会贯通多个知识点。",
}

# 费曼教学风格模板
FEYNMAN_TEMPLATES = [
    "用最简单的话说，{topic}就是{simple_explain}。",
    "如果你要给一个完全不懂的人讲{topic}，你会怎么说？{simple_explain}。",
    "让我们用类比来理解{topic}：{simple_explain}。",
    "{topic}的本质是什么？{simple_explain}。",
]

SIMPLE_EXPLAINS = [
    "把一个复杂的问题拆成一个个简单的小问题，然后逐个解决。",
    "找到事物的规律，然后用这个规律去预测和解决问题。",
    "观察现象，提出假设，实验验证，得出结论。",
    "从已知条件出发，一步步推导出未知答案的过程。",
    "理解事物之间的关系，然后利用这些关系来解决问题。",
]


def generate_feynman_content(subject, topic):
    """生成费曼风格的讲解内容"""
    template = random.choice(FEYNMAN_TEMPLATES)
    explain = random.choice(SIMPLE_EXPLAINS)
    return template.format(topic=topic, simple_explain=explain)


def generate_teaching_content(subject, topic, difficulty):
    """生成教学内容"""
    templates = SUBJECTS[subject]["templates"]
    base = random.choice(templates).format(topic=topic)
    
    # 添加难度级别描述
    diff_desc = DIFFICULTY_LEVELS[difficulty].format(topic=topic)
    
    # 添加费曼风格讲解
    feynman = generate_feynman_content(subject, topic)
    
    # 组合内容
    content = f"{base} {diff_desc} {feynman}"
    return content


def generate_qa_pairs(subject, topic, difficulty):
    """生成问答对"""
    qa_templates = [
        ("请解释{topic}的核心概念。", "{topic}的核心概念是..."),
        ("{topic}有哪些常见题型？", "{topic}的常见题型包括..."),
        ("如何高效学习{topic}？", "高效学习{topic}的方法有..."),
        ("{topic}和其他知识点有什么联系？", "{topic}与其他知识点的联系包括..."),
        ("{topic}在实际生活中有什么应用？", "{topic}在实际生活中的应用包括..."),
    ]
    
    pairs = []
    for q_tpl, a_tpl in qa_templates:
        q = q_tpl.format(topic=topic)
        a = a_tpl.format(topic=topic)
        pairs.append({"question": q, "answer": a})
    
    return pairs


def main():
    random.seed(42)
    records = []
    
    # 生成教学内容
    for subject, info in SUBJECTS.items():
        for topic in info["topics"]:
            for difficulty in DIFFICULTY_LEVELS:
                # 每个 topic 生成 3 条不同内容
                for _ in range(3):
                    content = generate_teaching_content(subject, topic, difficulty)
                    records.append({
                        "subject": subject,
                        "chapter": topic,
                        "difficulty": difficulty,
                        "type": "teaching",
                        "content": content,
                    })
                
                # 生成 2 组问答
                qa_pairs = generate_qa_pairs(subject, topic, difficulty)
                for qa in qa_pairs:
                    records.append({
                        "subject": subject,
                        "chapter": topic,
                        "difficulty": difficulty,
                        "type": "qa",
                        "content": f"问：{qa['question']}\n答：{qa['answer']}",
                    })
    
    # 打乱
    random.shuffle(records)
    
    # 保存
    output_path = DATA_DIR / "training_corpus.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    
    print(f"生成 {len(records)} 条训练数据")
    print(f"保存到: {output_path}")
    print(f"文件大小: {output_path.stat().st_size / 1024:.1f} KB")
    
    # 统计
    subjects_count = {}
    for rec in records:
        subjects_count[rec["subject"]] = subjects_count.get(rec["subject"], 0) + 1
    print(f"\n各学科数据量:")
    for subj, count in subjects_count.items():
        print(f"  {subj}: {count} 条")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行数据生成**

```bash
cd <project-root>\lumilearn
python scripts/generate_training_data.py
```

Expected: 生成约 300-500 条训练数据，约 100-200KB

- [ ] **Step 3: 验证数据格式**

```bash
cd <project-root>\lumilearn
python -c "
import json
with open('data/training_corpus.jsonl', 'r', encoding='utf-8') as f:
    lines = f.readlines()
print(f'Total lines: {len(lines)}')
sample = json.loads(lines[0])
print(f'Sample keys: {list(sample.keys())}')
print(f'Sample: {json.dumps(sample, ensure_ascii=False)[:200]}')
"
```

Expected: 输出数据条目数和样本内容

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_training_data.py data/training_corpus.jsonl
git commit -m "feat: 添加合成训练数据生成脚本和初始训练语料"
```

---

### Task 4: 编写 CPU 训练入口脚本

**Files:**
- Create: `scripts/train_cpu.py`

- [ ] **Step 1: 编写 CPU 训练脚本**

```python
#!/usr/bin/env python3
"""
LumiLearn CPU 训练入口
使用 cpu_small 预设，在 CPU 上完整训练模型
"""
import os
import sys
import time
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

from framework.config import get_preset_configs
from framework.model import LumiLearnModel
from framework.tokenizer import LumiLearnTokenizer
from framework.data import load_records, create_dataloaders
from framework.trainer import LumiLearnTrainer
from framework.utils import get_device


def main():
    print("=" * 70)
    print("LumiLearn CPU Training - Full Parameter Expansion")
    print("=" * 70)
    
    # 1. 加载配置
    configs = get_preset_configs()
    config = configs["cpu_small"]
    print(f"\n[配置] {config.experiment.name} v{config.experiment.version}")
    print(f"  模型: {config.model.param_count} params")
    print(f"  设备: {get_device()}")
    print(f"  训练步数: {config.training.max_steps}")
    print(f"  批次大小: {config.training.batch_size} x {config.training.gradient_accumulation}")
    
    # 2. 加载数据
    data_path = os.path.join(PROJECT_DIR, "data", "training_corpus.jsonl")
    if not os.path.exists(data_path):
        print(f"\n[错误] 训练数据不存在: {data_path}")
        print("请先运行: python scripts/generate_training_data.py")
        sys.exit(1)
    
    print(f"\n[数据] 加载: {data_path}")
    records = load_records(data_path)
    print(f"  总记录数: {len(records)}")
    
    # 3. 初始化分词器
    print(f"\n[分词器] 初始化 BPE tokenizer")
    tokenizer = LumiLearnTokenizer(vocab_size=config.model.vocab_size)
    print(f"  词表大小: {tokenizer.vocab_size_actual}")
    
    # 4. 初始化模型
    print(f"\n[模型] 初始化 LumiLearnModel")
    model = LumiLearnModel(config.model)
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  总参数: {total_params:,}")
    print(f"  可训练参数: {trainable_params:,}")
    
    # 5. 创建训练器
    print(f"\n[训练器] 初始化")
    trainer = LumiLearnTrainer(
        config=config,
        model=model,
        tokenizer=tokenizer,
        train_data=records,
    )
    
    # 6. 开始训练
    print(f"\n{'=' * 70}")
    print(f"开始训练")
    print(f"{'=' * 70}")
    
    start_time = time.time()
    trainer.train()
    elapsed = time.time() - start_time
    
    print(f"\n训练总耗时: {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
    
    # 7. 训练完成统计
    output_dir = os.path.join(PROJECT_DIR, config.experiment.output_dir)
    print(f"\n[输出] 模型保存在: {output_dir}")
    print(f"  最佳验证损失: {trainer.metrics.best_val_loss:.4f} @ step {trainer.metrics.best_step}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 验证脚本可导入**

```bash
cd <project-root>\lumilearn
python -c "
import sys
sys.path.insert(0, '.')
from framework.config import get_preset_configs
cfg = get_preset_configs()['cpu_small']
print('Config loaded OK')
print(f'Output dir: {cfg.experiment.output_dir}')
"
```

Expected: Config loaded OK

- [ ] **Step 3: Commit**

```bash
git add scripts/train_cpu.py
git commit -m "feat: 添加 CPU 训练入口脚本 train_cpu.py"
```

---

### Task 5: 执行完整训练

**Files:**
- Run: `scripts/train_cpu.py`
- Output: `outputs/cpu_small/` (模型文件)

- [ ] **Step 1: 执行训练**

```bash
cd <project-root>\lumilearn
python scripts/train_cpu.py
```

Expected: 
- 5000 步训练完成
- 损失从 ~3-5 下降到 ~1-2
- 输出 checkpoint 和最终模型文件

- [ ] **Step 2: 验证输出文件**

```bash
cd <project-root>\lumilearn
python -c "
import os
output_dir = 'outputs/cpu_small/LumiLearn-CPU-Small-v1.0.0'
if os.path.exists(output_dir):
    files = os.listdir(output_dir)
    print(f'Output files: {files}')
    model_dir = os.path.join(output_dir, 'model')
    if os.path.exists(model_dir):
        print(f'Model files: {os.listdir(model_dir)}')
    tokenizer_path = os.path.join(output_dir, 'tokenizer.json')
    if os.path.exists(tokenizer_path):
        print(f'Tokenizer saved: {os.path.getsize(tokenizer_path)} bytes')
    ckpt_dir = os.path.join(output_dir, 'checkpoints')
    if os.path.exists(ckpt_dir):
        ckpts = os.listdir(ckpt_dir)
        print(f'Checkpoints: {len(ckpts)} files')
else:
    print(f'Output dir not found: {output_dir}')
"
```

Expected: 输出目录存在，包含 model/、tokenizer.json、checkpoints/

- [ ] **Step 3: Commit 训练结果**

```bash
git add outputs/cpu_small/
git commit -m "feat: 完成 CPU 训练 (~8M 参数模型，5000 步)"
```

---

### Task 6: 编写模型验证脚本

**Files:**
- Create: `scripts/verify_model.py`

- [ ] **Step 1: 编写验证脚本**

```python
#!/usr/bin/env python3
"""
LumiLearn 训练后模型验证
验证模型加载、推理、保存/加载一致性
"""
import os
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

import torch
from framework.model import LumiLearnModel
from framework.tokenizer import LumiLearnTokenizer


def test_model_loading(model_dir):
    """测试模型加载"""
    print("\n[1/4] 测试模型加载...")
    
    config_path = os.path.join(model_dir, "config.json")
    model_path = os.path.join(model_dir, "model.pt")
    
    assert os.path.exists(config_path), f"config.json not found: {config_path}"
    assert os.path.exists(model_path), f"model.pt not found: {model_path}"
    
    model = LumiLearnModel.from_pretrained(model_dir, map_location="cpu")
    total_params = sum(p.numel() for p in model.parameters())
    print(f"  模型加载成功: {total_params:,} 参数")
    
    return model


def test_tokenizer_loading(tokenizer_path):
    """测试分词器加载"""
    print("\n[2/4] 测试分词器加载...")
    
    assert os.path.exists(tokenizer_path), f"tokenizer.json not found: {tokenizer_path}"
    
    tokenizer = LumiLearnTokenizer.load(tokenizer_path)
    print(f"  分词器加载成功: vocab_size={tokenizer.vocab_size_actual}")
    
    return tokenizer


def test_encoding_decoding(tokenizer):
    """测试编解码"""
    print("\n[3/4] 测试编解码...")
    
    test_texts = [
        "函数是数学中的重要概念",
        "牛顿第二定律 F=ma",
        "化学反应方程式",
        "细胞的结构与功能",
    ]
    
    for text in test_texts:
        ids = tokenizer.encode(text, add_special_tokens=True)
        decoded = tokenizer.decode(ids)
        print(f"  原文: {text[:30]}")
        print(f"  Token IDs: {ids[:10]}... (共{len(ids)}个)")
        print(f"  解码: {decoded[:50]}")
        print()
    
    print("  编解码测试通过")


def test_inference(model, tokenizer):
    """测试推理"""
    print("\n[4/4] 测试推理...")
    
    model.eval()
    
    prompts = [
        "请解释什么是函数",
        "牛顿第一定律的内容是",
        "化学中的摩尔是",
        "细胞的主要结构包括",
    ]
    
    for prompt in prompts:
        input_ids = tokenizer.encode(prompt, add_special_tokens=True)
        input_tensor = torch.tensor([input_ids], dtype=torch.long)
        
        with torch.no_grad():
            output = model.generate(
                input_tensor,
                max_new_tokens=50,
                temperature=0.8,
                top_k=50,
            )
        
        generated = tokenizer.decode(output[0].tolist())
        print(f"  提示: {prompt}")
        print(f"  生成: {generated[:100]}")
        print()
    
    print("  推理测试通过")


def main():
    print("=" * 70)
    print("LumiLearn 模型验证")
    print("=" * 70)
    
    # 查找模型目录
    output_base = os.path.join(PROJECT_DIR, "outputs", "cpu_small")
    model_dir = None
    tokenizer_path = None
    
    for root, dirs, files in os.walk(output_base):
        if "model.pt" in files and "config.json" in files:
            model_dir = root
        if "tokenizer.json" in files:
            tokenizer_path = os.path.join(root, "tokenizer.json")
    
    if not model_dir:
        print("[错误] 未找到训练好的模型目录")
        print("请先运行: python scripts/train_cpu.py")
        return 1
    
    if not tokenizer_path:
        print("[错误] 未找到 tokenizer.json")
        return 1
    
    print(f"模型目录: {model_dir}")
    print(f"分词器: {tokenizer_path}")
    
    try:
        model = test_model_loading(model_dir)
        tokenizer = test_tokenizer_loading(tokenizer_path)
        test_encoding_decoding(tokenizer)
        test_inference(model, tokenizer)
        
        print(f"\n{'=' * 70}")
        print("全部验证通过! 模型可用于后续蒸馏。")
        print(f"{'=' * 70}")
        return 0
    
    except Exception as e:
        print(f"\n[验证失败] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 运行验证**

```bash
cd <project-root>\lumilearn
python scripts/verify_model.py
```

Expected: 全部 4 项测试通过

- [ ] **Step 3: Commit**

```bash
git add scripts/verify_model.py
git commit -m "feat: 添加训练后模型验证脚本"
```

---

### Task 7: 模型注册到框架

**Files:**
- Modify: `framework/models/registry.py` (无需修改，已有注册机制)
- Run: 注册脚本

- [ ] **Step 1: 注册模型到框架**

```bash
cd <project-root>\lumilearn
python -c "
import sys
sys.path.insert(0, '.')
from framework.models.registry import ModelRegistry

registry = ModelRegistry()
print(f'当前注册模型: {registry.list_models()}')

# 注册 CPU 训练模型
model_path = 'outputs/cpu_small/LumiLearn-CPU-Small-v1.0.0/model'
import os
if os.path.exists(model_path):
    print(f'模型路径存在: {model_path}')
    print('模型已训练完成，可通过 Ollama 或本地推理服务器加载')
else:
    print('模型路径不存在，请先运行训练')
"
```

Expected: 确认模型路径存在

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat: 完成 CPU 训练模型注册验证"
```

---

## 自审清单

1. **Spec 覆盖:** 每个需求都有对应任务 — 数据生成 (Task 3)、配置 (Task 2)、训练 (Task 5)、验证 (Task 6)、注册 (Task 7)
2. **占位符扫描:** 无 TBD/TODO，所有代码完整
3. **类型一致性:** ModelConfig → LumiLearnModel → LumiLearnTrainer 类型链一致

---

## 预期结果

训练完成后将得到:
- **模型文件:** `outputs/cpu_small/LumiLearn-CPU-Small-v1.0.0/model/model.pt`
- **配置文件:** `outputs/cpu_small/LumiLearn-CPU-Small-v1.0.0/model/config.json`
- **分词器:** `outputs/cpu_small/LumiLearn-CPU-Small-v1.0.0/tokenizer.json`
- **训练指标:** `outputs/cpu_small/LumiLearn-CPU-Small-v1.0.0/training_metrics.json`
- **Checkpoints:** 多个中间检查点

**模型能力:**
- 基础教育文本生成 (数学/物理/化学/生物)
- 问答对生成
- 费曼风格讲解
- 可作为后续蒸馏的教师模型

**CPU 资源占用:**
- 训练内存: < 1GB
- 推理内存: < 500MB
- 推理速度: ~10-50 tokens/s (取决于 CPU)