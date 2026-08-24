# Changelog

所有重要变更将记录在此文件中。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

## [Unreleased]

### Added
- 多 Agent 协作系统（FeynmanTeacher + ScoreAgent + CoachAgent）
- RAG 知识库检索（纯 Python BM25，零外部依赖）
- 教师端学习分析仪表盘（掌握度趋势、薄弱点热力图）
- 数据合规导出功能（申请→审批→下载）
- Admin 面板 Agent 管理可视化

### Changed
- 优化多 Agent 推理速度（284s → 56.9s）
- 统一端口配置系统

### Security
- 全面清理 SSH 密码和服务器 IP（移除约 400 个文件）
- 加强 .gitignore 排除规则
- 移除本地调试脚本中的硬编码凭据

---

## [2026-08-14] - v1.2.0

### Security Fixes
- **移除 166 个含 SSH 凭据和真实 IP 的文件**（`2b642c0`）
- **移除 2 个安全风险脚本**（密码暴力破解、路径遍历）（`444a335`）
- 新增 .gitignore 规则：`scripts/_*.py`、`*.deploy*.py`、`*.ssh*.py` 等

### Added
- SECURITY.md 安全声明
- REPO_AND_VIDEO_CHECK_REPORT.md 仓库安全检查报告

---

## [2026-08-13] - v1.1.0

### Added
- **测试框架搭建**（`89a8816`）
  - tests/test_lumilearn_agent.py（902行，覆盖完整 LumiLearn 流程）
  - tests/test_database.py（核心 CRUD 测试）
  - tests/test_workflow_engine.py（工作流引擎测试）
- **chat_history 多轮对话持久化**
- **bare except 清理**
- **health_check.py** 服务健康检查

### Changed
- 修复 inference_server.py 语法错误
- 优化多 Agent 协作系统
- 修复 Admin 面板 no-cache 缓存问题

### Security
- 全面脱敏：远程/remote 路径清理（`63429d7`）
- 移除录屏脚本和隐私信息（`fa465a4`）
- 全仓库隐私清理与文档整理（`6528a0d`）

---

## [2026-08-12] - v1.0.3

### Added
- **RAG 知识库**（`b456e84`）
  - 1166 条 published 数据
  - 关键词倒排索引 + 简化 BM25
  - RAG 来源展示
- **多 Agent 速度优化**
  - num_predict 限长修复（284s → 56.9s）
- **评分修复**

### Changed
- 同步全部修复与参赛材料

---

## [2026-08-11] - v1.0.2

### Added
- **5010 引导式学习**（`802c60e`）
  - 苏格拉底式交互
  - 对话历史持久化
  - 推理日志入库
- **Admin 面板 no-cache 缓存修复**

---

## [2026-08-10] - v1.0.1

### Fixed
- 修复 classroom 互动教学本地化 CDN（`71dd107`）
- 修复错误文件展示（README 大小写死链）

---

## [2026-08-09] - v1.0.0

### Added
- **基础框架**
  - 费曼五步教学法引擎
  - 多模型调用（Ollama + 云端 API）
  - 学习报告生成
- **前端界面**
  - 课堂模式（classroom.html）
  - 对话终端（lumiterm.html）
- **测试覆盖**
  - 多 Agent 专项测试（26/26 通过）
  - 任务三专项测试（56/56 通过）
  - 全产品回归测试（124/124 通过）

### Performance
- CPU 推理：26.4 tok/s
- 峰值内存：1.77 GB
- 单次推理：2-6 秒

---

## [2026-05-29] - v0.1.0 (Initial)

### Added
- 自研微型 Transformer 模型（8M 参数）
- 数据管道（data_management/）
- 基础推理引擎
