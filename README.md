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

## 开源计划

- [x] 整理项目结构
- [x] 编写 README
- [x] 创建 GitHub 仓库
- [ ] 写技术博客
- [ ] 录制演示视频

## 许可证

MIT License

---

**最后更新**：2026-08-03