# LumiLearn 技能注册表

## 总览

LumiLearn Skills 是模块化、可复用的功能单元，每个技能聚焦于一个特定能力领域。通过标准化的 SKILL.md + Python 实现 + config.json 模式，统一管理并对外提供服务。

## 已注册技能（8 个）

| 技能名 | 来源 | 核心能力 | 实现状态 |
|--------|------|---------|---------|
| **ai-collab** | 自研 | 多智能体协作（任务分解/角色分配/结果整合） | ✅ v1.0.0 |
| **codegraph** | [GitHub 30K ⭐](https://github.com/iamgreedy/codegraph) | 代码知识图谱预索引（函数/调用/依赖） | ✅ v1.0.0 |
| **build-your-own-x** | [GitHub](https://github.com/codecrafters-io/build-your-own-x) | 手搓教程项目（10+ 教程/7 语言） | ✅ v1.0.0 |
| **hyperframes** | 自研 | 教学动画视频生成 | ✅ v1.0.0 |
| **rtk** | 自研 | Redux Toolkit 状态管理生成 | ✅ v1.0.0 |
| **understand-anything** | [GitHub 20.1K ⭐](https://github.com/) | 代码库理解（文件/概念/问题图谱） | ✅ v1.0.0 |
| **taste-skill** | [GitHub 22K ⭐](https://github.com/Leonxlnx/taste-skill) | 前端审美注入系统（配色/字体/间距/动效） | ✅ v2.2.0 |
| **impeccable** | [GitHub 10K ⭐](https://github.com/pbakaus/impeccable) | 大厂级响应式设计（20个设计命令/反模式库） | ✅ v1.0.0 |

## 三个新技能（2026-06-01 新增）

### 1. CodeGraph - 代码知识图谱预索引

**来源**: [iamgreedy/codegraph](https://github.com/iamgreedy/codegraph)（30K Star）

**核心价值**: 在 4000+ 文件项目中，AI 检索次数从 52 → 3（17× 提升）

**文件结构**:
```
skills/codegraph/
├── SKILL.md          # 技能说明
├── README.md         # 快速使用
├── config.json       # 配置文件
└── graph_builder.py  # Python 实现
    ├── CodeGraphBuilder
    ├── scan() / search_function() / get_callers()
    ├── get_callees() / get_dependencies() / find_unused()
    └── export_graph_json()
```

**测试结果**: 扫描 LumiLearn 项目 359 个文件，提取 1762 个函数，21413 个调用关系，330 个模块

### 2. Build-Your-Own-X - 手搓开源教程

**来源**: [codecrafters-io/build-your-own-x](https://github.com/codecrafters-io/build-your-own-x)

**核心价值**: 10+ 教程项目，覆盖 6 大类（解释器/OS/网络/图形/工具/前端）

**文件结构**:
```
skills/build-your-own-x/
├── SKILL.md
├── README.md
├── config.json
└── project_manager.py
    ├── BuildYourOwnXManager
    ├── 10 个项目目录 (LISP 解释器/HTTP 服务器/光线追踪器...)
    ├── init_project() / list_projects() / recommend()
    └── mark_completed() / get_progress()
```

**测试结果**: 智能推荐、自动脚手架生成（Python/JS/C/C++ 模板）正常

### 3. Understand-Anything - 代码库理解

**来源**: CodeGraph 姊妹项目（20.1K Star）

**核心价值**: 把 AI 生成的"屎山"代码转成知识图谱，让 AI 编程工具有"项目地图"

**文件结构**:
```
skills/understand-anything/
├── SKILL.md
├── README.md
├── config.json
└── graph_builder.py
    ├── UnderstandAnything
    ├── 3 种节点: FileNode / ConceptNode / QuestionNode
    ├── build() / ask() / navigate() / get_concept()
    └── export_graph_json()
```

**测试结果**: 提取 437 个文件节点，11 个概念节点，5 个问题节点，321 个关系

## 技能协同

### CodeGraph + UA 互补

| 维度 | CodeGraph | Understand-Anything |
|------|-----------|---------------------|
| 核心 | 函数/调用关系 | 概念/问题/文件 |
| 粒度 | 细（符号级） | 粗（概念级） |
| AI 焦点 | 定位代码位置 | 理解代码意图 |
| 适用 | 重构、检索 | 学习、答疑 |

**推荐组合**: CodeGraph 定位具体代码 → UA 理解设计意图

### 三技能工作流示例

```
用户: "理解 LumiLearn 的 tokenizer 实现"

Step 1 - CodeGraph: 定位 tokenizer 相关函数
  → 找到 13 个 tokenizer 函数
  → load_model_and_tokenizer @ export_gguf_v10_llama.py
  → 被调用 6 次

Step 2 - UA: 理解 tokenizer 概念
  → 概念: 分词
  → 涉及 6 个文件

Step 3 - Build-Your-Own-X: 推荐学习项目
  → 推荐手搓 LISP 解释器（练 AST 和分词）
```

## 技能注册机制

通过 `skills/__init__.py` 自动发现并注册所有技能：

```python
from skills import get_registry

reg = get_registry()
# 输出: [Skills] 已加载: codegraph v1.0.0
#       [Skills] 已加载: build-your-own-x v1.0.0
#       [Skills] 已加载: understand-anything v1.0.0
#       ...

# 列出所有技能
for s in reg.list_all():
    print(f"{s['name']}: {s['description']}")

# 按 tag 搜索
ai_skills = reg.search(tag='ai-coding')  # 2 个
```

## 安装与卸载

新增技能只需：
1. 在 `skills/<skill-name>/` 下创建目录
2. 编写 `SKILL.md`（YAML frontmatter + Markdown 详情）
3. 编写 `config.json`（可选）
4. 编写 `<skill>.py`（可选，提供 Python API）

技能会自动被注册表发现并加载。

## 上传到 GitHub 状态

⚠️ **当前状态**: 所有技能在本地 `e:\学习LLM\lumilearn\skills\` 下完成并通过测试

📋 **上传计划**: 按照用户规则，**需用户同意后才能 git push 到远程**

新增的文件统计：
- `codegraph/`: SKILL.md (300+ 行), graph_builder.py (250+ 行), config.json, README.md
- `build-your-own-x/`: SKILL.md (350+ 行), project_manager.py (300+ 行), config.json, README.md
- `understand-anything/`: SKILL.md (350+ 行), graph_builder.py (300+ 行), config.json, README.md
- `taste-skill/`: SKILL.md (400+ 行), taste_skill.py (300+ 行), config.json, README.md
- `impeccable/`: SKILL.md (350+ 行), impeccable.py (250+ 行), config.json, README.md
- 临时测试文件已清理

## 两个审美设计技能（2026-06-06 新增）

### 1. Taste-Skill - 前端审美注入系统

**来源**: [leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill)（22K+ Stars）

**核心价值**: 给 AI Coding Agent 注入顶级设计师和前端工程师的审美经验，告别"土味审美"

**文件结构**:
```
skills/taste-skill/
├── SKILL.md          # 完整审美规范文档
├── README.md         # 快速使用指南
├── config.json       # 配置文件
└── taste_skill.py    # Python 实现
    ├── TASTE_SYSTEM_PROMPT    # 系统提示词
    ├── COLOR_SCHEMES          # 配色方案
    ├── SPACING               # 间距常量
    ├── BORDER_RADIUS         # 圆角常量
    ├── SHADOWS               # 阴影样式
    └── TasteChecker          # 审美检查器类
```

**核心能力**:
1. **配色系统**: 禁止土味配色，60-30-10法则
2. **字体层级**: Inter/SF Pro专业字体，清晰层级
3. **间距系统**: 8px基准网格，标准化间距
4. **动效原则**: 流畅微交互，150-300ms过渡
5. **布局规范**: 卡片式设计，柔和阴影

**应用场景**:
- 动画生成器UI
- 网页部署landing page
- Agent交互界面
- 教学页面设计

### 2. Impeccable - 大厂级响应式设计

**来源**: [pbakaus/impeccable](https://github.com/pbakaus/impeccable)（10K+ Stars）

**作者**: Paul Bakaus (前 Google 开发者布道师)

**核心价值**: 20个设计命令 + 反模式库，让 AI 学会大厂级的响应式设计规范

**文件结构**:
```
skills/impeccable/
├── SKILL.md          # 完整设计规范文档
├── README.md         # 快速使用指南
├── config.json       # 配置文件
└── impeccable.py      # Python 实现
    ├── IMPECCABLE_SYSTEM_PROMPT     # 系统提示词
    ├── SLASH_COMMANDS              # 20个设计命令
    ├── BREAKPOINTS                 # 标准断点
    ├── ANTI_PATTERNS               # 反模式检查
    └── ImpeccableChecker           # 设计检查器类
```

**核心能力**:
1. **20个 Slash 命令**: 布局/响应式/视觉/交互全覆盖
2. **反模式库**: 内置"DO NOT"约束，精准狙击常见错误
3. **标准断点**: sm:640, md:768, lg:1024, xl:1280, 2xl:1536
4. **栅格系统**: 12列专业Grid
5. **触摸友好**: 44x44px最小触摸目标

**Slash 命令示例**:
```
/impeccable-responsive    # 添加完整响应式支持
/impeccable-mobile        # 优化移动端
/impeccable-grid          # 应用12列栅格
/impeccable-animation     # 添加微交互动效
/impeccable-focus         # 优化无障碍焦点
```

**应用场景**:
- 响应式教学页面
- 动画播放器界面
- 管理后台仪表盘
- 移动端优化
- 无障碍设计
