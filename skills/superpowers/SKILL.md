# Superpowers - AI 编程工程纪律框架

> GitHub 213K+ Stars | 让 AI 从"乱写"变"专业工程师"

---

## 元信息

- **名称**: Superpowers
- **版本**: v5.1.0+
- **GitHub**: [obra/superpowers](https://github.com/obra/superpowers)
- **作者**: Jesse Vincent (GitHub: obra)
- **Stars**: 213K+
- **类型**: AI 编程方法学 / Agentic Skills Framework
- **标签**: workflow, engineering-discipline, tdd, code-review, best-practices

---

## 🎯 核心理念

> **AI 编程最大的问题不是智力，是纪律**

Superpowers 是由 Jesse Vincent 创建的面向 AI 编程代理的技能型开发方法学。它的核心理念非常反直觉：

- ❌ AI 知道该写测试，但会跳过
- ❌ AI 知道 debug 要找根因，但会直接猜着改
- ✅ **解决方案**：不是给 AI 加能力，而是给 AI 加纪律

---

## 📦 三层架构

### 1. Skill（技能）
最基础的单元，每个 Skill 本质上是一个 Markdown 文件，定义"当你遇到这类任务时，必须按这个流程走"。

### 2. Workflow（工作流）
由多个 Skills 组合而成的完整开发流程。

### 3. Preset（预设）
针对特定场景的预配置工作流组合。

---

## 🛠️ 六大核心 Skills

### Skill 1: brainstorm（强制头脑风暴）
**问题**：AI 不问清楚就开干，导致返工

**强制流程**：
1. 理解需求：AI 必须先复述用户需求，确认理解正确
2. 澄清问题：列出需要澄清的问题，等待用户回答
3. 方案草稿：给出 2-3 个可选方案，说明优劣
4. 用户确认：等待用户选择或修改方案后再开始

**使用场景**：
```
用户："帮我写个登录接口"

AI 回应：
"好的，让我先理解需求：
1. 您说的登录接口是指用户认证系统吗？
2. 需要支持哪些登录方式？（用户名密码/手机验证码/OAuth）
3. 需要返回什么信息？（Token/用户信息/权限）
4. 有现有的用户表结构吗？

请确认以上需求后，我再开始设计..."
```

---

### Skill 2: git-worktree（Git 工作树隔离）
**问题**：AI 直接在 main 分支改代码，改坏了影响主分支

**强制流程**：
1. 创建新 worktree：`git worktree add feature/xxx`
2. 在隔离分支开发
3. 测试通过后合并
4. 清理 worktree

**使用场景**：
```
AI：
"我将使用 git worktree 隔离开发环境：
1. 创建功能分支 worktree：git worktree add ../feature-login main
2. 在 feature-login 分支实现
3. 测试通过后合并到 main
4. 清理 worktree

这样不会影响主分支的稳定性..."
```

---

### Skill 3: tdd（测试驱动开发）
**问题**：AI 写完代码不写测试，或者先写代码再补测试

**强制流程**：
1. **Red**：先写一个失败的测试
2. **Green**：写最少的代码让测试通过
3. **Refactor**：重构优化代码
4. **Repeat**：重复直到功能完成

**使用场景**：
```
AI：
"按照 TDD 流程开发：

【Step 1 - Red】先写测试
def test_login_success():
    """测试正常登录"""
    result = login("user", "pass123")
    assert result.success == True

【Step 2 - Green】写实现代码
def login(username, password):
    if username == "user" and password == "pass123":
        return LoginResult(success=True)
    return LoginResult(success=False)

【Step 3 - Refactor】
（优化代码结构和命名）

现在测试通过！"
```

---

### Skill 4: debugging（系统性调试）
**问题**：AI debug 是"试错法"，改改试试

**强制流程**：
1. **复现**：确认能复现 bug
2. **定位**：找到问题的根本原因（不是表象）
3. **修复**：只修复根因
4. **验证**：确认 bug 修复且没引入新问题
5. **总结**：记录根因和解决方案

**使用场景**：
```
AI：
"按照系统性调试流程：

【Step 1 - 复现】
运行命令：python app.py
错误信息：IndexError: list index out of range

【Step 2 - 定位】
添加调试代码打印中间变量：
print(f"users list: {users}, index: {i}")
发现：users 列表为空时仍然尝试访问索引

根因：没有检查 users 是否为空就访问索引

【Step 3 - 修复】
在访问前添加检查：
if users and i < len(users):
    return users[i]

【Step 4 - 验证】
重新运行，无报错 ✓

【Step 5 - 总结】
根因：缺少空列表检查
解决：添加长度验证
防止：后续所有列表访问都要先检查"
```

---

### Skill 5: code-review（代码审查）
**问题**：AI 代码写完不检查，直接交差

**强制流程**：
1. **自审**：AI 先自己审查一遍
2. **清单检查**：
   - 代码是否清晰易懂？
   - 是否有潜在的 bug？
   - 是否遵循项目规范？
   - 是否有性能问题？
   - 是否有安全问题？
3. **修复问题**
4. **标记完成**

**审查清单**：
```
□ 功能正确性
  - 代码逻辑是否正确？
  - 边界条件是否处理？
  - 错误处理是否完善？

□ 代码质量
  - 变量/函数命名是否清晰？
  - 是否有适当的注释？
  - 代码是否过于复杂？

□ 性能
  - 是否有明显的性能问题？
  - 循环是否可以优化？

□ 安全
  - 是否有 SQL 注入风险？
  - 是否有 XSS 风险？
  - 敏感数据是否泄露？

□ 测试
  - 是否有单元测试？
  - 测试覆盖是否充分？
```

---

### Skill 6: pre-flight（完成前验证）
**问题**：AI 说"完成了"，但跑不起来

**强制检查**：
1. 代码能运行吗？
2. 测试通过了吗？
3. 文档更新了吗？
4. 没有 lint 错误？
5. 没有新的 console.error？

**使用场景**：
```
AI：
"在宣布功能完成前，我需要验证：

□ 运行测试：pytest tests/ -v ✓
□ Lint 检查：ruff check . ✓
□ 类型检查：mypy . ✓
□ 功能验证：curl localhost:8000/api/login ✓
□ 端到端测试：playwright test ✓

所有检查通过，功能完成！"
```

---

## 🚀 快速开始

### 方法 1: Claude Code（推荐）

```bash
# 1. 克隆 Superpowers 仓库
git clone https://github.com/obra/superpowers ~/.claude/skills/superpowers

# 2. 在 Claude Code 中启用
# 创建 ~/.claude/projects/default/.claude.json
{
  "permissions": {
    "allow": ["*"]
  },
  "skills": {
    "workspace": {
      "superpowers": true
    }
  }
}

# 3. 开始使用
# 在 Claude Code 中输入：
# /skill brainstorm
# /skill tdd
```

### 方法 2: Cursor Agent

```bash
# 1. 克隆到 Cursor skills 目录
git clone https://github.com/obra/superpowers ~/.cursor/skills/superpowers

# 2. 在 Cursor 设置中启用
# Settings → Features → Agent → Skills → superpowers

# 3. 使用
# Ctrl+L 打开 Agent，对 AI 说：
# "使用 Superpowers 的 tdd workflow 开发这个功能"
```

### 方法 3: 自定义集成

对于其他 AI 工具，可以直接复制 Skills 文件到你的项目中：

```bash
# 克隆仓库
git clone https://github.com/obra/superpowers /tmp/superpowers

# 复制需要的 Skills
cp /tmp/superpowers/skills/brainstorm.md ./skills/
cp /tmp/superpowers/skills/tdd.md ./skills/
cp /tmp/superpowers/skills/debugging.md ./skills/

# 在 AI 系统提示词中注入
# 将 skills/*.md 的内容添加到系统提示词
```

---

## 📋 与 LumiLearn 集成

### LumiLearn 现有规范 vs Superpowers

| LumiLearn 规范 | Superpowers Skill | 对应关系 |
|---------------|-------------------|---------|
| PRODUCT.md | brainstorm | 需求澄清 |
| DESIGN.md | - | 设计规范（本项目特有） |
| AGENTS.md | workflow + pre-flight | 工作流程 + 完成验证 |
| PROJECT_PRINCIPLES.md | code-review | 编码原则 + 代码审查 |
| - | tdd | 测试驱动（本项目待加强） |
| - | git-worktree | Git 隔离（本项目待加强） |
| - | debugging | 系统调试（本项目待加强） |

### 建议的 LumiLearn Superpowers 配置

创建 `e:\学习LLM\lumilearn\.superpowers` 目录：

```
lumilearn/.superpowers/
├── skills/
│   ├── brainstorm.md       # 需求澄清（必选）
│   ├── tdd.md              # 测试驱动（推荐）
│   ├── debugging.md        # 系统调试（推荐）
│   ├── code-review.md      # 代码审查（必选）
│   └── pre-flight.md       # 完成验证（必选）
├── workflows/
│   └── lumilearn-dev.md    # LumiLearn 开发工作流
└── .claude.json            # Claude Code 配置
```

---

## 🎓 Superpowers vs 传统 AI 编程

| 方面 | 传统 AI 编程 | Superpowers |
|------|-------------|-------------|
| **需求理解** | 直接开干，边做边改 | 先澄清，确认后再做 |
| **代码修改** | 直接改 main 分支 | git worktree 隔离 |
| **测试** | 写完代码再补测试 | TDD，先写测试 |
| **调试** | 试错法，改改试试 | 系统性调试，找根因 |
| **代码质量** | 写完交差 | 自审 + 审查清单 |
| **完成标准** | AI 说完成了 | 5 项验证全部通过 |

---

## 💡 最佳实践

### 1. 组合使用 Skills

不要只用某一个 Skill，而是组合使用：

```
项目开发 = brainstorm + git-worktree + tdd + debugging + code-review + pre-flight
```

### 2. 根据任务选择

| 任务类型 | 推荐 Skills |
|---------|------------|
| 新功能开发 | brainstorm → tdd → code-review → pre-flight |
| Bug 修复 | debugging → code-review → pre-flight |
| 代码重构 | tdd → code-review → pre-flight |
| 小改动 | code-review → pre-flight |

### 3. 坚持执行

Superpowers 的核心是纪律，要坚持执行每个 Skill 的完整流程，不要跳过步骤。

---

## 🔗 资源链接

| 资源 | 链接 |
|------|------|
| GitHub 仓库 | https://github.com/obra/superpowers |
| 官方文档 | https://github.com/obra/superpowers#readme |
| 技能列表 | skills/ 目录 |
| 工作流示例 | workflows/ 目录 |

---

## 📚 相关项目

| 项目 | Stars | 说明 |
|------|-------|------|
| obra/superpowers | 213K+ | AI 编程工程纪律框架（本文） |
| Cursor | N/A | AI 原生 IDE |
| Claude Code | N/A | Anthropic 官方 CLI Agent |
| Codex | N/A | OpenAI 官方 Coding Agent |

---

*版本: v1.0.0 | 更新: 2026-06-09*
*基于 obra/superpowers v5.1.0 编写*
