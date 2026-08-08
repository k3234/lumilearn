#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 配置管理器
支持 YAML/JSON 配置加载、验证、合并
"""
import os
import sys
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class ModelProvider:
    """模型提供商配置"""
    name: str
    enabled: bool = False
    base_url: str = ""
    api_key_env: str = ""
    default_model: str = ""
    models: List[str] = field(default_factory=list)


@dataclass
class Endpoint:
    """用户端配置"""
    name: str
    enabled: bool = True
    port: int = 0
    path: str = ""
    features: List[str] = field(default_factory=list)


@dataclass
class ServerConfig:
    """服务器配置"""
    multi_port: bool = True
    terminal_port: int = 18080
    api_port: int = 18081
    models_port: int = 18082
    host: str = "0.0.0.0"
    debug: bool = False


class ConfigManager:
    """LumiLearn 配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else self._get_default_path()
        self.config: Dict[str, Any] = {}
        self._load()

    def _get_default_path(self) -> Path:
        """获取默认配置文件路径"""
        # 优先级：项目根目录 > 当前目录 > 默认路径
        candidates = [
            Path(__file__).parent.parent / "deploy_config.yaml",
            Path("deploy_config.yaml"),
            Path.home() / ".lumilearn" / "config.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]  # 返回默认路径

    def _load(self):
        """加载配置文件"""
        if not self.config_path.exists():
            self.config = self._default_config()
            return

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f) or {}

    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "version": "1.0.0",
            "project": "LumiLearn",
            "models": {
                "local": {
                    "enabled": True,
                    "default_provider": "ollama",
                    "ollama": {
                        "base_url": "http://localhost:11434",
                        "timeout": 300,
                        "default_model": "qwen2.5:7b",
                        "recommended_models": [
                            {"name": "qwen2.5:7b", "size": "4.4GB", "description": "平衡性能与速度"},
                            {"name": "deepseek-r1:7b", "size": "4.5GB", "description": "推理能力强"},
                            {"name": "llama3.2:3b", "size": "2.0GB", "description": "轻量快速"},
                        ]
                    }
                },
                "cloud": {
                    "enabled": False,
                    "providers": {}
                }
            },
            "server": {
                "multi_port": {"enabled": True, "terminal": 18080, "api": 18081, "models": 18082},
                "single_port": {"enabled": False, "port": 18080},
                "host": "0.0.0.0",
                "debug": False
            },
            "endpoints": {
                "student": {"enabled": True, "name": "学生端", "port": 18080, "path": "/", "features": ["feynman_teaching", "animation_video", "voice_input", "ocr_recognition", "mindmap", "slides"]},
                "admin": {"enabled": True, "name": "管理员端", "port": 18081, "path": "/admin", "features": ["model_management", "system_monitor", "user_management", "log_viewer", "data_export", "settings"]},
                "learning": {"enabled": True, "name": "学习端", "port": 18082, "path": "/learn", "features": ["feynman_teaching", "quiz", "progress_track", "bookmarks"]}
            },
            "features": {
                "speech_recognition": True,
                "ocr_recognition": True,
                "animation": True,
                "mindmap": True,
                "slides": True,
                "payment": True,
                "voicebox": True,
                "adaptive_learning": True,
                "resource_fetcher": True,
                "self_review": True
            }
        }

    def get_models(self) -> Dict[str, Any]:
        """获取模型配置"""
        return self.config.get("models", self._default_config()["models"])

    def get_local_models(self) -> Dict[str, Any]:
        """获取本地模型配置"""
        return self.config.get("models", {}).get("local", {})

    def get_cloud_providers(self) -> Dict[str, Any]:
        """获取云端API提供商配置"""
        return self.config.get("models", {}).get("cloud", {}).get("providers", {})

    def is_ollama_enabled(self) -> bool:
        """检查Ollama是否启用"""
        local = self.get_local_models()
        return local.get("enabled", True)

    def get_ollama_config(self) -> Dict[str, Any]:
        """获取Ollama配置"""
        local = self.get_local_models()
        return local.get("ollama", {
            "base_url": "http://localhost:11434",
            "timeout": 300,
            "default_model": "qwen2.5:7b"
        })

    def get_server_config(self) -> ServerConfig:
        """获取服务器配置"""
        server = self.config.get("server", {})
        multi_port = server.get("multi_port", {})

        return ServerConfig(
            multi_port=multi_port.get("enabled", True),
            terminal_port=multi_port.get("terminal", 18080),
            api_port=multi_port.get("api", 18081),
            models_port=multi_port.get("models", 18082),
            host=server.get("host", "0.0.0.0"),
            debug=server.get("debug", False)
        )

    def get_endpoints(self) -> Dict[str, Endpoint]:
        """获取用户端配置"""
        endpoints = {}
        for name, config in self.config.get("endpoints", {}).items():
            endpoints[name] = Endpoint(
                name=config.get("name", name),
                enabled=config.get("enabled", True),
                port=config.get("port", 0),
                path=config.get("path", "/"),
                features=config.get("features", [])
            )
        return endpoints

    def get_feature(self, feature_name: str) -> bool:
        """获取功能开关状态"""
        features = self.config.get("features", {})
        return features.get(feature_name, True)

    def get_api_key(self, provider: str) -> str:
        """从环境变量获取API Key"""
        env_var = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "tongyi": "DASHSCOPE_API_KEY",
            "zhipu": "ZHIPUAI_API_KEY",
            "kimi": "MOONSHOT_API_KEY",
            "doubao": "DOUBAO_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY"
        }.get(provider, "")

        if env_var:
            return os.environ.get(env_var, "")
        return ""

    def validate_config(self) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []

        # 验证端口
        server = self.get_server_config()
        if server.terminal_port == server.api_port:
            errors.append("terminal端口与api端口重复")
        if server.terminal_port == server.models_port:
            errors.append("terminal端口与models端口重复")
        if server.api_port == server.models_port:
            errors.append("api端口与models端口重复")

        # 验证模型配置
        local = self.get_local_models()
        if local.get("enabled", True):
            ollama = local.get("ollama", {})
            if not ollama.get("base_url"):
                errors.append("Ollama base_url不能为空")

        # 验证功能开关
        for feature in ["speech_recognition", "ocr_recognition", "animation", "mindmap", "slides"]:
            if not isinstance(self.get_feature(feature), bool):
                errors.append(f"功能开关 {feature} 必须为布尔值")

        return errors

    def save_config(self, path: Optional[str] = None):
        """保存配置"""
        save_path = Path(path) if path else self.config_path
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)

    def get_available_models(self) -> List[Dict[str, str]]:
        """获取可用的推荐模型列表"""
        ollama = self.get_ollama_config()
        return ollama.get("recommended_models", [])

    def get_supported_providers(self) -> List[str]:
        """获取支持的云端API提供商"""
        return ["openai", "anthropic", "tongyi", "zhipu", "kimi", "doubao", "deepseek"]

    def generate_quickstart(self) -> str:
        """生成快速启动指南"""
        return """
# LumiLearn 快速启动指南

## 1. 选择用户端
根据您的需求，选择启用以下用户端：

- 学生端 (学生端) - 端口 18080
  功能：费曼教学、动画视频、语音交互、OCR识别、思维导图、幻灯片

- 管理员端 (管理员端) - 端口 18081
  功能：模型管理、系统监控、用户管理、日志查看、数据导出、系统设置

- 学习端 (学习端) - 端口 18082
  功能：费曼教学、练习题、进度追踪、书签收藏

## 2. 配置模型
编辑 deploy_config.yaml：

# 本地模型（推荐）
models:
  local:
    enabled: true
    ollama:
      default_model: "qwen2.5:7b"

# 或启用云端API
models:
  local:
    enabled: false
  cloud:
    enabled: true
    providers:
      openai:
        enabled: true
        api_key: "${OPENAI_API_KEY}"
"""

    def print_config_summary(self):
        """打印配置摘要"""
        print("\n" + "=" * 60)
        print("  LumiLearn 配置摘要")
        print("=" * 60)

        # 模型配置
        local = self.get_local_models()
        print(f"\n🤖 模型配置:")
        print(f"  本地Ollama: {'✅ 已启用' if local.get('enabled', True) else '❌ 已禁用'}")
        if local.get('enabled', True):
            ollama = local.get('ollama', {})
            print(f"  默认模型: {ollama.get('default_model', 'qwen2.5:7b')}")
            print(f"  推荐模型:")
            for model in self.get_available_models():
                print(f"    - {model['name']} ({model['size']}) - {model['description']}")

        cloud = self.config.get('models', {}).get('cloud', {})
        print(f"  云端API: {'✅ 已启用' if cloud.get('enabled', False) else '❌ 已禁用'}")

        # 服务器配置
        server = self.get_server_config()
        print(f"\n🖥️ 服务器配置:")
        print(f"  端口模式: {'三端口' if server.multi_port else '单端口'}")
        if server.multi_port:
            print(f"  终端: {server.terminal_port} / API: {server.api_port} / 模型: {server.models_port}")
        print(f"  监听地址: {server.host}")

        # 用户端配置
        endpoints = self.get_endpoints()
        print(f"\n👥 用户端配置:")
        for name, endpoint in endpoints.items():
            status = "✅" if endpoint.enabled else "❌"
            print(f"  {status} {endpoint.name} - 端口: {endpoint.port} 路径: {endpoint.path}")
            print(f"     功能: {', '.join(endpoint.features)}")

        # 功能开关
        print(f"\n⚡ 功能开关:")
        for feature in ["speech_recognition", "ocr_recognition", "animation", "mindmap", "slides"]:
            status = "✅" if self.get_feature(feature) else "❌"
            print(f"  {status} {feature.replace('_', ' ')}")

        # 验证结果
        errors = self.validate_config()
        if errors:
            print(f"\n⚠️  配置错误:")
            for error in errors:
                print(f"  ❌ {error}")
        else:
            print(f"\n✅ 配置验证通过")

        print("\n" + "=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="LumiLearn 配置管理器")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--summary", action="store_true", help="显示配置摘要")
    parser.add_argument("--validate", action="store_true", help="验证配置")
    parser.add_argument("--quickstart", action="store_true", help="生成快速启动指南")
    parser.add_argument("--add-provider", help="添加云端API提供商")
    parser.add_argument("--set-model", help="设置默认模型")

    args = parser.parse_args()

    # 初始化配置管理器
    config_manager = ConfigManager(args.config)

    # 显示配置摘要
    if args.summary:
        config_manager.print_config_summary()

    # 验证配置
    if args.validate:
        errors = config_manager.validate_config()
        if errors:
            print("\n配置验证失败:")
            for error in errors:
                print(f"  ❌ {error}")
            sys.exit(1)
        else:
            print("\n✅ 配置验证通过")

    # 生成快速启动指南
    if args.quickstart:
        print(config_manager.generate_quickstart())

    # 添加提供商
    if args.add_provider:
        provider = args.add_provider
        print(f"\n请设置环境变量 {provider.upper()}_API_KEY 后重启服务")

    # 设置模型
    if args.set_model:
        local = config_manager.get_local_models()
        ollama = local.get("ollama", {})
        ollama["default_model"] = args.set_model
        local["ollama"] = ollama
        config_manager.config["models"]["local"] = local
        config_manager.save_config()
        print(f"\n✅ 已设置默认模型为: {args.set_model}")


if __name__ == "__main__":
    main()
