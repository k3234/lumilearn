# LumiLearn — 在 CPU 上从零训练的微型 AI 教育模型

> 输入学科和章节，自动生成知识点讲解、练习题和解析。  
> **全部在 CPU 上训练和推理，无 GPU 也能跑。**  
> 由一名高一学生开发维护。

## 10 秒看懂

| 问题 | 答案 |
|:---|:---|
| **做什么？** | 自研微型 Transformer 模型 + 前端教学演示系统，自动生成数学/物理/化学的讲解内容 |
| **为什么特别？** | 全部在 CPU 上训练（8M 参数），从 tokenizer 到推理全部自己实现 |
| **适合谁？** | 想学习"从数据到模型到部署"完整流程的学生开发者 |
| **教育价值** | 让老旧设备也能跑 AI 教学演示，推动"算力平权"，让资源不足的学校也能接触 AI 教育 |

## 快速导航

| 我想... | 去看 |
|:---|:---|
| 看这个项目长什么样 | [课堂模式演示](tianhong/templates/classroom.html) · [对话终端](tianhong/templates/lumiterm.html) |
| 了解系统架构 | [docs/development_summary.md](docs/development_summary.md) |
| 看模型怎么训练的 | `framework/model.py` · `framework/config.py` |
| 看数据怎么处理的 | `data_management/` 目录 |
| 了解开发原则 | [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) |
| 看学习笔记 | [docs/learning_journey/](docs/learning_journey/) |
| 看 Jupyter 教程 | [notebooks/](notebooks/) |
| 看研究规划 | [docs/research/](docs/research/) |

## 核心模块

| 模块 | 说明 | 状态 |
|:---|:---|:---|
| **微型 Transformer** | GPT-2 风格，8 层 8 头，256 隐藏维度，~8M 参数，BPE tokenizer | ✅ 完成 |
| **课堂模式** | 三栏布局（大纲 + 幻灯片 + AI 聊天），费曼五步学习法 | ✅ 完成 |
| **对话终端** | 轻量聊天界面，支持多轮对话，非流式 Ollama 代理 | ✅ 完成 |
| **智能讲解引擎** | 8 门预置课程，OBS 透明叠加层，自动翻页 | ✅ 完成 |
| **智能回复引擎** | 知识库 + 模型推理 + 乱码检测，12/12 测试通过 | ✅ 完成 |
| **数据管线** | 清洗、验证、版本管理管线 | ✅ 完成 |

## 模型规格

| 参数 | 值 |
|:---|:---|
| 架构 | GPT-2 Decoder-only (Pre-LN, GELU) |
| 层数 / 注意力头 | 8 / 8 |
| 隐藏维度 / FFN 维度 | 256 / 1024 |
| 序列最大长度 | 256 |
| 词表大小 | 8000 |
| 参数量 | ~8.3M |
| Tokenizer | BPE (HuggingFace tokenizers) |

## 快速开始

```bash
# 克隆
git clone https://github.com/k3234/lumilearn.git
cd lumilearn

# 安装依赖
pip install -r requirements.txt

# 启动课堂模式（浏览器打开 http://localhost:18080/classroom）
python framework/api/server.py --multi-port

# 或启动对话终端
# 浏览器打开 http://localhost:18080/chat
```

## API 基础用法

启动服务后，可通过 REST API 与模型交互：

```bash
# 健康检查
curl http://localhost:18080/api/health

# 发送聊天请求
curl -X POST http://localhost:18080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "讲解牛顿第二定律", "session_id": "optional"}'

# 生成幻灯片内容
curl -X POST http://localhost:18080/api/slides \
  -H "Content-Type: application/json" \
  -d '{"topic": "数学", "chapter": "函数"}'

# 获取思维导图
curl -X POST http://localhost:18080/api/mindmap \
  -H "Content-Type: application/json" \
  -d '{"topic": "化学", "chapter": "有机化学"}'
```

## 模型训练与部署（完整 Demo 流程）

> 训练在远程 CPU 服务器（`<SERVER_IP>`，14GB RAM）上进行，目标模型为 Qwen2.5-3B CPU 微调。详见 [docs/development_summary.md](docs/development_summary.md)。

```bash
cd <PROJECT_DIR>

# 1) 用真实费曼教学数据训练 LoRA adapter（CPU，约 44min/batch）
OMP_NUM_THREADS=4 python3 -u scripts/train_real.py \
    --data data/distil/train_data_real.jsonl \
    --adapter models/distil/adapter \
    --max-length 128 --epochs 1

# 2) 合并 LoRA adapter 为完整模型，并跑 5 道题验证推理
OMP_NUM_THREADS=4 python3 -u scripts/merge_and_test.py \
    --base <BASE_MODEL_PATH> \
    --adapter models/distil/adapter \
    --output models/distil/merged_model

# 3) 启动本地推理服务器（OpenAI/ollama 兼容接口）
python inference_server.py --port 18080 --model-dir models/distil/merged_model
```

验证推理接口：

```bash
curl http://localhost:18080/health
curl -X POST http://localhost:18080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"用费曼五步法讲解勾股定理"}]}'
```

## 项目结构
```
lumilearn/
├── framework/              # 微型 Transformer 框架
│   ├── model.py            #   GPT-2 风格模型架构
│   ├── config.py           #   训练配置中心
│   ├── tokenizer.py        #   BPE 分词器
│   ├── data.py             #   数据加载器
│   └── trainer.py          #   训练循环
├── framework/api/          # REST API 服务
│   ├── server.py           #   Flask 服务器
│   └── routes/             #   路由（chat/slides/mindmap/...）
├── framework/engines/      # 智能引擎
│   └── feynman_engine.py   #   费曼五步学习法引擎
├── framework/core/         # 核心模块
│   ├── config.py           #   配置管理
│   └── router.py           #   模型路由
├── framework/models/       # 模型提供者
│   ├── base.py             #   抽象基类
│   ├── ollama_provider.py  #   Ollama API实现
│   └── registry.py         #   模型注册表
├── framework/services/     # 服务层
│   ├── chat_service.py     #   聊天服务
│   └── provider_service.py #   云端提供商管理
├── framework/airllm/       # AirLLM优化模块
│   ├── attention.py        #   GQA注意力
│   └── rope.py             #   RoPE位置编码
├── tianhong/templates/     # 前端页面
│   ├── classroom.html      #   课堂模式
│   └── lumiterm.html       #   对话终端
├── data_management/        # 数据管线
├── scripts/                # 训练/部署脚本
│   ├── train_real.py       #   真实数据 LoRA 训练（CPU）
│   └── merge_and_test.py   #   LoRA 合并 + 推理测试
├── docs/                   # 学习笔记 & 研究文档
├── notebooks/              # Jupyter 教程
├── skills/                 # 技能模块
├── config/                 # 配置文件
│   ├── framework.yaml      #   框架配置
│   └── providers.yaml      #   云端提供商配置
├── train_lumilearn.sh      # 训练脚本
├── lesson_engine.py        # 智能讲解引擎
├── smart_reply_engine.py   # 智能回复引擎
└── PROJECT_PRINCIPLES.md   # 开发原则
```

## 开发原则

基于 Andrej Karpathy 编程原则制定：

- **诚实优先**：公开约束条件，不隐藏权衡
- **简洁优先**：用最少代码解决问题
- **目标驱动执行**：定义成功标准，循环验证
- **手术式修改**：只动必须修改的代码

详见 [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md)

## 路线图

### 已完成
- [x] 项目结构整理与开源
- [x] README 完善（含安装/运行/API 文档）
- [x] 微型 Transformer 模型（8M 参数）实现
- [x] 课堂模式与对话终端前端
- [x] 费曼五步学习法引擎
- [x] 数据管线（清洗/验证/版本管理）
- [x] MIT 许可证

### 进行中
- [ ] 单元测试覆盖率提升
- [ ] API 文档站点（完整版）
- [ ] 演示视频录制

### 未来规划
- [ ] 模型量化支持（INT8/INT4）
- [ ] 多语言界面（中/英/日）
- [ ] 贡献者指南与社区治理
- [ ] 安全扫描工具链集成
- [ ] 版本发布规范（语义化版本）

## 教育场景与算力平权

LumiLearn 的核心愿景是让**老旧设备也能运行 AI 教学演示**：

- **低配置友好**：8M 参数模型，14GB 内存的 CPU 笔记本即可训练和推理
- **无 GPU 依赖**：不依赖高端显卡，降低 AI 教育门槛
- **资源不足地区适用**：让算力资源有限的学校也能接触 AI 教育
- **完整学习路径**：从数据→模型→部署，一站式学习 AI 全流程

## 开源计划

- [x] 整理项目结构
- [x] 编写 README
- [x] 创建 GitHub 仓库
- [x] 添加 LICENSE
- [ ] 写技术博客
- [ ] 录制演示视频

## 许可证

[MIT License](LICENSE)

---

**最后更新**：2026-08-04