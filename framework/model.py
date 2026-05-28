#!/usr/bin/env python3
"""
LumiLearn 模型架构
GPT-2 风格 Transformer，支持:
- 预层归一化 (Pre-LN)
- GELU 激活
- 权重绑定 (embedding/lm_head)
- 梯度检查点 (可选)
"""
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Dict, Tuple

from .config import ModelConfig


class LayerNorm(nn.Module):
    def __init__(self, hidden_size: int, eps: float = 1e-5):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.bias = nn.Parameter(torch.zeros(hidden_size))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.layer_norm(x.float(), (x.size(-1),),
                            self.weight, self.bias, self.eps).type_as(x)


class CausalSelfAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, dropout: float = 0.1):
        super().__init__()
        assert hidden_size % num_heads == 0
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads

        self.qkv = nn.Linear(hidden_size, 3 * hidden_size, bias=False)
        self.out_proj = nn.Linear(hidden_size, hidden_size, bias=False)
        self.attn_dropout = nn.Dropout(dropout)
        self.out_dropout = nn.Dropout(dropout)

        self.register_buffer("mask", torch.tril(torch.ones(1, 1, 4096, 4096)))

    def forward(self, x: torch.Tensor,
                attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape

        qkv = self.qkv(x)
        q, k, v = qkv.split(self.hidden_size, dim=-1)
        q = q.view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = k.view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.num_heads, self.head_dim).transpose(1, 2)

        attn = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))
        attn = attn.masked_fill(self.mask[:, :, :T, :T] == 0, float('-inf'))
        attn = F.softmax(attn, dim=-1)
        attn = self.attn_dropout(attn)

        out = attn @ v
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        out = self.out_proj(out)
        out = self.out_dropout(out)

        return out


class FeedForward(nn.Module):
    def __init__(self, hidden_size: int, ff_dim: int, dropout: float = 0.1):
        super().__init__()
        self.fc1 = nn.Linear(hidden_size, ff_dim, bias=False)
        self.fc2 = nn.Linear(ff_dim, hidden_size, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.fc2(F.gelu(self.fc1(x))))


class TransformerBlock(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, ff_dim: int,
                 dropout: float = 0.1, layer_norm_eps: float = 1e-5):
        super().__init__()
        self.ln1 = LayerNorm(hidden_size, layer_norm_eps)
        self.attn = CausalSelfAttention(hidden_size, num_heads, dropout)
        self.ln2 = LayerNorm(hidden_size, layer_norm_eps)
        self.ffn = FeedForward(hidden_size, ff_dim, dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))
        x = x + self.ffn(self.ln2(x))
        return x


class LumiLearnModel(nn.Module):
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config = config

        self.token_emb = nn.Embedding(config.vocab_size, config.hidden_size)
        self.pos_emb = nn.Parameter(
            torch.randn(1, config.max_seq_len, config.hidden_size) * 0.02
        )
        self.emb_dropout = nn.Dropout(config.dropout)

        self.blocks = nn.ModuleList([
            TransformerBlock(
                config.hidden_size, config.num_heads, config.ff_dim,
                config.dropout, config.layer_norm_eps,
            )
            for _ in range(config.num_layers)
        ])

        self.ln_f = LayerNorm(config.hidden_size, config.layer_norm_eps)
        self.lm_head = nn.Linear(config.hidden_size, config.vocab_size, bias=False)

        if config.tie_weights:
            self.lm_head.weight = self.token_emb.weight

        self.apply(self._init_weights)
        self._print_param_count()

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def _print_param_count(self):
        total = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        print(f"LumiLearn Model: {total/1e6:.2f}M params "
              f"({trainable/1e6:.2f}M trainable)")

    def forward(self, input_ids: torch.Tensor,
                labels: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        B, T = input_ids.shape

        x = self.token_emb(input_ids) + self.pos_emb[:, :T, :]
        x = self.emb_dropout(x)

        for block in self.blocks:
            x = block(x)

        x = self.ln_f(x)
        logits = self.lm_head(x)

        loss = None
        if labels is not None:
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss = F.cross_entropy(
                shift_logits.view(-1, shift_logits.size(-1)),
                shift_labels.view(-1),
                ignore_index=0,
            )

        return {"logits": logits, "loss": loss}

    @torch.no_grad()
    def generate(self, input_ids: torch.Tensor, max_new_tokens: int = 128,
                 temperature: float = 0.8, top_k: int = 50) -> torch.Tensor:
        self.eval()
        for _ in range(max_new_tokens):
            seq = input_ids[:, -self.config.max_seq_len:]
            outputs = self.forward(seq)

            logits = outputs["logits"][:, -1, :] / temperature

            if top_k > 0:
                topk_vals, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < topk_vals[:, -1:]] = float('-inf')

            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            input_ids = torch.cat([input_ids, next_token], dim=-1)

            if next_token.item() == self.config.vocab_size - 1:
                break

        return input_ids

    def save_pretrained(self, path: str):
        import os, json
        os.makedirs(path, exist_ok=True)
        torch.save(self.state_dict(), os.path.join(path, "model.pt"))
        from dataclasses import asdict
        with open(os.path.join(path, "config.json"), "w") as f:
            json.dump(asdict(self.config), f, indent=2)

    @classmethod
    def from_pretrained(cls, path: str, map_location: str = "cpu") -> "LumiLearnModel":
        import json
        with open(f"{path}/config.json", "r") as f:
            config_dict = json.load(f)
        config = ModelConfig(**config_dict)
        model = cls(config)
        model.load_state_dict(
            torch.load(f"{path}/model.pt", map_location=map_location),
            strict=True,
        )
        return model