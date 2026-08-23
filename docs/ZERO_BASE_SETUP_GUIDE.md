# LumiLearn 零基础配置指南

> **适用人群**：完全没有 Linux/Docker/Python 经验的用户  
> **预估耗时**：15–30 分钟  
> **平台**：Windows 10/11（本指南以 Windows 为例）

---

## 一、前置准备：安装两个基础工具

LumiLearn 需要两个工具才能运行：**Python 3.9+**（程序语言）和 **Git**（下载工具）。

### 1.1 安装 Python

1. 打开浏览器，访问：<https://www.python.org/downloads/>
2. 点击 **Download Python 3.12.x**（最新稳定版）
3. 下载完成后，**双击安装包**，安装时 **务必勾选**：
   > ☑ **Add Python to PATH**（关键！不勾会导致后续命令全部找不到）
4. 点击 **Install Now**，等待安装完成
5. 打开 **PowerShell**（右键开始菜单 → "Windows PowerShell"），输入以下命令验证：
   ```powershell
   python --version
   ```
   正常输出类似：`Python 3.12.8`

### 1.2 安装 Git

1. 打开浏览器，访问：<https://git-scm.com/download/win>
2. 等待浏览器自动下载 `.exe` 安装文件
3. **双击安装**，全部使用默认选项（一路点 Next）
4. 安装完成后，打开 PowerShell，验证：
   ```powershell
   git --version
   ```
   正常输出类似：`git version 2.47.0.windows.1`

---

## 二、克隆（下载）项目

### 2.1 选择安装位置

选择一个磁盘空间充足的目录（建议 E 盘或 D 盘，**不要**选 C 盘根目录，且路径中**不要包含中文字符**以外的特殊字符）。

本指南以 `E:\` 为例。打开 PowerShell，执行：

```powershell
cd E:\
git clone https://github.com/k3234/lumilearn.git
cd lumilearn
```

第一行切换到 E 盘根目录；第二行下载项目；第三行进入项目目录。

### 2.2 验证克隆成功

```powershell
dir
```

你应该能看到以下目录/文件：
```
goai_web.py     framework/     docs/      scripts/     deploy/      tests/
requirements.txt  .env.example  README.md  config/
```

---

## 三、安装 Python 依赖

LumiLearn 有两种安装模式，请根据你电脑的配置选择：

### 3.1 快速模式（仅 Web 演示，无本地大模型）

适合：只是想体验前端界面、无需 AI 生成功能。

```powershell
pip install -r goai_requirements.txt
```

### 3.2 完整模式（含 AI 教学、模型推理）

适合：有 GPU 或希望体验完整 AI 功能。注意此模式下载量约 2–4 GB，耗时较长。

```powershell
pip install -r requirements.txt
```

### 3.3 遇到 "pip 不是内部命令" 的错误？

说明 Python 的 pip 工具未正确加入 PATH。运行以下命令：

```powershell
python -m pip install --upgrade pip
pip install -r goai_requirements.txt
```

---

## 四、配置环境变量（.env 文件）

### 4.1 创建 .env 文件

`.env` 是项目的环境配置文件，存放密钥和端口设置。仓库中的 `.gitignore` 已确保这个文件**不会被上传到 GitHub**，是安全的。

在 PowerShell 中执行：

```powershell
copy .env.example .env
notepad .env
```

### 4.2 最小配置（仅运行演示，无需 AI）

`.env` 文件只需保留以下内容（其他行保持原样不动）：

```
# 端口配置（默认即可，一般不需要改）
GOAI_PORT=5000
API_PORT=5010
TEACHER_PORT=5001
LUMILEARN_PORT=18080

# 模型配置（不配 Ollama 也能运行，AI 功能会降级为模拟模式）
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=lumilearn-v2:latest

# 安全密钥（本地开发模式自动生成，可留空）
LUMILEARN_ENV=development
```

### 4.3 配置本地 AI 模型（可选）

如需真正使用 AI 功能，需要安装 **Ollama**（本地模型运行器）：

1. 访问 <https://ollama.com/download/windows>，下载安装
2. 安装完成后打开 PowerShell，拉取模型（推荐小模型，CPU 可跑）：
   ```powershell
   ollama pull qwen2.5:1.5b
   ```
3. 验证 Ollama 是否运行：
   ```powershell
   curl http://localhost:11434/api/tags
   ```
   正常输出包含模型列表。

### 4.4 配置云端 AI（可选）

如果不想装 Ollama，可以使用云端 API。在 `.env` 中填入对应 Key：

```
# 豆包（字节跳动）
DOUBAO_API_KEY=你的_key

# Kimi（月之暗面）
MOONSHOT_API_KEY=你的_key
```

**注意**：API Key 是敏感信息，**绝不要**截图发到公开平台或上传到 GitHub。

---

## 五、启动服务

### 5.1 方式一：一键完整启动（推荐）

在 PowerShell 中，确保当前目录是 `lumilearn`，执行：

```powershell
python deploy/start.py
```

启动后你会看到类似输出：

```
============================================================
  🚀 LumiLearn 服务启动中（配置驱动）
============================================================
  🔗 Ollama 地址: http://localhost:11434
  📄 配置文件: ...\config\framework.yaml
  ▶ 启动 GOAI 学习 Web (端口 5000): python goai_web.py
      ✓ GOAI 学习 Web 已就绪 (PID 12345)
  ▶ 启动框架终端 (端口 18080): python -m framework.api.server --multi-port
      ✓ Framework API 已就绪 (PID 12346)
  ...
```

**浏览器会自动打开**，进入 GOAI 学习界面。

### 5.2 方式二：快速演示模式（无 AI 也能跑）

如果只想快速看界面，无需配置任何模型：

```powershell
python goai_web.py
```

服务在 `http://localhost:5000` 启动。

### 5.3 方式三：Lite 模式（低配电脑/自学专用）

内存不足或只想用核心学习功能时：

```powershell
python goai_web.py --mode lite
```

Lite 模式：
- 仅保留终端、API、学生端三个核心服务
- 自动关闭教师端、分析仪表盘
- 日志降噪（仅输出 WARNING 及以上级别）

### 5.4 多端口说明

| 端口 | 服务 | 用途 |
|---|---|---|
| 5000 | GOAI 学习 Web | 主要入口，学生登录/学习/答题 |
| 18080 | 框架终端 | Admin 管理面板 |
| 18081 | REST API | 纯 API 接口（供第三方调用） |
| 18082 | 模型管理 | 模型列表与切换 |
| 5001 | 教师门户 | 教师端班级管理 |
| 5010 | 学生端学习平台 | 独立学生端 |
| 18090 | 学习分析仪表盘 | 学情数据分析 |

---

## 六、首次使用：创建账号并学习

### 6.1 打开 GOAI 学习界面

浏览器访问 `http://localhost:5000`

### 6.2 登录

- 首次使用点击「注册」，填写用户名（如 `student001`）和密码
- 注册后登录

### 6.3 开始学习

在「学习目标」输入框中输入知识点，例如：
```
勾股定理
```
点击「开始学习」，系统会调用 AI（或模拟模式）生成讲解、练习题。

### 6.4 管理员面板

浏览器访问 `http://localhost:18080`

- 默认管理员账号：`admin`，密码为 `.env` 中 `LUMILEARN_ADMIN_INITIAL_PASSWORD` 设置的值（默认 `change_me`）
- 可在「用户管理」中创建教师/学生账号
- 可在「教材管理」中导入 Markdown 格式的教学文档
- 可在「三层记忆」面板中查看短期/中期/长期记忆分布

---

## 七、停止服务

### 方式一：使用启动脚本停止

```powershell
python deploy/stop.py
```

### 方式二：Ctrl+C

在启动服务的 PowerShell 窗口中按 `Ctrl+C` 可停止当前服务。

### 方式三：结束进程

```powershell
taskkill /F /IM python.exe
```

---

## 八、常见问题排查

### Q1：启动时报 "ModuleNotFoundError: No module named flask"

```powershell
pip install flask requests python-dotenv pyyaml
```

### Q2：浏览器访问 "无法连接"

- 确认服务正在运行（看启动终端的输出）
- 检查端口是否被占用：
  ```powershell
  netstat -ano | findstr ":5000"
  ```
- 如端口被占用，修改 `.env` 中的 `GOAI_PORT=5000` 为其他端口（如 `5020`）

### Q3：AI 学习功能返回空内容或 100%

- Ollama 未安装或未拉取模型，系统已自动降级为模拟模式
- 检查 Ollama：`curl http://localhost:11434/api/tags`
- 未安装 Ollama 也不影响基础功能（界面演示、答题记录等正常）

### Q4：数据库报错 "database is locked"

- 多个程序同时访问 `lumilearn.db` 导致
- 关闭其他终端，或重新启动服务

### Q5：启动时报 "SECRET_KEY 未定义"

- 确认 `.env` 文件中存在 `LUMILEARN_ENV=development`
- 生产环境才需要真实 SECRET_KEY，开发环境会自动生成

---

## 九、配置速查表

| 文件/命令 | 作用 | 是否需要修改 |
|---|---|---|
| `.env` | 环境变量（密钥/端口/模型地址） | 按需 |
| `config/framework.yaml` | 端口与服务配置 | 通常不需要 |
| `python deploy/start.py` | 启动全部服务 | 日常启动 |
| `python deploy/stop.py` | 停止全部服务 | 日常停止 |
| `python goai_web.py --mode lite` | Lite 模式启动 | 低配电脑 |
| `pip install -r requirements.txt` | 安装完整依赖 | 首次安装 |

---

## 十、数据与隐私

- **学习数据**：存储在本地 `lumilearn.db`（SQLite 文件），**不上传云端**
- **AI 请求**：使用 Ollama 时完全离线；使用云端 API 时仅发送学习文本，不含个人信息
- **`.env` 文件**：已在 `.gitignore` 中，不会被提交到 GitHub，可安全存放密钥
- **禁止外传**：API Key、密码等敏感信息**严禁**截图上传到任何公开平台
