# -*- coding: utf-8 -*-
"""
LumiLearn API安全网关
"""
import time
import uuid
import logging
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field
from functools import wraps
import threading

from framework.security.sanitize import mask_query_string

logger = logging.getLogger(__name__)


@dataclass
class RateLimit:
    """速率限制"""
    requests: int = 100
    window: int = 60  # 秒


@dataclass
class IPBlock:
    """IP封禁"""
    ip: str
    reason: str
    blocked_at: float
    duration: int = 3600  # 秒


class SecurityGateway:
    """API安全网关"""

    def __init__(self, config):
        self.config = config
        self.request_counts: Dict[str, list] = {}
        self.blocked_ips: Dict[str, IPBlock] = {}
        self.request_log: list = []
        self._lock = threading.Lock()
        self._request_counter = 0

    def check_request(self, ip: str, path: str, method: str = "GET") -> dict:
        """
        检查请求是否合法

        返回:
            {
                "allowed": bool,
                "reason": str,
                "remaining_requests": int,
                "reset_at": float
            }
        """
        result = {
            "allowed": True,
            "reason": "",
            "remaining_requests": self.config.gateway.rate_limit,
            "reset_at": time.time() + self.config.gateway.window
        }

        # 1. 检查IP是否被禁止
        if ip in self.blocked_ips:
            block = self.blocked_ips[ip]
            if time.time() - block.blocked_at < block.duration:
                result["allowed"] = False
                result["reason"] = f"IP被封禁: {block.reason}"
                logger.warning(f"请求被拒绝: IP={ip}, 原因={block.reason}")
                return result
            else:
                del self.blocked_ips[ip]

        # 2. 检查是否在允许的网段
        if not self.config.is_allowed_network(ip):
            result["allowed"] = False
            result["reason"] = "IP不在允许的网段内"
            self._block_ip(ip, "IP不在允许的网段", duration=300)
            return result

        # 3. 检查是否在禁止列表中
        if self.config.is_blocked_ip(ip):
            result["allowed"] = False
            result["reason"] = "IP在禁止列表中"
            return result

        # 4. 检查速率限制
        blocked = False
        with self._lock:
            current_time = time.time()
            if ip not in self.request_counts:
                self.request_counts[ip] = []

            # 清理过期请求
            self.request_counts[ip] = [
                t for t in self.request_counts[ip]
                if current_time - t < self.config.gateway.window
            ]

            # 检查是否超限
            if len(self.request_counts[ip]) >= self.config.gateway.rate_limit:
                result["allowed"] = False
                result["reason"] = "请求频率超限"
                blocked = True
            else:
                # 记录请求
                self.request_counts[ip].append(current_time)
                result["remaining_requests"] = self.config.gateway.rate_limit - len(self.request_counts[ip])

        # _block_ip 内部也加锁，必须在 with 块外调用，避免死锁
        if blocked:
            self._block_ip(ip, "请求频率超限", duration=60)

        # 5. 记录请求日志
        self._log_request(ip, path, method)

        return result

    def protect_endpoint(self, func=None, max_requests: int = 10, window: int = 60):
        """
        装饰器：保护API端点

        用法:
            @gateway.protect_endpoint  # 无参调用
            @gateway.protect_endpoint(max_requests=10, window=60)  # 有参调用
            def my_api():
                ...
        """
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                from flask import request
                ip = request.remote_addr

                result = self.check_request(ip, request.path, request.method)
                if not result["allowed"]:
                    from flask import jsonify
                    return jsonify({
                        "error": "请求被拒绝",
                        "reason": result["reason"],
                        "retry_after": result["reset_at"] - time.time()
                    }), 429

                return fn(*args, **kwargs)
            return wrapper

        if func is not None:
            # 无参调用: @gateway.protect_endpoint
            return decorator(func)
        # 有参调用: @gateway.protect_endpoint(max_requests=10)
        return decorator

    def block_ip(self, ip: str, reason: str, duration: int = 3600):
        """封禁IP"""
        self._block_ip(ip, reason, duration)

    def unblock_ip(self, ip: str):
        """解封IP"""
        with self._lock:
            if ip in self.blocked_ips:
                del self.blocked_ips[ip]
                logger.info(f"IP已解封: {ip}")

    def get_stats(self) -> dict:
        """获取网关统计信息"""
        return {
            "total_requests": self._request_counter,
            "blocked_ips": len(self.blocked_ips),
            "active_connections": len(self.request_counts),
            "rate_limit": self.config.gateway.rate_limit,
            "window": self.config.gateway.window
        }

    def _block_ip(self, ip: str, reason: str, duration: int = 3600):
        """内部封禁IP"""
        with self._lock:
            self.blocked_ips[ip] = IPBlock(
                ip=ip,
                reason=reason,
                blocked_at=time.time(),
                duration=duration
            )
        logger.warning(f"IP已封禁: {ip}, 原因: {reason}")

    def _log_request(self, ip: str, path: str, method: str):
        """记录请求日志（路径中的查询参数先脱敏，防止 token/key 落盘）"""
        with self._lock:
            self._request_counter += 1
            self.request_log.append({
                "timestamp": time.time(),
                "ip": ip,
                "path": mask_query_string(path),
                "method": method,
                "request_id": str(uuid.uuid4())
            })
            # 只保留最近1000条日志
            if len(self.request_log) > 1000:
                self.request_log = self.request_log[-1000:]

    def reset(self):
        """重置网关状态（用于测试）"""
        with self._lock:
            self.request_counts.clear()
            self.blocked_ips.clear()
            self.request_log.clear()
            self._request_counter = 0

    def get_request_log(self, limit: int = 100) -> list:
        """获取请求日志"""
        with self._lock:
            return self.request_log[-limit:]


# 全局网关实例
_gateway_instance: Optional[SecurityGateway] = None


def get_gateway(config=None):
    """获取全局网关实例"""
    global _gateway_instance
    if _gateway_instance is None:
        from .config import SecurityConfig
        cfg = config or SecurityConfig()
        _gateway_instance = SecurityGateway(cfg)
    return _gateway_instance


def reset_gateway():
    """重置网关实例（用于测试）"""
    global _gateway_instance
    _gateway_instance = None
