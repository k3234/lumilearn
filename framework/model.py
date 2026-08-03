#!/usr/bin/env python3
"""
LumiLearn 模型架构（AirLLM 升级版）
支持现代 Transformer 组件:
- 预层归一化 (Pre-LN): LayerNorm / RMSNorm（可选）
- 激活函数: GELU / SwiGLU（可选）
- 注意力: MHA / GQA + RoPE（可选）
- 权重绑定 (embedding/lm_head)
- 梯度检查点（训练时每层单独重算激活值，省60%内存）
"""
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Dict, Tuple

from .config import ModelConfig


# =============================================================================
# 归一化层
# =============================================================================

class LayerNorm(nn.Module):
    """标准 LayerNorm（保留向后兼容）"""
    def __init__(self, hidden_size: int, eps: float = 1e-5):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.bias = nn.Parameter(torch.zeros(hidden_size))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.layer_norm(x.float(), (x.size(-1),),
                            self.weight, self.bias, self.eps).type_as(x)


class RMSNorm(nn.Module):
    """
    RMSNorm: Root Mean Square Layer Normalization
    论文: Root Mean Square Layer Normalization (Zhang & Sennrich, 2019)

    相比 LayerNorm:
      - 不需要计算均值（省去一次归约操作）
      - 不需要 bias 参数（参数量减少一半）
      - 计算更快 ~15%，效果相当

    公式: RMSNorm(x) = x / RMS(x) * γ,  其中 RMS(x) = sqrt(mean(x²) + ε)
    """
    def __init__(self, hidden_size: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # 用 float32 计算保证数值稳定性
        x_f32 = x.float()
        rms = torch.sqrt(torch.mean(x_f32 ** 2, dim=-1, keepdim=True) + self.eps)
        return (x_f32 / rms * self.weight.float()).type_as(x)


def _make_norm(hidden_size: int, eps: float, use_rmsnorm: bool) -> nn.Module:
    """工厂函数：根据配置创建 LayerNorm 或 RMSNorm"""
    if use_rmsnorm:
        return RMSNorm(hidden_size, eps)
    return LayerNorm(hidden_size, eps)


# =============================================================================
# 前馈网络
# =============================================================================

class FeedForward(nn.Module):
    """
    标准 FFN: fc1(GELU) → dropout → fc2
    两个权重矩阵: [hidden, ff_dim] 和 [ff_dim, hidden]
    """
    def __init__(self, hidden_size: int, ff_dim: int, dropout: float = 0.1):
        super().__init__()
        self.fc1 = nn.Linear(hidden_size, ff_dim, bias=False)
        self.fc2 = nn.Linear(ff_dim, hidden_size, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.fc2(F.gelu(self.fc1(x))))


class SwiGLUFeedForward(nn.Module):
    """
    SwiGLU 前馈网络
    论文: GLU Variants Improve Transformer (Shazeer, 2020)

    结构: (x @ W_gate · σ(x @ W_up)) @ W_down
    三个权重矩阵: gate [hidden, ff_dim], up [hidden, ff_dim], down [ff_dim, hidden]

    相比 GELU:
      - 多一个权重矩阵（参数量 +50%），但 ff_dim 通常设为 2/3 以保持总参数相近
      - 实际训练效果更好（PaLM、LLaMA、Qwen 均采用）
    """
    def __init__(self, hidden_size: int, ff_dim: int, dropout: float = 0.1):
        super().__init__()
        # SwiGLU 需要三个投影矩阵
        self.gate_proj = nn.Linear(hidden_size, ff_dim, bias=False)   # 门控
        self.up_proj = nn.Linear(hidden_size, ff_dim, bias=False)     # 上投影
        self.down_proj = nn.Linear(ff_dim, hidden_size, bias=False)    # 下投影
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # SwiGLU(x) = (x @ W_gate · σ(x @ W_up)) @ W_down
        # 其中 σ 是 SiLU (Sigmoid Linear Unit) = x * sigmoid(x)
        gate = F.silu(self.gate_proj(x))   # SiLU 激活的门控
        up = self.up_proj(x)               # 线性上投影
        return self.dropout(self.down_proj(gate * up))


def _make_ffn(hidden_size: int, ff_dim: int, dropout: float,
              activation: str) -> nn.Module:
    """工厂函数：根据激活函数类型创建 FFN"""
    if activation == "swiglu":
        return SwiGLUFeedForward(hidden_size, ff_dim, dropout)
    return FeedForward(hidden_size, ff_dim, dropout)


# =============================================================================
# 注意力层（保留原版 + 支持 AirLLM GQA）
# =============================================================================

class CausalSelfAttention(nn.Module):
    """原版 MHA 自注意力（保留向后兼容）"""
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


# =============================================================================
# Transformer Block（新版，支持 AirLLM 所有特性）
# =============================================================================

class TransformerBlock(nn.Module):
    """
    Transformer 解码器块（Pre-LN 架构）

    支持:
      - 归一化: LayerNorm / RMSNorm（通过 use_rmsnorm 控制）
      - 注意力: MHA / GQA + RoPE（通过 use_rotary / num_kv_heads 控制）
      - 前馈: GELU / SwiGLU（通过 activation 控制）
    """
    def __init__(self, config: ModelConfig, layer_idx: int = 0):
        super().__init__()
        self.layer_idx = layer_idx

        # 归一化
        self.ln1 = _make_norm(config.hidden_size, config.layer_norm_eps,
                              config.use_rmsnorm)
        self.ln2 = _make_norm(config.hidden_size, config.layer_norm_eps,
                              config.use_rmsnorm)

        # 注意力（新版 GQA 或旧版 MHA）
        if config.num_kv_heads > 0 and config.num_kv_heads != config.num_heads:
            from .airllm.attention import CausalSelfAttentionGQA
            self.attn = CausalSelfAttentionGQA(
                config.hidden_size, config.num_heads, config.num_kv_heads,
                config.dropout, config.max_seq_len,
            )
        else:
            self.attn = CausalSelfAttention(
                config.hidden_size, config.num_heads, config.dropout,
            )

        # 前馈
        self.ffn = _make_ffn(config.hidden_size, config.ff_dim,
                             config.dropout, config.activation)

    def forward(self, x: torch.Tensor,
                cos: Optional[torch.Tensor] = None,
                sin: Optional[torch.Tensor] = None) -> torch.Tensor:
        # Pre-LN + 残差连接
        if cos is not None and hasattr(self.attn, 'forward'):
            # 新版 GQA 注意力（带 RoPE）
            x = x + self.attn(self.ln1(x), cos=cos, sin=sin)
        else:
            x = x + self.attn(self.ln1(x))
        x = x + self.ffn(self.ln2(x))
        return x


# =============================================================================
# 主模型
# =============================================================================

class LumiLearnModel(nn.Module):
    """
    LumiLearn 语言模型（GPT-style 自回归 Transformer）

    AirLLM 升级:
      - RoPE 旋转位置编码 → 支持外推到更长序列
      - RMSNorm → 计算量减少 ~15%
      - SwiGLU → 训练质量提升
      - GQA → KV 缓存减少 4 倍（32头→8KV头）
      - 梯度检查点 → 反向传播时重算激活，省 60% 内存
    """
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config = config

        # Token 嵌入
        self.token_emb = nn.Embedding(config.vocab_size, config.hidden_size)

        # 位置编码: 可学习嵌入 或 RoPE
        self.use_rotary = config.use_rotary
        if self.use_rotary:
            from .airllm.rope import RotaryEmbedding
            self.rope = RotaryEmbedding(
                config.hidden_size // config.num_heads,
                config.max_seq_len,
            )
        else:
            self.pos_emb = nn.Parameter(
                torch.randn(1, config.max_seq_len, config.hidden_size) * 0.02
            )

        self.emb_dropout = nn.Dropout(config.dropout)

        # Transformer 层
        self.blocks = nn.ModuleList([
            TransformerBlock(config, layer_idx=i)
            for i in range(config.num_layers)
        ])

        # 最终归一化
        self.ln_f = _make_norm(config.hidden_size, config.layer_norm_eps,
                               config.use_rmsnorm)
        self.lm_head = nn.Linear(config.hidden_size, config.vocab_size, bias=False)

        # 权重绑定
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
        features = [
            f"{total/1e6:.2f}M params ({trainable/1e6:.2f}M trainable)",
        ]
        if self.use_rotary:
            features.append("RoPE")
        if self.config.use_rmsnorm:
            features.append("RMSNorm")
        if self.config.activation == "swiglu":
            features.append("SwiGLU")
        if self.config.num_kv_heads > 0 and self.config.num_kv_heads != self.config.num_heads:
            features.append(f"GQA({self.config.num_heads}/{self.config.num_kv_heads})")
        print(f"LumiLearn Model: " + " | ".join(features))

    def forward(self, input_ids: torch.Tensor,
                labels: Optional[torch.Tensor] = None,
                use_checkpoint: bool = False) -> Dict[str, torch.Tensor]:
        """
        前向传播

        参数:
            input_ids: [batch, seq] token ID 序列
            labels: [batch, seq] 训练标签（用于计算 loss）
            use_checkpoint: 是否使用梯度检查点（训练时节省内存）
        """
        B, T = input_ids.shape

        # 嵌入
        x = self.token_emb(input_ids)

        # 位置编码
        if self.use_rotary:
            cos, sin = self.rope(T, x.device)
            x = self.emb_dropout(x)
        else:
            x = x + self.pos_emb[:, :T, :]
            x = self.emb_dropout(x)
            cos, sin = None, None

        # Transformer 层
        for block in self.blocks:
            if use_checkpoint and self.training:
                # 梯度检查点: 前向不保存中间激活，反向时重算
                x = torch.utils.checkpoint.checkpoint(
                    block, x, cos, sin,
                    use_reentrant=False,
                )
            else:
                x = block(x, cos=cos, sin=sin)

        x = self.ln_f(x)
        logits = self.lm_head(x)

        # 损失计算
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
        """自回归生成"""
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

            # FIX: EOS token ID is 1 (not vocab_size - 1)
            if next_token.item() == 1:
                break

        return input_ids

    def save_pretrained(self, path: str):
        """保存模型和配置"""
        import os, json
        os.makedirs(path, exist_ok=True)
        torch.save(self.state_dict(), os.path.join(path, "model.pt"))
        from dataclasses import asdict
        with open(os.path.join(path, "config.json"), "w", encoding="utf-8") as f:
            json.dump(asdict(self.config), f, indent=2, ensure_ascii=False)

    @classmethod
    def from_pretrained(cls, path: str, map_location: str = "cpu") -> "LumiLearnModel":
        """加载预训练模型"""
        import json
        with open(f"{path}/config.json", "r", encoding="utf-8") as f:
            config_dict = json.load(f)
        config = ModelConfig(**config_dict)
        model = cls(config)
        model.load_state_dict(
            torch.load(f"{path}/model.pt", map_location=map_location),
            strict=True,
        )
        return model