"""
测试 LumiLearn 分词器
覆盖 encode、decode、batch 编码
"""
import pytest
tokenizers = pytest.importorskip("tokenizers", reason="tokenizers 未安装，跳过分词器测试")
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from framework.tokenizer import LumiLearnTokenizer


class TestTokenizerBasic:
    """分词器基础功能测试"""

    @pytest.fixture
    def tokenizer(self, tmp_path):
        """创建测试用分词器（使用现有 tokenizer 文件）"""
        # 使用项目自带的 bpe_tokenizer.json
        tokenizer_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "framework", "bpe_tokenizer.json"
        )
        if os.path.exists(tokenizer_path):
            return LumiLearnTokenizer(tokenizer_path=tokenizer_path)
        else:
            pytest.skip("bpe_tokenizer.json 不存在")

    def test_encode_returns_list(self, tokenizer):
        """测试编码返回列表"""
        ids = tokenizer.encode("测试文本")
        assert isinstance(ids, list)
        assert len(ids) > 0

    def test_decode_returns_string(self, tokenizer):
        """测试解码返回字符串"""
        ids = tokenizer.encode("测试")
        text = tokenizer.decode(ids)
        assert isinstance(text, str)

    def test_special_tokens(self, tokenizer):
        """测试特殊 token ID"""
        assert tokenizer.pad_token_id == 0
        assert tokenizer.eos_token_id == 1
        assert tokenizer.bos_token_id == 2
        assert tokenizer.unk_token_id == 3

    def test_encode_batch(self, tokenizer):
        """测试批量编码"""
        texts = ["第一段文本", "第二段文本"]
        result = tokenizer.encode_batch(texts, max_len=64)
        assert "input_ids" in result
        assert "labels" in result
        assert len(result["input_ids"]) == 2

    def test_encode_without_special_tokens(self, tokenizer):
        """测试无特殊 token 编码"""
        ids_with = tokenizer.encode("测试", add_special_tokens=True)
        ids_without = tokenizer.encode("测试", add_special_tokens=False)
        # 有特殊 token 时应更长
        assert len(ids_with) >= len(ids_without)

    def test_decode_skip_special(self, tokenizer):
        """测试解码跳过特殊 token"""
        ids = tokenizer.encode("测试", add_special_tokens=True)
        text = tokenizer.decode(ids, skip_special=True)
        # 解码结果中不应包含特殊 token 标记
        assert "[PAD]" not in text
        assert "[EOS]" not in text

    def test_empty_decode(self, tokenizer):
        """测试空输入解码"""
        text = tokenizer.decode([])
        assert text == ""

    def test_save_and_load(self, tokenizer, tmp_path):
        """测试保存和加载"""
        save_path = os.path.join(tmp_path, "tokenizer.json")
        tokenizer.save(save_path)
        loaded = LumiLearnTokenizer.load(save_path)
        assert loaded.vocab_size == tokenizer.vocab_size
