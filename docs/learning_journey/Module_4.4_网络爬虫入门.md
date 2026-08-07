# Module 4.4 — 网络爬虫入门：学习资源获取

**日期**: 2026-06-01
**状态**: ✅ 完成
**相关模块**: Module 4.1（Whisper语音识别）、Module 4.2（OCR文字识别）、Module 4.3（Prompt工程）
**难度**: ⭐⭐⭐☆☆

---

## 📚 学习目标

完成本模块后，你将能够：

1. 理解 HTTP 请求的基本原理和 requests 库的核心用法
2. 掌握 BeautifulSoup 网页解析技术（CSS选择器、标签遍历）
3. 实现 DuckDuckGo HTML 搜索和 Bing 搜索结果抓取
4. 设计与实现搜索结果的 RAG 摘要（调用 Ollama 本地模型）
5. 理解降级策略（Graceful Degradation）在爬虫系统中的应用
6. 构建完整的 Flask API 端点（参数验证、错误处理、JSON 返回）

---

## 🧠 网络爬虫原理简介

### 什么是网络爬虫？

网络爬虫（Web Crawler / Web Scraper）是自动抓取网页内容的程序。在本模块中，我们实现的是一个**轻量级搜索聚合器**：

```
                        ┌──────────────────────────────┐
                        │      WebResourceFetcher        │
                        │                                │
    用户查询 ──────────▶│  1. DuckDuckGo HTML 搜索       │──▶ 搜索结果
    分类参数            │  2. Bing 搜索（备用）          │
                        │  3. 预设资源库（降级）          │
                        │  4. Ollama RAG 摘要            │──▶ AI摘要
                        └──────────────────────────────┘
```

### 为什么选择这些方案？

| 方案 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| DuckDuckGo HTML | 无需API Key，稳定可靠 | CSS选择器可能变更 | 首选方案 |
| Bing 搜索抓取 | 搜索结果质量高，中文支持好 | 反爬机制较严格 | 备用方案 |
| 预设资源库 | 零延迟，100%可用 | 内容固定不更新 | 降级方案 |
| Ollama RAG摘要 | 本地运行，无网络依赖 | 需要GPU/大内存 | 智能摘要 |

---

## 🧭 实现步骤（分步详解）

### 步骤 1：HTTP 请求 — 与网络对话

HTTP 请求是爬虫的第一步。我们使用 `requests.Session()` 来维持连接和自定义请求头：

```python
import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"
)

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

# GET 请求
resp = session.get("https://example.com", timeout=10)

# POST 请求（用于 DuckDuckGo HTML 搜索）
resp = session.post("https://html.duckduckgo.com/html/", data={"q": "数学"}, timeout=10)
```

**关键要点**：
- `User-Agent` 模拟浏览器身份，避免被识别为爬虫
- `Session()` 复用 TCP 连接，提高效率
- `timeout` 防止请求无限等待，是健壮性的基础

### 步骤 2：网页解析 — BeautifulSoup

拿到 HTML 后，需要从中提取结构化数据。BeautifulSoup 是最流行的 Python HTML 解析库：

```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(resp.text, "html.parser")

# CSS 选择器 — 最常用的解析方式
for item in soup.select(".result")[:5]:
    title_el = item.select_one(".result__title a")
    snippet_el = item.select_one(".result__snippet")
    if title_el:
        title = title_el.get_text(strip=True)   # 提取文字
        link = title_el.get("href", "")           # 提取属性
```

**CSS 选择器速查**：
| 选择器 | 含义 | 示例 |
|--------|------|------|
| `.class` | 按类名选择 | `.result` |
| `#id` | 按ID选择 | `#main` |
| `tag` | 按标签名选择 | `h2`, `a` |
| `parent > child` | 直接子元素 | `li > a` |
| `parent child` | 任意后代 | `.result a` |
| `[attr=value]` | 按属性选择 | `[name="description"]` |

### 步骤 3：数据提取与结构化

从 HTML 片段中提取标题、链接和摘要，统一为字典格式：

```python
# DuckDuckGo HTML 搜索结果解析
results = []
for item in soup.select(".result")[:max_results]:
    title_el = item.select_one(".result__title a")
    snippet_el = item.select_one(".result__snippet")
    if title_el:
        results.append({
            "title": title_el.get_text(strip=True),
            "url": title_el.get("href", ""),
            "snippet": snippet_el.get_text(strip=True) if snippet_el else ""
        })
return results
```

**结构化数据统一格式**对于后续处理至关重要：
- 所有搜索结果使用相同的 `{"title", "url", "snippet"}` 结构
- 预设资源和在线搜索结果格式完全一致，无缝切换

### 步骤 4：分类搜索关键词构建

不同学科需要不同的搜索策略。通过分类关键词映射提高搜索精度：

```python
CATEGORY_KEYWORDS = {
    "math": ["数学", "代数", "几何", "微积分", "线性代数", "概率",
             "math", "calculus", "algebra", "geometry"],
    "english": ["英语", "英文", "语法", "词汇", "听力", "口语",
                "english", "grammar", "vocabulary", "listening"],
    "physics": ["物理", "力学", "电磁学", "光学", "热力学", "量子",
                "physics", "mechanics", "electromagnetism"],
}

def _build_query(self, query, category="general"):
    keywords = CATEGORY_KEYWORDS.get(category, [])
    if keywords:
        best_kw = keywords[0]  # 默认第一个
        for kw in keywords[3:]:  # 尝试匹配用户查询中的词
            if kw in query.lower():
                best_kw = kw
                break
        return f"{best_kw} {query} 学习资源"
    return f"{query} 学习资源 site:edu OR site:org"
```

### 步骤 5：RAG 摘要生成

RAG（Retrieval-Augmented Generation）将搜索结果作为上下文注入 LLM，生成有针对性的摘要：

```
[RAG流程]
搜索结果 → 拼接为 Prompt 上下文 → Ollama 本地模型 → JSON 结构化摘要

Prompt模板:
  角色: 学习资源推荐专家
  输入: 搜索结果列表 + 用户查询
  输出: {summary, key_points, suggested_order}
```

```python
def summarize_resources(self, resources, query):
    # 将资源格式化为文本
    resource_text = ""
    for i, r in enumerate(resources, 1):
        resource_text += f"{i}. {r['title']}\n   摘要: {r['snippet']}\n"
    
    # 构建 Prompt
    prompt = f"""你是一位学习资源推荐专家...
    【学习者查询】{query}
    【搜索结果】{resource_text}
    请以JSON格式返回分析结果..."""
    
    # 调用 Ollama
    response = call_ollama("qwen2.5:7b", prompt, timeout=60)
    # 正则提取 JSON → 解析 → 返回
```

### 步骤 6：降级策略设计

降级策略（Graceful Degradation）是爬虫系统的核心设计模式：

```
         ┌─ DuckDuckGo 搜索 ──▶ 成功 ──▶ 返回结果
         │       │
  用户查询 ───┼─ 失败 ──▶ Bing 搜索 ──▶ 成功 ──▶ 返回结果
         │          │
         │      失败 ──▶ 预设资源库 ──▶ 返回结果（100%可用）
         │
         └─ Ollama 摘要失败 ──▶ 使用规则生成基础摘要
```

**降级策略设计原则**：
1. **多级后备**：每个环节都有备用方案
2. **静默降级**：失败时不抛异常，而是自动切换
3. **结果标记**：返回 `source` 字段（"web" / "preset"）让调用方知道数据来源
4. **缓存兜底**：成功的搜索结果缓存 1 小时，减少重复请求

### 步骤 7：Flask API 端点实现

将搜索功能封装为 RESTful API，遵循与 Whisper/OCR/Review 端点一致的代码风格：

```python
@app.route("/api/resources", methods=["POST", "OPTIONS"])
def api_resources():
    # 1. OPTIONS 预检处理
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    
    # 2. 参数验证
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "请求体为空"}), 400
    
    query = data.get("query", "")
    if not query.strip():
        return jsonify({"error": "缺少 query 字段"}), 400
    
    category = data.get("category", "general")
    if category not in CATEGORIES:
        return jsonify({"error": f"不支持的分类: {category}"}), 400
    
    max_results = data.get("max_results", 5)
    if not isinstance(max_results, int) or max_results < 1 or max_results > 10:
        return jsonify({"error": "max_results 必须为 1-10 的整数"}), 400
    
    # 3. 调用搜索
    fetcher = _get_resource_fetcher()
    result = fetcher.search_with_summary(query.strip(), category, max_results)
    
    # 4. 返回结构化 JSON
    return jsonify({
        "resources": result["resources"],
        "summary": result["summary"]["summary"],
        "key_points": result["summary"].get("key_points", []),
        "suggested_order": result["summary"].get("suggested_order", []),
        "query": query.strip(),
        "category": category,
        "source": "web" if result["resources"] else "preset"
    })
```

---

## 💻 关键代码（带注释）

### 完整功能架构

```
web_resource_fetcher.py (v1.0)
│
├── 配置区
│   ├── USER_AGENT              # 浏览器标识
│   ├── CATEGORIES              # 支持分类列表
│   ├── PRESET_RESOURCES        # 预设资源库（降级方案）
│   └── CATEGORY_KEYWORDS       # 分类关键词映射
│
├── WebResourceFetcher 类
│   ├── __init__()              # 初始化 requests.Session 和缓存
│   ├── _build_query()          # 构建分类搜索词
│   ├── _search_duckduckgo_html() # DuckDuckGo HTML 搜索
│   ├── _search_bing()          # Bing 搜索（备用）
│   ├── _fetch_page_metadata()  # 抓取网页元数据
│   ├── _fallback_preset_resources() # 预设资源降级
│   ├── search()                # 主搜索方法
│   ├── summarize_resources()   # RAG摘要生成
│   └── search_with_summary()  # 一站式搜索+摘要
│
└── 缓存机制
    ├── _get_cached()           # 内存缓存读取
    └── _set_cache()           # 内存缓存写入（LRU淘汰）
```

### 核心搜索流程

```python
def search(self, query, category="general", max_results=5):
    # 1. 检查缓存
    cache_key = f"{category}:{query}:{max_results}"
    cached = self._get_cached(cache_key)
    if cached:
        return cached

    # 2. 构建搜索词
    search_query = self._build_query(query, category)
    
    # 3. 三级搜索策略
    results = []
    
    # 第一级：DuckDuckGo HTML搜索
    try:
        results = self._search_duckduckgo_html(search_query, max_results)
    except Exception:
        pass

    # 第二级：Bing搜索（如果第一级失败）
    if not results:
        try:
            results = self._search_bing(search_query, max_results)
        except Exception:
            pass

    # 第三级：预设资源降级（如果两级都失败）
    if not results:
        results = self._fallback_preset_resources(query, category, max_results)
    
    # 4. 写入缓存
    self._set_cache(cache_key, results)
    return results[:max_results]
```

### 缓存机制实现

```python
def __init__(self):
    self.cache = {}       # {"key": {"data": [...], "time": 1234567}}
    self.cache_ttl = 3600 # 缓存有效期：1小时

def _get_cached(self, cache_key):
    if cache_key in self.cache:
        entry = self.cache[cache_key]
        if time.time() - entry["time"] < self.cache_ttl:
            return entry["data"]
    return None

def _set_cache(self, cache_key, data):
    self.cache[cache_key] = {"data": data, "time": time.time()}
    # LRU淘汰：缓存超过50条时删除最旧的
    if len(self.cache) > 50:
        oldest = min(self.cache.keys(), key=lambda k: self.cache[k]["time"])
        del self.cache[oldest]
```

### 预设资源智能匹配

```python
def _fallback_preset_resources(self, query, category, max_results):
    # 获取对应分类的资源
    resources = PRESET_RESOURCES.get(category, PRESET_RESOURCES["general"])
    
    # 关键词打分排序
    query_lower = query.lower()
    scored = []
    for r in resources:
        score = 0
        title_lower = r["title"].lower()
        snippet_lower = r["snippet"].lower()
        for word in query_lower.split():
            if word in title_lower:
                score += 3    # 标题匹配权重高
            if word in snippet_lower:
                score += 1    # 摘要匹配权重低
        scored.append((score, r))
    
    # 按分数降序排列
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:max_results]]
```

---

## 🎓 学习要点（核心知识点）

### 1. requests 库 — HTTP 请求基础

requests 是 Python 最流行的 HTTP 客户端库，核心用法：

| 方法 | 用途 | 示例 |
|------|------|------|
| `requests.get(url)` | GET 请求 | 获取网页内容 |
| `requests.post(url, data={})` | POST 请求 | 提交表单/搜索 |
| `requests.Session()` | 会话保持 | 复用连接、维持 Cookie |
| `resp.text` | 获取响应文本 | HTML 内容 |
| `resp.json()` | 获取 JSON 响应 | API 返回值 |
| `resp.status_code` | 获取状态码 | 200=成功, 404=未找到 |
| `resp.raise_for_status()` | 检查状态码 | 非 2xx 时抛异常 |
| `timeout=10` | 超时设置 | 防止无限等待 |

**常见状态码**：
```
2xx: 成功 (200 OK)
3xx: 重定向 (301 永久, 302 临时)
4xx: 客户端错误 (400 请求错误, 403 禁止, 404 未找到)
5xx: 服务器错误 (500 内部错误, 502 网关错误, 504 超时)
```

### 2. BeautifulSoup — HTML 解析核心

BeautifulSoup 将 HTML 转换为可遍历的树形结构：

```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html_text, "html.parser")

# 常用搜索方法
soup.find("tag")            # 查找第一个匹配标签
soup.find_all("tag")        # 查找所有匹配标签
soup.select(".class")       # CSS选择器（推荐）
soup.select_one("#id")      # 查找第一个（CSS选择器）

# 常用属性访问
element.get_text()          # 获取文本内容
element.get("href")         # 获取属性值
element["class"]            # 获取class列表
element.parent              # 父元素
element.children            # 子元素

# 常用参数
soup.select("li", limit=5)  # 限制结果数量
element.get_text(strip=True) # 去除首尾空白
```

### 3. RAG 摘要 — 检索增强生成

RAG（Retrieval-Augmented Generation）是将检索结果注入 LLM 上下文的技术：

```
传统 LLM 回答：
  用户: "推荐学习二次函数的资源"
  LLM: (基于训练知识回答，可能过时或不准确)

RAG 回答：
  用户: "推荐学习二次函数的资源"
  检索: [资源1, 资源2, 资源3, ...]  ← 实时搜索结果
  LLM: "根据最新搜索结果，推荐以下资源..."  ← 基于检索内容回答
```

在本模块中，RAG 的实现方式：
1. `retrieval`: `search()` 方法获取实时/预设资源
2. `augmented`: 将资源拼接为 Prompt 上下文
3. `generation`: Ollama 模型基于上下文生成结构化摘要

### 4. 降级策略 — 系统健壮性基石

降级策略（Graceful Degradation）确保系统在任何情况下都能返回可用结果：

```
优先级链：
┌──────────────────────────────────────────────────┐
│ 1. 在线搜索 (DuckDuckGo → Bing)                   │
│    ↓ 失败                                         │
│ 2. 预设资源库 (零延迟, 100%可用)                   │
│    ↓ 始终成功                                     │
│ 3. 返回结果 + source字段标记数据来源               │
└──────────────────────────────────────────────────┘
```

**降级策略最佳实践**：
- 每个环节独立 `try/except`，互不影响
- 预设资源库是最后的"安全网"
- 通过 `source` 字段让调用方知道数据质量
- 缓存成功的在线结果，减少降级概率

### 5. 多搜索引擎适配

不同搜索引擎有不同的 HTML 结构，需要不同的解析策略：

| 搜索引擎 | 搜索方式 | CSS选择器（标题/链接） | CSS选择器（摘要） |
|----------|----------|------------------------|-------------------|
| DuckDuckGo | POST | `.result__title a` | `.result__snippet` |
| Bing | GET | `li.b_algo h2 a` | `.b_caption p` |

适配新搜索引擎只需要添加一个 `_search_xxx()` 方法，然后加入多级搜索链即可。

---

## ❓ 常见问题（FAQ）

### Q1: DuckDuckGo HTML 搜索被限流怎么办？

**A**: 几种策略：

1. **增加请求间隔**：在连续请求间加 `time.sleep(1-2)` 秒
2. **轮换 User-Agent**：使用不同的浏览器标识
3. **切换到 Bing**：Bing 作为备用引擎自动生效
4. **依赖缓存**：成功的搜索结果缓存 1 小时
5. **使用预设资源**：降级方案 100% 可用

### Q2: BeautifulSoup 的 `html.parser` 和其他解析器有什么区别？

**A**: BeautifulSoup 支持多种解析器：

| 解析器 | 速度 | 容错性 | 安装 |
|--------|------|--------|------|
| `html.parser` | 中 | 中 | Python内置 |
| `lxml` | 快 | 高 | `pip install lxml` |
| `html5lib` | 慢 | 最高 | `pip install html5lib` |

本项目使用 `html.parser`（零额外依赖），如果需要更好的性能和容错性，可以切换到 `lxml`。

### Q3: 如何判断搜索结果是来自在线搜索还是预设资源？

**A**: API 返回中包含 `source` 字段：

```json
{
    "resources": [...],
    "source": "web"      // "web" = 在线搜索, "preset" = 降级预设
}
```

前端可以根据此字段显示不同的 UI 提示（如"在线搜索结果" vs "推荐资源"）。

### Q4: 为什么要用 requests.Session 而不是直接 requests.get？

**A**: `Session()` 的优势：

1. **连接复用**：多次请求复用同一个 TCP 连接，减少握手开销
2. **Cookie 保持**：自动管理 Cookie，适合需要登录的网站
3. **统一配置**：headers、proxies 等只需设置一次
4. **性能提升**：连续请求时延迟降低 30-50%

### Q5: 如果网页结构变了（CSS 类名改了），怎么处理？

**A**: 几种防护措施：

1. **多层选择器**：用多种选择器同时尝试匹配
2. **优雅降级**：解析失败时返回空列表 `[]`，触发下一级搜索
3. **结果验证**：检查 `title` 和 `url` 是否为空再返回
4. **日志记录**：在关键解析环节添加日志，便于排查

### Q6: Ollama 摘要调用失败怎么办？

**A**: 摘要功能有三级降级：

```python
try:
    response = call_ollama("qwen2.5:7b", prompt, timeout=60)
    # 解析 JSON...
except Exception:
    pass  # 不抛异常，使用规则生成的默认摘要

# 降级摘要
return {
    "summary": f"共找到 {len(resources)} 个与'{query}'相关的学习资源。",
    "key_points": [r["title"][:30] for r in resources[:3]],
    "suggested_order": [r["title"][:30] for r in resources[:2]]
}
```

---

## 🔗 相关资源链接

| 资源 | 说明 |
|------|------|
| [requests 官方文档](https://docs.python-requests.org/) | Python HTTP 客户端库文档 |
| [BeautifulSoup 文档](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) | HTML/XML 解析库文档 |
| [DuckDuckGo HTML 搜索](https://html.duckduckgo.com/html/) | DuckDuckGo 的非JS搜索版本 |
| [CSS 选择器参考](https://www.w3schools.com/cssref/css_selectors.php) | CSS 选择器速查表 |
| [HTTP 状态码大全](https://developer.mozilla.org/zh-CN/docs/Web/HTTP/Status) | MDN HTTP 状态码参考 |
| [RAG 技术概述](https://www.promptingguide.ai/techniques/rag) | Prompt Engineering Guide 的 RAG 介绍 |
| [Full Stack Python - Web Scraping](https://www.fullstackpython.com/web-scraping.html) | Python 爬虫技术全景 |
| LumiLearn archive/debug_scripts/web_resource_fetcher.py | 本模块核心实现（历史归档） |
| LumiLearn archive/debug_scripts/lumiterm_local_server.py | 本模块 API 端点实现（历史归档） |

---

## 📝 总结

通过本模块的学习，我们实现了一个完整的网络学习资源获取系统。主要收获：

1. **HTTP 请求基础** — 掌握 requests 库的 GET/POST/Session 用法，理解 User-Agent 和超时设置
2. **HTML 解析技术** — 使用 BeautifulSoup + CSS 选择器从网页中提取结构化数据
3. **多搜索引擎适配** — DuckDuckGo HTML 首选，Bing 备用，适配不同 HTML 结构
4. **RAG 摘要生成** — 将搜索结果注入 Ollama 上下文，生成针对性学习摘要
5. **降级策略设计** — 在线搜索 → 预设资源，确保 100% 可用
6. **Flask API 端点** — 遵循项目统一风格（OPTIONS预检、参数验证、错误处理、JSON返回）

> **核心理念**：爬虫系统的价值不在于"能爬"，而在于"爬不到时仍可用"。降级策略不是妥协，而是让系统在不可靠的互联网环境中保持可靠的关键设计。

---

## 🔜 下一步

- **Module 4.5**：多模态理解 — 结合Whisper、OCR和LLM，让AI"看懂"学习材料
- **Module 5.1**：前端网络搜索 — 在 LumiTerminal 中集成资源搜索 UI
- **Module 5.2**：RAG 问答系统 — 基于检索的智能问答，提升学习效率