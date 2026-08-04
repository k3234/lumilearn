# LumiLearn 自研模型开发总结

> 最后更新: 2026-06-06

---

## 一、项目概述

**目标:** 在天虹服务器（<SERVER_IP>，14GB RAM，无 GPU）上训练一个专属的教学模型，集成到 LumiLearn 学习平台框架中。

**方案:** QLoRA 微调 Qwen2.5-3B-Instruct，使用费曼五步法教学数据，CPU-only 训练。

---

## 二、技术架构

```
┌─────────────────────────────────────────┐
│              模型开发管线                 │
├─────────────┬─────────────┬─────────────┤
│  数据层      │   训练层     │   推理层    │
│             │             │             │
│ data_factory│  trainer.py │ evaluate.py │
│ prompts.py  │ simple_train│ merge+test  │
│ *.jsonl     │ *.py        │ GGUF export │
└─────────────┴─────────────┴─────────────┘
```

**核心文件:**
| 文件 | 职责 |
|------|------|
| `models/distil/trainer.py` | 训练器（含自定义训练循环） |
| `models/distil/data_factory.py` | 数据工厂（生成/清洗/验证） |
| `models/distil/prompts.py` | 24 个费曼五步法提示模板 |
| `models/distil/evaluate.py` | 模型评估套件 |
| `scripts/generate_responses.py` | 用模型生成训练回复 |
| `scripts/train_real.py` | 简化训练脚本 |
| `merge_and_test.py` | 合并+推理测试 |

---

## 三、开发历程

### 阶段 1：框架搭建
- 部署 LumiLearn 框架到服务器
- 尝试加载 Qwen2.5-7B → **OOM**（7B FP16 ~15GB > 14GB 物理内存）
- 改用 Qwen2.5-3B-Instruct（~6GB FP16）

### 阶段 2：训练管线构建
- 创建数据工厂（`data_factory.py`）：80 条费曼教学数据
- 创建 24 个提示模板（`prompts.py`）
- 创建评估套件（`evaluate.py`）
- 初始训练数据使用 DRY RUN 占位符

### 阶段 3：OOM 问题攻克（3 次迭代）
| 尝试 | 问题 | 修复 |
|------|------|------|
| #1 | Trainer + 3B FP16 → 13.5GB | 移除 `device_map` + `low_cpu_mem_usage` |
| #2 | `prepare_model_for_kbit_training` | CPU 模式跳过该调用 |
| #3 | Trainer 框架开销大 | **自定义 PyTorch 训练循环** |

### 阶段 4：自定义训练循环
```python
# 替代 HuggingFace Trainer，手动控制 forward/backward
for batch in dataloader:
    outputs = model(**batch)
    loss = outputs.loss
    loss.backward()
    optimizer.step()
    scheduler.step()
    optimizer.zero_grad()
```
- 去掉 DataCollatorForSeq2Seq
- 添加梯度裁剪、学习率调度
- 内存从 13.5GB 降到 7.2GB

### 阶段 5：输出缓冲修复（2 次迭代）
| 问题 | 原因 | 修复 |
|------|------|------|
| tqdm 输出不刷新 | `tee` 命令缓冲 `\r` | 改用 `>>` 重定向 |
| batch 完成无日志 | stdout 缓冲 | 添加 `sys.stdout.flush()` + `print(flush=True)` |

### 阶段 6：CPU 性能诊断
**基准测试结果（单条 forward pass）:**
| 序列长度 | 耗时 |
|----------|------|
| 6 tokens | 10.8s |
| 256 tokens | **275.6s** |

**训练实测（per batch, 128 tokens）:**
| 阶段 | 每 batch | loss 范围 |
|------|----------|-----------|
| DRY RUN (5 条) | ~21 min | 3.80 → 1.26 |
| 真实数据 (3/10) | **~44 min** | 3.29 → 2.35 |

> 真实数据比 DRY RUN 慢 2 倍，因回复长度 500-700 字 vs DRY RUN 的 30 字

### 阶段 7：合并与推理验证
- LoRA adapter → `merge_and_unload()` → 保存完整模型（5.8GB）
- 推理速度：~0.8 tok/s（CPU）
- 5 题推理测试全部通过，回复质量良好

---

## 四、当前状态（2026-06-06）

**服务器正在训练:**
- PID 2274542，已运行 2 小时 18 分钟
- 进度: **3/10 batches (30%)**
- Loss: 3.29 → 2.75 → 2.35（持续下降）
- 剩余: ~5.1 小时
- 完成后自动保存 adapter 到 `models/distil/adapter/`

**训练参数:**
- 模型: Qwen2.5-3B-Instruct (FP16)
- 数据: 10 条真实费曼教学数据（从 80 条中抽取）
- LoRA: r=16, alpha=32, 7 个 target modules
- 配置: max_length=128, batch_size=1, 1 epoch
- 硬件: R7-7840HS CPU, 线程数=4

---

## 五、关键数据

| 指标 | 数值 |
|------|------|
| 模型大小 (base) | 5.8GB (FP16) |
| LoRA adapter | 115MB |
| 训练数据总量 | 80 条（4 学科） |
| 训练速度 (CPU) | ~44 min/batch (128 tokens) |
| 推理速度 (CPU) | ~0.8 tok/s |
| 服务器内存上限 | 14GB |
| 训练峰值内存 | ~11.4GB |
| 模型部署方式 | llamafile (计划 GGUF 转换) |

---

## 六、经验总结

### 踩过的坑
1. **7B 模型 OOM**: 14GB 内存不够，必须用 3B
2. **`device_map='cpu'` 内存膨胀**: 导致额外 7GB 开销
3. **HuggingFace Trainer 内存浪费**: 自定义训练循环节省 40% 内存
4. **tee 缓冲问题**: tqdm `\r` 不触发 tee 刷新，需用 `>>`
5. **CPU FP16 极慢**: 没有原生 FP16 加速，~1/6 GPU 速度
6. **Local vs Server 数据不同步**: 本地 12 条 DRY RUN，服务器 80 条真实数据

### 有效做法
1. **限制线程数**: `OMP_NUM_THREADS=4` + `torch.set_num_threads(4)` 避免争用
2. **paramiko SFTP**: 远程部署比 SSH heredoc 更可靠
3. **增量保存**: 生成/训练时逐条保存，防止中断丢失
4. **基准测试先行**: 先测 forward pass 速度，再估算训练时间
5. **小规模验证**: 5 条数据验证 → 10 条数据训练 → 80 条完整训练

---

## 七、下一步方向

- [ ] 完成当前 10-batch 训练 + 合并测试
- [ ] 扩展到 80 条完整训练（~35 小时）
- [ ] GGUF 量化转换 + llamafile 部署
- [ ] 集成到 LumiLearn 框架（`lumilearn_unified_auto.py`）
- [ ] 付费系统接入（`payment_service.py`，待模型能力达标后启用）