#!/usr/bin/env python3
"""
LumiLearn 真实数据训练脚本（CPU / QLoRA）

在服务器（<SERVER_IP>，14GB RAM，无 GPU）上用真实费曼教学数据训练 LoRA adapter。
对应 docs/development_summary.md 中的训练管线，是 train_lumilearn.sh 之外
面向"真实数据微调 Qwen2.5-3B"的独立入口。

用法（在服务器上）:
    cd <PROJECT_DIR>
    OMP_NUM_THREADS=4 python3 -u scripts/train_real.py \
        --data data/distil/train_data_real.jsonl \
        --adapter models/distil/adapter \
        --max-length 128 --epochs 1

配置项:
    --base        基础模型路径/名称（默认 www.modelscope.cn 缓存路径）
    --data        JSONL 训练数据（每行 {instruction, response}）
    --adapter     LoRA adapter 输出目录
    --max-length  序列最大长度（128 对应 development_summary 的实测配置）
    --epochs      训练轮数
    --lr          学习率
    --threads     PyTorch CPU 线程数（建议 4，避免争用）
"""
import os
import sys
import json
import time
import argparse

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import torch
import torch.cuda

torch.set_num_threads(4)
torch.set_num_interop_threads(4)

DEFAULT_BASE = "<BASE_MODEL_PATH>"
SYSTEM_PROMPT = "你是一位专业的AI教师，请根据用户的提问给出详细、准确、易懂的回答。"


def log(msg: str) -> None:
    print(msg, flush=True)


def mem_gb() -> float:
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1e9
    except Exception:
        return 0.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LumiLearn 真实数据 LoRA 训练")
    p.add_argument("--base", default=DEFAULT_BASE, help="基础模型路径/名称")
    p.add_argument("--data", required=True, help="JSONL 训练数据路径")
    p.add_argument("--adapter", default="models/distil/adapter", help="adapter 输出目录")
    p.add_argument("--max-length", type=int, default=128)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--threads", type=int, default=4)
    return p.parse_args()


def load_data(data_file: str) -> list[str]:
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"训练数据不存在: {data_file}")
    with open(data_file, "r", encoding="utf-8") as f:
        raw = [json.loads(line) for line in f if line.strip()]
    texts = []
    for d in raw:
        instruction = d.get("instruction", d.get("input", ""))
        response = d.get("response", d.get("output", ""))
        texts.append(
            f"<|im_start|>system\n{SYSTEM_PROMPT}\n<|im_end|>\n"
            f"<|im_start|>user\n{instruction}\n<|im_end|>\n"
            f"<|im_start|>assistant\n{response}\n<|im_end|>"
        )
    return texts


def main() -> None:
    args = parse_args()
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(min(args.threads, 4))

    log(f"[内存] {mem_gb():.2f}GB 开始")

    # 加载模型与分词器
    from transformers import AutoModelForCausalLM, AutoTokenizer
    model = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=torch.float16, device_map=None,
        trust_remote_code=True, attn_implementation="sdpa",
    )
    tokenizer = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    log(f"[内存] {mem_gb():.2f}GB 模型加载完成")

    # LoRA 配置（r=16, alpha=32, 7 个 target modules，与 development_summary 一致）
    from peft import LoraConfig, get_peft_model
    lora_config = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )
    peft_model = get_peft_model(model, lora_config)
    log(f"[内存] {mem_gb():.2f}GB LoRA 完成")

    # 数据准备
    texts = load_data(args.data)
    tokenized = []
    for text in texts:
        t = tokenizer(text, truncation=True, max_length=args.max_length,
                      return_tensors="pt")
        t["labels"] = t["input_ids"].clone()
        tokenized.append(t)
    log(f"[内存] {mem_gb():.2f}GB 数据 {len(texts)} 条, max_length={args.max_length}")

    # 训练
    from torch.optim import AdamW
    from torch.optim.lr_scheduler import CosineAnnealingLR

    peft_model.train()
    peft_model = peft_model.to("cpu")
    trainable = [p for p in peft_model.parameters() if p.requires_grad]
    optimizer = AdamW(trainable, lr=args.lr, weight_decay=0.01)
    total_steps = len(tokenized) * args.epochs
    scheduler = CosineAnnealingLR(optimizer, T_max=total_steps)

    log(f"开始训练: {len(tokenized)} 条 x {args.epochs} epochs = {total_steps} batches")
    start = time.time()
    total_loss = 0.0
    step = 0

    for epoch in range(args.epochs):
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
            log(f"Epoch {epoch + 1}/{args.epochs} Batch {i + 1}/{len(tokenized)} | "
                f"loss={loss.item():.4f} | avg={total_loss / step:.4f} | "
                f"{dt:.0f}s | total={elapsed:.0f}s | mem={mem_gb():.2f}GB")

    duration = time.time() - start
    log(f"训练完成! 总时间 {duration / 60:.1f}min avg_loss={total_loss / step:.4f}")

    # 保存 LoRA adapter
    os.makedirs(args.adapter, exist_ok=True)
    peft_model.save_pretrained(args.adapter)
    tokenizer.save_pretrained(args.adapter)
    log(f"adapter 已保存到 {args.adapter}")


if __name__ == "__main__":
    main()