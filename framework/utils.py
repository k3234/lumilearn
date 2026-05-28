#!/usr/bin/env python3
"""
LumiLearn 训练工具
- TrainingMetrics: 指标追踪
- setup_logging: 日志配置
- count_parameters: 参数量统计
"""
import os
import json
import time
import math
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

import torch


class TrainingMetrics:
    def __init__(self):
        self.train_loss: List[float] = []
        self.val_loss: List[float] = []
        self.learning_rates: List[float] = []
        self.grad_norms: List[float] = []
        self.step_times: List[float] = []
        self.steps: List[int] = []
        self.best_val_loss: float = float('inf')
        self.best_step: int = 0
        self.start_time: float = time.time()

    def log_train(self, step: int, loss: float, lr: float, grad_norm: float):
        self.steps.append(step)
        self.train_loss.append(loss)
        self.learning_rates.append(lr)
        self.grad_norms.append(grad_norm)
        self.step_times.append(time.time() - self.start_time)

    def log_val(self, loss: float):
        self.val_loss.append(loss)

    def update_best(self, step: int, val_loss: float) -> bool:
        if val_loss < self.best_val_loss:
            self.best_val_loss = val_loss
            self.best_step = step
            return True
        return False

    @property
    def elapsed(self) -> float:
        return time.time() - self.start_time

    @property
    def elapsed_str(self) -> str:
        secs = int(self.elapsed)
        h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def eta(self, current_step: int, total_steps: int) -> str:
        if current_step == 0:
            return "未知"
        eta_secs = (self.elapsed / current_step) * (total_steps - current_step)
        h, m, s = int(eta_secs) // 3600, (int(eta_secs) % 3600) // 60, int(eta_secs) % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def to_dict(self) -> Dict:
        return {
            "steps": self.steps,
            "train_loss": self.train_loss,
            "val_loss": self.val_loss,
            "learning_rates": self.learning_rates,
            "grad_norms": self.grad_norms,
            "best_val_loss": self.best_val_loss,
            "best_step": self.best_step,
            "elapsed_seconds": self.elapsed,
        }

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def summary(self) -> str:
        if not self.train_loss:
            return "No training data"

        recent_loss = sum(self.train_loss[-100:]) / min(len(self.train_loss), 100)
        steps_per_sec = len(self.steps) / max(self.elapsed, 1)

        return (
            f"Steps: {len(self.steps)} | "
            f"TrainLoss: {self.train_loss[-1]:.4f} (avg100: {recent_loss:.4f}) | "
            f"ValLoss: {self.val_loss[-1]:.4f}" if self.val_loss else f"ValLoss: N/A"
            f" | LR: {self.learning_rates[-1]:.2e}" if self.learning_rates else ""
            f" | Speed: {steps_per_sec:.1f} st/s"
            f" | Time: {self.elapsed_str}"
        )


def setup_logging(output_dir: str, experiment_name: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(output_dir, f"{experiment_name}_{timestamp}")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def count_parameters(model: torch.nn.Module) -> Dict[str, int]:
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    non_trainable = total - trainable

    breakdown = defaultdict(int)
    for name, param in model.named_parameters():
        category = name.split('.')[0]
        breakdown[category] += param.numel()

    return {
        "total": total,
        "trainable": trainable,
        "non_trainable": non_trainable,
        "breakdown": dict(breakdown),
    }


def format_bytes(n: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def seed_everything(seed: int = 42):
    import random
    import numpy as np
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False