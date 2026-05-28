# -*- coding: utf-8 -*-
"""
LumiLearn 模型对比可视化
生成模型训练过程的对比图表
"""

import json
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 读取训练报告
with open('lumilearn_model_v2/training_report.json', 'r', encoding='utf-8') as f:
    v2_report = json.load(f)

with open('lumilearn_model_v3_extended/training_report.json', 'r', encoding='utf-8') as f:
    v3_report = json.load(f)

# 创建图表
fig, axes = plt.subplots(2, 2, figsize=(15, 12))

# 1. V2 训练损失曲线
ax1 = axes[0, 0]
epochs_v2 = range(1, len(v2_report['history']['train_loss']) + 1)
ax1.plot(epochs_v2, v2_report['history']['train_loss'], 'b-', label='训练损失', linewidth=2)
ax1.plot(epochs_v2, v2_report['history']['val_loss'], 'r-', label='验证损失', linewidth=2)
ax1.axhline(y=min(v2_report['history']['val_loss']), color='g', linestyle='--', label=f'最佳验证: {min(v2_report["history"]["val_loss"]):.3f}')
ax1.set_xlabel('Epoch')
ax1.set_ylabel('损失')
ax1.set_title('模型 V2 训练过程', fontsize=14, fontweight='bold')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 2. V3 训练损失曲线
ax2 = axes[0, 1]
epochs_v3 = range(1, len(v3_report['history']['train_loss']) + 1)
ax2.plot(epochs_v3, v3_report['history']['train_loss'], 'b-', label='训练损失', linewidth=2)
ax2.plot(epochs_v3, v3_report['history']['val_loss'], 'r-', label='验证损失', linewidth=2)
ax2.axhline(y=min(v3_report['history']['val_loss']), color='g', linestyle='--', label=f'最佳验证: {min(v3_report["history"]["val_loss"]):.3f}')
ax2.set_xlabel('Epoch')
ax2.set_ylabel('损失')
ax2.set_title('模型 V3 训练过程', fontsize=14, fontweight='bold')
ax2.legend()
ax2.grid(True, alpha=0.3)

# 3. 过拟合分析
ax3 = axes[1, 0]
models = ['V1', 'V2', 'V3', 'V4']
train_losses = [0.026, 0.074, 0.074, 1.0]  # 最终训练损失
val_losses = [1.192, 1.748, 1.748, 1.084]  # 最终验证损失
x = range(len(models))
width = 0.35
bars1 = ax3.bar([i - width/2 for i in x], train_losses, width, label='训练损失', color='blue', alpha=0.7)
bars2 = ax3.bar([i + width/2 for i in x], val_losses, width, label='验证损失', color='red', alpha=0.7)
ax3.set_ylabel('损失值')
ax3.set_title('各版本最终损失对比', fontsize=14, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels(models)
ax3.legend()
ax3.grid(True, alpha=0.3, axis='y')

# 添加差距标注
for i, (t, v) in enumerate(zip(train_losses, val_losses)):
    ratio = v / t if t > 0 else 0
    ax3.annotate(f'{ratio:.1f}x', xy=(i, max(t, v)), fontsize=10, ha='center', color='red')

# 4. 数据量对比
ax4 = axes[1, 1]
versions = ['V1', 'V2', 'V3', 'V4']
data_sizes = [1280, 1280, 2131, 'Skills']
colors = ['skyblue', 'skyblue', 'lightgreen', 'lightcoral']
bars = ax4.bar(versions, [1280, 1280, 2131, 1500], color=colors, edgecolor='black', linewidth=2)
ax4.set_ylabel('训练数据量')
ax4.set_title('各版本训练数据量', fontsize=14, fontweight='bold')
ax4.grid(True, alpha=0.3, axis='y')

# 添加数值标签
for bar, size in zip(bars, [1280, 1280, 2131, 'N/A']):
    height = bar.get_height()
    ax4.annotate(f'{size}',
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha='center', va='bottom', fontsize=12, fontweight='bold')

plt.tight_layout()
plt.savefig('model_comparison.png', dpi=150, bbox_inches='tight')
print("✅ 模型对比图已保存到: model_comparison.png")

# 生成损失差距分析图
fig2, ax = plt.subplots(figsize=(10, 6))

epochs = range(1, 51)
v2_gap = [v2_report['history']['val_loss'][i] / v2_report['history']['train_loss'][i] 
          if i < len(v2_report['history']['train_loss']) and v2_report['history']['train_loss'][i] > 0 else 0
          for i in range(min(50, len(v2_report['history']['val_loss'])))]

ax.plot(range(1, len(v2_gap)+1), v2_gap, 'r-', linewidth=2, marker='o', markersize=4)
ax.axhline(y=10, color='orange', linestyle='--', label='警戒线 (10x)')
ax.axhline(y=5, color='green', linestyle='--', label='理想线 (5x)')
ax.fill_between(range(1, len(v2_gap)+1), v2_gap, alpha=0.3, color='red')
ax.set_xlabel('Epoch')
ax.set_ylabel('验证损失 / 训练损失')
ax.set_title('V2 模型过拟合程度分析', fontsize=14, fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_ylim([0, 50])

plt.savefig('overfitting_analysis.png', dpi=150, bbox_inches='tight')
print("✅ 过拟合分析图已保存到: overfitting_analysis.png")

print("\n📊 图表生成完成!")
