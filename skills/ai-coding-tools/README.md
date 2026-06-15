# AI-Coding-Tools - GitHub 热门 AI 编程工具快速配置

> 让 AI 帮你写代码的完整工具链：Cursor + Continue + Aider + Copilot

---

## 🚀 快速开始（5 分钟搞定）

### 第 1 步: 安装 Ollama（本地模型，免费）
```bash
# Windows: 访问 https://ollama.com 下载安装
# 或者在 PowerShell 中：
winget install Ollama.Ollama

# 拉取适合编码的模型
ollama pull qwen2.5-coder:7b    # 阿里云千问代码模型（推荐）
ollama pull deepseek-coder:6.7b # 深度求索代码模型

# 测试一下
ollama run qwen2.5-coder:7b
# 输入: 用 Python 写一个快速排序
```

### 第 2 步: 选择你的 IDE

**选项 A: Cursor（推荐，AI 原生 IDE）**
```bash
# 访问: https://cursor.com
# 下载安装包直接安装
# 打开后用 GitHub 账号登录

# 快捷键:
# Ctrl + L → 打开 AI 聊天
# Ctrl + K → AI 命令面板
```

**选项 B: VSCode + Continue（开源免费）**
```bash
# 1. 安装 VSCode: https://code.visualstudio.com
# 2. 在扩展市场搜索 "Continue" 安装
# 3. 按 Ctrl+L 打开聊天，选择本地模型
```

### 第 3 步: 安装 Aider（终端工具）
```bash
pip install aider-chat

# 使用本地模型（免费）
aider --model ollama/qwen2.5-coder:7b

# 日常使用:
cd lumilearn
aider
> /add framework/model.py  # 添加文件到上下文
> 帮我添加一个新功能        # 用自然语言让 AI 写代码
```

---

## 🎯 场景推荐

| 场景 | 推荐工具 | 示例 |
|------|---------|------|
| 日常开发 | **Cursor / VSCode + Continue** | 写代码时的智能补全 |
| 项目重构 | **Cursor Agent 模式** | "重构整个数据模块" |
| 终端脚本 | **Aider** | "写一个自动测试脚本" |
| 代码审查 | **Continue / Aider** | "审查这段代码的问题" |
| 学习代码 | **Cursor Chat** | "解释这段代码的逻辑" |

---

## 📊 各工具的优势对比

| 工具 | 上手难度 | 成本 | 代码质量 | 隐私性 | 推荐场景 |
|------|---------|------|---------|--------|---------|
| Cursor | ⭐ 简单 | 免费版可用 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ 云端 | 全项目开发 |
| Continue | ⭐⭐ 需要配置 | 完全免费 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ 本地 | 日常编码 |
| Aider | ⭐⭐ 终端操作 | 免费+API费 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ 本地 | 自动化脚本 |
| Copilot | ⭐ 最简单 | $10/月 学生免费 | ⭐⭐⭐⭐ | ⭐⭐ 云端 | 代码补全 |

---

## 📁 目录结构

```
ai-coding-tools/
├── SKILL.md              # 详细配置指南（完整文档）
├── README.md             # 快速开始（本文件）
├── config.json           # 技能元信息
├── .cursorrules          # Cursor 规则集示例
└── ai_coding_tools.py    # 辅助脚本（可选功能）
```

---

## 🛠️ 配置文件示例

### Cursor 规则（.cursorrules）
放在项目根目录，让 AI 遵循你的项目规范：
```yaml
project_context: |
  这是 LumiLearn AI 教育平台项目。
  - PRODUCT.md: 产品目标和边界
  - DESIGN.md: 设计规范
  - AGENTS.md: 开发工作流程

coding_standards:
  - Python 使用 4 空格缩进
  - 函数名使用小写下划线
  - 添加中文注释说明关键逻辑

review_criteria:
  - 代码是否清晰易懂？
  - 是否有适当的错误处理？
  - 是否遵循 DESIGN.md 规范？
```

---

## 💡 使用技巧

### 技巧 1: 让 AI 更好理解你的项目
```
# 先告诉 AI 项目背景
> "先阅读 PROJECT.md 和 DESIGN.md，理解这个项目的目标"

# 再让 AI 做事情
> "好，现在帮我实现一个新功能..."
```

### 技巧 2: 用好上下文
```
# Cursor: 选中代码后按 Ctrl+L，AI 就知道你在说什么

# Aider: 先用 /add 文件名，把文件加入上下文
> /add framework/model.py
> "给这个模型添加保存和加载功能"
```

### 技巧 3: 学生免费福利
- GitHub Copilot: 学生认证免费！访问 https://education.github.com
- Cursor: 免费版够用，Pro 版按需购买
- Continue + Ollama: 完全免费，本地运行

---

## 🔗 有用链接

| 资源 | 链接 |
|------|------|
| Cursor 下载 | https://cursor.com |
| Continue 文档 | https://continue.dev |
| Aider GitHub | https://github.com/Aider-AI/aider |
| Ollama 模型库 | https://ollama.com/library |
| GitHub 学生包 | https://education.github.com/pack |

---

## 🎓 下一步

1. **先装 Ollama** —— 有本地模型才能免费用
2. **试试 Cursor 或 Continue** —— 选一个你喜欢的 IDE
3. **打开 lumilearn 项目** —— 让 AI 帮你开发
4. **遇到问题看 SKILL.md** —— 里面有详细配置和使用说明

---

*最后更新: 2026-06-09*
