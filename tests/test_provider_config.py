# -*- coding: utf-8 -*-
"""
ProviderService 配置层单测：DEFAULT_MODEL 解析 / server-providers.yml 映射 / protocol 默认值
（纯逻辑测试，不发起任何网络请求）
"""
import yaml

from framework.services.provider_service import (
    DEFAULT_PROTOCOL,
    PROVIDER_TEMPLATES,
    ProviderService,
    parse_default_model,
)


def _service(tmp_path, providers=None, server=None):
    """构造使用临时配置文件的 ProviderService"""
    providers_path = tmp_path / "providers.yaml"
    server_path = tmp_path / "server-providers.yml"
    providers_path.write_text(
        yaml.dump(providers or {"providers": {}}, allow_unicode=True),
        encoding="utf-8",
    )
    if server is not None:
        server_path.write_text(yaml.dump(server, allow_unicode=True), encoding="utf-8")
    return ProviderService(providers_path=providers_path,
                           server_providers_path=server_path)


# ---------------------------------------------------------------------------
# DEFAULT_MODEL 解析
# ---------------------------------------------------------------------------

def test_parse_default_model_basic():
    assert parse_default_model("google:gemini-3-flash-preview") == (
        "google", "gemini-3-flash-preview")


def test_parse_default_model_keeps_colon_in_model():
    # 只按第一个冒号切分：ollama 模型名自带冒号
    assert parse_default_model("ollama:lumilearn-v2:latest") == (
        "ollama", "lumilearn-v2:latest")


def test_parse_default_model_invalid():
    assert parse_default_model("") == (None, None)
    assert parse_default_model("gemini-3-flash") == (None, None)   # 无冒号
    assert parse_default_model(":model") == (None, None)           # 缺 provider
    assert parse_default_model("google:") == (None, None)          # 缺 model
    assert parse_default_model(None) == (None, None)


def test_get_default_model_env_priority(tmp_path, monkeypatch):
    # 环境变量 DEFAULT_MODEL 优先于 providers.yaml 顶层 default_model
    service = _service(tmp_path, providers={
        "providers": {},
        "default_model": "anthropic:claude-3-5-sonnet-20241022",
    })
    monkeypatch.setenv("DEFAULT_MODEL", "google:gemini-3-flash-preview")
    assert service.get_default_model() == ("google", "gemini-3-flash-preview")


def test_get_default_model_fallback_to_config(tmp_path, monkeypatch):
    monkeypatch.delenv("DEFAULT_MODEL", raising=False)
    service = _service(tmp_path, providers={
        "providers": {},
        "default_model": "ollama:lumilearn-v2:latest",
    })
    assert service.get_default_model() == ("ollama", "lumilearn-v2:latest")


def test_get_default_model_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("DEFAULT_MODEL", raising=False)
    service = _service(tmp_path)
    assert service.get_default_model() == (None, None)


# ---------------------------------------------------------------------------
# protocol 默认值 / 模板
# ---------------------------------------------------------------------------

def test_protocol_defaults_to_openai(tmp_path):
    service = _service(tmp_path, providers={
        "providers": {
            "deepseek": {"name": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
                         "api_key": "sk-x", "enabled": True, "models": []},
        }
    })
    providers = {p["key"]: p for p in service.list_providers()}
    assert providers["deepseek"]["protocol"] == DEFAULT_PROTOCOL == "openai"


def test_add_or_update_provider_stores_protocol(tmp_path):
    service = _service(tmp_path)
    result = service.add_or_update_provider(
        "anthropic", "Anthropic", "https://api.anthropic.com", "sk-ant-x",
        enabled=True, models=[{"id": "claude-3-5-sonnet-20241022", "name": "Sonnet"}],
        protocol="anthropic",
    )
    assert result["success"] is True
    providers = {p["key"]: p for p in service.list_providers()}
    assert providers["anthropic"]["protocol"] == "anthropic"
    assert providers["anthropic"]["has_api_key"] is True


def test_add_or_update_provider_rejects_invalid_protocol(tmp_path):
    service = _service(tmp_path)
    result = service.add_or_update_provider(
        "foo", "Foo", "https://api.example.com", "sk", protocol="grpc")
    assert result["success"] is False
    assert "protocol" in result["error"] or "协议" in result["error"]


def test_templates_include_anthropic_and_google(tmp_path):
    assert PROVIDER_TEMPLATES["anthropic"]["protocol"] == "anthropic"
    assert PROVIDER_TEMPLATES["google"]["protocol"] == "gemini"
    service = _service(tmp_path)
    templates = {t["key"]: t for t in service.get_available_templates()}
    assert templates["anthropic"]["protocol"] == "anthropic"
    assert templates["google"]["protocol"] == "gemini"
    # 其余 OpenAI 兼容模板协议为 openai
    assert templates["deepseek"]["protocol"] == "openai"


# ---------------------------------------------------------------------------
# server-providers.yml 兼容层（camelCase → snake_case）
# ---------------------------------------------------------------------------

def test_server_providers_mapping(tmp_path):
    server = {
        "providers": {
            "openai": {"apiKey": "sk-openai-test"},
            "anthropic": {"apiKey": "sk-ant-test", "models": ["claude-3-5-sonnet-20241022"]},
            "google": {"apiKey": "google-test-key", "models": ["gemini-2.0-flash"]},
            "azure": {"apiKey": "azure-test-key",
                      "baseUrl": "https://YOUR-RESOURCE.openai.azure.com/openai",
                      "models": ["YOUR-DEPLOYMENT-NAME"]},
        }
    }
    service = _service(tmp_path, providers={"providers": {}}, server=server)
    providers = {p["key"]: p for p in service.list_providers()}

    assert providers["openai"]["protocol"] == "openai"
    assert providers["anthropic"]["protocol"] == "anthropic"
    assert providers["google"]["protocol"] == "gemini"      # google → gemini
    assert providers["azure"]["protocol"] == "openai"       # azure → openai

    assert providers["azure"]["base_url"] == "https://YOUR-RESOURCE.openai.azure.com/openai"
    assert providers["azure"]["has_api_key"] is True
    # 字符串数组 models 归一化为 [{"id","name"}]
    assert providers["azure"]["models"] == [
        {"id": "YOUR-DEPLOYMENT-NAME", "name": "YOUR-DEPLOYMENT-NAME"}]
    assert providers["google"]["models"] == [
        {"id": "gemini-2.0-flash", "name": "gemini-2.0-flash"}]


def test_server_providers_does_not_override_providers_yaml(tmp_path):
    providers_cfg = {
        "providers": {
            "openai": {"name": "OpenAI(custom)", "base_url": "https://custom.example.com/v1",
                       "api_key": "sk-explicit", "enabled": True, "models": []},
        }
    }
    server = {"providers": {"openai": {"apiKey": "sk-from-server",
                                       "baseUrl": "https://api.openai.com/v1"}}}
    service = _service(tmp_path, providers=providers_cfg, server=server)
    providers = {p["key"]: p for p in service.list_providers()}
    # providers.yaml 显式配置优先，不被 server-providers.yml 覆盖
    assert providers["openai"]["base_url"] == "https://custom.example.com/v1"
    assert providers["openai"]["name"] == "OpenAI(custom)"
    assert service.get_provider_api_key("openai") == "sk-explicit"
    assert providers["openai"]["protocol"] == "openai"


def test_overlapping_provider_still_persisted_after_save(tmp_path):
    """显式同名项在保存后仍需落盘；server 派生项与其 Key 不得落盘"""
    providers_cfg = {
        "providers": {
            "openai": {"name": "OpenAI", "base_url": "https://custom.example.com/v1",
                       "api_key": "sk-explicit", "enabled": True, "models": []},
        }
    }
    server = {"providers": {"openai": {"apiKey": "sk-from-server"},
                            "google": {"apiKey": "google-secret"}}}
    service = _service(tmp_path, providers=providers_cfg, server=server)
    service.add_or_update_provider("zhipu", "智谱", "https://open.bigmodel.cn/api/paas/v4",
                                   "sk-zhipu", protocol="openai")

    raw = (tmp_path / "providers.yaml").read_text(encoding="utf-8")
    saved = yaml.safe_load(raw)
    assert saved["providers"]["openai"]["base_url"] == "https://custom.example.com/v1"
    assert "zhipu" in saved["providers"]
    assert "google" not in saved["providers"]      # server 派生项不落盘
    assert "sk-from-server" not in raw
    assert "google-secret" not in raw


def test_server_only_providers_not_persisted(tmp_path):
    """安全：server-providers.yml 派生的条目（含真实 Key）不得写回 providers.yaml"""
    server = {"providers": {"google": {"apiKey": "google-secret-key"}}}
    service = _service(tmp_path, providers={"providers": {}}, server=server)
    # 触发一次保存
    service.add_or_update_provider("zhipu", "智谱", "https://open.bigmodel.cn/api/paas/v4",
                                   "sk-zhipu", protocol="openai")
    saved = (tmp_path / "providers.yaml").read_text(encoding="utf-8")
    assert "zhipu" in saved
    assert "google-secret-key" not in saved
    assert "\n  google:" not in saved


# ---------------------------------------------------------------------------
# 协议适配器
# ---------------------------------------------------------------------------

def test_adapters_have_expected_interface_and_public_defaults(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("GOOGLE_BASE_URL", raising=False)
    from framework.models.anthropic_provider import AnthropicProvider
    from framework.models.gemini_provider import GeminiProvider

    anthropic = AnthropicProvider(api_key="sk-ant-test")
    gemini = GeminiProvider(api_key="google-test-key")

    for provider in (anthropic, gemini):
        assert callable(provider.chat)
        assert callable(provider.chat_sync)
        assert callable(provider.list_models)
        assert callable(provider.health_check)

    assert anthropic.base_url == "https://api.anthropic.com"
    assert gemini.base_url == "https://generativelanguage.googleapis.com"
    # 默认地址必须为公开地址，不得包含真实内网地址
    assert "192.168." not in anthropic.base_url and "127." not in anthropic.base_url
    assert "192.168." not in gemini.base_url and "127." not in gemini.base_url
