#!/usr/bin/env python3
"""
LumiLearn 模型路由器
根据请求特征选择最合适的模型
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import random


@dataclass
class RouteRequest:
    """路由请求"""
    topic: str
    mode: str = "chat"
    messages: List[Dict] = field(default_factory=list)
    preferred_model: Optional[str] = None


@dataclass
class RouteResult:
    """路由结果"""
    model_name: str
    provider: str = "ollama"
    base_url: str = ""
    reason: str = ""


class ModelRouter:
    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir
        self._load_models()

    def _load_models(self):
        self._models = {
            "ollama": {
                "base_url": "http://localhost:11434",
                "models": [
                    {"id": "lumilearn-v2:latest", "weight": 3.0, "type": "chat"},
                    {"id": "qwen2.5:7b", "weight": 0.5, "type": "chat"},
                    {"id": "deepseek-r1:1.5b", "weight": 0.5, "type": "reasoning"},
                ]
            }
        }
        import os
        base_url = os.getenv("OLLAMA_BASE_URL")
        if base_url:
            self._models["ollama"]["base_url"] = base_url

    def route(self, request: RouteRequest) -> RouteResult:
        if request.preferred_model:
            return RouteResult(
                model_name=request.preferred_model,
                provider="ollama",
                base_url=self._models.get("ollama", {}).get("base_url", ""),
                reason="用户偏好"
            )
        if request.mode == "feynman":
            return RouteResult(
                model_name="lumilearn-v2:latest",
                provider="ollama",
                base_url=self._models.get("ollama", {}).get("base_url", ""),
                reason="费曼教学默认模型"
            )
        if request.mode == "reasoning":
            reasoning_models = [
                m for m in self._models.get("ollama", {}).get("models", [])
                if m.get("type") == "reasoning"
            ]
            if reasoning_models:
                selected = random.choices(
                    reasoning_models,
                    weights=[m.get("weight", 1.0) for m in reasoning_models],
                    k=1
                )[0]
                return RouteResult(
                    model_name=selected["id"],
                    provider="ollama",
                    base_url=self._models.get("ollama", {}).get("base_url", ""),
                    reason="推理模式匹配"
                )
        chat_models = [
            m for m in self._models.get("ollama", {}).get("models", [])
            if m.get("type") in ("chat", "general")
        ]
        if chat_models:
            selected = random.choices(
                chat_models,
                weights=[m.get("weight", 1.0) for m in chat_models],
                k=1
            )[0]
            return RouteResult(
                model_name=selected["id"],
                provider="ollama",
                base_url=self._models.get("ollama", {}).get("base_url", ""),
                reason="默认聊天模型"
            )
        return RouteResult(
            model_name="lumilearn-v2:latest",
            provider="ollama",
            base_url="http://localhost:11434",
            reason="兜底默认"
        )
    def add_provider(self, name: str, base_url: str, models: List[Dict]):
        self._models[name] = {"base_url": base_url, "models": models}
    def list_models(self) -> List[Dict]:
        all_models = []
        for provider, cfg in self._models.items():
            for model in cfg.get("models", []):
                all_models.append({
                    "id": model.get("id"),
                    "provider": provider,
                    "type": model.get("type"),
                    "weight": model.get("weight", 1.0),
                })
        return all_models