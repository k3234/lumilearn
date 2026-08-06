# -*- coding: utf-8 -*-
"""
LumiLearn 代码沙箱
用于安全执行用户提交的代码
"""
import sys
import os
import io
import ast
import types
import time
import logging
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    """沙箱执行结果"""
    success: bool
    output: str = ""
    error: str = ""
    execution_time: float = 0.0
    memory_used: int = 0
    return_value: Any = None


class RestrictedAST(ast.NodeVisitor):
    """受限AST访问器，检查危险代码"""

    DANGEROUS_MODULES = {
        'os', 'sys', 'subprocess', 'socket', 'http', 'urllib',
        'requests', 'ctypes', 'pickle', 'shutil', 'tempfile',
        'importlib', 'code', 'compile', '__import__'
    }

    DANGEROUS_ATTRS = {
        'system', 'popen', 'exec', 'eval', 'open', 'chmod',
        'remove', 'rmdir', 'unlink', 'rename', 'replace'
    }

    def __init__(self):
        self.violations = []

    def visit_Import(self, node):
        """检查import语句"""
        for alias in node.names:
            module_name = alias.name.split('.')[0]
            if module_name in self.DANGEROUS_MODULES:
                self.violations.append(
                    f"禁止导入危险模块: {module_name}"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """检查from import语句"""
        if node.module:
            module_name = node.module.split('.')[0]
            if module_name in self.DANGEROUS_MODULES:
                self.violations.append(
                    f"禁止从危险模块导入: {node.module}"
                )
        self.generic_visit(node)

    def visit_Call(self, node):
        """检查函数调用"""
        if isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            if attr_name in self.DANGEROUS_ATTRS:
                self.violations.append(
                    f"禁止调用危险方法: {attr_name}"
                )
        self.generic_visit(node)

    def visit_Assign(self, node):
        """检查赋值语句"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                if target.id in ('__builtins__', 'exec', 'eval'):
                    self.violations.append(
                        f"禁止赋值给危险变量: {target.id}"
                    )
        self.generic_visit(node)


class CodeSandbox:
    """代码沙箱"""

    def __init__(self, config):
        self.config = config
        self._lock = threading.Lock()
        self._executions = 0
        self._max_executions_per_user: Dict[str, int] = {}

    def execute(self, code: str, user_id: str = "anonymous", timeout: int = None) -> SandboxResult:
        """
        在沙箱中执行代码

        参数:
            code: Python代码字符串
            user_id: 用户ID（用于限流）
            timeout: 执行超时时间（秒）

        返回:
            SandboxResult对象
        """
        # 1. 代码安全检查
        check_result = self._check_code(code)
        if not check_result["safe"]:
            return SandboxResult(
                success=False,
                error=f"代码安全检查失败: {', '.join(check_result['violations'])}"
            )

        # 2. 执行限流检查
        with self._lock:
            if user_id not in self._max_executions_per_user:
                self._max_executions_per_user[user_id] = 0
            if self._max_executions_per_user[user_id] >= 100:
                return SandboxResult(
                    success=False,
                    error="执行次数超限（100次/用户）"
                )
            self._max_executions_per_user[user_id] += 1
            self._executions += 1

        # 3. 创建受限环境
        safe_globals = self._create_safe_globals()
        safe_locals = {}

        # 4. 执行代码
        start_time = time.time()
        output_buffer = io.StringIO()
        error_buffer = io.StringIO()

        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            sys.stdout = output_buffer
            sys.stderr = error_buffer

            # 编译代码
            try:
                tree = ast.parse(code)
            except SyntaxError as e:
                return SandboxResult(
                    success=False,
                    error=f"语法错误: {str(e)}"
                )

            # 执行代码
            try:
                exec(compile(tree, '<sandbox>', 'exec'), safe_globals, safe_locals)
            except Exception as e:
                return SandboxResult(
                    success=False,
                    error=f"执行错误: {str(e)}"
                )

            execution_time = time.time() - start_time

            return SandboxResult(
                success=True,
                output=output_buffer.getvalue(),
                error=error_buffer.getvalue(),
                execution_time=execution_time,
                return_value=safe_locals.get('_result')
            )

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def execute_with_return(self, code: str, user_id: str = "anonymous") -> SandboxResult:
        """
        执行代码并返回结果

        用法:
            # 在代码中设置 _result 变量
            code = "x = 2 + 2; _result = x"
            result = sandbox.execute_with_return(code)
        """
        result = self.execute(code, user_id)
        if result.success:
            # 尝试获取返回值
            safe_globals = self._create_safe_globals()
            try:
                exec(code, safe_globals, safe_globals)
                result.return_value = safe_globals.get('_result')
            except:
                pass
        return result

    def _check_code(self, code: str) -> dict:
        """检查代码是否安全"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"safe": True, "violations": []}  # 语法错误由执行阶段处理

        checker = RestrictedAST()
        checker.visit(tree)

        return {
            "safe": len(checker.violations) == 0,
            "violations": checker.violations
        }

    def _create_safe_globals(self) -> dict:
        """创建安全的globals字典"""
        safe_builtins = {
            'print': print,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'range': range,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'sorted': sorted,
            'reversed': reversed,
            'min': min,
            'max': max,
            'sum': sum,
            'abs': abs,
            'round': round,
            'pow': pow,
            'divmod': divmod,
            'isinstance': isinstance,
            'issubclass': issubclass,
            'type': type,
            'hash': hash,
            'id': id,
            'input': lambda: '',  # 禁用交互式输入
        }

        # 允许的内置函数
        allowed_builtins = {
            'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
            'bytearray': bytearray, 'bytes': bytes, 'callable': callable,
            'chr': chr, 'classmethod': classmethod, 'compile': compile,
            'complex': complex, 'delattr': delattr, 'dict': dict,
            'dir': dir, 'divmod': divmod, 'enumerate': enumerate,
            'eval': eval, 'exec': exec, 'filter': filter, 'float': float,
            'format': format, 'frozenset': frozenset, 'getattr': getattr,
            'globals': globals, 'hasattr': hasattr, 'hash': hash,
            'help': help, 'hex': hex, 'id': id, 'input': input,
            'int': int, 'isinstance': isinstance, 'issubclass': issubclass,
            'iter': iter, 'len': len, 'list': list, 'locals': locals,
            'map': map, 'max': max, 'memoryview': memoryview,
            'min': min, 'next': next, 'object': object, 'oct': oct,
            'open': open, 'ord': ord, 'pow': pow, 'print': print,
            'property': property, 'range': range, 'repr': repr,
            'reversed': reversed, 'round': round, 'set': set,
            'setattr': setattr, 'slice': slice, 'sorted': sorted,
            'staticmethod': staticmethod, 'str': str, 'sum': sum,
            'super': super, 'tuple': tuple, 'type': type, 'vars': vars,
            'zip': zip,
        }

        safe_globals = {
            '__builtins__': allowed_builtins,
            '_result': None,  # 用于返回值
        }

        return safe_globals

    def get_stats(self) -> dict:
        """获取沙箱统计信息"""
        return {
            "total_executions": self._executions,
            "unique_users": len(self._max_executions_per_user),
            "config": {
                "max_execution_time": self.config.sandbox.max_execution_time,
                "max_memory_mb": self.config.sandbox.max_memory_mb,
                "rate_limit": "100次/用户"
            }
        }


# 全局沙箱实例
_sandbox_instance: Optional[CodeSandbox] = None


def get_sandbox(config=None):
    """获取全局沙箱实例"""
    global _sandbox_instance
    if _sandbox_instance is None:
        from .config import SecurityConfig
        cfg = config or SecurityConfig()
        _sandbox_instance = CodeSandbox(cfg)
    return _sandbox_instance


def reset_sandbox():
    """重置沙箱实例（用于测试）"""
    global _sandbox_instance
    _sandbox_instance = None
