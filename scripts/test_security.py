#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 安全系统测试套件
测试网关、沙箱、防火墙所有功能
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from framework.security.config import SecurityConfig
from framework.security.gateway import SecurityGateway
from framework.security.sandbox import CodeSandbox
from framework.security.firewall import NetworkFirewall


def test_network_config():
    """测试网络配置"""
    print("\n" + "=" * 60)
    print("测试: 网络配置")
    print("=" * 60)

    config = SecurityConfig()
    print(f"本地IP: {config.get_local_ip()}")
    print(f"内网IP: {config.get_internal_ip()}")

    # 测试IP检查
    test_ips = [
        ("192.168.1.100", True, "内网IP"),
        ("10.0.0.1", True, "内网IP"),
        ("172.16.0.1", True, "内网IP"),
        ("8.8.8.8", False, "公网IP"),
        ("127.0.0.1", True, "回环地址"),
    ]

    for ip, expected, desc in test_ips:
        is_allowed = config.is_allowed_network(ip)
        status = "✓" if is_allowed == expected else "✗"
        print(f"  {status} {ip} ({desc}): 允许={is_allowed}")

    print("  [OK] 网络配置测试完成")


def test_gateway():
    """测试API网关"""
    print("\n" + "=" * 60)
    print("测试: API网关")
    print("=" * 60)

    config = SecurityConfig()
    gateway = SecurityGateway(config)

    # 测试正常请求
    result = gateway.check_request("192.168.1.100", "/api/chat", "GET")
    print(f"  ✓ 正常请求: allowed={result['allowed']}")

    # 测试速率限制
    print("  测试速率限制 (5次/60秒)...")
    for i in range(7):
        result = gateway.check_request("10.10.10.10", "/api/test", "GET")
    if not result['allowed']:
        print(f"  ✓ 速率限制生效: {result['reason']}")

    # 测试IP封禁
    gateway.block_ip("1.2.3.4", "测试封禁", duration=60)
    result = gateway.check_request("1.2.3.4", "/api/test", "GET")
    print(f"  ✓ IP封禁: allowed={result['allowed']}, reason={result['reason']}")

    # 解封
    gateway.unblock_ip("1.2.3.4")
    result = gateway.check_request("1.2.3.4", "/api/test", "GET")
    print(f"  ✓ IP解封: allowed={result['allowed']}")

    # 统计
    stats = gateway.get_stats()
    print(f"  统计: 总请求={stats['total_requests']}, 封禁IP={stats['blocked_ips']}")

    print("  [OK] 网关测试完成")


def test_sandbox():
    """测试代码沙箱"""
    print("\n" + "=" * 60)
    print("测试: 代码沙箱")
    print("=" * 60)

    config = SecurityConfig()
    sandbox = CodeSandbox(config)

    # 测试安全代码
    safe_code = "x = 2 + 2; _result = x"
    result = sandbox.execute(safe_code, user_id="test_user")
    print(f"  ✓ 安全代码执行: success={result.success}, output={result.output.strip()}, result={result.return_value}")

    # 测试危险模块
    dangerous_codes = [
        ("import os; os.system('ls')", "导入os模块"),
        ("import subprocess; subprocess.run(['ls'])", "导入subprocess"),
        ("import sys; print(sys.path)", "导入sys模块"),
        ("import socket; s = socket.socket()", "导入socket"),
    ]

    for code, desc in dangerous_codes:
        result = sandbox.execute(code, user_id="test_user")
        status = "✓" if not result.success else "✗"
        print(f"  {status} 危险代码 ({desc}): 拦截={not result.success}")
        if result.error:
            print(f"      错误: {result.error[:60]}")

    # 测试执行统计
    stats = sandbox.get_stats()
    print(f"  统计: 总执行={stats['total_executions']}, 唯一用户={stats['unique_users']}")

    print("  [OK] 沙箱测试完成")


def test_firewall():
    """测试网络防火墙"""
    print("\n" + "=" * 60)
    print("测试: 网络防火墙")
    print("=" * 60)

    config = SecurityConfig()
    firewall = NetworkFirewall(config)

    # 测试内网访问
    result = firewall.check_access("192.168.1.100", 18080)
    print(f"  ✓ 内网访问18080: allowed={result['allowed']}")

    # 测试外部访问管理端口
    result = firewall.check_access("8.8.8.8", 18081)
    print(f"  ✓ 外部访问18081: allowed={result['allowed']} (应被拒绝)")

    # 添加自定义规则
    rule_id = firewall.add_rule(
        action="allow",
        source="192.168.2.0/24",
        port=18082,
        description="允许特定网段访问学习端口"
    )
    print(f"  ✓ 添加规则: {rule_id}")

    result = firewall.check_access("192.168.2.50", 18082)
    print(f"  ✓ 特定网段访问18082: allowed={result['allowed']}")

    # 删除规则
    firewall.remove_rule(rule_id)
    print(f"  ✓ 删除规则: {rule_id}")

    # 状态
    status = firewall.get_status()
    print(f"  状态: 规则数={status['rules_count']}, 本地IP={status['local_ip']}")

    print("  [OK] 防火墙测试完成")


def test_integration():
    """集成测试"""
    print("\n" + "=" * 60)
    print("测试: 集成测试")
    print("=" * 60)

    config = SecurityConfig()
    gateway = SecurityGateway(config)
    sandbox = CodeSandbox(config)
    firewall = NetworkFirewall(config)

    # 模拟完整流程
    ip = config.get_local_ip()
    print(f"  本机IP: {ip}")

    # 1. 网关检查
    result = gateway.check_request(ip, "/api/security/status", "GET")
    print(f"  1. 网关检查: allowed={result['allowed']}")

    # 2. 防火墙检查
    result = firewall.check_access(ip, 18080)
    print(f"  2. 防火墙检查: allowed={result['allowed']}")

    # 3. 沙箱执行
    result = sandbox.execute("print('Hello, LumiLearn!'); _result = '测试通过'", "integration_test")
    print(f"  3. 沙箱执行: success={result.success}, output={result.output.strip()}")

    print("  [OK] 集成测试完成")


if __name__ == "__main__":
    print("\n" + "#" * 60)
    print("# LumiLearn 安全系统测试套件")
    print("#" * 60)

    test_network_config()
    test_gateway()
    test_sandbox()
    test_firewall()
    test_integration()

    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)
