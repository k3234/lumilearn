# LumiLearn 开发工作流

> 整合 Superpowers 工程纪律 + AGESMD 规范

---

## 📋 概述

这个工作流整合了：
- **Superpowers**: AI 编程工程纪律框架（brainstorm → tdd → debugging → code-review → pre-flight）
- **AGESMD 规范**: LumiLearn 产品定义（PRODUCT.md, DESIGN.md, AGENTS.md）

---

## 🔄 完整开发流程

### Phase 1: 需求澄清（Superpowers: brainstorm）

**必须完成的任务**：
1. 阅读 PRODUCT.md 确认需求符合产品目标
2. 理解用户需求的本质
3. 列出需要澄清的问题
4. 给出 2-3 个可选方案
5. 等待用户确认后再继续

**澄清清单**：
```
□ 需求是否在 PRODUCT.md 定义的产品目标范围内？
□ 涉及哪些现有模块？
□ 有什么技术约束？
□ 成功标准是什么？
□ 优先级是高/中/低？
```

---

### Phase 2: 方案设计（参考 DESIGN.md）

**必须完成的任务**：
1. 阅读 DESIGN.md 了解设计规范
2. 确定文件结构和放置位置
3. 设计代码架构
4. 考虑性能、安全、可维护性
5. 给出设计方案供用户确认

**设计检查**：
```
□ 代码放在哪个目录？（framework/? skills/? scripts/?）
□ 遵循 DESIGN.md 的配色/字体/间距规范吗？（如果是 UI）
□ 遵循 AGENTS.md 的文件操作规范吗？
□ 需要新增还是修改现有代码？
```

---

### Phase 3: Git 隔离（Superpowers: git-worktree）

**必须完成的任务**：
1. 检查当前分支状态
2. 创建新的 worktree 或分支
3. 在隔离环境中开发

```bash
# 创建功能分支
git checkout -b feature/xxx

# 或者使用 worktree（推荐）
git worktree add ../feature-xxx main
cd ../feature-xxx
```

---

### Phase 4: TDD 开发（Superpowers: tdd）

**必须完成的任务**：
1. 先写一个失败的测试
2. 运行测试确认失败
3. 写最少的代码让测试通过
4. 重构优化代码
5. 重复直到功能完成

**测试优先清单**：
```
□ 有测试文件吗？（tests/test_xxx.py）
□ 测试能运行吗？
□ 测试覆盖核心功能吗？
□ 边界条件有测试吗？
```

---

### Phase 5: 系统调试（Superpowers: debugging）

**当遇到 Bug 时，必须遵循**：
1. 复现问题
2. 定位根因（不是表象）
3. 只修复根因
4. 验证修复
5. 记录根因和解决方案

**调试清单**：
```
□ 能复现这个 bug 吗？
□ 找到根因了吗？（不是表象）
□ 修复只改动必要的代码吗？
□ 修复后测试通过吗？
□ 有引入新的问题吗？
```

---

### Phase 6: 代码审查（Superpowers: code-review）

**必须完成的任务**：
1. AI 自审一遍
2. 按清单逐项检查
3. 修复发现的问题

**审查清单**：
```
□ 代码清晰易懂吗？（高一学生能看懂吗？）
□ 有中文注释吗？
□ 变量/函数命名清晰吗？
□ 有错误处理吗？
□ 遵循 DESIGN.md 规范吗？（如果是 UI）
□ 遵循 AGENTS.md 编码规范吗？
□ 没有引入不必要的依赖？
□ 代码简洁（没有多余代码）？
```

---

### Phase 7: 完成验证（Superpowers: pre-flight）

**在宣布完成前，必须验证**：

```
□ 功能测试通过了吗？
□ pytest tests/ -v ✓
□ 没有 lint 错误？（ruff check .）
□ 没有类型错误？（mypy .）
□ 文档更新了吗？（需要更新则更新）
□ 代码符合 AGESMD 规范吗？
```

---

### Phase 8: 提交代码

**Git 操作**：
```bash
# 1. 添加修改的文件
git add .

# 2. 提交（遵循 AGENTS.md 规范）
git commit -m "feat: 添加新功能描述

- 具体改动1
- 具体改动2"

# 3. 推送
git push origin feature/xxx

# 4. 如果使用了 worktree，合并后清理
git checkout main
git merge feature/xxx
git worktree remove ../feature-xxx
```

---

## 📝 快速检查清单

在完成任何任务前，确认以下所有项：

- [ ] **Phase 1**: 需求已澄清，用户已确认
- [ ] **Phase 2**: 设计方案已确认，参考了 DESIGN.md
- [ ] **Phase 3**: 在隔离分支中开发
- [ ] **Phase 4**: 有测试，测试通过
- [ ] **Phase 5**: Bug 已修复（如果有）
- [ ] **Phase 6**: 代码已自审
- [ ] **Phase 7**: 所有验证项通过
- [ ] **Phase 8**: 代码已提交

---

## 🎯 不同场景的工作流

### 新功能开发
```
brainstorm → 设计方案 → git-worktree → tdd → code-review → pre-flight → 提交
```

### Bug 修复
```
debugging → 修复根因 → code-review → pre-flight → 提交
```

### 小改动
```
code-review → pre-flight → 提交
```

### 重构
```
tdd → code-review → pre-flight → 提交
```

---

## 🔗 相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| Superpowers | [../superpowers/SKILL.md](SKILL.md) | 6 个核心 Skills |
| AGESMD | [../../PROJECT_PRINCIPLES.md](../../PROJECT_PRINCIPLES.md) | 开发原则 |
| AI Tools | [../ai-coding-tools/SKILL.md](../ai-coding-tools/SKILL.md) | AI 编程工具 |

---

*版本: v1.0.0 | 更新: 2026-06-09*
*整合 Superpowers + AGESMD*
