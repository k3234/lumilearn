#!/usr/bin/env python3
"""
LumiLearn 模型提供者基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Generator, Any


class ModelProvider(ABC):
    def __init__(self, name: str, base_url: str, default_model: str = ""):
        self._name = name
        self._base_url = base_url
        self._default_model = default_model

    @property
    def name(self) -> str:
        return self._name

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def default_model(self) -> str:
        return self._default_model

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], model: str = None,
            temperature: float = 0.7, max_tokens: int = 2048,
            stream: bool = True) -> Generator[str, None, None]:
        pass

    @abstractmethod
    def chat_sync(self, messages: List[Dict[str, str]], model: str = None,
                  temperature: float = 0.7, max_tokens: int = 2048) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_models(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        pass

    def __repr__(self) -> str:
        return f"<ModelProvider: {self._name} ({self._base_url})>"