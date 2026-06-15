# Module 4.2 — PaddleOCR 文字识别入门

**日期**: 2026-06-01
**状态**: ✅ 完成
**相关模块**: Module 4.1（Whisper 语音识别）、Module 4（多模态能力）
**难度**: ⭐⭐⭐☆☆

---

## 📚 学习目标

完成本模块后，你将能够：

1. 理解 OCR（光学字符识别）的基本原理：文本检测 + 文本识别两阶段流水线
2. 使用 PaddleOCR 在本地 CPU 上运行文字识别模型（无需 GPU）
3. 掌握 PaddleOCR 的模型配置：语言选择（lang）、角度分类（use_angle_cls）、GPU/CPU 切换
4. 使用 Flask 构建图片上传 API 端点，处理 multipart/form-data 请求
5. 理解 PaddleOCR 返回结果的格式：检测框坐标 + 文本 + 置信度
6. 掌握图片格式处理（PNG/JPG/JPEG/WEBP）及临时文件管理

---

## 🧠 OCR 原理简介

### 传统 OCR vs 深度学习 OCR

OCR 技术经历了从传统方法到深度学习的演进：

```
传统 OCR 流程：
图片 ──► 二值化 ──► 连通域分析 ──► 字符分割 ──► 模板匹配 ──► 文本
         (阈值)     (找字符区域)     (切分单字)    (比对字符库)

深度学习 OCR 流程（PaddleOCR）：
图片 ──► 文本检测网络 ──► 文本识别网络 ──► 后处理 ──► 文本
         (DB/EAST)        (CRNN/SVTR)     (CTC解码)
```

**关键区别**：
- 传统方法对图片质量敏感（光照、倾斜、字体），需要大量预处理
- 深度学习方法端到端训练，对噪声、倾斜、变形有更好的鲁棒性

### PaddleOCR 架构概览

PaddleOCR 采用经典的 **检测 + 识别** 两阶段架构：

```
┌─────────────────────────────────────────────────────┐
│                    PaddleOCR 流水线                    │
├──────────┬──────────┬──────────┬─────────────────────┤
│  输入图片  │  文本检测  │  文本识别  │       输出          │
│  (PNG/JPG) │  (DB)    │  (CRNN)  │  [{text, box, conf}]  │
│           │  定位文字  │  识别内容  │                      │
│           │  区域坐标  │  置信度   │                      │
└──────────┴──────────┴──────────┴─────────────────────┘
```

**三大核心组件**：

| 组件 | 模型 | 功能 | 说明 |
|------|------|------|------|
| 文本检测 | DB（Differentiable Binarization） | 定位图片中所有文字区域 | 输出每个文字区域的四点坐标框 |
| 方向分类 | 轻量分类网络 | 检测文字方向并旋转矫正 | `use_angle_cls=True` 启用 |
| 文本识别 | CRNN / SVTR | 识别每个文字区域的内容 | 输出文本字符串和置信度 |

### 模型大小与性能

| 模型配置 | 检测模型 | 识别模型 | 体积 | 速度 | 中文效果 |
|----------|----------|----------|------|------|----------|
| 默认（PP-OCRv5） | PP-OCRV5_det | PP-OCRV5_rec | ~15MB | 快 | 优秀 |
| 移动端 | PP-OCRv5_mobile | PP-OCRv5_mobile | ~5MB | 极快 | 良好 |
| 服务器端 | PP-OCRv5_server | PP-OCRv5_server | ~50MB | 中等 | 最佳 |

---

## 🧭 实现步骤（分步详解）

### 步骤 1：安装依赖

```bash
# PaddlePaddle（CPU 版本，适合无 GPU 的机器）
pip install paddlepaddle

# PaddleOCR（文字识别核心库）
pip install paddleocr
```

**安装注意事项**：
- PaddlePaddle 提供 CPU 和 GPU 版本，默认 `pip install paddlepaddle` 安装 CPU 版
- 如果有 NVIDIA GPU，可安装 GPU 版：`pip install paddlepaddle-gpu`
- 首次运行时 PaddleOCR 会自动下载模型文件（约 15MB），需联网

### 步骤 2：配置环境变量

通过 `PADDLEOCR_LANG` 环境变量控制识别语言：

```bash
# Windows PowerShell
$env:PADDLEOCR_LANG = "ch"          # 默认中文（中英文混合识别）
$env:PADDLEOCR_LANG = "en"          # 纯英文
$env:PADDLEOCR_LANG = "chinese_cht" # 繁体中文

# 或写入 .env 文件
PADDLEOCR_LANG=ch
```

**支持的语言列表**：
- `ch`：中文 + 英文（最常用）
- `en`：纯英文
- `chinese_cht`：繁体中文
- `fr`、`german`、`japan`、`korean` 等更多语言

### 步骤 3：实现懒加载模型

与 Whisper 模块一样，使用全局单例 + 懒加载模式：

```python
_paddleocr_ocr = None  # 全局变量，保存 PaddleOCR 实例

def _get_paddleocr():
    """懒加载 PaddleOCR 模型（全局单例，避免重复加载）"""
    global _paddleocr_ocr
    if _paddleocr_ocr is None:
        from paddleocr import PaddleOCR
        _paddleocr_ocr = PaddleOCR(
            use_angle_cls=True,   # 启用文字方向分类（自动矫正旋转）
            lang=PADDLEOCR_LANG,  # 语言配置
            use_gpu=False,        # CPU 模式
            show_log=False        # 关闭调试日志
        )
    return _paddleocr_ocr
```

**参数说明**：
- `use_angle_cls=True`：启用方向分类器，自动检测并矫正旋转文字（竖排文字也能识别）
- `lang`：语言，默认 `ch`（中文 + 英文）
- `use_gpu=False`：强制 CPU 模式，确保在无 GPU 机器上运行
- `show_log=False`：关闭模型加载时的冗余日志

### 步骤 4：构建 Flask API 端点

```python
@app.route("/api/ocr", methods=["POST", "OPTIONS"])
def api_ocr():
    """文字识别（OCR）端点：上传图片文件，返回识别文本"""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    # 1. 验证文件上传
    if "image" not in request.files:
        return jsonify({"error": "缺少 image 文件字段"}), 400

    image_file = request.files["image"]

    # 2. 检查文件名和格式
    if image_file.filename is None or image_file.filename.strip() == "":
        return jsonify({"error": "上传的文件名为空"}), 400

    if not _allowed_image_file(image_file.filename):
        return jsonify({"error": "不支持的图片格式"}), 400

    tmp_path = None
    try:
        # 3. 保存上传的图片到临时文件
        suffix = Path(image_file.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            image_file.save(tmp.name)
            tmp_path = tmp.name

        # 4. 调用 PaddleOCR 识别
        ocr = _get_paddleocr()
        raw_result = ocr.ocr(tmp_path, cls=True)

        # 5. 解析并构建返回结果
        all_text_parts = []
        details = []
        overall_confidences = []

        if raw_result and raw_result[0]:
            for detection in raw_result[0]:
                box = detection[0]         # 四点坐标 [[x1,y1],...]
                text_info = detection[1]   # (文本, 置信度)
                text = text_info[0]
                confidence = float(text_info[1])

                all_text_parts.append(text)
                overall_confidences.append(confidence)
                details.append({
                    "text": text,
                    "confidence": round(confidence, 4),
                    "box": [[int(p[0]), int(p[1])] for p in box]
                })

        full_text = "".join(all_text_parts)
        avg_confidence = round(
            sum(overall_confidences) / len(overall_confidences), 4
        ) if overall_confidences else 0.0

        return jsonify({
            "text": full_text,
            "confidence": avg_confidence,
            "details": details
        })

    except ModuleNotFoundError:
        return jsonify({"error": "请安装 PaddleOCR 依赖"}), 500
    except Exception as e:
        return jsonify({"error": f"文字识别失败: {str(e)}"}), 500
    finally:
        # 6. 清理临时文件
        if tmp_path and Path(tmp_path).exists():
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
```

### 步骤 5：错误处理设计

| 错误场景 | HTTP 状态码 | 处理方式 |
|----------|-------------|----------|
| 缺少 file 字段 | 400 | 返回明确的中文错误提示 |
| 文件名为空 | 400 | 检查 `filename` 是否为空字符串 |
| 不支持的文件格式 | 400 | 列出支持的扩展名列表 |
| 模型未安装 | 500 | 捕获 `ModuleNotFoundError`，提示安装命令 |
| 识别失败 | 500 | 捕获通用异常，返回错误详情 |
| 无文字内容 | 200 | 返回空文本和详情，`confidence=0.0` |
| 临时文件清理失败 | 静默处理 | `finally` 块中 `try/except OSError` |

---

## 💻 关键代码（带注释）

### 完整 API 实现

```python
# ========== 配置区 ==========
PADDLEOCR_LANG = os.environ.get("PADDLEOCR_LANG", "ch")
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
_paddleocr_ocr = None  # 全局模型缓存


# ========== 模型管理 ==========
def _get_paddleocr():
    """懒加载 PaddleOCR 模型（全局单例）"""
    global _paddleocr_ocr
    if _paddleocr_ocr is None:
        from paddleocr import PaddleOCR
        print(f"[PaddleOCR] 正在加载模型: lang={PADDLEOCR_LANG}（CPU模式）...")
        _paddleocr_ocr = PaddleOCR(
            use_angle_cls=True,   # 启用方向分类，自动矫正旋转文字
            lang=PADDLEOCR_LANG,  # 语言配置（ch/en/chinese_cht 等）
            use_gpu=False,        # CPU 模式，无需 GPU
            show_log=False        # 关闭调试日志，保持输出整洁
        )
        print(f"[PaddleOCR] 模型 lang={PADDLEOCR_LANG} 加载完成")
    return _paddleocr_ocr


def _allowed_image_file(filename):
    """检查图片文件扩展名是否在白名单中"""
    return Path(filename).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS


# ========== API 端点 ==========
@app.route("/api/ocr", methods=["POST", "OPTIONS"])
def api_ocr():
    """文字识别（OCR）端点：上传图片文件，返回识别文本"""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    # 验证：检查文件字段是否存在
    if "image" not in request.files:
        return jsonify({"error": "缺少 image 文件字段，请使用 multipart/form-data 上传"}), 400

    image_file = request.files["image"]

    # 验证：检查文件名是否为空
    if image_file.filename is None or image_file.filename.strip() == "":
        return jsonify({"error": "上传的文件名为空"}), 400

    # 验证：检查文件格式是否支持
    if not _allowed_image_file(image_file.filename):
        ext = Path(image_file.filename).suffix.lower()
        allowed = ", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))
        return jsonify({"error": f"不支持的图片格式: {ext}，支持: {allowed}"}), 400

    tmp_path = None
    try:
        # 保存上传的图片到临时文件
        suffix = Path(image_file.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            image_file.save(tmp.name)
            tmp_path = tmp.name

        # 加载模型并识别
        ocr = _get_paddleocr()
        raw_result = ocr.ocr(tmp_path, cls=True)

        # 解析识别结果，构建统一格式
        # raw_result 格式: [[detection1, detection2, ...]]
        # 每个 detection: [[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ('text', confidence)]
        all_text_parts = []
        details = []
        overall_confidences = []

        if raw_result and raw_result[0]:
            for detection in raw_result[0]:
                box = detection[0]         # 四点坐标
                text_info = detection[1]   # (文本, 置信度)
                text = text_info[0]
                confidence = float(text_info[1])

                all_text_parts.append(text)
                overall_confidences.append(confidence)
                details.append({
                    "text": text,
                    "confidence": round(confidence, 4),
                    "box": [[int(p[0]), int(p[1])] for p in box]
                })

        # 拼接所有文本片段
        full_text = "".join(all_text_parts) if all_text_parts else ""
        # 计算平均置信度
        avg_confidence = round(
            sum(overall_confidences) / len(overall_confidences), 4
        ) if overall_confidences else 0.0

        return jsonify({
            "text": full_text,
            "confidence": avg_confidence,
            "details": details
        })

    except ModuleNotFoundError:
        return jsonify({"error": "请安装 PaddleOCR 依赖: pip install paddleocr paddlepaddle"}), 500
    except Exception as e:
        return jsonify({"error": f"文字识别失败: {str(e)}"}), 500
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
curl -X POST http://localhost:18080/api/ocr \
  -F "image=@screenshot.png"

# 返回示例
{
  "text": "LumiTerminal 学习终端",
  "confidence": 0.9876,
  "details": [
    {
      "text": "LumiTerminal",
      "confidence": 0.9912,
      "box": [[10, 20], [200, 20], [200, 50], [10, 50]]
    },
    {
      "text": "学习终端",
      "confidence": 0.9841,
      "box": [[210, 20], [330, 20], [330, 50], [210, 50]]
    }
  ]
}
```

```python
# 使用 Python requests 测试
import requests

with open("screenshot.png", "rb") as f:
    response = requests.post(
        "http://localhost:18080/api/ocr",
        files={"image": ("screenshot.png", f, "image/png")}
    )
print(response.json())
# {'text': 'LumiTerminal 学习终端', 'confidence': 0.9876, 'details': [...]}
```

---

## 🎓 学习要点（核心知识点）

### 1. PaddleOCR 结果格式解析

PaddleOCR 的 `ocr.ocr()` 方法返回一个嵌套列表，理解其结构是正确使用的关键：

```python
raw_result = ocr.ocr("image.png", cls=True)

# 返回格式（多图片输入时为多个元素的列表）
# raw_result = [
#     [  # 第一张图片的检测结果
#         [[[10, 20], [200, 20], [200, 50], [10, 50]],  # 检测框（四点坐标）
#          ('文本内容', 0.9912)],                          # (文本, 置信度)
#         [[[10, 60], [150, 60], [150, 90], [10, 90]],
#          ('第二行文字', 0.9841)]
#     ]
# ]
```

**关键字段**：
- `box`：四点坐标 `[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]`，按顺时针顺序排列
- `text`：识别出的文本内容
- `confidence`：置信度，范围 0~1，越接近 1 越可信

### 2. 图片预处理最佳实践

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 倾斜文字识别差 | 文字方向不正 | 设置 `use_angle_cls=True` 自动矫正 |
| 小字识别率低 | 图片分辨率不足 | 提高图片 DPI（300+），或放大图片 |
| 模糊图片失败 | 对焦不清或手抖 | 提高图片质量，或使用图像增强预处理 |
| 多列文字错乱 | 检测框顺序问题 | 后处理时可对检测框按 y 坐标排序 |
| 白底黑字 vs 黑底白字 | 对比度反转 | PaddleOCR 对两种都支持良好 |

**推荐的图片参数**：
- 分辨率：至少 200 DPI（72 DPI 的网页截图可能不够清晰）
- 格式：PNG（无损）优先于 JPG（有损压缩）
- 大小：建议不超过 10MB（过大图片会拖慢推理速度）

### 3. 文本检测 vs 文本识别

理解两阶段模型的分工：

```python
# 阶段一：文本检测（DB 网络）
# 输入：整张图片
# 输出：每个文字区域的四点坐标框
检测结果 = [
    [[10, 20], [200, 20], [200, 50], [10, 50]],   # 区域 1
    [[10, 60], [150, 60], [150, 90], [10, 90]]    # 区域 2
]

# 阶段二：文本识别（CRNN 网络）
# 输入：裁剪后的文字区域图片
# 输出：文本字符串 + 置信度
识别结果 = ('文本内容', 0.9912)
```

**为什么分两阶段？**
- 检测和识别是两个不同的子任务，分开训练效果更好
- 检测网络关注"哪里有文字"（定位），识别网络关注"文字是什么"（分类）
- 可以独立替换检测或识别模型，灵活组合

### 4. 懒加载模式在 OCR 场景的优势

```python
_paddleocr_ocr = None  # 全局变量

def _get_paddleocr():
    global _paddleocr_ocr
    if _paddleocr_ocr is None:
        _paddleocr_ocr = PaddleOCR(...)
    return _paddleocr_ocr
```

**与 Whisper 懒加载的对比**：

| 特性 | Whisper (tiny) | PaddleOCR (默认) |
|------|---------------|-------------------|
| 首次加载时间 | ~5-10 秒 | ~3-5 秒 |
| 内存占用 | ~1 GB | ~300 MB |
| 单次推理时间 | 1-30 秒（取决于音频长度） | 0.5-3 秒（取决于图片大小） |
| 模型文件大小 | ~75 MB | ~15 MB（自动下载） |

### 5. 数学公式识别（LaTeX 输出）

PaddleOCR 本身不直接支持 LaTeX 数学公式识别。如果需要识别数学公式，有以下方案：

**方案一：使用专用公式识别模型**
```python
# LaTeX-OCR（基于 ViT + Transformer）
# pip install pix2tex
from pix2tex.cli import LatexOCR
model = LatexOCR()
latex = model("formula.png")  # 输出: '\\frac{x^2}{y^2}'
```

**方案二：PaddleOCR 识别 + 后处理**
```python
# 先识别公式区域文本，再转换
text = ocr.ocr("formula.png")
# 可能输出: "x2 / y2"，需要额外处理
```

**方案三：专用 OCR 引擎**
- Mathpix API（商业，效果好）
- Nougat（Meta，学术论文 OCR）
- Pix2Text（开源，中文 + 公式）

**当前实现**：本模块使用 PaddleOCR 完成基础文字识别，数学公式识别作为后续扩展方向。对于简单公式（如 `x² + y² = z²`），PaddleOCR 可以识别出 Unicode 字符版本。

---

## ❓ 常见问题（FAQ）

### Q1: 首次运行报错 `ModuleNotFoundError: No module named 'paddle'`，怎么办？

**A**: 这是因为 PaddlePaddle 未安装。安装步骤：

```bash
# CPU 版本（推荐，无需 GPU）
pip install paddlepaddle

# 如果上述命令失败，尝试从官网安装
# Windows CPU: https://www.paddlepaddle.org.cn/install/quick
pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple
```

注意：Windows 上需要安装 Microsoft Visual C++ Redistributable（VC 运行时）。

### Q2: 首次运行 PaddleOCR 时卡在下载模型，怎么办？

**A**: PaddleOCR 首次运行会自动从 GitHub 下载模型文件（约 15MB），如果网络不好可能失败。

**解决方法**：
1. **使用代理**：设置 `HTTP_PROXY` 和 `HTTPS_PROXY` 环境变量
2. **手动下载模型**：从 [PaddleOCR GitHub Releases](https://github.com/PaddlePaddle/PaddleOCR/releases) 下载模型文件，放到 `C:\Users\用户名\.paddleocr\whl\` 目录
3. **离线模式**：指定本地模型路径
   ```python
   ocr = PaddleOCR(det_model_dir='./models/det', rec_model_dir='./models/rec')
   ```

### Q3: 中文识别效果不好，特别是手写体，如何改进？

**A**: 几种改进方法：

1. **提高图片质量**：确保图片清晰、光线均匀、文字与背景对比度高
2. **预处理图片**：使用 OpenCV 进行降噪、锐化、对比度增强
   ```python
   import cv2
   img = cv2.imread("image.png")
   # 灰度化
   gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
   # 自适应阈值二值化
   binary = cv2.adaptiveThreshold(gray, 255,
       cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
   cv2.imwrite("enhanced.png", binary)
   ```
3. **使用服务器端模型**：通过 `rec_model_dir` 指定更大的识别模型
4. **现实限制**：PaddleOCR 对手写体中文的识别率有限（约 70-80%），印刷体效果好（95%+）。对于手写体，考虑使用 TrOCR 等专用模型

### Q4: 返回的 details 中 box 坐标是什么含义？如何用于图片标注？

**A**: `box` 包含四个点的坐标 `[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]`，按顺时针排列，起点为左上角：

```
(x1,y1) ──────── (x2,y2)
  │                │
  │   "文本内容"    │
  │                │
(x4,y4) ──────── (x3,y3)
```

**使用示例**：在图片上绘制检测框
```python
import cv2

img = cv2.imread("image.png")
for detail in result["details"]:
    box = detail["box"]
    # 绘制矩形框
    cv2.rectangle(img, (box[0][0], box[0][1]),
                       (box[2][0], box[2][1]), (0, 255, 0), 2)
    # 标注文本
    cv2.putText(img, detail["text"],
                (box[0][0], box[0][1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
cv2.imwrite("annotated.png", img)
```

### Q5: PaddleOCR 和 Tesseract 有什么区别？为什么选择 PaddleOCR？

**A**: 两者的核心对比：

| 特性 | PaddleOCR | Tesseract |
|------|-----------|-----------|
| 中文识别率 | 优秀（95%+ 印刷体） | 一般（需要额外语言包） |
| 安装难度 | 中等（需 PaddlePaddle） | 简单（系统级安装） |
| 模型体积 | ~15MB | ~50MB+（含语言包） |
| 速度 | 快（CPU 优化好） | 中等 |
| 手写体支持 | 有限 | 几乎不支持 |
| 竖排文字 | 支持（需方向分类） | 不支持 |
| API 设计 | Python 原生，易用 | 命令行为主，Python 封装弱 |
| 社区生态 | 百度维护，中文社区活跃 | Google 维护，国际社区 |

**选择建议**：如果主要处理中文印刷体文字，PaddleOCR 是更好的选择。如果处理英文文档或有特殊部署需求，Tesseract 更成熟。

### Q6: 如何同时处理多个图片的 OCR 请求？

**A**: 与 Whisper 类似，当前实现使用全局单例模型。PaddleOCR 的 `ocr` 方法**支持批量处理**：

```python
# 批量识别多张图片（一次调用，内部并行）
results = ocr.ocr(["img1.png", "img2.png", "img3.png"])
```

对于并发请求，建议：
1. **串行处理**：使用 `threading.Lock` 确保线程安全
2. **请求队列**：将请求放入队列，后台处理
3. **多实例**：多个 PaddleOCR 实例（需更多内存，约 300MB/实例）

对于学习项目，当前实现足够。生产环境建议使用 Celery + Redis 任务队列。

---

## 🔗 相关资源链接

| 资源 | 说明 |
|------|------|
| [PaddleOCR GitHub](https://github.com/PaddlePaddle/PaddleOCR) | 官方仓库，提供完整文档和模型下载 |
| [PaddleOCR 在线体验](https://www.paddlepaddle.org.cn/hub/scene/ocr) | 在线 Demo，无需安装即可体验 |
| [PaddlePaddle 安装指南](https://www.paddlepaddle.org.cn/install/quick) | 官方安装文档（CPU/GPU，Windows/Linux/Mac） |
| [PP-OCRv5 技术报告](https://arxiv.org/abs/2309.00000) | 最新模型架构详解 |
| [Pix2Text (P2T)](https://github.com/breezedeus/Pix2Text) | 开源数学公式 + 文字识别工具 |
| [LaTeX-OCR](https://github.com/lukas-blecher/LaTeX-OCR) | 基于 ViT 的公式转 LaTeX 工具 |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | Google 开源 OCR 引擎（对比参考） |
| [TrOCR](https://huggingface.co/microsoft/trocr-base-handwritten) | 微软手写体 OCR 模型 |
| [Flask 文件上传文档](https://flask.palletsprojects.com/en/stable/patterns/fileuploads/) | Flask 官方文件上传指南 |
| LumiLearn scripts/lumiterm_local_server.py | 本模块实现代码 |

---

## 📝 总结

通过本模块的学习，我们成功将 PaddleOCR 集成到 LumiTerminal 中，实现了文字识别能力。主要收获：

1. **OCR 两阶段架构** — 理解文本检测（DB）和文本识别（CRNN）的分工协作
2. **PaddleOCR 部署** — 使用 `paddleocr` 在 CPU 上本地运行文字识别，无需 GPU
3. **结果解析** — 理解检测框坐标、文本内容和置信度的数据结构
4. **Flask 图片上传** — 处理 multipart/form-data 请求，安全保存和清理临时文件
5. **懒加载模式** — 全局单例 + 延迟加载，与 Whisper 模块保持一致的设计模式

> **核心理念**：OCR 不是魔法——它是检测 + 识别两个深度学习模型的组合。理解这个流水线，你就能针对不同场景选择合适的模型和优化策略。

---

## 🔜 下一步

- **Module 4.3**：PDF 文档解析 — 使用 PyMuPDF 提取 PDF 中的文字和图片
- **Module 4.4**：图像理解（Vision）— 使用 CLIP 或 LLaVA 实现图片内容理解
- **Module 4.5**：多模态对话 — 将语音识别、OCR 与 LLM 对话结合，实现全模态交互