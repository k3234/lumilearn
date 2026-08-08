#!/usr/bin/env python3
"""
LumiLearn 训练 + 评测脚本
对预设模型快速训练，并输出 loss / 困惑度(perplexity) / 参数量等关键指标。

用法示例:
    python scripts/eval_model.py --preset fast_test --steps 200
    python scripts/eval_model.py --preset scratch_small --steps 1000 --data path/to/data.jsonl
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch

from framework.config import get_preset_configs
from framework.model import LumiLearnModel
from framework.trainer import LumiLearnTrainer


def count_parameters(model: LumiLearnModel) -> int:
    """统计模型实际可训练参数量（不含共享权重重复计数）。"""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def build_sample_data(preset: str):
    """构造一组用于验证的最小示例数据（preset 无关，仅用于冒烟验证）。"""
    subjects = ["数学", "物理", "化学", "生物", "英语"]
    samples = []
    for i in range(30):
        subject = subjects[i % len(subjects)]
        samples.append({
            "subject": subject,
            "chapter": f"示例章节{i % 5}",
            "content": (
                f"这是{subject}的示例内容，用于验证模型训练与评测管线是否完整。"
                "它包含足够多的字符，以保证分词后仍有可学习的序列长度。"
                f"（第{i}条）"
            ),
        })
    return samples


def main():
    parser = argparse.ArgumentParser(description="LumiLearn 训练 + 评测脚本")
    parser.add_argument("--preset", default="fast_test",
                        choices=list(get_preset_configs().keys()),
                        help="预设模型配置")
    parser.add_argument("--steps", type=int, default=None,
                        help="覆盖训练步数（默认取配置值）")
    parser.add_argument("--data", default=None,
                        help="自定义数据文件（jsonl/csv/json），为空则用示例数据")
    args = parser.parse_args()

    config = get_preset_configs()[args.preset]
    if args.steps is not None:
        config.training.max_steps = args.steps

    print("=" * 70)
    print("LumiLearn 训练 & 评测")
    print(config.summary())
    print("=" * 70)

    # 1) 初始化模型（用于参数统计）
    model = LumiLearnModel(config.model)

    # 2) 准备数据
    if args.data:
        from framework.data import load_records
        records = load_records(args.data)
    else:
        records = build_sample_data(args.preset)
    n = len(records)
    train_data = records[: max(1, int(n * 0.9))]
    val_data = records[int(n * 0.9):] or records[:1]

    # 3) 训练
    trainer = LumiLearnTrainer(
        config=config,
        model=model,
        train_data=train_data,
        val_data=val_data,
    )
    trainer.train()

    # 4) 评测指标
    final_loss = trainer.metrics.best_val_loss
    if final_loss == float("inf") or final_loss <= 0:
        final_loss = trainer.evaluate()

    perplexity = math.exp(final_loss) if final_loss > 0 else float("inf")
    n_params = count_parameters(model)

    print("\n" + "=" * 70)
    print("📊 评测结果")
    print("=" * 70)
    print(f"  参数量 (params):       {n_params:,}  ({n_params / 1e6:.2f}M)")
    print(f"  最佳验证 Loss:         {final_loss:.4f}")
    print(f"  困惑度 (Perplexity):   {perplexity:.2f}")
    print(f"  训练步数:              {trainer.global_step}")
    print(f"  模型输出目录:          {trainer.log_dir}")
    print("=" * 70)

    # 5) 便捷的文本生成示例（验证模型可推理）
    try:
        prompt = "物理 - 力学 - 牛顿第一定律"
        ids = trainer.tokenizer.encode(prompt, add_special_tokens=True)
        device = trainer.device
        model.eval()
        with torch.no_grad():
            generated = ids[:]
            for _ in range(32):
                input_ids = torch.tensor([generated[-config.model.max_seq_len:]],
                                         device=device)
                logits = model(input_ids)["logits"]
                next_id = int(logits[0, -1].argmax().item())
                generated.append(next_id)
                if next_id == trainer.tokenizer.eos_token_id:
                    break
        text = trainer.tokenizer.decode(generated, skip_special=True)
        print(f"\n🔤 生成示例（{prompt}）:\n{text[:200]}")
    except Exception as e:  # 推理示例失败不影响评测结果
        print(f"\n⚠️ 生成示例跳过: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
