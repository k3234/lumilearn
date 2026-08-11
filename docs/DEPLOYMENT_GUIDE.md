# LumiLearn 部署指南

> 本指南帮助你在任意 CPU 设备上复现 LumiLearn 全套系统。全部服务本地运行、无云依赖。

## 系统要求

| 项 | 最低 | 推荐 |
|---|---|---|
| CPU | 任意 x86_64 | 8 核及以上（16 线程） |
| 内存 | 8 GB | 16 GB |
| 操作系统 | Linux / macOS / Windows (WSL) | Linux |
| Python | 3.10+ | 3.11 |
| 磁盘 | 3 GB | 5 GB |

## 一键部署

```bash
git clone https://github.com/k3234/lumilearn.git
cd lumilearn
bash scripts/quick_deploy.sh
```

脚本自动完成：安装依赖 → 初始化数据库 → 确认模型 → 启动全部服务。

## 手动部署步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取模型

系统核心模型为 `lumilearn-v2`（Qwen2.5-1.5B 教学微调 + Q8_0 量化，约 1.64 GB）。

- 方式一（推荐）：已有任意 Ollama 可用的 Qwen2.5 系列模型时，直接配置端口模型即可（Admin 面板「模型管理」→「端口模型配置」）
- 方式二：按 [docs/MODEL_DOWNLOAD.md](MODEL_DOWNLOAD.md) 获取量化模型文件，用 Ollama 导入：
  ```bash
  ollama create lumilearn-v2 -f Modelfile
  ```
- 方式三（零模型快速体验）：未接入模型时，系统自动降级为**模板兜底教学**（费曼五步结构完整，内容为内置模板），流程可跑通

### 3. 初始化数据库

```bash
python3 -c "from framework.database import db; print(db.init())"
```

### 4. 启动服务

```bash
bash scripts/remote_start_all.sh
```

或分别启动（按需）：

```bash
# Framework API（课堂/终端/管理，端口 18080/18081/18082）
nohup python3 framework/api/server.py --multi-port --host 0.0.0.0 > logs/framework_api.log 2>&1 &

# GOAI 学习 Web（5000）
nohup python3 goai_web.py > logs/goai_web.log 2>&1 &

# 教师端（5001）
nohup python3 teacher_portal.py > logs/teacher_portal.log 2>&1 &

# 学生端学习平台（5010）
nohup python3 student_portal.py > logs/student_portal.log 2>&1 &

# 学习分析仪表盘（18090）
nohup python3 analytics_dashboard.py > logs/analytics_dashboard.log 2>&1 &
```

> 端口可通过 Admin「端口管理」面板或 `config/framework.yaml` 的 `port_settings` 灵活配置。

### 5. 访问入口

| 服务 | 地址 | 说明 |
|---|---|---|
| 课堂模式 | http://localhost:18080/classroom | 费曼五步学习 + AI 聊天 + 幻灯片演示 + 思维导图 |
| 对话终端 | http://localhost:18080/chat | 多角色 AI 对话（老师/助教/同学） |
| 管理面板 | http://localhost:18082/admin | 用户/模型/端口/Agent/日志/数据可视化（默认管理员 admin，登录后请立即改密） |
| GOAI 学习 Web | http://localhost:5000 | 多 Agent 协作学习 + RAG + 学习报告 |
| 学生端学习平台 | http://localhost:5010 | 引导式学习（苏格拉底式交互） |
| 教师端 | http://localhost:5001 | 班级管理 / 学习监控 / 任务分配 / 导出申请 |
| 学习分析仪表盘 | http://localhost:18090 | 掌握度趋势 / 学科对比 / 薄弱点排行 |
| Ollama | http://localhost:11434 | 模型推理网关 |

## 验证部署

```bash
python3 scripts/health_check.py
```

输出示例（全部 ✅ 即部署成功）：

```
LumiLearn 健康检查 (host=127.0.0.1)
========================================================
  ✅ 端口 18080  课堂/终端/管理 (Framework API)   OK
  ✅ 端口 18081  REST API                          OK
  ✅ 端口 18082  管理面板 API                      OK
  ✅ 端口 5000   GOAI 学习 Web                     OK
  ✅ 端口 5001   教师端                            OK
  ✅ 端口 5010   学生端学习平台                    OK
  ✅ 端口 18090  学习分析仪表盘                    OK
  ✅ 数据库 lumilearn.db  用户 N 人
========================================================
全部服务正常 🎉
```

也可以直接访问任一健康接口：

```bash
curl http://localhost:18080/health          # {"status":"ok",...}
curl http://localhost:5000/api/status       # 模型可用性与状态
```

## 数据与日志

| 路径 | 说明 |
|---|---|
| `lumilearn.db` | SQLite 主库：用户 / 学习报告 / 推理日志 / 导出审批 / 教学内容 |
| `logs/` | 各服务运行日志 |
| `export_data/` | 管理员审批通过的导出文件 |
| `training_data/` | 教学训练数据（671 条，用于复现 LoRA 微调） |

## 安全说明

- 所有远程凭据（SSH 等）一律通过环境变量注入，仓库不包含任何真实密钥
- 默认管理员账号 `admin`，首次登录后请在「设置」中修改密码
- 学生/教师账号由管理员创建，账号可启停、角色可调整，数据按角色隔离

## 常见问题

| 问题 | 处理 |
|---|---|
| 页面能开但互动慢 | 确认端口模型为 `lumilearn-v2`（CPU 快），避免使用 `qwen2.5:7b`（CPU 极慢） |
| 聊天无回复 | 检查 `curl http://localhost:11434/api/tags` 是否返回模型；未装模型时走模板兜底 |
| 部署后页面还是旧版 | 模板已带 `no-store` 缓存头，强制刷新（Ctrl+F5）即可 |
| 想跑通完整引导式学习 | 登录学生端（5010）发起学习，按提问依次回答即可 |
