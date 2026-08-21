#!/usr/bin/env python3
"""
LumiLearn 模型路由器
根据请求特征选择最合适的模型
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import random


class TaskType(str, Enum):
    """任务类型（多基座自适应调度）"""
    comprehension = "comprehension"  # 理解
    calculation = "calculation"      # 计算
    generation = "generation"        # 生成
    diagnostic = "diagnostic"        # 诊断


@dataclass
class RouteRequest:
    """路由请求"""
    topic: str
    mode: str = "chat"
    messages: List[Dict] = field(default_factory=list)
    preferred_model: Optional[str] = None
    task_type: Optional[TaskType] = None


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
        # 多基座自适应调度：按任务类型优先选择最合适的模型系列
        if request.task_type is not None:
            task_result = self._route_by_task_type(request.task_type)
            if task_result is not None:
                return task_result
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

    # 任务类型 -> 优先模型系列关键词（多基座自适应调度）
    _TASK_TYPE_KEYWORDS: Dict[TaskType, str] = {
        TaskType.calculation: "deepseek",   # 计算 → DeepSeek 系列
        TaskType.comprehension: "qwen",     # 理解 → Qwen 系列
    }

    def _route_by_task_type(self, task_type: TaskType) -> Optional[RouteResult]:
        """按任务类型在模型表中查找匹配的模型系列，未命中返回 None"""
        keyword = self._TASK_TYPE_KEYWORDS.get(task_type)
        if not keyword:
            return None
        for provider, cfg in self._models.items():
            for model in cfg.get("models", []):
                if keyword.lower() in model.get("id", "").lower():
                    return RouteResult(
                        model_name=model["id"],
                        provider=provider,
                        base_url=cfg.get("base_url", ""),
                        reason=f"任务类型 {task_type.value} 优先 {keyword} 系列模型"
                    )
        return None

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