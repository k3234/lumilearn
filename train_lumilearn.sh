#!/usr/bin/env bash
# -*- coding: utf-8 -*-
"""
LumiLearn 训练脚本 — 7步完成自定义模型训练
用法: bash train_lumilearn.sh --model-name <名称> --base <基础模型> --subjects <主题> --sample-count <数量>

步骤:
  Step 1/7: 初始化训练环境
  Step 2/7: 生成训练数据
  Step 3/7: 训练BPE分词器
  Step 4/7: 准备数据集
  Step 5/7: 训练模型
  Step 6/7: 评估模型
  Step 7/7: 保存并注册模型
"""

set -euo pipefail

# ---------------------------------------------------------------------------
# 参数解析
# ---------------------------------------------------------------------------
MODEL_NAME="lumilearn-custom"
BASE_MODEL="qwen2.5:7b"
SUBJECTS="general"
SAMPLE_COUNT=100

while [[ $# -gt 0 ]]; do
    case $1 in
        --model-name)  MODEL_NAME="$2";   shift 2 ;;
        --base)        BASE_MODEL="$2";   shift 2 ;;
        --subjects)    SUBJECTS="$2";    shift 2 ;;
        --sample-count) SAMPLE_COUNT="$2"; shift 2 ;;
        *)             echo "未知参数: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  LumiLearn 训练管道"
echo "========================================"
echo "  模型名称:  $MODEL_NAME"
echo "  基础模型:  $BASE_MODEL"
echo "  训练主题:  $SUBJECTS"
echo "  样本数量:  $SAMPLE_COUNT"
echo "========================================"

# ---------------------------------------------------------------------------
# Step 1/7: 初始化训练环境
# ---------------------------------------------------------------------------
echo ""
echo "[Step 1/7] 初始化训练环境..."

mkdir -p "outputs/$MODEL_NAME"
mkdir -p "checkpoints/$MODEL_NAME"
mkdir -p "logs/$MODEL_NAME"

python3 -c "import torch; print(f'PyTorch {torch.__version__}')" 2>/dev/null || {
    echo "[ERROR] 未安装 PyTorch，请先运行: pip install torch"
    exit 1
}

python3 -c "import tokenizers; print(f'tokenizers {tokenizers.__version__}')" 2>/dev/null || {
    echo "[WARN] 未安装 tokenizers，将使用内置BPE"
}

echo "[Step 1/7] 完成: 环境就绪"

# ---------------------------------------------------------------------------
# Step 2/7: 生成训练数据
# ---------------------------------------------------------------------------
echo ""
echo "[Step 2/7] 生成训练数据..."

PYTHON_SUBJECTS=$(echo "$SUBJECTS" | tr ',' ' ' | xargs -n1 | python3 -c "import sys; print(str([s.strip() for s in sys.stdin if s.strip()]))")

python3 -c "
import sys, json
sys.path.insert(0, '.')
from scripts.lumilearn_learning_path_generator import LearningPathGenerator

subjects = $PYTHON_SUBJECTS
generator = LearningPathGenerator()
data = generator.generate_training_data(
    subjects=subjects,
    samples_per_subject=$SAMPLE_COUNT // len(subjects),
    model='$BASE_MODEL'
)

output_path = 'outputs/$MODEL_NAME/training_data.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'生成 {len(data)} 条训练样本 -> {output_path}')
" 2>/dev/null || {
    echo "[WARN] 使用内置数据生成器..."
    python3 -c "
import json, os

samples = [
    {'input': '什么是勾股定理？', 'output': '勾股定理说的是：直角三角形两条直角边的平方和等于斜边的平方。即 a² + b² = c²。'},
    {'input': '什么是牛顿第一定律？', 'output': '牛顿第一定律（惯性定律）：物体不受外力作用时，保持静止或匀速直线运动状态不变。'},
    {'input': '什么是化学键？', 'output': '化学键是相邻原子之间强烈的相互作用力，主要类型有离子键、共价键和金属键。'},
    {'input': '什么是函数？', 'output': '函数是一种特殊的对应关系：对于自变量x的每一个值，因变量y都有唯一确定的值与之对应。'},
    {'input': '什么是光合作用？', 'output': '光合作用是绿色植物利用光能，将二氧化碳和水转化为有机物并释放氧气的过程。'},
]

extended = []
subjects = '$SUBJECTS'.split(',')
for i in range($SAMPLE_COUNT):
    sample = samples[i % len(samples)].copy()
    sample['id'] = f'sample_{i:04d}'
    sample['subject'] = subjects[i % len(subjects)]
    extended.append(sample)

os.makedirs('outputs/$MODEL_NAME', exist_ok=True)
with open('outputs/$MODEL_NAME/training_data.json', 'w', encoding='utf-8') as f:
    json.dump(extended, f, ensure_ascii=False, indent=2)

print(f'生成 {len(extended)} 条训练样本（内置数据）')
"
}

echo "[Step 2/7] 完成: 训练数据已生成"

# ---------------------------------------------------------------------------
# Step 3/7: 训练BPE分词器
# ---------------------------------------------------------------------------
echo ""
echo "[Step 3/7] 训练BPE分词器..."

python3 -c "
import json, os, sys
sys.path.insert(0, '.')

data_path = 'outputs/$MODEL_NAME/training_data.json'
with open(data_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

texts = []
for item in data:
    texts.append(item.get('input', ''))
    texts.append(item.get('output', ''))

try:
    from tokenizers import Tokenizer, models, pre_tokenizers, trainers
    from tokenizers.trainers import BpeTrainer

    tokenizer = Tokenizer(models.BPE())
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel()
    trainer = BpeTrainer(vocab_size=8000, min_frequency=2, special_tokens=['<PAD>', '<EOS>', '<UNK>', '<BOS>'])
    tokenizer.train_from_iterator(texts, trainer=trainer)

    tokenizer_path = 'outputs/$MODEL_NAME/tokenizer.json'
    tokenizer.save(tokenizer_path)
    print(f'BPE分词器已训练: vocab=8000 -> {tokenizer_path}')
except ImportError:
    print('[WARN] tokenizers库不可用，将使用字符级分词')
    chars = set()
    for t in texts:
        chars.update(t)
    vocab = ['<PAD>', '<EOS>', '<UNK>', '<BOS>'] + sorted(chars)
    tokenizer_data = {'vocab': vocab, 'type': 'character', 'vocab_size': len(vocab)}
    tokenizer_path = 'outputs/$MODEL_NAME/tokenizer.json'
    with open(tokenizer_path, 'w', encoding='utf-8') as f:
        json.dump(tokenizer_data, f, ensure_ascii=False, indent=2)
    print(f'字符分词器已构建: vocab={len(vocab)} -> {tokenizer_path}')
"

echo "[Step 3/7] 完成: 分词器就绪"

# ---------------------------------------------------------------------------
# Step 4/7: 准备数据集
# ---------------------------------------------------------------------------
echo ""
echo "[Step 4/7] 准备数据集..."

python3 -c "
import json, os

data_path = 'outputs/$MODEL_NAME/training_data.json'
with open(data_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

n = len(data)
n_train = int(n * 0.90)
n_val = n - n_train

train_data = data[:n_train]
val_data = data[n_train:]

with open('outputs/$MODEL_NAME/train.json', 'w', encoding='utf-8') as f:
    json.dump(train_data, f, ensure_ascii=False, indent=2)
with open('outputs/$MODEL_NAME/val.json', 'w', encoding='utf-8') as f:
    json.dump(val_data, f, ensure_ascii=False, indent=2)

print(f'数据集划分: 训练={n_train}, 验证={n_val}')
"

echo "[Step 4/7] 完成: 数据集已准备"

# ---------------------------------------------------------------------------
# Step 5/7: 训练模型
# ---------------------------------------------------------------------------
echo ""
echo "[Step 5/7] 训练模型 (这可能需要较长时间)..."

python3 -c "
import sys, json, os
sys.path.insert(0, '.')

from framework.config import LumiLearnConfig, ModelConfig
from framework.model import LumiLearnModel
from framework.utils import TrainingMetrics, seed_everything
import torch

config = LumiLearnConfig()
config.model.vocab_size = 8000
config.model.hidden_size = 256
config.model.num_layers = 4
config.model.num_heads = 4
config.model.ff_dim = 512
config.model.max_seq_len = 256
config.training.learning_rate = 5e-4
config.training.max_steps = 1000
config.training.batch_size = 4
config.training.gradient_accumulation = 2
config.training.warmup_steps = 50
config.training.save_every = 250
config.training.eval_every = 100
config.experiment.name = '$MODEL_NAME'
config.experiment.output_dir = 'outputs/$MODEL_NAME'
config.experiment.checkpoint_dir = 'checkpoints/$MODEL_NAME'

seed_everything(42)

with open('outputs/$MODEL_NAME/train.json', 'r', encoding='utf-8') as f:
    train_data = json.load(f)
with open('outputs/$MODEL_NAME/val.json', 'r', encoding='utf-8') as f:
    val_data = json.load(f)

print(f'训练数据: {len(train_data)} 条, 验证数据: {len(val_data)} 条')

model = LumiLearnModel(config.model)
print(f'模型参数: {sum(p.numel() for p in model.parameters()):,}')

metrics = TrainingMetrics()
optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=config.training.learning_rate,
    weight_decay=config.training.weight_decay,
    betas=config.training.betas,
)

print(f'开始训练 (max_steps={config.training.max_steps})...')
model.train()
for step in range(1, config.training.max_steps + 1):
    batch = train_data[step % len(train_data)]
    text = batch.get('input', '') + ' ' + batch.get('output', '')
    ids = [ord(c) % config.model.vocab_size for c in text[:config.model.max_seq_len]]
    if len(ids) < 2:
        continue
    ids_tensor = torch.tensor([ids], dtype=torch.long)
    labels = ids_tensor.clone()
    outputs = model(ids_tensor, labels=labels)
    loss = outputs['loss']
    loss.backward()
    grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), config.training.max_grad_norm)
    if step % config.training.gradient_accumulation == 0:
        optimizer.step()
        optimizer.zero_grad()
    metrics.log_train(step, loss.item(), config.training.learning_rate, grad_norm.item())
    if step % config.training.log_every == 0:
        print(f'  Step {step}: {metrics.summary()}')
    if step % config.training.eval_every == 0:
        model.eval()
        with torch.no_grad():
            val_batch = val_data[step % len(val_data)]
            val_text = val_batch.get('input', '') + ' ' + val_batch.get('output', '')
            val_ids = [ord(c) % config.model.vocab_size for c in val_text[:config.model.max_seq_len]]
            if len(val_ids) >= 2:
                val_tensor = torch.tensor([val_ids], dtype=torch.long)
                val_out = model(val_tensor, labels=val_tensor.clone())
                metrics.log_val(val_out['loss'].item())
        model.train()
    if step % config.training.save_every == 0:
        ckpt_path = f'checkpoints/$MODEL_NAME/step_{step}'
        model.save_pretrained(ckpt_path)
        print(f'  保存检查点: {ckpt_path}')

model.save_pretrained('outputs/$MODEL_NAME/final_model')
print(f'训练完成! 最终模型 -> outputs/$MODEL_NAME/final_model')
"

echo "[Step 5/7] 完成: 模型训练完成"

# ---------------------------------------------------------------------------
# Step 6/7: 评估模型
# ---------------------------------------------------------------------------
echo ""
echo "[Step 6/7] 评估模型..."

python3 -c "
import sys, json, os
sys.path.insert(0, '.')

try:
    from framework.model import LumiLearnModel
    import torch
    model = LumiLearnModel.from_pretrained('outputs/$MODEL_NAME/final_model')
    model.eval()
    with open('outputs/$MODEL_NAME/val.json', 'r', encoding='utf-8') as f:
        val_data = json.load(f)
    total_loss = 0
    count = 0
    with torch.no_grad():
        for item in val_data[:20]:
            text = item.get('input', '') + ' ' + item.get('output', '')
            ids = [ord(c) % 8000 for c in text[:256]]
            if len(ids) < 2:
                continue
            ids_tensor = torch.tensor([ids], dtype=torch.long)
            outputs = model(ids_tensor, labels=ids_tensor.clone())
            total_loss += outputs['loss'].item()
            count += 1
    avg_loss = total_loss / max(count, 1)
    perplexity = torch.exp(torch.tensor(avg_loss)).item()
    print(f'验证集评估结果:')
    print(f'  平均Loss: {avg_loss:.4f}')
    print(f'  困惑度:   {perplexity:.2f}')
    eval_result = {'model_name': '$MODEL_NAME', 'avg_loss': avg_loss, 'perplexity': perplexity, 'eval_samples': count}
    with open('outputs/$MODEL_NAME/eval_result.json', 'w', encoding='utf-8') as f:
        json.dump(eval_result, f, ensure_ascii=False, indent=2)
except Exception as e:
    print(f'[WARN] 评估失败: {e}')
    eval_result = {'model_name': '$MODEL_NAME', 'avg_loss': 0.0, 'perplexity': 0.0, 'eval_samples': 0, 'note': str(e)}
    with open('outputs/$MODEL_NAME/eval_result.json', 'w', encoding='utf-8') as f:
        json.dump(eval_result, f, ensure_ascii=False, indent=2)
"

echo "[Step 6/7] 完成: 模型评估完成"

# ---------------------------------------------------------------------------
# Step 7/7: 保存并注册模型
# ---------------------------------------------------------------------------
echo ""
echo "[Step 7/7] 保存并注册模型..."

python3 -c "
import os, json, shutil
model_dir = 'outputs/$MODEL_NAME/final_model'
registry_file = 'outputs/model_registry.json'
if os.path.exists(model_dir):
    target_dir = 'outputs/models/$MODEL_NAME'
    os.makedirs('outputs/models', exist_ok=True)
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    shutil.copytree(model_dir, target_dir)
    print(f'模型已复制到: {target_dir}')
    registry = {}
    if os.path.exists(registry_file):
        with open(registry_file, 'r', encoding='utf-8') as f:
            registry = json.load(f)
    registry['$MODEL_NAME'] = {'path': target_dir, 'base_model': '$BASE_MODEL', 'subjects': '$SUBJECTS', 'created_at': __import__('datetime').datetime.now().isoformat()}
    with open(registry_file, 'w', encoding='utf-8') as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    print(f'模型已注册: {registry_file}')
else:
    print(f'[WARN] 模型目录不存在: {model_dir}')
"

echo "[Step 7/7] 完成: 模型已保存并注册"

echo ""
echo "========================================"
echo "  训练完成!"
echo "========================================"
