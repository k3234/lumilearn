# LumiLearn V2 训练方法指南（脱敏版）

> 本文档完整记录 LumiLearn-V2（Qwen2.5-1.5B-Instruct + LoRA）的训练方法与过程，供复现与学习。
> **已脱敏**：不含服务器 IP、账号密码、本地路径等敏感信息。所有部署/训练命令均使用环境变量注入。

---

## 一、模型概览

| 项目 | 说明 |
|------|------|
| 基座模型 | Qwen2.5-1.5B-Instruct（约 15 亿参数） |
| 微调方式 | LoRA（r=16, alpha=32, dropout=0.05） |
| 训练设备 | CPU 训练（16 线程），无 GPU 依赖 |
| 训练数据 | 671 条真实高质量 SFT 数据（平均 333 字/条） |
| 数据格式 | instruction / response |
| 训练轮数 | 3 epochs |
| 最终 loss | 0.4057 |
| 产物 | LoRA adapter → 合并完整模型 → GGUF 量化（q8_0 / f16）→ Ollama 部署 |

---

## 二、训练数据构建

### 2.1 数据来源（4 类，671 条）

| 来源 | 数量 | 内容 |
|------|------|------|
| 云端 LLM 生成 SFT | 30 | 题目 + 详解的高质量问答 |
| 真实高一知识点 CSV | 628 | 人教A版各学科知识点（多模板指令重写） |
| 深度解析 Markdown | 12 | 数学深度解析（按章节拆分） |
| 四段式教学数据 | 1 | 完整教学流程 |

### 2.2 构建脚本

```bash
python scripts/build_training_data.py
# 输出：data/distil/train_data_high_quality.jsonl
```

### 2.3 数据质量要点（V1→V2 的关键改进）

- **V1（703 条合成模板）**：由模板拼接生成，回复是"模板级"质量
- **V2（671 条真实数据）**：来自真实教学资料，平均字数提升 3.4 倍，模型回复质量显著提升
- 同一真实知识点，通过 5 种不同指令模板改写，增强指令泛化能力

---

## 三、训练参数（实测有效）

| 参数 | 值 | 说明 |
|------|-----|------|
| max_length | 192 | 序列截断长度 |
| batch_size | 1 | 单样本批次 |
| gradient_accumulation | 8 | 有效 batch = 8 |
| epochs | 3 | 训练轮数 |
| dtype | bfloat16 | 与基座模型一致 |
| learning_rate | 2e-4 | AdamW |
| weight_decay | 0.01 | 权重衰减 |
| scheduler | CosineAnnealing | 余弦退火 |
| max_grad_norm | 1.0 | 梯度裁剪 |
| optimizer | AdamW | — |

### 训练耗时

- CPU 训练速度：约 1.3s/优化步
- 总耗时：约 70 分钟（671 条 × 3 epochs）
- loss：4.23 → 0.4057

---

## 四、训练过程中的关键经验（避坑指南）

### 4.1 ROCm / AMD 核显不可靠

- 实测 AMD 780M 核显（gfx1103，7.5GB）跑 3B 模型 FP16 训练**必挂**（GPU Hang / 无 traceback）
- **结论：CPU 训练是可靠路径**（R7-7840HS 16 线程足够）
- 强制 CPU：设置 `HIP_VISIBLE_DEVICES=-1` 和 `CUDA_VISIBLE_DEVICES=""`

### 4.2 attention 实现必须用 eager

- ROCm 环境 `attn_implementation="sdpa"` 不兼容，必须用 `"eager"`

### 4.3 DataLoader batch 维度坑

- tokenizer 返回 `[1, seq]`，DataLoader 再叠一层会变成 `[1, 1, seq]`
- **修复**：自定义 `collate_fn` 用 `torch.cat` 合并

### 4.4 CPU 训练禁用 gradient_checkpointing

- CPU + LoRA + gradient checkpointing 会导致 loss 无梯度
- CPU 内存充足，应禁用

### 4.5 合并模型必须用 bf16

- `merge_and_test.py` 必须用 `torch_dtype=torch.bfloat16`（与训练一致）
- fp16 会因 bf16 数值范围溢出产生 NaN 概率错误

### 4.6 bitsandbytes 4-bit 量化放弃

- bitsandbytes ROCm 二进制 ABI 不兼容（加载即 Segfault）
- 改用 GGUF 量化路线（q8_0 / f16）

---

## 五、训练 → 合并 → 部署全流程

### 5.1 LoRA 训练

```bash
python scripts/train_lora_gpu.py
# 需要环境变量指定数据路径（脚本默认相对路径）
```

### 5.2 合并 adapter 为完整模型

```bash
python scripts/merge_and_test.py \
    --base <BASE_MODEL_PATH> \
    --adapter models/distil/adapter_merged_v2 \
    --output models/distil/merged_model_15b_v2
```

### 5.3 转换 GGUF（Ollama 可用格式）

> 使用 llama.cpp 的 convert_hf_to_gguf.py（b4300 单文件版最稳）

```bash
# f16 精度（约 3.1GB）
python scripts/convert_hf_to_gguf_old.py models/distil/merged_model_15b_v2 \
    --outfile models/distil/lumilearn-v2-f16.gguf --outtype f16

# q8_0 量化（约 1.6GB，推荐部署）
python scripts/convert_hf_to_gguf_old.py models/distil/merged_model_15b_v2 \
    --outfile models/distil/lumilearn-v2-q8_0.gguf --outtype q8_0
```

### 5.4 注册到 Ollama

```bash
# Modelfile
FROM /path/to/lumilearn-v2-q8_0.gguf

TEMPLATE """{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{- end }}
<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""

PARAMETER temperature 0.7
PARAMETER top_p 0.8
PARAMETER num_ctx 4096

# 创建模型
ollama create lumilearn-v2 -f Modelfile
```

### 5.5 远程服务器部署

> 服务器信息通过环境变量注入，不写死在代码中

```bash
# PowerShell
$env:REMOTE_HOST='服务器IP'; $env:REMOTE_USER='用户名'; $env:REMOTE_PASSWORD='密码'
python scripts/_upload_gguf.py     # 上传 GGUF
python scripts/_deploy_ollama_remote.py  # 注册到 Ollama
```

### 5.6 应用侧配置

```bash
# lumilearn_agent / lumilearn_web 通过环境变量指定 Ollama 地址
$env:OLLAMA_URL='http://<ollama_host>:11434'
```

---

## 六、模型质量评估

### 6.1 推理性能（远程服务器 CPU，q8_0）

| 指标 | 值 |
|------|-----|
| 推理速度 | 26.4 tok/s |
| 模型大小 | 1.6 GB（q8_0） |

### 6.2 学科回答质量（关键词命中率）

| 学科 | 命中率 |
|------|--------|
| 数学（勾股定理） | ✅ 完整步骤（【问题分析】【模型构建】【公式推导】） |
| 化学（共价键） | ✅ 正确分类 + 详解 |
| 物理（牛顿定律） | ✅ 定律内容 + 公式 |
| 生物（光合作用） | ✅ 四阶段 |

### 6.3 与旧版对比

- V1（合成模板数据）：模板级回复
- V2（真实数据）：结构化、多步骤、正确率高
- **结论：数据质量是模型质量的关键**，而非参数量或训练时长

---

## 七、可复现性说明

1. **数据**：构建脚本 `scripts/build_training_data.py` 已开源，替换为你的教学数据即可
2. **训练**：`scripts/train_lora_gpu.py` 已开源，CPU/GPU 均可运行
3. **合并/转换/部署**：脚本均开源，按上文流程执行
4. **基座模型**：Qwen2.5-1.5B-Instruct（可改用 3B/7B，内存允许即可）

> 完整模型权重文件体积较大（GGUF q8_0 约 1.6GB / f16 约 3.1GB），不在 Git 仓库中直接托管，请按 5.3-5.5 节流程自行转换部署。
