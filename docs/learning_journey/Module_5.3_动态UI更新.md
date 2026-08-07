# Module 5.3 · 动态 UI 更新

> 在 LumiTerminal 中添加讲解质量自我审查前端功能，实现审查按钮、结果面板、DOM 动态插入等前端交互能力。

---

## 学习目标

- 掌握 DOM 动态插入（`insertBefore`）在聊天界面中的应用
- 理解前端状态管理：按钮状态（normal/disabled/loading）的完整生命周期
- 实现评分可视化：根据分数动态切换 CSS 类名控制颜色
- 建立 `fetch` POST JSON 的标准通信模式
- 学习从 DOM 中回溯查找特定元素（逆序遍历 `.message` 节点）

---

## 实现步骤

### 1. 审查按钮设计

在 `input-wrap` 中插入一个与 `.btn-send` 风格一致的审查按钮，使用 CSS 变量 `--accent-orange` 保持视觉统一：

```
用户点击 📋 按钮（或 Ctrl+R）
    → 逆序遍历 chatArea 找到最后一条 AI 消息
    → 提取 .msg-text 文本内容
    → POST JSON 到 /api/review
    → 接收结构化评分数据
    → 在聊天区域顶部动态插入审查面板
```

**关键 CSS 样式：**

```css
.btn-review {
  width: 44px; height: 44px;
  background: var(--accent-orange);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-review:hover { background: #c86641; transform: translateY(-1px); }
.btn-review:disabled { background: var(--border); cursor: not-allowed; }
```

按钮状态机：

| 状态 | 图标 | CSS 状态 | 说明 |
|------|------|----------|------|
| 就绪 | 📋 | 默认 | 等待用户触发审查 |
| 审查中 | ⏳ | `disabled` | 等待后端返回结果 |
| 完成/失败 | 📋 | 默认 | 恢复可点击状态 |

### 2. 查找最后一条 AI 消息

通过逆序遍历 `.message` 节点，找到最近的 AI 回复：

```javascript
function reviewLastContent() {
  var messages = chatArea.querySelectorAll('.message');
  var lastAIMessage = null;

  for (var i = messages.length - 1; i >= 0; i--) {
    var msg = messages[i];
    var avatar = msg.querySelector('.msg-avatar.model');
    if (avatar) {
      lastAIMessage = msg;
      break;
    }
  }

  if (!lastAIMessage) {
    alert('没有找到 AI 讲解内容，请先发送问题获取回复。');
    return;
  }

  var contentEl = lastAIMessage.querySelector('.msg-text');
  // ...发送到 /api/review
}
```

| 概念 | 说明 |
|------|------|
| `querySelectorAll('.message')` | 获取所有消息节点（Nodelist） |
| 逆序遍历 | 从最后一条开始找，效率更高 |
| `.msg-avatar.model` | 通过 avatar 的 CSS class 区分用户消息和 AI 消息 |
| 空值保护 | 没有 AI 消息时 `alert()` 提示用户先发送问题 |

### 3. 前后端 JSON 通信

前端使用 `fetch` POST JSON 到 `/api/review`：

```javascript
fetch('/api/review', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    content: contentEl.textContent.trim(),
    mode: 'quick'
  })
})
.then(function(resp) { return resp.json(); })
.then(function(data) {
  var latency = Math.round(performance.now() - t0);
  showReviewResult(data, latency);
  btnReview.disabled = false;
  btnReview.textContent = '📋';
})
.catch(function(err) {
  var panel = document.createElement('div');
  panel.className = 'review-panel';
  panel.innerHTML = '<div style="color:#f85149;">审查失败: ' + err.message + '</div>';
  chatArea.insertBefore(panel, chatArea.firstChild);
});
```

与已有通信模式对比：

| 功能 | 方法 | Content-Type | 端点 | 载荷格式 |
|------|------|-------------|------|----------|
| 聊天 | POST | `application/json` | `/api/chat` | `{model, messages, stream}` |
| 语音 | POST | `multipart/form-data` | `/api/speech` | FormData(音频) |
| OCR | POST | `multipart/form-data` | `/api/ocr` | FormData(图片) |
| 审查 | POST | `application/json` | `/api/review` | `{content, mode}` |

### 4. 评分可视化

根据分数动态分配 CSS 类名，实现颜色变化：

```javascript
function showReviewResult(data, latency) {
  var totalScore = data.overall || 0;  // 后端返回字段为 overall（见 Module 4.3 API）
  var scoreClass = totalScore >= 8 ? 'high' : (totalScore >= 5 ? 'medium' : 'low');

  // 总分显示
  panel.innerHTML += '<div class="review-score ' + scoreClass + '">' + totalScore.toFixed(1) + '</div>';

  // 各维度评分条
  var pct = Math.round((dScore / 10) * 100);
  dimHTML += '<div class="review-dim-bar">' +
    '<div class="review-dim-fill ' + dClass + '" style="width:' + pct + '%"></div>' +
    '</div>';
}
```

评分颜色规则：

| 分数范围 | CSS 类名 | 颜色 | 含义 |
|----------|----------|------|------|
| ≥ 8.0 | `.high` | 绿色 (`--accent-green`) | 优秀 |
| 5.0 ~ 7.9 | `.medium` | 橙色 (`--accent-orange`) | 一般 |
| < 5.0 | `.low` | 红色 (`#f85149`) | 需改进 |

评分条动画：CSS `transition: width 0.6s ease-out` 使评分条从 0 平滑过渡到目标宽度。

### 5. DOM 动态插入

审查面板插入到聊天区域顶部，使用 `insertBefore`：

```javascript
var panel = document.createElement('div');
panel.className = 'review-panel';
panel.innerHTML = '...'; // 完整的审查卡片 HTML

chatArea.insertBefore(panel, chatArea.firstChild);
chatArea.scrollTop = 0; // 滚动到顶部查看审查结果
```

面板结构：

```
.review-panel (卡片容器, 滑入动画)
├── .review-header (标题 + 关闭按钮 ✕)
├── .review-summary (审查摘要文本)
├── .review-score-wrap (总分 + 纬度标签)
│   └── .review-score (48px 大号数字)
├── .review-dimension × 4 (各维度评分)
│   ├── .review-dim-name (维度名 + 分数)
│   └── .review-dim-bar → .review-dim-fill (进度条)
└── .review-suggestions (改进建议列表)
    └── .review-suggestion × N (每条建议, ▸ 前缀)
```

关闭按钮直接操作 DOM 删除面板：

```html
<button class="review-close" onclick="this.parentNode.parentNode.remove()" title="关闭">✕</button>
```

### 6. clearChat 全面清理

更新 `clearChat()` 确保清除时不残留审查面板（通过 `innerHTML` 整体替换确保清理）：

```javascript
function clearChat() {
  chatArea.innerHTML = `
    <div class="welcome">
      <h2>LumiLearn V5 Observatory</h2>
      <p>...</p>
      <div class="hint">Enter 发送 · Shift+Enter 换行 · Ctrl+L 清屏 · Ctrl+M 录音 · Ctrl+O 识别 · Ctrl+R 审查</div>
    </div>`;
}
```

---

## 学习要点

### DOM 节点遍历与查找
- `querySelectorAll()` 返回 NodeList（不是数组，但可用索引遍历）
- 逆序遍历 `(i = list.length - 1; i >= 0; i--)` 是查找"最后一个匹配元素"的标准模式
- `querySelector()` 在指定元素内查找子元素（如 `msg.querySelector('.msg-avatar.model')`）

### 动态创建与插入 DOM
- `document.createElement('div')` 创建新节点
- `element.innerHTML = '...'` 设置内部 HTML
- `parent.insertBefore(newNode, referenceNode)` 在参考节点前插入
- `chatArea.firstChild` 获取第一个子节点（作为插入参考点）
- 插入后 `chatArea.scrollTop = 0` 控制滚动位置

### CSS 类名动态切换
- 三元表达式计算 CSS 类名：`score >= 8 ? 'high' : 'low'`
- 通过 `className` 属性或模板字符串拼接应用类名
- CSS 变量（`var(--accent-orange)`）保持主题一致性
- `transition` 实现平滑的颜色和宽度过渡

### 按钮状态管理
- 三种状态：就绪（默认）→ 加载中（disabled + 图标变化）→ 就绪（恢复）
- `btn.disabled = true` 禁用点击 + CSS `:disabled` 伪类触发样式变化
- 成功和失败路径都要恢复按钮状态
- `performance.now()` 测量请求耗时

### 错误处理模式
- `try-catch` / `.catch()` 捕获网络错误
- 失败时动态插入错误面板，不中断用户操作
- `resp.ok` 检查 + `resp.json()` 解析后端错误信息
- 错误信息 3 秒后自动恢复 placeholder（语音/OCR 模式）

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 审查按钮点击无反应 | 没有 AI 消息或 `lastAIMessage` 为 null | 检查 chatArea 中是否有 `.msg-avatar.model` 元素 |
| 审查面板不显示 | `/api/review` 端点不可用或返回格式错误 | 检查后端 Flask 路由，确认返回 `{scores, overall, suggestions}` |
| 评分条不显示颜色 | CSS 类名拼写错误或 CSS 变量未定义 | 检查 `.high/.medium/.low` 类名与 CSS 定义一致 |
| 清屏后面板残留 | `clearChat` 未使用 `innerHTML` 整体替换 | 使用 `chatArea.innerHTML = '...'` 确保完全清理 |
| 快捷键不生效 | `Ctrl+R` 与浏览器刷新快捷键冲突 | 已调用 `e.preventDefault()` 阻止浏览器默认行为 |

---

## 相关资源链接

- [MDN: insertBefore](https://developer.mozilla.org/zh-CN/docs/Web/API/Node/insertBefore)
- [MDN: querySelectorAll](https://developer.mozilla.org/zh-CN/docs/Web/API/Document/querySelectorAll)
- [MDN: Performance.now()](https://developer.mozilla.org/zh-CN/docs/Web/API/Performance/now)
- [MDN: CSS transition](https://developer.mozilla.org/zh-CN/docs/Web/CSS/transition)
- 项目文件: [lumiterm.html](file:///e:/学习LLM/lumilearn/tianhong/templates/lumiterm.html)
- 项目文件: [review_engine.py](file:///e:/学习LLM/lumilearn/archive/debug_scripts/self_review_engine.py)（历史归档）