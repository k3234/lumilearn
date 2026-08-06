#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 安全系统启动脚本
检测内网IP并初始化安全组件
"""
import sys
from pathlib import Path

# 添加到路径
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

def main():
    print("=" * 60)
    print("LumiLearn 安全系统初始化")
    print("=" * 60)

    # 导入安全模块
    try:
        from framework.security.config import SecurityConfig
        from framework.security.gateway import SecurityGateway
        from framework.security.sandbox import CodeSandbox
        from framework.security.firewall import NetworkFirewall
        print("[OK] 安全模块导入成功")
    except ImportError as e:
        print(f"[ERROR] 安全模块导入失败: {e}")
        return 1

    # 初始化配置
    config = SecurityConfig()
    print(f"\n[INFO] 本地IP: {config.get_local_ip()}")
    print(f"[INFO] 内网IP: {config.get_internal_ip()}")

    # 检查网络配置
    local_ip = config.get_local_ip()
    if config.is_allowed_network(local_ip):
        print(f"[OK] 本地IP {local_ip} 在允许网段内")
    else:
        print(f"[WARN] 本地IP {local_ip} 不在默认允许网段")
        print("[INFO] 允许的网段: {0}".format(", ".join(config.network.allowed_networks)))

    # 初始化组件
    gateway = SecurityGateway(config)
    sandbox = CodeSandbox(config)
    firewall = NetworkFirewall(config)

    print(f"\n[INFO] API网关已初始化")
    print(f"[INFO] 代码沙箱已初始化")
    print(f"[INFO] 网络防火墙已初始化 (规则数: {len(firewall.rules)})")

    # 显示防火墙规则
    print("\n" + "-" * 60)
    print("当前防火墙规则:")
    print("-" * 60)
    for rule in firewall.get_rules():
        icon = "✓" if rule['action'] == 'allow' else "✗"
        print(f"  {icon} {rule['rule_id']}: {rule['action']} {rule['source']}" +
              (f" port {rule['port']}" if rule['port'] else "") +
              f" - {rule['description']}")

    print("\n" + "=" * 60)
    print("安全系统初始化完成")
    print("=" * 60)

    return 0

if __name__ == "__main__":
    sys.exit(main())
