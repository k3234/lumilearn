# -*- coding: utf-8 -*-
"""
自适应学习引擎
知识图谱 + 进度追踪 + 智能推荐 + 动态学习路径

核心功能：
- 知识图谱：知识点之间的依赖关系
- 进度追踪：用户学习记录和掌握程度
- 薄弱点分析：识别需要加强的知识点
- 智能推荐：基于当前水平的个性化推荐
- 学习路径：动态生成最优学习顺序

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-06
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class KnowledgeNode:
    """知识图谱节点"""
    id: str
    name: str
    category: str  # geometry, algebra, physics, calculus, statistics
    difficulty: int  # 1-5
    prerequisites: List[str] = field(default_factory=list)
    animation_type: str = "auto"  # 对应的动画类型
    description: str = ""


# ============================================================
# 知识图谱定义
# ============================================================

KNOWLEDGE_GRAPH: Dict[str, KnowledgeNode] = {
    # === 几何 ===
    "triangle_basics": KnowledgeNode(
        id="triangle_basics", name="三角形基础", category="geometry",
        difficulty=1, animation_type="geometry",
        description="三角形的定义、分类、内角和"
    ),
    "pythagorean": KnowledgeNode(
        id="pythagorean", name="勾股定理", category="geometry",
        difficulty=2, prerequisites=["triangle_basics"], animation_type="geometry",
        description="直角三角形的边长关系"
    ),
    "circle_area": KnowledgeNode(
        id="circle_area", name="圆面积", category="geometry",
        difficulty=2, prerequisites=["triangle_basics"], animation_type="geometry",
        description="圆的面积公式推导"
    ),
    "cosine_rule": KnowledgeNode(
        id="cosine_rule", name="余弦定理", category="geometry",
        difficulty=3, prerequisites=["pythagorean"], animation_type="geometry",
        description="任意三角形的边长与角度关系"
    ),

    # === 代数 ===
    "quadratic_formula": KnowledgeNode(
        id="quadratic_formula", name="求根公式", category="algebra",
        difficulty=2, animation_type="formula",
        description="一元二次方程的求根公式推导"
    ),
    "completing_square": KnowledgeNode(
        id="completing_square", name="配方法", category="algebra",
        difficulty=2, prerequisites=["quadratic_formula"], animation_type="formula",
        description="通过配方解二次方程"
    ),
    "polynomial": KnowledgeNode(
        id="polynomial", name="多项式运算", category="algebra",
        difficulty=3, prerequisites=["quadratic_formula"], animation_type="formula",
        description="多项式的加减乘除和因式分解"
    ),

    # === 函数 ===
    "linear_function": KnowledgeNode(
        id="linear_function", name="一次函数", category="functions",
        difficulty=1, animation_type="functions",
        description="y=kx+b 的图像与性质"
    ),
    "quadratic_function": KnowledgeNode(
        id="quadratic_function", name="二次函数", category="functions",
        difficulty=2, prerequisites=["linear_function", "quadratic_formula"],
        animation_type="functions",
        description="y=ax²+bx+c 的图像与性质"
    ),

    # === 物理 ===
    "free_fall": KnowledgeNode(
        id="free_fall", name="自由落体", category="physics",
        difficulty=2, prerequisites=["quadratic_function"], animation_type="physics",
        description="匀加速直线运动"
    ),
    "light_refraction": KnowledgeNode(
        id="light_refraction", name="光的折射", category="physics",
        difficulty=3, prerequisites=["triangle_basics"], animation_type="physics",
        description="斯涅尔定律与折射现象"
    ),

    # === 统计 ===
    "mean_median": KnowledgeNode(
        id="mean_median", name="均值与中位数", category="statistics",
        difficulty=1, animation_type="statistics",
        description="描述性统计基础"
    ),
    "normal_distribution": KnowledgeNode(
        id="normal_distribution", name="正态分布", category="statistics",
        difficulty=3, prerequisites=["mean_median"], animation_type="statistics",
        description="正态分布的性质与应用"
    ),
}


class AdaptiveLearningEngine:
    """自适应学习引擎"""

    def __init__(self, data_dir: str = "data/learning"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.graph = KNOWLEDGE_GRAPH.copy()
        self._progress: Dict[str, Dict] = {}
        self._load_progress()

    # ============================================================
    # 进度管理
    # ============================================================

    def _progress_file(self) -> Path:
        return self.data_dir / "learning_progress.json"

    def _load_progress(self):
        """加载学习进度"""
        pf = self._progress_file()
        if pf.exists():
            try:
                self._progress = json.loads(pf.read_text("utf-8"))
            except (json.JSONDecodeError, IOError):
                self._progress = {}

    def _save_progress(self):
        """保存学习进度"""
        self._progress_file().write_text(
            json.dumps(self._progress, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def record_learning(self, user_id: str, node_id: str,
                        score: float = 1.0, time_spent: float = 0):
        """
        记录学习活动

        Args:
            user_id: 用户标识
            node_id: 知识点ID
            score: 学习得分 (0-1)
            time_spent: 学习时长（秒）
        """
        uid = user_id or "default"
        if uid not in self._progress:
            self._progress[uid] = {"nodes": {}, "history": []}

        node = self.graph.get(node_id)
        if not node:
            return

        # 更新节点掌握度
        if node_id not in self._progress[uid]["nodes"]:
            self._progress[uid]["nodes"][node_id] = {
                "mastery": 0.0,
                "attempts": 0,
                "total_time": 0,
                "last_study": None
            }

        entry = self._progress[uid]["nodes"][node_id]
        # 指数移动平均更新掌握度
        alpha = 0.3
        entry["mastery"] = entry["mastery"] * (1 - alpha) + score * alpha
        entry["attempts"] += 1
        entry["total_time"] += time_spent
        entry["last_study"] = time.time()

        # 记录历史
        self._progress[uid]["history"].append({
            "node_id": node_id,
            "score": score,
            "time_spent": time_spent,
            "timestamp": time.time()
        })

        self._save_progress()

    def get_progress(self, user_id: str = "default") -> Dict:
        """获取用户学习进度"""
        uid = user_id or "default"
        progress = self._progress.get(uid, {"nodes": {}, "history": []})

        # 计算总体统计
        nodes = progress.get("nodes", {})
        total_nodes = len(self.graph)
        mastered = sum(1 for n in nodes.values() if n.get("mastery", 0) >= 0.8)
        learning = sum(1 for n in nodes.values() if 0.3 <= n.get("mastery", 0) < 0.8)

        return {
            "user_id": uid,
            "total_knowledge_nodes": total_nodes,
            "studied_nodes": len(nodes),
            "mastered_nodes": mastered,
            "learning_nodes": learning,
            "not_started": total_nodes - len(nodes),
            "overall_progress": round(mastered / max(total_nodes, 1) * 100, 1),
            "nodes": {
                nid: {
                    "name": self.graph[nid].name if nid in self.graph else nid,
                    "category": self.graph[nid].category if nid in self.graph else "unknown",
                    "difficulty": self.graph[nid].difficulty if nid in self.graph else 0,
                    **info
                }
                for nid, info in nodes.items()
            },
            "recent_history": progress.get("history", [])[-20:]
        }

    # ============================================================
    # 薄弱点分析
    # ============================================================

    def analyze_weaknesses(self, user_id: str = "default") -> List[Dict]:
        """分析薄弱知识点"""
        uid = user_id or "default"
        nodes = self._progress.get(uid, {}).get("nodes", {})

        weaknesses = []
        for node_id, info in nodes.items():
            mastery = info.get("mastery", 0)
            if mastery < 0.6:
                node = self.graph.get(node_id)
                if node:
                    weaknesses.append({
                        "node_id": node_id,
                        "name": node.name,
                        "category": node.category,
                        "difficulty": node.difficulty,
                        "mastery": round(mastery, 2),
                        "attempts": info.get("attempts", 0),
                        "severity": "high" if mastery < 0.3 else "medium"
                    })

        # 按掌握度排序（最低优先）
        weaknesses.sort(key=lambda x: x["mastery"])
        return weaknesses

    # ============================================================
    # 智能推荐
    # ============================================================

    def recommend_next(self, user_id: str = "default", count: int = 5) -> List[Dict]:
        """
        推荐下一个学习知识点

        策略：
        1. 优先推荐可学习（前置条件满足）的知识点
        2. 按难度和用户水平匹配
        3. 薄弱点优先
        """
        uid = user_id or "default"
        nodes = self._progress.get(uid, {}).get("nodes", {})

        # 计算用户平均水平
        if nodes:
            avg_mastery = sum(n["mastery"] for n in nodes.values()) / len(nodes)
        else:
            avg_mastery = 0

        candidates = []
        for node_id, node in self.graph.items():
            # 已掌握的跳过
            if nodes.get(node_id, {}).get("mastery", 0) >= 0.85:
                continue

            # 检查前置条件
            prereqs_met = True
            for prereq_id in node.prerequisites:
                if nodes.get(prereq_id, {}).get("mastery", 0) < 0.7:
                    prereqs_met = False
                    break

            if not prereqs_met:
                continue

            current_mastery = nodes.get(node_id, {}).get("mastery", 0)

            # 计算推荐分数
            score = 0.0
            # 难度匹配：推荐略高于当前水平的
            difficulty_match = 1.0 - abs(node.difficulty - (avg_mastery * 5 + 1)) / 5
            score += difficulty_match * 0.3
            # 薄弱点加分
            if current_mastery < 0.5:
                score += (0.5 - current_mastery) * 0.4
            # 未学习的新知识点加分
            if current_mastery == 0:
                score += 0.3

            candidates.append({
                "node_id": node_id,
                "name": node.name,
                "category": node.category,
                "difficulty": node.difficulty,
                "current_mastery": round(current_mastery, 2),
                "animation_type": node.animation_type,
                "description": node.description,
                "recommendation_score": round(score, 3)
            })

        # 按推荐分数排序
        candidates.sort(key=lambda x: x["recommendation_score"], reverse=True)
        return candidates[:count]

    # ============================================================
    # 学习路径生成
    # ============================================================

    def generate_learning_path(self, user_id: str = "default",
                               target_category: str = None) -> List[Dict]:
        """
        生成最优学习路径

        使用拓扑排序 + 薄弱点优先策略
        """
        uid = user_id or "default"
        nodes = self._progress.get(uid, {}).get("nodes", {})

        # 过滤类别
        if target_category:
            available = {
                nid: node for nid, node in self.graph.items()
                if node.category == target_category
            }
        else:
            available = self.graph.copy()

        # 拓扑排序
        in_degree = {nid: len(node.prerequisites) for nid, node in available.items()}
        adj = defaultdict(list)
        for nid, node in available.items():
            for prereq in node.prerequisites:
                if prereq in available:
                    adj[prereq].append(nid)

        # 优先队列：薄弱点优先
        path = []
        visited = set()

        while len(path) < len(available):
            # 找入度为0的节点
            candidates = [nid for nid, deg in in_degree.items()
                          if deg == 0 and nid not in visited]

            if not candidates:
                # 有环或无法继续，加入剩余节点
                remaining = [nid for nid in available if nid not in visited]
                for nid in remaining:
                    node = available[nid]
                    path.append({
                        "node_id": nid,
                        "name": node.name,
                        "category": node.category,
                        "difficulty": node.difficulty,
                        "mastery": round(nodes.get(nid, {}).get("mastery", 0), 2),
                        "animation_type": node.animation_type,
                        "description": node.description,
                        "step": len(path) + 1
                    })
                    visited.add(nid)
                break

            # 按薄弱程度排序（掌握度低的优先）
            candidates.sort(key=lambda nid: nodes.get(nid, {}).get("mastery", 0))

            # 取第一个（最薄弱的）
            next_node = candidates[0]
            node = available[next_node]

            path.append({
                "node_id": next_node,
                "name": node.name,
                "category": node.category,
                "difficulty": node.difficulty,
                "mastery": round(nodes.get(next_node, {}).get("mastery", 0), 2),
                "animation_type": node.animation_type,
                "description": node.description,
                "step": len(path) + 1
            })

            visited.add(next_node)

            # 更新入度
            for neighbor in adj[next_node]:
                in_degree[neighbor] -= 1

            # 标记已处理
            in_degree[next_node] = -1

        return path

    # ============================================================
    # 知识图谱查询
    # ============================================================

    def get_knowledge_graph(self) -> Dict:
        """获取完整知识图谱"""
        nodes = []
        edges = []
        for nid, node in self.graph.items():
            nodes.append({
                "id": nid,
                "name": node.name,
                "category": node.category,
                "difficulty": node.difficulty,
                "animation_type": node.animation_type,
                "description": node.description
            })
            for prereq in node.prerequisites:
                edges.append({"from": prereq, "to": nid})

        return {
            "nodes": nodes,
            "edges": edges,
            "categories": list(set(n["category"] for n in nodes))
        }

    def get_node_detail(self, node_id: str) -> Optional[Dict]:
        """获取知识点详情"""
        node = self.graph.get(node_id)
        if not node:
            return None

        # 获取依赖关系
        dependents = [
            nid for nid, n in self.graph.items()
            if node_id in n.prerequisites
        ]

        return {
            "id": node.id,
            "name": node.name,
            "category": node.category,
            "difficulty": node.difficulty,
            "animation_type": node.animation_type,
            "description": node.description,
            "prerequisites": [
                {"id": pid, "name": self.graph[pid].name}
                for pid in node.prerequisites if pid in self.graph
            ],
            "dependents": [
                {"id": did, "name": self.graph[did].name}
                for did in dependents
            ]
        }

    def get_statistics(self, user_id: str = "default") -> Dict:
        """获取学习统计"""
        uid = user_id or "default"
        nodes = self._progress.get(uid, {}).get("nodes", {})
        history = self._progress.get(uid, {}).get("history", [])

        # 类别统计
        category_stats = defaultdict(lambda: {"total": 0, "mastered": 0, "avg_mastery": 0})
        for nid, node in self.graph.items():
            cat = node.category
            category_stats[cat]["total"] += 1
            mastery = nodes.get(nid, {}).get("mastery", 0)
            if mastery >= 0.8:
                category_stats[cat]["mastered"] += 1
            category_stats[cat]["avg_mastery"] += mastery

        for cat in category_stats:
            total = category_stats[cat]["total"]
            if total > 0:
                category_stats[cat]["avg_mastery"] = round(
                    category_stats[cat]["avg_mastery"] / total, 2
                )

        # 时间统计
        total_time = sum(n.get("total_time", 0) for n in nodes.values())
        total_attempts = sum(n.get("attempts", 0) for n in nodes.values())

        # 最近学习
        recent = history[-10:] if history else []

        return {
            "user_id": uid,
            "total_study_time_seconds": round(total_time, 1),
            "total_attempts": total_attempts,
            "category_stats": dict(category_stats),
            "weaknesses_count": len(self.analyze_weaknesses(uid)),
            "recent_activity": recent
        }


# 全局单例
_engine: Optional[AdaptiveLearningEngine] = None


def get_adaptive_engine() -> AdaptiveLearningEngine:
    """获取自适应学习引擎单例"""
    global _engine
    if _engine is None:
        _engine = AdaptiveLearningEngine()
    return _engine