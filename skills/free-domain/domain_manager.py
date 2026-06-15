"""
Free-Domain - 免费域名抢注与管理
集成 DigitalPlatDev/FreeDomain (GitHub 169K stars)
"""
import os
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class DomainCheckResult:
    domain: str
    available: bool
    provider: str
    note: str = ""


@dataclass
class DeploymentPlan:
    main_domain: str
    api_subdomain: str
    terminal_subdomain: str
    tianhong_ip: str
    dns_records: List[Dict]
    free_options: List[str]
    paid_options: List[str]


class DomainManager:
    """域名管理器"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent / "config.json"

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.providers = self.config["providers"]
        self.tianhong_config = self.config["tianhong_server"]

    def check_availability(self, domain: str) -> DomainCheckResult:
        """检查域名可用性（模拟）"""
        if "pages.dev" in domain:
            provider = "cloudflare_pages"
        elif "vercel.app" in domain:
            provider = "vercel"
        elif "netlify.app" in domain:
            provider = "netlify"
        elif "github.io" in domain:
            provider = "github_pages"
        elif "digitalplat.org" in domain:
            provider = "digital_plat"
        else:
            provider = "unknown"

        available = True
        note = "模拟：域名看起来可用（实际需去对应平台验证）"

        return DomainCheckResult(
            domain=domain,
            available=available,
            provider=provider,
            note=note
        )

    def search_brand_domains(self, brand_name: str) -> List[DomainCheckResult]:
        """搜索品牌相关域名"""
        results = []

        for provider, config in self.providers.items():
            if not config.get("enabled", False):
                continue

            for domain_pattern in config.get("supported_domains", []):
                domain = domain_pattern.replace("*", brand_name)
                check = self.check_availability(domain)
                results.append(check)

        return results

    def get_deployment_plan(self, brand_name: str = "lumilearn") -> DeploymentPlan:
        """获取 LumiLearn 部署方案"""
        free_domains = self.config["recommended_lumilearn_domains"]["free"]
        paid_domains = self.config["recommended_lumilearn_domains"]["paid"]

        main_domain = free_domains[0]

        dns_records = [
            {
                "subdomain": "",
                "type": "A",
                "target": self.tianhong_config["ip"],
                "description": "主站 A 记录"
            },
            {
                "subdomain": "api",
                "type": "A",
                "target": self.tianhong_config["ip"],
                "description": f"API 网关: {self.tianhong_config['ollama_port']}"
            },
            {
                "subdomain": "terminal",
                "type": "A",
                "target": self.tianhong_config["ip"],
                "description": f"终端服务: {self.tianhong_config['terminal_port']}"
            }
        ]

        return DeploymentPlan(
            main_domain=main_domain,
            api_subdomain=f"api.{main_domain}",
            terminal_subdomain=f"terminal.{main_domain}",
            tianhong_ip=self.tianhong_config["ip"],
            dns_records=dns_records,
            free_options=free_domains,
            paid_options=paid_domains
        )

    def register_cloudflare_pages(self, name: str) -> str:
        """注册 Cloudflare Pages 域名（模拟）"""
        domain = f"{name}.pages.dev"
        print(f"📝 模拟注册: {domain}")
        print("   1. 访问 https://pages.cloudflare.com")
        print("   2. 连接你的 GitHub 账号")
        print(f"   3. 创建项目 '{name}'")
        print(f"   4. 域名会自动分配: {domain}")
        return domain

    def register_vercel(self, name: str) -> str:
        """注册 Vercel 域名（模拟）"""
        domain = f"{name}.vercel.app"
        print(f"📝 模拟注册: {domain}")
        print("   1. 访问 https://vercel.com")
        print("   2. 连接你的 GitHub 账号")
        print(f"   3. 导入仓库并部署")
        print(f"   4. 域名会自动分配: {domain}")
        return domain

    def add_a_record(self, domain: str, ip: str) -> Dict:
        """添加 A 记录（模拟）"""
        print(f"📋 模拟添加 A 记录:")
        print(f"   {domain} → {ip}")
        print("   (实际需去对应域名管理平台添加)")
        return {"success": True, "domain": domain, "ip": ip}

    def add_cname(self, subdomain: str, target_domain: str) -> Dict:
        """添加 CNAME 记录（模拟）"""
        print(f"📋 模拟添加 CNAME 记录:")
        print(f"   {subdomain} → {target_domain}")
        return {"success": True, "subdomain": subdomain, "target": target_domain}

    def verify_deployment(self, domain: str) -> Dict:
        """验证部署（模拟）"""
        return {
            "domain": domain,
            "resolving": "OK",
            "ttl": 300,
            "note": "域名 DNS 解析检查（实际需去浏览器验证）"
        }

    def deploy_lumilearn_project(
        self,
        project_path: str = "./",
        target_domain: str = None,
        tianhong_server: str = None
    ) -> Dict:
        """部署 LumiLearn 项目（模拟）"""
        if target_domain is None:
            target_domain = self.config["recommended_lumilearn_domains"]["free"][0]

        if tianhong_server is None:
            tianhong_server = self.tianhong_config["ip"]

        print("=" * 60)
        print("🚀 LumiLearn 免费域名部署计划")
        print("=" * 60)

        plan = self.get_deployment_plan("lumilearn")

        print(f"\n📌 推荐配置:")
        print(f"   主站: {plan.main_domain}")
        print(f"   API: {plan.api_subdomain}")
        print(f"   终端: {plan.terminal_subdomain}")
        print(f"   天虹服务器 IP: {tianhong_server}")

        print(f"\n📝 域名列表:")
        print(f"   免费选项: {', '.join(plan.free_options)}")
        print(f"   付费选项: {', '.join(plan.paid_options)}")

        print(f"\n📋 DNS 记录配置:")
        for record in plan.dns_records:
            sub = f"{record['subdomain']}." if record['subdomain'] else ""
            print(f"   {sub}{target_domain} → {record['target']}")

        print(f"\n🔧 部署步骤:")
        print(f"   1. 注册 {target_domain} (见对应平台文档)")
        print(f"   2. 添加 A 记录指向 {tianhong_server}")
        print(f"   3. 配置子域名 api/terminal")
        print(f"   4. 在天虹服务器上部署 LumiLearn")
        print(f"   5. 验证连接")

        return asdict(plan)

    def print_free_domain_guide(self):
        """打印免费域名申请指南"""
        print("=" * 60)
        print("🎯 LumiLearn 免费域名申请指南")
        print("=" * 60)

        print(f"\n1. DigitalPlat FreeDomain (强烈推荐)")
        print(f"   项目: https://github.com/DigitalPlatDev/FreeDomain (169K stars)")
        print(f"   网站: https://domain.digitalplat.org")
        print(f"   格式: *.digitalplat.org, *.lumilearn.app")

        print(f"\n2. Cloudflare Pages (推荐)")
        print(f"   网站: https://pages.cloudflare.com")
        print(f"   格式: *.pages.dev")
        print(f"   步骤:")
        print(f"    - GitHub 仓库部署")
        print(f"    - 域名自动分配")

        print(f"\n3. Vercel (推荐)")
        print(f"   网站: https://vercel.com")
        print(f"   格式: *.vercel.app")
        print(f"   步骤:")
        print(f"    - GitHub 仓库部署")
        print(f"    - 域名自动分配")

        print(f"\n4. GitHub Pages")
        print(f"   网站: https://pages.github.com")
        print(f"   格式: *.github.io")
        print(f"   步骤:")
        print(f"    - 创建 repo: username.github.io")
        print(f"    - 开启 Pages 功能")

        print(f"\n5. 其他选择")
        print(f"   - *.js.org: https://js.org")
        print(f"   - *.eu.org: https://nic.eu.org")
        print(f"   - *.is-a.dev: https://www.is-a.dev")

        print("=" * 60)
        print("\n💡 提示:")
        print("   - 早期阶段用免费域名测试")
        print("   - 验证产品后注册付费顶级域")
        print("   - 过渡期间两者并用")


if __name__ == "__main__":
    dm = DomainManager()

    dm.print_free_domain_guide()

    print("\n" + "=" * 60)
    print("🔍 查询 LumiLearn 域名可用性")
    print("=" * 60)

    results = dm.search_brand_domains("lumilearn")
    for r in results:
        status = "✅" if r.available else "❌"
        print(f"   {status} {r.domain} ({r.provider})")

    print("\n" + "=" * 60)
    print("🚀 LumiLearn 部署方案")
    print("=" * 60)
    plan = dm.get_deployment_plan("lumilearn")
    dm.deploy_lumilearn_project()
