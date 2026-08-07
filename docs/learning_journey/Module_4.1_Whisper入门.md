# Module 4.1 — Whisper 语音识别入门

**日期**: 2026-06-01
**状态**: ✅ 完成
**相关模块**: Module 4（多模态能力）
**难度**: ⭐⭐⭐☆☆

---

## 📚 学习目标

完成本模块后，你将能够：

1. 理解 Whisper 语音识别模型的基本原理（编码器-解码器架构、多语言支持）
2. 使用 `openai-whisper` 库在本地加载并运行 Whisper 模型（CPU 即可）
3. 掌握 Whisper 模型大小选择（tiny / small / medium / large）及其适用场景
4. 使用 Flask 构建文件上传 API 端点，处理 multipart/form-data 请求
5. 理解音频格式处理（WAV、MP3 等）及临时文件管理
6. 掌握懒加载模式（全局单例）避免重复加载大型模型

---

## 🧠 Whisper 模型原理简介

### 架构概览

Whisper 是 OpenAI 开源的通用语音识别模型，采用经典的 **Encoder-Decoder Transformer** 架构：

```
输入音频 ──► 对数梅尔频谱图 ──► Encoder ──► Decoder ──► 文本输出
  (WAV)      (80维 x 3000帧)    (多模态)    (自回归)    (多语言)
```

**关键设计**：
- **输入**：音频被转换为 80 维对数梅尔频谱图（log-mel spectrogram），每 10ms 提取一帧
- **Encoder**：处理频谱图，提取音频特征表示
- **Decoder**：自回归生成文本，输出包含特殊标记（如 `<|zh|>` 语言标记、`<|transcribe|>` 任务标记）
- **多任务训练**：Whisper 在 68 万小时多语言多任务监督数据上训练，同时支持语音识别、语言识别、翻译等任务

### 模型大小对比

| 模型 | 参数量 | 显存需求 | 相对速度 | 中文效果 |
|------|--------|----------|----------|----------|
| tiny | 39M | ~1 GB | 最快 | 基本可用 |
| base | 74M | ~1 GB | 快 | 一般 |
| small | 244M | ~2 GB | 中等 | 较好 |
| medium | 769M | ~5 GB | 慢 | 好 |
| large-v3 | 1550M | ~10 GB | 最慢 | 最好 |

**选择建议**：
- **开发调试**：用 `tiny`（加载快，够用）
- **中文识别**：至少 `small`（tiny 中文效果一般）
- **生产环境**：`medium` 或 `large-v3`（准确率优先）

---

## 🧭 实现步骤（分步详解）

### 步骤 1：安装依赖

```bash
# Python 依赖
pip install openai-whisper

# 系统依赖（Windows）
# 下载 ffmpeg: https://www.gyan.dev/ffmpeg/builds/
# 将 ffmpeg.exe 所在目录添加到系统 PATH
```

**为什么需要 ffmpeg？**
- Whisper 内部使用 `ffmpeg` 解码各种音频格式（MP3、M4A 等）
- 如果只处理 WAV 文件，理论上不需要 ffmpeg
- 但推荐安装，因为 WAV 文件过大，实际使用中 MP3 更常见

### 步骤 2：配置环境变量

通过 `WHISPER_MODEL` 环境变量控制模型大小：

```bash
# Windows PowerShell
$env:WHISPER_MODEL = "tiny"    # 默认使用 tiny（最快）
$env:WHISPER_MODEL = "small"   # 切换为 small（中文更好）

# 或写入 .env 文件
WHISPER_MODEL=tiny
```

### 步骤 3：实现懒加载模型

大模型加载耗时较长（small 约 10-30 秒），不应在每次请求时重新加载：

```python
_whisper_model = None  # 全局变量，保存模型实例

def _get_whisper_model():
    """懒加载 Whisper 模型（全局单例，避免重复加载）"""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model(WHISPER_MODEL_NAME, device="cpu")
    return _whisper_model
```

**设计要点**：
- **懒加载**：首次调用时才加载，节省启动时间
- **全局单例**：所有请求共享同一个模型实例，避免内存浪费
- **CPU 模式**：`device="cpu"` 确保在无 GPU 的机器上也能运行
- 模型加载后常驻内存，后续请求只需推理，无需等待加载

### 步骤 4：构建 Flask API 端点

API 端点需要处理以下流程：

```python
@app.route("/api/speech", methods=["POST", "OPTIONS"])
def api_speech():
    # 1. 处理 CORS 预检请求
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    # 2. 验证文件上传
    if "audio" not in request.files:
        return jsonify({"error": "缺少 audio 文件字段"}), 400

    audio_file = request.files["audio"]

    # 3. 检查文件扩展名
    if not _allowed_audio_file(audio_file.filename):
        return jsonify({"error": "不支持的音频格式"}), 400

    # 4. 保存为临时文件
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            audio_file.save(tmp.name)
            tmp_path = tmp.name

        # 5. 调用 Whisper 转写
        model = _get_whisper_model()
        result = model.transcribe(tmp_path)

        # 6. 返回 JSON 结果
        return jsonify({
            "text": result.get("text", "").strip(),
            "language": result.get("language", "zh")
        })

    finally:
        # 7. 清理临时文件
        if tmp_path and Path(tmp_path).exists():
            os.unlink(tmp_path)
```

### 步骤 5：错误处理设计

| 错误场景 | HTTP 状态码 | 处理方式 |
|----------|-------------|----------|
| 缺少 file 字段 | 400 | 返回明确的中文错误提示 |
| 文件名为空 | 400 | 检查 `filename` 是否为空字符串 |
| 不支持的文件格式 | 400 | 列出支持的扩展名列表 |
| 模型未安装 | 500 | 捕获 `ModuleNotFoundError`，提示安装命令 |
| 转写失败 | 500 | 捕获通用异常，返回错误详情 |
| 临时文件清理失败 | 静默处理 | `finally` 块中 `try/except OSError` |

---

## 💻 关键代码（带注释）

### 完整 API 实现

```python
# ========== 配置区 ==========
WHISPER_MODEL_NAME = os.environ.get("WHISPER_MODEL", "tiny")
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}
_whisper_model = None  # 全局模型缓存


# ========== 模型管理 ==========
def _get_whisper_model():
    """懒加载 Whisper 模型（全局单例）"""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        print(f"[Whisper] 正在加载模型: {WHISPER_MODEL_NAME}（CPU模式）...")
        _whisper_model = whisper.load_model(WHISPER_MODEL_NAME, device="cpu")
        print(f"[Whisper] 模型 {WHISPER_MODEL_NAME} 加载完成")
    return _whisper_model


def _allowed_audio_file(filename):
    """检查音频文件扩展名是否在白名单中"""
    return Path(filename).suffix.lower() in ALLOWED_AUDIO_EXTENSIONS


# ========== API 端点 ==========
@app.route("/api/speech", methods=["POST", "OPTIONS"])
def api_speech():
    """语音识别端点：上传音频文件，返回识别文本"""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    # 验证：检查文件字段是否存在
    if "audio" not in request.files:
        return jsonify({"error": "缺少 audio 文件字段"}), 400

    audio_file = request.files["audio"]

    # 验证：检查文件名是否为空
    if audio_file.filename is None or audio_file.filename.strip() == "":
        return jsonify({"error": "上传的文件名为空"}), 400

    # 验证：检查文件格式是否支持
    if not _allowed_audio_file(audio_file.filename):
        ext = Path(audio_file.filename).suffix.lower()
        allowed = ", ".join(sorted(ALLOWED_AUDIO_EXTENSIONS))
        return jsonify({"error": f"不支持的音频格式: {ext}，支持: {allowed}"}), 400

    tmp_path = None
    try:
        # 保存上传的音频到临时文件
        suffix = Path(audio_file.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            audio_file.save(tmp.name)
            tmp_path = tmp.name

        # 加载模型并转写
        model = _get_whisper_model()
        result = model.transcribe(tmp_path)

        # 提取识别结果
        detected_lang = result.get("language", "zh")
        text = result.get("text", "").strip()

        return jsonify({
            "text": text,
            "language": detected_lang
        })

    except ModuleNotFoundError:
        return jsonify({"error": "请安装 openai-whisper 依赖"}), 500
    except Exception as e:
        return jsonify({"error": f"语音识别失败: {str(e)}"}), 500
    finally:
        # 清理临时文件（确保无论如何都会执行）
        if tmp_path and Path(tmp_path).exists():
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
```

### 调用示例

```bash
# 使用 curl 测试 API
curl -X POST http://localhost:18080/api/speech \
  -F "audio=@sample.wav"

# 返回示例
{
  "text": "你好，这是语音识别测试",
  "language": "zh"
}
```

```python
# 使用 Python requests 测试
import requests

with open("sample.wav", "rb") as f:
    response = requests.post(
        "http://localhost:18080/api/speech",
        files={"audio": ("sample.wav", f, "audio/wav")}
    )
print(response.json())
# {'text': '你好，这是语音识别测试', 'language': 'zh'}
```

---

## 🎓 学习要点（核心知识点）

### 1. Whisper 模型选择策略

| 场景 | 推荐模型 | 理由 |
|------|----------|------|
| 快速原型验证 | `tiny` | 加载快（<5秒），占用内存小 |
| 中文语音识别 | `small` 或以上 | tiny 中文效果不够理想 |
| 多语言混合 | `medium` | 语言识别更准确 |
| 高精度要求 | `large-v3` | 最佳准确率，但需要 GPU |
| 嵌入式设备 | `tiny` | 唯一能在树莓派等设备上运行 |

**关键代码**：
```python
model = whisper.load_model("tiny", device="cpu")
#  参数1: 模型名称（tiny/base/small/medium/large-v3）
#  参数2: device="cpu" 强制 CPU 运行（无需 GPU）
```

### 2. 音频格式处理

Whisper 内部使用 `ffmpeg` 处理音频解码，支持多种格式：

| 格式 | 扩展名 | 特点 |
|------|--------|------|
| WAV | `.wav` | 无损、文件大（~10MB/分钟），直接可用 |
| MP3 | `.mp3` | 有损压缩、文件小（~1MB/分钟），需 ffmpeg |
| M4A | `.m4a` | AAC 编码，苹果设备常用 |
| OGG | `.ogg` | 开源格式，音质好 |
| FLAC | `.flac` | 无损压缩，文件比 WAV 小 |

**安全考虑**：使用白名单模式限制允许的扩展名，防止上传恶意文件。

### 3. Flask 文件上传处理

Flask 处理文件上传的核心概念：

```python
# request.files: 类似字典，键为表单字段名，值为 FileStorage 对象
audio_file = request.files["audio"]

# FileStorage 常用属性/方法
audio_file.filename   # 原始文件名
audio_file.save(path) # 保存到指定路径
audio_file.read()     # 读取文件内容（字节流）
```

**multipart/form-data**：文件上传必须使用此编码方式，不能使用 JSON。

### 4. 临时文件管理

```python
import tempfile

# NamedTemporaryFile: 创建有名称的临时文件
# delete=False: 关闭后不自动删除（我们需要手动管理生命周期）
# suffix=".wav": 保留原始扩展名（Whisper 用它判断格式）
with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
    audio_file.save(tmp.name)
    tmp_path = tmp.name  # 保存路径，在 with 块外使用

# 使用完毕后手动清理
os.unlink(tmp_path)  # 删除临时文件
```

**为什么 `delete=False`？**
- 默认 `delete=True` 会在 `with` 块结束时自动删除文件
- 但我们需要在 `with` 块外调用 `model.transcribe(tmp_path)` 读取文件
- 所以设置 `delete=False`，手动在 `finally` 块中清理

### 5. 懒加载模式（Lazy Loading）

```python
_whisper_model = None  # 全局变量

def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model("tiny")
    return _whisper_model
```

**优势**：
- **首次请求**：加载模型（耗时），缓存实例
- **后续请求**：直接返回缓存实例，几乎零延迟
- **内存效率**：只有一个模型实例，所有请求共享

---

## ❓ 常见问题（FAQ）

### Q1: 运行时报错 `FileNotFoundError: ffmpeg`，怎么办？

**A**: Whisper 依赖 `ffmpeg` 解码音频。Windows 上安装步骤：
1. 前往 https://www.gyan.dev/ffmpeg/builds/ 下载 `ffmpeg-release-full.7z`
2. 解压到 `C:\ffmpeg\`
3. 将 `C:\ffmpeg\bin\` 添加到系统 PATH 环境变量
4. 重新打开终端，运行 `ffmpeg -version` 验证安装

如果只需要处理 WAV 格式，可以跳过，但推荐安装。

### Q2: tiny 模型中文识别效果很差，有哪些改进方法？

**A**: 几种改进思路：
1. **升级模型**：使用 `small` 或 `medium`（最直接的方法）
2. **指定语言**：`model.transcribe(audio, language="zh")` 强制中文模式，提高准确率
3. **音频预处理**：降噪、提高音量、去除静音段
4. **提示词引导**：`model.transcribe(audio, initial_prompt="这是一个中文对话")` 提供上下文

### Q3: 模型加载太慢，首次请求要等 30 秒，怎么办？

**A**: 几种优化策略：
1. **启动时预热**：在 `__main__` 中调用 `_get_whisper_model()` 提前加载
2. **使用 tiny 模型**：加载时间从 30 秒降到 5 秒
3. **量化模型**：使用 `whisper.cpp` 替代 Python 版（速度提升 4-5 倍）
4. **接受现状**：这是正常的首次加载耗时，后续请求几乎无延迟

```python
# 启动时预加载（可选）
if __name__ == "__main__":
    _get_whisper_model()  # 提前加载，避免首次请求等待
    app.run(...)
```

### Q4: 如何同时处理多个并发语音识别请求？

**A**: 当前实现使用全局单例模型，所有请求共享同一个模型实例。Whisper 的 `transcribe` 方法**不是线程安全的**，并发调用可能导致错误。

**解决方案**：
1. **串行处理**：使用 `threading.Lock` 确保同一时间只有一个请求在转写
2. **请求队列**：将请求放入队列，后台线程逐个处理
3. **多实例**：启动多个进程，每个进程一个模型实例（需要更多内存）

对于学习项目，当前实现足够。生产环境建议使用 Celery + Redis 任务队列。

### Q5: 如何限制上传文件大小，防止上传超大文件？

**A**: Flask 默认无文件大小限制。可以通过配置限制：

```python
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 限制 25MB
```

超过限制时 Flask 会返回 413 状态码。建议根据预期音频时长设置合理上限（1 分钟 WAV 约 1.9MB，16kHz 单声道 16bit；44.1kHz 立体声约 10MB）。

### Q6: 返回的 language 字段是什么格式？

**A**: Whisper 返回的语言代码遵循 ISO 639-1 标准：
- `zh`：中文
- `en`：英语
- `ja`：日语
- `ko`：韩语
- `fr`：法语
- `de`：德语

可以通过 `whisper.tokenizer.LANGUAGES` 查看完整支持列表（99 种语言）。

---

## 🔗 相关资源链接

| 资源 | 说明 |
|------|------|
| [OpenAI Whisper GitHub](https://github.com/openai/whisper) | 官方仓库，模型下载与使用文档 |
| [Whisper 论文](https://arxiv.org/abs/2212.04356) | Robust Speech Recognition via Large-Scale Weak Supervision |
| [openai-whisper PyPI](https://pypi.org/project/openai-whisper/) | Python 包页面 |
| [whisper.cpp](https://github.com/ggerganov/whisper.cpp) | C++ 高性能推理（4-5 倍加速） |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | CTranslate2 加速版（4 倍加速，2 倍内存节省） |
| [ffmpeg 官方下载](https://ffmpeg.org/download.html) | 音频解码必备工具 |
| [Flask 文件上传文档](https://flask.palletsprojects.com/en/stable/patterns/fileuploads/) | Flask 官方文件上传指南 |
| [Python tempfile 文档](https://docs.python.org/3/library/tempfile.html) | 临时文件管理 |
| LumiLearn archive/debug_scripts/lumiterm_local_server.py | 本模块实现代码（历史归档） |

---

## 📝 总结

Whisper 语音识别集成是 LumiLearn 多模态能力的重要一步。通过实现这个模块，我们学习了：

1. **Whisper 模型原理** — 理解 Transformer 编码器-解码器架构在语音识别中的应用
2. **模型部署** — 使用 `openai-whisper` 在 CPU 上本地运行语音识别模型
3. **Flask 文件上传** — 处理 multipart/form-data 请求，安全保存和清理临时文件
4. **懒加载模式** — 全局单例 + 延迟加载，优化大型模型的内存和启动时间
5. **错误处理设计** — 分层验证（文件存在 → 格式检查 → 处理异常 → 资源清理）

> **核心理念**：先用最简单的方案（tiny + CPU）跑通流程，再根据实际需求迭代优化。过早优化是万恶之源。

---

## 🔜 下一步

- **Module 4.2**：语音合成（TTS）集成 — 使用 Edge-TTS 或 Coqui TTS 实现文本转语音
- **Module 4.3**：多模态对话 — 将语音识别与 LLM 对话结合，实现语音交互循环