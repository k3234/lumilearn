# LumiLearn 项目进度

> 最后更新: 2026-08-10
>
> 本文档基于仓库实际内容整理（README / framework.yaml / 代码模块 / 模型对照表 / CHANGELOG / git log），不包含任何内网 IP、密码或敏感信息。

## 一、模块进度总览

| 模块 | 功能说明 | 完成度 | 运行端口 | 状态 |
|------|---------|--------|---------|------|
| GOAI 学习智能体 | 教育智能体核心引擎：任务理解（学科/难度/类型识别）、流程编排（费曼五步教学法）、Agent 工具调用（多模型并行 + AI 评分）、学习报告交付（掌握度+薄弱点+建议）；另有 LangGraph 多模型编排引擎（12 个模型并行调用→汇总投票） | ✅ | 5000（经 GOAI Web 调用） | 运行中 |
| 框架终端（LumiTerminal） | 轻量聊天界面，支持多轮对话，非流式 Ollama 代理；随 Admin 面板共享 | ✅ | 18080 | 运行中 |
| REST API | Flask 多端口服务器，15 个蓝图路由：chat / slides / mindmap / feynman / ocr / speech / voicebox / review / resources / animation / providers / payment / security / admin 等 | ✅ | 18081 | 运行中 |
| 模型管理（Admin 面板） | 管理员认证、用户/Agent/模型管理、系统监控；模型管理拆分为「本地模型 / 云端提供者 / 端口模型配置」三个子标签页，支持端口选择性配置（启停/改端口） | ✅ | 18082 | 运行中 |
| GOAI Web（学习 Web + 服务仪表盘） | Flask 后端 + 单页前端，用户登录、提交学习目标生成学习报告（持久化到 learning_reports 表）、学习历史查看、服务仪表盘 | ✅ | 5000 | 运行中 |
| 教师门户 | 独立 Flask 应用（共享 lumilearn.db，教师账号登录）：班级管理（学校/年级/班级三级）、学生管理、学习监控（报告/掌握度/薄弱点）、任务管理、教学资源 | ✅ | 5001 | 运行中 |
| 费曼引擎 | 费曼五步学习法（现象引入→认知冲突→思维模型→自主推导→30 秒测试），配套模板库；另集成学习工作流引擎（五步编排+数据库持久化）与输出检测系统（五维评分+引导式强化） | ✅ | —（随框架 API 18080） | 运行中 |
| 手写识别 / OCR | PaddleOCR 图片文字识别服务（支持 .png/.jpg/.jpeg/.webp，懒加载），路由 `/api/ocr` | ✅ | —（经 REST API 18081） | 完成 |
| 语音 / 字幕 | Whisper 语音转文字（tiny 模型，懒加载）+ 语音合成（speech / voicebox 两套端点，edge-tts） | ✅ | —（经 REST API 18081） | 完成 |
| 训练系统 | 从零训练（V1 8M CPU）+ LoRA 微调（train_real.py / train_lora_gpu.py / train_cpu.py，Qwen2.5 LoRA）+ GGUF 转换（convert_hf_to_gguf.py）+ Ollama 部署（_deploy_ollama_remote.py / _upload_gguf.py）+ 评测（eval_model.py） | ✅ | —（CLI 脚本） | 完成（CPU 训练速度慢，已产出可用模型） |
| 安全系统 | 网络隔离（内网网段白名单/黑名单）、API 网关（限流/突发限制/请求体大小）、代码沙箱（受限模块/路径/超时）、防火墙规则、CSP 策略、API Key 认证 | ✅ | —（中间件，随主服务） | 完成 |
| 学习笔记 / 文档体系 | 学习旅程笔记（docs/learning_journey/，含 Whisper/OCR/Prompt/前端等模块）、研究报告（docs/research/，20+ 篇）、Jupyter 教程（notebooks/）、技能模块（skills/） | ✅ | — | 持续补充中 |

## 二、服务部署信息

| 服务 | 端口 | 启动命令 | 访问地址 | 默认状态 |
|------|------|---------|---------|---------|
| Ollama 模型服务 | 11434 | `ollama serve`（remote_start_all.sh 自动确认/启动） | http://localhost:11434 | ✅ 启用（核心依赖） |
| 框架终端 + Admin 面板 | 18080 | `python -m framework.api.server --multi-port` | http://localhost:18080（/admin） | ✅ 启用 |
| REST API（纯接口） | 18081 | 同上（随 --multi-port 一起启动） | http://localhost:18081/health | ✅ 启用 |
| 模型管理服务 | 18082 | 同上（随 --multi-port 一起启动） | http://localhost:18082 | ✅ 启用 |
| GOAI Web 学习平台（学生端） | 5000 | `python goai_web.py` | http://localhost:5000 | ✅ 启用 |
| 教师门户 Teacher Portal | 5001 | `python teacher_portal.py` | http://localhost:5001 | ✅ 启用 |
| 学生端学习平台 Student Portal | 5010 | `python student_portal.py` | http://localhost:5010 | ✅ 启用 |
| 学习分析仪表盘 Analytics | 18090 | `python analytics_dashboard.py` | http://localhost:18090 | ✅ 启用 |

- **Windows 一键启动**：`start_services.bat`（检查 Python → 委托 `deploy/start.py` 按 `config/framework.yaml` 的 `port_settings` 与 `.env` 启动启用的服务 → 自动打开浏览器）
- **停止服务**：`stop_services.bat`（按进程名查杀 goai_web / framework.api.server）
- **远程服务器一键启动**：`bash scripts/remote_start_all.sh`（初始化数据库 → 确认/启动 Ollama → 按 framework.yaml 的 port_settings 选择性启动各端口服务，带幂等检查与状态汇总）
- **端口配置**：`config/framework.yaml` 的 `port_settings` 节（terminal/api/models/goai_web/teacher_portal 各含 enabled + port），Admin 面板「端口管理」可在线修改；Ollama 地址通过环境变量 `OLLAMA_URL` / `OLLAMA_BASE_URL` 覆盖（默认 localhost:11434），避免硬编码内网地址

## 三、模型资产清单

> 主数据来源：docs/MODEL_COMPARISON.md（2026-08-10 脱敏版）+ MODEL_COMPARISON_CN.md。

| 模型 | 架构/基座 | 参数量 | 量化 | 大小 | 位置 | 状态 | 用途 |
|------|----------|-------|------|------|------|------|------|
| **lumilearn-v2:latest** | Qwen2 | 1.5B | Q8_0 | 1.65 GB | 远程服务器 Ollama + 本地 GGUF | ✅ 生产运行 | 主力教学模型（默认，671 条真实教学问答 LoRA 微调） |
| lumilearn-v2-f16 | Qwen2 | 1.5B | F16 | 3.09 GB | 本地 GGUF | ⏸ 未使用 | 高精度版本 |
| merged_model_15b_v2 | Qwen2 | 1.5B | bf16 | 2.87 GB | 本地 HuggingFace | ⏸ 未使用 | 继续训练 / 微调基座 |
| merged_model_15b | Qwen2 | 1.5B | bf16 | 2.87 GB | 本地 HuggingFace | ⏸ 未使用 | V1 合并模型 |
| lumilearn-merged | Qwen2 | 3.1B | F16 | 6.18 GB | 远程服务器 Ollama | ⏸ 未使用 | 早期合并实验 |
| qwen2.5:7b | Qwen2 | 7.6B | Q4_K_M | 4.68 GB | 远程服务器 Ollama | ✅ 备用 | 复杂推理 / 数学 |
| lumilearn-v5:real | Llama | 33.27M | — | 133 MB | 远程服务器 Ollama | ⏸ 保留 | 从零训练极小模型 |
| lumilearn-v5:latest | GPT-2 | 27.32M | — | 110 MB | 远程服务器 Ollama | ⏸ 保留 | 轻量对话 / 快速原型 |
| lumilearn-v5:test | GPT-2 | 21.01M | — | 84 MB | 远程服务器 Ollama | ⏸ 保留 | 快速原型验证 |
| lumilearn-v4 | Llama | 23.38M | — | 94 MB | 远程服务器 Ollama | ⏸ 保留 | 早期迭代 |
| lumilearn-v3 | Llama | 23.38M | — | 94 MB | 远程服务器 Ollama | ⏸ 保留 | 早期迭代 |
| LumiLearn v1 | GPT-2 style（自研） | 8.03M | — | 33 MB | CPU / Ollama（GGUF） | ✅ 可用 | 边缘设备讲解（超小体积） |
| Qwen2-0.5B Choice LoRA | Qwen2-0.5B | 504M（LoRA 可训练 8.8M） | — | 49 MB | CPU / GPU | ✅ 可用（选择题准确率 71.27%） | 选择题专项生成 |
| DeepSeek 1B | DeepSeek | ~1B | — | 14 GB | 训练产物（merged / adapter 多版本） | ✅ 可用 | 通用对话 |
| LumiLearn 7B | — | ~7B | — | 8 KB（仅占位符） | 本地 | ❌ 未完成 | 规划中 |

**训练数据**：V2 使用真实教学问答（CSV + SFT + 教材，671 条，3 epochs）；V1 使用合成模板数据（703 条）；LoRA 配置 r=16 / alpha=32；训练设备为远程服务器 CPU（R7-7840HS，14GB RAM 无 GPU，峰值内存 ~11.4GB，V1 微型模型 8M 参数从零训练）。

**推理性能（远程服务器 CPU）**：lumilearn-v2:latest 约 26.4 tok/s（~38ms/tok）；qwen2.5:7b 约 8-12 tok/s；v2-f16 约 9.7 tok/s。

## 四、开发里程碑

| 日期 | 里程碑 | 说明 |
|------|--------|------|
| 2026-05-17 | V1 模型训练完成 | 8M 参数微型 Transformer，CPU 从零训练（BPE tokenizer + GPT-2 风格架构） |
| 2026-05-29 | 框架初建 | 自研 Transformer 框架 + BPE 子词分词器 + 智能讲解引擎 |
| 2026-05-31 | 引导式学习模式 | Koji 风格"不给答案"逆向教学法 |
| 2026-06-01 | 费曼引擎与 V3/V4/V5 迭代 | 费曼五步教学引擎（feynman_engine.py）+ V3/V4/V5 小模型迭代（GGUF 格式，Ollama 部署） |
| 2026-06-06 | Distil 蒸馏模型首次训练 | Qwen2.5-3B LoRA CPU 训练（远程服务器），攻克 OOM（自定义训练循环，内存 13.5GB→7.2GB） |
| 2026-06-15 | 项目聚焦冻结 | 归档支付/语音/冗余脚本，聚焦 CPU 微型模型 V1.0 核心 |
| 2026-08-03~04 | 服务层与开源整理 | 15 个 API 蓝图 + 模型服务层（注册表/Ollama 提供者/路由）；CI（ruff + pytest）、单元测试、README、MIT 许可证 |
| 2026-08-05 | DeepSeek 1B + GOAI Agent | DeepSeek 1B 训练完成；GOAI 教育智能体核心引擎（任务理解/流程编排/工具调用） |
| 2026-08-07 | 综合数据 LoRA 训练 + 评估 | 综合数据 LoRA 训练（远程服务器 CPU）；模型开发现状评估（整体 ~80%）；管理员管理系统 + Agent 注册表；学习工作流引擎 + 输出检测系统；学生学习输出检测分析 |
| 2026-08-08 | V2 高质量数据训练 + Ollama 部署 | 真实教学问答 LoRA 训练完成，GGUF Q8_0 转换并部署远程服务器 Ollama（lumilearn-v2:latest 主力上线）；GOAI 演示 + CPU/GPU 训练脚本 |
| 2026-08-09 | 服务仪表盘 + 一键启动 | 服务仪表盘与一键启动/停止脚本（Windows start_services.bat / 远程 remote_start_all.sh）；教师端部署脚本；移除硬编码内网 IP（改用环境变量） |
| 2026-08-10 | 隐私脱敏与仓库整理 | 敏感字样全面脱敏（统一为"远程服务器/remote"，清理 IP / GitHub 用户名 / 服务器路径 / 录屏脚本）；新增教师门户、学校-年级-班级组织架构、AI 思维导图与幻灯片生成、云端提供者接入（7 家模板 + API Key 安全存储）、端口选择性配置；模型对照表 + 全面评估（Choice LoRA 71.27%） |

## 五、下一步计划

- **一键部署脚本（进行中）**：deploy.sh 已支持 Linux/macOS/Docker（系统检测 → 依赖安装 → 虚拟环境 → Ollama 配置 → 启动 + 健康检查），Windows 侧以 start_services.bat 为主，待统一/完善
- **云端模型 API 接入完善**：内置 DeepSeek/OpenAI/智谱/Moonshot/通义千问/SiliconFlow 等 7 家提供者模板与端口模型配置机制，各提供者 API Key 待配置启用（deploy_config.yaml 云端模型默认关闭）
- **本地 Ollama 可选安装**：deploy.sh 已内置 Ollama 安装/启动逻辑，支持本地拉起模型后运行
- **其他（README 路线图待办）**：单元测试覆盖率提升、完整 API 文档站点、演示视频录制、模型量化支持（INT8/INT4）、多语言界面（中/英/日）、安全扫描工具链集成、语义化版本发布规范
