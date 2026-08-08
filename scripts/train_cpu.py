#!/usr/bin/env python3
"""
LumiLearn CPU 训练入口
使用 cpu_small 预设，在 CPU 上完整训练模型

用法:
    # 从零训练
    python scripts/train_cpu.py

    # 从已有模型权重 warm-start 续训（综合数据）
    python scripts/train_cpu.py --init-from outputs/cpu_small/<exp_dir>/model --max-steps 3000

    # 指定数据文件
    python scripts/train_cpu.py --data data/merged_corpus.jsonl
"""
import os
import sys
import time
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

from framework.config import get_preset_configs
from framework.model import LumiLearnModel
from framework.tokenizer import LumiLearnTokenizer
from framework.data import load_records
from framework.trainer import LumiLearnTrainer
from framework.utils import get_device


def parse_args():
    p = argparse.ArgumentParser(description="LumiLearn CPU 训练")
    p.add_argument("--preset", default="cpu_small", help="配置预设名称")
    p.add_argument("--data", default=None,
                   help="训练数据路径（默认 data/merged_corpus.jsonl，不存在则用 training_corpus.jsonl）")
    p.add_argument("--init-from", default=None,
                   help="已有模型目录（含 config.json + model.pt），加载权重后续训")
    p.add_argument("--max-steps", type=int, default=None, help="覆盖训练步数")
    return p.parse_args()


def main():
    args = parse_args()
    print("=" * 70)
    print("LumiLearn CPU Training - Full Parameter Expansion")
    print("=" * 70)

    configs = get_preset_configs()
    config = configs[args.preset]
    if args.max_steps:
        config.training.max_steps = args.max_steps

    print(f"\n[配置] {config.experiment.name} v{config.experiment.version}")
    print(f"  模型: {config.model.param_count} params")
    print(f"  设备: {get_device()}")
    print(f"  训练步数: {config.training.max_steps}")
    print(f"  批次大小: {config.training.batch_size} x {config.training.gradient_accumulation}")

    # 数据路径: 优先 merged_corpus.jsonl（综合训练集）
    data_path = args.data
    if data_path is None:
        merged = os.path.join(PROJECT_DIR, "data", "merged_corpus.jsonl")
        if os.path.exists(merged):
            data_path = merged
        else:
            data_path = os.path.join(PROJECT_DIR, "data", "training_corpus.jsonl")
    if not os.path.exists(data_path):
        print(f"\n[错误] 训练数据不存在: {data_path}")
        sys.exit(1)

    print(f"\n[数据] 加载: {data_path}")
    records = load_records(data_path)
    print(f"  总记录数: {len(records)}")

    # 初始化 tokenizer
    print(f"\n[分词器] 初始化 BPE tokenizer")
    tokenizer = LumiLearnTokenizer(vocab_size=config.model.vocab_size)
    print(f"  词表大小: {tokenizer.vocab_size_actual}")

    # 初始化模型（可选：从已有权重加载）
    print(f"\n[模型] 初始化 LumiLearnModel")
    if args.init_from and os.path.exists(args.init_from):
        model = LumiLearnModel.from_pretrained(args.init_from, map_location="cpu")
        print(f"  从已有权重加载: {args.init_from}")
    else:
        model = LumiLearnModel(config.model)
        if args.init_from:
            print(f"  [警告] init_from 路径不存在: {args.init_from}，使用随机初始化")

    print(f"\n[训练器] 初始化")
    trainer = LumiLearnTrainer(
        config=config,
        model=model,
        tokenizer=tokenizer,
        train_data=records,
    )

    print(f"\n{'=' * 70}")
    print(f"开始训练")
    print(f"{'=' * 70}")

    start_time = time.time()
    trainer.train()
    elapsed = time.time() - start_time

    print(f"\n训练总耗时: {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")

    output_dir = os.path.join(PROJECT_DIR, config.experiment.output_dir)
    print(f"\n[输出] 模型保存在: {output_dir}")
    print(f"  最佳验证损失: {trainer.metrics.best_val_loss:.4f} @ step {trainer.metrics.best_step}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
