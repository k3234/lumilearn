#!/usr/bin/env python3
"""本地验证综合训练后的模型"""
import sys, os
sys.path.insert(0, "<project-root>")
import torch
from framework.model import LumiLearnModel
from framework.tokenizer import LumiLearnTokenizer

model_dir = "<project-root>/outputs/cpu_small/merged_gpu_train/model"
tok_path = "<project-root>/outputs/cpu_small/merged_gpu_train/tokenizer.json"

model = LumiLearnModel.from_pretrained(model_dir, map_location="cpu")
tokenizer = LumiLearnTokenizer.load(tok_path)
model.eval()

print(f"综合训练模型: {sum(p.numel() for p in model.parameters())/1e6:.2f}M 参数")
print(f"分词器: vocab={tokenizer.vocab_size_actual}")
print("=" * 60)

prompts = [
    "请解释什么是函数",
    "牛顿第一定律的内容是",
    "化学中的摩尔是什么",
    "细胞的主要结构包括",
]
for p in prompts:
    ids = tokenizer.encode(p, add_special_tokens=True)
    t = torch.tensor([ids], dtype=torch.long)
    with torch.no_grad():
        out = model.generate(t, max_new_tokens=50, temperature=0.7, top_k=40)
    text = tokenizer.decode(out[0].tolist())
    print(f"问: {p}")
    print(f"答: {text[:150]}")
    print()
print("验证完成")
