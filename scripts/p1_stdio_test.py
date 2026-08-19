# -*- coding: utf-8 -*-
"""P1-5 stdio 端到端独立测试"""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from agent_core.mcp_external import get_external_mcp_registry, reset_external_mcp_registry, ExternalMCPServerConfig
from agent_core.mcp_client import MCPClient

reset_external_mcp_registry()
reg = get_external_mcp_registry()

# 生成 stdio MCP server 脚本
script = os.path.join(os.path.dirname(__file__), "_stdio_test_server.py")
with open(script, "w", encoding="utf-8") as f:
    f.write(r'''
import sys, json
sys.stdin.reconfigure(encoding="utf-8", errors="replace")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def respond(req, result=None, error=None):
    resp = {"jsonrpc":"2.0","id": req.get("id"), "result": result, "error": error}
    if result is None and error is None:
        return
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()

while True:
    line = sys.stdin.readline()
    if not line:
        break
    try:
        req = json.loads(line.strip())
        method = req.get("method", "")
        rid = req.get("id")
        if method == "initialize":
            respond(req, result={
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "test", "version": "1.0"}
            })
        elif method == "tools/list":
            respond(req, result={
                "tools": [{"name": "echo", "description": "echo",
                           "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}}}]
            })
        elif method == "tools/call":
            name = req.get("params", {}).get("name", "")
            args = req.get("params", {}).get("arguments", {})
            if name == "echo":
                respond(req, result={"content": [{"type": "text", "text": args.get("text", "")}]})
            else:
                respond(req, error={"code": -32601, "message": f"unknown: {name}"})
        elif method.startswith("notifications/"):
            pass
        else:
            respond(req, error={"code": -32601, "message": f"unknown method: {method}"})
    except Exception as e:
        if rid is not None:
            respond(req, error={"code": -32603, "message": str(e)})
''')

cfg = ExternalMCPServerConfig(
    server_name="stdio_test",
    transport="stdio",
    command=sys.executable,
    args=[script],
    enabled=True,
    description="test"
)
res = reg.add_server(cfg)
print(f"add_server: {res}")

# 直接用 MCPClient 测试 stdio 协议
print("\n=== 直接用 MCPClient 测试 stdio ===")
client = MCPClient(name="stdio_test_client")
try:
    init = client.connect_stdio(sys.executable, [script])
    print(f"initialize: {init}")
    tools = client.list_tools()
    print(f"list_tools: {tools}")
    result = client.call_tool("echo", {"text": "你好stdio"})
    print(f"call_tool echo: {result}")
    result2 = client.call_tool("nonexistent", {})
    print(f"call_tool nonexistent: isError={result2.get('isError')}, text={result2.get('text')}")
    client.close()
    print("\n✅ stdio MCP 协议验证通过")
except Exception as e:
    print(f"\n❌ stdio MCP 协议失败: {e}")
    import traceback; traceback.print_exc()

# 通过 registry 测试
print("\n=== 通过 registry 测试 stdio ===")
try:
    tools2 = reg.list_tools("stdio_test")
    print(f"list_tools via registry: {tools2}")
    result3 = reg.call_tool("stdio_test", "echo", {"text": "你好P1-5"})
    print(f"call_tool via registry: isError={result3.get('isError')}, text={result3.get('text','')[:50]}")
    print("✅ registry stdio 验证通过")
except Exception as e:
    print(f"❌ registry stdio 失败: {e}")
    import traceback; traceback.print_exc()

reg.delete_server("stdio_test")
os.remove(script)
print("\n完成")
