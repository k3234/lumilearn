# LumiLearn — 在 CPU 上从零训练的微型 AI 教育模型

输入学科和章节，自动生成知识点讲解、练习题和解析。

**全部在 CPU 上训练和推理，无 GPU 也能跑。**

由一名高中学生开发维护。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![pytest](https://img.shields.io/badge/tested%20with-pytest-009688.svg)](https://pytest.org/)
[![Ruff](https://img.shields.io/badge/linted%20with-ruff-ff69b4.svg)](https://docs.astral.sh/ruff/)

## 安全声明

- **AI 辅助教育工具边界**：LumiLearn 是 AI 辅助教学工具，**不替代教师**。AI 生成的知识讲解、练习题与学习报告仅供参考，请由教师/家长/学习者**人工校验后使用**。
- **幻觉风险提示**：大语言模型可能生成看似合理但错误的"幻觉"内容，涉及考试、升学等关键决策时务必以权威教材和教师意见为准。
- **数据本地存储**：学习数据默认存储在本机 **SQLite 数据库**，**不上传云端**；如需调用云端模型，仅按需发送请求文本，请勿提交含个人敏感信息的资料。
- **密钥走环境变量**：所有密钥（API Key、SECRET_KEY、管理员密码等）一律通过环境变量（`.env`）注入，不写入代码或配置文件，且 `.env` 已被 `.gitignore` 忽略、不进入公开仓库。

## 📋 GOAI 2026 参赛材料

- [作品简介](docs/GOAI_SUBMISSION.md) — 可直接复制到 GOAI 作品提交页面「作品简介」字段
- [参赛技术方案](docs/GOAI_TECHNICAL.md) — 项目定位 / 架构 / 技术路线 / 创新点
- [部署指南](docs/DEPLOYMENT_GUIDE.md) — 一键部署与手动部署（含健康检查）
- [评测结果](docs/EVALUATION_RESULTS.md) — 全量测试与真实环境测评数据
- [CPU 低配测评](docs/CPU_LOWMEM_EVALUATION.md) — CPU/低内存运行能力实测（34 tok/s、峰值内存 1.77GB）
- [运行证据](docs/RUNNING_EVIDENCE.md) — 服务状态 / API 实测 / 数据落库证据
- [模型下载](docs/MODEL_DOWNLOAD.md) — lumilearn-v2 获取与 Ollama 导入
- [AI 使用声明](AI-DECLARATION.md) — AI 参与方式与责任声明

## 10 秒看懂

| 问题 | 答案 |
|---|---|
| **做什么？** | 自研微型 Transformer 模型 + 前端教学演示系统，自动生成数学/物理/化学的讲解内容 |
| **为什么特别？** | 全部在 CPU 上训练（8M 参数），从 tokenizer 到推理全部自己实现 |
| **适合谁？** | 想学习"从数据到模型到部署"完整流程的学生开发者 |
| **教育价值** | 让老旧设备也能跑 AI 教学演示，推动"算力平权"，让资源不足的学校也能接触 AI 教育 |

## ⚡ 快速开始

```bash
# 安装依赖
pip install -r goai_requirements.txt

# 标准模式启动（竞赛演示，默认）
python goai_web.py

# Lite 模式启动（轻量自学，仅保留核心学习流程）
python goai_web.py --mode lite
```

启动后浏览器访问 `http://localhost:5000` 进入 GOAI 学习 Web（端口可用环境变量或端口配置调整）。两种模式的差异见下方「模式说明」。

## 🧭 模式说明

LumiLearn 提供两种运行模式，按使用场景选择：

| 模式 | 使用场景 | 启动命令 |
|---|---|---|
| **标准模式（竞赛演示）** | GOAI 竞赛演示、完整功能展示，启用全部服务（终端 / API / 学生端 / 教师端 / 分析仪表盘 / Admin 等） | `python goai_web.py` |
| **Lite 模式（轻量自学）** | 个人轻量自学、低资源设备，聚焦「导入 → 学习 → 复盘」核心闭环 | `python goai_web.py --mode lite` |

Lite 模式（`--mode lite`）具体表现：

- 关闭演示模块加载，只保留「导入 → 学习 → 复盘」核心流程
- 仅启用 `terminal` / `api` / `student_portal` 三个核心服务，关闭教师端、分析仪表盘等非核心服务，降低资源占用、启动更快

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         前端展示层 (Static/Template)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ classroom.html│  │ lumiterm.html │  │ admin.html   │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         └──────────────────┼──────────────────┘                      │
│                            │                                          │
├────────────────────────────┼─────────────────────────────────────────┤
│                        API 网关层 (Flask Blueprints)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  教学 API     │  │  学习分析 API │  │  Admin API   │              │
│  │  /api/learn  │  │ /api/analytics│  │ /api/admin/* │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         └──────────────────┼──────────────────┘                      │
│                            │                                          │
├────────────────────────────┼─────────────────────────────────────────┤
│                        业务逻辑层 (Framework)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ FeynmanEngine │  │KnowledgeRetr │  │SecurityGW    │              │
│  │ 费曼五步法    │  │ RAG检索      │  │ 速率限制/IP封 │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         └──────────────────┼──────────────────┘                      │
│                            │                                          │
├────────────────────────────┼─────────────────────────────────────────┤
│                        Agent 协作层 (Multi-Agent)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ FeynmanAgent │  │ScoreAgent    │  │CoachAgent    │              │
│  │ 教学         │  │ 评分         │  │ 建议         │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         └──────────────────┼──────────────────┘                      │
│                            │                                          │
├────────────────────────────┼─────────────────────────────────────────┤
│                        模型推理层                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Ollama     │  │  云端 API    │  │ 自研模型     │              │
│  │ qwen2.5:7b   │  │ DeepSeek等   │  │ 8M Transformer│              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

## 快速导航

| 我想... | 去看 |
|---|---|
| 看这个项目长什么样 | [课堂模式演示](remote/templates/classroom.html) · [对话终端](remote/templates/lumiterm.html) |
| 了解系统架构 | [docs/development_summary.md](docs/development_summary.md) |
| 看模型怎么训练的 | `framework/model.py` · `framework/config.py` |
| 看数据怎么处理的 | `data_management/` 目录 |
| 了解开发原则 | [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) |
| 看学习笔记 | [docs/learning_journey/](docs/learning_journey) |
| 看 Jupyter 教程 | [notebooks/](notebooks) |
| 看研究规划 | [docs/research/](docs/research) |
| 了解如何贡献 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 了解版本变更 | [CHANGELOG.md](CHANGELOG.md) |

## 🤖 Agent 智能体

LumiLearn 内置一套可独立启停、统一生命周期的 Agent 框架（`framework/admin/agents.py`），并在 Admin 面板「Agent 管理」中可视化运行；另有一个面向完整学习闭环的 GOAI 教育智能体（`goai_agent.py`）。

| Agent | ID | 能力 |
|---|---|---|
| **费曼教学 Agent** | `feynman_teacher` | 基于费曼五步法讲解知识点；传入对话历史时自动切换为**交互式单步引导** （现象引入 → 认知冲突 → 思维模型 → 自主推导 → 费曼测试），上下文连贯、逐步推进 |
| **输出检测 Agent** | `output_detector` | 检测学生学习输出质量（简洁/准确/比喻/完整/术语五维评分），给出改进建议 |
| **自适应学习 Agent** | `adaptive_path` | 根据学生学习进度与掌握度推荐个性化学习路径 |
| **对话助手 Agent** | `chat_assistant` | 通用多轮对话，自动路由到当前端口配置的模型 |
| **GOAI 教育智能体** | `goai_agent.py` | 任务理解 → 流程编排（费曼五步） → 多模型工具调用 → 完整学习报告（掌握度 + 薄弱点 + 建议），推理过程写入本地推理记录库，供管理员/教师/模型自查 |

所有 Agent 支持 `start / stop / status / run` 统一生命周期，Agent 运行状态持久化到数据库；推理过程（费曼每步、GOAI 学习）自动写入 `reasoning_logs` 推理记录库，可通过 Admin「推理记录」、教师端「推理记录」、API `/api/reasoning-logs` 三方查看。

## 🤖 多 Agent 协作系统（GOAI 评审亮点）

从"单 Agent 四模块串行"升级为"三 Agent 协作编排"（`goai_multi_agent.py`），GOAI 学习 Web（5000 端口）学习页默认调用：

```
学生输入 ─→ FeynmanTeacher（教学）─→ ScoreAgent（评分）─→ CoachAgent（建议）─→ 聚合报告
 │ RAG 检索注入 │ 五维评估 │ 学习路径推荐
 ▼ ▼ ▼
 费曼五步（现象→冲突→模型→推导→测试） 掌握度评分 建议 + 推荐知识点
```

| 特性 | 说明 |
|---|---|
| 独立模型 | 每个 Agent 可配置不同模型（`MULTI_AGENT_*_MODEL` 环境变量，优先读端口配置） |
| 失败降级 | 单 Agent 异常不阻塞后续，`agent_trace` 记录 ok/skipped/failed |
| 交互模式 | 传 `dialogue` 历史时自动切交互式单步引导 |
| 报告落库 | 有评分时写入 `learning_reports`，Admin/教师端可视化可见 |

## 📚 RAG 知识库检索（Day 3）

教学内容"有据可查"：从 `training_data`（已发布教学资源）与 `knowledge_nodes`（知识点）构建**关键词倒排索引** ，纯 Python 实现、零外部依赖、不引入向量数据库。

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

LumiLearn 支持**本地模型容器** 与**云端 API**  两类推理来源，其中 **Ollama 为默认推荐容器** 。全部接入模型可通过 Admin 面板「模型管理」集中配置，并按端口指定各服务使用的模型。

| 来源 | 说明 | 模型发现 |
|---|---|---|
| **Ollama（推荐）** | 本地/远程 Ollama 服务，默认 `http://localhost:11434` | 自动调用 `/api/tags` 发现容器内**全部模型** |
| **其他本地容器** | OpenAI 兼容接口：vLLM / LM Studio / LocalAI / llama.cpp server 等 | 自动调用 `/models` 发现容器内**全部模型** |
| **云端 API** | 豆包 / 智谱 / Kimi / MiniMax / OpenAI / DeepSeek 等（OpenAI 兼容） | 配置时登记模型列表 |

**模型接入** ：运行 `deploy/setup.py` 交互式引导（探测并列出容器内全部模型供选择），或在 Admin 面板「模型管理」中手动添加。

**主要模型资产** ：

| 模型 | 来源 | 用途 |
|---|---|---|
| `lumilearn-v2:latest` | 自研 LoRA 微调（Qwen2.5-1.5B，Q8_0 量化） | 默认对话/学习模型，CPU 推理 26+ tok/s |
| `qwen2.5:7b` | Ollama 官方 | 费曼引导默认模型（上下文利用更强） |
| 微调 Transformer（8M） | 从零训练 | 课堂演示、教学编排 |
| 云端模型（可选） | 各厂商 API | 高质量生成场景 |

**端口模型配置** ：每个端口（终端/API/模型管理/GOAI Web/教师端）可独立指定使用哪个提供商的哪个模型，配置实时生效，无需重启。

## 💡 技术创新

| 创新点 | 位置 | 说明 |
|---|---|---|
| **知识分层拆解流水线** | `agent_core/knowledge_pipeline.py` | 章节粗切 → 知识点细切 → 格式校验 → 去重/冲突检测，将教材文档自动拆解为结构化知识点并落库 |
| **双路校验机制** | `agent_core/verifier.py`（`dual_verify`）+ `agent_core/fact_checker.py`（`verify_question`） | 主模型生成内容，校验子模型独立复核，双重把关输出质量 |
| **Trace + 自动评测闭环** | `agent_core/observability.py`（`eval_metrics` + `system_eval` 表） | 自动统计知识点召回率、出题格式合格率、错题识别准确率，形成可量化的评测闭环 |
| **多基座自适应调度** | `framework/core/router.py`（`TaskType`）+ `agent_core/model_registry.py`（`fallback_chain`） | 按任务类型路由到合适的模型基座，基座失败时自动降级（fallback），保证服务持续可用 |
| **分层记忆系统** | `framework/storage/layered_memory.py` | 短期会话（24 小时过期）/ 中期单元（按章节沉淀）/ 长期错题（持久保存并标记）三层记忆 |
| **SQLite/文件存储双模式** | `framework/storage/file_compat.py` | SQLite 优先、JSON 文件自动降级，接口一致、无缝切换 |

## 🚀 零文件一键部署（无需下载任何文件）

不需要下载、保存任何脚本文件，一行命令完成「克隆/更新仓库 → 配置 → 启动」：

```bash
# Linux / macOS
curl -fsSL https://raw.githubusercontent.com/k3234/lumilearn/master/deploy/install.sh | bash
# 带参数（管道传参用 bash -s --）：--quick 全默认值 / --no-start 只克隆+配置
curl -fsSL https://raw.githubusercontent.com/k3234/lumilearn/master/deploy/install.sh | bash -s -- --quick --no-start
```

```powershell
# Windows PowerShell
irm https://raw.githubusercontent.com/k3234/lumilearn/master/deploy/install.ps1 | iex
# 选项用环境变量：$env:LUMILEARN_QUICK="1"、$env:LUMILEARN_NO_START="1"、$env:LUMILEARN_DIR="D:\lumilearn" 等
```

- 管道模式自动 `--quick` 全默认值；`--no-start` 只克隆+配置、不启动服务
- 仓库/分支可用环境变量 `LUMILEARN_REPO_URL` / `LUMILEARN_BRANCH` 覆盖
- 凭据一律走环境变量（`REMOTE_HOST` / `REMOTE_USER` / `REMOTE_PASSWORD` 或 API Key），脚本不含任何真实 IP / 密码
- 详细说明（参数/环境变量清单、Node.js 可选路径、与 bootstrap.* 的区别）见 [deploy/README.md](deploy/README.md)

## 🐳 Docker 部署（推荐）

```bash
# 一键启动全部服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f api
```

**docker-compose.yml** 配置了以下服务：

| 服务 | 端口 | 说明 |
|---|---|---|
| `api` | 5010 | 主 API 服务 |
| `goai-web` | 5000 | GOAI 学习 Web |
| `teacher` | 5001 | 教师端 |
| `admin` | 18080 | Admin 管理面板 |
| `analytics` | 18090 | 学习分析仪表盘 |
| `ollama` | 11434 | 本地模型推理 |
| `nginx` | 80 | 反向代理（可选） |

数据持久化到 `./data/` 和 `./ollama_data/` 目录。

## 文档索引

| 文档 | 说明 |
|---|---|
| [docs/PROGRESS.md](docs/PROGRESS.md) | 项目进度总览（模块状态 / 部署信息 / 模型资产清单） |
| [docs/admin_guide.md](docs/admin_guide.md) | 管理员系统使用指南 |
| [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | 本地与服务器部署指南（一键部署 + 健康检查） |
| [docs/MODEL_COMPARISON.md](docs/MODEL_COMPARISON.md) | 模型资产对照表（脱敏版） |
| [docs/REMOTE_DEPLOYMENT.md](docs/REMOTE_DEPLOYMENT.md) | 远程部署说明 |
| [docs/rag_design.md](docs/rag_design.md) | RAG 知识库设计说明 |
| [docs/privacy_compliance.md](docs/privacy_compliance.md) | 数据合规说明 |
| [docs/open_source_plan.md](docs/open_source_plan.md) | 开源路线图 |
| [docs/learning_journey/INDEX.md](docs/learning_journey/INDEX.md) | 学习旅程笔记索引 |
| [notebooks/INDEX.md](notebooks/INDEX.md) | Jupyter 教程索引 |
| [deploy/README.md](deploy/README.md) | 一键部署工具说明 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更记录 |
| [docs/SECURITY_LOCAL_AUDIT_20260817.md](docs/SECURITY_LOCAL_AUDIT_20260817.md) | 本地安全审计报告 |
| [docs/ZERO_BASE_SETUP_GUIDE.md](docs/ZERO_BASE_SETUP_GUIDE.md) | 零基础用户配置指南（Windows，15分钟上手） |

## 核心模块

| 模块 | 说明 | 状态 |
|---|---|---|
| **微型 Transformer** | GPT-2 风格，8 层 8 头，自训练轻量模型（framework/trainer.py） | ✅ 可用 |
| **Agent 核心** | 路由 / 费曼教学 / 验证 / 事实核查多智能体（agent_core/） | ✅ 可用 |
| **多智能体编排** | LangGraph 工作流 + 任务队列 + 成本追踪（agent_core/langgraph_engine.py） | ✅ 可用 |
| **安全系统** | 安全网关 / 防火墙 / 代码沙箱 / 上传校验（framework/security/） | ✅ 可用 |
| **Web 应用** | 学生端 / 教师端 / Admin 管理 / 学习分析仪表盘 | ✅ 可用 |
| **部署** | Docker Compose / 一键脚本（deploy/）/ 远程部署（scripts/deploy_remote.py） | ✅ 可用 |

## ⚠️ 系统局限性与未来规划

### 当前局限

- **自研模型能力上限**：8M 参数自研 Transformer 适合演示；实际教学推荐 lumilearn-v2（1.5B）或 qwen2.5:7b
- **评测规模有限**：当前 150 题自动化评测反映种子知识库规模较小；未进行大规模真实课堂试验
- **学科覆盖**：聚焦数理化，语文、英语等其他学科暂不支持
- **Skills 插件**：部分技能模块（hyperframes / rtk）为设计文档阶段，未接入主流程
- **并发测试**：未做高并发压力测试，多用户同时使用时响应时间可能延长

### 完整风险声明

详见 [RISK-STATEMENT.md](RISK-STATEMENT.md)，包含 AI 幻觉风险、教育适用边界、隐私说明、模型依赖风险等完整披露。

### 未来规划

- **V3**：扩充学科（语文/英语/生物），接入真实用户试用反馈，完善 Skills 插件生态
- **V4**：探索多模态（图文混排教学）、离线语音交互、跨设备学习同步
- 详细路线见 [docs/runtime-roadmap/spec.md](docs/runtime-roadmap/spec.md)
