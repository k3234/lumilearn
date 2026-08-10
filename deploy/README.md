# LumiLearn 部署说明

本目录提供 LumiLearn 的一键部署工具：

| 文件 | 作用 |
| --- | --- |
| `setup.py` | 核心配置引导脚本（环境检测 / 依赖安装 / 端口配置 / 模型配置） |
| `setup.bat` | Windows 一键入口 |
| `setup.sh` | Linux / macOS 一键入口 |
| `README.md` | 本文档 |

---

## 1. 环境要求

- **Python ≥ 3.9**（已安装 pip）
- **Ollama**（可选）：本地模型推理服务，默认地址 `http://localhost:11434`；未安装时也可以先只配置云端 API，稍后再接入 Ollama
- **网络**：安装依赖需要访问 PyPI；使用云端大模型 API 需要相应网络环境

> 项目运行时依赖见根目录 `requirements.txt`（flask、requests、python-dotenv、pyyaml 等）。
> 若你的环境缺少 `pyyaml` 且 `requirements.txt` 未包含，请单独执行 `pip install pyyaml`。

---

## 2. Windows 一键部署

```bat
cd lumilearn
deploy\setup.bat
```

或直接双击 `deploy\setup.bat`。脚本会依次引导：

1. 环境检测（Python / pip）
2. 是否安装依赖（`pip install -r requirements.txt`，可输入 `n` 跳过）
3. 端口配置（逐服务启用 / 修改端口号，默认沿用当前配置）
4. 模型配置（Ollama 地址 + 默认模型；云端 API Key 可选）
5. 配置完成后运行 `start_services.bat` 启动服务

常用参数：

```bat
deploy\setup.bat --skip-deps   :: 跳过依赖安装
deploy\setup.bat --quick       :: 全部使用默认值，不交互（适合自动化/CI）
```

---

## 3. Linux 一键部署

```bash
cd lumilearn
chmod +x deploy/setup.sh
./deploy/setup.sh
```

常用参数：

```bash
./deploy/setup.sh --skip-deps   # 跳过依赖安装
./deploy/setup.sh --quick       # 全部使用默认值，不交互（适合自动化/CI）
```

配置完成后启动服务：

```bash
# 启动框架三端口（终端 18080 / REST API 18081 / 模型管理 18082）
./start.sh
```

> 根目录 `start.sh` **仅**启动框架三端口；需要同时启动 GOAI Web（5000）/ 教师门户（5001）时，
> Windows 请运行 `start_services.bat`，Linux / macOS 请运行 `deploy/start.sh`。

> 根目录 `start.sh` 会探测本机 Ollama（`localhost:11434`）；若配置了**远程 Ollama**，
> `start_services.bat` / `deploy/start.sh` 内部委托 `deploy/start.py`，由它从 `.env` 读取
> `OLLAMA_URL` / `OLLAMA_BASE_URL` 并注入各服务进程（无硬编码地址），
> 框架侧（`python -m framework.api.server --multi-port`）同样读取 `.env` 中的 `OLLAMA_BASE_URL`。

---

## 4. 端口配置说明

配置保存在 `config/framework.yaml` 的 `port_settings` 段，部署脚本只修改该段，其他字段（`server`、`ollama`、`security` 等）保持不变。

| 服务键 | 默认端口 | 说明 |
| --- | --- | --- |
| `terminal` | 18080 | 框架终端（HTML 界面） |
| `api` | 18081 | REST API |
| `models` | 18082 | 模型管理 |
| `goai_web` | 5000 | GOAI 学习 Web |
| `teacher_portal` | 5001 | 教师门户 |

每个服务可独立设置 `enabled`（是否启用）与 `port`（端口号，1-65535 整数）。
设置后需重启对应服务生效。也可在 Admin 面板「端口管理」中修改。

> **已知限制**：框架三端口（terminal/api/models）由 `framework.api.server --multi-port` 统一拉起，
> `enabled` 开关对框架三端口暂不生效（仅对 `goai_web` / `teacher_portal` 生效），后续版本改进。

---

## 5. 模型接入说明

### 5.1 本地 Ollama（默认）

- Ollama 地址保持默认 `http://localhost:11434`
- 脚本会探测 `/api/tags` 列出本机可用模型，供你选择默认模型（写入 `OLLAMA_MODEL`）

### 5.2 远程 Ollama

- 输入远程地址，如 `http://192.168.x.x:11434`（请使用你自己的服务器地址）
- 脚本会探测该地址的 `/api/tags` 校验连通性并列出可用模型
- 若探测失败，会提示跳过，可稍后手动修改 `.env` 中的 `OLLAMA_BASE_URL`

### 5.3 其他本地模型容器（可选，OpenAI 兼容）

支持 **vLLM / LM Studio / LocalAI / llama.cpp server** 等提供 OpenAI 兼容接口的本地容器。
运行 `deploy/setup.py` 后输入容器地址（如 `http://localhost:8000/v1`），脚本会自动调用 `/models`
发现容器内**全部模型**并注册到 `config/providers.yaml`；之后可在 Admin 面板「端口模型配置」中为任意端口选用。

常用容器默认地址：

| 容器 | 默认地址 |
| --- | --- |
| vLLM | `http://localhost:8000/v1` |
| LM Studio | `http://localhost:1234/v1` |
| LocalAI | `http://localhost:8080/v1` |
| llama.cpp server | `http://localhost:8080/v1` |

> 本地容器不需要 API Key（系统已兼容无 Key 场景）；`Ollama` 仍是默认推荐容器。

### 5.4 云端大模型 API（OpenAI 兼容）

脚本可选配置以下提供者（默认跳过，输入 `y` 后粘贴 API Key）：

| 环境变量 | 提供者 |
| --- | --- |
| `DOUBAO_API_KEY` | 豆包 |
| `ZHIPU_API_KEY` | 智谱 |
| `MOONSHOT_API_KEY` | Kimi |
| `MINIMAX_API_KEY` | MiniMax |

API Key 仅写入本仓库 `.env`（已被 `.gitignore` 忽略），不会硬编码在代码或配置模板中。

### 5.5 .env 说明

- `.env` 不存在时，脚本会从 `.env.example` 复制生成
- 写入采用"更新/追加"方式：只更新 `OLLAMA_BASE_URL`、`OLLAMA_URL`、`OLLAMA_MODEL` 与填写的 API Key，其他行与注释原样保留
- 隐私约定：不要将真实 IP、密码、API Key 提交到 GitHub 等公开仓库

---

## 6. 常见问题

**Q1：提示"缺少 PyYAML"？**
执行 `pip install pyyaml`（或 `pip install -r requirements.txt`）后重试。

**Q2：Ollama 探测失败怎么办？**
确认 Ollama 已启动（`ollama serve`），且地址正确。若未安装 Ollama，可直接跳过，先使用云端 API 或稍后接入；配置值已写入 `.env`，不影响其他服务启动。

**Q3：修改端口后不生效？**
重启对应服务；框架三端口优先读取 `config/framework.yaml` 的 `port_settings`，确认 `enabled: true` 且端口未被占用。

**Q4：goai_web.py 连不上远程 Ollama？**
`goai_web.py` 读取环境变量 `OLLAMA_URL`（部署脚本会与 `OLLAMA_BASE_URL` 同步写入 `.env`）。通过 `start_services.bat` 启动时，其内部委托 `deploy/start.py`，会从 `.env` 读取 `OLLAMA_URL` / `OLLAMA_BASE_URL` 并注入子进程环境，无硬编码地址；确认 `.env` 中两个变量已同步更新后重启服务即可。

**Q5：--quick 模式会做什么？**
端口全部沿用当前配置；Ollama 地址用 `localhost` 并探测（探测失败则保留默认模型名）；云端 API 全部跳过。适合无人值守自动化部署。
