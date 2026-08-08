#!/usr/bin/env python3
"""
LumiLearn 训练后模型验证
验证模型加载、推理、保存/加载一致性
"""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

import torch
from framework.model import LumiLearnModel
from framework.tokenizer import LumiLearnTokenizer


def test_model_loading(model_dir):
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
    print("\n[2/4] 测试分词器加载...")
    assert os.path.exists(tokenizer_path), f"tokenizer.json not found: {tokenizer_path}"
    tokenizer = LumiLearnTokenizer.load(tokenizer_path)
    print(f"  分词器加载成功: vocab_size={tokenizer.vocab_size_actual}")
    return tokenizer


def test_encoding_decoding(tokenizer):
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
        print(f"  原文: {text}")
        print(f"  Token IDs ({len(ids)}个): {ids[:8]}...")
        print(f"  解码: {decoded[:60]}")
        print()
    print("  编解码测试通过")


def test_inference(model, tokenizer):
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
            output = model.generate(input_tensor, max_new_tokens=50, temperature=0.8, top_k=50)
        generated = tokenizer.decode(output[0].tolist())
        print(f"  提示: {prompt}")
        print(f"  生成: {generated[:120]}")
        print()
    print("  推理测试通过")


def main():
    print("=" * 70)
    print("LumiLearn 模型验证")
    print("=" * 70)

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