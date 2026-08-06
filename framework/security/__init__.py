# -*- coding: utf-8 -*-
"""
LumiLearn 安全系统
- 内网IP自动检测
- API网关
- 沙箱系统
- 防火墙规则

注意：直接导入子模块以避免framework/__init__.py的tokenizers依赖
"""

# 直接导入，绕过框架主初始化（避免加载tokenizer等重型依赖）
from .config import SecurityConfig, NetworkConfig, GatewayConfig, SandboxConfig
from .gateway import SecurityGateway, get_gateway, reset_gateway
from .sandbox import CodeSandbox, get_sandbox, reset_sandbox
from .firewall import NetworkFirewall, get_firewall, reset_firewall

__all__ = [
    'SecurityGateway',
    'CodeSandbox',
    'NetworkFirewall',
    'SecurityConfig',
    'NetworkConfig',
    'GatewayConfig',
    'SandboxConfig',
    'get_security_config',
    'get_gateway',
    'get_sandbox',
    'get_firewall',
    'reset_gateway',
    'reset_sandbox',
    'reset_firewall',
]


def get_security_config():
    """获取安全配置"""
    return SecurityConfig()


# 全局实例（懒加载，避免启动时依赖问题）
_gateway = None
_sandbox = None
_firewall = None


def init_security():
    """初始化安全组件（在Flask应用启动时调用）"""
    global _gateway, _sandbox, _firewall
    if _gateway is None:
        _gateway = SecurityGateway(SecurityConfig())
    if _sandbox is None:
        _sandbox = CodeSandbox(SecurityConfig())
    if _firewall is None:
        _firewall = NetworkFirewall(SecurityConfig())
    return _gateway, _sandbox, _firewall
