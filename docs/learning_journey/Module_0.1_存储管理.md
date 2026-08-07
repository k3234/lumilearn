# Module 0.1 — 存储管理与磁盘空间优化

**日期**: 2026-06-01
**状态**: ✅ 完成
**相关模块**: Module 0（基础运维）
**难度**: ⭐⭐☆☆☆

---

## 📚 学习目标

完成本模块后，你将能够：

1. 使用 `shutil.disk_usage()` 监控 C 盘磁盘空间使用情况
2. 理解并实现安全的文件清理策略（先预览后执行）
3. 掌握 `os.symlink` 创建符号链接实现大文件跨盘迁移
4. 使用 `glob` / `fnmatch` 模式匹配批量查找目标文件
5. 生成结构化 JSON 清理日志用于审计和回溯
6. 理解"安全边界"概念——确保清理脚本只操作项目文件，不触碰系统目录

---

## 🧭 实现步骤（分步详解）

### 步骤 1：确定清理目标和安全策略

在设计存储清理工具之前，首先要明确：

| 清理目标 | 文件类型 | 安全策略 |
|----------|----------|----------|
| 旧训练检查点 | `outputs/` 子目录、`checkpoints/*.pt` | 保留最新一个 |
| 临时文件 | `*.tmp`、`*.cache` | 全部清理（可重建） |
| 过期日志 | `*.log`（>7天） | 按时间戳判断 |
| Python 缓存 | `__pycache__/`、`.pytest_cache/`、`*.pyc` | 全部清理（自动重建） |
| 大文件迁移 | >100MB 文件 | 移走 + 创建符号链接 |

**安全底线**：
- 白名单目录（`.git/`、`config/`、`data/`）永不触碰
- 路径越界检查：所有操作限定在项目根目录内
- `--dry-run` 预览模式：先看会删什么，再决定是否执行

### 步骤 2：实现磁盘空间检查

使用 `shutil.disk_usage()` 是 Python 标准库中最简单直接的磁盘空间获取方式：

```python
import shutil

# shutil.disk_usage 返回 namedtuple: (total, used, free)
# 三个值都以字节为单位
使用情况 = shutil.disk_usage("C:\\")
总空间GB = 使用情况.total / (1024 ** 3)   # 除以 1024^3 转换为 GiB（二进制换算）
已用GB = 使用情况.used / (1024 ** 3)
可用GB = 使用情况.free / (1024 ** 3)
```

**关键知识点**：
- `shutil.disk_usage` 在所有主流操作系统（Windows/Linux/macOS）上均可用
- 返回的数值是精确的字节数，需要除以 `1024³`（1073741824）才能转为 GiB（严格区分：磁盘厂商按 1000³ 计算 GB，系统按 1024³ 计算 GiB，二者相差约 7%）
- 在清理前后各调用一次，对比差异即可验证释放效果

### 步骤 3：实现安全检查函数

安全检查是防止误删的核心机制：

```python
def 安全检查(路径: Path) -> bool:
    # 规则 1：路径必须在项目根目录内
    try:
        解析路径 = 路径.resolve()
        解析路径.relative_to(PROJECT_ROOT)  # 如果不在项目内，抛 ValueError
    except ValueError:
        return False

    # 规则 2：路径不能经过白名单目录
    路径部件 = set(part for part in 解析路径.relative_to(PROJECT_ROOT).parts)
    if 路径部件 & {".git", "config", "data"}:
        return False

    return True
```

**设计思路**：
- `Path.resolve()` 会把相对路径变为绝对路径，防止 `../` 越界攻击
- `Path.relative_to()` 如果目标不是当前路径的子路径，会抛出 `ValueError`
- 白名单使用集合交集运算，O(1) 效率

### 步骤 4：实现训练检查点清理

训练检查点通常是 `.pt` 文件或按时间戳命名的子目录：

```python
def 清理训练检查点(预览模式, 激进模式):
    输出目录 = PROJECT_ROOT / "outputs"
    # 按名称排序（名称中包含时间戳），最新的在最后
    检查点列表 = sorted(
        [d for d in 输出目录.iterdir() if d.is_dir()],
        key=lambda d: d.name,
    )
    # 保留最新（最后一个），删除其余
    if len(检查点列表) > 1:
        保留 = 检查点列表[-1]
        待删除 = 检查点列表[:-1]
        for 检查点 in 待删除:
            if 预览模式:
                print(f"[预览] 将删除: {检查点}")
            else:
                shutil.rmtree(检查点)  # 递归删除整个目录
```

**为什么保留最新一个？**
- 最新检查点代表训练的最新进度
- 删除所有检查点意味着训练进度完全丢失
- 保留一个 = 安全底线

### 步骤 5：实现复杂模式匹配（fnmatch）

`glob` 只支持当前目录的简单模式匹配，要递归扫描需要配合 `os.walk` + `fnmatch`：

```python
import fnmatch

for root, _dirs, files in os.walk(PROJECT_ROOT):
    for f in files:
        if fnmatch.fnmatch(f, "*.tmp"):
            # 匹配到临时文件，执行清理逻辑
            文件路径 = Path(root) / f
```

**glob vs fnmatch 对比**：

| 工具 | 适用场景 | 限制 |
|------|----------|------|
| `Path.glob("*.py")` | 单层目录匹配 | 不递归（需 `**/*.py`） |
| `Path.rglob("*.py")` | 递归匹配 | 不支持复杂条件 |
| `fnmatch.fnmatch()` | 自定义遍历+匹配 | 需配合 `os.walk` |

### 步骤 6：实现大文件迁移 + 符号链接

这是整个系统最复杂的功能，工作原理如下：

```
【迁移前】                      【迁移后】
C:\项目\大文件.pt ──────>  D:\lumilearn_migrated\大文件.pt
                            ↑
C:\项目\大文件.pt ─── 符号链接 ──┘
```

代码实现：

```python
import os
import shutil

# 1. 移动文件到目标盘
shutil.move(str(原路径), str(目标路径))  # 物理移动

# 2. 在原位置创建符号链接
os.symlink(str(目标路径), str(原路径))   # 创建软链接

# 3. 效果：C盘空间释放，但文件仍然可访问
```

**⚠️ Windows 特别注意事项**：
- `os.symlink` 在 Windows 上需要**管理员权限**或开启**开发者模式**
- 如果 symlink 失败，代码会自动回滚（将文件移回原位置）
- 目标路径会保持相同的目录结构，便于管理

### 步骤 7：生成 JSON 清理日志

JSON 格式的日志比纯文本日志更适合程序化分析和审计：

```python
日志数据 = {
    "时间戳": "2026-06-01 12:00:00",
    "模式": "标准模式 + 实际执行",
    "清理前C盘空间": {"总空间_GB": 256.0, "已用_GB": 180.5, "可用_GB": 75.5},
    "清理后C盘空间": {"总空间_GB": 256.0, "已用_GB": 175.2, "可用_GB": 80.8},
    "释放空间": "5.30 GB",
    "释放字节": 5690831667,
    "处理项数": 42,
    "达到目标": True,
    "删除文件列表": [
        {"路径": "...", "类型": "检查点目录", "大小": 1073741824, "状态": "已删除"},
        ...
    ]
}

with open(日志路径, "w", encoding="utf-8") as f:
    json.dump(日志数据, f, ensure_ascii=False, indent=2)
```

---

## 💻 关键代码（带注释）

### 完整功能架构

```
storage_cleaner.py (v4.0)
│
├── 配置区
│   ├── PROJECT_ROOT     # 项目根目录
│   ├── C_DRIVE          # C盘路径
│   ├── WHITELIST_DIRS   # 白名单目录（永不触碰）
│   ├── TARGET_FREE_BYTES  # 目标释放 5GB
│   └── LOG_RETENTION_DAYS # 日志保留 7 天
│
├── 工具函数
│   ├── 格式化大小()     # 字节 → 人类可读
│   ├── 安全检查()       # 路径安全边界
│   ├── 检查磁盘空间()   # shutil.disk_usage
│   └── 获取清理日志路径() # 时间戳命名
│
├── 清理功能
│   ├── 清理训练检查点() # outputs/ + checkpoints/*.pt
│   ├── 清理临时文件()   # *.tmp + *.cache
│   ├── 清理日志文件()   # *.log（>7天）
│   ├── 清理Python缓存() # __pycache__ + .pytest_cache
│   └── 迁移大文件()     # os.symlink 跨盘迁移
│
├── 日志生成
│   └── 生成JSON清理日志() # 结构化 JSON 输出
│
└── main() 主流程
    ├── 阶段1: 清理前空间检查
    ├── 阶段2-6: 各类型清理
    ├── 阶段7: 清理后空间检查
    └── 汇总报告 + JSON日志
```

### 激进模式 vs 标准模式

| 维度 | 标准模式 | 激进模式 (`--aggressive`) |
|------|----------|---------------------------|
| 日志保留 | 7 天 | 3 天 |
| 检查点清理 | outputs/ 目录 | + checkpoints/*.pt, outputs/*.pt |
| 大文件阈值 | >100 MB | >50 MB |
| 临时文件 | *.tmp, *.cache | 同上（不受影响） |
| Python 缓存 | 全部清理 | 同上（不受影响） |

---

## 🎓 学习要点（核心知识点）

### 1. `shutil.disk_usage` — 磁盘空间监控

```python
import shutil
usage = shutil.disk_usage("C:\\")
# usage.total  → 总容量（字节）
# usage.used   → 已用空间（字节）
# usage.free   → 可用空间（字节）
```

- Python 3.3+ 标准库内置，无需安装第三方包
- 跨平台兼容（Windows/Linux/macOS）
- 返回值是 `namedtuple`，可用 `.total` `.used` `.free` 访问
- **字节转 GB**：`bytes / (1024 ** 3)`

### 2. `os.symlink` — 符号链接创建

```python
os.symlink(目标路径, 链接路径)
# 目标路径：文件实际存储位置（如 D:\data\model.pt）
# 链接路径：符号链接的存放位置（如 C:\project\model.pt）
```

**符号链接 vs 硬链接**：
- 符号链接（软链接）：类似"快捷方式"，指向目标路径，目标删除后链接失效
- 硬链接：多个文件名指向同一数据块，删除任意一个不影响数据
- Windows 上 `os.symlink` 需要管理员权限

**实际效果**：
- C 盘上看到一个"文件"，但实际数据在 D 盘
- 读取时系统自动跳转到 D 盘取数据，对程序透明
- C 盘空间被释放

### 3. `glob` / `fnmatch` — 文件模式匹配

```python
# Path.glob — 简单直接
for pt_file in Path("outputs").glob("*.pt"):
    print(pt_file)

# Path.rglob — 递归匹配
for py_file in Path(".").rglob("*.py"):
    print(py_file)

# fnmatch + os.walk — 最灵活
for root, dirs, files in os.walk("."):
    for f in files:
        if fnmatch.fnmatch(f, "*.tmp"):
            完整路径 = Path(root) / f
```

### 4. 文件清理策略 — 安全第一

| 原则 | 说明 |
|------|------|
| **先预览后执行** | `--dry-run` 模式让用户确认操作范围 |
| **白名单保护** | 关键目录（.git, config, data）永不触碰 |
| **路径越界检查** | 只操作项目目录内的文件 |
| **保留最新** | 检查点至少保留一个，不全部删除 |
| **可回滚设计** | 大文件迁移失败时自动回滚 |
| **完整日志** | JSON 格式记录每次操作的详细信息 |

---

## ❓ 常见问题（FAQ）

### Q1: 运行 `--target D:` 时报"需要管理员权限"，怎么办？

**A**: Windows 上创建符号链接需要管理员权限。有两种解决方式：
1. **以管理员身份运行**：右键 PowerShell/CMD → "以管理员身份运行"
2. **开启开发者模式**：设置 → 更新和安全 → 开发者选项 → 开启"开发人员模式"

### Q2: `--dry-run` 预览显示能释放 10GB，但实际执行只释放了 3GB，为什么？

**A**: 预览模式的估算是"乐观估计"——它计算的是所有候选文件的总大小。实际执行时：
- 某些文件可能已被其他程序占用
- 权限不够导致部分操作跳过
- 文件在预览后被修改或删除

建议预览后仔细检查输出，确认关键文件不会受影响。

### Q3: 为什么删除 `__pycache__` 和 `.pytest_cache` 是安全的？

**A**: 这些目录是 Python 运行时自动生成的**字节码缓存**：
- `__pycache__`：Python 导入模块时自动生成 `.pyc` 编译缓存
- `.pytest_cache`：pytest 测试框架的运行缓存
- 删除后下次运行时 Python/pytest 会自动重建，功能完全不受影响

### Q4: 白名单目录 `.git` 为什么被保护？

**A**: `.git` 目录包含 Git 版本控制的全部历史数据。误删会导致：
- 所有提交历史丢失
- 分支/标签信息丢失
- 项目变为"野文件"，无法追溯变更

### Q5: 激进模式 (`--aggressive`) 会删除什么额外内容？

**A**: 相比标准模式，激进模式额外：
- 缩短日志保留期（7天 → 3天）
- 清理 `checkpoints/*.pt` 和 `outputs/*.pt` 独立文件
- 降低大文件迁移阈值（100MB → 50MB）

建议在磁盘空间极度紧张时使用，平时用标准模式即可。

### Q6: JSON 清理日志有什么用？

**A**: JSON 日志可用于：
- **审计回溯**：知道某天删除了哪些文件
- **自动化分析**：脚本读取 JSON，统计各类型文件占比
- **空间趋势图**：积累多天日志，绘制磁盘空间变化曲线
- **误删恢复**：日志中的完整路径列表帮助定位被误删的文件

---

## 🔗 相关资源链接

| 资源 | 说明 |
|------|------|
| [Python shutil 官方文档](https://docs.python.org/3/library/shutil.html) | `shutil.disk_usage`、`shutil.rmtree`、`shutil.move` |
| [Python os.symlink 官方文档](https://docs.python.org/3/library/os.html#os.symlink) | 符号链接创建详解 |
| [Python pathlib 官方文档](https://docs.python.org/3/library/pathlib.html) | `Path.rglob`、`Path.relative_to` |
| [Python fnmatch 官方文档](https://docs.python.org/3/library/fnmatch.html) | Unix shell 风格通配符匹配 |
| [Python json 官方文档](https://docs.python.org/3/library/json.html) | JSON 序列化/反序列化 |
| [Python argparse 官方文档](https://docs.python.org/3/library/argparse.html) | 命令行参数解析 |
| [Windows 符号链接说明](https://learn.microsoft.com/en-us/windows/win32/fileio/symbolic-links) | Microsoft 官方符号链接文档 |
| LumiLearn archive/debug_scripts/storage_cleaner.py | 本模块实现代码（历史归档） |

---

## 📝 总结

存储管理是每个项目的**基础运维能力**。通过实现这个模块，我们学习了：

1. **磁盘空间监控** (`shutil.disk_usage`) — 实时了解 C 盘余量
2. **文件系统操作** (`os.walk`, `shutil.rmtree`, `shutil.move`) — 批量管理文件
3. **符号链接** (`os.symlink`) — 跨盘迁移的高级技巧
4. **安全编程** — 白名单、路径检查、预览模式、回滚机制
5. **结构化日志** — JSON 格式日志支持程序化分析和审计

> **核心理念**：安全设计比清理效率更重要。**宁可少删，不能误删。**