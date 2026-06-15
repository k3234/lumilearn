"""
Understand-Anything 知识图谱构建器
将代码库和文档转化为文件/概念/问题节点的知识图谱
"""
import os
import re
import ast
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict, field
from collections import defaultdict


@dataclass
class FileNode:
    id: str
    path: str
    type: str
    size_lines: int
    responsibility: str
    key_symbols: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    imported_by: List[str] = field(default_factory=list)
    ai_generated_score: float = 0.0


@dataclass
class ConceptNode:
    id: str
    name: str
    category: str
    definition: str
    files_containing: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    doc_refs: List[str] = field(default_factory=list)


@dataclass
class QuestionNode:
    id: str
    question: str
    category: str
    related_files: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    possible_answers: List[str] = field(default_factory=list)
    verified: bool = False


@dataclass
class Relationship:
    from_node: str
    to_node: str
    type: str
    weight: int = 1


class UnderstandAnything:
    """代码库理解工具"""

    def __init__(self, project_root: str = "./", db_path: str = "./.ua/graph.db"):
        self.project_root = Path(project_root).resolve()
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.file_nodes: Dict[str, FileNode] = {}
        self.concept_nodes: Dict[str, ConceptNode] = {}
        self.question_nodes: Dict[str, QuestionNode] = {}
        self.relationships: List[Relationship] = []

        self.concept_keywords = {
            "tokenizer": "分词",
            "bpe": "BPE",
            "embedding": "嵌入",
            "transformer": "Transformer",
            "attention": "注意力机制",
            "model": "模型",
            "trainer": "训练器",
            "inference": "推理",
            "optimizer": "优化器",
            "vocab": "词汇表",
            "config": "配置",
            "pipeline": "管道",
            "router": "路由",
            "agent": "智能体",
            "skill": "技能",
        }

        self.question_patterns = [
            r"如何.*\?",
            r"怎么.*\?",
            r"为什么.*\?",
            r"什么是.*\?",
            r"#\s*TODO[:：]?\s*(.+)",
            r"#\s*FIXME[:：]?\s*(.+)",
            r"#\s*XXX[:：]?\s*(.+)",
        ]

        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS file_nodes (
            id TEXT PRIMARY KEY,
            data TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS concept_nodes (
            id TEXT PRIMARY KEY,
            data TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS question_nodes (
            id TEXT PRIMARY KEY,
            data TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_node TEXT,
            to_node TEXT,
            type TEXT,
            weight INTEGER
        )''')
        conn.commit()
        conn.close()

    def build(self, include_docs: bool = True) -> Dict:
        """构建知识图谱"""
        files = list(self.project_root.rglob("*.py"))
        if include_docs:
            files.extend(self.project_root.rglob("*.md"))

        for f in files:
            if self._should_skip(f):
                continue
            try:
                self._process_file(f)
            except Exception as e:
                print(f"  Skip {f}: {e}")

        self._extract_concepts_from_files()
        self._mine_questions()
        self._build_relationships()
        self._save_to_db()

        return {
            "file_nodes": len(self.file_nodes),
            "concept_nodes": len(self.concept_nodes),
            "question_nodes": len(self.question_nodes),
            "relationships": len(self.relationships)
        }

    def _should_skip(self, file_path: Path) -> bool:
        skip_dirs = {'__pycache__', '.git', 'node_modules', 'venv', '.venv', 'outputs'}
        return any(part in skip_dirs for part in file_path.parts)

    def _process_file(self, file_path: Path):
        """处理单个文件"""
        rel_path = str(file_path.relative_to(self.project_root))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, PermissionError):
            return

        lines = content.split("\n")
        symbols = []
        imports = []

        if file_path.suffix == ".py":
            try:
                tree = ast.parse(content, filename=str(file_path))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        symbols.append(node.name)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module.split(".")[0])
            except SyntaxError:
                pass

        responsibility = self._guess_responsibility(file_path, symbols)
        ai_score = self._estimate_ai_generated(content)

        self.file_nodes[rel_path] = FileNode(
            id=f"file_{rel_path}",
            path=rel_path,
            type=file_path.suffix.lstrip("."),
            size_lines=len(lines),
            responsibility=responsibility,
            key_symbols=symbols[:20],
            imports=imports,
            ai_generated_score=ai_score
        )

    def _guess_responsibility(self, file_path: Path, symbols: List[str]) -> str:
        """猜测文件职责"""
        name = file_path.stem
        if "test" in name:
            return "测试代码"
        if "config" in name:
            return "配置定义"
        if "model" in name:
            return "模型定义"
        if "train" in name:
            return "训练相关"
        if "inference" in name or "predict" in name:
            return "推理相关"
        if "token" in name:
            return "分词器"
        if "engine" in name:
            return "核心引擎"
        if "skill" in name:
            return "技能模块"
        if "agent" in name:
            return "智能体"
        if "data" in name:
            return "数据处理"
        return f"{name} 模块"

    def _estimate_ai_generated(self, content: str) -> float:
        """估计 AI 生成的概率"""
        score = 0.0
        if re.search(r'""".*?Args:.*?Returns:.*?"""', content, re.DOTALL):
            score += 0.3
        if "Type hints" in content or ": " in content[:500]:
            score += 0.2
        if re.search(r"# Generated by|# Auto-generated", content, re.IGNORECASE):
            score += 0.4
        if re.search(r"print\(f['\"]", content):
            score += 0.1
        return min(score, 1.0)

    def _extract_concepts_from_files(self):
        """从文件中提取概念"""
        concept_to_files = defaultdict(list)

        for fpath, fnode in self.file_nodes.items():
            fpath_lower = fpath.lower()
            for keyword, concept_name in self.concept_keywords.items():
                if keyword in fpath_lower:
                    concept_id = f"concept_{concept_name}"
                    concept_to_files[concept_id].append(fpath)

        for concept_id, files in concept_to_files.items():
            concept_name = concept_id.replace("concept_", "")
            self.concept_nodes[concept_id] = ConceptNode(
                id=concept_id,
                name=concept_name,
                category="技术概念",
                definition=f"与 {concept_name} 相关的代码模块和文档",
                files_containing=files
            )

    def _mine_questions(self):
        """从代码和文档中挖掘问题"""
        question_id = 0
        for fpath, fnode in self.file_nodes.items():
            try:
                full_path = self.project_root / fpath
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (UnicodeDecodeError, FileNotFoundError):
                continue

            for pattern in self.question_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    match = match.strip()
                    if len(match) < 5 or len(match) > 200:
                        continue
                    question_id += 1
                    qid = f"q_{question_id:04d}"
                    self.question_nodes[qid] = QuestionNode(
                        id=qid,
                        question=match if "?" in match or "？" in match else f"如何处理: {match}",
                        category="代码注释",
                        related_files=[fpath]
                    )

    def _build_relationships(self):
        """构建节点关系"""
        for fpath, fnode in self.file_nodes.items():
            for imp in fnode.imports:
                imp_path = f"file_{imp}"
                if imp_path in self.file_nodes or any(
                    fpath_str.startswith(imp) for fpath_str in self.file_nodes.keys()
                ):
                    self.relationships.append(Relationship(
                        from_node=fnode.id,
                        to_node=imp_path,
                        type="imports",
                        weight=1
                    ))

        for cid, cnode in self.concept_nodes.items():
            for fpath in cnode.files_containing:
                self.relationships.append(Relationship(
                    from_node=cnode.id,
                    to_node=f"file_{fpath}",
                    type="uses",
                    weight=1
                ))

        for qid, qnode in self.question_nodes.items():
            for fpath in qnode.related_files:
                self.relationships.append(Relationship(
                    from_node=qid,
                    to_node=f"file_{fpath}",
                    type="addresses",
                    weight=1
                ))

    def _save_to_db(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("DELETE FROM file_nodes")
        c.execute("DELETE FROM concept_nodes")
        c.execute("DELETE FROM question_nodes")
        c.execute("DELETE FROM relationships")

        for fnode in self.file_nodes.values():
            c.execute("INSERT INTO file_nodes VALUES (?, ?)",
                     (fnode.id, json.dumps(asdict(fnode), ensure_ascii=False)))
        for cnode in self.concept_nodes.values():
            c.execute("INSERT INTO concept_nodes VALUES (?, ?)",
                     (cnode.id, json.dumps(asdict(cnode), ensure_ascii=False)))
        for qnode in self.question_nodes.values():
            c.execute("INSERT INTO question_nodes VALUES (?, ?)",
                     (qnode.id, json.dumps(asdict(qnode), ensure_ascii=False)))
        for rel in self.relationships:
            c.execute("INSERT INTO relationships (from_node, to_node, type, weight) VALUES (?, ?, ?, ?)",
                     (rel.from_node, rel.to_node, rel.type, rel.weight))

        conn.commit()
        conn.close()

    def ask(self, question: str) -> Dict:
        """回答用户问题（基础版：图谱检索）"""
        question_lower = question.lower()
        matched_concepts = []
        matched_files = []

        for cid, cnode in self.concept_nodes.items():
            if cnode.name.lower() in question_lower or question_lower in cnode.name.lower():
                matched_concepts.append(cnode)

        for fpath, fnode in self.file_nodes.items():
            for symbol in fnode.key_symbols:
                if symbol.lower() in question_lower:
                    matched_files.append(fnode)
                    break

        sources = []
        for c in matched_concepts[:3]:
            sources.append({
                "type": "concept",
                "name": c.name,
                "definition": c.definition,
                "files": c.files_containing[:5]
            })
        for f in matched_files[:3]:
            sources.append({
                "type": "file",
                "path": f.path,
                "responsibility": f.responsibility,
                "key_symbols": f.key_symbols[:5]
            })

        return {
            "question": question,
            "sources": sources,
            "matched_concepts": len(matched_concepts),
            "matched_files": len(matched_files),
            "related_questions": [
                q.question for q in list(self.question_nodes.values())[:3]
            ]
        }

    def get_concept(self, concept_name: str) -> Optional[ConceptNode]:
        """获取概念详情"""
        for cid, cnode in self.concept_nodes.items():
            if cnode.name.lower() == concept_name.lower():
                return cnode
        return None

    def navigate(self, target: str) -> Dict:
        """导航到目标"""
        concept = self.get_concept(target)
        if concept:
            return {
                "type": "concept",
                "name": concept.name,
                "files": concept.files_containing,
                "related_concepts": concept.related_concepts,
                "doc_refs": concept.doc_refs
            }

        for fpath, fnode in self.file_nodes.items():
            if target in fpath or target in fnode.responsibility:
                return {
                    "type": "file",
                    "path": fpath,
                    "responsibility": fnode.responsibility,
                    "key_symbols": fnode.key_symbols,
                    "imports": fnode.imports
                }

        return {"type": "unknown", "target": target, "found": False}

    def export_graph_json(self) -> Dict:
        """导出图谱为 JSON"""
        return {
            "file_nodes": {fid: asdict(f) for fid, f in self.file_nodes.items()},
            "concept_nodes": {cid: asdict(c) for cid, c in self.concept_nodes.items()},
            "question_nodes": {qid: asdict(q) for qid, q in self.question_nodes.items()},
            "relationships": [asdict(r) for r in self.relationships],
            "stats": {
                "files": len(self.file_nodes),
                "concepts": len(self.concept_nodes),
                "questions": len(self.question_nodes),
                "relationships": len(self.relationships)
            }
        }


if __name__ == "__main__":
    ua = UnderstandAnything(project_root="./")
    result = ua.build()
    print(f"构建完成: {result}")
    print(f"  示例概念: {[c.name for c in list(ua.concept_nodes.values())[:5]]}")
    print(f"  示例文件: {list(ua.file_nodes.keys())[:3]}")
