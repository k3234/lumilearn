"""
Build-Your-Own-X 项目管理器
为 LumiLearn 提供手搓教程项目脚手架、推荐、评估能力
"""
import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Project:
    id: str
    name: str
    category: str
    language: str
    difficulty: str
    estimated_hours: int
    skills: List[str]
    description: str
    tutorial_url: str = ""
    github_template: str = ""


PROJECTS_CATALOG = [
    {
        "id": "lisp-interpreter-py",
        "name": "LISP 解释器",
        "category": "interpreters",
        "language": "python",
        "difficulty": "beginner",
        "estimated_hours": 20,
        "skills": ["AST", "递归", "求值器"],
        "description": "从零实现一个 LISP 方言解释器，掌握递归求值和树遍历"
    },
    {
        "id": "http-server-c",
        "name": "HTTP 服务器",
        "category": "network",
        "language": "c",
        "difficulty": "intermediate",
        "estimated_hours": 15,
        "skills": ["Socket编程", "HTTP协议", "并发"],
        "description": "用 C 实现一个支持 GET/POST 的 HTTP 服务器"
    },
    {
        "id": "raytracer-cpp",
        "name": "光线追踪渲染器",
        "category": "graphics",
        "language": "cpp",
        "difficulty": "advanced",
        "estimated_hours": 30,
        "skills": ["3D数学", "光线求交", "渲染管线"],
        "description": "实现 Whitted-style 光线追踪器，渲染真实感图像"
    },
    {
        "id": "tiny-shell-c",
        "name": "Unix Shell",
        "category": "tools",
        "language": "c",
        "difficulty": "intermediate",
        "estimated_hours": 20,
        "skills": ["进程管理", "系统调用", "管道"],
        "description": "实现一个支持管道、重定向的简单 shell"
    },
    {
        "id": "lisp-vm-rust",
        "name": "字节码虚拟机",
        "category": "interpreters",
        "language": "rust",
        "difficulty": "advanced",
        "estimated_hours": 40,
        "skills": ["字节码", "栈式VM", "指令集"],
        "description": "实现 Lox 语言的字节码编译器和虚拟机"
    },
    {
        "id": "pong-cpp",
        "name": "Pong 游戏",
        "category": "graphics",
        "language": "cpp",
        "difficulty": "beginner",
        "estimated_hours": 10,
        "skills": ["游戏循环", "简单渲染", "事件系统"],
        "description": "用 C++ 和 SFML 实现经典 Pong 游戏"
    },
    {
        "id": "regex-engine-c",
        "name": "正则表达式引擎",
        "category": "tools",
        "language": "c",
        "difficulty": "advanced",
        "estimated_hours": 25,
        "skills": ["状态机", "NFA/DFA", "字符串处理"],
        "description": "实现支持 . * + ? | () 的正则匹配器"
    },
    {
        "id": "tiny-git-py",
        "name": "Git 简化版",
        "category": "tools",
        "language": "python",
        "difficulty": "intermediate",
        "estimated_hours": 30,
        "skills": ["内容寻址", "对象存储", "DAG"],
        "description": "实现 Git 的核心命令：init/add/commit/log"
    },
    {
        "id": "mini-os-rust",
        "name": "微型操作系统",
        "category": "os",
        "language": "rust",
        "difficulty": "advanced",
        "estimated_hours": 50,
        "skills": ["内核", "中断", "内存管理"],
        "description": "基于博客 OS 教程实现 x86_64 微型内核"
    },
    {
        "id": "c-compiler-c",
        "name": "C 子集编译器",
        "category": "interpreters",
        "language": "c",
        "difficulty": "advanced",
        "estimated_hours": 60,
        "skills": ["词法分析", "语法分析", "代码生成"],
        "description": "实现 C 语言的子集编译器，生成 x86 汇编"
    }
]


class BuildYourOwnXManager:
    """Build-Your-Own-X 项目管理器"""

    def __init__(self, projects_dir: str = "./.byox_projects"):
        self.projects_dir = Path(projects_dir).resolve()
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.user_progress_file = self.projects_dir / "progress.json"
        self.progress = self._load_progress()

    def _load_progress(self) -> Dict:
        if self.user_progress_file.exists():
            with open(self.user_progress_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "completed": [],
            "current": None,
            "user_profile": {}
        }

    def _save_progress(self):
        with open(self.user_progress_file, "w", encoding="utf-8") as f:
            json.dump(self.progress, f, ensure_ascii=False, indent=2)

    def list_projects(self, language: Optional[str] = None,
                     difficulty: Optional[str] = None,
                     category: Optional[str] = None) -> List[Dict]:
        """列出可用项目"""
        results = []
        for proj in PROJECTS_CATALOG:
            if language and proj["language"] != language:
                continue
            if difficulty and proj["difficulty"] != difficulty:
                continue
            if category and proj["category"] != category:
                continue
            results.append(proj)
        return results

    def get_project(self, project_id: str) -> Optional[Dict]:
        """获取项目详情"""
        for proj in PROJECTS_CATALOG:
            if proj["id"] == project_id:
                return proj
        return None

    def init_project(self, project_id: str, target_dir: str = None) -> Dict:
        """初始化项目脚手架"""
        proj = self.get_project(project_id)
        if not proj:
            return {"success": False, "error": "Project not found"}

        target = Path(target_dir) if target_dir else self.projects_dir / project_id
        target.mkdir(parents=True, exist_ok=True)

        files = self._generate_scaffold(proj, target)
        self.progress["current"] = project_id
        self._save_progress()

        return {
            "success": True,
            "project_id": project_id,
            "path": str(target),
            "files_created": files
        }

    def _generate_scaffold(self, project: Dict, target: Path) -> List[str]:
        """生成项目脚手架"""
        created = []
        lang = project["language"]

        readme = f"""# {project['name']}

{project['description']}

**难度**: {project['difficulty']}
**预计耗时**: {project['estimated_hours']} 小时
**语言**: {lang}

## 技能点
{chr(10).join(f'- {s}' for s in project['skills'])}

## 步骤

1. 阅读教程
2. 实现核心代码
3. 运行测试
4. 提交作业

## 评估
使用 `build-your-own-x evaluate` 评估你的实现。
"""
        (target / "README.md").write_text(readme, encoding="utf-8")
        created.append("README.md")

        if lang == "python":
            (target / "main.py").write_text(
                f'"""\n{project["name"]} - 主入口\n"""\n\n\ndef main():\n    print("Hello, {project["name"]}!")\n\n\nif __name__ == "__main__":\n    main()\n',
                encoding="utf-8"
            )
            created.append("main.py")

            (target / "tests").mkdir(exist_ok=True)
            (target / "tests" / "__init__.py").write_text("", encoding="utf-8")
            (target / "tests" / "test_main.py").write_text(
                'import pytest\nfrom main import main\n\n\ndef test_main():\n    assert main() is None\n',
                encoding="utf-8"
            )
            created.append("tests/test_main.py")

            (target / "requirements.txt").write_text("pytest>=7.0\n", encoding="utf-8")
            created.append("requirements.txt")

        elif lang in ("javascript", "typescript"):
            (target / "package.json").write_text(json.dumps({
                "name": project["id"],
                "version": "0.1.0",
                "main": "index.js",
                "scripts": {
                    "test": "jest",
                    "start": "node index.js"
                }
            }, indent=2), encoding="utf-8")
            created.append("package.json")
            (target / "index.js").write_text(
                f"// {project['name']} - Main Entry\n\nfunction main() {{\n  console.log('Hello, {project['name']}!');\n}}\n\nmain();\n",
                encoding="utf-8"
            )
            created.append("index.js")

        elif lang in ("c", "cpp"):
            ext = "cpp" if lang == "cpp" else "c"
            (target / f"main.{ext}").write_text(
                f'// {project["name"]}\n#include <stdio.h>\n\nint main() {{\n    printf("Hello, {project["name"]}!\\n");\n    return 0;\n}}\n',
                encoding="utf-8"
            )
            created.append(f"main.{ext}")
            (target / "Makefile").write_text(
                f"CC = gcc\nCFLAGS = -Wall -Wextra\n\nall: main\n\nmain: main.{ext}\n\t$(CC) $(CFLAGS) -o main main.{ext}\n\ntest: main\n\t./main\n\nclean:\n\trm -f main\n",
                encoding="utf-8"
            )
            created.append("Makefile")

        (target / ".gitignore").write_text(
            "__pycache__/\n*.pyc\nnode_modules/\n*.o\nmain\n*.exe\n",
            encoding="utf-8"
        )
        created.append(".gitignore")

        return created

    def mark_completed(self, project_id: str, github_url: str = ""):
        """标记项目完成"""
        if project_id not in self.progress["completed"]:
            self.progress["completed"].append({
                "project_id": project_id,
                "completion_date": datetime.now().isoformat(),
                "github_url": github_url
            })
        self.progress["current"] = None
        self._save_progress()

    def get_progress(self) -> Dict:
        """获取学习进度"""
        total = len(PROJECTS_CATALOG)
        completed = len(self.progress["completed"])
        return {
            "completed": completed,
            "total": total,
            "percentage": round(completed / total * 100, 1) if total > 0 else 0,
            "current": self.progress.get("current"),
            "completed_list": self.progress["completed"]
        }

    def recommend(self, user_profile: Dict) -> List[Dict]:
        """根据用户水平推荐项目"""
        level = user_profile.get("level", "beginner")
        languages = user_profile.get("languages", ["python"])
        completed_ids = {c["project_id"] for c in self.progress["completed"]}

        difficulty_map = {
            "beginner": ["beginner"],
            "intermediate": ["beginner", "intermediate"],
            "advanced": ["beginner", "intermediate", "advanced"]
        }
        allowed_difficulties = difficulty_map.get(level, ["beginner"])

        recommendations = []
        for proj in PROJECTS_CATALOG:
            if proj["id"] in completed_ids:
                continue
            if proj["language"] not in languages:
                continue
            if proj["difficulty"] not in allowed_difficulties:
                continue
            recommendations.append(proj)

        return recommendations[:5]


if __name__ == "__main__":
    manager = BuildYourOwnXManager()
    print(f"总项目数: {len(PROJECTS_CATALOG)}")
    print(f"  Python 入门项目: {len(manager.list_projects(language='python', difficulty='beginner'))}")
    print(f"  当前进度: {manager.get_progress()}")

    recs = manager.recommend({"level": "beginner", "languages": ["python"]})
    print(f"  推荐项目:")
    for r in recs:
        print(f"    - {r['name']} ({r['difficulty']}, {r['estimated_hours']}h)")
