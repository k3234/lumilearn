# Free-Domain - 免费域名抢注与管理

## 快速开始

```python
from skills.free-domain.domain_manager import DomainManager

dm = DomainManager()

# 查看免费域名指南
dm.print_free_domain_guide()

# 查询 LumiLearn 域名
results = dm.search_brand_domains("lumilearn")
for r in results:
    print(f"{r.domain} - {'可用' if r.available else '已被注册'}")

# 获取部署方案
plan = dm.get_deployment_plan("lumilearn")
print(plan)
```

## 推荐免费域名

按优先级：
1. **lumilearn.pages.dev** (Cloudflare Pages)
2. **lumilearn.vercel.app** (Vercel)
3. **lumilearn.netlify.app** (Netlify)
4. **lumilearn.digitalplat.org** (169K stars 免费项目)
5. **lumilearn.github.io** (GitHub Pages)

## 与 LumiLearn 部署集成

```python
dm.deploy_lumilearn_project(
    target_domain="lumilearn.pages.dev",
    tianhong_server="192.168.2.63"
)
```

## 来源

- **DigitalPlatDev/FreeDomain**: https://github.com/DigitalPlatDev/FreeDomain (169K stars)
- **Cloudflare Pages**: https://pages.cloudflare.com
- **Vercel**: https://vercel.com
- **Netlify**: https://www.netlify.com
