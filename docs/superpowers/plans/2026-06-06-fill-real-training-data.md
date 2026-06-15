# 填充真实训练数据 & 完整训练 Implementation Plan

> **For agentic workers:** 按任务顺序执行，每步完成后再进行下一步。使用 checkbox (`- [ ]`) 追踪进度。

**Goal:** 将 train_data.jsonl 中 12 条 DRY RUN 占位符替换为 Qwen2.5-3B 生成的真实教学回复，然后用真实数据重新训练 LoRA adapter。

**Architecture:** 三步走：生成真实回复 → 更新训练数据 → 重新训练。使用服务器上的 Qwen2.5-3B 模型生成回复（self-distillation 模式），用 `simple_train.py` 定制训练循环在 CPU 上完成训练。

**Tech Stack:** Python 3.10, transformers + peft, PyTorch (CPU), Qwen2.5-3B-Instruct, paramiko (远程部署)

**当前状态:**
- 训练数据: `data/distil/train_data.jsonl`，12 条，全部为 DRY RUN 占位符
- 合并模型: `models/distil/merged_model/`（5.8GB，5-batch 训练的产物）
- Adapter: `models/distil/adapter/`（115MB，旧版）
- 服务器: 192.168.2.xx，14GB RAM，无 GPU

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `data/distil/train_data.jsonl` | 修改 | 训练数据，替换 DRY RUN 为真实回复 |
| `scripts/generate_responses.py` | 新建 | 用 Qwen2.5-3B 为每条 instruction 生成回复 |
| `scripts/simple_train.py` | 新建 | 简化训练循环（替代 trainer.py 的复杂流程） |
| `models/distil/adapter/` | 覆盖 | 重新训练后的 LoRA adapter |
| `models/distil/merged_model/` | 覆盖 | 重新合并后的完整模型 |

---

## Task 1: 生成真实教学回复

**Files:**
- Create: `scripts/generate_responses.py`

**说明:** 在服务器上用 Qwen2.5-3B 为 12 条 instruction 生成真实回复。每条回复约 300-800 字，使用费曼五步法格式。生成结果保存为 `data/distil/train_data_real.jsonl`（保留原始文件备份）。

- [ ] **Step 1: 创建生成脚本**

```python
# scripts/generate_responses.py
"""
用 Qwen2.5-3B 为训练数据中的 instruction 生成真实回复
输出: data/distil/train_data_real.jsonl
"""
import os, sys, json, time
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import torch
torch.set_num_threads(4)
torch.set_num_interop_threads(4)

BASE_MODEL = "~/.cache/modelscope/qwen/Qwen2___5-3B-Instruct"
INPUT_FILE = "data/distil/train_data.jsonl"
OUTPUT_FILE = "data/distil/train_data_real.jsonl"

SYSTEM_PROMPT = """你是一位资深AI教师，擅长用费曼五步法讲解各学科知识。

【费曼五步法格式】
1. 【描述】用简单的话描述这个概念是什么
2. 【类比】用一个生活场景或熟悉的事物来类比
3. 【定义】给出清晰准确的定义
4. 【例证】举一个具体的例子帮助理解
5. 【归纳总结】用一句话总结核心要点

【质量要求】
- 回复总字数300-800字
- 语言通俗易懂，避免学术黑话
- 公式用 LaTeX 语法: $E=mc^2$
- 每个步骤必须有实质内容，不能只有标题
- 例证必须具体，不能泛泛而谈"""

def log(msg):
    print(msg, flush=True)

def make_prompt(instruction):
    return f"<|im_start|>system\n{SYSTEM_PROMPT}\n<|im_end|>\n<|im_start|>user\n{instruction}\n<|im_end|>\n<|im_start|>assistant\n"

# 加载模型
log("加载模型...")
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL, torch_dtype=torch.float16, device_map=None,
    trust_remote_code=True, attn_implementation="sdpa"
)
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
log("模型加载完成")

# 加载训练数据
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = [json.loads(l) for l in f.readlines()]
log(f"加载 {len(data)} 条训练数据")

# 生成回复
results = []
for i, item in enumerate(data):
    instruction = item["instruction"]
    log(f"\n[{i+1}/{len(data)}] {instruction[:60]}...")

    prompt = make_prompt(instruction)
    inputs = tokenizer(prompt, return_tensors="pt")

    t0 = time.time()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    elapsed = time.time() - t0

    full = tokenizer.decode(outputs[0], skip_special_tokens=True)
    reply = full.split("<|im_start|>assistant\n")[-1].split("<|im_end|>")[0].strip()
    tokens = outputs.shape[1] - inputs["input_ids"].shape[1]

    log(f"  生成: {tokens} tokens, {elapsed:.0f}s, 回复: {len(reply)}字")

    results.append({
        "instruction": instruction,
        "response": reply,
        "input_tokens": inputs["input_ids"].shape[1],
        "output_tokens": tokens,
        "generation_time": elapsed,
    })

    # 增量保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

log(f"\n完成! 生成 {len(results)} 条回复，保存到 {OUTPUT_FILE}")
```

- [ ] **Step 2: 部署到服务器并运行**

将 `scripts/generate_responses.py` 通过 SFTP 上传到 `~/lumilearn/scripts/generate_responses.py`，然后运行：

```bash
cd ~/lumilearn
mkdir -p scripts
OMP_NUM_THREADS=4 python3 -u scripts/generate_responses.py
```

- [ ] **Step 3: 验证生成结果**

```bash
# 检查生成的数据
python3 -c "
import json
with open('data/distil/train_data_real.jsonl') as f:
    data = [json.loads(l) for l in f]
print(f'总数: {len(data)}')
for d in data:
    print(f'指令: {d[\"instruction\"][:60]}')
    print(f'回复: {d[\"response\"][:80]}...')
    print(f'回复长度: {len(d[\"response\"])}字')
    print()
"
```

预期: 12 条数据，每条回复 300-800 字，包含费曼五步法结构。

---

## Task 2: 更新训练数据并重新训练

**Files:**
- Create: `scripts/simple_train.py`
- Modify: `data/distil/train_data.jsonl` → 替换为真实数据

**说明:** 将真实数据替换原始 DRY RUN 数据，然后用 12 条数据重新训练 3 epochs（共 36 batches）。

- [ ] **Step 1: 创建简化训练脚本**

```python
# scripts/simple_train.py
"""简化训练脚本：加载真实数据，训练 LoRA adapter"""
import sys, os, json, time
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import torch
torch.set_num_threads(4)
torch.set_num_interop_threads(4)

BASE_MODEL = "~/.cache/modelscope/qwen/Qwen2___5-3B-Instruct"
DATA_FILE = "data/distil/train_data_real.jsonl"
ADAPTER_PATH = "models/distil/adapter"
MAX_LENGTH = 256
EPOCHS = 3

def log(msg):
    print(msg, flush=True)
def _mem():
    import psutil; return psutil.Process().memory_info().rss / 1e9

log(f"内存: {_mem():.2f}GB 开始")

# 加载模型
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL, torch_dtype=torch.float16, device_map=None,
    trust_remote_code=True, attn_implementation="sdpa"
)
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
log(f"内存: {_mem():.2f}GB 模型加载完成")

# LoRA
from peft import LoraConfig, get_peft_model
lora_config = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"]
)
peft_model = get_peft_model(model, lora_config)
log(f"内存: {_mem():.2f}GB LoRA完成")

# 加载数据
with open(DATA_FILE, "r", encoding="utf-8") as f:
    raw_data = [json.loads(l) for l in f.readlines()]

SYSTEM_PROMPT = "你是一位专业的AI教师，请根据用户的提问给出详细、准确、易懂的回答。"
data = []
for d in raw_data:
    text = f"<|im_start|>system\n{SYSTEM_PROMPT}\n<|im_end|>\n<|im_start|>user\n{d['instruction']}\n<|im_end|>\n<|im_start|>assistant\n{d['response']}\n<|im_end|>"
    data.append(text)

tokenized = []
for text in data:
    t = tokenizer(text, truncation=True, max_length=MAX_LENGTH, return_tensors="pt")
    t["labels"] = t["input_ids"].clone()
    tokenized.append(t)
log(f"内存: {_mem():.2f}GB 数据: {len(data)}条, max_length={MAX_LENGTH}")

# 训练
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

peft_model.train()
peft_model = peft_model.to("cpu")
trainable = [p for p in peft_model.parameters() if p.requires_grad]
optimizer = AdamW(trainable, lr=2e-4, weight_decay=0.01)
total_steps = len(tokenized) * EPOCHS
scheduler = CosineAnnealingLR(optimizer, T_max=total_steps)

log(f"开始训练: {len(tokenized)}条 x {EPOCHS} epochs = {total_steps} batches")
start = time.time()
total_loss = 0.0
step = 0

for epoch in range(EPOCHS):
    for i, batch in enumerate(tokenized):
        t0 = time.time()
        batch = {k: v.to("cpu") for k, v in batch.items()}
        outputs = peft_model(**batch)
        loss = outputs.loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(trainable, max_norm=1.0)
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad()
        total_loss += loss.item()
        step += 1
        dt = time.time() - t0
        elapsed = time.time() - start
        log(f"Epoch {epoch+1}/{EPOCHS} Batch {i+1}/{len(tokenized)} | "
            f"loss={loss.item():.4f} | avg={total_loss/step:.4f} | "
            f"{dt:.0f}s | total={elapsed:.0f}s | mem={_mem():.2f}GB")

duration = time.time() - start
log(f"训练完成! 总时间: {duration:.0f}s ({duration/60:.1f}min) avg_loss={total_loss/step:.4f}")

# 保存
import os as _os
_os.makedirs(ADAPTER_PATH, exist_ok=True)
peft_model.save_pretrained(ADAPTER_PATH)
tokenizer.save_pretrained(ADAPTER_PATH)
log(f"模型已保存到 {ADAPTER_PATH}")
```

- [ ] **Step 2: 部署到服务器并运行**

SFTP 上传 `scripts/simple_train.py` 到服务器，然后运行：

```bash
cd ~/lumilearn
OMP_NUM_THREADS=4 python3 -u scripts/simple_train.py >> /tmp/train_real.log 2>&1
```

预计时间: 12条 x 3 epochs x ~21min/batch = **~12.6 小时**（256 tokens）

- [ ] **Step 3: 验证训练结果**

训练完成后检查 loss 曲线是否下降，adapter 是否保存成功。

---

## Task 3: 合并并测试最终模型

**Files:**
- 复用: `merge_and_test.py`（已存在）

**说明:** 训练完成后，使用已有的 `merge_and_test.py` 合并并测试。

- [ ] **Step 1: 运行合并测试**

```bash
cd ~/lumilearn
OMP_NUM_THREADS=4 python3 -u merge_and_test.py
```

- [ ] **Step 2: 对比结果**

对比新模型与旧模型（5-batch DRY RUN）的推理效果，确认训练数据替换后质量提升。

---

## 时间估算

| 阶段 | 任务 | 预计时间 |
|------|------|----------|
| Task 1 | 生成 12 条回复 | ~1.5 小时 |
| Task 2 | 训练 12x3=36 batches | ~12.6 小时 |
| Task 3 | 合并测试 | ~1 小时 |
| **总计** | | **~15 小时** |

## 风险与注意事项

1. **Self-distillation 局限**: 用 3B 模型生成数据再训练 3B 模型，效果提升有限。最佳方案是未来用 7B 模型生成数据。
2. **内存风险**: 生成回复时 max_new_tokens=512，加上输入长度，需确保不超 14GB 内存。
3. **训练时间**: 12.6 小时较长，建议设置 `nohup` 后台运行，次日检查结果。
4. **数据质量**: 生成的回复质量取决于 3B 模型的能力，建议人工抽查 2-3 条。