#!/usr/bin/env python3
"""
LumiLearn 训练配置中心
集中管理所有超参数，支持 JSON 导入/导出
"""
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ModelConfig:
    vocab_size: int = 8000
    hidden_size: int = 384
    num_layers: int = 8
    num_heads: int = 8
    ff_dim: int = 1024
    max_seq_len: int = 384
    dropout: float = 0.3
    activation: str = "gelu"
    use_rotary: bool = False
    tie_weights: bool = True
    layer_norm_eps: float = 1e-5

    @property
    def param_count(self) -> str:
        emb = self.vocab_size * self.hidden_size
        per_layer = 4 * self.hidden_size * self.hidden_size + 2 * self.hidden_size
        total = emb + self.num_layers * per_layer + self.hidden_size * self.vocab_size
        if total > 1e9:
            return f"{total/1e9:.2f}B"
        return f"{total/1e6:.2f}M"


@dataclass
class TrainingConfig:
    learning_rate: float = 1e-3
    min_lr: float = 1e-5
    weight_decay: float = 0.1
    betas: tuple = (0.9, 0.95)
    warmup_steps: int = 500
    max_steps: int = 50000
    batch_size: int = 8
    gradient_accumulation: int = 4
    max_grad_norm: float = 1.0
    save_every: int = 2000
    eval_every: int = 1000
    log_every: int = 100
    early_stop_patience: int = 10
    use_amp: bool = False


@dataclass
class DataConfig:
    train_ratio: float = 0.90
    val_ratio: float = 0.05
    min_content_length: int = 80
    max_content_length: int = 2000
    num_workers: int = 0
    pin_memory: bool = False
    prefetch_factor: int = 2
    shuffle_buffer_size: int = 10000


@dataclass
class ExperimentConfig:
    name: str = "LumiLearn-v5"
    version: str = "5.0.0"
    description: str = ""
    seed: int = 42
    output_dir: str = "outputs"
    checkpoint_dir: str = "checkpoints"
    log_dir: str = "logs"
    use_wandb: bool = False
    wandb_project: str = "lumilearn"
    tags: list = field(default_factory=list)


@dataclass
class LumiLearnConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    data: DataConfig = field(default_factory=DataConfig)
    experiment: ExperimentConfig = field(default_factory=ExperimentConfig)

    @classmethod
    def from_json(cls, path: str) -> "LumiLearnConfig":
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        config = cls()
        if "model" in raw:
            for k, v in raw["model"].items():
                if hasattr(config.model, k):
                    setattr(config.model, k, v)
        if "training" in raw:
            for k, v in raw["training"].items():
                if hasattr(config.training, k):
                    setattr(config.training, k, v)
        if "data" in raw:
            for k, v in raw["data"].items():
                if hasattr(config.data, k):
                    setattr(config.data, k, v)
        if "experiment" in raw:
            for k, v in raw["experiment"].items():
                if hasattr(config.experiment, k):
                    setattr(config.experiment, k, v)
        return config

    def to_json(self, path: str):
        d = {
            "model": asdict(self.model),
            "training": asdict(self.training),
            "data": asdict(self.data),
            "experiment": asdict(self.experiment),
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

    def summary(self) -> str:
        lines = [
            f"LumiLearn {self.experiment.version} · {self.experiment.name}",
            f"Model: {self.model.param_count} params | "
            f"H={self.model.hidden_size} L={self.model.num_layers} "
            f"Hd={self.model.num_heads} FF={self.model.ff_dim}",
            f"Training: lr={self.training.learning_rate} "
            f"bs={self.training.batch_size}x{self.training.gradient_accumulation} "
            f"steps={self.training.max_steps} warmup={self.training.warmup_steps}",
            f"Data: max_seq={self.model.max_seq_len} "
            f"vocab={self.model.vocab_size}",
            f"Output: {self.experiment.output_dir}",
        ]
        return "\n".join(lines)


def get_preset_configs() -> dict:
    return {
        "scratch_small": LumiLearnConfig(
            model=ModelConfig(vocab_size=4000, hidden_size=256, num_layers=6,
                              num_heads=8, ff_dim=768, max_seq_len=256, dropout=0.3),
            training=TrainingConfig(learning_rate=1e-3, max_steps=5000,
                                    warmup_steps=500, batch_size=4, gradient_accumulation=2),
        ),
        "scratch_medium": LumiLearnConfig(
            model=ModelConfig(vocab_size=8000, hidden_size=512, num_layers=10,
                              num_heads=8, ff_dim=1536, max_seq_len=512, dropout=0.25),
            training=TrainingConfig(learning_rate=8e-4, max_steps=80000,
                                    warmup_steps=1000, batch_size=6, gradient_accumulation=6),
        ),
        "scratch_large": LumiLearnConfig(
            model=ModelConfig(vocab_size=20000, hidden_size=768, num_layers=12,
                              num_heads=12, ff_dim=2048, max_seq_len=512, dropout=0.2),
            training=TrainingConfig(learning_rate=6e-4, max_steps=100000,
                                    warmup_steps=1500, batch_size=4, gradient_accumulation=8),
        ),
        "fast_test": LumiLearnConfig(
            model=ModelConfig(vocab_size=8000, hidden_size=256, num_layers=4,
                              num_heads=4, ff_dim=512, max_seq_len=256, dropout=0.2),
            training=TrainingConfig(learning_rate=5e-4, max_steps=1000,
                                    warmup_steps=50, batch_size=16, gradient_accumulation=1),
        ),
        "scratch_gpu": LumiLearnConfig(
            model=ModelConfig(vocab_size=8000, hidden_size=512, num_layers=8,
                              num_heads=8, ff_dim=1024, max_seq_len=384, dropout=0.25),
            training=TrainingConfig(learning_rate=8e-4, max_steps=2000,
                                    warmup_steps=250, batch_size=8, gradient_accumulation=4,
                                    save_every=1000, eval_every=500, log_every=100),
        ),
    }