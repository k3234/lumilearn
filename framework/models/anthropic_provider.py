#!/usr/bin/env python3
"""
LumiLearn Anthropic Claude 模型提供者
封装 Anthropic Messages API（/v1/messages）
"""
import json
import logging
import os
import time
from typing import Any, Dict, Generator, List, Optional

import requests

from .base import ModelProvider

logger = logging.getLogger("lumilearn.anthropic_provider")

# 公开默认地址（禁止硬编码任何真实内网地址或 Key）
DEFAULT_BASE_URL = "https://api.anthropic.com"
DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
ANTHROPIC_VERSION = "2023-06-01"

_anthropic_provider_instance: Optional["AnthropicProvider"] = None


class AnthropicProvider(ModelProvider):
    """
    Anthropic Claude 模型提供者
    与 OllamaProvider 同构：chat / chat_sync / list_models / health_check
    """

    def __init__(self, base_url: str = None, default_model: str = None,
                 api_key: str = None):
        """
        参数:
            base_url: Anthropic API 地址（默认 https://api.anthropic.com）
            default_model: 默认模型名称
            api_key: API Key（默认读环境变量 ANTHROPIC_API_KEY）
        """
        if base_url is None:
            base_url = os.getenv("ANTHROPIC_BASE_URL", DEFAULT_BASE_URL)
        if default_model is None:
            default_model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)
        if api_key is None:
            api_key = os.getenv("ANTHROPIC_API_KEY", "")

        super().__init__(name="anthropic", base_url=base_url.rstrip("/"),
                         default_model=default_model)
        self._api_key = api_key
        self._timeout = int(os.getenv("ANTHROPIC_TIMEOUT", "300"))

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

    @staticmethod
    def _split_system(messages: List[Dict[str, str]]):
        """把 system 消息抽到顶层 system 字段（Anthropic Messages API 约定）"""
        system_parts, chat_messages = [], []
        for m in messages or []:
            if m.get("role") == "system":
                system_parts.append(str(m.get("content", "")))
            else:
                chat_messages.append({"role": m.get("role", "user"),
                                      "content": m.get("content", "")})
        return "\n".join(p for p in system_parts if p), chat_messages

    def chat(self, messages: List[Dict[str, str]], model: str = None,
             temperature: float = 0.7, max_tokens: int = 2048,
             stream: bool = True) -> Generator[str, None, None]:
        """流式对话（SSE，逐段 yield JSON 字符串）"""
        if model is None:
            model = self._default_model
        system, chat_messages = self._split_system(messages)

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": chat_messages,
            "temperature": temperature,
            "stream": True,
        }
        if system:
            payload["system"] = system

        try:
            resp = requests.post(
                f"{self._base_url}/v1/messages",
                json=payload,
                headers=self._headers(),
                timeout=self._timeout,
                stream=True,
            )
            if resp.status_code != 200:
                yield json.dumps({
                    "error": f"anthropic returned {resp.status_code}: {resp.text[:500]}"
                }, ensure_ascii=False)
                return

            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8")
                if not line_str.startswith("data: "):
                    continue
                try:
                    data = json.loads(line_str[6:])
                except json.JSONDecodeError:
                    continue
                event_type = data.get("type")
                if event_type == "content_block_delta":
                    text = (data.get("delta") or {}).get("text", "")
                    if text:
                        yield json.dumps({
                            "message": {"role": "assistant", "content": text},
                            "done": False,
                        }, ensure_ascii=False)
                elif event_type == "message_stop":
                    break
        except requests.exceptions.Timeout:
            yield json.dumps({"error": "anthropic request timed out"}, ensure_ascii=False)
        except requests.exceptions.ConnectionError:
            yield json.dumps({"error": "unable to connect to anthropic"}, ensure_ascii=False)
        except Exception as e:
            yield json.dumps({"error": str(e)}, ensure_ascii=False)

    def chat_sync(self, messages: List[Dict[str, str]], model: str = None,
                  temperature: float = 0.7, max_tokens: int = 2048) -> Dict[str, Any]:
        """同步对话，解析 content[0].text"""
        if model is None:
            model = self._default_model
        system, chat_messages = self._split_system(messages)

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": chat_messages,
            "temperature": temperature,
        }
        if system:
            payload["system"] = system

        try:
            resp = requests.post(
                f"{self._base_url}/v1/messages",
                json=payload,
                headers=self._headers(),
                timeout=self._timeout,
            )
            if resp.status_code != 200:
                return {"error": f"anthropic returned {resp.status_code}: {resp.text[:500]}"}
            data = resp.json()
            content = data.get("content") or []
            text = "".join(
                block.get("text", "") for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
            return {
                "message": {"role": "assistant", "content": text},
                "model": model,
                "done": True,
            }
        except Exception as e:
            return {"error": str(e)}

    def list_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表（GET /v1/models）"""
        try:
            resp = requests.get(
                f"{self._base_url}/v1/models",
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                return [{"name": m.get("id", "unknown"), "id": m.get("id", "")}
                        for m in resp.json().get("data", [])]
        except Exception as e:
            logger.error(f"Failed to list anthropic models: {e}")
        return []

    def health_check(self) -> Dict[str, Any]:
        """健康检查（与 OllamaProvider 同构的返回结构）"""
        result = {"status": "unknown", "gateway": "unknown", "models": 0, "latency_ms": 0}
        try:
            t0 = time.time()
            resp = requests.get(
                f"{self._base_url}/v1/models",
                headers=self._headers(),
                timeout=5,
            )
            latency = round((time.time() - t0) * 1000)
            if resp.status_code == 200:
                result["status"] = "healthy"
                result["gateway"] = "online"
                result["models"] = len(resp.json().get("data", []))
                result["latency_ms"] = latency
            else:
                result["status"] = "degraded"
                result["gateway"] = "offline"
        except Exception as e:
            result["status"] = "offline"
            result["gateway"] = "offline"
            result["error"] = str(e)
        return result


def get_anthropic_provider(base_url: str = None, default_model: str = None,
                           api_key: str = None) -> AnthropicProvider:
    """获取 AnthropicProvider 单例"""
    global _anthropic_provider_instance
    if _anthropic_provider_instance is None:
        _anthropic_provider_instance = AnthropicProvider(base_url, default_model, api_key)
    return _anthropic_provider_instance
