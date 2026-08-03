#!/usr/bin/env python3
"""
LumiLearn AirLLM - GQA (Grouped Query Attention) 注意力层
支持 RoPE 旋转位置编码
"""
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional


class CausalSelfAttentionGQA(nn.Module):
    """
    GQA (Grouped Query Attention) 因果自注意力层
    
    GQA 原理：
    - 多个 Query 头共享一组 KV 头
    - 例如 8 个 Q 头，2 个 KV 头，每 4 个 Q 头共享 1 个 KV 头
    - 减少 KV Cache 内存占用，加速推理
    
    支持 RoPE (Rotary Position Embedding)：
    - 旋转位置编码，支持外推到更长序列
    - 通过 cos/sin 旋转矩阵编码位置信息
    """
    
    def __init__(self, hidden_size: int, num_heads: int, num_kv_heads: int,
                 dropout: float = 0.1, max_seq_len: int = 2048):
        super().__init__()
        assert hidden_size % num_heads == 0
        assert num_heads % num_kv_heads == 0
        
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.num_kv_heads = num_kv_heads
        self.head_dim = hidden_size // num_heads
        self.num_queries_per_kv = num_heads // num_kv_heads
        
        # Q 投影
        self.q_proj = nn.Linear(hidden_size, num_heads * self.head_dim, bias=False)
        # KV 投影（KV 头数少于 Q 头）
        self.k_proj = nn.Linear(hidden_size, num_kv_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(hidden_size, num_kv_heads * self.head_dim, bias=False)
        # 输出投影
        self.out_proj = nn.Linear(hidden_size, hidden_size, bias=False)
        
        self.attn_dropout = nn.Dropout(dropout)
        self.out_dropout = nn.Dropout(dropout)
        
        # 因果掩码
        self.register_buffer(
            "mask",
            torch.tril(torch.ones(1, 1, max_seq_len, max_seq_len))
        )
    
    def forward(self, x: torch.Tensor,
                cos: Optional[torch.Tensor] = None,
                sin: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        
        # Q 投影
        q = self.q_proj(x)
        q = q.view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        
        # KV 投影
        k = self.k_proj(x)
        k = k.view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x)
        v = v.view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        
        # 应用 RoPE
        if cos is not None and sin is not None:
            q, k = self._apply_rotary(q, k, cos, sin)
        
        # GQA: 扩展 KV 头以匹配 Q 头数
        if self.num_queries_per_kv > 1:
            k = k.repeat_interleave(self.num_queries_per_kv, dim=1)
            v = v.repeat_interleave(self.num_queries_per_kv, dim=1)
        
        # 注意力计算
        attn = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))
        attn = attn.masked_fill(self.mask[:, :, :T, :T] == 0, float('-inf'))
        attn = F.softmax(attn, dim=-1)
        attn = self.attn_dropout(attn)
        
        out = attn @ v
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        out = self.out_proj(out)
        out = self.out_dropout(out)
        
        return out
    
    def _apply_rotary(self, q: torch.Tensor, k: torch.Tensor,
                       cos: torch.Tensor, sin: torch.Tensor):
        """应用旋转位置编码"""
        # cos, sin: [seq_len, head_dim]
        # q, k: [batch, heads, seq_len, head_dim]
        cos = cos.unsqueeze(0).unsqueeze(0)
        sin = sin.unsqueeze(0).unsqueeze(0)
        
        # 旋转：x1*cos - x2*sin, x1*sin + x2*cos
        q_cos = q * cos
        q_sin = torch.cat([
            q[..., self.head_dim//2:] * (-1),
            q[..., :self.head_dim//2]
        ], dim=-1)
        q_rot = q_cos + q_sin * sin
        
        k_cos = k * cos
        k_sin = torch.cat([
            k[..., self.head_dim//2:] * (-1),
            k[..., :self.head_dim//2]
        ], dim=-1)
        k_rot = k_cos + k_sin * sin
        
        return q_rot, k_rot
