# LumiLearn GOAI 参赛作品
# LumiLearn - AI 教育引擎 + CPU 轻量 Transformer + 费曼五步教学

## GOAI 2026 参赛作品信息

### 作品简介
LumiLearn 是一款面向 AI+教育场景的开源智能教学系统，核心理念是"算力平权"——让没有高端显卡的普通电脑也能流畅运行 AI 教学服务。

### 核心技术栈
- **语言**: Python 3.10+
- **Web框架**: Flask 3.1 + Flask-CORS
- **数据库**: SQLite（零配置，开箱即用）
- **模型推理**: Ollama（本地） + 多云端 API（DeepSeek/智谱/Kimi 等）
- **前端**: 原生 HTML/CSS/JS + 响应式设计
- **测试**: pytest + unittest

### 核心亮点

#### 1. 自研轻量模型（CPU 友好）
- 从零训练 8M 参数微型 Transformer
- Q8_0 量化后仅 8MB，CPU 推理 26+ tok/s
- 峰值内存 1.77GB，老电脑也能跑

#### 2. 费曼学习法编排
- 五步教学法：现象引入 → 认知冲突 → 思维模型 → 自主推导 → 费曼测试
- 交互式单步引导，AI 根据学生回答动态调整

#### 3. 多 Agent 协作（GOAI 评审重点）
- FeynmanTeacher（教学）→ ScoreAgent（评分）→ CoachAgent（建议）
- 独立模型配置、失败降级、agent_trace 状态追踪

#### 4. RAG 知识库
- 纯 Python 实现轻量 BM25 检索
- 零外部依赖，1166 条知识库数据
- 5/5 检索命中率

#### 5. 完整教学闭环
- 任务理解 → 流程编排 → 多模型调用 → 学习报告
- 推理日志落库，可追溯

### 评测结果
- 全量测试：**382/382 通过**
  - pytest 核心：59/59
  - 多 Agent 专项：26/26
  - 任务三专项：56/56
  - 全产品回归：124/124
  - Day3 RAG 专项：18/18
  - 引导式学习：21/21
  - 天虹真实服务测评：37/37
- 真实场景：勾股定理评分 100（59.2s）、多 Agent 56.9s

### 部署方式
```bash
# 一键部署
bash scripts/quick_deploy.sh

# 健康检查
python scripts/health_check.py
```

### 项目地址
https://github.com/k3234/lumilearn

### 演示视频
https://b23.tv/Zn7NNXq

---

### AI 使用声明
本项目在开发过程中使用了 AI 辅助编程工具（Trae CN、DeepSeek、Claude 等），用于代码框架生成和文档整理。开发者负责了系统架构设计、任务拆解、代码审查和验收标准的制定，对全部代码的功能正确性和可维护性负责。

### 开源协议
MIT License
