#!/usr/bin/env python3
"""本地验证合并后的 LumiLearn 1.5B 模型"""
import sys, os, time
sys.path.insert(0, "e:/学习LLM/lumilearn")

MODEL_DIR = "e:/学习LLM/lumilearn/models/distil/merged_model_15b_v2"

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

print("=" * 60)
print("LumiLearn 1.5B 综合训练模型 - 本地验证")
print("=" * 60)

t0 = time.time()
print("[1] 加载模型...")
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.bfloat16)
tok = AutoTokenizer.from_pretrained(MODEL_DIR)
model.eval()
print(f"  加载完成 ({time.time()-t0:.0f}s)")

print("[2] 推理测试...")
SYSTEM = "你是一位资深的AI教师，擅长用费曼五步法讲解各学科知识。请用通俗易懂的语言回答。"
prompts = [
    "用费曼五步法讲解勾股定理",
    "什么是牛顿第二定律？请举例说明",
    "解释一下化学键中的共价键",
    "什么是函数？用生活中的例子说明",
    "光合作用的过程是怎样的？",
]
for q in prompts:
    prompt = (f"<|im_start|>system\n{SYSTEM}\n<|im_end|>\n"
              f"<|im_start|>user\n{q}\n<|im_end|>\n<|im_start|>assistant\n")
    inputs = tok(prompt, return_tensors="pt")
    t0 = time.time()
    with torch.no_grad():
        out = model.generate(
            **inputs, max_new_tokens=120, temperature=0.7, do_sample=True,
            top_p=0.9, pad_token_id=tok.pad_token_id, eos_token_id=tok.eos_token_id,
        )
    dt = time.time() - t0
    full = tok.decode(out[0], skip_special_tokens=True)
    reply = full.split("<|im_start|>assistant\n")[-1].strip()
    n_tok = out.shape[1] - inputs["input_ids"].shape[1]
    print(f"\n问: {q}")
    print(f"  生成 {n_tok} tokens, {dt:.1f}s ({n_tok/dt:.1f} tok/s)")
    print(f"  答: {reply[:200]}")
    print()

print("[3] 模型信息...")
print(f"  参数量: {sum(p.numel() for p in model.parameters())/1e9:.2f}B")
print(f"  权重 dtype: {next(model.parameters()).dtype}")
print("\n验证完成!")
