#!/usr/bin/env python3
"""
LumiLearn 模型提供者管理服务
管理 providers.yaml 中所有云端大模型提供者的 API Key 和模型配置
"""
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger("lumilearn.provider_service")

PROVIDERS_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "providers.yaml"
FRAMEWORK_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "framework.yaml"
# OpenMAIC 兼容层：可选的 camelCase 提供者配置（结构见 server-providers.yml.example）。
# 该文件通常保存真实 Key，应加入 .gitignore，不要提交到仓库。
SERVER_PROVIDERS_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "server-providers.yml"

# 协议取值：openai / anthropic / gemini / ollama（默认 openai）
DEFAULT_PROTOCOL = "openai"
VALID_PROTOCOLS = ("openai", "anthropic", "gemini", "ollama")

# server-providers.yml 段名 → 内部 protocol 推断（对齐 OpenMAIC 的 camelCase 结构）
SECTION_PROTOCOL_MAP = {
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "gemini",   # OpenMAIC 中 google 段即 Gemini
    "gemini": "gemini",
    "azure": "openai",    # Azure OpenAI 走 OpenAI 兼容协议
    "deepseek": "openai",
}


def parse_default_model(value: str):
    """解析 DEFAULT_MODEL 的 `provider:model` 约定。

    只按**第一个冒号**切分，因此模型名中的冒号会被完整保留，例如：
        "google:gemini-3-flash-preview" -> ("google", "gemini-3-flash-preview")
        "ollama:lumilearn-v2:latest"    -> ("ollama", "lumilearn-v2:latest")

    参数:
        value: 形如 "provider:model" 的字符串
    返回:
        (provider, model)；无法解析时返回 (None, None)
    """
    if not value or not isinstance(value, str):
        return None, None
    value = value.strip()
    if ":" not in value:
        return None, None
    provider, model = value.split(":", 1)
    provider, model = provider.strip(), model.strip()
    if not provider or not model:
        return None, None
    return provider, model


# 标准提供者模板（预设名称、默认地址、协议、已知模型列表）
PROVIDER_TEMPLATES = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "protocol": "openai",
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek Chat"},
            {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner"},
        ]
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "protocol": "openai",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
        ]
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "base_url": "https://api.anthropic.com",
        "protocol": "anthropic",
        "models": [
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
            {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku"},
        ]
    },
    "google": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com",
        "protocol": "gemini",
        "models": [
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
        ]
    },
    "zhipu": {
        "name": "智谱清言",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "protocol": "openai",
        "models": [
            {"id": "glm-4-flash", "name": "GLM-4 Flash"},
            {"id": "glm-4", "name": "GLM-4"},
            {"id": "glm-4-plus", "name": "GLM-4 Plus"},
        ]
    },
    "moonshot": {
        "name": "Moonshot",
        "base_url": "https://api.moonshot.cn/v1",
        "protocol": "openai",
        "models": [
            {"id": "moonshot-v1-8k", "name": "Moonshot v1 8K"},
            {"id": "moonshot-v1-32k", "name": "Moonshot v1 32K"},
        ]
    },
    "qwen": {
        "name": "通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "protocol": "openai",
        "models": [
            {"id": "qwen-turbo", "name": "Qwen Turbo"},
            {"id": "qwen-plus", "name": "Qwen Plus"},
            {"id": "qwen-max", "name": "Qwen Max"},
        ]
    },
    "siliconflow": {
        "name": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "protocol": "openai",
        "models": [
            {"id": "Qwen/Qwen2.5-7B-Instruct", "name": "Qwen2.5-7B-Instruct"},
            {"id": "Qwen/Qwen2.5-14B-Instruct", "name": "Qwen2.5-14B-Instruct"},
            {"id": "deepseek-ai/DeepSeek-V2.5", "name": "DeepSeek V2.5"},
        ]
    },
}

# 默认端口-模型映射（各端口使用的模型配置）
DEFAULT_PORT_MODEL_MAP = {
    "terminal": {"provider": "ollama", "model": "lumilearn-v2:latest", "port": 18080},
    "api": {"provider": "ollama", "model": "lumilearn-v2:latest", "port": 18081},
    "models": {"provider": "ollama", "model": "lumilearn-v2:latest", "port": 18082},
    "teacher_portal": {"provider": "ollama", "model": "lumilearn-v2:latest", "port": 5001},
    "student_portal": {"provider": "ollama", "model": "lumilearn-v2:latest", "port": 5010},
    "analytics_dashboard": {"provider": "ollama", "model": "lumilearn-v2:latest", "port": 18090},
}

PORT_DISPLAY_NAMES = {
    "terminal": "终端 (18080)",
    "api": "REST API (18081)",
    "models": "模型管理 (18082)",
    "teacher_portal": "教师端 (5001)",
    "student_portal": "学生端学习平台 (5010)",
    "analytics_dashboard": "学习分析仪表盘 (18090)",
}

# 端口服务默认配置（可选择性启用/自定义端口号）
PORT_SETTINGS_DEFAULTS = {
    "terminal": {"enabled": True, "port": 18080, "desc": "框架终端 + Admin 面板", "script": "framework/api/server.py"},
    "api": {"enabled": True, "port": 18081, "desc": "REST API 纯接口服务", "script": "framework/api/server.py"},
    "models": {"enabled": True, "port": 18082, "desc": "模型管理服务", "script": "framework/api/server.py"},
    "teacher_portal": {"enabled": True, "port": 5001, "desc": "教师端 Teacher Portal", "script": "teacher_portal.py"},
    "student_portal": {"enabled": True, "port": 5010, "desc": "学生端学习平台（原型+真实后端）", "script": "student_portal.py"},
    "analytics_dashboard": {"enabled": True, "port": 18090, "desc": "学习分析仪表盘", "script": "analytics_dashboard.py"},
}


class ProviderService:
    """模型提供者配置管理服务"""

    def __init__(self, providers_path=None, server_providers_path=None):
        # 允许注入自定义配置路径（便于单元测试；默认使用仓库内 config/ 下的文件）
        self._providers_path = Path(providers_path) if providers_path else PROVIDERS_CONFIG_PATH
        self._server_providers_path = (
            Path(server_providers_path) if server_providers_path else SERVER_PROVIDERS_CONFIG_PATH
        )
        self._providers: Dict[str, Dict] = {}
        # providers.yaml 顶层 default_model（provider:model），env DEFAULT_MODEL 优先级更高
        self._config_default_model: str = ""
        # 仅这些 key 会被写回 providers.yaml；server-providers.yml 派生的条目默认不落盘，
        # 避免把 server-providers.yml 中的真实 Key 意外写入可提交的 providers.yaml。
        self._persisted_keys: set = set()
        self._load_providers()

    def _load_providers(self):
        """加载提供者配置。

        合并优先级（高 → 低）：
            1. providers.yaml（显式配置，最高优先级）
            2. server-providers.yml（OpenMAIC 兼容层，camelCase，不覆盖同名项）
            3. 内置 PROVIDER_TEMPLATES（仅用于 UI 模板，不在加载阶段参与合并）
        """
        providers: Dict[str, Dict] = {}
        default_model = ""
        path = self._providers_path
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                providers = data.get("providers", {}) or {}
                default_model = str(data.get("default_model", "") or "")
                logger.info(f"已加载 {len(providers)} 个提供者配置")
            except Exception as e:
                logger.error(f"加载提供者配置失败: {e}")
                providers = {}
        # 归一化：补齐 protocol（缺省 openai）
        for cfg in providers.values():
            if isinstance(cfg, dict) and not cfg.get("protocol"):
                cfg["protocol"] = DEFAULT_PROTOCOL

        # 合并 server-providers.yml（不覆盖 providers.yaml 中已显式配置的同名项）
        server_providers = self._load_server_providers()
        merged_keys = set()
        for key, cfg in server_providers.items():
            if key in providers:
                continue
            providers[key] = cfg
            merged_keys.add(key)
        if merged_keys:
            logger.info(f"已从 server-providers.yml 合并 {len(merged_keys)} 个提供者")

        self._providers = providers
        self._config_default_model = default_model
        # 仅 server 派生项不落盘；providers.yaml 中已有的同名项仍需持久化
        self._persisted_keys = set(providers.keys()) - merged_keys

    def _load_server_providers(self) -> Dict[str, Dict]:
        """读取 config/server-providers.yml（OpenMAIC 兼容格式，camelCase）。

        将 camelCase 的 apiKey/baseUrl/models 映射为内部 snake_case 条目，
        protocol 由段名推断（openai→openai、anthropic→anthropic、
        google→gemini、azure→openai）。
        """
        result: Dict[str, Dict] = {}
        path = self._server_providers_path
        if not path.exists():
            return result
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"加载 server-providers.yml 失败: {e}")
            return result

        raw = data.get("providers", {}) or {}
        for section, cfg in raw.items():
            if not isinstance(cfg, dict):
                continue
            protocol = SECTION_PROTOCOL_MAP.get(str(section).lower(), DEFAULT_PROTOCOL)
            result[section] = {
                "name": cfg.get("name") or section,
                "base_url": cfg.get("baseUrl") or cfg.get("base_url") or "",
                "api_key": cfg.get("apiKey") or cfg.get("api_key") or "",
                "enabled": bool(cfg.get("enabled", True)),
                "models": self._normalize_server_models(cfg.get("models")),
                "protocol": protocol,
            }
        return result

    @staticmethod
    def _normalize_server_models(models) -> List[Dict]:
        """把 server-providers.yml 的 models 归一化为 [{"id","name"}] 结构。

        支持字符串数组（OpenMAIC 的 azure.models: [deployment-name]）与对象数组。
        """
        normalized: List[Dict] = []
        for m in models or []:
            if isinstance(m, str):
                normalized.append({"id": m, "name": m})
            elif isinstance(m, dict):
                mid = m.get("id") or m.get("name") or m.get("model") or ""
                if mid:
                    normalized.append({"id": mid, "name": m.get("name") or mid})
        return normalized

    def _save_providers(self):
        """保存提供者配置到 providers.yaml（仅落盘显式配置项，不含 server 派生项）"""
        path = self._providers_path
        path.parent.mkdir(parents=True, exist_ok=True)
        persisted = {k: self._providers[k] for k in self._persisted_keys if k in self._providers}
        data = {"providers": persisted}
        if self._config_default_model:
            data["default_model"] = self._config_default_model
        try:
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            logger.info(f"提供者配置已保存: {path}")
        except Exception as e:
            logger.error(f"保存提供者配置失败: {e}")

    def list_providers(self) -> List[Dict]:
        """获取所有已配置的提供者列表"""
        result = []
        for key, cfg in self._providers.items():
            result.append({
                "key": key,
                "name": cfg.get("name", key),
                "base_url": cfg.get("base_url", ""),
                "enabled": cfg.get("enabled", False),
                "has_api_key": bool(cfg.get("api_key", "")),
                "local": bool(cfg.get("local", False)),   # 本地 OpenAI 兼容容器（无需 API Key）
                "protocol": cfg.get("protocol", DEFAULT_PROTOCOL),
                "models": cfg.get("models", []),
            })
        return result

    def get_available_templates(self) -> List[Dict]:
        """获取可用的提供者模板列表"""
        return [
            {"key": key, "name": info["name"], "base_url": info["base_url"],
             "protocol": info.get("protocol", DEFAULT_PROTOCOL),
             "models": info["models"]}
            for key, info in PROVIDER_TEMPLATES.items()
        ]

    def add_or_update_provider(self, key: str, name: str, base_url: str,
                                api_key: str, enabled: bool = True,
                                models: Optional[List[Dict]] = None,
                                protocol: str = DEFAULT_PROTOCOL) -> Dict:
        """添加或更新提供者配置"""
        if not key or not name:
            return {"success": False, "error": "提供者标识和名称不能为空"}
        if protocol not in VALID_PROTOCOLS:
            return {"success": False,
                    "error": f"无效协议，可选: {', '.join(VALID_PROTOCOLS)}"}

        # 如果传入了 models，使用传入的；否则使用模板默认
        if models is None:
            template = PROVIDER_TEMPLATES.get(key, {})
            models = template.get("models", [])

        self._providers[key] = {
            "name": name,
            "base_url": base_url,
            "api_key": api_key,
            "enabled": enabled,
            "models": models,
            "protocol": protocol,
        }
        # 显式配置项需落盘
        self._persisted_keys.add(key)
        self._save_providers()
        return {"success": True, "message": f"提供者 {name} 已保存"}

    def delete_provider(self, key: str) -> Dict:
        """删除提供者配置"""
        if key not in self._providers:
            return {"success": False, "error": "提供者不存在"}
        name = self._providers[key].get("name", key)
        del self._providers[key]
        self._persisted_keys.discard(key)
        self._save_providers()
        return {"success": True, "message": f"提供者 {name} 已删除"}

    def get_provider(self, key: str) -> Optional[Dict]:
        """获取单个提供者配置"""
        cfg = self._providers.get(key)
        if not cfg:
            return None
        return {
            "key": key,
            "name": cfg.get("name", key),
            "base_url": cfg.get("base_url", ""),
            "has_api_key": bool(cfg.get("api_key", "")),
            "enabled": cfg.get("enabled", False),
            "local": bool(cfg.get("local", False)),
            "protocol": cfg.get("protocol", DEFAULT_PROTOCOL),
            "models": cfg.get("models", []),
        }

    def get_default_model(self):
        """解析默认模型（`provider:model` 约定）。

        优先级（高 → 低）：
            1. 环境变量 DEFAULT_MODEL
            2. providers.yaml 顶层 default_model 字段
        两者均未配置时返回 (None, None)，调用方应回退到既有逻辑：
            framework.yaml 的 ollama.default_model / port_model_mapping（按请求端口解析）。
        只按第一个冒号切分，模型名中的冒号会被保留。
        """
        for raw in (os.environ.get("DEFAULT_MODEL", ""), self._config_default_model):
            if raw and str(raw).strip():
                provider, model = parse_default_model(str(raw))
                if provider and model:
                    return provider, model
        return None, None

    def get_provider_api_key(self, key: str) -> str:
        """获取指定提供者的 API Key（内部使用）"""
        cfg = self._providers.get(key, {})
        return cfg.get("api_key", "")

    def get_enabled_providers(self) -> Dict[str, Dict]:
        """获取所有已启用的提供者（内部使用；本地容器无需 API Key）"""
        return {
            k: v for k, v in self._providers.items()
            if v.get("enabled", False) and (v.get("api_key") or v.get("local", False))
        }

    def reload(self):
        """重新从 providers.yaml 加载配置（Admin 修改后调用，保证热更新）"""
        self._load_providers()

    # ======== 端口-模型映射管理 ========

    def get_port_model_map(self) -> Dict[str, Dict]:
        """获取端口-模型映射配置"""
        config = self._load_framework_config()
        port_map = config.get("port_model_mapping", {})
        # 合并默认值，确保所有端口都有配置
        result = {}
        for port_key, default in DEFAULT_PORT_MODEL_MAP.items():
            result[port_key] = {**default, **port_map.get(port_key, {})}
            result[port_key]["display_name"] = PORT_DISPLAY_NAMES.get(port_key, port_key)
        return result

    def set_port_model(self, port_key: str, provider: str, model: str) -> Dict:
        """设置某个端口使用的模型"""
        valid_ports = list(DEFAULT_PORT_MODEL_MAP.keys())
        if port_key not in valid_ports:
            return {"success": False, "error": f"无效端口标识，可选: {', '.join(valid_ports)}"}

        config = self._load_framework_config()
        if "port_model_mapping" not in config:
            config["port_model_mapping"] = {}
        config["port_model_mapping"][port_key] = {
            "provider": provider,
            "model": model,
        }
        self._save_framework_config(config)
        return {"success": True, "message": f"{PORT_DISPLAY_NAMES.get(port_key, port_key)} 已设置为 {provider}/{model}"}

    def get_ollama_models(self) -> List[Dict]:
        """获取本地 Ollama 模型列表（地址优先 .env 的 OLLAMA_BASE_URL）"""
        try:
            import requests
            base_url = os.environ.get(
                "OLLAMA_BASE_URL",
                os.environ.get("OLLAMA_URL", "http://localhost:11434"),
            ).rstrip("/")
            resp = requests.get(f"{base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                return [{"name": m.get("name", "unknown"), "provider": "ollama"}
                        for m in resp.json().get("models", [])]
        except Exception as e:
            logger.warning(f"获取 Ollama 模型列表失败: {e}")
        return []

    def get_all_available_models(self) -> List[Dict]:
        """获取所有可用的模型（Ollama + 已启用云提供者 + 本地 OpenAI 兼容容器）"""
        models = []
        # Ollama 本地模型
        ollama_models = self.get_ollama_models()
        for m in ollama_models:
            m["provider_display"] = "Ollama (本地)"
            models.append(m)
        # 云端提供者 / 本地容器模型
        for key, cfg in self._providers.items():
            if not cfg.get("enabled", False):
                continue
            # 云端提供者需要 API Key；本地容器（vLLM / LM Studio / LocalAI 等）无需
            if not cfg.get("api_key") and not cfg.get("local", False):
                continue
            is_local = bool(cfg.get("local", False))
            for model in cfg.get("models", []):
                models.append({
                    "name": model.get("id", ""),
                    "provider": key,
                    "provider_display": f"{cfg.get('name', key)} ({'本地容器' if is_local else '云端'})",
                })
        return models

    # ======== 端口选择性配置管理 ========

    def get_port_settings(self) -> Dict[str, Dict]:
        """获取端口服务配置（合并默认值），并检测实际监听状态"""
        config = self._load_framework_config()
        saved = config.get("port_settings", {})
        result = {}
        for key, default in PORT_SETTINGS_DEFAULTS.items():
            item = {**default, **saved.get(key, {})}
            item["key"] = key
            item["display_name"] = PORT_DISPLAY_NAMES.get(key, key)
            # 实际监听状态
            item["listening"] = self._check_port_listening(int(item.get("port", 0)))
            result[key] = item
        return result

    def set_port_settings(self, settings: Dict) -> Dict:
        """保存端口服务配置（enabled 开关 + 自定义端口号）"""
        config = self._load_framework_config()
        if "port_settings" not in config:
            config["port_settings"] = {}
        errors = []
        for key, item in settings.items():
            if key not in PORT_SETTINGS_DEFAULTS:
                continue
            entry = {"enabled": bool(item.get("enabled", True))}
            port = int(item.get("port", PORT_SETTINGS_DEFAULTS[key]["port"]))
            if not (1 <= port <= 65535):
                errors.append(f"{key} 端口号无效: {port}")
                continue
            # 检查端口冲突（与其他已启用端口服务重复）
            if entry["enabled"]:
                for other_key, other_item in settings.items():
                    if other_key == key or other_key not in PORT_SETTINGS_DEFAULTS:
                        continue
                    other_port = int(other_item.get("port", PORT_SETTINGS_DEFAULTS[other_key]["port"]))
                    if other_port == port and other_item.get("enabled", True):
                        errors.append(f"{key} 与 {other_key} 端口号冲突: {port}")
                        break
            entry["port"] = port
            config["port_settings"][key] = entry
        if errors:
            return {"success": False, "errors": errors}
        self._save_framework_config(config)
        return {"success": True, "message": "端口配置已保存，重启对应服务后生效"}

    def get_port_health(self) -> List[Dict]:
        """获取所有端口服务的健康状态（用于 Admin 展示）"""
        return [
            {"key": k, "display_name": v["display_name"], "port": v["port"],
             "enabled": v["enabled"], "listening": v["listening"], "desc": v.get("desc", "")}
            for k, v in self.get_port_settings().items()
        ]

    def _check_port_listening(self, port: int) -> bool:
        """检测端口是否在监听"""
        if port <= 0:
            return False
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            result = s.connect_ex(("127.0.0.1", port)) == 0
            s.close()
            return result
        except Exception:
            return False

    def _load_framework_config(self) -> Dict:
        """加载 framework.yaml"""
        path = FRAMEWORK_CONFIG_PATH
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
        return {}

    def _save_framework_config(self, config: Dict):
        """保存 framework.yaml"""
        path = FRAMEWORK_CONFIG_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


# 单例
_instance: Optional[ProviderService] = None


def get_provider_service() -> ProviderService:
    global _instance
    if _instance is None:
        _instance = ProviderService()
    return _instance
