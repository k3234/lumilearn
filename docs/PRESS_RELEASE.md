# LumiLearn 发布说明

> **发布日期**：2026-08-21
> **版本**：V2.5（竞赛版）
> **许可证**：MIT License
> **项目地址**：https://github.com/k3234/lumilearn

---

## 一句话简介

**LumiLearn** 是一款面向中学理科教育的多智能体学习平台，可在普通 CPU 上完整运行——无需 GPU，无需高价云服务，让每一位学生都能拥有自己的 AI 教师。

---

## 解决的问题

教育 AI 产品普遍依赖云端大模型，对算力要求高、需要持续付费。在资源不足的学校和家庭，这种门槛把学生挡在了 AI 教育之外。

LumiLearn 打破了这道门槛：

- **CPU 可训可推**：自研的 lumilearn-v2 模型（1.5B 参数）在普通笔记本 CPU 上以 34 tokens/秒 的速度推理，单条回答 3.5 秒出结果
- **本地化数据**：学习记录、对话历史全部存储在本地 SQLite，不上传任何第三方
- **零付费运行**：使用本地 Ollama 部署，无需 API Key，无需月费

---

## 核心功能

| 功能 | 说明 |
|---|---|
| 费曼五步法教学 | FeynmanTeacher Agent 按"引入→建模→推导→冲突→测试"五步生成互动内容 |
| 多 Agent 协作 | FeynmanTeacher + ScoreAgent + CoachAgent 三路协同，自动评测与学习建议 |
| RAG 知识检索 | 纯 Python 实现，内置同义词词典扩展，无需向量数据库 |
| Self-Critique 自评 | 输出质量 0-100 分，低于 70 分自动重试，最多 2 次 |
| Trace 可视化 | 所有推理日志落库，Admin 面板可回溯完整调用链 |
| 学生端 | 学习交互、错题记录、学习报告、章节测验 |
| 教师端 | 班级管理、作业发布、批改统计、学情分析 |
| 管理员面板 | 知识库管理、Agent 配置、训练上传、系统监控 |
| 数据分析仪表盘 | 学习进度、错题分布、知识点掌握度可视化 |

---

## 技术亮点

1. **纯 CPU 训练 + 推理**：8M 参数自研 Transformer 从零训练；1.5B 微调模型可在 4GB 内存机器上流畅运行
2. **多模型兼容**：本地 Ollama（lumilearn-v2 / qwen2.5:7b）+ 云端 API（DeepSeek / 豆包 / GLM）无缝切换
3. **一键部署**：pip install 一行启动；提供 Docker Compose 完整编排；支持 --mode lite 低配模式
4. **完整可观测性**：pytest 569 测试用例通过；自动化评测 150 题跑通；所有 trace 落库可查
5. **安全合规**：环境变量注入密钥，无硬编码；本地 SQLite 存储；《风险声明》完整披露

---

## 开发者

LumiLearn 由一名**高中生独立开发**，从模型训练、Agent 系统、Web 前后端到部署脚本全部亲手实现。项目始于 2025 年 6 月，历经 122 次提交，持续迭代至今。

---

## 如何开始

```bash
# 克隆仓库
git clone https://github.com/k3234/lumilearn.git
cd lumilearn

# 安装依赖
pip install -r requirements.txt

# 拉取模型
ollama pull lumilearn-v2:latest

# 启动
python lumilearn_web.py --mode lite
```

详细部署指南见 [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)。

---

## 开源协议

本项目采用 **MIT License**，欢迎学习、研究、二次开发。  
商用请联系作者获取授权。

---

*本发布说明适用于 LumiLearn 2026 竞赛参赛版本（V2.5）。*
