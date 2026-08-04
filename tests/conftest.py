"""
LumiLearn 测试配置和共享 fixtures
"""
import os
import sys
import torch
import pytest

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
framework_DIR = os.path.join(PROJECT_ROOT, "framework")
sys.path.insert(0, framework_DIR)

from framework.config import ModelConfig, LumiLearnConfig, TrainingConfig, DataConfig, ExperimentConfig, get_preset_configs
from framework.model import LumiLearnModel


@pytest.fixture
def default_config():
    """默认模型配置"""
    return ModelConfig()


@pytest.fixture
def lumilearn_config():
    """完整 LumiLearn 配置"""
    return LumiLearnConfig()


@pytest.fixture
def model(default_config):
    """初始化默认模型"""
    return LumiLearnModel(default_config)


@pytest.fixture
def fast_model():
    """快速测试用小的小模型"""
    config = get_preset_configs()["fast_test"]
    return LumiLearnModel(config)
