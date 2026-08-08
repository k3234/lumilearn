#!/usr/bin/env python3
"""
天虹 GPU 版 LoRA 综合数据训练脚本
使用 703 条综合数据训练 Qwen2.5-3B LoRA adapter
用法: HSA_OVERRIDE_GFX_VERSION=11.0.0 python3 -u scripts/train_lora_gpu.py
"""
import sys, os, json, time
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
# 强制纯 CPU：避免 AMD 核显 ROCm 初始化导致崩溃
os.environ["HIP_VISIBLE_DEVICES"] = "-1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
import torch

def log(msg):
    print(msg, flush=True)

def mem():
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1e9
    except Exception:
        return 0.0

BASE_MODEL = "/home/kai/.cache/modelscope/models/Qwen/Qwen2.5-1.5B-Instruct"
DATA_FILE = "data/distil/train_data_high_quality.jsonl"
ADAPTER_PATH = "models/distil/adapter_merged_v2"
MAX_LENGTH = 192
USE_GPU = False  # AMD 核显 ROCm 不稳定，强制 CPU 训练（实测 7.5s/batch）

log(f"mem={mem():.2f}GB start")

# 设备选择
if USE_GPU and torch.cuda.is_available():
    device = "cuda"
    log(f"使用 GPU: {torch.cuda.get_device_name(0)}")
else:
    device = "cpu"
    torch.set_num_threads(16)
    log("使用 CPU (16线程)")
from transformers import AutoModelForCausalLM, AutoTokenizer
t0 = time.time()
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL, torch_dtype=torch.bfloat16, device_map=None,
    trust_remote_code=True, attn_implementation="eager",
)
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
log(f"mem={mem():.2f}GB model loaded ({time.time()-t0:.0f}s)")

from peft import LoraConfig, get_peft_model
lora_config = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
)
peft_model = get_peft_model(model, lora_config)
log(f"mem={mem():.2f}GB LoRA done")

# 加载 703 条综合数据
with open(DATA_FILE, "r", encoding="utf-8") as f:
    raw = [json.loads(l) for l in f if l.strip()]
log(f"加载数据: {len(raw)} 条")

SYSTEM = "你是一位专业的AI教师，请根据用户的提问给出详细、准确、易懂的回答。"
texts = []
for d in raw:
    t = (f"<|im_start|>system\n{SYSTEM}\n<|im_end|>\n"
         f"<|im_start|>user\n{d['instruction']}\n<|im_end|>\n"
         f"<|im_start|>assistant\n{d['response']}\n<|im_end|>")
    texts.append(t)

# Tokenize 全部数据
tokenized = []
for text in texts:
    t = tokenizer(text, truncation=True, max_length=MAX_LENGTH, return_tensors="pt")
    t["labels"] = t["input_ids"].clone()
    tokenized.append(t)
log(f"mem={mem():.2f}GB data tokenized: {len(tokenized)} items")

# 组装 DataLoader（batch_size=1 节省显存，梯度累积）
from torch.utils.data import DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

def collate_fn(batch):
    """自定义 collate：tokenizer 返回 [1, seq]，这里合并为 [B, seq]"""
    input_ids = torch.cat([b["input_ids"] for b in batch], dim=0)
    attention_mask = torch.cat([b["attention_mask"] for b in batch], dim=0)
    labels = torch.cat([b["labels"] for b in batch], dim=0)
    return {"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels}

BATCH_SIZE = 1
GRAD_ACCUM = 8  # 有效 batch = 8
EPOCHS = 3

loader = DataLoader(tokenized, batch_size=BATCH_SIZE, shuffle=True, collate_fn=collate_fn)
peft_model.train()
peft_model = peft_model.to(device)
trainable = [p for p in peft_model.parameters() if p.requires_grad]
optimizer = AdamW(trainable, lr=2e-4, weight_decay=0.01)
total_steps = len(loader) * EPOCHS
scheduler = CosineAnnealingLR(optimizer, T_max=total_steps)

log(f"train: {len(tokenized)} samples x {EPOCHS} epochs = {total_steps} steps, "
    f"grad_accum={GRAD_ACCUM}, device={device}")

start = time.time()
total_loss = 0.0
step = 0

for epoch in range(EPOCHS):
    log(f"\n--- Epoch {epoch+1}/{EPOCHS} ---")
    accum_loss = 0.0
    for i, batch in enumerate(loader):
        t0 = time.time()
        batch = {k: v.to(device) for k, v in batch.items()}
        outputs = peft_model(**batch)
        loss = outputs.loss / GRAD_ACCUM
        loss.backward()
        accum_loss += loss.item() * GRAD_ACCUM

        if (i + 1) % GRAD_ACCUM == 0:
            torch.nn.utils.clip_grad_norm_(trainable, max_norm=1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            step += 1
            avg = accum_loss / GRAD_ACCUM
            total_loss += avg
            dt = time.time() - t0
            elapsed = time.time() - start
            lr = optimizer.param_groups[0]["lr"]
            log(f"E{epoch+1} S{step}/{total_steps} | loss={avg:.4f} | "
                f"avg={total_loss/step:.4f} | lr={lr:.2e} | "
                f"{dt:.1f}s/step | {elapsed:.0f}s | mem={mem():.2f}GB")
            accum_loss = 0.0

dur = time.time() - start
log(f"\nDONE! time={dur:.0f}s ({dur/60:.1f}min) avg_loss={total_loss/max(step,1):.4f}")

os.makedirs(ADAPTER_PATH, exist_ok=True)
peft_model.save_pretrained(ADAPTER_PATH)
tokenizer.save_pretrained(ADAPTER_PATH)
log(f"adapter 已保存: {ADAPTER_PATH}")
