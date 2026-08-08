"""
LumiLearn 测试配置和共享 fixtures
"""
import os
import sys
import torch
import pytest

# 脚本式集成测试：依赖本地 Web 服务(localhost:5000)与 Ollama，CI 无法运行
collect_ignore = [
    "test_api_performance.py",
    "test_api_stress.py",
    "test_classroom_concurrent.py",
    "test_classroom_sequential.py",
    "test_feynman_workflow.py",
    "test_handwriting_flow.py",
    "test_robustness_and_admin.py",
]

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
    return LumiLearnModel(config.model)
