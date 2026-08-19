# -*- coding: utf-8 -*-
"""
LumiLearn 沙箱安全回归测试（C-1 修复验证）
验证：逃逸原语被拦截、AST 检查覆盖裸调用与属性链、超时生效、端点需管理员认证。
"""
import os
import sys
from unittest import mock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from framework.security.config import SecurityConfig
from framework.security.sandbox import CodeSandbox, get_sandbox


class _FakeConfig:
    class _Sandbox:
        max_execution_time = 2
        max_memory_mb = 128
    sandbox = _Sandbox()


def _sandbox():
    return CodeSandbox(_FakeConfig())


# ---------- AST 逃逸拦截 ----------
class TestSandboxEscapeBlocked:
    def setup_method(self):
        self.sb = _sandbox()

    def test_block_exec_bare_call(self):
        """裸调用 exec(...) 必须被拦截"""
        r = self.sb.execute("exec(\"import os; os.system('id')\")")
        assert r.success is False
        assert "安全检查失败" in r.error

    def test_block_eval_bare_call(self):
        r = self.sb.execute("eval('__import__(\"os\").system(\"id\")')")
        assert r.success is False
        assert "安全检查失败" in r.error

    def test_block_open_bare_call(self):
        r = self.sb.execute("open('/etc/passwd').read()")
        assert r.success is False
        assert "安全检查失败" in r.error

    def test_block_dangerous_import(self):
        r = self.sb.execute("import os\nprint('hi')")
        assert r.success is False
        assert "禁止导入" in r.error

    def test_block_dunder_chain(self):
        """__class__.__bases__.__subclasses__ 属性链逃逸必须被拦截"""
        r = self.sb.execute("().__class__.__bases__[0].__subclasses__()")
        assert r.success is False
        assert "安全检查失败" in r.error

    def test_block_getattr_globals(self):
        r = self.sb.execute("getattr(globals(), 'x')")
        assert r.success is False
        assert "安全检查失败" in r.error

    def test_block_input(self):
        r = self.sb.execute("input('password')")
        assert r.success is False
        assert "安全检查失败" in r.error


# ---------- 合法代码仍可执行 ----------
class TestSandboxLegitCode:
    def setup_method(self):
        self.sb = _sandbox()

    def test_simple_arithmetic(self):
        r = self.sb.execute("_result = 2 + 3")
        assert r.success is True
        assert r.return_value == 5

    def test_print_captured(self):
        r = self.sb.execute("print('hello')")
        assert r.success is True
        assert "hello" in r.output

    def test_list_comprehension(self):
        r = self.sb.execute("_result = [x * x for x in range(5)]")
        assert r.success is True
        assert r.return_value == [0, 1, 4, 9, 16]

    def test_execute_with_return(self):
        r = self.sb.execute_with_return("x = 2 + 2; _result = x")
        assert r.success is True
        assert r.return_value == 4


# ---------- 超时控制 ----------
class TestSandboxTimeout:
    def test_infinite_loop_times_out(self):
        sb = CodeSandbox(_FakeConfig())  # max_execution_time=2
        r = sb.execute("while True: pass", timeout=1)
        assert r.success is False
        assert "超时" in r.error


# ---------- 端点认证 ----------
class TestSandboxEndpointAuth:
    def setup_method(self):
        import goai_web  # noqa: F401
        # security blueprint 挂在 framework/api/server 中；此处直接验证 require_admin 装饰器
        from framework.api.routes import security
        self.mod = security

    def test_execute_requires_admin(self):
        """execute_code 必须被 require_admin 保护"""
        assert hasattr(self.mod.execute_code, "__wrapped__")

    def test_firewall_apply_requires_admin(self):
        assert hasattr(self.mod.apply_system_firewall, "__wrapped__")

    def test_reset_requires_admin(self):
        assert hasattr(self.mod.reset_security_system, "__wrapped__")

    def test_gateway_block_requires_admin(self):
        assert hasattr(self.mod.block_ip, "__wrapped__")

    def test_gateway_unblock_requires_admin(self):
        assert hasattr(self.mod.unblock_ip, "__wrapped__")


# ---------- 白名单内置函数（深度防御） ----------
class TestSandboxBuiltins:
    def test_dangerous_builtins_removed(self):
        sb = _sandbox()
        g = sb._create_safe_globals()
        bi = g["__builtins__"]
        for dangerous in ("eval", "exec", "open", "compile", "getattr",
                          "globals", "locals", "vars", "input", "setattr",
                          "__import__", "type", "super", "memoryview", "dir"):
            assert dangerous not in bi, f"{dangerous} 不应存在于白名单"

    def test_safe_builtins_present(self):
        sb = _sandbox()
        bi = sb._create_safe_globals()["__builtins__"]
        for safe in ("print", "len", "str", "int", "range", "list",
                     "dict", "sum", "abs", "max", "min"):
            assert safe in bi
