#!/usr/bin/env python3
"""
灵学 lumilearn - 对话服务
封装 ModelProvider 调用，集成费曼引擎，消息历史管理
"""
import json
import time
import logging
import requests
import os
from typing import Any, Dict, List, Optional, Generator

from framework.models.ollama_provider import get_ollama_provider
from framework.models.base import ModelProvider
from framework.core.router import ModelRouter, RouteRequest, RouteResult
from framework.core.config import get_config
from framework.engines.feynman_engine import FeynmanEngine

logger = logging.getLogger("lumilearn.chat_service")

DEFAULT_MODEL = "lumilearn-v2:latest"
GATEWAY_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
TIMEOUT = 300


class ChatService:
    """
    对话服务
    """

    def __init__(self, config_dir: str = None):
        self._config = get_config(config_dir)
        self._router = ModelRouter(config_dir)
        self._ollama = get_ollama_provider()
        self._feynman: Optional[FeynmanEngine] = None
        self._history: Dict[str, List[Dict[str, str]]] = {}
        self._default_model = self._ollama.default_model or DEFAULT_MODEL

    def _get_feynman(self) -> FeynmanEngine:
        """懒加载费曼引擎"""
        if self._feynman is None:
            self._feynman = FeynmanEngine(model_name=self._default_model)
        return self._feynman

    def chat(self, messages: List[Dict[str, str]],
             mode: str = "chat",
             temperature: float = 0.7,
             max_tokens: int = 2048,
             stream: bool = True) -> Generator:
        """流式对话"""
        if mode == "feynman":
            yield from self._feynman_chat(messages, stream)
            return

        # 路由选择模型
        last_msg = messages[-1]["content"] if messages else ""
        route_request = RouteRequest(
            topic=last_msg[:50],
            mode=mode,
            messages=messages
        )
        route_result = self._router.route(route_request)
        model = route_result.model_name

        if stream:
            yield json.dumps({"model_version": self.get_model_version(model)}, ensure_ascii=False)
            yield from self._stream_chat(messages, model, temperature, max_tokens)
        else:
            result = self._ollama.chat(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            yield json.dumps(result, ensure_ascii=False)

    def _stream_chat(self, messages: List[Dict[str, str]],
                     model: str,
                     temperature: float,
                     max_tokens: int) -> Generator:
        """通过 Ollama API 进行流式对话"""
        base_url = os.environ.get("OLLAMA_BASE_URL", GATEWAY_URL)

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens}
        }

        try:
            resp = requests.post(
                f"{base_url}/api/chat",
                json=payload,
                timeout=TIMEOUT,
                stream=True
            )

            if resp.status_code != 200:
                error_body = resp.text[:500]
                yield json.dumps({
                    "error": f"gateway returned {resp.status_code}: {error_body}"
                }, ensure_ascii=False)
                return

            for line in resp.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        yield json.dumps(data, ensure_ascii=False)
                    except json.JSONDecodeError:
                        continue

        except requests.exceptions.Timeout:
            yield json.dumps({"error": "gateway request timed out"}, ensure_ascii=False)
        except requests.exceptions.ConnectionError:
            yield json.dumps({"error": "unable to connect to gateway"}, ensure_ascii=False)
        except Exception as e:
            yield json.dumps({"error": str(e)}, ensure_ascii=False)

    def _feynman_chat(self, messages: List[Dict[str, str]],
                      stream: bool = True) -> Generator:
        """费曼教学模式对话"""
        feynman = self._get_feynman()

        topic = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                topic = msg.get("content", "")
                break

        if not topic:
            yield json.dumps({
                "content": "请提供一个学习主题，我来用费曼教学法为你讲解。",
                "done": True
            }, ensure_ascii=False)
            return

        level = "junior"
        for msg in reversed(messages):
            content = msg.get("content", "").lower()
            if "大学" in content or "college" in content:
                level = "college"
                break
            elif "高中" in content or "senior" in content:
                level = "senior"
                break

        for step_data in feynman.explain_stream(topic, level):
            yield json.dumps({
                "step": step_data["step"],
                "step_name": step_data["step_name"],
                "content": step_data["content"],
                "is_last": step_data["is_last"],
                "mode": "feynman"
            }, ensure_ascii=False)
            time.sleep(0.1)

    def chat_sync(self, messages: List[Dict[str, str]],
                  mode: str = "chat",
                  temperature: float = 0.7,
                  max_tokens: int = 2048) -> Dict[str, Any]:
        """同步对话"""
        if mode == "feynman":
            feynman = self._get_feynman()
            topic = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    topic = msg.get("content", "")
                    break
            return feynman.explain(topic, "junior")

        route_request = RouteRequest(
            topic=messages[-1]["content"][:50] if messages else "",
            mode=mode,
            messages=messages
        )
        route_result = self._router.route(route_request)
        model = route_result.model_name

        result = self._ollama.chat_sync(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        result["model_version"] = self.get_model_version(model)
        return result

    def get_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        base_url = os.environ.get("OLLAMA_BASE_URL", GATEWAY_URL)
        try:
            resp = requests.get(f"{base_url}/api/tags", timeout=10)
            models = resp.json().get("models", [])
            return [{
                "name": m.get("name", "unknown"),
                "size": m.get("size", "?"),
                "modified": m.get("modified_at", "")
            } for m in models]
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return []

    def list_custom_models(self) -> List[Dict[str, Any]]:
        """获取自定义训练模型列表"""
        try:
            model_list = get_config().get("models", {}).get("providers", {})
            custom_models = []
            for provider_key, provider_cfg in model_list.items():
                if not provider_cfg.get("enabled", True):
                    continue
                for model in provider_cfg.get("models", []):
                    is_custom = model.get("custom", False)
                    has_custom_tag = "custom" in model.get("tags", [])
                    if is_custom or has_custom_tag:
                        custom_models.append({
                            "name": model.get("id", "unknown"),
                            "model_id": model.get("id", "unknown"),
                            "provider": provider_key,
                            "base_url": provider_cfg.get("base_url", ""),
                            "priority": model.get("priority", None),
                            "tags": model.get("tags", []),
                            "custom": True,
                        })
            return custom_models
        except Exception as e:
            logger.error(f"获取自定义模型列表失败: {e}")
            return []

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取指定模型的元数据信息"""
        try:
            model_list = get_config().get("models", {}).get("providers", {})
            for provider_key, provider_cfg in model_list.items():
                for model in provider_cfg.get("models", []):
                    if model.get("id") == model_name:
                        return {
                            "name": model.get("id", "unknown"),
                            "model_id": model.get("id", "unknown"),
                            "provider": provider_key,
                            "base_url": provider_cfg.get("base_url", ""),
                            "priority": model.get("priority", None),
                            "tags": model.get("tags", []),
                            "custom": model.get("custom", False) or ("custom" in model.get("tags", [])),
                            "version": model.get("version", "latest"),
                        }
            return None
        except Exception as e:
            logger.error(f"获取模型信息失败 ({model_name}): {e}")
            return None

    def get_model_version(self, model_name: str = None) -> str:
        """获取模型版本信息"""
        if model_name is None:
            model_name = self._default_model
        info = self.get_model_info(model_name)
        if info:
            return info.get("version", "latest")
        return "latest"

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        base_url = os.environ.get("OLLAMA_BASE_URL", GATEWAY_URL)
        result = {
            "status": "healthy",
            "gateway": "online",
            "default_model": self._default_model,
            "model_version": self.get_model_version(),
            "feynman_available": self._feynman is not None
        }
        try:
            t0 = time.time()
            resp = requests.get(f"{base_url}/api/tags", timeout=5)
            latency = round((time.time() - t0) * 1000)
            models_count = len(resp.json().get("models", []))
            result["models"] = models_count
            result["latency_ms"] = latency
        except Exception as e:
            result["status"] = "degraded"
            result["gateway"] = "offline"
            result["error"] = str(e)
        return result

    def update_history(self, session_id: str, messages: List[Dict[str, str]]):
        """更新对话历史"""
        self._history[session_id] = messages

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """获取对话历史"""
        return self._history.get(session_id, [])

    def clear_history(self, session_id: str):
        """清除对话历史"""
        self._history.pop(session_id, None)


_chat_service_instance: Optional[ChatService] = None


def get_chat_service(config_dir: str = None) -> ChatService:
    """获取 ChatService 单例"""
    global _chat_service_instance
    if _chat_service_instance is None:
        _chat_service_instance = ChatService(config_dir)
    return _chat_service_instance
