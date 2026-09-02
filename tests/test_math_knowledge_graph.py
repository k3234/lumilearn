# -*- coding: utf-8 -*-
"""
tests/test_math_knowledge_graph.py
高中数学知识点图谱验证
覆盖：节点数量、板块覆盖、依赖链完整性（DAG无环）、common_mistakes 字段
"""
import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from framework.services.adaptive_learning import KNOWLEDGE_GRAPH, KnowledgeNode


# ========== 节点数量 ==========

class TestKnowledgeNodeCount:
    """验证知识点数量"""

    def test_total_nodes_at_least_50(self):
        """KNOWLEDGE_GRAPH 包含至少 50 个节点"""
        assert len(KNOWLEDGE_GRAPH) >= 50, f"知识点数量 {len(KNOWLEDGE_GRAPH)} < 50"

    def test_exact_node_count(self):
        """知识点数量为 65（13 原有 + 52 新增）"""
        assert len(KNOWLEDGE_GRAPH) == 65, f"期望 65 个知识点，实际 {len(KNOWLEDGE_GRAPH)}"


# ========== 板块覆盖 ==========

class TestSectionCoverage:
    """验证 7 大板块覆盖"""

    SECTIONS = {
        "集合与逻辑": [
            "set_concepts", "set_intersection_union", "set_complement",
            "sufficient_necessary", "proposition_quantifier", "inequality_solving"
        ],
        "函数与导数": [
            "function_concept", "domain_range", "function_monotonicity",
            "function_parity", "exponential_function", "logarithm_function",
            "inverse_function", "derivative_concept", "derivative_application",
            "extreme_values", "tangent_line"
        ],
        "三角函数": [
            "arbitrary_angle", "radian_system", "trig_definitions",
            "trig_induction", "trig_graph_property", "trig_transform",
            "solve_triangle", "sine_rule"
        ],
        "数列": [
            "arithmetic_sequence", "geometric_sequence", "sequence_sum",
            "sequence_recursion", "math_induction", "sequence_limit"
        ],
        "向量": [
            "vector_concept", "vector_linear_op", "vector_dot_product",
            "vector_coordinate", "vector_fundamental"
        ],
        "概率统计": [
            "counting_principle", "permutation_combination",
            "probability_definition", "conditional_probability",
            "random_variable", "binomial_distribution",
            "normal_distribution_node", "statistics_charts", "regression_analysis"
        ],
        "解析几何": [
            "line_equation", "circle_equation", "ellipse",
            "hyperbola", "parabola", "coordinate_transform", "conic_section_summary"
        ],
    }

    def test_all_sections_present(self):
        """7 大板块全部存在于知识点图谱"""
        for section, node_ids in self.SECTIONS.items():
            for nid in node_ids:
                assert nid in KNOWLEDGE_GRAPH, f"缺少节点: {nid}（板块：{section}）"

    def test_section_node_counts(self):
        """各板块节点数量完整"""
        for section, node_ids in self.SECTIONS.items():
            found = {nid for nid in node_ids if nid in KNOWLEDGE_GRAPH}
            assert len(found) == len(node_ids), \
                f"板块 '{section}' 节点不完整：缺少 {set(node_ids) - found}"


# ========== 节点字段完整性 ==========

class TestKnowledgeNodeFields:
    """验证每个知识点包含 prerequisites、difficulty、common_mistakes 字段"""

    def test_all_nodes_have_prerequisites_field(self):
        """所有节点有 prerequisites 字段（可为空列表）"""
        for nid, node in KNOWLEDGE_GRAPH.items():
            assert isinstance(node.prerequisites, list), \
                f"节点 {nid} 的 prerequisites 不是 list"

    def test_all_nodes_have_difficulty_field(self):
        """所有节点有 difficulty 字段（1-5）"""
        for nid, node in KNOWLEDGE_GRAPH.items():
            assert isinstance(node.difficulty, int), \
                f"节点 {nid} 的 difficulty 不是 int"
            assert 1 <= node.difficulty <= 5, \
                f"节点 {nid} 的 difficulty={node.difficulty} 不在 1-5 范围内"

    def test_all_nodes_have_common_mistakes_field(self):
        """所有节点有 common_mistakes 字段（可为空列表）"""
        for nid, node in KNOWLEDGE_GRAPH.items():
            assert isinstance(node.common_mistakes, list), \
                f"节点 {nid} 的 common_mistakes 不是 list"

    def test_at_least_some_common_mistakes_populated(self):
        """至少有 10 个节点填写了 common_mistakes"""
        populated = sum(
            1 for node in KNOWLEDGE_GRAPH.values()
            if node.common_mistakes
        )
        assert populated >= 10, f"只有 {populated} 个节点填写了 common_mistakes，期望 >= 10"


# ========== DAG 依赖链完整性 ==========

class TestDAGIntegrity:
    """验证知识图谱为有向无环图（DAG）"""

    def test_no_circular_dependencies(self):
        """依赖链无环"""
        visited = set()
        rec_stack = set()

        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            node = KNOWLEDGE_GRAPH.get(node_id)
            if node:
                for prereq in node.prerequisites:
                    if prereq not in visited:
                        if has_cycle(prereq):
                            return True
                    elif prereq in rec_stack:
                        return True
            rec_stack.discard(node_id)
            return False

        for nid in KNOWLEDGE_GRAPH:
            if nid not in visited:
                assert not has_cycle(nid), f"发现环：从 {nid} 出发"

    def test_all_prerequisites_exist_in_graph(self):
        """所有 prereq 节点都在 KNOWLEDGE_GRAPH 中"""
        all_ids = set(KNOWLEDGE_GRAPH.keys())
        for nid, node in KNOWLEDGE_GRAPH.items():
            for prereq in node.prerequisites:
                assert prereq in all_ids, \
                    f"节点 {nid} 的 prereq '{prereq}' 不存在于图谱中"

    def test_no_self_prerequisite(self):
        """没有节点以自己作为前置条件"""
        for nid, node in KNOWLEDGE_GRAPH.items():
            assert nid not in node.prerequisites, f"节点 {nid} 自引用"


# ========== 节点类型分布 ==========

class TestNodeCategoryDistribution:
    """验证各板块节点数量合理分布"""

    def test_math_sections_only(self):
        """所有高中数学节点 category 在预期范围内"""
        expected_categories = {
            "geometry", "algebra", "functions", "trigonometry",
            "sequences", "vectors", "probability", "statistics",
            "analytic_geometry", "calculus", "logic", "physics",
        }
        for nid, node in KNOWLEDGE_GRAPH.items():
            assert node.category in expected_categories, \
                f"节点 {nid} 的 category='{node.category}' 不在预期集合中"

    def test_high_difficulty_nodes_exist(self):
        """存在难度 3+ 的中高阶知识点（高中数学主体为难度2-3）"""
        high_diff = [nid for nid, n in KNOWLEDGE_GRAPH.items() if n.difficulty >= 3]
        assert len(high_diff) >= 10, f"只有 {len(high_diff)} 个难度>=3 的节点"
