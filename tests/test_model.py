"""
测试 LumiLearn 模型架构
覆盖模型初始化、前向传播、生成
"""
import pytest
torch = pytest.importorskip("torch", reason="torch 未安装，跳过模型测试")
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from framework.config import ModelConfig, get_preset_configs
from framework.model import LumiLearnModel


class TestModelInitialization:
    """模型初始化测试"""

    def test_default_model_init(self):
        """测试默认配置模型初始化"""
        config = ModelConfig()
        model = LumiLearnModel(config)
        assert model.config.vocab_size == 8000
        assert len(model.blocks) == 8

    def test_model_param_count(self):
        """测试模型参数量"""
        config = ModelConfig()
        model = LumiLearnModel(config)
        total = sum(p.numel() for p in model.parameters())
        assert 8_000_000 < total < 9_000_000  # ~8.3M

    def test_tie_weights(self):
        """测试权重绑定"""
        config = ModelConfig(tie_weights=True)
        model = LumiLearnModel(config)
        assert model.lm_head.weight is model.token_emb.weight

    def test_no_tie_weights(self):
        """测试无权重绑定"""
        config = ModelConfig(tie_weights=False)
        model = LumiLearnModel(config)
        assert model.lm_head.weight is not model.token_emb.weight

    def test_rope_model(self):
        """测试 RoPE 模型初始化"""
        config = ModelConfig(use_rotary=True)
        model = LumiLearnModel(config)
        assert model.use_rotary is True
        assert hasattr(model, 'rope')

    def test_rmsnorm_model(self):
        """测试 RMSNorm 模型初始化"""
        config = ModelConfig(use_rmsnorm=True)
        model = LumiLearnModel(config)
        assert model.config.use_rmsnorm is True


class TestModelForward:
    """模型前向传播测试"""

    def test_forward_shape(self):
        """测试前向传播输出形状"""
        config = get_preset_configs()["fast_test"]
        model = LumiLearnModel(config.model)
        model.eval()
        input_ids = torch.randint(0, config.model.vocab_size, (2, 32))
        with torch.no_grad():
            output = model(input_ids)
        assert "logits" in output
        assert output["logits"].shape == (2, 32, config.model.vocab_size)

    def test_forward_with_labels(self):
        """测试带标签的前向传播"""
        config = get_preset_configs()["fast_test"]
        model = LumiLearnModel(config.model)
        input_ids = torch.randint(0, config.model.vocab_size, (2, 32))
        labels = input_ids.clone()
        output = model(input_ids, labels=labels)
        assert "loss" in output
        assert output["loss"] is not None
        assert output["loss"].item() > 0

    def test_forward_no_labels(self):
        """测试不带标签的前向传播"""
        config = get_preset_configs()["fast_test"]
        model = LumiLearnModel(config.model)
        input_ids = torch.randint(0, config.model.vocab_size, (2, 32))
        with torch.no_grad():
            output = model(input_ids)
        assert output["loss"] is None


class TestModelGenerate:
    """模型生成测试"""

    def test_generate_basic(self):
        """测试基本生成功能"""
        config = get_preset_configs()["fast_test"]
        model = LumiLearnModel(config.model)
        model.eval()
        input_ids = torch.randint(0, config.model.vocab_size, (1, 8))
        with torch.no_grad():
            output = model.generate(input_ids, max_new_tokens=10)
        assert output.shape[1] > 8  # 至少生成了部分 token

    def test_generate_temperature(self):
        """测试温度采样"""
        config = get_preset_configs()["fast_test"]
        model = LumiLearnModel(config.model)
        model.eval()
        input_ids = torch.randint(0, config.model.vocab_size, (1, 8))
        with torch.no_grad():
            out1 = model.generate(input_ids, max_new_tokens=5, temperature=0.5)
            out2 = model.generate(input_ids, max_new_tokens=5, temperature=1.0)
        # 不同温度应产生不同结果（高概率）
        assert out1.shape[0] == 1
        assert out2.shape[0] == 1

    def test_generate_top_k(self):
        """测试 top-k 采样"""
        config = get_preset_configs()["fast_test"]
        model = LumiLearnModel(config.model)
        model.eval()
        input_ids = torch.randint(0, config.model.vocab_size, (1, 8))
        with torch.no_grad():
            output = model.generate(input_ids, max_new_tokens=5, top_k=10)
        assert output.shape[1] > 8


class TestModelSaveLoad:
    """模型保存和加载测试"""

    def test_save_pretrained(self, tmp_path):
        """测试保存预训练模型"""
        config = get_preset_configs()["fast_test"]
        model = LumiLearnModel(config.model)
        save_path = os.path.join(tmp_path, "model")
        model.save_pretrained(save_path)
        assert os.path.exists(os.path.join(save_path, "model.pt"))
        assert os.path.exists(os.path.join(save_path, "config.json"))

    def test_from_pretrained(self, tmp_path):
        """测试加载预训练模型"""
        config = get_preset_configs()["fast_test"]
        model = LumiLearnModel(config.model)
        save_path = os.path.join(tmp_path, "model")
        model.save_pretrained(save_path)
        loaded = LumiLearnModel.from_pretrained(save_path)
        assert loaded.config.vocab_size == config.model.vocab_size
        assert loaded.config.hidden_size == config.model.hidden_size

    def test_save_load_roundtrip(self, tmp_path):
        """测试保存-加载往返"""
        config = get_preset_configs()["fast_test"]
        model = LumiLearnModel(config.model)
        save_path = os.path.join(tmp_path, "model")
        model.save_pretrained(save_path)
        loaded = LumiLearnModel.from_pretrained(save_path)
        # 验证权重一致
        for p1, p2 in zip(model.parameters(), loaded.parameters()):
            assert torch.equal(p1, p2)
