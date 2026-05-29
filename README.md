# LumiLearn - AI 智能教育平台

> 从零构建的 AI 教育平台：自研微型 Transformer + 智能讲解引擎 + 直播课堂系统

---

## 项目简介

LumiLearn 是一个端到端的 AI 教育平台，包含三大核心产品和一个自研 ML 框架：

| 模块 | 说明 | 状态 |
|------|------|------|
| 智能讲解引擎 | AI 老师自动授课，8 门课程，OBS 直播叠加 | ✅ 完成 |
| 智能回复引擎 | 知识库 + 模型 + 乱码检测，12/12 测试通过 | ✅ 完成 |
| 直播助手 | 弹幕 AI 互动，OBS 浏览器源叠加 | ✅ 完成 |
| 微型 Transformer | GPT-2 风格，字符级 tokenizer，从零训练 | ✅ 完成 |

---

## 智能讲解引擎 (`lesson_engine.py`)

**核心功能**：AI 老师自动按幻灯片讲解知识点，可直接叠加到直播画面。

### 特点

- 8 门预置课程（数学/英语/语文/学习方法），每门 5-7 张幻灯片
- 每张幻灯片含：标题、正文、公式、例题、小贴士、TTS 旁白
- OBS 透明叠加层，自动翻页（8-14 秒/页）
- REST API 控制：开始、下一张、上一张、跳转

### 快速启动

```bash
# 启动讲解引擎服务器（端口 8766）
python lesson_engine.py

# 在 OBS 中添加"浏览器源"
# URL: http://localhost:8766/overlay
# 宽: 800, 高: 600

# 开始讲课
curl http://localhost:8766/api/lesson/start?lesson_id=triangle_area
```

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/lessons` | GET | 获取所有课程列表 |
| `/api/lesson/start?lesson_id=xxx` | GET | 开始指定课程 |
| `/api/lesson/next` | GET | 下一张幻灯片 |
| `/api/lesson/prev` | GET | 上一张幻灯片 |
| `/api/lesson?id=xxx` | GET | 获取课程详情 |
| `/overlay` | GET | OBS 叠加层页面 |

### 课程列表

| ID | 科目 | 年级 | 标题 |
|----|------|------|------|
| `triangle_area` | 数学 | 小学 | 三角形的面积 |
| `linear_equation` | 数学 | 初中 | 一元一次方程 |
| `fraction_ops` | 数学 | 小学 | 分数的加减法 |
| `prime_numbers` | 数学 | 小学 | 质数与合数 |
| `english_tenses` | 英语 | 初中 | 英语时态 |
| `english_phrases` | 英语 | 初中 | 常用英语短语 |
| `essay_writing` | 语文 | 通用 | 作文写作技巧 |
| `study_methods` | 学习方法 | 通用 | 高效学习方法 |

---

## 智能回复引擎 (`smart_reply_engine.py`)

**核心功能**：混合回复策略，知识库精确匹配 + 模型推理 + 乱码检测兜底。

```
用户问题 → 知识库精确匹配 → LumiLearn 模型推理 → 规则引擎兜底
                ↓                    ↓                ↓
            标准回答            AI 自由生成        通用回复
                                     ↓
                              乱码检测过滤
```

### 特点

- 21 个教育知识库主题（数学、物理、化学、英语、学习方法等）
- 中文常用字频率分析的乱码检测
- 语义有效性验证（过滤掉看似正常但无意义的文本）
- 12/12 测试用例全部通过

### 快速测试

```bash
python -c "
from smart_reply_engine import LiveTutor
tutor = LiveTutor()
for q in ['什么是三角形面积公式', '怎么学英语', '如何提高记忆力']:
    print(f'Q: {q}')
    print(f'A: {tutor.reply(q)}\n')
"
```

---

## 直播助手 (`live_anchor.py`)

集成智能回复引擎，在直播间实时回复弹幕。支持 OBS 浏览器源叠加。

### 架构

```
抖音/快手弹幕 → WebSocket → AIResponder(LiveTutor) → OBS 叠加层
                                                    ↓
                                              TTS 语音输出
```

---

## ML 框架 (`framework/`)

从零实现的 GPT-2 风格 Transformer：

```
framework/
├── model.py      # GPT-2 风格 Transformer (Pre-LN, GELU)
├── config.py     # 训练配置中心
├── tokenizer.py  # 字符级 tokenizer (vocab_size=8000)
├── data.py       # 数据加载器
├── trainer.py    # 训练循环
└── utils.py      # 工具函数
```

### 模型规格

| 参数 | 值 |
|------|------|
| 架构 | GPT-2 Decoder-only |
| 层数 | 8 |
| 注意力头 | 8 |
| 隐藏维度 | 384 |
| FFN 维度 | 1024 |
| 词表大小 | 8000-12000 |
| 参数量 | ~8M |
| Tokenizer | 字符级 |

---

## 数据管线 (`data_management/`)

```
data_management/
├── cleaner.py    # 数据清洗
├── validator.py  # 质量验证
├── pipeline.py   # 数据流水线
├── schema.py     # 数据模式
└── versioner.py  # 版本管理
```

---

## 部署

### 推理服务器（天虹服务器）

```bash
# 部署推理服务器到天虹 (192.168.2.63:18080)
python deploy_inference_server.py

# 部署智能回复引擎
python deploy_smart_engine.py
```

### Docker

```bash
docker-compose up -d
```

---

## 项目结构

```
lumilearn/
├── framework/              # 微型 Transformer 框架
│   ├── model.py            #   GPT-2 风格模型架构
│   ├── config.py           #   训练配置中心
│   ├── tokenizer.py        #   字符级分词器
│   ├── data.py             #   数据加载器
│   ├── trainer.py          #   训练循环
│   └── utils.py            #   工具函数
├── data_management/        # 数据管线
│   ├── cleaner.py          #   数据清洗
│   ├── validator.py        #   质量验证
│   ├── pipeline.py         #   数据流水线
│   ├── schema.py           #   数据模式
│   └── versioner.py        #   版本管理
├── scripts/                # 自动化脚本/流水线
│   ├── lumilearn_unified_auto.py   # 统一自动化流水线
│   ├── generate_personal_study.py  # 个人学习生成器
│   ├── lumilearn_learning_path_generator.py  # 学习路径生成
│   └── ...
├── skills/                 # 技能模块
├── lesson_engine.py        # 智能讲解引擎 ⭐
├── smart_reply_engine.py   # 智能回复引擎 ⭐
├── langgraph_engine.py     # 多模型并行编排引擎
├── batch_data_collector.py # 全学科数据收集器
├── animation_generator.py  # Manim 动画生成器
├── lumilearn_shared.py     # 共享模块(路径/模型/工具)
├── live_anchor.py          # 直播助手
├── live_anchor_preview.html # OBS 叠加层预览
├── live_demo.html          # 交互演示页面
├── inference.py            # 模型推理
├── inference_server.py     # Flask 推理服务器
├── deploy_inference_server.py # 部署到天虹
├── deploy_smart_engine.py  # 部署智能引擎
├── docker-compose.yml
├── docker-compose.tianhong.yml
├── Dockerfile*
├── requirements.txt
├── PROJECT_PRINCIPLES.md   # 开发原则
└── .env.example
```

---

## 快速开始

```bash
# 克隆
git clone https://github.com/yourname/lumilearn.git
cd lumilearn

# 安装依赖
pip install -r requirements.txt

# 启动智能讲解引擎（浏览器打开 http://localhost:8766/overlay）
python lesson_engine.py

# 在其他终端测试 API
curl http://localhost:8766/api/lessons
```

---

## 开发原则

基于 Andrej Karpathy 编程原则制定：

- 诚实优先：公开约束条件，不隐藏权衡
- 简洁优先：用最少代码解决问题
- 目标驱动执行：定义成功标准，循环验证
- 手术式修改：只动必须修改的代码

详见 [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md)

---

## 开源计划

- [x] 整理项目结构
- [x] 编写 README
- [x] 配置 .gitignore
- [ ] 创建 GitHub 仓库
- [ ] 写技术博客
- [ ] 录制演示视频

---

## 许可证

MIT License

---

**最后更新**：2026-05-28