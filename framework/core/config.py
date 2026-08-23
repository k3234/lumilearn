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
        "lite_mode": False,
        "server": {
            "terminal_port": 18080,
            "api_port": 18081,
            "models_port": 18082,
            "host": "0.0.0.0"
        },
        "ollama": {
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "default_model": os.getenv("OLLAMA_MODEL", "lumilearn-v2:latest"),
            "timeout": 300
        },
        "models": {"providers": {}},
        "security": {"api_key_required": False, "allowed_origins": ["http://localhost:5000", "http://127.0.0.1:5000"]}
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


# ---------- Web 安全辅助（H-1 / M-1 修复，见 docs/SECURITY_LOCAL_AUDIT_20260817.md） ----------

def get_app_secret_key(env_var: str, app_name: str) -> str:
    """
    获取应用 SECRET_KEY（fail-closed）。

    生产环境（LUMILEARN_ENV=production）必须通过环境变量提供，
    缺失则拒绝启动；非生产环境自动随机生成，避免硬编码密钥。
    """
    import secrets
    key = os.environ.get(env_var, "").strip()
    if key:
        return key
    is_production = os.environ.get("LUMILEARN_ENV", "").lower() == "production"
    if is_production:
        raise RuntimeError(
            f"[Security] 生产环境必须设置环境变量 {env_var}（{app_name} 的 SECRET_KEY）"
        )
    return secrets.token_hex(32)


def register_csrf_guard(app):
    """
    注册 CSRF 防护（Origin/Referer 校验 + 会话 Token 生成）。

    - 非安全方法（POST/PUT/DELETE 等）校验请求来源是否与 Host 一致
    - 每个请求注入会话级 CSRF Token（secrets.token_hex(32)），模板可读取
    """
    import secrets
    from urllib.parse import urlparse

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

    @app.before_request
    def _csrf_guard():
        from flask import request, session
        # 每个请求确保会话存在 CSRF Token（模板用于生成隐藏字段）
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_hex(32)

        if request.method in SAFE_METHODS:
            return None

        # Origin/Referer 校验：存在则必须与请求 Host 匹配
        origin = request.headers.get("Origin") or request.headers.get("Referer")
        if not origin:
            # 无来源头（如同源非浏览器客户端）放行
            return None
        host = request.headers.get("Host", "")
        try:
            o = urlparse(origin)
            origin_netloc = o.netloc
        except Exception:
            origin_netloc = ""
        if origin_netloc == host:
            return None
        # 允许 localhost 同源
        if host.startswith("localhost") and (
            origin_netloc.startswith("localhost") or origin_netloc.startswith("127.0.0.1")
        ):
            return None
        from flask import jsonify
        return jsonify({"error": "CSRF 校验失败", "reason": "非法请求来源"}), 403