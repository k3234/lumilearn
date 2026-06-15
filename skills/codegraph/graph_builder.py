"""
CodeGraph - 代码知识图谱构建器
为 LumiLearn 提供代码库预索引能力
"""
import os
import ast
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class FunctionDef:
    name: str
    file: str
    line_start: int
    line_end: int
    signature: str
    docstring: Optional[str] = None
    decorators: List[str] = None
    complexity: str = "O(?)"


@dataclass
class CallRel:
    caller: str
    callee: str
    file: str
    line: int
    call_type: str = "direct"


@dataclass
class ModuleDep:
    module: str
    imports: List[str]
    imported_by: List[str]


class CodeGraphBuilder:
    """Python 代码知识图谱构建器"""

    def __init__(self, project_root: str = "./", db_path: str = "./.codegraph/graph.db"):
        self.project_root = Path(project_root).resolve()
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.functions: Dict[str, FunctionDef] = {}
        self.calls: List[CallRel] = []
        self.modules: Dict[str, ModuleDep] = {}
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS functions (
            id TEXT PRIMARY KEY,
            name TEXT,
            file TEXT,
            line_start INTEGER,
            line_end INTEGER,
            signature TEXT,
            docstring TEXT,
            data TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caller TEXT,
            callee TEXT,
            file TEXT,
            line INTEGER
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS modules (
            module TEXT PRIMARY KEY,
            imports TEXT,
            imported_by TEXT
        )''')
        conn.commit()
        conn.close()

    def scan(self, include_patterns: List[str] = None,
             exclude_patterns: List[str] = None) -> Dict:
        """扫描项目并构建图谱"""
        include_patterns = include_patterns or ["**/*.py"]
        exclude_patterns = exclude_patterns or [
            "**/__pycache__/**", "**/.git/**", "**/outputs/**",
            "**/node_modules/**", "**/venv/**", "**/.venv/**"
        ]

        files_scanned = 0
        for pattern in include_patterns:
            for file_path in self.project_root.glob(pattern):
                if any(file_path.match(exc) for exc in exclude_patterns):
                    continue
                if self._should_skip(file_path):
                    continue
                try:
                    self._parse_file(file_path)
                    files_scanned += 1
                except Exception as e:
                    print(f"  Skip {file_path}: {e}")

        self._save_to_db()
        return {
            "files_scanned": files_scanned,
            "functions": len(self.functions),
            "calls": len(self.calls),
            "modules": len(self.modules)
        }

    def _should_skip(self, file_path: Path) -> bool:
        skip_dirs = {'__pycache__', '.git', 'node_modules', 'venv', '.venv', 'outputs'}
        return any(part in skip_dirs for part in file_path.parts)

    def _parse_file(self, file_path: Path):
        """解析 Python 文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            return

        rel_path = str(file_path.relative_to(self.project_root))
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_def = self._extract_function(node, rel_path)
                self.functions[func_def.name + "@" + rel_path] = func_def

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])

            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    call = CallRel(
                        caller=f"file:{rel_path}",
                        callee=node.func.id,
                        file=rel_path,
                        line=node.lineno
                    )
                    self.calls.append(call)
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        call = CallRel(
                            caller=f"file:{rel_path}",
                            callee=f"{node.func.value.id}.{node.func.attr}",
                            file=rel_path,
                            line=node.lineno
                        )
                        self.calls.append(call)

        if imports:
            self.modules[rel_path] = ModuleDep(
                module=rel_path,
                imports=sorted(imports),
                imported_by=[]
            )

    def _extract_function(self, node: ast.FunctionDef, file_path: str) -> FunctionDef:
        """提取函数定义信息"""
        args_list = []
        for arg in node.args.args:
            args_list.append(arg.arg)

        defaults_count = len(node.args.defaults)
        if defaults_count > 0:
            required = args_list[:-defaults_count]
            optional = args_list[-defaults_count:]
            sig_parts = required + [f"{a}=?" for a in optional]
        else:
            sig_parts = args_list

        signature = f"def {node.name}({', '.join(sig_parts)})"

        docstring = ast.get_docstring(node)

        decorators = []
        for dec in node.decorator_list:
            try:
                decorators.append(ast.unparse(dec))
            except Exception:
                pass

        return FunctionDef(
            name=node.name,
            file=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            signature=signature,
            docstring=docstring,
            decorators=decorators
        )

    def _save_to_db(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("DELETE FROM functions")
        c.execute("DELETE FROM calls")
        c.execute("DELETE FROM modules")

        for fid, fdef in self.functions.items():
            c.execute(
                "INSERT INTO functions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (fid, fdef.name, fdef.file, fdef.line_start, fdef.line_end,
                 fdef.signature, fdef.docstring, json.dumps(asdict(fdef)))
            )

        for call in self.calls:
            c.execute(
                "INSERT INTO calls (caller, callee, file, line) VALUES (?, ?, ?, ?)",
                (call.caller, call.callee, call.file, call.line)
            )

        for mod, dep in self.modules.items():
            c.execute(
                "INSERT INTO modules VALUES (?, ?, ?)",
                (mod, json.dumps(dep.imports), json.dumps(dep.imported_by))
            )

        conn.commit()
        conn.close()

    def search_function(self, name: str) -> List[FunctionDef]:
        """搜索函数定义"""
        results = []
        for fid, fdef in self.functions.items():
            if name.lower() in fdef.name.lower():
                results.append(fdef)
        return results

    def get_callers(self, function_name: str) -> List[CallRel]:
        """获取调用了某函数的所有位置"""
        return [c for c in self.calls if c.callee == function_name
                or c.callee.endswith(f".{function_name}")]

    def get_callees(self, function_name: str) -> List[CallRel]:
        """获取某函数调用的所有函数"""
        return [c for c in self.calls if c.caller == function_name]

    def get_dependencies(self, module: str) -> List[str]:
        """获取模块依赖"""
        if module in self.modules:
            return self.modules[module].imports
        return []

    def find_unused(self) -> List[str]:
        """查找未被调用的函数"""
        called = set()
        for c in self.calls:
            called.add(c.callee)

        unused = []
        for fid, fdef in self.functions.items():
            if fdef.name not in called and not fdef.name.startswith("_"):
                unused.append(fid)
        return unused

    def export_graph_json(self) -> Dict:
        """导出为 JSON 格式"""
        return {
            "functions": {fid: asdict(f) for fid, f in self.functions.items()},
            "calls": [asdict(c) for c in self.calls],
            "modules": {m: asdict(d) for m, d in self.modules.items()},
            "stats": {
                "functions": len(self.functions),
                "calls": len(self.calls),
                "modules": len(self.modules)
            }
        }


if __name__ == "__main__":
    builder = CodeGraphBuilder(project_root="./")
    result = builder.scan()
    print(f"扫描完成: {result}")
    print(f"  示例函数: {[f.name for f in list(builder.functions.values())[:5]]}")
    print(f"  未使用函数数: {len(builder.find_unused())}")
