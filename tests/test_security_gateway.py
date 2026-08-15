# -*- coding: utf-8 -*-
"""
tests/test_security_gateway.py
SecurityGateway 安全网关单元测试
覆盖：速率限制、IP封禁、请求日志、端点保护
"""
import sys, os
from unittest import mock
import pytest
from datetime import datetime, timedelta
from dataclasses import replace

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from framework.security.gateway import SecurityGateway, RateLimit, IPBlock, get_gateway, reset_gateway
from framework.security.config import SecurityConfig, GatewayConfig


@pytest.fixture
def gateway():
    """创建测试用的安全网关实例"""
    config = SecurityConfig(gateway=GatewayConfig(rate_limit=100, window=60))
    return SecurityGateway(config)


class TestRateLimit:
    """测试 RateLimit 数据类（数据模型，无行为）"""

    def test_rate_limit_creation(self):
        rl = RateLimit(requests=5, window=60)
        assert rl.requests == 5
        assert rl.window == 60

    def test_rate_limit_defaults(self):
        rl = RateLimit()
        assert rl.requests == 100
        assert rl.window == 60


class TestIPBlock:
    """测试 IPBlock 数据类（数据模型，无行为）"""

    def test_ip_block_creation(self):
        import time
        ib = IPBlock(ip="10.0.0.1", reason="suspicious", blocked_at=time.time())
        assert ib.ip == "10.0.0.1"
        assert ib.reason == "suspicious"
        assert ib.duration == 3600

    def test_ip_block_with_duration(self):
        import time
        ib = IPBlock(ip="10.0.0.2", reason="test", blocked_at=time.time(), duration=1800)
        assert ib.duration == 1800


class TestSecurityGateway:
    """测试 SecurityGateway 主类"""

    def test_check_request_allows_normal(self, gateway):
        result = gateway.check_request("192.168.1.1", "/api/health", "GET")
        assert result["allowed"] is True
        assert result["reason"] == ""

    def test_check_request_blocks_after_limit(self, gateway):
        """模拟超过速率限制"""
        # 创建低限制的网关
        low_config = SecurityConfig(gateway=GatewayConfig(rate_limit=3, window=60))
        low_gateway = SecurityGateway(low_config)
        for i in range(3):
            low_gateway.check_request("192.168.1.1", "/api/test", "GET")
        # 第4次应该被限制
        result = low_gateway.check_request("192.168.1.1", "/api/test", "GET")
        assert result["allowed"] is False
        assert result.get("reason") == "请求频率超限"

    def test_check_request_blocks_blocked_ip(self, gateway):
        gateway.block_ip("10.0.0.1", "test_block", 3600)
        result = gateway.check_request("10.0.0.1", "/api/test", "GET")
        assert result["allowed"] is False
        assert "封禁" in result.get("reason", "")

    def test_block_and_unblock_ip(self, gateway):
        gateway.block_ip("10.0.0.1", "suspicious", 3600)
        assert gateway.check_request("10.0.0.1", "/api/test", "GET")["allowed"] is False
        gateway.unblock_ip("10.0.0.1")
        assert gateway.check_request("10.0.0.1", "/api/test", "GET")["allowed"] is True

    def test_get_stats(self, gateway):
        gateway.check_request("127.0.0.1", "/api/test", "GET")
        stats = gateway.get_stats()
        assert "total_requests" in stats
        assert "blocked_ips" in stats
        assert stats["total_requests"] >= 1

    def test_get_request_log(self, gateway):
        gateway.check_request("127.0.0.1", "/api/test", "GET")
        logs = gateway.get_request_log(limit=10)
        assert isinstance(logs, list)
        if logs:
            assert "ip" in logs[0]
            assert "path" in logs[0]

    def test_protect_endpoint_requires_request_context(self):
        """测试装饰器在没有Flask请求上下文时正确报错"""
        config = SecurityConfig(gateway=GatewayConfig(rate_limit=100, window=60))
        gateway = SecurityGateway(config)

        @gateway.protect_endpoint(max_requests=5, window=60)
        def test_view():
            return "ok"

        # 无 Flask 请求上下文时应报错
        with pytest.raises(RuntimeError, match="request context"):
            test_view()

    @mock.patch("framework.security.gateway.request")
    def test_protect_endpoint_with_mock_request(self, mock_request):
        """测试装饰器在有请求上下文时正常工作"""
        config = SecurityConfig(gateway=GatewayConfig(rate_limit=100, window=60))
        gateway = SecurityGateway(config)

        @gateway.protect_endpoint(max_requests=5, window=60)
        def test_view():
            return "ok"

        # 需要 Flask 请求上下文
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/api/test'):
            result = test_view()
            assert result == "ok"


class TestGatewaySingleton:
    """测试 get_gateway 单例"""

    def test_get_gateway_returns_instance(self):
        reset_gateway()
        gw = get_gateway()
        assert gw is not None
        assert isinstance(gw, SecurityGateway)

    def test_reset_gateway(self):
        reset_gateway()
        gw = get_gateway()
        assert gw is not None
        reset_gateway()
        assert get_gateway() is not gw  # 重置后是不同实例


class TestSecurityIntegration:
    """集成测试：模拟完整请求流程"""

    def test_normal_request_flow(self, gateway):
        """正常请求应该通过"""
        result = gateway.check_request("192.168.1.100", "/api/learn", "POST")
        assert result["allowed"] is True
        assert "remaining_requests" in result

    def test_blocked_ip_flow(self, gateway):
        """被封禁的IP应该被拒绝"""
        gateway.block_ip("10.0.0.99", "brute_force", 3600)
        result = gateway.check_request("10.0.0.99", "/api/admin", "GET")
        assert result["allowed"] is False
        assert "封禁" in result.get("reason", "")

    def test_rate_limit_and_block_interaction(self):
        """速率限制触发后的IP封禁"""
        config = SecurityConfig(gateway=GatewayConfig(rate_limit=2, window=60))
        gw = SecurityGateway(config)
        # 超过限制后应该被封禁
        gw.check_request("10.0.0.5", "/api/test", "GET")
        gw.check_request("10.0.0.5", "/api/test", "GET")
        result = gw.check_request("10.0.0.5", "/api/test", "GET")
        assert result["allowed"] is False
        # 此时IP应该被临时封禁
        assert "10.0.0.5" in gw.blocked_ips


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
