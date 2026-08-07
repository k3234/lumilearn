# Module 5.1 · 前端录音 API

> 在 LumiTerminal 中添加语音识别前端功能，实现浏览器端音频采集与后端通信。

---

## 学习目标

- 掌握 `navigator.mediaDevices.getUserMedia()` 获取麦克风权限
- 掌握 `MediaRecorder` API 进行浏览器端音频录制
- 理解 `Blob` 和 `FormData` 在前后端文件传输中的作用
- 实现完整的"前端录音 → 上传 → 后端识别 → 结果回填"闭环

---

## 实现步骤

### 1. MediaRecorder API 使用

MediaRecorder 是浏览器内置的音频/视频录制接口，核心流程如下：

```
getUserMedia({ audio: true })
    → 获取 MediaStream
    → 创建 MediaRecorder(stream, options)
    → 监听 ondataavailable 收集数据块
    → 监听 onstop 组装完整音频
    → 停止后释放轨道
```

**关键代码流程：**

```javascript
// 1. 请求麦克风权限，获取音频流
let stream = await navigator.mediaDevices.getUserMedia({ audio: true });

// 2. 检测浏览器支持的编码格式（优先 Opus 编码的 WebM）
let mimeType = '';
if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
  mimeType = 'audio/webm;codecs=opus';
} else if (MediaRecorder.isTypeSupported('audio/webm')) {
  mimeType = 'audio/webm';
}

// 3. 创建 MediaRecorder 实例
mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType: mimeType } : {});

// 4. 收集音频数据块（每当有数据可用时触发）
mediaRecorder.ondataavailable = function(e) {
  if (e.data.size > 0) {
    audioChunks.push(e.data); // e.data 是 Blob 对象
  }
};

// 5. 录制停止时组装并发送
mediaRecorder.onstop = function() {
  let audioBlob = new Blob(audioChunks, {
    type: mediaRecorder.mimeType || 'audio/webm'
  });
  stream.getTracks().forEach(function(track) { track.stop(); }); // 释放麦克风
  sendAudioToServer(audioBlob);
};

// 6. 开始录制
mediaRecorder.start();   // 浏览器开始采集音频
isRecording = true;
```

### 2. 音频格式处理

| 格式 | MIME Type | 说明 |
|------|-----------|------|
| WebM + Opus | `audio/webm;codecs=opus` | 首选，压缩率高，质量好 |
| WebM 默认 | `audio/webm` | 兜底方案，Chrome/Firefox/Edge 均支持 |
| WAV（不支持） | `audio/wav` | MediaRecorder 通常不直接支持 WAV |

> **注意：** `audioChunks` 中每个元素已经是 `Blob`，最终用 `new Blob(chunks, { type })` 合并即可，无需手动拼接 ArrayBuffer。

### 3. 前后端通信

前端使用 `FormData` 封装音频文件，通过 `fetch` POST 到 `/api/speech`：

```javascript
function sendAudioToServer(audioBlob) {
  let formData = new FormData();
  formData.append('audio', audioBlob, 'recording.webm');
  //     字段名 ↑       ↑ Blob 数据    ↑ 文件名（服务器端通过此名接收）

  fetch('/api/speech', {
    method: 'POST',
    body: formData   // 浏览器自动设置 Content-Type: multipart/form-data
  })
  .then(function(resp) {
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    return resp.json();
  })
  .then(function(data) {
    inputBox.value = data.text || '';     // 识别结果填入输入框
    inputBox.dispatchEvent(new Event('input')); // 触发 textarea 自适应高度
  });
}
```

| 概念 | 说明 |
|------|------|
| `Blob` | 二进制大对象，表示原始文件数据 |
| `FormData` | 模拟 HTML 表单，支持文件上传 |
| `multipart/form-data` | FormData 自动使用的 Content-Type |

### 4. 错误处理

常见错误场景及处理：

```javascript
// 1. 浏览器不支持 getUserMedia
if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
  alert('你的浏览器不支持录音功能');
}

// 2. 用户拒绝麦克风权限
catch (err) {
  if (err.name === 'NotAllowedError') {
    alert('麦克风权限被拒绝');
  }
}

// 3. 后端识别失败
.catch(function(err) {
  inputBox.placeholder = '❌ 识别失败: ' + err.message;
  setTimeout(function() { inputBox.placeholder = '> 输入你的问题...'; }, 3000);
});
```

### 5. UI 状态管理

录音过程中的 UI 状态变化：

| 状态 | 按钮样式 | 按钮文字 | placeholder |
|------|----------|----------|-------------|
| 待机 | `.btn-mic`（蓝色） | 🎤 | `> 输入你的问题...` |
| 录音中 | `.btn-mic.recording`（红色脉冲） | ⏹ | `🎙️ 正在录音...` |
| 识别中 | `.btn-mic`（蓝色） | 🎤 | `🔍 识别中...` |
| 失败 | `.btn-mic`（蓝色） | 🎤 | `❌ 识别失败: ...`（3秒后恢复） |

---

## 学习要点

### getUserMedia
- `navigator.mediaDevices.getUserMedia({ audio: true })` 请求麦克风
- 返回 Promise<MediaStream>，需要用户授权
- 仅在 HTTPS 或 localhost 下可用（安全上下文要求）
- 获取的 stream 用完必须 `track.stop()` 释放

### MediaRecorder
- 构造函数：`new MediaRecorder(stream, { mimeType })`
- `start()` 开始录制，`stop()` 停止录制
- `ondataavailable` 事件以 Blob 形式提供数据块
- `onstop` 事件在录制停止后触发，适合做数据组装
- `state` 属性：`'inactive'` / `'recording'` / `'paused'`

### Blob
- `new Blob([chunks], { type: 'audio/webm' })` 合并数据块
- `chunks` 可以是 ArrayBuffer、Blob、String 等
- 不可变对象，表示原始二进制数据

### FormData
- `formData.append(key, blob, filename)` 添加文件字段
- 传递给 `fetch` 的 `body`，自动设置 multipart 编码
- 后端通过 `request.files['audio']`（Flask）或 `req.file`（Express）接收

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `getUserMedia` 返回 `undefined` | 非安全上下文（HTTP 非 localhost） | 使用 HTTPS 或 localhost |
| `NotAllowedError` | 用户拒绝或系统禁止麦克风 | 引导用户在浏览器设置中允许 |
| `NotFoundError` | 没有检测到麦克风设备 | 检查硬件连接 |
| 录音文件为空 | `ondataavailable` 未触发或 `e.data.size === 0` | 确认已调用 `start()`；数据会在 `stop()` 时一次性提供，若需分块请用 `start(timeslice)` 设置定时触发间隔 |
| `MediaRecorder.isTypeSupported` 返回 false | 浏览器不支持该编码 | 降级到不指定 mimeType |
| 后端收到空文件 | Blob 类型不匹配 | 确保 `type` 参数与后端预期一致 |

---

## 相关资源链接

- [MDN: MediaDevices.getUserMedia()](https://developer.mozilla.org/zh-CN/docs/Web/API/MediaDevices/getUserMedia)
- [MDN: MediaRecorder API](https://developer.mozilla.org/zh-CN/docs/Web/API/MediaRecorder)
- [MDN: Blob](https://developer.mozilla.org/zh-CN/docs/Web/API/Blob)
- [MDN: FormData](https://developer.mozilla.org/zh-CN/docs/Web/API/FormData)
- [Web Audio API 规范](https://www.w3.org/TR/webaudio/)