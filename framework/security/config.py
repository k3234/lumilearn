# -*- coding: utf-8 -*-
"""
LumiLearn 安全配置
"""
import os
import socket
import ipaddress
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class NetworkConfig:
    """网络配置"""
    # 内网IP段
    allowed_networks: List[str] = field(default_factory=lambda: [
        "192.168.0.0/16",   # 私有网络A
        "10.0.0.0/8",      # 私有网络B
        "172.16.0.0/12",   # 私有网络C
    ])

    # 禁止的IP
    blocked_ips: List[str] = field(default_factory=list)

    # 信任的网关
    trusted_gateways: List[str] = field(default_factory=lambda: [
        "192.168.1.1",
        "192.168.0.1",
        "10.0.0.1",
    ])

    # 网络超时
    connection_timeout: int = 30
    request_timeout: int = 60


@dataclass
class GatewayConfig:
    """API网关配置"""
    enabled: bool = True
    rate_limit: int = 100  # 每秒请求数
    window: int = 60  # 时间窗口（秒）
    burst_limit: int = 50  # 突发限制
    max_body_size: int = 10 * 1024 * 1024  # 10MB
    allowed_methods: List[str] = field(default_factory=lambda: [
        "GET", "POST", "PUT", "DELETE", "OPTIONS"
    ])
    allowed_headers: List[str] = field(default_factory=lambda: [
        "Content-Type",
        "Authorization",
        "X-Request-ID",
        "X-API-Key",
    ])
    cors_enabled: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_methods: List[str] = field(default_factory=lambda: [
        "GET", "POST", "PUT", "DELETE", "OPTIONS"
    ])
    cors_headers: List[str] = field(default_factory=lambda: [
        "Content-Type",
        "Authorization",
    ])


@dataclass
class SandboxConfig:
    """沙箱配置"""
    enabled: bool = True
    max_execution_time: int = 30  # 秒
    max_memory_mb: int = 512  # MB
    max_cpu_percent: int = 80  # CPU使用率上限
    allowed_modules: List[str] = field(default_factory=lambda: [
        "math",
        "random",
        "datetime",
        "collections",
        "functools",
        "itertools",
        "operator",
        "string",
        "re",
        "json",
        "os.path",
    ])
    blocked_modules: List[str] = field(default_factory=lambda: [
        "os",
        "subprocess",
        "sys",
        "importlib",
        "socket",
        "http",
        "urllib",
        "requests",
        "ctypes",
        "pickle",
        "shutil",
        "tempfile",
    ])
    isolated_paths: List[str] = field(default_factory=lambda: [
        "/etc",
        "/var",
        "/usr",
        "/bin",
        "/sbin",
        "/proc",
        "/dev",
    ])
    output_limits: Dict[str, int] = field(default_factory=lambda: {
        "stdout": 1024 * 1024,  # 1MB
        "stderr": 1024 * 1024,  # 1MB
    })


@dataclass
class SecurityConfig:
    """安全配置总览"""
    network: NetworkConfig = field(default_factory=NetworkConfig)
    gateway: GatewayConfig = field(default_factory=GatewayConfig)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)

    # API认证
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"

    # 日志
    log_level: str = "INFO"
    log_file: str = "./logs/security.log"

    def get_local_ip(self) -> str:
        """获取本机IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def get_internal_ip(self) -> str:
        """获取内网IP地址"""
        try:
            import netifaces  # type: ignore
            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr['addr']
                        if self._is_private_ip(ip):
                            return ip
        except ImportError:
            pass
        except Exception:
            pass
        return self.get_local_ip()

    def _is_private_ip(self, ip: str) -> bool:
        """检查是否为私有IP"""
        try:
            return ipaddress.ip_address(ip).is_private
        except:
            return False

    def is_allowed_network(self, ip: str) -> bool:
        """检查IP是否在允许的网段"""
        try:
            addr = ipaddress.ip_address(ip)
            for network in self.network.allowed_networks:
                if addr in ipaddress.ip_network(network):
                    return True
            return False
        except:
            return False

    def is_blocked_ip(self, ip: str) -> bool:
        """检查IP是否被禁止"""
        return ip in self.network.blocked_ips
