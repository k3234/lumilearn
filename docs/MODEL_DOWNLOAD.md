# LumiLearn 模型下载与导入指南

> LumiLearn 核心教学模型为 `lumilearn-v2`（Qwen2.5-1.5B-Instruct 教学微调 + Q8_0 量化）。
> 模型文件较大，**不随代码仓库分发**，按本指南获取。

## 一、模型文件清单

| 文件 | 说明 | 大小 | 用途 |
|---|---|---|---|
| `lumilearn-v2-q8_0.gguf` | Q8_0 量化 | ≈1.64 GB | **部署首选**，CPU 推理 26.4 tok/s |
| `lumilearn-v2-f16.gguf` | FP16 原精度 | ≈3.09 GB | 需要更高精度时使用 |
| `merged_model_15b_v2/` | LoRA 合并后的 HF 完整模型（bf16） | ≈2.89 GB | 复现/二次微调用 |

> 文件位于项目 `models/distil/`（`.gitignore` 已排除，不入库）。

## 二、获取方式

### 方式 A：已有合并且转换过的模型

从你的训练环境/共享存储直接拷贝 `models/distil/*.gguf` 到目标机 `models/distil/` 即可。

### 方式 B：从模型库下载基座模型后微调（复现路径）

```bash
# 1. 下载 Qwen2.5-1.5B-Instruct（ModelScope / HuggingFace）
pip install modelscope
modelscope download --model Qwen/Qwen2.5-1.5B-Instruct --local_dir ./qwen2.5-1.5b

# 2. LoRA 微调（CPU 可跑，约 70 分钟/轮，见 scripts/train_lora_gpu.py 的 CPU 模式说明）
python3 scripts/train_lora_gpu.py          # 数据: training_data/ 671 条

# 3. 合并 LoRA adapter
python3 scripts/merge_and_test.py          # 必须 torch_dtype=bfloat16

# 4. GGUF 转换（b4300 单文件版，支持 f32/f16/bf16/q8_0）
python3 scripts/convert_hf_to_gguf_old.py --outtype q8_0 \
    --outfile models/distil/lumilearn-v2-q8_0.gguf ./merged_model_15b_v2
```

### 方式 C：完全从零训练自研微型模型（8M）

数据与脚本均在仓库内（`framework/model.py`、`scripts/train_cpu.py`、`data_management/`），纯 CPU 约 46 分钟/轮，用于教学演示"从数据到模型"完整流程。

## 三、导入 Ollama

1. 创建 Modelfile（Qwen im_start 对话模板）：

```bash
FROM ./lumilearn-v2-q8_0.gguf

TEMPLATE """{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>{{ end }}<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
PARAMETER num_predict 512
```

2. 导入并验证：

```bash
ollama create lumilearn-v2 -f Modelfile
ollama list                      # 确认 lumilearn-v2 出现
ollama run lumilearn-v2 "用一句话解释什么是力"
```

3. 在系统内启用：Admin 面板「模型管理 → 端口模型配置」为各端口选择 `lumilearn-v2`，或设置环境变量 `OLLAMA_MODEL=lumilearn-v2`。

## 四、模型路由与降级

| 场景 | 行为 |
|---|---|
| 已导入 `lumilearn-v2` | 各端口按配置使用，CPU 推理 2-6s/次 |
| 未导入但 Ollama 有其他模型 | Admin 端口模型配置可切换（如 `qwen2.5:1.5b`） |
| 无任何模型 | 自动降级**模板兜底教学**（费曼五步结构完整），流程可跑通 |

> ⚠️ CPU 环境请避免使用 7B 及以上模型（单次推理可达 60s+），`lumilearn-v2`（1.5B）是最佳平衡。
