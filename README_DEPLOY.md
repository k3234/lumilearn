# LumiLearn 训练数据扩充与部署系统

## 📋 概述

这是LumiLearn完整的数据管理、训练和部署系统，包含：

- 📊 智能训练数据生成器
- 💾 磁盘与备份管理器（支持F盘自动备份）
- 🚀 天虹主机自动化训练部署
- 🐳 Docker容器化部署（Ollama + API服务）
- 🎨 Web管理仪表板

## 📁 新增文件

### 核心工具
| 文件 | 说明 |
|------|------|
| `data_generator.py` | 智能训练数据生成器 |
| `storage_manager.py` | 磁盘与备份管理器 |
| `tianhong_deployer.py` | 天虹主机部署工具 |
| `dashboard.py` | Web管理仪表板 |

### Docker配置
| 文件 | 说明 |
|------|------|
| `docker-compose.yml` | Docker Compose配置 |
| `Dockerfile.api` | API服务容器 |
| `Dockerfile.train` | 训练容器 |
| `Dockerfile.data` | 数据准备容器 |

### 配置与文档
| 文件 | 说明 |
|------|------|
| `requirements.txt` | Python依赖 |
| `.env.example` | 环境配置模板 |
| `MODEL_CHECK_REPORT.md` | 模型检测报告 |
| `PROJECT_OPTIMIZATION_SUMMARY.md` | 优化总结 |
| `MODEL_DETECTION_SUMMARY.md` | 检测摘要 |
| `MODEL_QUICK_GUIDE.md` | 快速指南 |
| `README_DEPLOY.md` | 本文档 |

---

## 🚀 快速开始

### 1. 检查当前状态

```bash
cd e:\学习LLM\lumilearn

# 查看项目状态
python storage_manager.py
```

### 2. 生成训练数据

```bash
# 运行数据生成器
python data_generator.py

# 按提示输入要生成的数量（推荐每次200条）
```

### 3. 创建备份

```bash
# 备份数据到F盘
python storage_manager.py
# 选择操作 1 或 4
```

### 4. 天虹主机训练

```bash
# 运行部署工具
python tianhong_deployer.py

# 选择完整流程或分步执行
```

### 5. Web管理界面

```bash
# 启动Web仪表板
python dashboard.py

# 在浏览器访问: http://localhost:5000
```

---

## 💾 磁盘管理策略

### 磁盘分配
- **C:** 系统盘 - Docker、系统文件
- **D:/E:** 数据盘 - 训练数据、临时文件、模型
- **F:** 备份盘 - 压缩备份、长期存储

### 自动备份
- 自动压缩关键数据
- 保留最近10个备份
- 清理旧备份释放空间
- 空间告警通知

---

## 📊 训练数据管理

### 数据生成
- 智能补充薄弱学科（英语、语文优先级最高）
- 自动去重检测
- 多学科、多难度、多类型覆盖
- 目标：10,000条高质量数据

### 学科分布
当前已有约 **2,017条** 数据，覆盖：
- 数学 (202条) ✅
- 英语 (117条) ⚠️ 需补充
- 语文 (128条) ⚠️ 需补充
- 物理 (90条)
- 化学 (85条)
- AI模型开发 (610条)
- 其他学科...

---

## 🚀 天虹主机部署

### 系统要求
- Ubuntu 22.04+
- R7-7840HS CPU
- 16GB+ RAM
- PyTorch 2.4.1+ (ROCm/CUDA)

### 训练步骤

#### 1. 本地准备
```bash
# 生成充足的数据
python data_generator.py

# 创建备份
python storage_manager.py
```

#### 2. 上传到天虹
使用WinSCP或文件共享，上传：
- `lumilearn_master.csv`
- 需要继续训练的模型文件夹
- 训练脚本 (`train_tianhong_v4.py`)

#### 3. 天虹训练
```bash
# SSH登录天虹
ssh lumi@192.168.2.63

# 进入目录
cd /home/lumi/lumilearn

# 开始训练
python train_tianhong_v4.py

# 监控日志
tail -f training.log
```

---

## 🐳 Docker部署

### 1. 启动Ollama
```bash
cd e:\学习LLM\lumilearn

# 启动Ollama服务
docker compose up -d ollama

# 下载模型
docker exec lumilearn-ollama ollama pull qwen2.5:7b
docker exec lumilearn-ollama ollama pull deepseek-r1:1.5b
```

### 2. 启动API服务
```bash
docker compose up -d api-gateway

# 验证服务
curl http://localhost:8000/health
```

### 3. 内网访问
API服务运行在 `http://192.168.2.63:8000`

局域网设备可通过IP访问。

---

## 🎨 Web管理仪表板

### 启动方式
```bash
python dashboard.py
```

### 访问地址
http://localhost:5000

### 功能
- 📊 数据概览与进度
- 💾 磁盘状态监控
- 🤖 模型状态管理
- 🌐 服务健康检查
- ⚡ 快捷操作入口

---

## 📋 完整工作流程

```
1. 数据生成
   ↓
2. 本地检查 & 备份 (F盘)
   ↓
3. 同步到天虹主机
   ↓
4. 天虹训练
   ↓
5. 模型回传
   ↓
6. Docker部署 (Ollama + API)
   ↓
7. 内网访问测试
```

---

## ⚙️ 配置说明

### 环境变量
复制 `.env.example` 为 `.env` 并修改配置：

```env
# Ollama服务
OLLAMA_BASE_URL=http://192.168.2.63:11434

# 训练配置
BATCH_SIZE=4
LEARNING_RATE=3e-4
MAX_EPOCHS=30
```

### 数据生成配置
在 `data_generator.py` 中可调整：
- `TARGET_COUNT = 10000` 目标数据量
- `BATCH_SIZE = 100` 每批数量
- `SUBJECT_PRIORITY` 学科优先级

---

## 🔍 监控与诊断

### 检查模型状态
```bash
# 查看详细模型报告
# 打开 MODEL_CHECK_REPORT.md
# 或查看生成的图表: model_comparison.png
```

### 检查数据质量
```bash
# 查看学科分布
python -c "
from data_generator import TrainingDataGenerator
g = TrainingDataGenerator()
print(g.subject_counts)
"
```

### 检查磁盘空间
```bash
python storage_manager.py
# 查看各盘使用情况
```

---

## 📌 最佳实践

### 数据管理
1. **每天生成少量**：每次100-200条，避免大量生成导致质量下降
2. **定期备份**：每次训练前先备份到F盘
3. **质量检查**：定期抽查生成的内容

### 训练管理
1. **监控验证损失**：如开始上升立即停止
2. **早停策略**：使用推荐的早停参数
3. **Checkpoint管理**：保留最佳checkpoint，而非最终epoch

### 部署管理
1. **先测试再部署**：在天虹完成训练测试后再正式部署
2. **版本管理**：每个模型版本独立文件夹
3. **资源监控**：定期检查内存和磁盘使用

---

## 🆘 常见问题

### Q: 如何解决过拟合问题？
A: 1) 增加训练数据 2) 使用早停 3) 增强正则化 4) 降低学习率

### Q: F盘空间不足怎么办？
A: 1) 清理旧备份 2) 调整保留数量 3) 使用更大压缩率

### Q: 天虹训练中断怎么办？
A: 从最佳checkpoint继续训练，使用 `lumilearn_continue_training.py`

### Q: Docker服务无法启动？
A: 1) 检查端口占用 2) 检查GPU驱动 3) 查看Docker日志

---

## 📞 相关文件索引

### 核心文档
- [MODEL_CHECK_REPORT.md](MODEL_CHECK_REPORT.md) - 详细模型检测
- [MODEL_QUICK_GUIDE.md](MODEL_QUICK_GUIDE.md) - 快速参考
- [MODEL_DETECTION_SUMMARY.md](MODEL_DETECTION_SUMMARY.md) - 检测摘要

### 工具脚本
- [data_generator.py](data_generator.py) - 数据生成
- [storage_manager.py](storage_manager.py) - 存储管理
- [tianhong_deployer.py](tianhong_deployer.py) - 部署工具
- [dashboard.py](dashboard.py) - Web仪表板

### 训练脚本
- [train_tianhong_v4.py](train_tianhong_v4.py) - 天虹训练
- [lumilearn_full_training_v6.py](lumilearn_full_training_v6.py) - 完整训练

---

## 🎉 总结

我们创建了完整的系统：
✅ 智能数据生成（可扩充到10,000+条）
✅ 磁盘管理与自动备份到F盘
✅ 天虹主机训练部署流程
✅ Docker容器化部署方案
✅ Web管理界面与监控
✅ 详细文档与报告

现在可以开始使用这些工具进行数据扩充和训练了！
