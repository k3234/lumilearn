# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — 外部 MCP 服务器接入管理（P1-5）

实现 Agent 通过 MCP（Model Context Protocol）接入外部工具/服务的统一入口：

  - ExternalMCPServerConfig : 外部 MCP 服务器配置数据模型
  - ExternalMCPRegistry     : 配置注册表 + 连接池 + 工具调用
      * 配置持久化于 framework.database.agent_mcp_configs 表
      * http → connect_http(url)，stdio → connect_stdio(command, args)
      * 连接池 self._clients 以 threading.Lock 保护，按 server_name 复用连接
      * list_tools / call_tool 任何异常返回 {"isError": True, ...}，绝不抛异常

用法：
    from agent_core.mcp_external import get_external_mcp_registry

    reg = get_external_mcp_registry()
    tools = reg.list_tools("my_server")
    result = reg.call_tool("my_server", "some_tool", {"arg": 1})
"""

from __future__ import annotations

import os
import sys
import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# 确保直接运行脚本时能导入 agent_core / framework 子模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.mcp_client import MCPClient

logger = logging.getLogger("lumilearn.agent.mcp_external")


@dataclass
class ExternalMCPServerConfig:
    """外部 MCP 服务器配置（与 agent_mcp_configs 表字段对应）"""
    server_name: str
    transport: str = "http"
    url: str = ""
    command: str = ""
    args: List[str] = field(default_factory=list)
    enabled: bool = True
    description: str = ""


def _error_response(message: str) -> Dict:
    """统一的 MCP 失败返回格式（降级原则：绝不抛异常）"""
    return {
        "isError": True,
        "content": [{"type": "text", "text": message}],
    }


class ExternalMCPRegistry:
    """
    外部 MCP 服务器注册表。

    配置通过 framework.database 持久化；运行时维护 server_name → MCPClient
    连接池，支持按需连接、断开、工具枚举与调用。
    """

    def __init__(self):
        from framework.database import db
        self._db = db
        self._clients: Dict[str, MCPClient] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------
    # 配置管理
    # ------------------------------------------------------------
    def list_servers(self) -> List[ExternalMCPServerConfig]:
        """列出全部外部 MCP 服务器配置"""
        return [self._to_config(row) for row in self._db.list_mcp_servers()]

    def get_server(self, server_name: str) -> Optional[ExternalMCPServerConfig]:
        """按名称获取外部 MCP 服务器配置"""
        row = self._db.get_mcp_server(server_name)
        return self._to_config(row) if row else None

    def add_server(self, config: ExternalMCPServerConfig) -> Dict:
        """新增配置；同名已存在时返回 {"error": ...}"""
        if self._db.get_mcp_server(config.server_name):
            return {"error": f"MCP Server '{config.server_name}' 已存在"}
        self._db.add_mcp_server(
            server_name=config.server_name,
            transport=config.transport,
            url=config.url,
            command=config.command,
            args=config.args,
            enabled=1 if config.enabled else 0,
            description=config.description,
        )
        return {"success": True,
                "server": self._db.get_mcp_server(config.server_name)}

    def update_server(self, server_name: str, **fields) -> bool:
        """更新配置（仅更新传入字段，args 为 list 时自动序列化）"""
        return self._db.update_mcp_server(server_name, **fields)

    def delete_server(self, server_name: str) -> bool:
        """删除配置并断开已建立的连接"""
        self.disconnect_server(server_name)
        return self._db.delete_mcp_server(server_name)

    # ------------------------------------------------------------
    # 连接池
    # ------------------------------------------------------------
    def connect_server(self, server_name: str, timeout: float = 30.0) -> MCPClient:
        """
        建立/复用连接：http → connect_http(url)，stdio → connect_stdio(command, args)。
        连接失败时记录日志并返回 {"error": ...}（不抛出异常）。
        """
        with self._lock:
            client = self._clients.get(server_name)
            if client is not None:
                return client
            config = self._db.get_mcp_server(server_name)
            if config is None:
                logger.error("MCP server 未配置: %s", server_name)
                return {"error": f"MCP server 未配置: {server_name}"}
            client = MCPClient(name=server_name)
            try:
                if config["transport"] == "http":
                    client.connect_http(config.get("url") or "", timeout)
                else:
                    client.connect_stdio(config.get("command") or "",
                                         config.get("args") or [])
            except Exception as e:
                logger.error("连接 MCP server '%s' 失败: %s", server_name, e)
                return {"error": f"连接 MCP server '{server_name}' 失败: {e}"}
            self._clients[server_name] = client
            return client

    def disconnect_server(self, server_name: str) -> None:
        """断开指定外部 MCP 服务器连接"""
        with self._lock:
            client = self._clients.pop(server_name, None)
        if client is not None:
            try:
                client.close()
            except Exception as e:
                logger.warning("关闭 MCP server '%s' 连接失败: %s", server_name, e)

    def disconnect_all(self) -> None:
        """断开全部连接（reset 用）"""
        with self._lock:
            names = list(self._clients.keys())
        for name in names:
            self.disconnect_server(name)

    def _ensure_connected(self, server_name: str, timeout: float) -> Optional[MCPClient]:
        """获取已连接客户端；未连接则尝试连接，失败返回 None"""
        client = self._clients.get(server_name)
        if client is not None:
            return client
        result = self.connect_server(server_name, timeout)
        return result if isinstance(result, MCPClient) else None

    # ------------------------------------------------------------
    # 工具枚举与调用（降级原则：任何异常返回 {"isError": True, ...}）
    # ------------------------------------------------------------
    def list_tools(self, server_name: str, timeout: float = 30.0) -> List[Dict]:
        """列出指定服务器的可用工具"""
        try:
            client = self._ensure_connected(server_name, timeout)
            if client is None:
                return _error_response(f"MCP 调用失败: 连接 server '{server_name}' 失败")
            return client.list_tools(timeout)
        except Exception as e:
            logger.error("列出 MCP server '%s' 工具失败: %s", server_name, e)
            return _error_response(f"MCP 调用失败: {e}")

    def call_tool(self, server_name: str, tool_name: str,
                  arguments: Optional[Dict] = None) -> Dict:
        """在指定服务器上调用工具"""
        try:
            client = self._ensure_connected(server_name, timeout=30.0)
            if client is None:
                return _error_response(f"MCP 调用失败: 连接 server '{server_name}' 失败")
            return client.call_tool(tool_name, arguments or {})
        except Exception as e:
            logger.error("调用 MCP server '%s' 工具 '%s' 失败: %s",
                         server_name, tool_name, e)
            return _error_response(f"MCP 调用失败: {e}")

    def call_tool_by_name(self, tool_name: str,
                          arguments: Optional[Dict] = None) -> Dict:
        """遍历已启用 servers 依次尝试，第一个成功即返回"""
        last_error: Optional[Dict] = None
        for config in self.list_servers():
            if not config.enabled:
                continue
            result = self.call_tool(config.server_name, tool_name, arguments)
            if not result.get("isError"):
                return result
            last_error = result
        return last_error or _error_response(
            f"MCP 调用失败: 所有已启用 server 均未提供工具 '{tool_name}'")

    def get_status(self) -> List[Dict]:
        """返回各服务器的连接状态与工具数概览"""
        statuses: List[Dict] = []
        for config in self.list_servers():
            entry = {
                "server_name": config.server_name,
                "transport": config.transport,
                "enabled": config.enabled,
                "reachable": False,
                "tools_count": 0,
                "error": "",
            }
            if config.enabled:
                result = self.list_tools(config.server_name)
                if isinstance(result, dict):
                    content = result.get("content") or []
                    entry["error"] = "".join(
                        item.get("text", "") for item in content
                        if isinstance(item, dict)
                    ) or str(result.get("error", ""))
                else:
                    entry["reachable"] = True
                    entry["tools_count"] = len(result)
            statuses.append(entry)
        return statuses

    # ------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------
    @staticmethod
    def _to_config(row: Dict) -> ExternalMCPServerConfig:
        """数据库行 → ExternalMCPServerConfig"""
        return ExternalMCPServerConfig(
            server_name=row.get("server_name", ""),
            transport=row.get("transport", "http"),
            url=row.get("url", ""),
            command=row.get("command", ""),
            args=list(row.get("args") or []),
            enabled=bool(row.get("enabled", 1)),
            description=row.get("description", ""),
        )


# ================================================================
# 单例
# ================================================================
_registry: Optional[ExternalMCPRegistry] = None


def get_external_mcp_registry() -> ExternalMCPRegistry:
    """获取外部 MCP 注册表单例（懒加载）"""
    global _registry
    if _registry is None:
        _registry = ExternalMCPRegistry()
    return _registry


def reset_external_mcp_registry():
    """重置外部 MCP 注册表单例（测试用：关闭所有连接并置 None）"""
    global _registry
    if _registry is not None:
        _registry.disconnect_all()
        _registry = None
