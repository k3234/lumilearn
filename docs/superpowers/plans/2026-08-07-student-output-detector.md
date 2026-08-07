# 学生学习成果输出检测系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建学生学习成果输出检测系统，支持多维度的学习成果评估、报告生成和可视化输出。

**Architecture:** 基于现有数据库系统（13张表），新增输出检测模块，通过整合思考记录、AI会话、概念理解和答题数据，生成结构化的学习成果报告。系统采用"检测→评估→报告"三层架构。

**Tech Stack:** Python 3.14, SQLite (via existing database.py), Jinja2 (optional for HTML reports), Matplotlib (optional for charts)

---

## 文件结构设计

| 文件路径 | 职责 |
|---------|------|
| `framework/output_detector.py` | 核心检测引擎：整合多源数据，计算成果指标 |
| `framework/output_reports.py` | 报告生成器：JSON/Markdown/HTML格式输出 |
| `framework/output_charts.py` | 可视化：学习曲线、知识掌握雷达图 |
| `scripts/db_admin.py` | 扩展CLI：新增 output 子命令 |
| `tests/test_output_detector.py` | 单元测试：检测逻辑验证 |
| `tests/test_output_reports.py` | 单元测试：报告生成验证 |

---

## Task 1: 核心检测引擎 (output_detector.py)

**Files:**
- Create: `framework/output_detector.py`

- [ ] **Step 1: 创建模块骨架和导入**

```python
#!/usr/bin/env python3
"""学生学习成果输出检测引擎"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Optional, Any
from datetime import datetime
from framework.database import db

__all__ = [
    "OutputDetector",
    "detect_student_output",
    "generate_output_report",
]
```

- [ ] **Step 2: 实现 OutputDetector 类**

```python
class OutputDetector:
    """学生学习成果检测器"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self._cache: Dict[str, Any] = {}

    def _load(self, key: str) -> Any:
        """懒加载数据"""
        if key not in self._cache:
            self._cache[key] = self._fetch(key)
        return self._cache[key]

    def _fetch(self, key: str) -> Any:
        """从数据库获取数据"""
        if key == "thoughts":
            return db.get_thoughts(user_id=self.user_id, limit=500)
        elif key == "ai_sessions":
            return db.get_ai_sessions(user_id=self.user_id, limit=100)
        elif key == "concept_progress":
            return db.get_concept_progress(user_id=self.user_id)
        elif key == "stats":
            return db.get_stats(user_id=self.user_id)
        elif key == "answers":
            return db.get_answers(user_id=self.user_id, limit=500)
        elif key == "daily_stats":
            return db.get_daily_stats(user_id=self.user_id, days=30)
        elif key == "tasks":
            return db.get_user_tasks(self.user_id)
        elif key == "insights":
            return db.get_learning_insights(user_id=self.user_id)
        return None

    def get_output_score(self) -> Dict:
        """计算综合输出分数 (0-100)"""
        thoughts = self._load("thoughts")
        ai_sessions = self._load("ai_sessions")
        concept_progress = self._load("concept_progress")
        stats = self._load("stats")

        # 思考质量分 (30%)
        thought_score = self._calc_thought_score(thoughts)

        # AI会话产出分 (25%)
        ai_score = self._calc_ai_session_score(ai_sessions)

        # 概念掌握分 (30%)
        concept_score = concept_progress["overall_progress"]

        # 答题正确率分 (15%)
        answer_score = stats.get("accuracy", 0)

        total = (
            thought_score * 0.30
            + ai_score * 0.25
            + concept_score * 0.30
            + answer_score * 0.15
        )

        return {
            "user_id": self.user_id,
            "total_score": round(total, 2),
            "thought_score": round(thought_score, 2),
            "ai_score": round(ai_score, 2),
            "concept_score": round(concept_score, 2),
            "answer_score": round(answer_score, 2),
            "weights": {
                "thought": 0.30,
                "ai_session": 0.25,
                "concept": 0.30,
                "answer": 0.15,
            },
        }

    def _calc_thought_score(self, thoughts: List[Dict]) -> float:
        """计算思考质量分 (0-100)"""
        if not thoughts:
            return 0.0
        total = len(thoughts)
        # 思考数量分 (40%)
        count_score = min(100, total / 10 * 100)
        # 思考类型多样性分 (30%)
        types = set(t["thought_type"] for t in thoughts)
        diversity_score = min(100, len(types) / 4 * 100)
        # AI回复率分 (30%)
        replied = sum(1 for t in thoughts if t.get("ai_feedback"))
        reply_rate = replied / total if total > 0 else 0
        reply_score = reply_rate * 100
        return count_score * 0.4 + diversity_score * 0.3 + reply_score * 0.3

    def _calc_ai_session_score(self, sessions: List[Dict]) -> float:
        """计算AI会话产出分 (0-100)"""
        if not sessions:
            return 0.0
        completed = [s for s in sessions if s["status"] == "completed"]
        if not completed:
            return 0.0
        # 会话完成率 (40%)
        completion_rate = len(completed) / len(sessions)
        completion_score = completion_rate * 100
        # 平均轮次深度 (30%)
        avg_turns = sum(s["total_thoughts"] for s in completed) / len(completed)
        depth_score = min(100, avg_turns / 5 * 100)
        # 平均用时 (30%)
        avg_time = sum(s["time_spent"] for s in completed) / len(completed) / 60  # 分钟
        time_score = min(100, avg_time / 10 * 100)
        return completion_score * 0.4 + depth_score * 0.3 + time_score * 0.3

    def detect_thinking_patterns(self) -> Dict:
        """检测思维模式"""
        thoughts = self._load("thoughts")
        if not thoughts:
            return {"pattern": "unknown", "confidence": 0, "details": "无思考记录"}

        type_counts = {}
        for t in thoughts:
            t_type = t["thought_type"]
            type_counts[t_type] = type_counts.get(t_type, 0) + 1

        dominant = max(type_counts, key=type_counts.get)
        total = sum(type_counts.values())
        confidence = type_counts[dominant] / total

        patterns = {
            "question_heavy": "question_heavy",
            "idea_heavy": "idea_generator",
            "conclusion_heavy": "conclusion_focused",
            "balanced": "balanced_thinker",
        }

        if confidence > 0.6:
            pattern = patterns.get(f"{dominant}_heavy", "balanced")
        else:
            pattern = "balanced"

        return {
            "pattern": pattern,
            "confidence": round(confidence, 2),
            "type_distribution": type_counts,
            "total_thoughts": total,
        }

    def detect_learning_style(self) -> Dict:
        """检测学习风格"""
        sessions = self._load("ai_sessions")
        stats = self._load("stats")
        concept = self._load("concept_progress")

        styles = {}

        # 探究型学习者：高AI会话参与
        if sessions:
            exploration = sum(1 for s in sessions if s["session_type"] == "exploration")
            styles["explorer"] = exploration / len(sessions) if sessions else 0

        # 实践型学习者：高答题量
        if stats:
            styles["practitioner"] = stats.get("total_answers", 0) / 100

        # 反思型学习者：高思考质量
        thoughts = self._load("thoughts")
        if thoughts:
            ideas = sum(1 for t in thoughts if t["thought_type"] == "idea")
            styles["reflector"] = ideas / len(thoughts) if thoughts else 0

        # 总结型学习者：高结论输出
        if thoughts:
            conclusions = sum(1 for t in thoughts if t["thought_type"] == "conclusion")
            styles["synthesizer"] = conclusions / len(thoughts) if thoughts else 0

        # 确定主导风格
        dominant = max(styles, key=styles.get) if styles else "unknown"
        return {
            "dominant_style": dominant,
            "style_scores": {k: round(v, 2) for k, v in styles.items()},
        }

    def generate_weakness_report(self) -> Dict:
        """生成弱点分析报告"""
        concept = self._load("concept_progress")
        insights = self._load("insights")
        thoughts = self._load("thoughts")

        weaknesses = []

        # 知识点弱点
        if concept.get("difficult"):
            for node in concept.get("nodes", []):
                if node["state"] == "difficult":
                    weaknesses.append({
                        "type": "concept",
                        "target": node["node_id"],
                        "name": node["name"],
                        "level": round(node["understanding"], 2),
                        "suggestion": "加强基础练习，使用AI辅助理解",
                    })

        # 思维模式弱点
        if thoughts:
            wrong_count = sum(1 for t in thoughts if t.get("correctness_hint") == "wrong")
            if wrong_count > len(thoughts) * 0.3:
                weaknesses.append({
                    "type": "thinking",
                    "target": "critical_thinking",
                    "name": "批判性思维",
                    "level": round(1 - wrong_count / len(thoughts), 2),
                    "suggestion": "增加多角度思考练习",
                })

        # 学习投入弱点
        if insights.get("hint_dependency", 0) > 0.3:
            weaknesses.append({
                "type": "independence",
                "target": "self_learning",
                "name": "自主学习",
                "level": round(1 - insights["hint_dependency"], 2),
                "suggestion": "减少提示依赖，尝试独立推理",
            })

        return {
            "user_id": self.user_id,
            "weaknesses": weaknesses,
            "total_weaknesses": len(weaknesses),
            "risk_level": "high" if len(weaknesses) > 3 else ("medium" if len(weaknesses) > 1 else "low"),
        }

    def generate_achievement_report(self) -> Dict:
        """生成学习成果报告"""
        score = self.get_output_score()
        patterns = self.detect_thinking_patterns()
        styles = self.detect_learning_style()
        weaknesses = self.generate_weakness_report()
        concept = self._load("concept_progress")
        stats = self._load("stats")

        return {
            "report_id": f"output_{self.user_id}_{int(time.time())}",
            "user_id": self.user_id,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "overall_score": score,
            "thinking_patterns": patterns,
            "learning_style": styles,
            "weaknesses": weaknesses,
            "knowledge_mastery": {
                "total_nodes": concept["total_nodes"],
                "mastered": concept["mastered"],
                "learning": concept["learning"],
                "difficult": concept["difficult"],
                "progress": concept["overall_progress"],
            },
            "learning_stats": stats,
            "summary": self._generate_summary(score, patterns, styles, weaknesses),
        }

    def _generate_summary(self, score: Dict, patterns: Dict, styles: Dict, weaknesses: Dict) -> str:
        """生成文本摘要"""
        total = score["total_score"]
        if total >= 80:
            level = "优秀"
            comment = "学习成果显著，继续保持！"
        elif total >= 60:
            level = "良好"
            comment = "基础扎实，可进一步提升。"
        elif total >= 40:
            level = "中等"
            comment = "需要加强练习，重点关注薄弱环节。"
        else:
            level = "待提高"
            comment = "建议重新开始学习路径，打好基础。"

        return f"综合评分: {total:.1f}分 ({level})\n思维模式: {patterns['pattern']}\n主导风格: {styles['dominant_style']}\n弱点数量: {weaknesses['total_weaknesses']}\n{comment}"
```

- [ ] **Step 3: 实现便捷函数**

```python
def detect_student_output(user_id: int) -> Dict:
    """检测学生学习成果"""
    detector = OutputDetector(user_id)
    return detector.generate_achievement_report()

def generate_output_report(user_id: int, format: str = "json") -> str:
    """生成学习成果报告"""
    from framework.output_reports import OutputReportGenerator
    generator = OutputReportGenerator(user_id)
    return generator.generate(format)
```

- [ ] **Step 4: 验证语法**

```bash
python -m py_compile framework/output_detector.py
```

---

## Task 2: 报告生成器 (output_reports.py)

**Files:**
- Create: `framework/output_reports.py`

- [ ] **Step 1: 创建模块骨架**

```python
#!/usr/bin/env python3
"""学生学习成果报告生成器"""
import sys
import os
import json
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from framework.output_detector import detect_student_output

__all__ = ["OutputReportGenerator"]
```

- [ ] **Step 2: 实现 OutputReportGenerator 类**

```python
class OutputReportGenerator:
    """学习成果报告生成器"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.data = detect_student_output(user_id)

    def generate(self, format: str = "json") -> str:
        """生成报告"""
        if format == "json":
            return self._to_json()
        elif format == "markdown":
            return self._to_markdown()
        elif format == "html":
            return self._to_html()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _to_json(self) -> str:
        return json.dumps(self.data, ensure_ascii=False, indent=2)

    def _to_markdown(self) -> str:
        lines = []
        lines.append(f"# 学生学习成果报告")
        lines.append(f"")
        lines.append(f"**用户ID:** {self.user_id}")
        lines.append(f"**生成时间:** {self.data['generated_at']}")
        lines.append(f"")
        lines.append(f"## 综合评分")
        lines.append(f"- 总分: {self.data['overall_score']['total_score']:.2f}")
        lines.append(f"- 思考质量: {self.data['overall_score']['thought_score']:.2f}")
        lines.append(f"- AI会话产出: {self.data['overall_score']['ai_score']:.2f}")
        lines.append(f"- 概念掌握: {self.data['overall_score']['concept_score']:.2f}")
        lines.append(f"- 答题正确率: {self.data['overall_score']['answer_score']:.2f}")
        lines.append(f"")
        lines.append(f"## 思维模式")
        lines.append(f"- 模式: {self.data['thinking_patterns']['pattern']}")
        lines.append(f"- 置信度: {self.data['thinking_patterns']['confidence']}")
        lines.append(f"")
        lines.append(f"## 知识掌握")
        km = self.data['knowledge_mastery']
        lines.append(f"- 总节点: {km['total_nodes']}")
        lines.append(f"- 已掌握: {km['mastered']}")
        lines.append(f"- 学习中: {km['learning']}")
        lines.append(f"- 困难: {km['difficult']}")
        lines.append(f"- 进度: {km['progress']:.1f}%")
        lines.append(f"")
        if self.data['weaknesses']['weaknesses']:
            lines.append(f"## 薄弱环节")
            for w in self.data['weaknesses']['weaknesses']:
                lines.append(f"- [{w['type']}] {w['name']}: {w['level']:.2f}")
        lines.append(f"")
        lines.append(f"## 总结")
        lines.append(f"{self.data['summary']}")
        return "\n".join(lines)

    def _to_html(self) -> str:
        """生成HTML报告（基础版）"""
        score = self.data['overall_score']
        km = self.data['knowledge_mastery']
        weaknesses = self.data['weaknesses']['weaknesses']

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>学生学习成果报告 - 用户{self.user_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .score {{ font-size: 48px; color: #2196F3; }}
        .section {{ margin: 20px 0; padding: 20px; border-radius: 8px; }}
        .score-card {{ background: #f5f5f5; padding: 15px; margin: 10px 0; }}
        .weakness {{ color: #f44336; }}
        .good {{ color: #4CAF50; }}
    </style>
</head>
<body>
    <h1>学生学习成果报告</h1>
    <p>用户ID: {self.user_id} | 生成时间: {self.data['generated_at']}</p>

    <div class="section">
        <h2>综合评分</h2>
        <div class="score">{score['total_score']:.2f}</div>
        <div class="score-card">思考质量: {score['thought_score']:.2f}</div>
        <div class="score-card">AI会话产出: {score['ai_score']:.2f}</div>
        <div class="score-card">概念掌握: {score['concept_score']:.2f}</div>
        <div class="score-card">答题正确率: {score['answer_score']:.2f}</div>
    </div>

    <div class="section">
        <h2>知识掌握</h2>
        <p>进度: {km['progress']:.1f}% | 掌握: {km['mastered']}/{km['total_nodes']}</p>
    </div>

    <div class="section">
        <h2>薄弱环节</h2>
        {''.join(f'<p class="weakness">- {w["name"]}: {w["level"]:.2f}</p>' for w in weaknesses)}
        {'' if weaknesses else '<p class="good">暂无薄弱环节</p>'}
    </div>

    <div class="section">
        <h2>总结</h2>
        <p>{self.data['summary']}</p>
    </div>
</body>
</html>"""
        return html
```

- [ ] **Step 3: 验证语法**

```bash
python -m py_compile framework/output_reports.py
```

---

## Task 3: 可视化模块 (output_charts.py)

**Files:**
- Create: `framework/output_charts.py`

- [ ] **Step 1: 创建模块骨架**

```python
#!/usr/bin/env python3
"""学生学习成果可视化"""
import sys
import os
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from framework.output_detector import detect_student_output

__all__ = ["OutputChartGenerator"]
```

- [ ] **Step 2: 实现 OutputChartGenerator 类**

```python
class OutputChartGenerator:
    """学习成果可视化生成器"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.data = detect_student_output(user_id)

    def generate_radial_chart(self, output_path: str) -> str:
        """生成雷达图（知识掌握维度）"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.font_manager as fm
        except ImportError:
            return "matplotlib未安装，无法生成图表"

        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        # 维度数据
        categories = ['思考质量', 'AI会话', '概念掌握', '答题正确率']
        values = [
            self.data['overall_score']['thought_score'],
            self.data['overall_score']['ai_score'],
            self.data['overall_score']['concept_score'],
            self.data['overall_score']['answer_score'],
        ]

        # 闭合雷达图
        values += values[:1]
        angles = [n / float(len(categories)) * 2 * plt.pi for n in range(len(categories))]
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        ax.plot(angles, values, 'o-', linewidth=2, color='#2196F3')
        ax.fill(angles, values, alpha=0.25, color='#2196F3')
        ax.set_thetagrids([a * 180 / plt.pi for a in angles[:-1]], categories)
        ax.set_ylim(0, 100)
        ax.set_title(f"用户{self.user_id}学习成果雷达图", fontsize=14)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        return output_path

    def generate_progress_chart(self, output_path: str) -> str:
        """生成学习进度柱状图"""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return "matplotlib未安装，无法生成图表"

        km = self.data['knowledge_mastery']
        labels = ['已掌握', '学习中', '困难', '未开始']
        values = [km['mastered'], km['learning'], km['difficult'], km['total_nodes'] - km['studied']]
        colors = ['#4CAF50', '#FF9800', '#f44336', '#9E9E9E']

        fig, ax = plt.subplots(figsize=(8, 4))
        bars = ax.bar(labels, values, color=colors, edgecolor='white', linewidth=1.5)

        # 添加数值标签
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                   str(val), ha='center', va='bottom', fontsize=12, fontweight='bold')

        ax.set_title(f"用户{self.user_id}知识点掌握情况", fontsize=14)
        ax.set_ylabel('节点数量')
        ax.set_ylim(0, max(values) * 1.2)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        return output_path
```

- [ ] **Step 3: 验证语法**

```bash
python -m py_compile framework/output_charts.py
```

---

## Task 4: 扩展 CLI (db_admin.py)

**Files:**
- Modify: `scripts/db_admin.py`

- [ ] **Step 1: 添加 output 子命令解析**

在 `subparsers` 中添加：

```python
# output
p_output = subparsers.add_parser("output", help="学生学习成果检测")
p_output.add_argument("--user-id", type=int, dest="user_id")
p_output.add_argument("--format", choices=["json", "markdown", "html"], default="json")
p_output.add_argument("--output", help="输出文件路径")
```

- [ ] **Step 2: 添加命令处理器**

```python
def cmd_output(args):
    """学生学习成果检测"""
    from framework.output_detector import detect_student_output
    from framework.output_reports import OutputReportGenerator

    user_id = args.user_id or 1
    report = detect_student_output(user_id)

    if args.output:
        generator = OutputReportGenerator(user_id)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(generator.generate(args.format))
        print(f"[OK] 报告已保存: {args.output}")
    else:
        if args.format == "json":
            import json
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            generator = OutputReportGenerator(user_id)
            print(generator.generate(args.format))
```

- [ ] **Step 3: 注册命令**

在 `commands` 字典中添加：

```python
"output": cmd_output,
```

- [ ] **Step 4: 验证**

```bash
python scripts/db_admin.py output --user-id 2
```

---

## Task 5: 单元测试 (test_output_detector.py)

**Files:**
- Create: `tests/test_output_detector.py`

- [ ] **Step 1: 测试模块骨架**

```python
#!/usr/bin/env python3
"""学生学习成果检测系统单元测试"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.output_detector import OutputDetector, detect_student_output
from framework.database import db


class TestOutputDetector(unittest.TestCase):
    """输出检测器测试"""

    def setUp(self):
        db.init()
        self.detector = OutputDetector(user_id=2)

    def test_detect_output_score(self):
        """测试综合评分计算"""
        score = self.detector.get_output_score()
        self.assertIn('total_score', score)
        self.assertIn('thought_score', score)
        self.assertIn('ai_score', score)
        self.assertIn('concept_score', score)
        self.assertIn('answer_score', score)
        self.assertIsInstance(score['total_score'], float)
        self.assertGreaterEqual(score['total_score'], 0)
        self.assertLessEqual(score['total_score'], 100)

    def test_detect_thinking_patterns(self):
        """测试思维模式检测"""
        patterns = self.detector.detect_thinking_patterns()
        self.assertIn('pattern', patterns)
        self.assertIn('confidence', patterns)
        self.assertIn('type_distribution', patterns)
        self.assertGreaterEqual(patterns['confidence'], 0)
        self.assertLessEqual(patterns['confidence'], 1)

    def test_detect_learning_style(self):
        """测试学习风格检测"""
        styles = self.detector.detect_learning_style()
        self.assertIn('dominant_style', styles)
        self.assertIn('style_scores', styles)

    def test_generate_weakness_report(self):
        """测试弱点分析报告"""
        weaknesses = self.detector.generate_weakness_report()
        self.assertIn('weaknesses', weaknesses)
        self.assertIn('total_weaknesses', weaknesses)
        self.assertIn('risk_level', weaknesses)
        self.assertIn(weaknesses['risk_level'], ['low', 'medium', 'high'])

    def test_generate_achievement_report(self):
        """测试完整报告生成"""
        report = self.detector.generate_achievement_report()
        self.assertIn('report_id', report)
        self.assertIn('overall_score', report)
        self.assertIn('thinking_patterns', report)
        self.assertIn('learning_style', report)
        self.assertIn('weaknesses', report)
        self.assertIn('knowledge_mastery', report)
        self.assertIn('summary', report)

    def test_detect_student_output_function(self):
        """测试便捷函数"""
        result = detect_student_output(user_id=2)
        self.assertIsInstance(result, dict)
        self.assertEqual(result['user_id'], 2)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 运行测试**

```bash
python -m pytest tests/test_output_detector.py -v
```

---

## Task 6: 单元测试 (test_output_reports.py)

**Files:**
- Create: `tests/test_output_reports.py`

- [ ] **Step 1: 测试模块骨架**

```python
#!/usr/bin/env python3
"""学习成果报告生成器单元测试"""
import sys
import os
import unittest
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.output_reports import OutputReportGenerator
from framework.database import db


class TestOutputReports(unittest.TestCase):
    """报告生成器测试"""

    def setUp(self):
        db.init()
        self.generator = OutputReportGenerator(user_id=2)

    def test_generate_json(self):
        """测试JSON格式报告"""
        report = self.generator.generate(format="json")
        data = json.loads(report)
        self.assertIn('overall_score', data)
        self.assertIn('thinking_patterns', data)

    def test_generate_markdown(self):
        """测试Markdown格式报告"""
        report = self.generator.generate(format="markdown")
        self.assertIn('# 学生学习成果报告', report)
        self.assertIn('综合评分', report)
        self.assertIn('知识掌握', report)

    def test_generate_html(self):
        """测试HTML格式报告"""
        report = self.generator.generate(format="html")
        self.assertIn('<!DOCTYPE html>', report)
        self.assertIn('<title>', report)
        self.assertIn('学生学习成果报告', report)

    def test_generate_invalid_format(self):
        """测试无效格式"""
        with self.assertRaises(ValueError):
            self.generator.generate(format="xml")

    def test_report_content_consistency(self):
        """测试报告内容一致性"""
        report_json = self.generator.generate(format="json")
        data = json.loads(report_json)
        self.assertEqual(data['user_id'], 2)
        self.assertIsInstance(data['overall_score']['total_score'], float)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 运行测试**

```bash
python -m pytest tests/test_output_reports.py -v
```

---

## Task 7: 端到端集成测试

**Files:**
- Create: `tests/test_output_integration.py`

- [ ] **Step 1: 集成测试**

```python
#!/usr/bin/env python3
"""学生学习成果检测系统集成测试"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.output_detector import detect_student_output
from framework.output_reports import OutputReportGenerator
from framework.output_charts import OutputChartGenerator


def test_full_pipeline():
    """测试完整流程"""
    print("=" * 60)
    print("学生学习成果检测系统 - 端到端测试")
    print("=" * 60)

    # 初始化
    db.init()
    print("\n[1] 数据库初始化: OK")

    # 检测
    report = detect_student_output(user_id=2)
    print(f"[2] 成果检测: OK")
    print(f"    总分: {report['overall_score']['total_score']:.2f}")

    # 报告生成
    generator = OutputReportGenerator(user_id=2)
    json_report = generator.generate(format="json")
    md_report = generator.generate(format="markdown")
    html_report = generator.generate(format="html")
    print(f"[3] 报告生成: OK")
    print(f"    JSON: {len(json_report)} 字符")
    print(f"    Markdown: {len(md_report)} 字符")
    print(f"    HTML: {len(html_report)} 字符")

    # 可视化
    chart_gen = OutputChartGenerator(user_id=2)
    chart_path = os.path.join(os.path.dirname(__file__), "..", "outputs", "radar_chart.png")
    os.makedirs(os.path.dirname(chart_path), exist_ok=True)
    result = chart_gen.generate_radial_chart(chart_path)
    if result.endswith(".png"):
        print(f"[4] 图表生成: OK")
        print(f"    路径: {result}")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_full_pipeline()
```

- [ ] **Step 2: 运行测试**

```bash
python tests/test_output_integration.py
```

---

## Task 8: 文档更新

**Files:**
- Modify: `README.md`
- Create: `docs/output_detector.md`

- [ ] **Step 1: 更新 README.md**

在"功能特性"部分添加：

```markdown
### 学习成果检测
- 多维度评分：思考质量、AI会话、概念掌握、答题正确率
- 思维模式检测：探究型、实践型、反思型、总结型
- 学习风格分析：四种学习风格识别
- 弱点报告：自动生成薄弱环节分析
- 多格式报告：JSON、Markdown、HTML
```

- [ ] **Step 2: 创建技术文档**

```markdown
# 学习成果检测系统

## 功能概述

学生学习成果输出检测系统是 LumiLearn 的核心评估模块，通过分析学生的：
- 思考记录（student_thoughts）
- AI学习会话（ai_student_sessions）
- 概念理解（concept_understanding）
- 答题记录（answers）

生成综合评分和详细报告。

## 使用方法

```python
from framework.output_detector import detect_student_output
from framework.output_reports import OutputReportGenerator

# 检测学习成果
report = detect_student_output(user_id=2)
print(f"总分: {report['overall_score']['total_score']}")

# 生成报告
generator = OutputReportGenerator(user_id=2)
print(generator.generate("json"))
print(generator.generate("markdown"))
print(generator.generate("html"))
```

## CLI 使用

```bash
# 查看 JSON 报告
python scripts/db_admin.py output --user-id 2

# 生成 Markdown 报告
python scripts/db_admin.py output --user-id 2 --format markdown

# 保存到文件
python scripts/db_admin.py output --user-id 2 --format html --output report.html
```
```

---

## 验收标准

1. **功能完整**: 所有 8 个 Task 完成，无 TODO
2. **测试通过**: `pytest tests/test_output_*.py -v` 全部通过
3. **语法正确**: `py_compile` 所有新增文件通过
4. **CLI 可用**: `db_admin.py output` 命令正常工作
5. **报告准确**: 检测结果与数据库数据一致
6. **文档完整**: README 和技术文档已更新

---

## 风险与依赖

| 风险 | 缓解措施 |
|------|---------|
| matplotlib 未安装 | 图表生成函数捕获 ImportError，降级为文本输出 |
| 数据库无数据 | 检测函数返回零值而不是报错 |
| 评分权重不合理 | 提供可配置的 weights 参数 |
