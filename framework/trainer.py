#!/usr/bin/env python3
"""
LumiLearn 训练器
完整的训练循环: 梯度累积 / Warmup+Cosine调度 / 自动混合精度 / Checkpoint / 早停
"""
import os
import json
import time
import math
import shutil
from pathlib import Path
from typing import Optional, Dict, Tuple

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.nn.utils import clip_grad_norm_

from .config import LumiLearnConfig
from .model import LumiLearnModel
from .tokenizer import LumiLearnTokenizer
from .data import LumiLearnDataset, create_dataloaders
from .utils import TrainingMetrics, setup_logging, seed_everything, get_device


class LumiLearnTrainer:
    def __init__(self, config: LumiLearnConfig,
                 model: Optional[LumiLearnModel] = None,
                 tokenizer: Optional[LumiLearnTokenizer] = None,
                 train_data: Optional[list] = None,
                 val_data: Optional[list] = None):
        self.config = config
        self.device = get_device()

        seed_everything(config.experiment.seed)

        self.tokenizer = tokenizer or LumiLearnTokenizer(config.model.vocab_size)
        self.model = model or LumiLearnModel(config.model)
        self.model = self.model.to(self.device)

        self.metrics = TrainingMetrics()
        self.log_dir = setup_logging(
            config.experiment.output_dir, config.experiment.name
        )
        self.ckpt_dir = os.path.join(self.log_dir, "checkpoints")
        os.makedirs(self.ckpt_dir, exist_ok=True)

        self._build_dataloaders(train_data, val_data)
        self._build_optimizer()
        self._build_scheduler()

        self.global_step = 0
        self.epoch = 0
        self.best_val_loss = float('inf')
        self.early_stop_counter = 0

        self._save_config()

        print(f"\n{'='*70}")
        print(f"🚀 LumiLearn Trainer 初始化完成")
        print(f"{'='*70}")
        print(self.config.summary())
        print(f"  设备: {self.device}")
        print(f"  训练集: {len(self.train_loader.dataset)} 条")
        print(f"  验证集: {len(self.val_loader.dataset)} 条")
        print(f"  日志: {self.log_dir}")
        print(f"{'='*70}\n")

    def _build_dataloaders(self, train_data, val_data):
        cfg = self.config

        if train_data is not None:
            train_ds = LumiLearnDataset(train_data, self.tokenizer,
                                        cfg.model.max_seq_len)
            val_ds = LumiLearnDataset(val_data or [], self.tokenizer,
                                      cfg.model.max_seq_len)

            common = dict(num_workers=cfg.data.num_workers,
                          pin_memory=cfg.data.pin_memory)

            self.train_loader = DataLoader(
                train_ds, batch_size=cfg.training.batch_size,
                shuffle=True, **common
            )
            self.val_loader = DataLoader(
                val_ds, batch_size=cfg.training.batch_size,
                shuffle=False, **common
            )
        else:
            raise ValueError("Must provide train_data (list of dicts)")

    def _build_optimizer(self):
        cfg = self.config.training

        decay_params = []
        no_decay_params = []

        for name, param in self.model.named_parameters():
            if not param.requires_grad:
                continue
            if 'bias' in name or 'norm' in name.lower() or 'ln_' in name:
                no_decay_params.append(param)
            else:
                decay_params.append(param)

        self.optimizer = optim.AdamW([
            {"params": decay_params, "weight_decay": cfg.weight_decay},
            {"params": no_decay_params, "weight_decay": 0.0},
        ], lr=cfg.learning_rate, betas=cfg.betas)

    def _build_scheduler(self):
        cfg = self.config.training

        def lr_lambda(step):
            if step < cfg.warmup_steps:
                return step / max(1, cfg.warmup_steps)
            progress = (step - cfg.warmup_steps) / max(1, cfg.max_steps - cfg.warmup_steps)
            cosine_decay = 0.5 * (1 + math.cos(math.pi * progress))
            min_factor = cfg.min_lr / cfg.learning_rate
            return max(min_factor, cosine_decay)

        self.scheduler = optim.lr_scheduler.LambdaLR(self.optimizer, lr_lambda)

    def _save_config(self):
        self.config.to_json(os.path.join(self.log_dir, "config.json"))

    def train(self):
        cfg = self.config.training
        self.model.train()
        self.metrics.start_time = time.time()

        accum_loss = 0.0
        iter_in_accum = 0

        print(f"🏃 开始训练: {cfg.max_steps} 步, "
              f"warmup={cfg.warmup_steps}, "
              f"grad_accum={cfg.gradient_accumulation}\n")

        while self.global_step < cfg.max_steps:
            for batch in self.train_loader:
                input_ids = batch["input_ids"].to(self.device)
                labels = batch["labels"].to(self.device)

                outputs = self.model(input_ids, labels=labels)
                loss = outputs["loss"] / cfg.gradient_accumulation
                accum_loss += loss.item()
                iter_in_accum += 1

                loss.backward()

                if (iter_in_accum) % cfg.gradient_accumulation == 0:
                    grad_norm = clip_grad_norm_(
                        self.model.parameters(), cfg.max_grad_norm
                    )
                    self.optimizer.step()
                    self.scheduler.step()
                    self.optimizer.zero_grad()

                    self.global_step += 1
                    avg_loss = accum_loss / cfg.gradient_accumulation
                    lr = self.optimizer.param_groups[0]["lr"]
                    accum_loss = 0.0

                    self.metrics.log_train(
                        self.global_step, avg_loss, lr, grad_norm.item()
                    )

                    if self.global_step % cfg.log_every == 0:
                        self._print_progress()

                    if self.global_step % cfg.eval_every == 0:
                        val_loss = self.evaluate()
                        self.metrics.log_val(val_loss)

                        is_best = self.metrics.update_best(self.global_step, val_loss)

                        if is_best:
                            self.early_stop_counter = 0
                            self.save_checkpoint("best")
                        else:
                            self.early_stop_counter += 1

                        self._print_eval(val_loss, is_best)

                        if self.early_stop_counter >= cfg.early_stop_patience:
                            print(f"\n⏹ 早停触发: {cfg.early_stop_patience} 次验证未改善")
                            self._finalize()
                            return

                        self.model.train()

                    if self.global_step % cfg.save_every == 0:
                        self.save_checkpoint(f"step_{self.global_step}")

                    if self.global_step >= cfg.max_steps:
                        break

                if self.global_step >= cfg.max_steps:
                    break

        self._finalize()

    def _print_progress(self):
        cfg = self.config.training
        lr = self.optimizer.param_groups[0]["lr"]

        print(
            f"[{self.metrics.elapsed_str}] "
            f"Step {self.global_step}/{cfg.max_steps} | "
            f"Loss: {self.metrics.train_loss[-1]:.4f} | "
            f"LR: {lr:.2e} | "
            f"ETA: {self.metrics.eta(self.global_step, cfg.max_steps)}"
        )

    def _print_eval(self, val_loss: float, is_best: bool):
        marker = " 🏆 NEW BEST" if is_best else ""
        print(
            f"  📊 Val Loss: {val_loss:.4f} | "
            f"Best: {self.metrics.best_val_loss:.4f} @ step {self.metrics.best_step}"
            f"{marker}"
        )

    @torch.no_grad()
    def evaluate(self) -> float:
        self.model.eval()
        total_loss = 0.0
        count = 0

        for batch in self.val_loader:
            input_ids = batch["input_ids"].to(self.device)
            labels = batch["labels"].to(self.device)
            outputs = self.model(input_ids, labels=labels)
            loss = outputs["loss"]
            if loss is not None:
                total_loss += loss.item()
                count += 1

        return total_loss / max(count, 1)

    def save_checkpoint(self, tag: str):
        ckpt = {
            "step": self.global_step,
            "epoch": self.epoch,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "scheduler_state_dict": self.scheduler.state_dict(),
            "metrics": self.metrics.to_dict(),
            "config": self.config,
        }

        path = os.path.join(self.ckpt_dir, f"checkpoint_{tag}.pt")
        torch.save(ckpt, path)

        if tag == "best":
            best_link = os.path.join(self.log_dir, "best_model.pt")
            if os.path.exists(best_link):
                os.remove(best_link)
            shutil.copy2(path, best_link)

        print(f"  💾 Checkpoint saved: {tag}")

    def load_checkpoint(self, path: str):
        ckpt = torch.load(path, map_location=self.device)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        self.scheduler.load_state_dict(ckpt["scheduler_state_dict"])
        self.global_step = ckpt["step"]
        self.epoch = ckpt.get("epoch", 0)

        if "metrics" in ckpt:
            self.metrics = TrainingMetrics()
            m = ckpt["metrics"]
            self.metrics.steps = m.get("steps", [])
            self.metrics.train_loss = m.get("train_loss", [])
            self.metrics.val_loss = m.get("val_loss", [])
            self.metrics.learning_rates = m.get("learning_rates", [])
            self.metrics.best_val_loss = m.get("best_val_loss", float('inf'))
            self.metrics.best_step = m.get("best_step", 0)

        print(f"  📂 Checkpoint loaded: step {self.global_step}")

    def _finalize(self):
        self.save_checkpoint("final")
        self.metrics.save(os.path.join(self.log_dir, "training_metrics.json"))

        best_path = os.path.join(self.log_dir, "best_model.pt")
        final_path = os.path.join(self.log_dir, "final_model.pt")
        if not os.path.exists(best_path) and os.path.exists(final_path):
            shutil.copy2(final_path, best_path)

        self.model.save_pretrained(os.path.join(self.log_dir, "model"))
        self.tokenizer.save(os.path.join(self.log_dir, "tokenizer.json"))

        print(f"\n{'='*70}")
        print(f"🎉 训练完成!")
        print(f"  最终步数: {self.global_step}")
        print(f"  最佳ValLoss: {self.metrics.best_val_loss:.4f} @ step {self.metrics.best_step}")
        print(f"  总耗时: {self.metrics.elapsed_str}")
        print(f"  模型保存在: {self.log_dir}")
        print(f"{'='*70}")