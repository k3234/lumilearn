# -*- coding: utf-8 -*-
"""
LumiLearn 网络防火墙
管理内网IP和访问规则
"""
import ipaddress
import logging
import platform
import subprocess
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import threading

logger = logging.getLogger(__name__)


@dataclass
class FirewallRule:
    """防火墙规则"""
    rule_id: str
    action: str  # "allow" or "deny"
    source: str  # IP or CIDR
    destination: str = "any"
    port: Optional[int] = None
    protocol: str = "tcp"
    description: str = ""
    enabled: bool = True


class NetworkFirewall:
    """网络防火墙"""

    def __init__(self, config):
        self.config = config
        self.rules: List[FirewallRule] = []
        self._lock = threading.Lock()
        self._rule_counter = 0

        # 初始化默认规则
        self._init_default_rules()

    def _init_default_rules(self):
        """初始化默认规则"""
        # 允许内网访问
        for network in self.config.network.allowed_networks:
            self.add_rule(
                action="allow",
                source=network,
                description=f"允许内网网络: {network}"
            )

        # 禁止访问管理端口
        self.add_rule(
            action="deny",
            source="0.0.0.0/0",
            port=18081,
            description="禁止外部访问管理端口"
        )

        # 禁止访问模型管理端口
        self.add_rule(
            action="deny",
            source="0.0.0.0/0",
            port=18082,
            description="禁止外部访问模型管理端口"
        )

        logger.info(f"已初始化 {len(self.rules)} 条防火墙规则")

    def add_rule(self, action: str, source: str, port: int = None,
                 description: str = "") -> str:
        """添加防火墙规则"""
        with self._lock:
            self._rule_counter += 1
            rule_id = f"rule_{self._rule_counter:04d}"

            rule = FirewallRule(
                rule_id=rule_id,
                action=action.lower(),
                source=source,
                port=port,
                description=description,
                enabled=True
            )

            self.rules.append(rule)
            logger.info(f"添加规则: {rule_id} - {action} {source}" +
                       (f" port {port}" if port else "") +
                       f" ({description})")

            return rule_id

    def remove_rule(self, rule_id: str) -> bool:
        """移除防火墙规则"""
        with self._lock:
            for i, rule in enumerate(self.rules):
                if rule.rule_id == rule_id:
                    self.rules.pop(i)
                    logger.info(f"移除规则: {rule_id}")
                    return True
            return False

    def check_access(self, source_ip: str, dest_port: int) -> dict:
        """
        检查访问是否允许

        返回:
            {
                "allowed": bool,
                "rule_id": str,
                "action": str,
                "message": str
            }
        """
        with self._lock:
            for rule in reversed(self.rules):
                if not rule.enabled:
                    continue

                if rule.port and rule.port != dest_port:
                    continue

                if self._ip_matches(source_ip, rule.source):
                    return {
                        "allowed": rule.action == "allow",
                        "rule_id": rule.rule_id,
                        "action": rule.action,
                        "message": f"匹配规则 {rule.rule_id}: {rule.description}"
                    }

            # 默认拒绝
            return {
                "allowed": False,
                "rule_id": "default_deny",
                "action": "deny",
                "message": "默认拒绝规则"
            }

    def get_local_ip(self) -> str:
        """获取本机IP"""
        return self.config.get_local_ip()

    def get_internal_ip(self) -> str:
        """获取内网IP"""
        return self.config.get_internal_ip()

    def is_internal_ip(self, ip: str) -> bool:
        """检查是否为内网IP"""
        try:
            addr = ipaddress.ip_address(ip)
            return addr.is_private
        except:
            return False

    def _ip_matches(self, ip: str, pattern: str) -> bool:
        """检查IP是否匹配规则"""
        try:
            # 如果是CIDR表示法
            if '/' in pattern:
                return ipaddress.ip_address(ip) in ipaddress.ip_network(pattern)
            else:
                # 精确匹配
                return ip == pattern
        except:
            return False

    def get_rules(self) -> List[dict]:
        """获取所有规则"""
        with self._lock:
            return [
                {
                    "rule_id": r.rule_id,
                    "action": r.action,
                    "source": r.source,
                    "port": r.port,
                    "description": r.description,
                    "enabled": r.enabled
                }
                for r in self.rules
            ]

    def apply_system_firewall(self):
        """
        尝试应用系统级防火墙规则
        注意：需要root权限
        """
        if platform.system() == "Windows":
            self._apply_windows_firewall()
        elif platform.system() == "Linux":
            self._apply_linux_firewall()
        else:
            logger.warning(f"不支持的系统: {platform.system()}")

    def _apply_windows_firewall(self):
        """应用Windows防火墙规则"""
        try:
            # 允许内网访问
            for network in self.config.network.allowed_networks:
                cmd = [
                    "netsh", "advfirewall", "firewall", "add", "rule",
                    f"name=LumiLearn-Allow-{network.replace('.', '-')}",
                    f"dir=in", "action=allow", "network={network}",
                    "protocol=tcp", "localport=18080"
                ]
                subprocess.run(cmd, capture_output=True, check=False)
                logger.info(f"Windows防火墙规则已添加: 允许 {network}")

            logger.info("Windows防火墙规则已应用")
        except Exception as e:
            logger.error(f"应用Windows防火墙规则失败: {e}")
            logger.warning("请手动配置Windows防火墙规则")

    def _apply_linux_firewall(self):
        """应用Linux防火墙规则"""
        try:
            # 检查iptables是否存在
            result = subprocess.run(
                ["which", "iptables"],
                capture_output=True,
                check=False
            )
            if result.returncode != 0:
                logger.warning("未检测到iptables，尝试使用ufw")
                self._apply_ufw_rules()
                return

            # 允许内网访问
            for network in self.config.network.allowed_networks:
                cmd = [
                    "sudo", "iptables", "-A", "INPUT",
                    "-s", network, "-p", "tcp", "--dport", "18080",
                    "-j", "ACCEPT"
                ]
                subprocess.run(cmd, capture_output=True, check=False)
                logger.info(f"Linux防火墙规则已添加: 允许 {network}")

            # 拒绝其他访问
            cmd = [
                "sudo", "iptables", "-A", "INPUT",
                "-p", "tcp", "--dport", "18080",
                "-j", "REJECT"
            ]
            subprocess.run(cmd, capture_output=True, check=False)
            logger.info("Linux防火墙规则已应用")

        except Exception as e:
            logger.error(f"应用Linux防火墙规则失败: {e}")
            logger.warning("请手动配置防火墙规则")

    def _apply_ufw_rules(self):
        """应用UFW防火墙规则"""
        try:
            # 检查ufw是否存在
            result = subprocess.run(
                ["which", "ufw"],
                capture_output=True,
                check=False
            )
            if result.returncode != 0:
                logger.warning("未检测到ufw")
                return

            # 允许内网访问
            for network in self.config.network.allowed_networks:
                cmd = [
                    "sudo", "ufw", "allow", "from", network,
                    "to", "any", "port", "18080", "proto", "tcp"
                ]
                subprocess.run(cmd, capture_output=True, check=False)
                logger.info(f"UFW规则已添加: 允许 {network}")

            logger.info("UFW防火墙规则已应用")

        except Exception as e:
            logger.error(f"应用UFW规则失败: {e}")

    def get_status(self) -> dict:
        """获取防火墙状态"""
        return {
            "rules_count": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules if r.enabled),
            "local_ip": self.get_local_ip(),
            "internal_ip": self.get_internal_ip(),
            "allowed_networks": self.config.network.allowed_networks,
            "blocked_ips": self.config.network.blocked_ips
        }


# 全局防火墙实例
_firewall_instance: Optional[NetworkFirewall] = None


def get_firewall(config=None):
    """获取全局防火墙实例"""
    global _firewall_instance
    if _firewall_instance is None:
        from .config import SecurityConfig
        cfg = config or SecurityConfig()
        _firewall_instance = NetworkFirewall(cfg)
    return _firewall_instance


def reset_firewall():
    """重置防火墙实例（用于测试）"""
    global _firewall_instance
    _firewall_instance = None
