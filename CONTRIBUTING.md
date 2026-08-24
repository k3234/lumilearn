# Contributing to LumiLearn

感谢你对 LumiLearn 的关注！本文档说明如何参与项目贡献。

## 开发环境搭建

### 1. 克隆仓库

```bash
git clone https://github.com/k3234/lumilearn.git
cd lumilearn
```

### 2. 创建虚拟环境

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# 或
source venv/bin/activate  # Linux/Mac
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
pip install -r requirements.txt  # 开发环境需要额外依赖
```

### 4. 安装 Ollama 和模型

```bash
# 安装 Ollama（见 https://ollama.com）
# 拉取模型
ollama pull qwen2.5:7b
ollama pull lumilearn-v2:latest
```

### 5. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际配置
```

## 代码规范

### Python 风格

- 遵循 [PEP 8](https://peps.python.org/pep-0008/) 代码风格
- 使用 [Ruff](https://github.com/astral-sh/ruff) 进行 linting
- 使用 [Black](https://black.readthedocs.io/) 进行代码格式化
- 类型注解：关键函数添加 `typing` 注解

```python
from typing import Dict, List, Optional, Tuple

def process_data(data: List[str]) -> Dict[str, int]:
    """处理数据并返回统计结果。"""
    ...
```

### 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
feat: 添加用户登录功能
fix: 修复数据库连接超时问题
docs: 更新 README 部署说明
test: 添加 feynman_engine 单元测试
chore: 更新依赖版本
refactor: 拆分 database.py 为独立模块
security: 移除硬编码密码和 IP
```

### 测试要求

- 新增功能必须编写单元测试
- 核心模块（feynman_engine, security_gateway）测试覆盖率 ≥ 80%
- 运行测试：`pytest tests/ -v`

## 贡献流程

### 1. 创建分支

```bash
git checkout -b feat/your-feature-name
# 或
git checkout -b fix/issue-description
```

### 2. 开发并提交

```bash
git add .
git commit -m "feat: 描述你的改动"
```

### 3. 推送到远程

```bash
git push origin feat/your-feature-name
```

### 4. 创建 Pull Request

在 GitHub 上创建 PR，描述：
- 改动内容
- 测试情况
- 相关 Issue 链接

## 目录结构说明

```
lumilearn/
├── framework/          # 核心框架
│   ├── api/           # API 路由
│   ├── admin/         # Agent 管理
│   ├── core/          # 配置系统
│   ├── engines/       # 教学引擎（feynman）
│   ├── models/        # 模型适配器
│   ├── security/      # 安全网关
│   └── services/      # 服务模块（RAG、语音等）
├── tests/             # 单元测试
├── scripts/           # 工具脚本
├── remote/            # 前端模板
├── config/            # 配置文件
├── deploy/            # 部署脚本
├── docs/              # 文档
└── video/             # 演示视频
```

## 安全注意事项

⚠️ **严禁提交以下敏感信息**：

- SSH 密码、API Key、Token
- 真实服务器 IP 地址
- SSH 私钥文件（.pem, .key）
- `.env` 文件

已在 `.gitignore` 中配置排除规则。提交前请运行：

```bash
git grep -l "password\|secret\|token" HEAD -- "*.py"
```

## 问题反馈

- 提交 Issue：描述问题、复现步骤、期望行为
- 加入讨论：在 Issue 中评论或发起讨论

## License

本项目采用 MIT License。贡献代码即表示同意以 MIT License 发布。
