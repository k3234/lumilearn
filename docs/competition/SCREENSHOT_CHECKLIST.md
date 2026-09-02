# LumiLearn 项目截图素材清单

> 用于 APAI 视频演示和 Word 设计文档的截图收集指南

---

## 必需截图清单

### A. 系统概览（3 张）

| # | 截图内容 | 说明 | 优先级 |
|---|---------|------|--------|
| A1 | README 首页（SDG4 关联部分） | 展示项目定位和社会价值 | ⭐⭐⭐ |
| A2 | 系统架构图 | 五层架构图（来自 ARCHITECTURE.md 或 README） | ⭐⭐⭐ |
| A3 | 性能数据面板 | 591 测试通过 + CPU 推理速度 + 内存占用 | ⭐⭐⭐ |

### B. 核心功能演示（6 张）

| # | 截图内容 | 说明 | 优先级 |
|---|---------|------|--------|
| B1 | 课堂模式首页 | classroom.html 三栏布局 | ⭐⭐⭐ |
| B2 | 费曼五步教学面板 | 五步学习流程切换 | ⭐⭐⭐ |
| B3 | 引导式学习（学生端 5010） | 提问 → 学生回答 → AI 调整引导 | ⭐⭐⭐ |
| B4 | 多 Agent 协作结果 | 教学 + 评分 + 建议聚合报告 | ⭐⭐⭐ |
| B5 | Trace 可视化面板 | Admin 后台的 Agent 调用链 | ⭐⭐ |
| B6 | 学习分析仪表盘 | 掌握度趋势 + 薄弱点排行 | ⭐⭐ |

### C. 技术细节（4 张）

| # | 截图内容 | 说明 | 优先级 |
|---|---------|------|--------|
| C1 | RAG 知识库检索 | /api/knowledge/search 结果 | ⭐⭐ |
| C2 | 同义词扩展 | synonym_dict.py 内容 | ⭐ |
| C3 | Self-Critique 评分 | 评分结果示例 | ⭐⭐ |
| C4 | 自动化评测报告 | eval_report_*.html | ⭐⭐ |

### D. 部署与安全（2 张）

| # | 截图内容 | 说明 | 优先级 |
|---|---------|------|--------|
| D1 | 健康检查输出 | health_check.py 结果 | ⭐⭐ |
| D2 | 安全审计结果 | SECURITY_LOCAL_AUDIT 摘要 | ⭐ |

### E. TRL 证据（2 张）

| # | 截图内容 | 说明 | 优先级 |
|---|---------|------|--------|
| E1 | 服务器监控 | CPU/内存占用截图 | ⭐⭐⭐ |
| E2 | 多端口并发 | 7 个端口同时运行 | ⭐⭐ |

---

## 截图获取方法

### 方法一：浏览器手动截图

1. 启动服务：`python -m framework.api.server --multi-port`
2. 依次访问各页面，用浏览器开发者工具截图或系统截图工具
3. 保存为 `docs/competition/screenshots/` 目录

### 方法二：自动化截图（推荐）

使用项目已有的 browser walkthrough 脚本：
```bash
python3 scripts/_browser_walkthrough.py
```
截图保存至 `docs/evidence/` 目录（已有 16 张）。

### 方法三：API 响应截图

对于 API 类截图，使用 curl + 终端录制：
```bash
# 示例：获取 RAG 检索结果
curl http://localhost:18080/api/knowledge/search?q=勾股定理
```

---

## 截图命名规范

```
docs/competition/screenshots/
├── A1_readme_sdg4.png
├── A2_architecture.png
├── A3_performance.png
├── B1_classroom.png
├── B2_feynman_steps.png
├── B3_guided_learning.png
├── B4_multi_agent.png
├── B5_traces.png
├── B6_analytics.png
├── C1_rag_retrieval.png
├── C2_synonyms.png
├── C3_self_critique.png
├── C4_eval_report.png
├── D1_health_check.png
├── D2_security_audit.png
├── E1_server_monitor.png
└── E2_multi_port.png
```

---

## 视频截图序列（3 分钟演示）

| 时间段 | 截图 | 用途 |
|--------|------|------|
| 0:00-0:25 | A1 + A3 | 开场 + 性能数据 |
| 0:25-0:55 | A2 | 架构图 |
| 0:55-1:40 | B1 → B2 → B3 → B4 | 演示流程 |
| 1:40-2:20 | E1 + E2 | 低配验证 |
| 2:20-3:00 | A1 | 总结 |

---

## 已有素材

以下素材已存在，可直接使用：
- `docs/evidence/` — 16 张浏览器走查截图
- `docs/RUNNING_EVIDENCE.md` — 运行证据文档
- `docs/CPU_LOWMEM_EVALUATION.md` — 性能数据
- `reports/eval_report_*.html` — 自动化评测报告

---

*清单创建时间：2026-09-02*
