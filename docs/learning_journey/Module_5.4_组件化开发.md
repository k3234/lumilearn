# Module 5.4 · 组件化开发

> 在 LumiTerminal 中添加资源获取前端功能，实现可折叠面板、搜索按钮、RAG 摘要展示等组件化 UI 模式。

---

## 学习目标

- 掌握可折叠面板（collapsible panel）的 CSS 实现与 JavaScript 控制
- 理解组件化 UI 的设计模式：按钮 → 面板 → 数据展示的完整链路
- 实现多入口数据获取（输入框关键词 / 历史消息回溯）
- 掌握 `classList.toggle()` 和 CSS transition 实现平滑动画
- 建立前端快捷键注册的统一模式（`handleKey` 扩展）

---

## 实现步骤

### 1. 组件架构设计

资源获取功能由三个组件协作完成：

```
用户操作入口（三选一）
├── 点击 🔍 按钮 → fetchResources()
├── 按 Ctrl+F    → fetchResources()
└── 点击 📚 切换 → toggleResources()
         ↓
   fetchResources()    ← 核心调度函数
         ↓
   POST /api/resources  ← 后端 API
         ↓
   showResources(data)  ← 数据渲染函数
         ↓
   .resources-panel     ← 可折叠面板容器
    ├── .resources-toggle  ← 展开/收起切换条
    └── .resources-list    ← 资源列表 + RAG 摘要
```

### 2. 可折叠面板 CSS 实现

通过 `max-height` 过渡实现平滑折叠/展开：

```css
.resources-panel {
  max-height: 360px;          /* 展开状态 */
  overflow: hidden;
  transition: max-height 0.35s ease, padding 0.35s ease;
}
.resources-panel.collapsed {
  max-height: 42px;           /* 折叠状态：仅显示切换条 */
}
```

| CSS 属性 | 作用 | 说明 |
|----------|------|------|
| `max-height: 360px` | 展开时内容区最大高度 | 配合 `overflow-y: auto` 实现滚动 |
| `max-height: 42px` | 折叠时只显示切换条 | 切换条行高 + padding |
| `transition: max-height 0.35s ease` | 平滑过渡动画 | 模拟 `slideDown`/`slideUp` 效果 |
| `overflow: hidden` | 隐藏溢出内容 | 折叠状态下内容不可见 |

**为什么用 `max-height` 而不是 `height`？**

因为面板内容高度是动态的（资源数量不定），`max-height` 配合 `auto` 内容高度可以实现自适应的折叠展开。

### 3. 切换按钮的箭头方向更新

折叠/展开时更新箭头符号：

```javascript
function toggleResources() {
  var panel = document.getElementById('resourcesPanel');
  panel.classList.toggle('collapsed');
  updateResourcesToggle();
}

function updateResourcesToggle() {
  var panel = document.getElementById('resourcesPanel');
  var toggle = panel.querySelector('.resources-toggle');
  if (panel.classList.contains('collapsed')) {
    toggle.innerHTML = '📚 相关资源 ▼';
  } else {
    toggle.innerHTML = '📚 相关资源 ▲';
  }
}
```

`classList.toggle()` 是原生 DOM API，无需手动检查当前状态再设置：
- 有 `collapsed` 类 → 移除
- 无 `collapsed` 类 → 添加

### 4. 多入口数据获取

`fetchResources()` 支持两种获取关键词的方式：

```javascript
function fetchResources() {
  var keyword = inputBox.value.trim();

  // 入口1：输入框中的关键词
  if (!keyword) {
    // 入口2：回溯最后一条用户消息
    var messages = chatArea.querySelectorAll('.message');
    for (var i = messages.length - 1; i >= 0; i--) {
      var avatar = messages[i].querySelector('.msg-avatar.user');
      if (avatar) {
        var textEl = messages[i].querySelector('.msg-text');
        if (textEl && textEl.textContent.trim()) {
          keyword = textEl.textContent.trim();
          break;
        }
      }
    }
  }

  if (!keyword) {
    alert('请输入搜索关键词或先发送一条消息。');
    return;
  }
  // ... 发送请求
}
```

| 入口 | 优先级 | 适用场景 |
|------|--------|----------|
| 输入框内容 | 高 | 用户主动输入搜索词 |
| 最后一条用户消息 | 低（降级） | 用户刚聊完某个话题想搜索相关资源 |
| 无关键词 | 失败 | 提示用户输入 |

这与审查功能的"查找最后一条 AI 消息"模式一致，但查找的是用户消息。

### 5. 资源数据渲染

`showResources(data)` 构建资源列表 DOM：

```javascript
function showResources(data) {
  var list = document.getElementById('resourcesList');
  var html = '';

  var resources = data.resources || [];
  for (var i = 0; i < resources.length; i++) {
    var r = resources[i];
    html += '<div class="resource-item">';
    html += '<a href="' + (r.url || '#') + '" target="_blank">' + (r.title || '未命名资源') + '</a>';
    if (r.summary) {
      html += '<div class="resource-summary">' + r.summary + '</div>';
    }
    if (r.source) {
      html += '<div class="resource-source">来源: ' + r.source + '</div>';
    }
    html += '</div>';
  }

  // RAG 摘要
  if (data.rag_summary) {
    html += '<div class="resource-rag-summary">';
    html += '<h4>🤖 AI 学习摘要</h4>';
    html += '<p>' + data.rag_summary + '</p>';
    html += '</div>';
  }

  list.innerHTML = html;
}
```

后端返回的数据结构（预期）：

```json
{
  "resources": [
    { "title": "...", "url": "https://...", "summary": "...", "source": "DuckDuckGo" }
  ],
  "rag_summary": "基于检索结果生成的学习路径建议...",
  "source": "DuckDuckGo + Ollama"
}
```

### 6. 快捷键注册

在 `handleKey` 中统一注册 `Ctrl+F`：

```javascript
if (e.key === 'f' && e.ctrlKey) {
  e.preventDefault();
  fetchResources();
}
```

快捷键一览表：

| 快捷键 | 功能 | 冲突处理 |
|--------|------|----------|
| Enter | 发送消息 | 仅非 Shift 时触发 |
| Ctrl+L | 清屏 | 覆盖浏览器地址栏聚焦 |
| Ctrl+M | 录音 | 无冲突 |
| Ctrl+O | OCR 识别 | 覆盖浏览器打开文件 |
| Ctrl+R | 审查讲解 | 覆盖浏览器刷新 |
| Ctrl+F | 搜索资源 | 覆盖浏览器页面搜索 |

所有快捷键都调用了 `e.preventDefault()` 阻止浏览器默认行为。

### 7. clearChat 全面清理

更新 `clearChat()` 确保同时折叠资源面板和清空资源列表：

```javascript
function clearChat() {
  chatArea.innerHTML = `...`;  // 重置聊天区域

  var panel = document.getElementById('resourcesPanel');
  if (panel && !panel.classList.contains('collapsed')) {
    panel.classList.add('collapsed');
  }
  var rList = document.getElementById('resourcesList');
  if (rList) rList.innerHTML = '';
}
```

---

## 学习要点

### 组件化开发的三个层次

| 层次 | 本模块示例 | 说明 |
|------|-----------|------|
| 视觉层（CSS） | `.resources-panel`, `.resource-item` | 样式定义，使用 CSS 变量保持主题一致 |
| 交互层（JS） | `toggleResources()`, `fetchResources()` | 事件处理、状态管理、API 通信 |
| 数据层（API） | `/api/resources` POST JSON | 后端数据接口，返回结构化 JSON |

### CSS transition 动画技巧

- `max-height` 过渡模拟折叠：比 `display: none` 更平滑，但比 `height: auto` 过渡更可控
- 过渡时间 `0.35s` 是 UI 组件的常用值（不太快也不太慢）
- `ease` 缓动函数让动画开始和结束更自然

### 按钮状态机

按钮同样遵循三态模式：

| 状态 | 图标 | 说明 |
|------|------|------|
| 就绪 | 🔍 | 等待用户点击 |
| 搜索中 | ⏳ | `disabled` + 后端返回前 |
| 完成/失败 | 🔍 | 恢复可点击 |

### 用户提示字符串的更新

所有涉及快捷键提示的 HTML 都需要同步更新：
- 初始 welcome div 中的 `.hint`
- `clearChat()` 函数中重建的 welcome HTML

两个位置的提示文字必须保持一致。

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 面板折叠后内容不可见 | `.collapsed` 的 `max-height: 42px` 隐藏了内容 | 检查 `overflow: hidden` 是否正确设置 |
| 箭头方向不更新 | `toggleResources()` 未调用 `updateResourcesToggle()` | 确保切换函数最后调用 `updateResourcesToggle()` |
| 搜索按钮无反应 | `/api/resources` 端点不可用 | 检查后端 Flask 路由，确认端点存在 |
| Ctrl+F 仍触发浏览器搜索 | `e.preventDefault()` 未生效 | 确认 `handleKey` 中 `e.key === 'f'` 的判断正确 |
| 清屏后资源面板仍展开 | `clearChat()` 未处理资源面板 | 检查 `clearChat` 中是否包含面板折叠和列表清空逻辑 |

---

## 相关资源链接

- [MDN: classList.toggle()](https://developer.mozilla.org/zh-CN/docs/Web/API/DOMTokenList/toggle)
- [MDN: CSS max-height](https://developer.mozilla.org/zh-CN/docs/Web/CSS/max-height)
- [MDN: CSS transition](https://developer.mozilla.org/zh-CN/docs/Web/CSS/transition)
- [MDN: KeyboardEvent.key](https://developer.mozilla.org/zh-CN/docs/Web/API/KeyboardEvent/key)
- 项目文件: [lumiterm.html](file:///e:/学习LLM/lumilearn/remote/templates/lumiterm.html)
- 项目文件: [resources.py](file:///e:/学习LLM/lumilearn/framework/api/routes/resources.py)