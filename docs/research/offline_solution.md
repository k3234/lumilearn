# LumiLearn 完全离线配置方案

> 设计日期：2026-06-03
> 硬件：R7-7840HS（8核16线程，集成 GPU 780M）
> 目标：脱离 Ollama，实现完全本地推理

---

## 一、当前架构分析

```
当前 LumiLearn 架构
┌─────────────────────────────────────────────────────────────────┐
│                         用户浏览器                                │
│                    http://192.168.2.63:18080                    │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    lumiterm_local_server.py                      │
│                      (HTTP API 服务)                            │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    langgraph_engine.py                          │
│                      (云端 API 调用)                            │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Ollama (192.168.2.63:11434)               │
│                        (本地模型服务)                           │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                   qwen2.5:7b / lumilearn-v5                     │
│                      (本地模型文件)                             │
└─────────────────────────────────────────────────────────────────┘

问题：
1. langgraph_engine.py 依赖外部 API（DeepSeek/Claude 等）
2. 模型服务依赖 Ollama
3. 无法完全离线运行
```

---

## 二、离线方案对比

### 2.1 方案对比矩阵

| 方案 | 依赖 | CPU 支持 | GPU 支持 | 难度 | 推荐度 |
|------|------|----------|----------|------|--------|
| **方案A：纯 Ollama** | Ollama | ✅ | ✅ | ⭐ | ⭐⭐⭐ |
| **方案B：llama.cpp** | 无 | ✅ | ✅ | ⭐⭐ | ⭐⭐⭐⭐ |
| **方案C：llamafile** | 无 | ✅ | ✅ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **方案D：vLLM** | 需要 GPU | ❌ | ✅ | ⭐⭐⭐ | ⭐⭐ |

---

## 三、方案A：优化 Ollama 离线配置（最简单）

### 3.1 核心思路

```
Ollama 本身就是本地的，只需要：
1. 模型文件完全本地存储
2. 不调用任何外部 API
3. 修改 langgraph_engine.py 绕过 API 调用
```

### 3.2 实施步骤

#### 步骤1：下载完整模型文件

```bash
# 创建本地模型存储目录
mkdir -p e:\学习LLM\models

# 下载模型（一次性，之后无需网络）
ollama pull qwen2.5:7b
ollama pull llama3.2:3b

# 查看模型位置
ollama list
```

#### 步骤2：修改代码绕过外部 API

修改 [langgraph_engine.py](file:///e:/学习LLM/lumilearn/langgraph_engine.py)，强制使用本地 Ollama：

```python
# langgraph_engine.py

# ============ 配置 ============
# 强制使用本地模型，不调用外部 API
USE_LOCAL_ONLY = True
OLLAMA_BASE = "http://192.168.2.63:11434"
LOCAL_MODEL = "qwen2.5:7b"

def call_model(prompt, model=None):
    """调用模型（完全本地）"""
    if USE_LOCAL_ONLY:
        # 只使用本地 Ollama
        return call_ollama(prompt, model or LOCAL_MODEL)

    # 原有逻辑：多模型投票 + 云端调用
    ...
```

#### 步骤3：测试离线运行

```bash
# 1. 确保 Ollama 服务运行
ollama serve

# 2. 测试本地模型
curl http://192.168.2.63:11434/api/generate \
  -d '{"model": "qwen2.5:7b", "prompt": "你好"}'

# 3. 启动 LumiLearn
cd e:\学习LLM\lumilearn
python lumiterm_local_server.py
```

---

## 四、方案B：llama.cpp（推荐）

### 4.1 核心优势

| 优势 | 说明 |
|------|------|
| **零依赖** | 不需要 Ollama，不需要 Python |
| **跨平台** | Windows/Mac/Linux 通用 |
| **CPU 优化** | 专为 CPU 推理优化 |
| **GPU 支持** | 支持 CUDA/OpenCL/Vulkan |
| **量化支持** | 4bit/8bit 量化，减小体积 |

### 4.2 实施步骤

#### 步骤1：下载 llama.cpp

```bash
# Windows 版本
# 下载地址：https://github.com/ggerganov/llama.cpp/releases

# 选择 llama-cli-windows-bin.zip
# 下载后解压到 e:\学习LLM\llama.cpp
```

#### 步骤2：下载模型（GGUF 格式）

```bash
# 下载 Qwen2.5-7B 的 Q4_K_M 量化版本（约 4GB）
# 推荐从 HuggingFace 下载

# 方法1：使用 huggingface-cli
huggingface-cli download Qwen/Qwen2.5-7B-Instruct-GGUF qwen2.5-7b-instruct-q4_k_m.gguf --local-dir e:\学习LLM\models

# 方法2：直接下载
# https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/tree/main
```

#### 步骤3：运行本地推理

```bash
cd e:\学习LLM\llama.cpp

# CPU 推理（7B 模型约 4GB 内存）
.\llama-cli.exe ^
  -m e:\学习LLM\models\qwen2.5-7b-instruct-q4_k_m.gguf ^
  -n 512 ^
  --temp 0.7 ^
  -p "你是小澍，一个专业的AI学习助手。请用简洁的语言回答。\n\n用户：%s\n小澍：" ^
  --no-display-prompt

# GPU 推理（使用 780M）
.\llama-cli.exe ^
  -m e:\学习LLM\models\qwen2.5-7b-instruct-q4_k_m.gguf ^
  -ngl 99 ^
  -n 512 ^
  --temp 0.7 ^
  -p "你是小澍，一个专业的AI学习助手。\n\n用户：%s\n小澍："
```

#### 步骤4：启动 HTTP 服务

```bash
# 启动 llama.cpp HTTP 服务器（兼容 OpenAI API）
.\llama-server.exe ^
  -m e:\学习LLM\models\qwen2.5-7b-instruct-q4_k_m.gguf ^
  -ngl 99 ^
  -c 2048 ^
  --host 192.168.2.63 ^
  --port 8080

# 现在可以通过 http://192.168.2.63:8080/v1/chat/completions 访问
```

#### 步骤5：修改 LumiLearn 对接

修改 [langgraph_engine.py](file:///e:/学习LLM/lumilearn/langgraph_engine.py)：

```python
# langgraph_engine.py

import requests

# llama.cpp HTTP 服务器地址
LLAMA_CPP_BASE = "http://192.168.2.63:8080/v1"
MODEL_NAME = "qwen2.5-7b-instruct"

def call_llama_cpp(prompt, max_tokens=512):
    """调用本地 llama.cpp 服务器"""
    response = requests.post(
        f"{LLAMA_CPP_BASE}/chat/completions",
        json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
    )
    return response.json()["choices"][0]["message"]["content"]

def call_model(prompt, model=None):
    """统一调用接口"""
    return call_llama_cpp(prompt)
```

---

## 五、方案C：llamafile（极简推荐 ⭐⭐⭐⭐⭐）

### 5.1 核心优势

| 优势 | 说明 |
|------|------|
| **单文件** | 一个 .exe 文件包含所有内容 |
| **无需安装** | 下载后直接运行 |
| **自动 GPU** | 自动检测并使用 GPU |
| **内置 HTTP** | 自带 API 服务器 |
| **跨平台** | Windows/Mac/Linux 通用 |

### 5.2 实施步骤（最简单）

#### 步骤1：下载 llamafile

```bash
# 下载经过 llamafile 打包的 Qwen 模型
# 地址：https://github.com/Mozilla-Ocho/llamafile/releases

# 或者下载空壳 llamafile + 自己的模型
# 下载 llamafile.exe
Invoke-WebRequest -Uri "https://github.com/Mozilla-Ocho/llamafile/releases/download/0.1.8/llamafile.exe" -OutFile e:\学习LLM\llamafile.exe
```

#### 步骤2：下载模型

```bash
# 下载 Qwen2.5-7B GGUF 模型
# 地址：https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF

# 下载 qwen2.5-7b-instruct-q4_k_m.gguf（约 4GB）
```

#### 步骤3：一键启动

```powershell
# 将模型文件和 llamafile.exe 放在同一目录
cd e:\学习LLM
.\llamafile.exe -m qwen2.5-7b-instruct-q4_k_m.gguf --host 192.168.2.63 --port 8080

# 搞定！现在可以访问 http://192.168.2.63:8080
```

### 5.3 llamafile vs Ollama 对比

| 维度 | llamafile | Ollama |
|------|-----------|--------|
| **文件数量** | 1 个 .exe | 多个文件 + 模型目录 |
| **安装** | 无需安装 | 需要安装 |
| **GPU** | 自动检测 | 需要配置 |
| **API 兼容** | OpenAI 兼容 | 兼容 |
| **内存占用** | 更低 | 较高 |
| **适合场景** | 嵌入式/移动端 | 服务器 |

---

## 六、完全离线架构（最终方案）

### 6.1 架构图

```
完全离线 LumiLearn 架构
┌─────────────────────────────────────────────────────────────────┐
│                         用户浏览器                                │
│                    http://192.168.2.63:18080                    │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    lumiterm_local_server.py                      │
│                      (HTTP API 服务)                            │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    langgraph_engine.py                          │
│                   (使用 llama.cpp API)                          │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    llama.cpp HTTP Server                         │
│                  (http://192.168.2.63:8080)                    │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│              Qwen2.5-7B-Instruct-Q4_K_M.gguf                    │
│                    (本地模型文件，约 4GB)                        │
└─────────────────────────────────────────────────────────────────┘

关键变化：
1. ❌ 移除 Ollama
2. ❌ 移除外部 API 依赖
3. ✅ 使用 llama.cpp / llamafile
4. ✅ 完全本地运行
5. ✅ 支持 CPU + GPU 推理
```

### 6.2 文件清单

```
e:\学习LLM\lumilearn_offline\
├── lumiterm_local_server.py    # LumiLearn HTTP 服务
├── langgraph_engine.py         # 修改后：只用 llama.cpp
├── smart_reply_engine.py        # 智能回复引擎
├── lesson_engine.py            # 课程引擎
├── models\                     # 模型目录
│   └── qwen2.5-7b-q4_k_m.gguf  # 量化模型（约 4GB）
├── llama.cpp\                   # llama.cpp 目录
│   ├── llama-cli.exe           # 命令行工具
│   └── llama-server.exe        # HTTP 服务器
└── data\                       # 数据目录
    └── lessons.json            # 课程数据
```

---

## 七、量化模型推荐（R7-7840HS）

### 7.1 模型选择

| 模型 | 量化 | 内存需求 | 推理速度 | 推荐度 |
|------|------|----------|----------|--------|
| Qwen2.5-7B | Q4_K_M | ~4GB | 快 | ⭐⭐⭐⭐⭐ |
| Qwen2.5-3B | Q4_K_M | ~2GB | 很快 | ⭐⭐⭐⭐ |
| Llama3.2-3B | Q4_K_M | ~2GB | 很快 | ⭐⭐⭐ |
| Phi-3.5-mini | Q4_K_M | ~2GB | 很快 | ⭐⭐⭐⭐ |

### 7.2 下载地址

```bash
# HuggingFace 模型下载
# Qwen2.5-7B-Q4
https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF

# Llama3.2-3B
https://huggingface.co/unsloth/Llama-3.2-3B-Instruct-GGUF

# Phi-3.5-mini
https://huggingface.co/microsoft/Phi-3.5-mini-instruct-gguf
```

---

## 八、实施时间表

### 8.1 本周任务

```
Day 1: 下载 llamafile 和模型
├── 下载 llamafile.exe
├── 下载 Qwen2.5-7B-Q4 模型
└── 测试命令行推理

Day 2: 启动 HTTP 服务
├── 启动 llama-server.exe
├── 测试 API 调用
└── 修改 langgraph_engine.py

Day 3: 集成测试
├── 启动 lumiterm_local_server.py
├── 测试完整流程
└── 验证离线运行
```

### 8.2 验收标准

```
✅ 模型完全本地存储
✅ 无外部 API 调用
✅ 可以断网运行
✅ 推理延迟可接受（<10s）
✅ 支持 CPU 和 GPU
```

---

## 九、总结

### 9.1 推荐方案

| 优先级 | 方案 | 理由 |
|--------|------|------|
| 🥇 | **方案C：llamafile** | 最简单，单文件运行 |
| 🥈 | **方案B：llama.cpp** | 更灵活，适合定制 |
| 🥉 | **方案A：优化 Ollama** | 最简单但仍需 Ollama |

### 9.2 关键优势

```
完全离线后：
✅ 不需要网络连接
✅ 数据完全私有
✅ 无 API 费用
✅ 可在偏远地区使用
✅ 更适合教育场景
```

---

## 十、下一步行动

```bash
# 1. 下载 llamafile
Invoke-WebRequest -Uri "https://github.com/Mozilla-Ocho/llamafile/releases/download/0.1.8/llamafile.exe" -OutFile e:\学习LLM\llamafile.exe

# 2. 下载模型（Qwen2.5-7B-Q4）
# 访问 https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF
# 下载 qwen2.5-7b-instruct-q4_k_m.gguf

# 3. 启动服务
.\llamafile.exe -m qwen2.5-7b-instruct-q4_k_m.gguf --host 192.168.2.63 --port 8080

# 4. 测试
curl http://192.168.2.63:8080/v1/models
```

---

需要我帮您下载并配置 llamafile 吗？