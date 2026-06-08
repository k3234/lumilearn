"""云端大模型 API Key 管理服务"""
import os
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
PROVIDERS_FILE = CONFIG_DIR / "providers.yaml"

# 预设提供商定义
PRESET_PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek Chat"},
            {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner"},
        ],
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
        ],
    },
    "zhipu": {
        "name": "智谱清言",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": [
            {"id": "glm-4-flash", "name": "GLM-4 Flash"},
            {"id": "glm-4", "name": "GLM-4"},
        ],
    },
    "moonshot": {
        "name": "Moonshot",
        "base_url": "https://api.moonshot.cn/v1",
        "models": [
            {"id": "moonshot-v1-8k", "name": "Moonshot v1 8K"},
            {"id": "moonshot-v1-32k", "name": "Moonshot v1 32K"},
        ],
    },
}

class ProviderService:
    def __init__(self):
        self._ensure_config()

    def _ensure_config(self):
        if not PROVIDERS_FILE.exists():
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(PROVIDERS_FILE, "w", encoding="utf-8") as f:
                f.write("# LumiLearn 云端大模型提供商配置\nproviders: {}\n")

    def _load(self) -> dict:
        with open(PROVIDERS_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # YAML 中 "providers:" 后无内容会被解析为 None
        if not isinstance(data.get("providers"), dict):
            data["providers"] = {}
        return data

    def _save(self, data: dict):
        with open(PROVIDERS_FILE, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    def add_key(self, provider: str, api_key: str) -> dict:
        preset = PRESET_PROVIDERS.get(provider)
        if not preset:
            return {"error": f"Unknown provider: {provider}"}
        data = self._load()
        if "providers" not in data:
            data["providers"] = {}
        data["providers"][provider] = {
            **preset,
            "api_key": api_key,
            "enabled": True,
        }
        self._save(data)
        return {"status": "ok", "provider": provider}

    def delete_key(self, provider: str) -> dict:
        data = self._load()
        if "providers" in data and provider in data["providers"]:
            del data["providers"][provider]
            self._save(data)
        return {"status": "ok"}

    def list_providers(self) -> List[dict]:
        data = self._load()
        providers = data.get("providers", {}) or {}
        result = []
        for key, cfg in providers.items():
            api_key = cfg.get("api_key", "")
            if api_key and len(api_key) > 8:
                masked = api_key[:4] + "***" + api_key[-4:]
            else:
                masked = api_key
            result.append({
                "id": key,
                "name": cfg.get("name", key),
                "masked_key": masked,
                "models": cfg.get("models", []),
                "enabled": cfg.get("enabled", True),
            })
        return result

    def get_provider(self, provider: str) -> Optional[dict]:
        data = self._load()
        return data.get("providers", {}).get(provider)

    def get_api_key(self, provider: str) -> Optional[str]:
        cfg = self.get_provider(provider)
        return cfg.get("api_key") if cfg else None

    def get_base_url(self, provider: str) -> Optional[str]:
        cfg = self.get_provider(provider)
        return cfg.get("base_url") if cfg else None

    def list_presets(self) -> List[dict]:
        return [
            {"id": k, "name": v["name"], "models": v["models"]}
            for k, v in PRESET_PROVIDERS.items()
        ]