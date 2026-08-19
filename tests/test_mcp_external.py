# -*- coding: utf-8 -*-
"""
LumiLearn — P1-5 外部 MCP 服务器接入测试

覆盖 agent_core.mcp_external 的完整链路：
  - 配置 CRUD（add / list / update / delete，重名拒绝）
  - HTTP 传输端到端（连接本地 MCPServer，枚举/调用内置工具）
  - stdio 传输端到端（子进程 MCP Server，握手 + echo 工具）
  - 不可达 server 的降级行为（isError 返回，不抛异常）
  - enabled 开关在 get_status / list_servers 中的反映

每个用例使用唯一 server_name（test_ 前缀），并在测试中清理：
  - 连接清理：reset_external_mcp_registry()（teardown）
  - 数据库记录清理：db.delete_mcp_server(name)
"""

import os
import sys
import tempfile

import pytest

from agent_core.mcp_client import MCPClient, MCPServer
from agent_core.mcp_external import (
    ExternalMCPServerConfig,
    get_external_mcp_registry,
    reset_external_mcp_registry,
)
from framework.database import db


@pytest.fixture
def mcp_env():
    """每个测试独立的 registry；teardown 时断开全部连接并重置单例"""
    reg = get_external_mcp_registry()
    yield reg
    reset_external_mcp_registry()


# stdio 子进程 MCP Server 脚本：纯标准库，实现 initialize / tools/list / tools/call(echo)
STDIO_ECHO_SERVER = r'''# -*- coding: utf-8 -*-
"""极简 stdio MCP Server（echo）：用于 P1-5 外部接入测试"""
import json
import sys


def _reconfigure():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _send(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    _reconfigure()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        method = msg.get("method")
        msg_id = msg.get("id")
        if method == "initialize":
            _send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "echo-stdio-server", "version": "1.0.0"},
                },
            })
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            _send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {"tools": [{
                    "name": "echo",
                    "description": "回显输入文本",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                }]},
            })
        elif method == "tools/call":
            params = msg.get("params", {})
            args = params.get("arguments", {})
            text = str(args.get("text", ""))
            _send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": text}],
                    "isError": False,
                },
            })
        else:
            _send({
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32601, "message": "unsupported method"},
            })


if __name__ == "__main__":
    main()
'''


# ================================================================
# 1. 配置 CRUD
# ================================================================
def test_crud_add_list_update_delete(mcp_env):
    reg = mcp_env
    name = "test_crud_http_server"
    try:
        result = reg.add_server(ExternalMCPServerConfig(
            server_name=name, transport="http",
            url="http://127.0.0.1:9000/mcp", enabled=True,
            description="crud test"))
        assert "error" not in result
        names = [s.server_name for s in reg.list_servers()]
        assert name in names

        assert reg.update_server(name, url="http://127.0.0.1:9001/mcp") is True
        cfg = reg.get_server(name)
        assert cfg is not None
        assert cfg.url == "http://127.0.0.1:9001/mcp"

        assert reg.delete_server(name) is True
        names = [s.server_name for s in reg.list_servers()]
        assert name not in names
        assert reg.get_server(name) is None
    finally:
        db.delete_mcp_server(name)


# ================================================================
# 2. 重名拒绝
# ================================================================
def test_add_duplicate_rejected(mcp_env):
    reg = mcp_env
    name = "test_dup_http_server"
    cfg = ExternalMCPServerConfig(
        server_name=name, transport="http", url="http://127.0.0.1:9002/mcp")
    try:
        first = reg.add_server(cfg)
        assert "error" not in first
        second = reg.add_server(cfg)
        assert "error" in second
        assert name in second["error"]
    finally:
        db.delete_mcp_server(name)


# ================================================================
# 3. HTTP 传输端到端
# ================================================================
def test_http_end_to_end(mcp_env):
    reg = mcp_env
    name = "test_http_e2e_server"
    server = MCPServer(port=0)
    server.start()
    try:
        reg.add_server(ExternalMCPServerConfig(
            server_name=name, transport="http", url=server.url, enabled=True))
        client = reg.connect_server(name)
        assert isinstance(client, MCPClient)

        tools = reg.list_tools(name)
        assert isinstance(tools, list)
        tool_names = {t.get("name") for t in tools}
        assert {"generate_question", "knowledge_retrieval", "render_chart"} <= tool_names

        result = reg.call_tool(name, "generate_question", {"topic": "函数"})
        assert result.get("isError") is False
        assert "函数" in result.get("text", "")
    finally:
        server.stop()
        db.delete_mcp_server(name)


# ================================================================
# 4. stdio 传输端到端
# ================================================================
def test_stdio_end_to_end(mcp_env):
    reg = mcp_env
    name = "test_stdio_echo_server"
    fd, script_path = tempfile.mkstemp(
        suffix=".py", prefix="mcp_stdio_server_", dir=tempfile.gettempdir())
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(STDIO_ECHO_SERVER)
    try:
        reg.add_server(ExternalMCPServerConfig(
            server_name=name, transport="stdio",
            command=sys.executable, args=[script_path], enabled=True))

        client = reg.connect_server(name)
        assert isinstance(client, MCPClient)

        tools = reg.list_tools(name)
        assert isinstance(tools, list)
        assert "echo" in [t.get("name") for t in tools]

        result = reg.call_tool(name, "echo", {"text": "你好，MCP stdio"})
        assert result.get("isError") is False
        assert result.get("text") == "你好，MCP stdio"
    finally:
        os.unlink(script_path)
        db.delete_mcp_server(name)


# ================================================================
# 5. 不可达 server 降级
# ================================================================
def test_unreachable_server_degraded(mcp_env):
    reg = mcp_env
    name = "test_unreachable_http_server"
    try:
        reg.add_server(ExternalMCPServerConfig(
            server_name=name, transport="http",
            url="http://127.0.0.1:1/mcp", enabled=True))

        tools_result = reg.list_tools(name)
        assert isinstance(tools_result, dict)
        assert tools_result.get("isError") is True

        call_result = reg.call_tool(name, "any_tool", {"x": 1})
        assert isinstance(call_result, dict)
        assert call_result.get("isError") is True

        statuses = reg.get_status()
        entry = next(s for s in statuses if s["server_name"] == name)
        assert entry["reachable"] is False
    finally:
        db.delete_mcp_server(name)


# ================================================================
# 6. enabled 开关反映
# ================================================================
def test_toggle_enabled_reflected(mcp_env):
    reg = mcp_env
    name = "test_toggle_http_server"
    try:
        reg.add_server(ExternalMCPServerConfig(
            server_name=name, transport="http",
            url="http://127.0.0.1:1/mcp", enabled=True))

        statuses = reg.get_status()
        entry = next(s for s in statuses if s["server_name"] == name)
        assert entry["enabled"] is True

        assert reg.update_server(name, enabled=0) is True

        cfg = reg.get_server(name)
        assert cfg is not None
        assert cfg.enabled is False

        servers = reg.list_servers()
        entry_cfg = next(s for s in servers if s.server_name == name)
        assert entry_cfg.enabled is False

        statuses = reg.get_status()
        entry = next(s for s in statuses if s["server_name"] == name)
        assert entry["enabled"] is False
        assert entry["reachable"] is False
        assert entry["error"] == ""
    finally:
        db.delete_mcp_server(name)
