#!/usr/bin/env python3
"""
LumiLearn Training Entry Point
Trains the model with BPE tokenizer on CSV training data
"""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from framework.config import LumiLearnConfig
from framework.model import LumiLearnModel
from framework.tokenizer import LumiLearnTokenizer
from framework.data import load_records
from framework.trainer import LumiLearnTrainer


def main():
    config = LumiLearnConfig()

    data_path = os.path.join(SCRIPT_DIR, "lumilearn_master.csv")
    if not os.path.exists(data_path):
        data_path = os.path.join(SCRIPT_DIR, "lumilearn_training_merged.csv")

    print(f"Data: {data_path}")

    records = load_records(data_path)

    tokenizer = LumiLearnTokenizer(vocab_size=config.model.vocab_size)
    print(f"Tokenizer: vocab={tokenizer.vocab_size_actual} (BPE subword)")

    model = LumiLearnModel(config.model)
    print(f"Model: {sum(p.numel() for p in model.parameters()):,} params")

    trainer = LumiLearnTrainer(
        config=config,
        model=model,
        tokenizer=tokenizer,
        train_data=records,
    )

    trainer.train()


if __name__ == "__main__":
    main()