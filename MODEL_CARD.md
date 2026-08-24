# Model Card — LumiLearn-V2

> LumiLearn-V2 是一个用于高中教育问答的 SFT 微调模型，基于 Qwen2.5-1.5B-Instruct。
> 由一名高中学生基于真实教学资料构建训练数据并完成 CPU 微调。

## 基本信息

| 字段 | 值 |
|------|-----|
| 模型名称 | lumilearn-v2 |
| 基座模型 | Qwen2.5-1.5B-Instruct |
| 参数量 | ~1.5B |
| 微调方法 | LoRA（r=16, alpha=32, dropout=0.05） |
| 训练设备 | CPU（16 线程，无 GPU） |
| 训练数据 | 671 条真实高质量 SFT 数据 |
| 训练轮数 | 3 epochs |
| 最终训练 loss | 0.4057 |
| 输入格式 | ChatML（`<|im_start|>` / `<|im_end|>`） |
| 语言 | 中文（高中数/理/化/生/语文等学科） |
| 许可证 | MIT（基座模型遵循 Qwen 开源协议） |

## 量化版本

| 版本 | 精度 | 大小 | 用途 |
|------|------|------|------|
| lumilearn-v2:q8_0 | Q8_0 | ~1.6 GB | 推荐部署，CPU 推理 26+ tok/s |
| lumilearn-v2:f16 | F16 | ~3.1 GB | 更高精度，内存充足时使用 |

## 能力

- 高中学科知识讲解（数学 / 物理 / 化学 / 生物 / 语文）
- 结构化回答（【问题分析】【模型构建】【公式推导】等步骤）
- 费曼教学法风格讲解

## 限制

- 基于 671 条 SFT 数据的领域微调，**通用能力有限**
- 适合教育问答场景演示，不适用于专业领域问答
- 可能存在幻觉，重要信息需人工核验

## 获取方式

> 模型权重文件较大（1.6~3.1GB），不在 Git 仓库中托管。可自行按 [训练方法指南](docs/research/TRAINING_METHOD_GUIDE_20260808.md) 复现，或通过部署脚本转换生成。

### 方式一：自行复现训练（推荐）

```bash
# 1. 构建训练数据（替换为自己的教学数据）
python scripts/build_training_data.py

# 2. LoRA 训练
python scripts/train_lora_gpu.py

# 3. 合并完整模型
python scripts/merge_and_test.py

# 4. 转换 GGUF 并注册到 Ollama
python scripts/convert_hf_to_gguf_old.py <model_dir> --outtype q8_0
ollama create lumilearn-v2 -f Modelfile
```

### 方式二：连接已有 Ollama 服务

通过环境变量指向已部署模型的 Ollama 服务：

```bash
# PowerShell
$env:OLLAMA_URL='http://<ollama_host>:11434'
python -c "from framework.engines.feynman_engine import FeynmanEngine; print(FeynmanEngine.run('讲解勾股定理'))"
```

## 部署后验证

```bash
# 健康检查
curl http://<ollama_host>:11434/api/tags

# 推理测试
curl -X POST http://<ollama_host>:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"lumilearn-v2","prompt":"用一句话解释勾股定理","stream":false}'
```

## 相关文档

- [训练方法指南（脱敏）](docs/research/TRAINING_METHOD_GUIDE_20260808.md)
- [模型开发现状评估](docs/research/MODEL_DEVELOPMENT_STATUS_20260807.md)
- [CPU 训练扩展计划](docs/superpowers/plans/2026-08-07-cpu-training-expansion.md)
