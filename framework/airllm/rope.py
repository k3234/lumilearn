#!/usr/bin/env python3
"""
LumiLearn AirLLM - RoPE (Rotary Position Embedding)
旋转位置编码，支持外推到更长序列
"""
import torch
import torch.nn as nn
import math


class RotaryEmbedding(nn.Module):
    """
    旋转位置编码 (RoPE)
    
    原理：
    - 通过旋转矩阵编码位置信息
    - 支持外推到训练时未见过的序列长度
    - 相比绝对位置编码，更好地捕获相对位置关系
    
    论文：RoFormer: Enhanced Transformer with Rotary Position Embedding
    """
    
    def __init__(self, head_dim: int, max_seq_len: int = 2048, base: int = 10000):
        super().__init__()
        self.head_dim = head_dim
        self.max_seq_len = max_seq_len
        self.base = base
        
        # 预计算频率
        inv_freq = 1.0 / (base ** (torch.arange(0, head_dim, 2).float() / head_dim))
        self.register_buffer("inv_freq", inv_freq)
        
        # 预计算 cos/sin 缓存
        self._build_cache(max_seq_len)
    
    def _build_cache(self, seq_len: int):
        """构建 cos/sin 缓存"""
        t = torch.arange(seq_len, device=self.inv_freq.device).float()
        freqs = torch.outer(t, self.inv_freq)
        emb = torch.cat([freqs, freqs], dim=-1)
        self.register_buffer("cos_cached", emb.cos())
        self.register_buffer("sin_cached", emb.sin())
    
    def forward(self, seq_len: int, device: torch.device = None):
        """
        获取指定长度的 cos/sin
        
        参数：
            seq_len: 序列长度
            device: 设备
            
        返回：
            cos, sin: [seq_len, head_dim]
        """
        if seq_len > self.cos_cached.shape[0]:
            self._build_cache(seq_len)
        
        cos = self.cos_cached[:seq_len]
        sin = self.sin_cached[:seq_len]
        
        if device is not None:
            cos = cos.to(device)
            sin = sin.to(device)
        
        return cos, sin
