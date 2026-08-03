#!/usr/bin/env python3
"""
LumiLearn Ollama 模型提供者
封装 Ollama API 调用
"""
import os
import json
import time
import logging
import requests
from typing import List, Dict, Optional, Generator, Any

from .base import ModelProvider

logger = logging.getLogger("lumilearn.ollama_provider")

# 单例实例
_ollama_provider_instance: Optional["OllamaProvider"] = None


class OllamaProvider(ModelProvider):
    """
    Ollama 模型提供者
    封装 Ollama API 的流式/同步调用
    """
    
    def __init__(self, base_url: str = None, default_model: str = None):
        """
        初始化 Ollama 提供者
        
        参数:
            base_url: Ollama API 地址
            default_model: 默认模型名称
        """
        if base_url is None:
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        if default_model is None:
            default_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        
        super().__init__(name="ollama", base_url=base_url, default_model=default_model)
        self._timeout = int(os.getenv("OLLAMA_TIMEOUT", "300"))
    
    def chat(self, messages: List[Dict[str, str]], model: str = None,
            temperature: float = 0.7, max_tokens: int = 2048,
            stream: bool = True) -> Generator[str, None, None]:
        """
        流式对话
        """
        if model is None:
            model = self._default_model
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            resp = requests.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=self._timeout,
                stream=True
            )
            
            if resp.status_code != 200:
                error_body = resp.text[:500]
                yield json.dumps({
                    "error": f"Ollama returned {resp.status_code}: {error_body}"
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
            yield json.dumps({"error": "Ollama request timed out"}, ensure_ascii=False)
        except requests.exceptions.ConnectionError:
            yield json.dumps({"error": "unable to connect to Ollama"}, ensure_ascii=False)
        except Exception as e:
            yield json.dumps({"error": str(e)}, ensure_ascii=False)
    
    def chat_sync(self, messages: List[Dict[str, str]], model: str = None,
                  temperature: float = 0.7, max_tokens: int = 2048) -> Dict[str, Any]:
        """
        同步对话
        """
        if model is None:
            model = self._default_model
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            resp = requests.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=self._timeout
            )
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {
                    "error": f"Ollama returned {resp.status_code}: {resp.text[:500]}"
                }
        except Exception as e:
            return {"error": str(e)}
    
    def generate(self, prompt: str, model: str = None,
                 temperature: float = 0.7, max_tokens: int = 2048,
                 stream: bool = False) -> str:
        """
        文本生成（非对话模式）
        
        参数:
            prompt: 提示词
            model: 模型名称
            temperature: 温度
            max_tokens: 最大 token 数
            stream: 是否流式
            
        返回:
            生成的文本
        """
        if model is None:
            model = self._default_model
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            resp = requests.post(
                f"{self._base_url}/api/generate",
                json=payload,
                timeout=self._timeout
            )
            
            if resp.status_code == 200:
                return resp.json().get("response", "")
            else:
                logger.error(f"Ollama generate error: {resp.status_code}")
                return ""
        except Exception as e:
            logger.error(f"Ollama generate exception: {e}")
            return ""
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        获取可用模型列表
        """
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=10)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [{
                    "name": m.get("name", "unknown"),
                    "size": m.get("size", 0),
                    "modified_at": m.get("modified_at", "")
                } for m in models]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
        return []
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        """
        result = {
            "status": "unknown",
            "gateway": "unknown",
            "models": 0,
            "latency_ms": 0
        }
        
        try:
            t0 = time.time()
            resp = requests.get(f"{self._base_url}/api/tags", timeout=5)
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


def get_ollama_provider(base_url: str = None, default_model: str = None) -> OllamaProvider:
    """
    获取 OllamaProvider 单例
    
    参数:
        base_url: Ollama API 地址
        default_model: 默认模型名称
        
    返回:
        OllamaProvider 实例
    """
    global _ollama_provider_instance
    if _ollama_provider_instance is None:
        _ollama_provider_instance = OllamaProvider(base_url, default_model)
    return _ollama_provider_instance
