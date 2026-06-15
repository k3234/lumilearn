# 从零开始训练大模型完整实施计划

> **制定日期:** 2026-06-06
> **适用场景:** 完全从零开始，不依赖现有预训练模型，从数据准备到模型部署全流程

---

## 一、项目概述

### 目标
从零开始设计、训练并部署一个新的大语言模型，具备完整的预训练、微调、对齐、评测和部署能力。

### 核心架构
```
┌─────────────────────────────────────────────────────────────┐
│  从零开始训练大模型完整管线                                  │
├────────────┬────────────┬──────────┬────────────┬───────────┤
│  阶段 1    │  阶段 2    │  阶段 3  │  阶段 4    │  阶段 5   │
│            │            │          │            │           │
│  数据层    │  架构层    │  训练层  │  对齐层    │  部署层   │
│ (40%)      │ (15%)      │ (25%)    │ (15%)      │ (5%)      │
└────────────┴────────────┴──────────┴────────────┴───────────┘
```

### 技术栈
| 组件 | 推荐选型 |
|------|----------|
| 数据处理 | Python + Apache Spark (可选) |
| 框架 | PyTorch + DeepSpeed (或 Megatron-LM) |
| 分词器 | 自定义 SentencePiece 或 HuggingFace Tokenizers |
| 分布式训练 | DeepSpeed / Megatron-LM / LoRA (可选) |
| 评估 | LM Evaluation Harness + 自定义评测集 |
| 部署 | vLLM / TGI / llamafile |

---

## 二、分阶段实施计划

### 阶段 1：数据准备与预处理（40% 工作量）

**核心原则：数据质量 > 数据数量**

#### Task 1.1：数据收集与多元化配比
```
目标数据规模：
├─ 1-10B 参数量级：100-500GB 纯文本（Token数 ~100B）
├─ 30-70B 参数量级：500GB-2TB 纯文本（Token数 ~300B）
└─ 100B+ 参数量级：2TB+ 纯文本（Token数 ~500B+）

数据配比建议：
├─ 网络爬虫数据（CommonCrawl、WebText2）：~60-70%
├─ 图书数据（Project Gutenberg、ArXiv）：~15-20%
├─ 代码数据（GitHub、StackOverflow）：~10-15%
└─ 对话/指令数据（可选，早期预训练不加入）：0%
```

**关键文件：**
- [data/collection/web_crawler.py](file:///e:/学习LLM/lumilearn/data/collection/web_crawler.py)
- [data/collection/book_scraper.py](file:///e:/学习LLM/lumilearn/data/collection/book_scraper.py)
- [data/collection/code_scraper.py](file:///e:/学习LLM/lumilearn/data/collection/code_scraper.py)

- [ ] **Step 1: 配置数据下载源与爬取器**
  ```python
  # data/collection/config.py
  DATA_SOURCES = {
      "commoncrawl": {"url": "https://commoncrawl.org", "max_size": "300GB"},
      "webtext2": {"url": "https://openwebtext2.readthedocs.io", "max_size": "200GB"},
      "gutenberg": {"url": "https://www.gutenberg.org", "max_size": "50GB"},
      "arxiv": {"url": "https://arxiv.org", "max_size": "100GB"},
      "github": {"url": "https://github.com", "languages": ["Python", "C++", "JavaScript"], "max_size": "100GB"}
  }
  ```
- [ ] **Step 2: 并行下载多源数据**
  ```bash
  python data/collection/web_crawler.py --output /data/raw/
  python data/collection/book_scraper.py --output /data/raw/books/
  python data/collection/code_scraper.py --output /data/raw/code/
  ```
- [ ] **Step 3: 数据去重与数据清洗**
  ```python
  # data/cleaning/dedup.py - 基于minhash去重
  # data/cleaning/clean.py - 去噪、去广告、去低质量内容
  from fuzzywuzzy import fuzz
  def minhash_dedup(texts):
      # 快速去重算法：minhash + LSH
      pass
  ```
- [ ] **Step 4: 数据配比与混合**
  ```python
  # data/mixture/mixture.py
  MIXTURE_RATIOS = {
      "web": 0.7, "books": 0.15, "code": 0.15
  }
  ```

#### Task 1.2：分词器训练
```
目标：训练专属 SentencePiece 分词器
├─ 词汇表大小：32k-128k（根据模型规模）
├─ 覆盖：多语言（如中文+英文+代码）
└─ 格式：与 HuggingFace Transformers 兼容
```

**关键文件：**
- [tokenizer/train_tokenizer.py](file:///e:/学习LLM/lumilearn/tokenizer/train_tokenizer.py)
- [tokenizer/tokenizer.json](file:///e:/学习LLM/lumilearn/tokenizer/tokenizer.json)

- [ ] **Step 1: 准备分词器训练语料（1-10GB 混合文本）**
- [ ] **Step 2: 训练 SentencePiece 分词器**
  ```python
  import sentencepiece as spm
  spm.SentencePieceTrainer.train(
      input='/data/processed/tokenizer_corpus.txt',
      model_prefix='lumilearn_tokenizer',
      vocab_size=65536,
      character_coverage=0.9995,
      model_type='bpe',
      user_defined_symbols=['<|im_start|>', '<|im_end|>', '<|end_of_text|>']
  )
  ```
- [ ] **Step 3: 转换为 HuggingFace Tokenizer 格式**
- [ ] **Step 4: 分词器覆盖率测试**
  ```bash
  python tokenizer/verify_tokenizer.py
  ```

#### Task 1.3：预训练数据格式化为训练样本
```
格式：
  原始文本 -> 分词 -> 滑动窗口分块 -> 转换为训练样本
  每个样本长度：512/1024/2048/4096 tokens（取决于设计）
  样本格式：{"input_ids": [...], "labels": [...]}
```

**关键文件：**
- [data/processing/prepare_pretrain_data.py](file:///e:/学习LLM/lumilearn/data/processing/prepare_pretrain_data.py)

- [ ] **Step 1: 切分文本为滑动窗口块**
  ```python
  def sliding_window_chunks(
      text_tokens: list[int], chunk_size: int=2048, overlap: int=0
  ):
      chunks = []
      for i in range(0, len(text_tokens), chunk_size-overlap):
          chunks.append(text_tokens[i:i+chunk_size])
      return chunks
  ```
- [ ] **Step 2: 转换为 PyTorch Dataset 格式**
- [ ] **Step 3: 存储为 Memory-Mapped 格式（MMAP）用于高效加载**

---

### 阶段 2：模型架构设计与实现（15% 工作量）

#### Task 2.1：定义模型配置
```
核心设计决策：
├─ 模型规模：1B、3B、7B、13B、70B（选择 1 个初始目标）
├─ 层设计：Transformer Decoder 架构（纯自回归）
├─ 归一化：RMSNorm（默认）或 LayerNorm
├─ 注意力：MQA / GQA / Multi-Head（初始用 MHA，优化可用 MQA）
├─ 激活：GELU / SwiGLU / FFNSwiGLU
└─ 位置编码：RoPE（旋转位置编码）
```

**关键文件：**
- [models/configs/model_config.py](file:///e:/学习LLM/lumilearn/models/configs/model_config.py)
- [models/modeling_lumilearn.py](file:///e:/学习LLM/lumilearn/models/modeling_lumilearn.py)

- [ ] **Step 1: 配置模型超参数**
  ```python
  # 3B 参数量级示例配置
  LUMILEARN_3B_CONFIG = {
      "vocab_size": 65536,
      "hidden_size": 3072,
      "num_hidden_layers": 32,
      "num_attention_heads": 24,
      "num_key_value_heads": 8,  # GQA
      "intermediate_size": 8192,
      "max_position_embeddings": 8192,
      "norm_eps": 1e-05,
      "hidden_act": "silu",  # SwiGLU
      "rope_theta": 10000.0
  }
  ```
- [ ] **Step 2: 实现 Transformer Decoder 核心组件**
  ```python
  class RMSNorm(nn.Module): pass
  class RotaryEmbedding(nn.Module): pass
  class Attention(nn.Module): pass
  class MLP(nn.Module): pass
  class TransformerBlock(nn.Module): pass
  ```
- [ ] **Step 3: 完整模型类实现**
  ```python
  class LumiLearnForCausalLM(nn.Module):
      def __init__(self, config):
          self.embeddings = nn.Embedding(...)
          self.layers = nn.ModuleList([TransformerBlock(...) for _ in range(config.num_hidden_layers)])
          self.norm = RMSNorm(config.hidden_size)
          self.lm_head = nn.Linear(config.hidden_size, config.vocab_size, bias=False)
  ```
- [ ] **Step 4: 单元测试**
  ```bash
  pytest tests/test_model.py -v
  ```

---

### 阶段 3：预训练（25% 工作量）

#### Task 3.1：训练环境与基础设施
```
硬件需求评估：
├─ 1B-7B 参数量级：单台 8x A100/H100 GPU 服务器
├─ 7B-30B 参数量级：多机多卡（4-8 台，每台 8x GPU）
└─ 30B+ 参数量级：大规模分布式集群（16+ 服务器）

软件依赖：
├─ PyTorch >= 2.1.0
├─ DeepSpeed >= 0.13.0
├─ Accelerate >= 0.25.0
└─ FlashAttention >= 2.3.0
```

**关键文件：**
- [training/train_pretrain.py](file:///e:/学习LLM/lumilearn/training/train_pretrain.py)
- [training/deepspeed_config.json](file:///e:/学习LLM/lumilearn/training/deepspeed_config.json)

- [ ] **Step 1: 配置分布式训练（DeepSpeed 或 Megatron）**
- [ ] **Step 2: 配置训练参数**
  ```python
  # training/config.py
  TRAIN_CONFIG = {
      "learning_rate": 3e-4,
      "lr_scheduler_type": "cosine",
      "warmup_steps": 2000,
      "total_steps": 500000,
      "batch_size_per_gpu": 4,
      "grad_accumulation": 8,
      "weight_decay": 0.1,
      "max_grad_norm": 1.0
  }
  ```
- [ ] **Step 3: 训练循环实现**
  ```python
  # training/train_pretrain.py
  for step in range(total_steps):
      batch = next(data_loader)
      outputs = model(**batch)
      loss = outputs.loss
      loss.backward()
      # 梯度裁剪
      optimizer.step()
      scheduler.step()
      optimizer.zero_grad()
      # 评估+Checkpoint保存
  ```
- [ ] **Step 4: Checkpoint机制与训练监控**
  ```bash
  # 启动多机训练（示例）
  deepspeed --num_gpus=8 --num_nodes=4 training/train_pretrain.py
  ```

#### Task 3.2：预训练策略与课程学习
```
建议训练策略：
├─ 阶段 1：短上下文（512 tokens）+ 高学习率 0.0003 → 200k steps
├─ 阶段 2：长上下文（2048 tokens）+ 稍低学习率 → 200k steps
└─ 阶段 3：长上下文（4096-8192 tokens）+ 低学习率 → 100k steps
```

---

### 阶段 4：对齐与指令微调（15% 工作量）

#### Task 4.1：SFT（有监督微调）数据准备
```
目标数据量：10k-100k 指令-回复对
数据来源：
├─ 开源数据集：Flan、ShareGPT、UltraChat
├─ 合成数据：用更强的老师模型生成
└─ 垂直领域数据：教育内容（如果是教学模型）
```

**关键文件：**
- [data/sft/prepare_sft_data.py](file:///e:/学习LLM/lumilearn/data/sft/prepare_sft_data.py)
- [training/train_sft.py](file:///e:/学习LLM/lumilearn/training/train_sft.py)

- [ ] **Step 1: 准备 SFT 数据（使用 `<|im_start|>user/assistant` 格式）**
  ```json
  {
    "instruction": "用费曼五步法讲解勾股定理",
    "response": "1. 简单描述..."
  }
  ```
- [ ] **Step 2: 全参数或 LoRA SFT 微调**
- [ ] **Step 3: SFT 后的初步评估**

#### Task 4.2：RLHF/DPO（可选，能力进阶）
```
对齐流程（可选但强烈推荐）：
├─ 1. 标注排名数据（或用 AI 标注）
├─ 2. 训练 Reward Model（RM）
└─ 3. DPO/PPO 强化学习微调
```

---

### 阶段 5：评估与部署（5% 工作量）

#### Task 5.1：模型评估
```
评估维度：
├─ 知识能力：MMLU、CMMLU
├─ 推理能力：GSM8K（数学）、HumanEval（代码）
├─ 对话能力：MT-Bench
└─ 垂直能力：如果是教学模型，自定义教学评测集
```

**关键文件：**
- [evaluation/run_evals.py](file:///e:/学习LLM/lumilearn/evaluation/run_evals.py)

- [ ] **Step 1: 集成 LM Evaluation Harness**
- [ ] **Step 2: 基准评估与对比**
  ```bash
  python evaluation/run_evals.py --checkpoint /checkpoints/lumilearn-v1/
  ```

#### Task 5.2：模型压缩与部署
```
部署路径选择：
├─ 路径 A：全精度/半精度推理（vLLM/TGI）
├─ 路径 B：量化到 GGUF（llama.cpp/llamafile）
└─ 路径 C：API 服务（FastAPI + vLLM）
```

**关键文件：**
- [deployment/export_model.py](file:///e:/学习LLM/lumilearn/deployment/export_model.py)
- [deployment/server.py](file:///e:/学习LLM/lumilearn/deployment/server.py)

- [ ] **Step 1: 模型保存与转换为 GGUF 格式**
  ```python
  # deployment/export_gguf.py
  from ctransformers import GGUFConfig
  config = GGUFConfig(quantization='Q4_K_M')
  model = AutoModelForCausalLM.from_pretrained(...)
  model.save_gguf('/output/lumilearn-v1.gguf', config)
  ```
- [ ] **Step 2: 部署本地/在线推理服务**
  ```python
  # deployment/server.py
  from fastapi import FastAPI
  app = FastAPI()
  @app.post('/v1/chat/completions')
  def chat():
      pass
  ```

---

## 三、时间与资源估算

### 人员与时间
| 阶段 | 单团队（3-5 人） | 小团队（1-2 人） |
|------|-------------------|------------------|
| 数据准备 | 1-2 个月 | 2-4 个月 |
| 架构实现 | 0.5-1 个月 | 1-2 个月 |
| 预训练 | 1-3 个月（取决于规模+硬件） | 2-6 个月 |
| SFT + 对齐 | 0.5-1 个月 | 1-2 个月 |
| 评估部署 | 0.5 个月 | 1 个月 |
| **总计** | **3.5-8 个月** | **7-15 个月** |

### 硬件成本估算
| 目标规模 | 推荐配置 | 成本估算 |
|----------|----------|----------|
| 1-3B | 8x A100 (40GB) | 云服务 ~¥1-3万/月 |
| 7-13B | 多机 16-32x A100 | 云服务 ~¥5-10万/月 |
| 70B+ | 大规模集群 | 自建或云服务，成本极高 |

---

## 四、风险与注意事项

1. **成本风险**：大模型预训练成本极贵（GPU 集群、电费、人力），3B 模型全从零开始通常 >¥100 万
2. **数据风险**：低质量数据训练出低质量模型，数据准备是重中之重
3. **技术风险**：单卡训练不现实，必须分布式并行，DeepSpeed/Megatron 的调试有门槛
4. **替代路径**：建议**不要纯从零开始**，先在现有基座上微调，验证产品价值后再投入纯预训练

---

## 五、下一步行动

1. **评估是否真需要从零开始**：建议先用 LumiLearn 现有 QLoRA 微调验证教学产品需求
2. **小规模验证全流程**：用 100M 参数小模型走通一遍：数据→模型→训练→部署
3. **硬件与资源规划**：如果确实要做大，规划 GPU 集群（或云服务预算）
4. **逐步迭代**：先做教学领域的 1-3B 专业模型，再逐步扩大

---

**计划文档保存位置：** [docs/superpowers/plans/2026-06-06-train-llm-from-scratch.md](file:///e:/学习LLM/lumilearn/docs/superpowers/plans/2026-06-06-train-llm-from-scratch.md)

