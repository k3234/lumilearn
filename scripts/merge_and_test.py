#!/usr/bin/env python3
"""
LumiLearn 合并 + 推理测试脚本

训练完成后，将 LoRA adapter 合并回基础模型（merge_and_unload），
保存完整模型，并跑 5 道题验证回复质量。

对应 development_summary.md 阶段 7：合并与推理验证。

用法（在服务器上）:
    cd <PROJECT_DIR>
    OMP_NUM_THREADS=4 python3 -u scripts/merge_and_test.py \
        --base <BASE_MODEL_PATH> \
        --adapter models/distil/adapter \
        --output models/distil/merged_model \
        --questions data/distil/test_questions.json

配置项:
    --base        基础模型路径
    --adapter     训练好的 LoRA adapter 目录
    --output      合并后的完整模型输出目录
    --questions   测试题 JSON 文件（可选，默认内置 5 题）
    --max-new-tokens  生成最大 token 数
"""
import os
import sys
import json
import time
import argparse

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import torch

torch.set_num_threads(4)
torch.set_num_interop_threads(4)

DEFAULT_QUESTIONS = [
    "用费曼五步法讲解勾股定理",
    "什么是牛顿第二定律？请举例说明",
    "解释一下化学键中的共价键",
    "什么是函数？用生活中的例子说明",
    "光合作用的过程是怎样的？",
]

SYSTEM_PROMPT = "你是一位资深的AI教师，擅长用费曼五步法讲解各学科知识。请用通俗易懂的语言回答。"


def log(msg: str) -> None:
    print(msg, flush=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LumiLearn LoRA 合并 + 推理测试")
    p.add_argument("--base", required=True, help="基础模型路径")
    p.add_argument("--adapter", default="models/distil/adapter", help="adapter 目录")
    p.add_argument("--output", default="models/distil/merged_model", help="合并输出目录")
    p.add_argument("--questions", default=None, help="测试题 JSON 文件（可选）")
    p.add_argument("--max-new-tokens", type=int, default=256)
    return p.parse_args()


def load_questions(path: str | None) -> list[str]:
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else [q.get("question", str(q)) for q in data]
    return DEFAULT_QUESTIONS


def main() -> None:
    args = parse_args()

    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    log(f"[内存] 加载基础模型: {args.base}")
    base = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=torch.float16, device_map=None,
        trust_remote_code=True, attn_implementation="sdpa",
    )
    tokenizer = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    log(f"[内存] 加载 adapter: {args.adapter}")
    model = PeftModel.from_pretrained(base, args.adapter)

    log("合并 LoRA adapter -> 完整模型 (merge_and_unload)")
    model = model.merge_and_unload()
    model = model.to("cpu")
    model.eval()

    os.makedirs(args.output, exist_ok=True)
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    log(f"完整模型已保存: {args.output}")

    # 推理测试
    questions = load_questions(args.questions)
    log(f"\n开始推理测试: {len(questions)} 题 (max_new_tokens={args.max_new_tokens})")

    results = []
    for i, q in enumerate(questions, 1):
        prompt = (f"<|im_start|>system\n{SYSTEM_PROMPT}\n<|im_end|>\n"
                  f"<|im_start|>user\n{q}\n<|im_end|>\n<|im_start|>assistant\n")
        inputs = tokenizer(prompt, return_tensors="pt")
        t0 = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        elapsed = time.time() - t0
        full = tokenizer.decode(outputs[0], skip_special_tokens=True)
        reply = full.split("<|im_start|>assistant\n")[-1].strip()
        tokens = outputs.shape[1] - inputs["input_ids"].shape[1]
        rate = tokens / max(elapsed, 0.01)
        results.append({"question": q, "reply": reply, "tokens": tokens,
                        "time_s": round(elapsed, 1), "tok_per_s": round(rate, 2)})
        log(f"\n[{i}/{len(questions)}] {q}")
        log(f"  生成 {tokens} tokens, {elapsed:.1f}s ({rate:.2f} tok/s)")
        log(f"  回复: {reply[:120]}...")

    # 保存测试结果
    out_json = os.path.join(args.output, "inference_test.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"\n推理测试完成，结果已保存: {out_json}")


if __name__ == "__main__":
    main()