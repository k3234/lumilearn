# LumiLearn Skills - 技能总览

## 已注册技能（7 个）

### 🆕 free-domain (新增)

**状态**: ✅ 已集成并测试通过

**来源**: DigitalPlatDev/FreeDomain (GitHub 169K stars)

**核心功能**:
- 免费域名抢注与管理
- 集成多个免费域名平台
- DNS 配置与部署方案
- LumiLearn 专项域名推荐

**推荐域名**:
- 免费: lumilearn.pages.dev, lumilearn.vercel.app, lumilearn.digitalplat.org
- 付费: lumilearn.com, lumilearn.cn, lumilearn.ai

**位置**: `skills/free-domain/`

---

### codegraph

**状态**: ✅ 已集成

**来源**: GitHub 30K stars

**核心功能**: 代码知识图谱预索引

---

### build-your-own-x

**状态**: ✅ 已集成

**来源**: GitHub 经典教程项目

**核心功能**: 手搓软件教程

---

### understand-anything

**状态**: ✅ 已集成

**来源**: GitHub 20.1K stars

**核心功能**: 代码库知识图谱

---

### ai-collab

**状态**: ✅ 已集成

**核心功能**: 多智能体协作

---

### hyperframes

**状态**: ✅ 已集成

**核心功能**: 教学动画生成

---

### rtk

**状态**: ✅ 已集成

**核心功能**: Redux Toolkit 生成

---

## 新增技能目录结构

```
skills/free-domain/
├── SKILL.md          # 详细文档（350+ 行）
├── config.json       # 配置文件
├── domain_manager.py # Python 实现
└── README.md         # 快速使用
```

## LumiLearn 域名推荐方案

### 早期阶段（测试）

| 域名 | 成本 | 用途 |
|------|------|------|
| lumilearn.pages.dev | 免费 | 主站 |
| lumilearn.vercel.app | 免费 | 备用站 |
| lumilearn.digitalplat.org | 免费 | 演示站 |

### 产品上线后

| 域名 | 成本 | 用途 |
|------|------|------|
| lumilearn.com | ~¥60/年 | 主品牌 |
| lumilearn.cn | ~¥30/年 | 国内 |
| lumilearn.ai | ~¥100/年 | AI 品牌 |

## 免费域名申请指南

1. **DigitalPlat FreeDomain** - 169K stars
   - https://github.com/DigitalPlatDev/FreeDomain
   - https://domain.digitalplat.org

2. **Cloudflare Pages**
   - https://pages.cloudflare.com

3. **Vercel**
   - https://vercel.com

4. **GitHub Pages**
   - https://pages.github.com

## 使用示例

```python
# 新技能调用示例
from skills.free-domain.domain_manager import DomainManager

dm = DomainManager()

# 查看免费域名指南
dm.print_free_domain_guide()

# 查询域名可用性
results = dm.search_brand_domains("lumilearn")

# 获取部署方案
plan = dm.get_deployment_plan("lumilearn")

# 部署 LumiLearn 项目
dm.deploy_lumilearn_project(
    target_domain="lumilearn.pages.dev",
    tianhong_server="192.168.2.63"
)
```

## 上传到 GitHub

⚠️ **当前状态**: 所有技能在本地完成并调试通过

📋 **如需上传**: 请告诉我，我会帮你提交到 GitHub
