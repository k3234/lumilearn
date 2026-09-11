#!/usr/bin/env python3
"""
LumiLearn Google Gemini 模型提供者
封装 Gemini Generative Language API（/v1beta/models/{model}:generateContent）
"""
import json
import logging
import os
import time
from typing import Any, Dict, Generator, List, Optional

import requests

from .base import ModelProvider

logger = logging.getLogger("lumilearn.gemini_provider")

# 公开默认地址（禁止硬编码任何真实内网地址或 Key）
DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com"
DEFAULT_MODEL = "gemini-2.0-flash"

_gemini_provider_instance: Optional["GeminiProvider"] = None


class GeminiProvider(ModelProvider):
    """
    Google Gemini 模型提供者
    与 OllamaProvider 同构：chat / chat_sync / list_models / health_check
    """

    def __init__(self, base_url: str = None, default_model: str = None,
                 api_key: str = None):
        """
        参数:
            base_url: Gemini API 地址（默认 https://generativelanguage.googleapis.com）
            default_model: 默认模型名称
            api_key: API Key（默认读环境变量 GOOGLE_API_KEY）
        """
        if base_url is None:
            base_url = os.getenv("GOOGLE_BASE_URL", DEFAULT_BASE_URL)
        if default_model is None:
            default_model = os.getenv("GOOGLE_MODEL", DEFAULT_MODEL)
        if api_key is None:
            api_key = os.getenv("GOOGLE_API_KEY", "")

        super().__init__(name="gemini", base_url=base_url.rstrip("/"),
                         default_model=default_model)
        self._api_key = api_key
        self._timeout = int(os.getenv("GOOGLE_TIMEOUT", "300"))

    @staticmethod
    def _build_payload(messages: List[Dict[str, str]], temperature: float,
                       max_tokens: int) -> Dict[str, Any]:
        """把 OpenAI 风格 messages 转成 Gemini 的 contents + systemInstruction"""
        contents, system_parts = [], []
        for m in messages or []:
            role = m.get("role", "user")
            text = str(m.get("content", ""))
            if role == "system":
                system_parts.append(text)
                continue
            contents.append({
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": text}],
            })
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature,
                                 "maxOutputTokens": max_tokens},
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}
        return payload

    @staticmethod
    def _extract_text(data: Dict[str, Any]) -> str:
        """从 generateContent 响应解析 candidates[0].content.parts[*].text"""
        candidates = data.get("candidates") or []
        if not candidates:
            return ""
        parts = ((candidates[0].get("content") or {}).get("parts")) or []
        return "".join(p.get("text", "") for p in parts if isinstance(p, dict))

    def chat(self, messages: List[Dict[str, str]], model: str = None,
             temperature: float = 0.7, max_tokens: int = 2048,
             stream: bool = True) -> Generator[str, None, None]:
        """流式对话（streamGenerateContent + SSE，逐段 yield JSON 字符串）"""
        if model is None:
            model = self._default_model
        payload = self._build_payload(messages, temperature, max_tokens)

        try:
            resp = requests.post(
                f"{self._base_url}/v1beta/models/{model}:streamGenerateContent",
                params={"alt": "sse", "key": self._api_key},
                json=payload,
                timeout=self._timeout,
                stream=True,
            )
            if resp.status_code != 200:
                yield json.dumps({
                    "error": f"gemini returned {resp.status_code}: {resp.text[:500]}"
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
                text = self._extract_text(data)
                if text:
                    yield json.dumps({
                        "message": {"role": "assistant", "content": text},
                        "done": False,
                    }, ensure_ascii=False)
        except requests.exceptions.Timeout:
            yield json.dumps({"error": "gemini request timed out"}, ensure_ascii=False)
        except requests.exceptions.ConnectionError:
            yield json.dumps({"error": "unable to connect to gemini"}, ensure_ascii=False)
        except Exception as e:
            yield json.dumps({"error": str(e)}, ensure_ascii=False)

    def chat_sync(self, messages: List[Dict[str, str]], model: str = None,
                  temperature: float = 0.7, max_tokens: int = 2048) -> Dict[str, Any]:
        """同步对话，解析 candidates[0].content.parts[0].text"""
        if model is None:
            model = self._default_model
        payload = self._build_payload(messages, temperature, max_tokens)

        try:
            resp = requests.post(
                f"{self._base_url}/v1beta/models/{model}:generateContent",
                params={"key": self._api_key},
                json=payload,
                timeout=self._timeout,
            )
            if resp.status_code != 200:
                return {"error": f"gemini returned {resp.status_code}: {resp.text[:500]}"}
            text = self._extract_text(resp.json())
            return {
                "message": {"role": "assistant", "content": text},
                "model": model,
                "done": True,
            }
        except Exception as e:
            return {"error": str(e)}

    def list_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表（GET /v1beta/models）"""
        try:
            resp = requests.get(
                f"{self._base_url}/v1beta/models",
                params={"key": self._api_key},
                timeout=10,
            )
            if resp.status_code == 200:
                models = []
                for m in resp.json().get("models", []):
                    name = m.get("name", "")              # 形如 models/gemini-2.0-flash
                    mid = name.split("/", 1)[-1] if name else ""
                    models.append({"name": mid or name, "id": mid})
                return models
        except Exception as e:
            logger.error(f"Failed to list gemini models: {e}")
        return []

    def health_check(self) -> Dict[str, Any]:
        """健康检查（与 OllamaProvider 同构的返回结构）"""
        result = {"status": "unknown", "gateway": "unknown", "models": 0, "latency_ms": 0}
        try:
            t0 = time.time()
            resp = requests.get(
                f"{self._base_url}/v1beta/models",
                params={"key": self._api_key},
                timeout=5,
            )
            latency = round((time.time() - t0) * 1000)
            if resp.status_code == 200:
                result["status"] = "healthy"
                result["gateway"] = "online"
                result["models"] = len(resp.json().get("models", []))
                result["latency_ms"] = latency
            else:
                result["status"] = "degraded"
                result["gateway"] = "offline"
        except Exception as e:
            result["status"] = "offline"
            result["gateway"] = "offline"
            result["error"] = str(e)
        return result


def get_gemini_provider(base_url: str = None, default_model: str = None,
                        api_key: str = None) -> GeminiProvider:
    """获取 GeminiProvider 单例"""
    global _gemini_provider_instance
    if _gemini_provider_instance is None:
        _gemini_provider_instance = GeminiProvider(base_url, default_model, api_key)
    return _gemini_provider_instance
