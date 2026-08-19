"""
LumiLearn 测试配置和共享 fixtures
"""
import os
import sys
try:
    import torch
except ImportError:
    torch = None
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
# LumiLearnModel requires torch; import lazily to avoid ImportError when torch is absent


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """
    每个测试使用独立的临时数据库，并预置测试所需用户。
    避免测试依赖项目根 lumilearn.db 中的残留数据（导致 CI 外键约束失败）。
    """
    from framework.database import db
    from framework.admin import auth as admin_auth
    from werkzeug.security import generate_password_hash

    db_path = str(tmp_path / "test_lumilearn.db")
    monkeypatch.setenv("LUMILEARN_DB_PATH", db_path)
    db.close()
    db.init(db_path)

    # 预置测试用用户（与各测试文件硬编码的 user_id 对应）
    for uid, name in [(1, "测试用户1"), (2, "测试用户2"), (3, "测试用户3"),
                      (5, "测试用户5"), (99, "测试用户99"), (2001, "测试用户2001")]:
        db.conn.execute(
            "INSERT OR IGNORE INTO users (id, name, role) VALUES (?, ?, 'student')",
            (uid, name),
        )
    # 预置默认管理员 admin / admin123（每个测试独立库，需重建）
    if not db.get_admins():
        db.add_admin("admin", generate_password_hash("admin123"),
                     display_name="超级管理员", role="super_admin")
    db.conn.commit()

    # 重置 admin 认证单例，确保指向新库
    admin_auth._auth_instance = None
    # 重置 Agent 注册表单例与运行状态（每个测试独立库，需重新注册内置 Agent）
    from framework.admin import agents as agents_module
    agents_module._registry_instance = None
    agents_module._agent_runners.clear()
    # 重新注册内置 Agent：agents 表必须预置数据，
    # 否则 agent_weight_config / knowledge_accumulation / agent_call_log
    # 的外键约束（REFERENCES agents）会失败
    agents_module.get_agent_registry()

    yield

    db.close()
    monkeypatch.delenv("LUMILEARN_DB_PATH", raising=False)


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
    from framework.model import LumiLearnModel
    return LumiLearnModel(default_config)


@pytest.fixture
def fast_model():
    """快速测试用小的小模型"""
    from framework.model import LumiLearnModel
    config = get_preset_configs()["fast_test"]
    return LumiLearnModel(config.model)
