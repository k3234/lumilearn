# AI-Coding-Tools - GitHub 热门 AI 编程工具配置指南

## 元信息

- **名称**: ai-coding-tools
- **版本**: 1.0.0
- **来源**: GitHub 热门项目整合
- **类型**: AI 编程工具配置指南
- **标签**: cursor, continue, aider, copilot, ai-programming, code-agent

---

## 📌 工具对比总览

| 工具 | 类型 | 模型 | 免费可用 | 本地运行 | 推荐度 | 最佳场景 |
|------|------|------|----------|----------|--------|----------|
| **Cursor** | AI IDE | 多模型可选 | ⭐ 有免费版 | ❌ 云端为主 | ⭐⭐⭐⭐⭐ | 全项目开发 |
| **Continue** | VSCode 插件 | 自定义模型 | ✅ 完全免费 | ✅ 支持本地 | ⭐⭐⭐⭐⭐ | 日常开发 |
| **Aider** | 终端 Agent | OpenAI/Anthropic | ✅ 免费开源 | ✅ 可本地 | ⭐⭐⭐⭐⭐ | 终端/自动化 |
| **GitHub Copilot** | VSCode 插件 | GPT-4/ Claude | ❌ 付费（$10/月） | ❌ 云端 | ⭐⭐⭐⭐ | 代码补全 |
| **Claude Code** | 终端 Agent | Claude | ✅ 免费 | ✅ 可本地 | ⭐⭐⭐⭐ | 命令行开发 |

---

## 🔥 工具 1: Cursor - AI 原生 IDE

### 简介
**Cursor** 是一个以 AI 为中心重建的 VS Code，保留了 VS Code 的一切（扩展、快捷键、工作流），同时添加了理解整个代码仓库的 AI 能力。

### 核心能力
- **智能补全**: 理解上下文的代码补全
- **聊天对话**: Ctrl+L 打开 AI 聊天，直接问代码问题
- **Agent 模式**: Ctrl+K 打开命令面板，让 AI 自动修改代码
- **代码库理解**: 自动索引整个项目，AI 知道你的代码结构
- **多文件编辑**: AI 可以同时修改多个文件
- **规则集**: 可配置自定义规则，让 AI 遵循你的编码风格

### 下载安装
```bash
# Windows
# 访问: https://cursor.com
# 下载安装包直接安装

# 或者使用 Winget（如果可用）
winget install Cursor
```

### 快捷键速查
```
Ctrl + L          → 打开 AI 聊天（问问题、解释代码）
Ctrl + K          → 打开命令面板（让 AI 修改代码）
Ctrl + Shift + L  → 选择相似代码
Ctrl + Enter      → 在聊天中确认 AI 的修改
Esc               → 关闭 AI 面板
```

### 配置技巧

#### 1. 模型选择（设置 → Models）
```
- Claude Sonnet 4.7 (推荐，平衡速度与质量)
- Claude Opus 4.7 (质量最好，但较慢)
- GPT-4.1 Turbo (快速代码生成)
- Gemini 2.5 Pro (Google 模型)
```

#### 2. 规则配置（项目根目录创建 .cursorrules）
```yaml
# .cursorrules 文件放在项目根目录
# 让 AI 遵循你的项目规范

coding_style:
  - 使用 4 空格缩进（Python）
  - 函数名使用小写下划线（snake_case）
  - 类名使用大驼峰（PascalCase）
  - 添加中文注释说明关键逻辑

project_specific:
  - 这是一个 AI 教育平台项目
  - 参考 PRODUCT.md, DESIGN.md, AGENTS.md
  - 保持代码简洁，学生友好

file_structure:
  - framework/ 放核心框架代码
  - skills/ 放技能模块
  - docs/ 放文档
```

#### 3. 使用示例

**问问题**:
```
# 选中代码后按 Ctrl+L
"解释这段代码的逻辑"
"这段代码有什么可以优化的？"
```

**让 AI 修改代码**:
```
# 选中代码后按 Ctrl+K
"重构这个函数，添加错误处理"
"用更简洁的方式重写这段逻辑"
"添加单元测试"
```

**Agent 模式（全项目修改）**:
```
# 不选代码直接按 Ctrl+L
"在 framework/engines/ 中新增一个 quiz_engine.py，实现智能出题功能"
"给所有 API 端点添加请求日志"
"把项目中所有的 print() 改为 logging"
```

---

## 🚀 工具 2: Continue - 开源 VSCode AI 助手

### 简介
**Continue** 是一个完全开源的 VS Code 插件，本身不提供 AI 模型，但可以接入任何 LLM（包括本地 Ollama 模型），实现自定义 AI 编程助手。

### 核心能力
- **多模型接入**: 支持 Ollama, OpenAI, Anthropic, 自定义 API
- **本地优先**: 可以完全本地运行，保护代码隐私
- **代码补全**: 自动代码补全
- **聊天对话**: 选中代码聊天
- **命令系统**: 可自定义 /命令 触发特定操作

### 安装步骤

#### 1. 在 VSCode 中安装
```
# VSCode 扩展市场搜索 "Continue"
# 或者访问: https://marketplace.visualstudio.com/items?itemName=Continue.continue
```

#### 2. 配置本地模型（推荐 Ollama）
```bash
# 确保已安装 Ollama
# 拉取适合编码的模型
ollama pull qwen2.5-coder:7b   # 阿里云千问代码模型
ollama pull deepseek-coder:6.7b # 深度求索代码模型
ollama pull codegecko:7b        # 轻量级代码模型
```

#### 3. 配置 Continue（Ctrl+Shift+P → "Continue: Config"）

在 `~/.continue/config.json` 中添加:

```json
{
  "models": [
    {
      "title": "Qwen2.5-Coder (本地)",
      "provider": "ollama",
      "model": "qwen2.5-coder:7b",
      "apiBase": "http://localhost:11434",
      "completionOptions": {
        "temperature": 0.7,
        "topP": 1
      }
    },
    {
      "title": "DeepSeek-Coder (本地)",
      "provider": "ollama",
      "model": "deepseek-coder:6.7b",
      "apiBase": "http://localhost:11434"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Qwen2.5-Coder",
    "provider": "ollama",
    "model": "qwen2.5-coder:7b"
  }
}
```

#### 4. 自定义命令

在 Continue 配置中添加自定义命令:
```json
{
  "customCommands": [
    {
      "name": "review",
      "description": "代码审查",
      "prompt": "请审查以下代码，找出潜在的 bug、性能问题和代码风格问题：\n\n{{{code}}}"
    },
    {
      "name": "explain",
      "description": "解释代码",
      "prompt": "用通俗易懂的中文解释以下代码的逻辑：\n\n{{{code}}}"
    },
    {
      "name": "test",
      "description": "生成测试",
      "prompt": "为以下代码编写单元测试：\n\n{{{code}}}"
    }
  ]
}
```

### 使用方式

#### 快捷键
```
Ctrl + L          → 打开 Continue 聊天
/                 → 输入命令（如 /review, /explain）
选中代码 + Ctrl+L → 对选中代码提问
```

#### 常用命令
```
/review     → 代码审查
/explain    → 解释代码
/test       → 生成测试
/refactor   → 重构代码
/docs       → 生成文档
```

---

## 💻 工具 3: Aider - 终端 AI 编程助手

### 简介
**Aider** 是一个基于终端的开源 AI 结对编程工具，可以直接在命令行中让 AI 帮你写代码、改代码、审查代码。

### 核心能力
- **终端操作**: 直接在终端中与 AI 协作
- **自动编辑**: AI 可以直接修改你的文件
- **Git 集成**: 自动提交代码变更
- **多文件编辑**: AI 可以跨文件修改
- **代码理解**: 理解整个项目的上下文
- **本地模型**: 支持本地 Ollama 模型

### 安装步骤

#### 1. 安装 Aider
```bash
# 使用 pip 安装
pip install aider-chat

# 或者克隆源码
git clone https://github.com/Aider-AI/aider
cd aider
pip install -e .
```

#### 2. 配置 API Key
```bash
# 方式 1: 使用环境变量
$env:OPENAI_API_KEY = "sk-your-key-here"

# 方式 2: 创建 .env 文件
# 在项目根目录创建 .env
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

#### 3. 使用本地 Ollama 模型（免费）
```bash
# 不需要 API Key，直接用本地模型
aider --model ollama/qwen2.5-coder:7b

# 或者在 ~/.aider.conf.yml 中配置:
# model: ollama/qwen2.5-coder:7b
```

### 常用命令

```bash
# 启动 Aider（在项目目录中）
cd lumilearn
aider

# 启动并指定模型
aider --model claude-sonnet-4-7        # Claude
aider --model gpt-4.1-turbo           # GPT-4
aider --model ollama/qwen2.5-coder:7b # 本地模型

# 添加文件让 AI 理解上下文
/add framework/model.py
/add lesson_engine.py

# 让 AI 做事情（直接输入自然语言）
> 给这个函数添加错误处理
> 重构这个模块，使其更模块化
> 添加单元测试
> 解释这段代码的逻辑
> 帮我写一个新的 API 端点

# 常用快捷键
/help      → 查看帮助
/add       → 添加文件到上下文
/clear     → 清空对话
/git       → 运行 git 命令
/quit      → 退出
```

### Aider + LumiLearn 使用示例

```bash
cd <project-root>\lumilearn

# 启动 Aider，加入核心文件
aider
> /add framework/model.py
> /add lesson_engine.py
> /add smart_reply_engine.py

# 让 AI 帮你添加功能
> 我想添加一个学习进度跟踪功能，帮我设计并实现

# AI 会自动修改相关文件，你可以确认修改
> 看起来不错，继续实现

# 让 AI 帮你调试
> 运行时出现了这个错误：XXX，帮我看看
```

---

## 🐙 工具 4: GitHub Copilot - 官方代码补全

### 简介
**GitHub Copilot** 是 GitHub 官方出品的 AI 编程助手，直接安装在 VSCode 中使用，提供实时代码补全。

### 核心能力
- **智能补全**: 根据上下文预测下一行代码
- **代码生成**: 根据注释生成代码
- **代码建议**: 提供多种实现方案
- **聊天对话**: Copilot Chat 解释代码
- **安全扫描**: 识别潜在的安全问题

### 安装配置

#### 1. 订阅
```
# 访问: https://github.com/features/copilot
# 个人版: $10/月 或 $100/年
# 学生认证: 免费！（推荐，你是高一学生）
```

#### 2. VSCode 安装
```
# 在 VSCode 扩展市场搜索 "GitHub Copilot"
# 安装后登录 GitHub 账号
```

#### 3. 推荐配置
```json
// VSCode settings.json
{
  "github.copilot.enable": {
    "*": true,
    "markdown": true,
    "plaintext": true
  },
  "github.copilot.advanced": {
    "inlineSuggestCount": 3
  }
}
```

### 使用技巧

#### 代码补全
```python
# 写一个注释，然后按 Tab
# 计算斐波那契数列
def fibonacci(n):
    # [AI 会自动补全]

# 或者直接写函数名
def calculate_student_progress
    # [AI 会根据函数名补全]
```

#### Copilot Chat
```
# 选中代码后，右键 → Copilot Chat
# 或者按 Ctrl+I

# 常用提问:
"解释这段代码"
"这段代码有什么问题？"
"重构这段代码使其更清晰"
"添加类型注解"
"编写测试用例"
```

---

## 🎯 推荐组合方案

### 方案 A: 学生/初学者（低成本）
| 层级 | 工具 | 成本 |
|------|------|------|
| 日常开发 | **Continue + Ollama 本地模型** | 免费 |
| 代码补全 | **GitHub Copilot（学生免费）** | 免费 |
| 终端操作 | **Aider + 本地模型** | 免费 |

### 方案 B: 进阶开发者（推荐）
| 层级 | 工具 | 成本 |
|------|------|------|
| 主 IDE | **Cursor** | 免费版可用 |
| 代码补全 | **Continue 或 Copilot** | 免费/$10月 |
| 终端 Agent | **Aider** | 免费 + API 费用 |

### 方案 C: 全本地（隐私优先）
| 层级 | 工具 | 成本 |
|------|------|------|
| IDE | **VSCode** | 免费 |
| AI 助手 | **Continue + Ollama** | 免费 |
| 终端 | **Aider + Ollama** | 免费 |

---

## 📝 快速上手 Checklist

- [ ] 安装 **VSCode** 或 **Cursor**
- [ ] 安装 **Ollama** 用于本地模型
- [ ] 拉取至少一个代码模型（`ollama pull qwen2.5-coder:7b`）
- [ ] 安装 **Continue** 插件（如果用 VSCode）
- [ ] 安装 **Aider**（`pip install aider-chat`）
- [ ] 申请 **GitHub Copilot 学生认证**（免费）
- [ ] 创建第一个 `.cursorrules` 文件（如果用 Cursor）
- [ ] 尝试用 AI 生成一段代码！

---

## 🔗 资源链接

| 项目 | GitHub | Stars | 说明 |
|------|--------|-------|------|
| Cursor | https://cursor.com | N/A | AI 原生 IDE |
| Continue | https://github.com/continuedev/continue | 20K+ | 开源 VSCode 插件 |
| Aider | https://github.com/Aider-AI/aider | 18K+ | 终端 AI 编程 |
| GitHub Copilot | https://github.com/features/copilot | N/A | 官方代码补全 |
| Ollama | https://github.com/ollama/ollama | 90K+ | 本地模型运行 |

---

## 🚀 与 LumiLearn 集成

### 在 LumiLearn 项目中使用

#### 1. Cursor 规则集
创建 `<project-root>\lumilearn\.cursorrules`:
```yaml
project_context: |
  这是 LumiLearn AI 教育平台项目。
  - PRODUCT.md: 产品目标和边界
  - DESIGN.md: 设计规范
  - AGENTS.md: 开发工作流程
  - framework/: 核心框架代码
  - skills/: 技能模块
  - lesson_engine.py: 智能讲解引擎
  - smart_reply_engine.py: 智能回复引擎

coding_standards:
  - Python 使用 4 空格缩进
  - 函数和变量使用小写下划线
  - 类名使用大驼峰
  - 添加中文注释说明关键逻辑
  - 保持代码简洁，学生友好

review_criteria:
  - 代码是否清晰易懂？
  - 是否有适当的注释？
  - 是否有错误处理？
  - 是否遵循项目的设计规范（DESIGN.md）？
```

#### 2. Aider 项目配置
在 `<project-root>\lumilearn\.aider.conf.yml` 中:
```yaml
model: ollama/qwen2.5-coder:7b
auto-commits: true
test-command: python -m pytest tests/ -v
lint: true
```

#### 3. 日常开发流程
```bash
# 1. 打开 Cursor 或 VSCode
# 2. 让 AI 理解项目
> "阅读 PRODUCT.md 和 DESIGN.md，理解这个项目"

# 3. 开始开发
> "帮我实现一个新功能：XXX"
# 或使用 Aider:
aider
> 我想添加一个新的功能...
```

---

*版本: 1.0.0 | 更新: 2026-06-09*
