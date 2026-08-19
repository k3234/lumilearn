# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — MCP 客户端与教育工具集（Phase 4）

实现 MCP（Model Context Protocol）1.0 协议支持，满足 Roadmap Phase 4 交付物：

  - MCPClient        : JSON-RPC 2.0 客户端（stdio / HTTP 两种传输）
  - BuiltinToolRegistry : 预置教育工具集（知识库检索 / 题目生成 / 图表渲染）
  - MCPServer        : 极简本地 MCP Server（HTTP 传输），对外暴露注册工具

协议要点（MCP 1.0）：
  - 传输：stdio（JSON-RPC 2.0 over stdin/stdout）、HTTP（Streamable HTTP）
  - 方法：initialize / notifications/initialized / tools/list / tools/call
  - 消息格式：{"jsonrpc":"2.0","id":N,"method":"...","params":{...}}

零依赖策略：
  - stdio 传输使用标准库 subprocess
  - HTTP 传输优先 httpx（已安装），缺失时回退标准库 urllib
  - 本地 Server 使用标准库 http.server，无需额外安装
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
from typing import Any, Callable, Dict, List, Optional

# 确保直接运行脚本时能导入 agent_core / framework 子模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("lumilearn.agent.mcp")

# MCP 1.0 协议版本标识
MCP_PROTOCOL_VERSION = "2025-06-18"


# ================================================================
# JSON-RPC 2.0 消息工具
# ================================================================
def _make_request(method: str, params: Dict, msg_id: int) -> Dict:
    return {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}


def _make_notification(method: str, params: Dict) -> Dict:
    return {"jsonrpc": "2.0", "method": method, "params": params}


# ================================================================
# 传输层
# ================================================================
class _StdioTransport:
    """MCP stdio 传输：通过子进程 stdin/stdout 收发 JSON-RPC"""

    def __init__(self, command: str, args: Optional[List[str]] = None):
        self._proc = subprocess.Popen(
            [command] + (args or []),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self._lock = threading.Lock()
        self._read_lock = threading.Lock()
        self._closed = False

    def send(self, message: Dict) -> None:
        with self._lock:
            if self._closed:
                raise ConnectionError("MCP stdio 传输已关闭")
            line = json.dumps(message, ensure_ascii=False) + "\n"
            self._proc.stdin.write(line)
            self._proc.stdin.flush()

    def receive(self, timeout: float = 30.0) -> Dict:
        with self._read_lock:
            if self._closed:
                raise ConnectionError("MCP stdio 传输已关闭")
            line = self._proc.stdout.readline()
            if not line:
                raise ConnectionError("MCP server 已退出（stdout 关闭）")
            return json.loads(line)

    def close(self) -> None:
        self._closed = True
        try:
            self._proc.stdin.close()
            self._proc.terminate()
            self._proc.wait(timeout=5)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass


class _HttpTransport:
    """MCP Streamable HTTP 传输（POST JSON-RPC）"""

    def __init__(self, url: str, timeout: float = 30.0):
        self._url = url
        self._timeout = timeout

    def send(self, message: Dict) -> None:
        # HTTP 传输的 send/receive 合并为一次往返，send 仅记录待发送消息
        self._pending = message

    def close(self) -> None:
        """HTTP 传输无长连接，无需额外清理"""
        self._pending = None

    def receive(self, timeout: float = 30.0) -> Dict:
        message = getattr(self, "_pending", None)
        if message is None:
            raise ConnectionError("HTTP 传输需先 send")
        self._pending = None
        return self._http_post(message, timeout)

    def _http_post(self, message: Dict, timeout: float) -> Dict:
        payload = json.dumps(message, ensure_ascii=False)
        try:
            import httpx
            resp = httpx.post(
                self._url,
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
                timeout=timeout,
            )
            resp.raise_for_status()
        except ImportError:
            raise ConnectionError(
                "MCP HTTP 传输需要 httpx 库，请先 pip install httpx")
        except Exception as e:
            raise ConnectionError(f"MCP HTTP 请求失败: {e}")

        content_type = resp.headers.get("content-type", "")
        text = resp.text if hasattr(resp, "text") else resp.read().decode("utf-8")
        # SSE 响应（text/event-stream）：取 data: 行解析
        if "text/event-stream" in content_type:
            for line in text.splitlines():
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data and data != "[DONE]":
                        return json.loads(data)
            raise ConnectionError("MCP SSE 响应缺少 data 行")
        # 普通 JSON 响应
        return json.loads(text)


# ================================================================
# MCP 客户端
# ================================================================
class MCPClient:
    """
    MCP（Model Context Protocol）客户端。

    用法：
        client = MCPClient()
        client.connect_stdio("python", ["mcp_server.py"])
        # 或 client.connect_http("http://localhost:8900/mcp")

        tools = client.list_tools()
        result = client.call_tool("generate_question", {"topic": "函数"})
        client.close()
    """

    def __init__(self, name: str = "lumilearn", version: str = "1.0.0"):
        self.client_name = name
        self.client_version = version
        self._transport: Optional[Any] = None
        self._seq = 0
        self._lock = threading.Lock()
        self._initialized = False
        self.server_info: Dict = {}
        self.server_capabilities: Dict = {}

    # ---------- 连接 ----------
    def connect_stdio(self, command: str,
                      args: Optional[List[str]] = None) -> Dict:
        """通过 stdio 连接 MCP server（子进程）"""
        self._transport = _StdioTransport(command, args)
        return self.initialize()

    def connect_http(self, url: str, timeout: float = 30.0) -> Dict:
        """通过 HTTP 连接 MCP server"""
        self._transport = _HttpTransport(url, timeout)
        return self.initialize()

    # ---------- MCP 生命周期 ----------
    def initialize(self, timeout: float = 30.0) -> Dict:
        """
        MCP 握手：initialize → 收到响应后发 initialized 通知。

        返回：
            {"protocol_version": str, "capabilities": Dict, "server_info": Dict}
        """
        if self._transport is None:
            raise ConnectionError("未连接 MCP server，请先 connect_stdio/connect_http")

        msg_id = self._next_id()
        result = self._request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "clientInfo": {"name": self.client_name, "version": self.client_version},
            },
            msg_id,
            timeout,
        )
        self._initialized = True
        self.server_info = result.get("serverInfo", {})
        self.server_capabilities = result.get("capabilities", {})
        # 发送 initialized 通知（notifications/initialized 无需响应）
        self._notify("notifications/initialized", {})
        return {
            "protocol_version": result.get("protocolVersion", ""),
            "capabilities": self.server_capabilities,
            "server_info": self.server_info,
        }

    # ---------- 工具调用 ----------
    def list_tools(self, timeout: float = 30.0) -> List[Dict]:
        """列出 server 可用工具：[{name, description, inputSchema}]"""
        result = self._request("tools/list", {}, self._next_id(), timeout)
        return result.get("tools", [])

    def call_tool(self, tool_name: str, arguments: Dict = None,
                  timeout: float = 60.0) -> Dict:
        """
        调用 MCP 工具。

        返回：
            {"content": [{"type":"text","text":...}], "isError": bool,
             "text": 拼接后的文本（便捷字段）}
        """
        result = self._request(
            "tools/call",
            {"name": tool_name, "arguments": arguments or {}},
            self._next_id(),
            timeout,
        )
        content = result.get("content", [])
        text = "".join(
            item.get("text", "") for item in content if item.get("type") == "text"
        )
        return {
            "content": content,
            "isError": result.get("isError", False),
            "text": text,
        }

    # ---------- 内部 ----------
    def _request(self, method: str, params: Dict, msg_id: int,
                 timeout: float) -> Dict:
        message = _make_request(method, params, msg_id)
        with self._lock:
            self._transport.send(message)
            raw = self._transport.receive(timeout)
        # 校验响应 id
        if raw.get("id") != msg_id:
            raise ConnectionError(
                f"MCP 响应 id 不匹配: 期望 {msg_id}, 实际 {raw.get('id')}")
        if "error" in raw:
            err = raw["error"]
            if err is None:
                raise RuntimeError(f"MCP 方法 {method} 返回空错误")
            raise RuntimeError(f"MCP 方法 {method} 出错: {err.get('message', err)}")
        return raw.get("result", {})

    def _notify(self, method: str, params: Dict) -> None:
        message = _make_notification(method, params)
        with self._lock:
            self._transport.send(message)

    def _next_id(self) -> int:
        self._seq += 1
        return self._seq

    def close(self) -> None:
        """关闭连接"""
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        self._initialized = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ================================================================
# 内置教育工具集
# ================================================================
class BuiltinToolRegistry:
    """
    预置教育工具注册表（MCP 兼容 schema）。

    内置工具：
      - knowledge_retrieval : 检索自积累知识库
      - generate_question   : 生成题目（模拟）
      - render_chart        : 渲染图表（模拟，返回图表描述）
    """

    def __init__(self):
        self._tools: Dict[str, Dict] = {}
        self._handlers: Dict[str, Callable] = {}
        self._register_builtin()

    def register_tool(self, name: str, description: str, input_schema: Dict,
                      handler: Callable) -> None:
        """注册自定义工具（第三方可通过 MCP 接入后也走此格式）"""
        self._tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
        }
        self._handlers[name] = handler

    def list_tools(self) -> List[Dict]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[Dict]:
        return self._tools.get(name)

    def call_tool(self, name: str, arguments: Dict) -> Dict:
        handler = self._handlers.get(name)
        if handler is None:
            return {
                "content": [{"type": "text", "text": f"未知工具: {name}"}],
                "isError": True,
            }
        try:
            text = handler(arguments or {})
            return {"content": [{"type": "text", "text": str(text)}],
                    "isError": False}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"工具调用失败: {e}"}],
                    "isError": True}

    # ---------- 内置工具 ----------
    def _register_builtin(self):
        # 1. 知识库检索
        self.register_tool(
            name="knowledge_retrieval",
            description="检索自积累知识库，获取指定主题的已积累知识点",
            input_schema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "检索主题"},
                    "subject": {"type": "string", "description": "学科（可选）"},
                },
                "required": ["topic"],
            },
            handler=self._handle_knowledge_retrieval,
        )
        # 2. 题目生成
        self.register_tool(
            name="generate_question",
            description="根据主题和难度生成一道练习题目（含答案解析）",
            input_schema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "difficulty": {"type": "string",
                                   "enum": ["简单", "中等", "困难"]},
                },
                "required": ["topic"],
            },
            handler=self._handle_generate_question,
        )
        # 3. 图表渲染
        self.register_tool(
            name="render_chart",
            description="渲染教学图表，返回图表类型与数据结构描述",
            input_schema={
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string",
                                   "enum": ["line", "bar", "pie"]},
                    "title": {"type": "string"},
                    "points": {"type": "array", "items": {"type": "number"}},
                },
                "required": ["chart_type"],
            },
            handler=self._handle_render_chart,
        )

    def _handle_knowledge_retrieval(self, args: Dict) -> str:
        topic = args.get("topic", "")
        subject = args.get("subject", "")
        try:
            from agent_core.knowledge_cache import get_knowledge_cache
            ctx = get_knowledge_cache().get_context(topic, subject)
            return ctx or f"知识库中暂无「{topic}」的积累内容"
        except Exception as e:
            return f"[知识库检索不可用: {e}]"

    def _handle_generate_question(self, args: Dict) -> str:
        topic = args.get("topic", "未知主题")
        difficulty = args.get("difficulty", "中等")
        return (f"【题目】请说明「{topic}」的核心概念（难度：{difficulty}）。\n"
                f"【解析】答题需先给出定义，再举例说明，最后总结要点。")

    def _handle_render_chart(self, args: Dict) -> str:
        chart_type = args.get("chart_type", "line")
        title = args.get("title", "")
        points = args.get("points", [])
        return (f"图表类型: {chart_type} | 标题: {title} | "
                f"数据点: {points}（此工具返回图表描述，由前端渲染）")


# ================================================================
# 极简本地 MCP Server（HTTP 传输）
# ================================================================
class MCPServer:
    """
    极简本地 MCP Server（HTTP transport），对外暴露注册工具。

    用于：
      - Agent 将教育工具能力以 MCP 协议对外提供
      - 端到端测试（client → server → tools/call）

    用法：
        server = MCPServer(host="127.0.0.1", port=8900)
        server.start()
        server.stop()
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8900,
                 registry: Optional[BuiltinToolRegistry] = None,
                 name: str = "lumilearn-tools", version: str = "1.0.0"):
        self.host = host
        self.port = port
        self.registry = registry or BuiltinToolRegistry()
        self.name = name
        self.version = version
        self._httpd: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def url(self) -> str:
        # port=0 时系统自动分配，启动后需从实际地址读取
        if self._httpd is not None:
            host, port = self._httpd.server_address[:2]
            return f"http://{host}:{port}/mcp"
        return f"http://{self.host}:{self.port}/mcp"

    def start(self) -> None:
        """启动 HTTP server（后台线程）"""
        if self._httpd is not None:
            return
        self._httpd = self._build_handler()
        self._thread = threading.Thread(target=self._httpd.serve_forever,
                                        daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None

    # ---------- 内部 ----------
    def _build_handler(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        server_ref = self

        class _MCPHandler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):  # 静默日志
                pass

            def do_POST(self):
                if self.path != "/mcp":
                    self._json_error(404, "未找到端点")
                    return
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    body = json.loads(self.rfile.read(length) or b"{}")
                except Exception:
                    self._json_error(400, "无效的 JSON-RPC 请求")
                    return

                response = server_ref._handle_message(body)
                if response is None:
                    # notification 无需响应
                    self.send_response(202)
                    self.end_headers()
                    return
                data = json.dumps(response, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _json_error(self, code: int, message: str):
                body = json.dumps(
                    {"jsonrpc": "2.0", "id": None,
                     "error": {"code": code, "message": message}},
                    ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return ThreadingHTTPServer((self.host, self.port), _MCPHandler)

    def _handle_message(self, msg: Dict) -> Optional[Dict]:
        method = msg.get("method", "")
        msg_id = msg.get("id")

        # notification（无 id）→ 不响应
        if method == "notifications/initialized":
            return None

        try:
            if method == "initialize":
                params = msg.get("params", {})
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "protocolVersion": params.get(
                            "protocolVersion", MCP_PROTOCOL_VERSION),
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": self.name, "version": self.version},
                    },
                }
            if method == "tools/list":
                return {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {"tools": self.registry.list_tools()},
                }
            if method == "tools/call":
                params = msg.get("params", {})
                result = self.registry.call_tool(
                    params.get("name", ""), params.get("arguments", {}))
                return {"jsonrpc": "2.0", "id": msg_id, "result": result}
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32601, "message": f"不支持的方法: {method}"},
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32603, "message": str(e)},
            }


# ================================================================
# 单例
# ================================================================
_client: Optional[MCPClient] = None
_registry: Optional[BuiltinToolRegistry] = None


def get_mcp_client(name: str = "lumilearn", version: str = "1.0.0") -> MCPClient:
    """获取 MCP 客户端单例"""
    global _client
    if _client is None:
        _client = MCPClient(name, version)
    return _client


def get_tool_registry() -> BuiltinToolRegistry:
    """获取内置教育工具注册表单例"""
    global _registry
    if _registry is None:
        _registry = BuiltinToolRegistry()
    return _registry


def reset_mcp_client():
    """重置 MCP 客户端（测试用）"""
    global _client
    if _client is not None:
        _client.close()
        _client = None


if __name__ == "__main__":
    print("=== MCP 客户端 + 教育工具集端到端测试 ===")

    server = MCPServer(port=8910)
    server.start()
    print(f"本地 MCP Server 启动: {server.url}")

    client = MCPClient()
    info = client.connect_http(server.url)
    print(f"握手完成: server={info['server_info']}")

    tools = client.list_tools()
    print(f"可用工具: {[t['name'] for t in tools]}")

    r1 = client.call_tool("generate_question", {"topic": "函数单调性", "difficulty": "困难"})
    print(f"调用 generate_question: {r1['isError']} | {r1['text'][:40]}...")

    r2 = client.call_tool("knowledge_retrieval", {"topic": "牛顿第二定律"})
    print(f"调用 knowledge_retrieval: {r2['text'][:60]}")

    client.close()
    server.stop()
    print("端到端测试完成")
