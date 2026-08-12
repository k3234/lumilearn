# LumiLearn — 在 CPU 上从零训练的微型 AI 教育模型

> 输入学科和章节，自动生成知识点讲解、练习题和解析。  
> **全部在 CPU 上训练和推理，无 GPU 也能跑。**  
> 由一名高中学生开发维护。

## 📋 GOAI 2026 参赛材料

- [作品简介](docs/GOAI_SUBMISSION.md) — 可直接复制到 GOAI 作品提交页面「作品简介」字段
- [参赛技术方案](docs/GOAI_TECHNICAL.md) — 项目定位 / 架构 / 技术路线 / 创新点
- [部署指南](docs/DEPLOYMENT_GUIDE.md) — 一键部署与手动部署（含健康检查）
- [评测结果](docs/EVALUATION_RESULTS.md) — 全量测试与真实环境测评数据
- [运行证据](docs/RUNNING_EVIDENCE.md) — 服务状态 / API 实测 / 数据落库证据
- [模型下载](docs/MODEL_DOWNLOAD.md) — lumilearn-v2 获取与 Ollama 导入
- [AI 使用声明](AI-DECLARATION.md) — AI 参与方式与责任声明

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
| 看这个项目长什么样 | [课堂模式演示](remote/templates/classroom.html) · [对话终端](remote/templates/lumiterm.html) |
| 了解系统架构 | [docs/development_summary.md](docs/development_summary.md) |
| 看模型怎么训练的 | `framework/model.py` · `framework/config.py` |
| 看数据怎么处理的 | `data_management/` 目录 |
| 了解开发原则 | [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) |
| 看学习笔记 | [docs/learning_journey/](docs/learning_journey/) |
| 看 Jupyter 教程 | [notebooks/](notebooks/) |
| 看研究规划 | [docs/research/](docs/research/) |

## 🤖 Agent 智能体

LumiLearn 内置一套可独立启停、统一生命周期的 Agent 框架（`framework/admin/agents.py`），并在 Admin 面板「Agent 管理」中可视化运行；另有一个面向完整学习闭环的 GOAI 教育智能体（`goai_agent.py`）。

| Agent | ID | 能力 |
|:---|:---|:---|
| **费曼教学 Agent** | `feynman_teacher` | 基于费曼五步法讲解知识点；传入对话历史时自动切换为**交互式单步引导**（现象引入 → 认知冲突 → 思维模型 → 自主推导 → 费曼测试），上下文连贯、逐步推进 |
| **输出检测 Agent** | `output_detector` | 检测学生学习输出质量（简洁/准确/比喻/完整/术语五维评分），给出改进建议 |
| **自适应学习 Agent** | `adaptive_path` | 根据学生学习进度与掌握度推荐个性化学习路径 |
| **对话助手 Agent** | `chat_assistant` | 通用多轮对话，自动路由到当前端口配置的模型 |
| **GOAI 教育智能体** | `goai_agent.py` | 任务理解 → 流程编排（费曼五步） → 多模型工具调用 → 完整学习报告（掌握度 + 薄弱点 + 建议），推理过程写入本地推理记录库，供管理员/教师/模型自查 |

所有 Agent 支持 `start / stop / status / run` 统一生命周期，Agent 运行状态持久化到数据库；推理过程（费曼每步、GOAI 学习）自动写入 `reasoning_logs` 推理记录库，可通过 Admin「推理记录」、教师端「推理记录」、API `/api/reasoning-logs` 三方查看。

## 🤖 多 Agent 协作系统（GOAI 评审亮点）

从"单 Agent 四模块串行"升级为"三 Agent 协作编排"（`goai_multi_agent.py`），GOAI 学习 Web（5000 端口）学习页默认调用：

```
学生输入 ─→ FeynmanTeacher（教学）─→ ScoreAgent（评分）─→ CoachAgent（建议）─→ 聚合报告
                │  RAG 检索注入            │  五维评估             │  学习路径推荐
                ▼                          ▼                      ▼
        费曼五步（现象→冲突→模型→推导→测试）  掌握度评分          建议 + 推荐知识点
```

| 特性 | 说明 |
|---|---|
| 独立模型 | 每个 Agent 可配置不同模型（`MULTI_AGENT_*_MODEL` 环境变量，优先读端口配置） |
| 失败降级 | 单 Agent 异常不阻塞后续，`agent_trace` 记录 ok/skipped/failed |
| 交互模式 | 传 `dialogue` 历史时自动切交互式单步引导 |
| 报告落库 | 有评分时写入 `learning_reports`，Admin/教师端可视化可见 |

## 📚 RAG 知识库检索（Day 3）

教学内容"有据可查"：从 `training_data`（已发布教学资源）与 `knowledge_nodes`（知识点）构建**关键词倒排索引**，纯 Python 实现、零外部依赖、不引入向量数据库。

- 模块：`framework/services/knowledge_retrieval.py`（轻量中文分词 + 简化 BM25）
- 集成：FeynmanTeacher 生成前自动检索相关知识点注入 prompt，报告带 `rag_sources` 展示来源
- API：`GET/POST /api/knowledge/search?q=...`、`GET /api/knowledge/status`（需登录）
- 设计文档：[docs/rag_design.md](docs/rag_design.md)

## 📊 数据可视化 + 账号权限 + 数据合规导出（Day 2 任务三）

| 能力 | 端口 | 说明 |
|---|---|---|
| 数据可视化 | Admin 18080 / 教师 5001 | 掌握度趋势、学科对比、薄弱点排行、知识点热力、模型推理统计、学生排行（教师仅本班） |
| 管理员分级 | Admin | `super_admin`（管理）+ `operator`（查看），独立 `admins` 表 |
| 用户启停/改角色 | Admin | 登录拦截、防锁死保护（不能禁用/删除自己） |
| 数据合规导出 | Admin / 教师 | 教师申请 → 管理员审批 → 下载（JSON/CSV），全流程审计 |

## 🧠 模型与模型容器

LumiLearn 支持**本地模型容器**与**云端 API** 两类推理来源，其中 **Ollama 为默认推荐容器**。全部接入模型可通过 Admin 面板「模型管理」集中配置，并按端口指定各服务使用的模型。

| 来源 | 说明 | 模型发现 |
|:---|:---|:---|
| **Ollama（推荐）** | 本地/远程 Ollama 服务，默认 `http://localhost:11434` | 自动调用 `/api/tags` 发现容器内**全部模型** |
| **其他本地容器** | OpenAI 兼容接口：vLLM / LM Studio / LocalAI / llama.cpp server 等 | 自动调用 `/models` 发现容器内**全部模型** |
| **云端 API** | 豆包 / 智谱 / Kimi / MiniMax / OpenAI / DeepSeek 等（OpenAI 兼容） | 配置时登记模型列表 |

**模型接入**：运行 `deploy/setup.py` 交互式引导（探测并列出容器内全部模型供选择），或在 Admin 面板「模型管理」中手动添加。

**主要模型资产**：

| 模型 | 来源 | 用途 |
|:---|:---|:---|
| `lumilearn-v2:latest` | 自研 LoRA 微调（Qwen2.5-1.5B，Q8_0 量化） | 默认对话/学习模型，CPU 推理 26+ tok/s |
| `qwen2.5:7b` | Ollama 官方 | 费曼引导默认模型（上下文利用更强） |
| 微调 Transformer（8M） | 从零训练 | 课堂演示、教学编排 |
| 云端模型（可选） | 各厂商 API | 高质量生成场景 |

**端口模型配置**：每个端口（终端/API/模型管理/GOAI Web/教师端）可独立指定使用哪个提供商的哪个模型，配置实时生效，无需重启。

## 文档索引

| 文档 | 说明 |
|:---|:---|
| [docs/PROGRESS.md](docs/PROGRESS.md) | 项目进度总览（模块状态 / 部署信息 / 模型资产清单） |
| [docs/admin_guide.md](docs/admin_guide.md) | 管理员系统使用指南 |
| [docs/deployment_guide.md](docs/deployment_guide.md) | 本地与服务器部署指南 |
| [docs/MODEL_COMPARISON.md](docs/MODEL_COMPARISON.md) | 模型资产对照表（脱敏版） |
| [docs/REMOTE_DEPLOYMENT.md](docs/REMOTE_DEPLOYMENT.md) | 远程部署说明 |
| [docs/rag_design.md](docs/rag_design.md) | RAG 知识库设计说明 |
| [docs/privacy_compliance.md](docs/privacy_compliance.md) | 数据合规说明 |
| [docs/open_source_plan.md](docs/open_source_plan.md) | 开源路线图 |
| [docs/learning_journey/INDEX.md](docs/learning_journey/INDEX.md) | 学习旅程笔记索引 |
| [notebooks/INDEX.md](notebooks/INDEX.md) | Jupyter 教程索引 |
| [deploy/README.md](deploy/README.md) | 一键部署工具说明 |

## 核心模块

| 模块 | 说明 | 状态 |
|:---|:---|:---|
| **微型 Transformer** | GPT-2 风格，8 层 8 头，256 隐藏维度，~8M 参数，BPE tokenizer | ✅ 完成 |
| **课堂模式** | 三栏布局（大纲 + 幻灯片 + AI 聊天），费曼五步学习法 | ✅ 完成 |
| **对话终端** | 轻量聊天界面，支持多轮对话，非流式 Ollama 代理 | ✅ 完成 |
| **智能讲解引擎** | 8 门预置课程，OBS 透明叠加层，自动翻页 | ✅ 完成 |
| **智能回复引擎** | 知识库 + 模型推理 + 乱码检测，12/12 测试通过 | ✅ 完成 |
| **学习工作流引擎** | 五步学习法编排，自动检测输出质量 | ✅ 完成 |
| **输出检测系统** | 多维度评分（简洁/准确/比喻/完整/术语），引导式强化 | ✅ 完成 |
| **数据管线** | 清洗、验证、版本管理管线 | ✅ 完成 |
| **管理员系统** | 认证、用户/模型/Agent管理、系统监控、Web 管理面板 | ✅ 完成 |
| **Agent 框架** | Agent 注册表 + 4 个内置 Agent（费曼/检测/自适应/对话） | ✅ 完成 |

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

## 🚀 快速开始 / 一键部署

从零到跑通全部服务，只需一条命令。部署工具位于 `deploy/` 目录，交互式引导完成环境检测、依赖安装、端口配置与模型接入，无需手工编辑配置文件。

### 环境要求

| 依赖 | 说明 |
|:---|:---|
| **Python ≥ 3.9** | 需自带 pip |
| **Git**（仅从零部署需要） | 一键脚本自动克隆仓库时使用 |
| **Ollama**（可选） | 本地模型推理服务，默认地址 `http://localhost:11434`；未安装时可先接入云端 API，稍后再补 |
| **网络** | 安装依赖需访问 PyPI；使用云端大模型 API 需相应网络环境 |

### 从零一键部署（含克隆仓库）

**无需手动克隆**，下载 `deploy/bootstrap.bat` / `deploy/bootstrap.sh` 到任意目录运行，自动完成：
`克隆/更新仓库 → 检测环境 → 安装依赖 → 配置端口与模型 → 启动服务`。

**Windows：**

```bat
:: 下载 deploy/bootstrap.bat 后，在任意目录运行
bootstrap.bat
:: 无人值守：bootstrap.bat --quick
```

**Linux / macOS：**

```bash
# 下载 deploy/bootstrap.sh 后
chmod +x bootstrap.sh
./bootstrap.sh
```

### 已有仓库（更新 + 配置 + 启动）

已克隆过仓库时，在仓库根目录运行：

**Windows：**

```bat
deploy\setup.bat
```

**Linux / macOS：**

```bash
bash deploy/setup.sh
```

脚本会自动完成：

1. 检测环境（Python / pip）
2. 安装依赖（`pip install -r requirements.txt`，可输入 `n` 跳过）
3. 引导配置各服务端口（默认沿用当前配置）
4. 引导接入模型（Ollama 本地/远程地址 + 云端 API Key）
5. 输出启动指引

### 选择端口

五个服务可独立设置 `enabled`（是否启用）与 `port`（端口号），配置持久化到 `config/framework.yaml` 的 `port_settings` 段：

| 服务键 | 默认端口 | 用途 |
|:---|:---|:---|
| `goai_web` | 5000 | GOAI 学习 Web |
| `teacher_portal` | 5001 | 教师门户 |
| `terminal` | 18080 | 框架终端（HTML 界面） |
| `api` | 18081 | REST API |
| `models` | 18082 | 模型管理 |

端口随时可改：再次运行 setup 引导，或在 Admin 面板「端口管理」中直接调整，改后重启对应服务生效。

### 接入模型

| 方式 | 说明 |
|:---|:---|
| **本地 Ollama**（默认推荐） | 地址保持 `http://localhost:11434`，脚本会校验连通并列出本机全部模型供选择 |
| **远程 Ollama** | 填写你的远程服务器 Ollama 地址，脚本会校验连通性并列出可用模型 |
| **其他本地容器** | vLLM / LM Studio / LocalAI / llama.cpp 等 OpenAI 兼容容器，填写地址后自动探测 `/models` 并注册其全部模型 |
| **云端 API** | 豆包 / 智谱 / Kimi / MiniMax 填入 API Key 即可，之后可在 Admin 面板「端口模型配置」中选用 |

API Key 仅写入本仓库 `.env`（已被 `.gitignore` 忽略）。请勿将真实 IP、密码、API Key 提交到公开仓库。

### 启动服务

配置完成后按脚本提示启动：

- **Windows**：`start_services.bat`（内部调用 `deploy/start.py`）
- **Linux**：`deploy/start.sh`

启动器按已保存的配置拉起全部服务，二次启动无需重新配置。

### 快速模式（自动化）

```bash
python deploy/setup.py --quick        # 全部使用默认值，无交互（适合 CI/自动化）
python deploy/setup.py --skip-deps    # 跳过依赖安装
```

`--quick` 模式：端口沿用当前配置，Ollama 用默认地址并探测，云端 API 全部跳过，适合无人值守部署。

### 访问地址

| 服务 | 默认地址 |
|:---|:---|
| GOAI 学习 Web | http://localhost:5000 |
| 教师门户 | http://localhost:5001 |
| 框架终端 | http://localhost:18080 |
| REST API | http://localhost:18081 |
| 模型管理 | http://localhost:18082 |

### 排障提示

- **提示缺少 PyYAML**：执行 `pip install pyyaml`（或 `pip install -r requirements.txt`）后重试
- **Ollama 探测失败**：确认 Ollama 已启动（`ollama serve`）且地址正确；未安装 Ollama 可直接跳过，先使用云端 API
- **端口被占用 / 修改后不生效**：确认 `port_settings` 中 `enabled: true`、端口未被占用，并重启对应服务
- **`.env` 缺失**：脚本会自动从 `.env.example` 复制生成，无需手动创建
- **远程 Ollama 连不上**：确认 `.env` 中 `OLLAMA_BASE_URL` 与 `OLLAMA_URL` 已同步更新（部署脚本会自动写入）

更多细节见 [deploy/README.md](deploy/README.md)。

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
curl http://localhost:18080/health

# 发送聊天请求（messages 为 OpenAI 兼容格式）
curl -X POST http://localhost:18080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "讲解牛顿第二定律"}]}'

# 生成幻灯片内容
curl -X POST http://localhost:18080/api/slides/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "数学：函数"}'

# 生成思维导图
curl -X POST http://localhost:18080/api/mindmap/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "化学：有机化学"}'
```

## 模型训练与部署（完整 Demo 流程）

> 训练在远程 CPU 服务器（`<SERVER_IP>`，14GB RAM）上进行，目标模型为 Qwen2.5-3B CPU 微调。详见 [docs/development_summary.md](docs/development_summary.md)。

```bash
cd <PROJECT_DIR>

# 0) 快速冒烟验证完整管线（模型初始化 → 训练 → 评测，约 200 步）
python scripts/eval_model.py --preset fast_test --steps 200
# 输出：参数量 / 最佳验证 Loss / 困惑度（Perplexity），自定义数据可用 --data data.jsonl

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
├── framework/              # 核心框架
│   ├── model.py            #   GPT-2 风格模型架构
│   ├── config.py           #   训练配置中心
│   ├── tokenizer.py        #   BPE 分词器
│   ├── data.py             #   数据加载器
│   ├── trainer.py          #   训练循环
│   ├── database.py         #   数据库访问层
│   ├── workflow_engine.py  #   学习工作流引擎（五步法编排）
│   ├── admin/              #   管理员模块（认证 / Agent 管理）
│   ├── security/           #   安全模块（防火墙 / 网关 / 沙箱）
│   ├── api/                #   REST API 服务
│   │   ├── server.py       #   Flask 服务器（三端口）
│   │   └── routes/         #   路由（chat/slides/mindmap/...）
│   ├── engines/            # 智能引擎
│   │   └── feynman_engine.py   #   费曼五步学习法引擎
│   ├── core/               # 核心模块
│   │   ├── config.py       #   配置管理
│   │   └── router.py       #   模型路由
│   ├── models/             # 模型提供者
│   │   ├── base.py         #   抽象基类
│   │   ├── ollama_provider.py  #   Ollama API实现
│   │   └── registry.py     #   模型注册表
│   ├── services/           # 服务层
│   │   ├── chat_service.py #   聊天服务
│   │   ├── provider_service.py # 云端提供商管理
│   │   └── knowledge_retrieval.py # RAG 关键词检索（Day 3）
│   └── airllm/             # AirLLM优化模块
│       ├── attention.py    #   GQA注意力
│       └── rope.py         #   RoPE位置编码
├── remote/templates/       # 前端页面
│   ├── classroom.html      #   课堂模式
│   ├── lumiterm.html       #   对话终端
│   ├── admin.html          #   管理面板
│   └── teacher.html        #   教师门户
├── deploy/                 # 一键部署工具
│   ├── setup.py            #   配置引导脚本
│   ├── start.py            #   统一启动脚本
│   ├── stop.py             #   停止脚本
│   └── README.md           #   部署说明
├── data_management/        # 数据管线
├── scripts/                # 训练/部署脚本
│   ├── train_real.py       #   真实数据 LoRA 训练（CPU）
│   └── merge_and_test.py   #   LoRA 合并 + 推理测试
├── docs/                   # 学习笔记 & 研究文档（含 PROGRESS.md 进度）
├── notebooks/              # Jupyter 教程
├── skills/                 # 技能模块
├── config/                 # 配置文件
│   ├── framework.yaml      #   框架配置
│   └── providers.yaml      #   云端提供商配置
├── goai_web.py             # GOAI 学习 Web（端口 5000）
├── goai_multi_agent.py     # 多 Agent 协作系统（教学→评分→建议）
├── teacher_portal.py       # 教师门户（端口 5001）
├── goai_agent.py           # GOAI 教育智能体（CLI）
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

## 合规与隐私说明

- 本仓库**不含任何真实凭据**：不含真实 IP、服务器地址、密码、API Key 等敏感信息；文档与示例中的地址（如 `localhost`、`192.168.x.x`）均为占位符。
- 运行期配置（Ollama 地址、云端 API Key 等）统一通过根目录 `.env` 完成，`.env` 已被 [.gitignore](.gitignore) 忽略、不会随仓库提交；初始模板见 `.env.example`，云端提供商的占位配置见 `config/providers.yaml`。
- 请勿将真实密钥、内网 IP、服务器登录凭证提交到 GitHub 等公开平台；如需对外展示，请先以脱敏占位符替换并复查后再提交。

## 许可证

[MIT License](LICENSE)

---

**最后更新**：2026-08-11