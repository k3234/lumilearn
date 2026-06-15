---
name: "free-domain"
version: "1.0.0"
description: "免费域名抢注与管理技能，集成 DigitalPlatDev/FreeDomain (GitHub 169K stars) 和常见免费域名资源"
tags:
  - domain
  - free
  - web
  - deployment
author: "LumiLearn Team"
license: "AGPL-3.0"
source: "https://github.com/DigitalPlatDev/FreeDomain"
---

# Free-Domain - 免费域名抢注与管理

## 概述

本技能集成了 **DigitalPlatDev/FreeDomain (GitHub 169K stars)** 和其他常见免费域名资源，帮助你零成本获得域名，用于 LumiLearn 项目部署、个人测试、临时项目等场景。

## 核心价值

| 特性 | 说明 |
|------|------|
| 零注册费 | 免费域名 |
| 零续费 | 免费续期 |
| 无隐形收费 | 完全公益开源 |
| 多后缀可选 | 常见子域名与免费顶级域 |
| DNS 管理 | 完整的域名解析功能 |

## 来源项目

- **DigitalPlatDev/FreeDomain**: 169K stars 免费域名项目
- **其他集成**: Cloudflare Pages, Vercel, Netlify, etc.

## 免费域名资源

### 一级资源（强烈推荐）

| 提供商 | 域名格式 | 价格 | 限制 |
|--------|---------|------|------|
| **DigitalPlat FreeDomain** | `*.digitalplat.org` / `*.lumilearn.app` | 免费 | 无注册费，永久免费 |
| **Cloudflare Pages** | `*.pages.dev` | 免费 | 需绑定 GitHub/GitLab |
| **Vercel** | `*.vercel.app` | 免费 | 需绑定 GitHub |
| **Netlify** | `*.netlify.app` | 免费 | 需绑定 GitHub |
| **Render** | `*.onrender.com` | 免费 | 需绑定 GitHub |

### 二级资源（可选）

| 提供商 | 域名格式 | 价格 |
|--------|---------|------|
| **eu.org** | `*.eu.org` | 免费 |
| **js.org** | `*.js.org` | 免费 |
| **is-a.dev** | `*.is-a.dev` | 免费 |
| **github.io** | `*.github.io` | 免费 |

### 顶级域优惠

| 后缀 | 首年价格 | 适合 |
|------|---------|------|
| `.xyz` | $1-5/年 | 通用 |
| `.io` | $30-80/年 | 技术品牌 |
| `.ai` | $100-150/年 | AI 品牌 |
| `.dev` | $12-20/年 | 开发者 |

## 技能结构

```
skills/free-domain/
├── SKILL.md          # 本文件
├── README.md         # 快速使用指南
├── config.json       # 配置
└── domain_manager.py # Python API
```

## 核心能力

### 1. 域名查询与可用性检查

```python
from skills.free-domain.domain_manager import DomainManager

dm = DomainManager()

# 查询 DigitalPlat 免费域名
available = dm.check_availability("lumilearn.digitalplat.org")

# 查询 LumiLearn 品牌域名
results = dm.search_brand_domains("lumilearn")
# → lumilearn.pages.dev, lumilearn.vercel.app, lumilearn.netlify.app
```

### 2. 自动注册（部分）

```python
# 注册 Cloudflare Pages 子域名
domain = dm.register_cloudflare_pages("lumilearn")

# 注册 Vercel 子域名
domain = dm.register_vercel("lumilearn")
```

### 3. DNS 管理

```python
# 添加 A 记录到天虹服务器
dm.add_a_record("lumilearn.digitalplat.org", "192.168.2.xx")

# 添加 CNAME
dm.add_cname("www.lumilearn.digitalplat.org", "lumilearn.digitalplat.org")
```

### 4. LumiLearn 部署方案

```python
# 推荐配置
plan = dm.get_deployment_plan("lumilearn")
print(plan)
```

输出示例：
```
主站: lumilearn.pages.dev → 192.168.2.xx
API: api.lumilearn.pages.dev → 192.168.2.xx:11434
终端: terminal.lumilearn.pages.dev → 192.168.2.xx:18080
```

## LumiLearn 推荐域名列表

按优先级排序：

### 必须抢注

| 域名 | 类型 | 成本 | 部署目标 |
|------|------|------|---------|
| `lumilearn.pages.dev` | Cloudflare Pages | 免费 | 官网主站 |
| `lumilearn.vercel.app` | Vercel | 免费 | 备用站 |
| `lumilearn.netlify.app` | Netlify | 免费 | 演示站 |

### 品牌保护

| 域名 | 类型 | 成本 |
|------|------|------|
| `lumilearn.github.io` | GitHub Pages | 免费 |
| `lumilearn.digitalplat.org` | DigitalPlat | 免费 |
| `lumilearn.xyz` | 付费 | ~$1/年 |

### 专业品牌（可选）

| 域名 | 成本 | 适合 |
|------|------|------|
| `lumilearn.com` | ~¥60/年 | 主品牌 |
| `lumilearn.cn` | ~¥30/年 | 国内 |
| `lumilearn.ai` | ~¥100/年 | AI 品牌 |

## 与 LumiLearn 现有技能协同

### 1. 与 AI-Collab 协同

```python
from skills.ai-collab.orchestrator import AICollabOrchestrator
from skills.free-domain.domain_manager import DomainManager

# AI 帮你抢注域名
orchestrator = AICollabOrchestrator()
domain_agent = orchestrator.get_agent("DomainAgent")
result = domain_agent.register_and_deploy("lumilearn")
```

### 2. 与 CodeGraph 协同

```python
# 自动为你的项目申请域名
cg = CodeGraphBuilder(project_root="./")
domain = dm.get_domain_for_project(cg.get_project_info())
```

### 3. 与 Understand-Anything 协同

```python
# 根据你的项目自动推荐域名
ua = UnderstandAnything(project_root="./")
suggestions = dm.recommend_based_on_codebase(ua)
```

## 使用示例

### 完整工作流

```python
from skills.free-domain.domain_manager import DomainManager

# 初始化
dm = DomainManager()

# 查询域名可用性
options = [
    "lumilearn.pages.dev",
    "lumilearn.vercel.app",
    "lumilearn.digitalplat.org"
]

for domain in options:
    if dm.check_availability(domain):
        print(f"✅ {domain} 可用")
    else:
        print(f"❌ {domain} 已被注册")

# 注册域名（Cloudflare Pages）
domain = dm.register_cloudflare_pages("lumilearn")

# 配置 DNS
dm.add_a_record(domain, "192.168.2.xx")
dm.add_subdomain("api", domain, "192.168.2.xx:11434")
dm.add_subdomain("terminal", domain, "192.168.2.xx:18080")

# 验证部署
result = dm.verify_deployment(domain)
print(result)
```

### 快速部署 LumiLearn

```python
plan = dm.deploy_lumilearn_project(
    project_path="./",
    target_domain="lumilearn.pages.dev",
    tianhong_server="192.168.2.xx"
)
```

## 免费域名 vs 付费域名对比

| 维度 | 免费域名 | 付费域名 |
|------|---------|---------|
| 成本 | 0 | ¥30-150/年 |
| 记忆度 | 一般 | 高 |
| SEO | 一般 | 好 |
| 品牌感 | 一般 | 强 |
| 变更灵活 | 差（可能受限） | 好 |
| 适合场景 | 测试、演示 | 正式产品 |

**建议策略**:
- 早期阶段: 先用免费域名部署测试
- 产品验证后: 注册付费品牌域名
- 过渡期: 两者并用，逐步迁移

## 常见问题

### Q: DigitalPlat FreeDomain 真的永久免费吗？

A: 是的，根据 GitHub 项目说明，该项目完全免费、零续费、无隐形收费。

### Q: 可以用免费域名部署商用产品吗？

A: 需查看各平台条款。Cloudflare Pages/Vercel/Netlify 对商业用途有免费额度。

### Q: 如何同时使用免费域名和付费域名？

A: 使用 CNAME 解析，免费域名作为备用或演示地址。

### Q: 免费域名会影响 SEO 吗？

A: 对 SEO 有轻微影响，产品上线前建议切换到付费顶级域。

## 相关资源

- [DigitalPlatDev/FreeDomain GitHub](https://github.com/DigitalPlatDev/FreeDomain)
- [Cloudflare Pages 文档](https://pages.cloudflare.com/)
- [Vercel 自定义域名](https://vercel.com/docs/custom-domains)
- [Netlify 自定义域名](https://www.netlify.com/docs/custom-domains/)
- [免费域名汇总](https://github.com/awesome-foss/awesome-foss-domains)

## 更新日志

### v1.0.0 (2026-06-05)
- 初始版本
- 集成 DigitalPlatDev/FreeDomain (169K stars)
- 支持 Cloudflare Pages, Vercel, Netlify, GitHub Pages
- DNS 管理功能
- LumiLearn 专项部署方案
- 与 AI-Collab/CodeGraph/Understand-Anything 协同
