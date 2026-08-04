"""
测试 LumiLearn 配置模块
覆盖 ModelConfig、LumiLearnConfig、预设配置
"""
import pytest
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from framework.config import (
    ModelConfig,
    LumiLearnConfig,
    TrainingConfig,
    DataConfig,
    ExperimentConfig,
    get_preset_configs,
)


class TestModelConfig:
    """ModelConfig 单元测试"""

    def test_default_param_count(self):
        """测试默认配置的参数量估算"""
        config = ModelConfig()
        params = config.param_count
        assert "M" in params
        assert "8" in params  # ~8M params

    def test_param_count_with_tie_weights(self):
        """测试 tie_weights=True 时参数量计算"""
        config = ModelConfig(tie_weights=True, hidden_size=256, vocab_size=8000)
        # 计算: 8000*256 + 8*(4*256^2 + 2*256*1024) = 8,339,456
        params = config.param_count
        assert "8" in params

    def test_param_count_without_tie_weights(self):
        """测试 tie_weights=False 时参数量计算"""
        config = ModelConfig(tie_weights=False, hidden_size=256, vocab_size=8000)
        params = config.param_count
        # 不共享权重时参数量更大
        assert "M" in params

    def test_param_count_swiglu(self):
        """测试 SwiGLU 激活函数的参数量"""
        config_gelu = ModelConfig(activation="gelu")
        config_swiglu = ModelConfig(activation="swiglu")
        # SwiGLU 有 3 个矩阵，GELU 有 2 个，参数量应更大
        assert config_swiglu.param_count != config_gelu.param_count

    def test_default_values(self):
        """测试默认配置值"""
        config = ModelConfig()
        assert config.vocab_size == 8000
        assert config.hidden_size == 256
        assert config.num_layers == 8
        assert config.num_heads == 8
        assert config.max_seq_len == 256
        assert config.tie_weights is True

    def test_gqa_config(self):
        """测试 GQA 配置"""
        config = ModelConfig(num_kv_heads=4, num_heads=8)
        assert config.num_kv_heads == 4
        assert config.num_kv_heads != config.num_heads


class TestLumiLearnConfig:
    """LumiLearnConfig 单元测试"""

    def test_default_construction(self):
        """测试默认构造"""
        config = LumiLearnConfig()
        assert isinstance(config.model, ModelConfig)
        assert isinstance(config.training, TrainingConfig)
        assert isinstance(config.data, DataConfig)
        assert isinstance(config.experiment, ExperimentConfig)

    def test_summary(self):
        """测试配置摘要输出"""
        config = LumiLearnConfig()
        summary = config.summary()
        assert "LumiLearn" in summary
        assert "params" in summary
        assert "lr" in summary

    def test_to_json(self, tmp_path):
        """测试配置保存为 JSON"""
        config = LumiLearnConfig()
        json_path = os.path.join(tmp_path, "config.json")
        config.to_json(json_path)
        assert os.path.exists(json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "model" in data
        assert "training" in data

    def test_from_json(self, tmp_path):
        """测试从 JSON 加载配置"""
        config = LumiLearnConfig()
        json_path = os.path.join(tmp_path, "config.json")
        config.to_json(json_path)
        loaded = LumiLearnConfig.from_json(json_path)
        assert loaded.model.hidden_size == config.model.hidden_size
        assert loaded.model.vocab_size == config.model.vocab_size


class TestPresetConfigs:
    """预设配置测试"""

    def test_all_presets_exist(self):
        """测试所有预设配置存在"""
        presets = get_preset_configs()
        expected = ["scratch_small", "scratch_medium", "scratch_large",
                   "fast_test", "scratch_gpu", "airllm_1b", "airllm_3b", "airllm_smoke"]
        for name in expected:
            assert name in presets, f"预设配置 {name} 缺失"

    def test_fast_test_preset(self):
        """测试快速测试预设配置"""
        presets = get_preset_configs()
        config = presets["fast_test"]
        assert config.training.max_steps <= 1000
        assert config.model.num_layers <= 4

    def test_airllm_presets(self):
        """测试 AirLLM 预设配置"""
        presets = get_preset_configs()
        airllm = presets["airllm_1b"]
        assert airllm.model.activation == "swiglu"
        assert airllm.model.use_rotary is True
        assert airllm.model.use_rmsnorm is True
