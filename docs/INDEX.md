# LumiLearn 文档索引

> 本文件整理仓库文档结构，方便评审和贡献者快速找到所需内容。

---

## 竞赛材料（必读）

| 文档 | 路径 | 说明 |
|---|---|---|
| GOAI 提交材料 | [GOAI_SUBMISSION.md](GOAI_SUBMISSION.md) | 参赛项目完整提交文档 |
| 技术方案 | [GOAI_TECHNICAL.md](GOAI_TECHNICAL.md) | 系统架构、Agent 设计、技术细节 |
| V2.5 技术总结 | [V25_COMPETITION_TECHNICAL_REPORT.md](V25_COMPETITION_TECHNICAL_REPORT.md) | 竞赛版本核心能力与测试数据 |
| 风险评估 | [../RISK-STATEMENT.md](../RISK-STATEMENT.md) | AI 幻觉风险、教育边界、隐私声明 |
| 评测报告 | [evaluation-report.md](evaluation-report.md) | 自动化测试 + 学科评测数据 |
| 发布说明 | [PRESS_RELEASE.md](PRESS_RELEASE.md) | 项目简介与功能总览 |

---

## 技术文档

| 文档 | 路径 | 说明 |
|---|---|---|
| 系统架构 | [ARCHITECTURE.md](ARCHITECTURE.md) | 五层架构图、模块接口表、依赖说明 |
| RAG 设计 | [rag_design.md](rag_design.md) | 知识检索、同义词扩展、语义检索占位 |
| 部署指南 | [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | pip/Docker/端口配置完整说明 |
| 模型下载 | [MODEL_DOWNLOAD.md](MODEL_DOWNLOAD.md) | Ollama 模型安装、GGUF 导入步骤 |
| 模型对比 | [MODEL_COMPARISON.md](MODEL_COMPARISON.md) | lumilearn-v2 vs qwen2.5 vs DeepSeek |
| 远程部署 | [REMOTE_DEPLOYMENT.md](REMOTE_DEPLOYMENT.md) | 天虹服务器部署记录 |
| 运行时规划 | [runtime-roadmap/spec.md](runtime-roadmap/spec.md) | V2.5 开发规格 |
| 竞赛规划 | [runtime-roadmap/competition-plan.md](runtime-roadmap/competition-plan.md) | 竞赛版本专项计划 |

---

## 评测与运行证据

| 文档 | 路径 | 说明 |
|---|---|---|
| 评测结果 | [EVALUATION_RESULTS.md](EVALUATION_RESULTS.md) | 真实环境教学推理、多 Agent、RAG 运行记录 |
| 跑测证据 | [RUNNING_EVIDENCE.md](RUNNING_EVIDENCE.md) | 前端运行截图、API 响应记录 |
| CPU 低配评测 | [CPU_LOWMEM_EVALUATION.md](CPU_LOWMEM_EVALUATION.md) | 34 tok/s 推理速度、1.77GB 内存峰值实测 |
| 安全审计报告 | [SECURITY_LOCAL_AUDIT_20260817.md](SECURITY_LOCAL_AUDIT_20260817.md) | 隐私扫描、安全修复记录 |
| 合规清单 | [compliance_checklist.md](compliance_checklist.md) | 数据合规、权限分级、审计流程 |

---

## 开发日志（参考）

| 文档 | 路径 | 说明 |
|---|---|---|
| 学习笔记 | [learning_journey/README.md](learning_journey/) | 模块学习记录，按主题组织 |
| 研究文档 | [research/](research/) | 市场调研、竞品分析、技术调研 |
| 进度记录 | [DEVELOPMENT_SUMMARY_20260818.md](DEVELOPMENT_SUMMARY_20260818.md) | 阶段性开发总结 |
| 计划文档 | [superpowers/plans/](superpowers/plans/) | 功能开发计划（计划模式生成） |

---

## 快速导航

```
docs/
├── 竞赛材料（必读）
│   ├── GOAI_SUBMISSION.md        ← 参赛提交主文档
│   ├── GOAI_TECHNICAL.md          ← 技术方案详情
│   ├── V25_COMPETITION_TECHNICAL_REPORT.md ← 竞赛版本总结
│   ├── evaluation-report.md       ← 自动化评测报告
│   ├── PRESS_RELEASE.md           ← 项目发布说明
│   └── ../RISK-STATEMENT.md       ← 根目录风险声明
├── 技术文档
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT_GUIDE.md
│   └── ...
├── 评测与证据
│   ├── EVALUATION_RESULTS.md
│   ├── CPU_LOWMEM_EVALUATION.md
│   └── SECURITY_LOCAL_AUDIT_20260817.md
└── 开发日志
    ├── learning_journey/
    └── research/
```
