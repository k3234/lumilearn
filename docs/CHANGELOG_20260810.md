# LumiLearn 更新记录（2026-08-10）

> 本文档整理 2026-08-10 前后所有新增与修改内容，供维护与发布参考。
> 说明：不包含测试脚本、本地验收过程与任何敏感凭据；服务器地址一律使用占位符。

---

## 一、新增功能

### 1. 教师端（Teacher Portal）⭐

**新增文件**：`teacher_portal.py`（独立 Flask 应用，端口 5001）、`remote/templates/teacher.html`（明亮简洁风单页前端）

教师端为教师角色提供完整的教学管理工作台，复用 `users` 表认证（仅 `role=teacher` 可登录），与主框架、学习平台 Web 共享同一数据库。

| 模块 | 功能 |
|---|---|
| 登录认证 | 教师账号登录，学生账号访问被拒绝 |
| 总览 | 班级数 / 学生数 / 任务数 / 学习报告数统计 |
| 班级管理 | 学校库 → 年级库 → 班级库三级组织，学生入班 / 出班 |
| 学生管理 | 查看学生、创建学生账号、重置密码、搜索 |
| 学习监控 | 每位学生的 学习报告（列表/详情）、知识图谱掌握度、答题正确率、薄弱知识点 |
| 任务管理 | 创建任务、从知识点自动生成任务、按全班 / 个人分配、完成情况跟踪 |
| 教学资源 | 已发布教学内容库、知识点库（点击知识点可生成任务） |

**权限设计**：教师只能管理自己为班主任的班级；跨教师数据隔离。

### 2. 数据库组织架构（班级库 / 年级库 / 学校库）

**修改文件**：`framework/database.py`

新增 4 张表，构建"学校 → 年级 → 班级 → 学生"四级组织体系：

- `schools`（学校库）：学校基本信息
- `grades`（年级库）：挂载于学校下
- `classes`（班级库）：挂载于年级下，可指定班主任（teacher_id）
- `class_students`（学生-班级绑定）：UNIQUE(class_id, user_id) 防重复

配套新增 20+ 方法：学校/年级/班级的增删查（删除级联清理下层）、学生入班/出班、教师可见学生列表、教师端总览统计、按班级批量分配任务、任务分配名单（含学生姓名）等。旧库升级时通过 `CREATE TABLE IF NOT EXISTS` 自动建表，无需迁移。

### 3. AI 思维导图生成

**修改文件**：`framework/api/routes/mindmap.py`

新增 `/api/mindmap/generate` 端点：基于本地 Ollama 模型（默认 `lumilearn-v2:latest`）真实生成思维导图，输出 `nodes/edges` 结构化数据；模型异常时自动降级为通用教学分支模板，保证功能可用。

### 4. AI 幻灯片生成（PPT）

**修改文件**：`framework/api/routes/slides.py`

新增幻灯片生成端点：基于 Ollama 生成教学内容幻灯片，支持 Markdown / 分页格式解析，内置 HTML 转义清洗与兜底模板，输出可直接渲染的幻灯片结构。

### 5. 云端模型提供者接入（API Key）

**修改文件**：`framework/services/provider_service.py`、`config/providers.yaml`、`framework/api/routes/admin.py`

- 内置 7 家提供者模板：DeepSeek、OpenAI、智谱清言、Moonshot、通义千问、SiliconFlow 等
- Admin 面板可配置各提供者的 API Key、接口地址、启用状态与模型列表
- API Key 安全存储：前端不返回明文，后端通过内部方法读取
- 提供者配置变更后内存热更新（`reload()`）

---

## 二、功能增强

### 1. 学习平台 Web 用户认证与数据库共享

**修改文件**：`lumilearn_web.py`

学习平台 Web（端口 5000）从"仅演示"升级为完整学习平台：

- 用户登录 / 退出（复用 `users` 表，werkzeug 密码哈希校验）
- 直接共享框架数据库 `lumilearn.db`（与 18080 / 5001 一致）
- 学习报告自动持久化到新增的 `learning_reports` 表
- 学习历史查看（重新打开已生成报告）
- 顶栏显示当前登录用户，未登录无法发起学习

### 2. Admin 面板增强

**修改文件**：`remote/templates/admin.html`、`framework/api/routes/admin.py`

- **设置**：侧边栏新增"⚙️ 设置"，支持修改管理员密码（旧密码 + 新密码 + 确认）
- **学习记录**：新增"📚 学习记录"面板，查看所有学生的学习报告（可筛选用户）
- **用户管理**：支持创建带登录用户名/密码的账号、显示密码状态徽标、一键重置密码
- **模型管理**：拆分为"本地模型 / 云端提供者 / 端口模型配置"三个子标签页
- **端口模型配置**：为各端口选择使用的模型（本地或云端），卡片式折叠菜单展示全部可选模型
- 修复：云端模型 API 路径错误（`/admin/providers` → `/providers`）；学习报告详情嵌套结构解析错误

### 3. 端口模型配置机制

**修改文件**：`framework/services/provider_service.py`、`framework/api/routes/chat.py`、`remote/templates/lumiterm.html`

- 新增 `port_model_mapping` 配置：为终端（18080）、REST API（18081）、模型管理（18082）、学习平台 Web（5000）分别指定模型
- `chat.py` 新增端口感知解析：根据请求端口自动选择该端口配置的模型
- `ProviderService` 改为全局单例，Admin 面板修改后即时生效
- 终端页面加载时读取端口配置并更新模型徽标（本地 / 云端）
- `lumilearn_agent.py` 支持调用端口配置的云端模型

### 4. 端口选择性配置（端口管理）

**修改文件**：`framework/services/provider_service.py`、`framework/api/routes/admin.py`、`remote/templates/admin.html`、`config/framework.yaml`、`scripts/remote_start_all.sh`、`lumilearn_web.py`、`teacher_portal.py`、`framework/api/server.py`

Admin 面板新增「🔌 端口管理」面板，用户可**选择性启用/禁用各端口服务并自定义端口号**：

| 端口服务 | 说明 | 默认端口 |
|---|---|---|
| terminal | 框架终端 + Admin 面板 | 18080 |
| api | REST API 纯接口服务 | 18081 |
| models | 模型管理服务 | 18082 |
| lumilearn_web | 学习平台 Web 学习平台（学生端） | 5000 |
| teacher_portal | 教师端 Teacher Portal | 5001 |

- 每个服务独立开关 + 端口号输入框，实时显示运行状态（● 运行中 / ○ 未运行）
- 保存时校验：端口号范围（1-65535）、端口冲突检测
- 配置写入 `config/framework.yaml` 的 `port_settings` 节
- 生效机制：保存后运行 `bash remote_start_all.sh`，脚本按配置选择性启停服务（禁用则杀进程，启用则启动）
- `lumilearn_web.py` / `teacher_portal.py` / `server.py` 启动时自动读取 `port_settings` 确定端口（支持环境变量覆盖）

---

## 三、修复与调整

### 1. 云端模型调用修复

- `chat.py` 中 `_resolve_cloud_model` 调用不存在的 `provider_service._load()` → 改为 `_providers`，云端模型（如 DeepSeek）配置后不再回退本地模型

### 2. 默认模型统一

- `framework/core/router.py`、`framework/services/chat_service.py`、`framework/models/ollama_provider.py`、`framework/engines/feynman_engine.py` 默认模型统一为 `lumilearn-v2:latest`

### 3. 动画健康检查

- `framework/api/routes/animation.py` 新增 `/api/animation/health`：Manim 未部署时返回 `unavailable`，前端走画布占位动画

### 4. 前端细节

- 终端页面移除顶部模型选择下拉框与设置弹窗，模型管理权限集中到 Admin 面板
- 终端 ⚙ 按钮改为跳转 Admin 面板

### 5. 安全策略调整

- `framework/api/server.py` 调整 CSP 策略：放行内联脚本与 jsdelivr CDN 资源（适配单文件 HTML 前端），`connect-src` 放行本机端口调试

### 6. 新增资产

- `docs/MODEL_COMPARISON.md` + `docs/model_comparison_chart.html`：模型对比分析文档与可视化图表
- `demo_lumilearn_20260809.mp4`：系统演示视频
- `output/demo_report.json`：演示学习报告数据

---

## 四、部署与运维

### 1. 一键启动脚本

**修改文件**：`scripts/remote_start_all.sh`（远程服务器服务器）、`start_services.bat`（Windows 本地）

- 远程服务器脚本：初始化数据库 → 确认/启动 Ollama → 启动框架三端口（18080/18081/18082）→ 启动 学习平台 Web（5000），带幂等检查（已运行则跳过）与最终状态汇总
- Windows 脚本：启动框架服务并指向远程服务器 Ollama

### 2. 环境变量

**修改文件**：`.env.example`

- `OLLAMA_URL` / `OLLAMA_BASE_URL`：Ollama 服务地址
- `REMOTE_HOST` / `REMOTE_USER` / `REMOTE_PASSWORD`：远程部署 SSH 连接（必填，不提交真实值）
- `LUMILEARN_DB_PATH`：数据库文件路径（可自定义）
- `LumiLearn_SECRET_KEY` / `TEACHER_SECRET_KEY`：Web 会话密钥

### 3. 教师端部署脚本

**新增文件**：`scripts/_upload_teacher_portal.py`、`scripts/_start_teacher_remote.py`、`scripts/_teacher_start.sh`

上传教师端代码并后台启动（`setsid nohup`），重启用 `pkill -f teacher_portal.py`。

---

## 五、服务端口一览

| 端口 | 服务 | 入口 |
|---|---|---|
| 11434 | Ollama 模型服务 | - |
| 18080 | 框架终端 + Admin 面板（/admin） | 终端、管理 |
| 18081 | REST API（纯接口） | 第三方集成 |
| 18082 | 模型管理 | 模型配置 |
| 5000 | 学习平台 Web 学习平台 | 学生端 |
| 5001 | 教师端 Teacher Portal | 教师端 |

---

## 六、数据模型变化

- `users` 表新增 `username`、`password_hash` 列（登录用）
- 新增 `learning_reports` 表（学习报告持久化）
- 新增 `schools`、`grades`、`classes`、`class_students` 表（组织架构）
- 全部为增量建表，旧库无需迁移脚本
