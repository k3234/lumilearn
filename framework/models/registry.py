#!/usr/bin/env python3
"""
LumiLearn 模型注册中心
管理所有可用的模型提供者
"""
import logging
from typing import Dict, Optional, Any

from .base import ModelProvider
from .ollama_provider import OllamaProvider

logger = logging.getLogger("lumilearn.registry")


class ModelRegistry:
    """
    模型注册中心
    管理所有已注册的模型提供者
    """
    
    def __init__(self):
        self._providers: Dict[str, ModelProvider] = {}
        self._default_provider: Optional[str] = None
    
    def register(self, name: str, provider: ModelProvider, alias: str = None,
                metadata: Dict[str, Any] = None):
        """
        注册模型提供者
        
        参数:
            name: 提供者名称
            provider: 提供者实例
            alias: 别名
            metadata: 元数据
        """
        self._providers[name] = provider
        
        # 如果标记为默认，设置为默认提供者
        if metadata and metadata.get("default"):
            self._default_provider = name
        
        # 如果没有默认提供者，第一个注册的成为默认
        if self._default_provider is None:
            self._default_provider = name
        
        logger.info(f"Registered model provider: {name}")
    
    def get(self, name: str = None) -> Optional[ModelProvider]:
        """
        获取模型提供者
        
        参数:
            name: 提供者名称，None 则返回默认提供者
            
        返回:
            提供者实例
        """
        if name is None:
            name = self._default_provider
        
        return self._providers.get(name)
    
    def get_default(self) -> Optional[ModelProvider]:
        """获取默认提供者"""
        if self._default_provider:
            return self._providers.get(self._default_provider)
        return None
    
    def list_providers(self) -> Dict[str, ModelProvider]:
        """列出所有提供者"""
        return dict(self._providers)
    
    def unregister(self, name: str):
        """注销提供者"""
        if name in self._providers:
            del self._providers[name]
            if self._default_provider == name:
                self._default_provider = next(iter(self._providers), None)
    
    def __repr__(self) -> str:
        return f"<ModelRegistry: {len(self._providers)} providers>"
    
    def __len__(self) -> int:
        return len(self._providers)


# 单例实例
_registry_instance: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    """
    获取 ModelRegistry 单例
    
    返回:
        ModelRegistry 实例
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ModelRegistry()
    return _registry_instance
