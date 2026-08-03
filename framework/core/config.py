#!/usr/bin/env python3
"""
LumiLearn 配置管理中心
统一管理所有配置项，支持 YAML 配置文件加载
"""
import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional

# 默认配置路径
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "framework.yaml"

# 全局配置实例
_config_instance: Optional[Dict[str, Any]] = None


def load_config(config_path: str = None) -> Dict[str, Any]:
    global _config_instance
    if config_path is None:
        config_path = str(DEFAULT_CONFIG_PATH)
    default_config = {
        "version": "1.0.0",
        "debug": False,
        "server": {
            "terminal_port": 18080,
            "api_port": 18081,
            "models_port": 18082,
            "host": "0.0.0.0"
        },
        "ollama": {
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "default_model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            "timeout": 300
        },
        "models": {"providers": {}},
        "security": {"api_key_required": False, "allowed_origins": ["*"]}
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                if config_path.endswith(".yaml") or config_path.endswith(".yml"):
                    file_config = yaml.safe_load(f)
                else:
                    file_config = json.load(f)
            if file_config:
                default_config = _deep_merge(default_config, file_config)
        except Exception as e:
            print(f"[Config] 加载配置文件失败: {e}，使用默认配置")
    if os.getenv("OLLAMA_BASE_URL"):
        default_config["ollama"]["base_url"] = os.getenv("OLLAMA_BASE_URL")
    if os.getenv("OLLAMA_MODEL"):
        default_config["ollama"]["default_model"] = os.getenv("OLLAMA_MODEL")
    _config_instance = default_config
    return _config_instance

def get_config(config_path: str = None) -> Dict[str, Any]:
    global _config_instance
    if _config_instance is None:
        return load_config(config_path)
    return _config_instance

def get_server_ports() -> Dict[str, int]:
    config = get_config()
    return {
        "terminal": config.get("server", {}).get("terminal_port", 18080),
        "api": config.get("server", {}).get("api_port", 18081),
        "models": config.get("server", {}).get("models_port", 18082),
    }
def get_version() -> str:
    config = get_config()
    return config.get("version", "1.0.0")

def is_debug() -> bool:
    config = get_config()
    return config.get("debug", False)

def get_model_list() -> list:
    config = get_config()
    providers = config.get("models", {}).get("providers", {})
    model_list = []
    for provider_key, provider_cfg in providers.items():
        if not provider_cfg.get("enabled", True):
            continue
        for model in provider_cfg.get("models", []):
            model_list.append({
                "name": model.get("id", ""),
                "model_id": model.get("id", ""),
                "provider": provider_key,
                "base_url": provider_cfg.get("base_url", ""),
                "priority": model.get("priority", 0),
                "tags": model.get("tags", []),
                "custom": model.get("custom", False),
                "version": model.get("version", "latest"),
            })
    return model_list
def _deep_merge(base: Dict, override: Dict) -> Dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
def ensure_config_dir():
    config_dir = Path(__file__).resolve().parent.parent.parent / "config"
    config_dir.mkdir(exist_ok=True)
    return config_dir