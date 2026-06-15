# Module 5.2 · 文件上传 API

> 在 LumiTerminal 中添加图片 OCR 识别前端功能，实现浏览器端图片选择/拖拽与后端 OCR 通信。

---

## 学习目标

- 掌握 `FileReader` API 读取本地图片文件
- 理解 `FormData` 在图片上传中的作用（与音频上传共享模式）
- 实现拖拽上传（Drag & Drop API）
- 建立 OCR 前端状态管理（待机/加载中/成功/失败）

---

## 实现步骤

### 1. 文件选择与读取

通过隐藏的 `<input type="file">` 触发文件选择对话框，使用 `FileReader` 读取图片并进行预览：

```
用户点击 OCR 按钮
    → element.click() 打开文件对话框
    → onchange 触发 handleOCRFile()
    → 验证文件类型（image/*）和大小（<10MB）
    → FileReader.readAsDataURL() 生成预览缩略图
    → 调用 sendImageToOCR() 上传识别
```

**关键代码流程：**

```javascript
// 1. 触发隐藏的文件输入
function triggerOCR() {
  document.getElementById('ocrFileInput').click();
}

// 2. 处理选择的文件
function handleOCRFile(event) {
  var file = event.target.files[0];
  if (!file) return;

  // 3. 验证文件类型
  if (!file.type.startsWith('image/')) {
    alert('请选择图片文件');
    return;
  }

  // 4. 验证文件大小（10MB 限制）
  var maxSize = 10 * 1024 * 1024;
  if (file.size > maxSize) {
    alert('图片文件不能超过 10MB');
    return;
  }

  // 5. 读取文件为 Data URL 用于预览
  var reader = new FileReader();
  reader.onload = function(e) {
    var preview = document.getElementById('ocrPreview');
    preview.style.display = 'block';
    preview.innerHTML = '<img src="' + e.target.result + '" alt="OCR 预览">';
  };
  reader.readAsDataURL(file);

  // 6. 发送到后端识别
  sendImageToOCR(file);
}
```

### 2. 前后端通信

前端使用 `FormData` 封装图片文件，通过 `fetch` POST 到 `/api/ocr`：

```javascript
function sendImageToOCR(imageFile) {
  var btnOcr = document.getElementById('btnOcr');
  btnOcr.classList.add('loading');  // 绿色旋转动画
  btnOcr.disabled = true;

  var formData = new FormData();
  formData.append('image', imageFile);
  //     字段名 ↑       ↑ File 对象（浏览器自动填充文件名和类型）

  fetch('/api/ocr', {
    method: 'POST',
    body: formData   // Content-Type: multipart/form-data 自动设置
  })
  .then(function(resp) {
    if (!resp.ok) {
      return resp.json().then(function(errData) {
        throw new Error(errData.error || 'HTTP ' + resp.status);
      });
    }
    return resp.json();
  })
  .then(function(data) {
    inputBox.value = data.text || '';     // OCR 结果填入输入框
    inputBox.dispatchEvent(new Event('input')); // 触发自适应高度
    btnOcr.classList.remove('loading');
    btnOcr.disabled = false;
  });
}
```

| 概念 | 说明 |
|------|------|
| `event.target.files[0]` | 用户选择的第一个文件（File 对象） |
| `FileReader` | 异步读取文件内容，支持 Data URL / ArrayBuffer / Text |
| `readAsDataURL()` | 将文件读为 Base64 Data URL（可直接用作 `<img src>`） |
| `FormData.append('image', file)` | 添加文件字段，浏览器自动设置 filename 和 Content-Type |

### 3. 拖拽上传

为 `.input-bar` 区域添加拖拽事件监听，实现拖拽图片到输入区域触发 OCR：

```javascript
inputBar.addEventListener('dragover', function(e) {
  e.preventDefault();
  e.stopPropagation();  // 阻止浏览器默认行为（打开文件）
});

inputBar.addEventListener('drop', function(e) {
  e.preventDefault();
  e.stopPropagation();

  var files = e.dataTransfer.files;
  if (files.length === 0) return;

  var file = files[0];
  // 与 handleOCRFile 相同的验证和预览逻辑
  // 最终调用 sendImageToOCR(file)
});
```

| 事件 | 说明 |
|------|------|
| `dragover` | 拖拽文件悬停在目标区域时持续触发，必须 `preventDefault()` 才能允许 drop |
| `drop` | 松开鼠标释放文件时触发，`e.dataTransfer.files` 获取文件列表 |

### 4. 快捷键支持

在 `handleKey` 函数中添加 `Ctrl+O` 快捷键触发 OCR：

```javascript
if (e.key === 'o' && e.ctrlKey) {
  e.preventDefault();
  triggerOCR();
}
```

### 5. UI 状态管理

OCR 过程中的 UI 状态变化：

| 状态 | 按钮样式 | 按钮状态 | placeholder | 预览区域 |
|------|----------|----------|-------------|----------|
| 待机 | `.btn-ocr`（绿色） | 可用 | `> 输入你的问题...` | 隐藏 |
| 识别中 | `.btn-ocr.loading`（旋转动画） | 禁用 | `🔍 图片识别中...` | 显示缩略图 |
| 成功 | `.btn-ocr`（绿色） | 可用 | `> 输入你的问题...` | 显示缩略图 |
| 失败 | `.btn-ocr`（绿色） | 可用 | `❌ OCR 识别失败: ...`（3秒后恢复） | 显示缩略图 |

---

## 学习要点

### FileReader API
- `new FileReader()` 创建异步文件读取器
- `readAsDataURL(file)` 读取为 Base64 Data URL
- `reader.onload` 回调获取读取结果 `reader.result`
- Data URL 格式：`data:image/png;base64,iVBORw0KGgo...`

### FormData（与音频上传对比）

| 对比项 | OCR 图片上传 | 语音上传 |
|--------|-------------|----------|
| 表单字段名 | `image` | `audio` |
| 文件类型 | `image/png`, `image/jpeg` 等 | `audio/webm` |
| 后端端点 | `/api/ocr` | `/api/speech` |
| 返回数据 | `{ text, confidence, details }` | `{ text }` |

> 图片上传与音频上传共享相同的 `FormData + fetch` 模式，体现了代码复用和一致性设计。

### Drag & Drop API
- `dragover` 事件必须 `preventDefault()` 才能接受 drop
- `drop` 事件通过 `e.dataTransfer.files` 获取文件
- `stopPropagation()` 防止事件冒泡干扰其他处理
- 拖拽和点击选择复用相同的验证和上传逻辑

### CSS 动画
- `@keyframes ocrSpin` 定义旋转动画（0° → 360°）
- `.loading` 类名触发 `animation: ocrSpin 1s linear infinite`
- 禁用时 `animation: none` 清除动画

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 文件选择后无反应 | `onchange` 事件未绑定或 `e.target.files` 为空 | 检查 `<input>` 的 `onchange` 属性和 `accept="image/*"` |
| 拖拽无响应 | `dragover` 未调用 `preventDefault()` | 必须在 `dragover` 中阻止默认行为 |
| 预览不显示 | Data URL 读取未完成或 DOM 元素不存在 | 确保 `reader.onload` 回调中正确设置 `innerHTML` |
| 上传 413 (Payload Too Large) | 文件超过服务器限制 | 前端 10MB 限制 + 后端 Nginx/Flask 配置 |
| 图片识别为空 | OCR 引擎未找到文字 | 检查图片是否包含清晰文字，确保 PaddleOCR 已初始化 |
| 快捷键冲突 | Ctrl+O 与浏览器"打开文件"快捷键冲突 | `preventDefault()` 阻止浏览器默认行为 |

---

## 相关资源链接

- [MDN: FileReader API](https://developer.mozilla.org/zh-CN/docs/Web/API/FileReader)
- [MDN: FormData](https://developer.mozilla.org/zh-CN/docs/Web/API/FormData)
- [MDN: Drag and Drop API](https://developer.mozilla.org/zh-CN/docs/Web/API/HTML_Drag_and_Drop_API)
- [MDN: input type="file"](https://developer.mozilla.org/zh-CN/docs/Web/HTML/Element/input/file)
- [CSS Animation 规范](https://www.w3.org/TR/css-animations-1/)