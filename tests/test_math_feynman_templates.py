# -*- coding: utf-8 -*-
"""
tests/test_math_feynman_templates.py
费曼引擎数学专项模板验证
覆盖：MATH_CALC_TEMPLATE、MATH_CONCEPT_TEMPLATE、MATH_PROOF_TEMPLATE 的存在性、
      detect_math_type 自动识别逻辑、模板输出格式
"""
import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from framework.engines.feynman_templates import FEYNMAN_TEMPLATES, get_template
from framework.engines.feynman_engine import FeynmanEngine, MATH_TYPE_KEYWORDS


# ========== 模板存在性 ==========

class TestMathTemplatePresence:
    """验证数学专项模板已注册到 FEYNMAN_TEMPLATES"""

    def test_math_calc_template_exists(self):
        """MATH_CALC_TEMPLATE 存在于 math 分类"""
        assert "math_calc" in FEYNMAN_TEMPLATES["math"], \
            "FEYNMAN_TEMPLATES['math'] 缺少 'math_calc' 模板"

    def test_math_concept_template_exists(self):
        """MATH_CONCEPT_TEMPLATE 存在于 math 分类"""
        assert "math_concept" in FEYNMAN_TEMPLATES["math"], \
            "FEYNMAN_TEMPLATES['math'] 缺少 'math_concept' 模板"

    def test_math_proof_template_exists(self):
        """MATH_PROOF_TEMPLATE 存在于 math 分类"""
        assert "math_proof" in FEYNMAN_TEMPLATES["math"], \
            "FEYNMAN_TEMPLATES['math'] 缺少 'math_proof' 模板"


# ========== 模板内容格式 ==========

class TestMathTemplateContent:
    """验证数学专项模板包含正确的步骤结构"""

    REQUIRED_STEPS = ["phenomenon", "conflict", "model", "derive", "test"]

    def _check_template(self, template_key: str):
        template = FEYNMAN_TEMPLATES["math"][template_key]
        for step in self.REQUIRED_STEPS:
            assert step in template, f"模板 {template_key} 缺少步骤: {step}"
            assert isinstance(template[step], str), f"模板 {template_key}.{step} 不是字符串"
            assert len(template[step]) > 5, f"模板 {template_key}.{step} 内容过短"

    def test_math_calc_template_content(self):
        """MATH_CALC_TEMPLATE 包含全部 5 步"""
        self._check_template("math_calc")

    def test_math_concept_template_content(self):
        """MATH_CONCEPT_TEMPLATE 包含全部 5 步"""
        self._check_template("math_concept")

    def test_math_proof_template_content(self):
        """MATH_PROOF_TEMPLATE 包含全部 5 步"""
        self._check_template("math_proof")

    def test_math_calc_contains_calculation_keywords(self):
        """MATH_CALC_TEMPLATE 内容包含计算类关键词"""
        content = FEYNMAN_TEMPLATES["math"]["math_calc"]["derive"]
        calc_keywords = ["导数", "积分", "求导", "极限", "Δx"]
        assert any(kw in content for kw in calc_keywords), \
            f"math_calc derive 步骤缺少计算关键词: {calc_keywords}"

    def test_math_concept_contains_concept_keywords(self):
        """MATH_CONCEPT_TEMPLATE 内容包含概念类关键词"""
        content = FEYNMAN_TEMPLATES["math"]["math_concept"]["phenomenon"]
        concept_keywords = ["向量", "函数", "映射", "性质", "定义"]
        assert any(kw in content for kw in concept_keywords), \
            f"math_concept phenomenon 步骤缺少概念关键词: {concept_keywords}"

    def test_math_proof_contains_proof_keywords(self):
        """MATH_PROOF_TEMPLATE 内容包含证明类关键词"""
        content = FEYNMAN_TEMPLATES["math"]["math_proof"]["derive"]
        proof_keywords = ["证明", "因为", "所以", "全等", "定理"]
        assert any(kw in content for kw in proof_keywords), \
            f"math_proof derive 步骤缺少证明关键词: {proof_keywords}"


# ========== 数学类型自动识别 ==========

class TestMathTypeDetection:
    """验证 detect_math_type 自动识别逻辑"""

    def setup_method(self):
        self.engine = FeynmanEngine()

    def test_detect_calc_type_by_topic_keyword(self):
        """topic 含'求导'关键词应识别为 math_calc"""
        result = self.engine.detect_math_type(topic="求导计算")
        assert result == "math_calc", f"期望 math_calc，实际: {result}"

    def test_detect_concept_type_by_topic_keyword(self):
        """topic 含'函数'关键词应识别为 math_concept"""
        result = self.engine.detect_math_type(topic="函数单调性与奇偶性")
        assert result == "math_concept", f"期望 math_concept，实际: {result}"

    def test_detect_proof_type_by_topic_keyword(self):
        """topic 含'证明'关键词应识别为 math_proof"""
        result = self.engine.detect_math_type(topic="三角恒等变换证明")
        assert result == "math_proof", f"期望 math_proof，实际: {result}"

    def test_detect_with_calc_focused_node(self):
        """计算类节点可正确识别为 math_calc"""
        node = {
            "name": "导数应用",
            "description": "利用导数公式求极限和切线斜率",
            "category": "functions"
        }
        result = self.engine.detect_math_type(node)
        assert result == "math_calc", f"期望 math_calc，实际: {result}"

    def test_detect_with_concept_focused_node(self):
        """概念类节点可正确识别为 math_concept"""
        node = {
            "name": "函数概念",
            "description": "函数的定义域、值域与映射对应关系",
            "category": "functions"
        }
        result = self.engine.detect_math_type(node)
        assert result == "math_concept", f"期望 math_concept，实际: {result}"

    def test_detect_default_to_general(self):
        """无匹配关键词时返回 general"""
        result = self.engine.detect_math_type(topic="一些不常见的数学话题")
        assert result == "general", f"期望 general，实际: {result}"

    def test_detect_math_type_empty_input(self):
        """空输入返回 general"""
        result = self.engine.detect_math_type(None, "")
        assert result == "general"

    def test_math_type_keywords_defined(self):
        """MATH_TYPE_KEYWORDS 包含 math_calc / math_concept / math_proof 三类"""
        assert "math_calc" in MATH_TYPE_KEYWORDS
        assert "math_concept" in MATH_TYPE_KEYWORDS
        assert "math_proof" in MATH_TYPE_KEYWORDS


# ========== 模板获取函数 ==========

class TestGetTemplate:
    """验证 get_template 函数返回正确的模板"""

    def test_get_math_calc_template(self):
        """get_template 能获取 math_calc 模板的 phenomenon 步骤"""
        template = get_template("math", "math_calc", "phenomenon")
        assert template is not None
        assert isinstance(template, str)
        assert len(template) > 5

    def test_get_math_concept_template(self):
        """get_template 能获取 math_concept 模板"""
        template = get_template("math", "math_concept", "derive")
        assert template is not None
        assert isinstance(template, str)

    def test_get_math_proof_template(self):
        """get_template 能获取 math_proof 模板"""
        template = get_template("math", "math_proof", "test")
        assert template is not None
        assert isinstance(template, str)

    def test_get_template_fallback_to_general(self):
        """获取不存在的步骤时回退到通用模板"""
        result = get_template("math", "math_calc", "nonexistent_step_xyz")
        assert isinstance(result, str)
        assert len(result) > 0
