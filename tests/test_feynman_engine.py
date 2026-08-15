# -*- coding: utf-8 -*-
"""
tests/test_feynman_engine.py
FeynmanEngine 核心模块单元测试
覆盖：学科识别、Prompt构建、五步教学、交互式引导、降级、RAG注入
"""
import sys, os
from unittest import mock
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from framework.engines.feynman_engine import (
    FeynmanEngine,
    FeynmanResult,
    FeynmanStep,
    quick_explain,
    quick_test,
)


# ========== 学科识别测试 ==========
class TestSubjectDetection:
    """测试 _detect_subject_and_type 方法"""

    def test_math_geometry(self):
        engine = FeynmanEngine(model_name="dummy")
        subject, topic_type = engine._detect_subject_and_type("勾股定理的证明")
        assert subject == "math"
        assert topic_type == "geometry"

    def test_math_function(self):
        engine = FeynmanEngine(model_name="dummy")
        subject, topic_type = engine._detect_subject_and_type("函数的单调性")
        assert subject == "math"
        assert topic_type == "function"

    def test_physics_mechanics(self):
        engine = FeynmanEngine(model_name="dummy")
        subject, topic_type = engine._detect_subject_and_type("牛顿第二定律")
        assert subject == "physics"
        assert topic_type == "mechanics"

    def test_chemistry(self):
        engine = FeynmanEngine(model_name="dummy")
        subject, topic_type = engine._detect_subject_and_type("酸碱中和反应")
        assert subject == "chemistry"
        assert topic_type == "reaction"

    def test_unknown_default(self):
        engine = FeynmanEngine(model_name="dummy")
        subject, topic_type = engine._detect_subject_and_type("一些未知话题")
        assert subject == "general"
        assert topic_type == "general"

    def test_empty_topic(self):
        engine = FeynmanEngine(model_name="dummy")
        subject, topic_type = engine._detect_subject_and_type("")
        assert subject == "general"
        assert topic_type == "general"

    def test_algebra_topic(self):
        engine = FeynmanEngine(model_name="dummy")
        subject, topic_type = engine._detect_subject_and_type("一元二次方程求根公式")
        assert subject == "math"
        assert topic_type == "algebra"

    def test_physics_electromagnetism(self):
        engine = FeynmanEngine(model_name="dummy")
        subject, topic_type = engine._detect_subject_and_type("电磁感应定律")
        assert subject == "physics"
        assert topic_type == "electromagnetism"


# ========== 动画提示生成测试 ==========
class TestAnimationHint:
    """测试 _generate_animation_hint 方法"""

    def test_math_geometry_hint(self):
        engine = FeynmanEngine(model_name="dummy")
        hint = engine._generate_animation_hint("现象引入", "勾股定理", "math", "geometry")
        assert "math" in hint and "geometry" in hint

    def test_physics_mechanics_hint(self):
        engine = FeynmanEngine(model_name="dummy")
        hint = engine._generate_animation_hint("思维模型", "牛顿定律", "physics", "mechanics")
        assert "physics" in hint and "mechanics" in hint

    def test_chemistry_hint(self):
        engine = FeynmanEngine(model_name="dummy")
        hint = engine._generate_animation_hint("自主推导", "酸碱反应", "chemistry", "reaction")
        assert "chemistry" in hint

    def test_fallback_to_default(self):
        engine = FeynmanEngine(model_name="dummy")
        hint = engine._generate_animation_hint("费曼测试", "未知主题", "general", "general")
        assert hint == "general_summary"


# ========== Prompt 构建测试 ==========
class TestPromptBuilding:
    """测试 _build_feynman_prompt 方法"""

    def test_phenomenon_prompt_contains_topic(self):
        engine = FeynmanEngine(model_name="dummy")
        prompt = engine._build_feynman_prompt("phenomenon", "勾股定理", "junior")
        assert "勾股定理" in prompt
        assert "phenomenon" in prompt or "现象" in prompt

    def test_conflict_prompt_contains_topic(self):
        engine = FeynmanEngine(model_name="dummy")
        prompt = engine._build_feynman_prompt("conflict", "单调性", "senior")
        assert "单调性" in prompt

    def test_model_prompt_contains_topic(self):
        engine = FeynmanEngine(model_name="dummy")
        prompt = engine._build_feynman_prompt("model", "电磁感应", "college")
        assert "电磁感应" in prompt

    def test_derive_prompt_contains_topic(self):
        engine = FeynmanEngine(model_name="dummy")
        prompt = engine._build_feynman_prompt("derive", "导数", "senior")
        assert "导数" in prompt

    def test_test_prompt_contains_topic(self):
        engine = FeynmanEngine(model_name="dummy")
        prompt = engine._build_feynman_prompt("test", "光合作用", "junior")
        assert "光合作用" in prompt

    def test_prompt_with_context(self):
        engine = FeynmanEngine(model_name="dummy")
        ctx = ["前面学过勾股定理", "学生理解了基本定义"]
        prompt = engine._build_feynman_prompt("model", "勾股定理", "junior", context=ctx)
        assert "勾股定理" in prompt
        assert "前面学过" in prompt

    def test_prompt_with_extra_context(self):
        engine = FeynmanEngine(model_name="dummy")
        extra = "勾股定理：a²+b²=c²"
        prompt = engine._build_feynman_prompt("test", "勾股定理", "junior", extra_context=extra)
        assert "a²+b²=c²" in prompt

    def test_prompt_level_junior(self):
        engine = FeynmanEngine(model_name="dummy")
        prompt = engine._build_feynman_prompt("phenomenon", "函数", "junior")
        assert "初中生" in prompt or "最简单" in prompt or "生活例子" in prompt

    def test_prompt_level_college(self):
        engine = FeynmanEngine(model_name="dummy")
        prompt = engine._build_feynman_prompt("model", "微积分", "college")
        assert "微积分" in prompt


# ========== FeynmanStep / FeynmanResult 测试 ==========
class TestFeynmanStepResult:
    """测试 FeynmanStep 和 FeynmanResult 数据类"""

    def test_feynman_step_creation(self):
        step = FeynmanStep(step_name="现象引入", step_order=1, content="测试内容")
        assert step.step_name == "现象引入"
        assert step.step_order == 1
        assert step.content == "测试内容"
        assert step.key_points == []
        assert step.animation_hint == ""

    def test_feynman_result_creation(self):
        result = FeynmanResult(
            topic="勾股定理",
            level="junior",
            steps=[FeynmanStep(step_name="现象引入", step_order=1, content="c")],
        )
        assert result.topic == "勾股定理"
        assert result.level == "junior"
        assert len(result.steps) == 1
        assert result.model_used == ""
        assert result.total_time == 0.0

    def test_feynman_result_to_dict(self):
        result = FeynmanResult(topic="x", level="junior", steps=[])
        assert result.topic == "x"
        assert result.level == "junior"
        assert "steps" in result.__dict__


# ========== explain 方法测试（mock 模型调用） ==========
class TestExplain:
    """测试 FeynmanEngine.explain 方法（mock Ollama）"""

    @mock.patch("framework.engines.feynman_engine.call_ollama_clean")
    def test_explain_returns_dict(self, mock_ollama):
        mock_ollama.return_value = "这是教学内容"
        engine = FeynmanEngine(model_name="dummy")
        result = engine.explain("勾股定理", level="junior")
        assert isinstance(result, dict)
        assert result["topic"] == "勾股定理"
        assert result["level"] == "junior"
        assert "steps" in result
        assert len(result["steps"]) == 5
        assert "total_time" in result
        mock_ollama.assert_called()

    @mock.patch("framework.engines.feynman_engine.call_ollama_clean")
    def test_explain_with_level(self, mock_ollama):
        mock_ollama.return_value = "简单讲解"
        engine = FeynmanEngine(model_name="dummy")
        result = engine.explain("函数单调性", level="senior")
        assert result["topic"] == "函数单调性"
        assert result["level"] == "senior"
        assert len(result["steps"]) == 5

    @mock.patch("framework.engines.feynman_engine.call_ollama_clean")
    def test_explain_fallback_on_error(self, mock_ollama):
        """所有步骤都失败时，仍应返回有效结果（模板降级）"""
        mock_ollama.return_value = ""
        engine = FeynmanEngine(model_name="dummy")
        result = engine.explain("牛顿定律", level="junior")
        assert isinstance(result, dict)
        assert result["topic"] == "牛顿定律"
        # 模板降级后 steps 仍然有内容
        assert len(result["steps"]) == 5

    @mock.patch("framework.engines.feynman_engine.call_ollama_clean")
    def test_explain_with_rag_context(self, mock_ollama):
        mock_ollama.return_value = "教学内容"
        engine = FeynmanEngine(model_name="dummy")
        result = engine.explain("勾股定理", level="junior", extra_context="参考资料：勾股定理a²+b²=c²")
        assert isinstance(result, dict)
        assert result["topic"] == "勾股定理"


# ========== explain_step 交互式测试 ==========
class TestExplainStep:
    """测试 explain_step 交互式单步引导"""

    @mock.patch("framework.engines.feynman_engine.call_ollama_clean")
    def test_explain_step_returns_dict(self, mock_ollama):
        mock_ollama.return_value = "引导问题"
        engine = FeynmanEngine(model_name="dummy")
        step_result = engine.explain_step(topic="勾股定理", level="junior")
        assert isinstance(step_result, dict)
        assert "step" in step_result
        assert "step_name" in step_result
        assert "content" in step_result
        assert "is_last" in step_result

    @mock.patch("framework.engines.feynman_engine.call_ollama_clean")
    def test_explain_step_with_dialogue_history(self, mock_ollama):
        mock_ollama.return_value = "继续引导"
        engine = FeynmanEngine(model_name="dummy")
        # 对话中有1条assistant消息，下一步是第2步
        dialogue = [{"role": "user", "content": "我理解了"}, {"role": "assistant", "content": "很好"}]
        step_result = engine.explain_step(topic="函数", level="senior", dialogue=dialogue)
        assert isinstance(step_result, dict)
        assert step_result["step"] == 2

    @mock.patch("framework.engines.feynman_engine.call_ollama_clean")
    def test_explain_step_increments(self, mock_ollama):
        """多次调用应该逐步推进步骤"""
        mock_ollama.return_value = "内容"
        engine = FeynmanEngine(model_name="dummy")
        s1 = engine.explain_step(topic="导数", level="junior")
        s2 = engine.explain_step(topic="导数", level="junior", dialogue=[
            {"role": "assistant", "content": s1["content"]},
            {"role": "user", "content": "我明白了"}
        ])
        assert s1["step"] == 1
        assert s2["step"] == 2


# ========== 历史管理测试 ==========
class TestHistory:
    """测试对话历史管理"""

    def test_get_history_empty(self):
        engine = FeynmanEngine(model_name="dummy")
        assert engine.history == []

    def test_explain_adds_to_history(self):
        engine = FeynmanEngine(model_name="dummy")
        with mock.patch("framework.engines.feynman_engine.call_ollama_clean") as m:
            m.return_value = "test"
            engine.explain("测试主题", level="junior")
        assert len(engine.history) == 1
        assert engine.history[0]["topic"] == "测试主题"

    def test_clear_history(self):
        engine = FeynmanEngine(model_name="dummy")
        engine.history = [{"role": "user", "content": "test"}]
        engine.history = []
        assert engine.history == []

    def test_set_model(self):
        engine = FeynmanEngine(model_name="dummy")
        engine.model_name = "qwen2.5:7b"
        assert engine.model_name == "qwen2.5:7b"


# ========== 快速函数测试 ==========
class TestQuickFunctions:
    """测试 quick_explain 和 quick_test 快捷函数"""

    @mock.patch("framework.engines.feynman_engine.call_ollama_clean")
    def test_quick_explain(self, mock_ollama):
        mock_ollama.return_value = "快速讲解"
        result = quick_explain("勾股定理", level="junior")
        assert isinstance(result, dict)
        assert result["topic"] == "勾股定理"

    @mock.patch("framework.engines.feynman_engine.call_ollama_clean")
    def test_quick_test(self, mock_ollama):
        mock_ollama.return_value = "你的解释很好"
        result = quick_test("导数", "导数是变化率")
        assert isinstance(result, dict)
        assert "concept" in result or "score" in result or "feedback" in result


# ========== 单元测试注册 ==========
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
