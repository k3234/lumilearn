# Superpowers - 让 AI 变成专业工程师

> 213K+ GitHub Stars | AI 编程工程纪律框架

---

## 🎯 为什么需要 Superpowers？

你是不是也有这样的经历：
- 打开 Claude Code / Cursor
- 敲一句"帮我写个登录接口"
- AI 噼里啪啦输出几百行代码
- 跑起来一看，逻辑对了七八成，但剩下那两成全是它自己发明的需求
- 你说这是 bug，它说好，改了一通，结果把能跑的地方也改坏了

**这不是 AI 不够聪明，是它太"勤快"了——不问、不验、不收，直接上手干。**

---

## 💡 Superpowers 的解决方案

> **不是给 AI 加能力，而是给 AI 加纪律**

Superpowers 把软件工程几十年积累的最佳实践，变成了 AI 必须遵守的铁律：
- ✅ 需求不澄清不干活
- ✅ 不写测试不写代码
- ✅ 调试必须找根因
- ✅ 完成后必须验证

---

## 🚀 5 分钟快速开始

### 步骤 1: 理解核心概念

Superpowers 有 **6 个核心 Skills**：

| Skill | 作用 | 解决的问题 |
|-------|------|----------|
| **brainstorm** | 需求澄清 | AI 不问清楚就干 |
| **git-worktree** | 分支隔离 | 直接改坏主分支 |
| **tdd** | 测试驱动 | 不写测试或后补测试 |
| **debugging** | 系统调试 | 试错式 debug |
| **code-review** | 代码审查 | 代码写完不检查 |
| **pre-flight** | 完成验证 | 说完成了但跑不通 |

### 步骤 2: 在 AI 工具中启用

**Claude Code（推荐）**：
```bash
git clone https://github.com/obra/superpowers ~/.claude/skills/superpowers
```

**Cursor**：
```bash
git clone https://github.com/obra/superpowers ~/.cursor/skills/superpowers
```

### 步骤 3: 开始使用

在 AI 对话中直接说：
```
"用 Superpowers 的 brainstorm 流程帮我设计这个功能"
"用 TDD 流程开发登录模块"
"用 debugging 流程修复这个 bug"
```

---

## 📁 目录结构

```
superpowers/
├── SKILL.md              ← 完整技能文档（详细说明）
├── README.md             ← 快速开始（本文档）
├── config.json           ← 元信息配置
└── lumilearn-workflow.md ← LumiLearn 专用工作流
```

---

## 🎯 LumiLearn 项目使用建议

### 新功能开发

```
1. brainstorm → 澄清需求
2. 设计方案（参考 DESIGN.md）
3. git worktree → 创建隔离分支
4. tdd → 先写测试
5. 写代码 → 让测试通过
6. code-review → 自审代码
7. pre-flight → 验证完成
8. 合并分支
```

### Bug 修复

```
1. debugging → 系统性定位根因
2. 修复根因（不是表象）
3. code-review → 检查修复
4. pre-flight → 验证修复
```

---

## 🔗 更多资源

- **GitHub**: https://github.com/obra/superpowers
- **详细文档**: 查看 SKILL.md
- **LumiLearn AGESMD**: 参考 PRODUCT.md, DESIGN.md, AGENTS.md

---

*最后更新: 2026-06-09*
