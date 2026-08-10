# LumiLearn 模型对照表

> 最后更新: 2026-08-10

## 一、总览

| 模型名称 | 架构 | 参数量 | 量化 | 大小 | 存储位置 | 部署状态 | 质量 |
|---------|------|-------|------|------|---------|---------|------|
| **lumilearn-v2:latest** | Qwen2 | 1.5B | Q8_0 | 1.65 GB | 天虹 Ollama + 本地 GGUF | ✅ 生产运行 | ★★★★★ |
| **lumilearn-v2-f16** | Qwen2 | 1.5B | F16 | 3.09 GB | 本地 GGUF | ⏸ 未使用 | ★★★★★ |
| **merged_model_15b_v2** | Qwen2 | 1.5B | bf16 | 2.87 GB | 本地 HuggingFace | ⏸ 未使用 | ★★★★★ |
| **merged_model_15b** | Qwen2 | 1.5B | bf16 | 2.87 GB | 本地 HuggingFace | ⏸ 未使用 | ★★☆☆☆ |
| **lumilearn-merged** | Qwen2 | 3.1B | F16 | 6.18 GB | 天虹 Ollama | ⏸ 未使用 | ★★★☆☆ |
| **qwen2.5:7b** | Qwen2 | 7.6B | Q4_K_M | 4.68 GB | 天虹 Ollama | ✅ 备用 | ★★★★☆ |
| **lumilearn-v5:real** | Llama | 33.27M | — | 133 MB | 天虹 Ollama | ⏸ 保留 | ★☆☆☆☆ |
| **lumilearn-v5:latest** | GPT-2 | 27.32M | — | 110 MB | 天虹 Ollama | ⏸ 保留 | ★☆☆☆☆ |
| **lumilearn-v5:test** | GPT-2 | 21.01M | — | 84 MB | 天虹 Ollama | ⏸ 保留 | ★☆☆☆☆ |
| **lumilearn-v4-tianhong** | Llama | 23.38M | — | 94 MB | 天虹 Ollama | ⏸ 保留 | ★☆☆☆☆ |
| **lumilearn-v3** | Llama | 23.38M | — | 94 MB | 天虹 Ollama | ⏸ 保留 | ★☆☆☆☆ |

## 二、模型大小对比

```
lumilearn-v2:latest   (1.5B Q8_0)  ████████████████████████████░░░░  1.65 GB
lumilearn-v2-f16      (1.5B F16)   ██████████████████████████████████████████████████░░  3.09 GB
merged_model_15b_v2   (1.5B bf16)  ████████████████████████████████████████████████░░░░  2.87 GB
merged_model_15b      (1.5B bf16)  ████████████████████████████████████████████████░░░░  2.87 GB
lumilearn-merged      (3.1B F16)   ████████████████████████████████████████████████████████████████████████████████████  6.18 GB
qwen2.5:7b            (7.6B Q4)    ████████████████████████████████████████████████████████████████████████████████████░░  4.68 GB
lumilearn-v5:real     (33M)        ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  133 MB
```

## 三、训练数据来源

| 模型 | 基座模型 | 训练数据 | 数据量 | 训练方式 |
|------|---------|---------|-------|---------|
| lumilearn-v2 | Qwen2.5-1.5B-Instruct | 真实教学问答（CSV + SFT + 教材） | 671 条 | LoRA, 3 epochs, bf16 |
| lumilearn-v1 | Qwen2.5-1.5B-Instruct | 合成模板数据 | 703 条 | LoRA, 3 epochs, bf16 |
| lumilearn-merged | Qwen2.5-1.5B-Instruct | 早期实验 | — | 早期 LoRA |
| lumilearn-v5 | 自训练极小模型 | 极小规模实验数据 | — | 从零训练 |
| qwen2.5:7b | — | 通义千问官方预训练 | — | 官方预训练 |

## 四、推理性能

| 模型 | 推理速度 (tok/s) | 硬件 | 延迟 |
|------|-----------------|------|------|
| **lumilearn-v2:latest** (Q8_0) | **26.4 tok/s** | 天虹 CPU (R7-7840HS) | ~38ms/tok |
| lumilearn-v2-f16 (F16) | ~9.7 tok/s | 天虹 CPU | ~103ms/tok |
| qwen2.5:7b (Q4_K_M) | ~8-12 tok/s | 天虹 CPU | ~80-125ms/tok |
| merged_model_15b_v2 (bf16) | ~8 tok/s | 天虹 CPU | ~125ms/tok |
| merged_model_15b_v2 (bf16) | 1-3 tok/s | 本地 CPU | ~300-1000ms/tok |

## 五、推荐使用场景

```
┌─────────────────────────────────────────────────────────────────────┐
│  场景                    │  推荐模型              │  原因             │
├─────────────────────────────────────────────────────────────────────┤
│  日常学习问答             │  lumilearn-v2:latest   │  最快 + 质量最高  │
│  复杂推理/数学            │  qwen2.5:7b            │  参数量更大        │
│  教学演示/展示            │  lumilearn-v2:latest   │  专为教学微调      │
│  本地离线使用             │  lumilearn-v2-q8_0.gguf│  1.65GB, 可本地跑  │
│  快速原型验证             │  lumilearn-v5 系列     │  < 133MB, 启动快   │
│  模型继续训练/微调         │  merged_model_15b_v2   │  HuggingFace 格式   │
└─────────────────────────────────────────────────────────────────────┘
```

## 六、文件清单

### 本地文件（`models/distil/`）

```
models/distil/
├── lumilearn-v2-q8_0.gguf          # 主力模型 GGUF Q8_0 (1.65 GB)
├── lumilearn-v2-f16.gguf           # 高精度 GGUF F16 (3.09 GB)
├── merged_model_15b_v2/            # V2 合并模型 HuggingFace (2.87 GB)
│   ├── config.json
│   ├── model.safetensors
│   ├── tokenizer.json
│   └── ...
└── merged_model_15b/               # V1 合并模型 HuggingFace (2.87 GB)
    ├── config.json
    ├── model.safetensors
    ├── tokenizer.json
    └── ...
```

### 天虹服务器 Ollama

```
ollama list
├── lumilearn-v2:latest          # 主力 (1.65 GB, Q8_0, Qwen2-1.5B)
├── lumilearn-merged:latest      # 早期合并 (6.18 GB, F16, Qwen2-3.1B)
├── qwen2.5:7b                   # 备用 (4.68 GB, Q4_K_M, Qwen2-7.6B)
├── lumilearn-v5:real            # 保留 (133 MB, Llama-33M)
├── lumilearn-v5:latest          # 保留 (110 MB, GPT2-27M)
├── lumilearn-v5:test            # 保留 (84 MB, GPT2-21M)
├── lumilearn-v4-tianhong:latest # 保留 (94 MB, Llama-23M)
└── lumilearn-v3:latest          # 保留 (94 MB, Llama-23M)
```