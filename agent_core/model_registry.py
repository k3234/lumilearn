# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — 模型注册表

从 langgraph_engine.py 提取的模型注册表，提供统一的模型管理能力。

模型来源（共12个）：
  远程 Ollama (2):  qwen2.5:7b, deepseek-r1:1.5b
  远程自定义 (1):   lumilearn-remote
  云端 (5):         Doubao-Seed-2.0-Code, GLM-5, Kimi-K2.5, MiniMax-M2.5, Doubao-Seed-Code
  SOLO (5):         同上5个云端模型（降级模拟）
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# 确保能导入项目配置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumilearn_config import (
    REMOTE_HOST, REMOTE_OLLAMA_PORT, REMOTE_API_PORT,
    CLOUD_MODELS, REMOTE_MODELS, get_cloud_api_key,
)
from lumilearn_shared import OLLAMA_MODELS, SOLO_MODELS


# ================================================================
# 模型条目
# ================================================================
@dataclass
class ModelEntry:
    """
    模型注册条目。

    provider 类型：
      - remote_ollama  : 远程 Ollama 服务
      - remote_custom  : 远程自定义 API（如 LumiLearn 自有模型）
      - cloud          : 云端 API（Doubao/GLM/Kimi/MiniMax）
      - solo           : SOLO 内置降级模拟
    """
    id: str
    name: str
    provider: str          # "remote_ollama" | "remote_custom" | "cloud" | "solo"
    weight: int            # 投票权重
    endpoint: str          # API 地址
    api_key: str = ""
    model_ref: str = ""    # 实际调用时用的 model name
    max_tokens: int = 2000
    timeout: int = 60

    def call(self, prompt: str, timeout: Optional[int] = None) -> str:
        """调用模型并返回文本响应"""
        t0 = time.time()
        try:
            if self.provider == "remote_ollama":
                result = self._call_ollama(prompt, timeout or self.timeout)
            elif self.provider == "remote_custom":
                result = self._call_remote_api(prompt, timeout or self.timeout)
            elif self.provider == "cloud":
                result = self._call_cloud(prompt, timeout or self.timeout)
            elif self.provider == "solo":
                result = self._solo_simulate(prompt)
            else:
                result = f"[未知provider: {self.provider}]"
            return result
        except Exception as e:
            return f"[{self.name} 调用失败: {e}]"
        finally:
            self._last_latency = time.time() - t0

    @property
    def last_latency(self) -> float:
        return getattr(self, "_last_latency", 0.0)

    def _call_ollama(self, prompt: str, timeout: int) -> str:
        try:
            import requests
            resp = requests.post(
                f"{self.endpoint}/api/generate",
                json={"model": self.model_ref, "prompt": prompt,
                      "stream": False, "options": {"temperature": 0.3}},
                timeout=timeout,
            )
            return resp.json().get("response", "")
        except Exception as e:
            return f"[{self.name} 不可用: {e}]"

    def _call_remote_api(self, prompt: str, timeout: int) -> str:
        try:
            import requests
            resp = requests.post(
                f"{self.endpoint}/api/generate",
                json={"model": self.model_ref, "prompt": prompt,
                      "stream": False, "temperature": 0.3},
                timeout=timeout,
            )
            return resp.json().get("response", "")
        except Exception as e:
            return f"[{self.name} 不可用: {e}]"

    def _call_cloud(self, prompt: str, timeout: int) -> str:
        if not self.api_key:
            return f"[{self.name} 无API Key]"
        try:
            import requests
            resp = requests.post(
                f"{self.endpoint}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "model": self.model_ref,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                },
                timeout=timeout,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            return f"[{self.name} HTTP{resp.status_code}]"
        except Exception as e:
            return f"[{self.name} 不可用: {e}]"

    def _solo_simulate(self, prompt: str) -> str:
        """SOLO 模型降级：基于规则的质量评估"""
        content = prompt.lower()
        score = 0
        if len(content) > 100:
            score += 1
        if any(kw in content for kw in ["概念", "定义", "公式", "定理", "分析", "推导"]):
            score += 1
        if not any(bad in content for bad in ["错误", "不对"]):
            score += 1
        return "PASS: 内容质量达标" if score >= 2 else "NEEDS_REVIEW: 需进一步优化"


# ================================================================
# 模型注册表构建
# ================================================================
def build_model_registry() -> List[ModelEntry]:
    """
    构建完整的模型注册表（12个模型）。

    Returns:
        List[ModelEntry]: 所有注册模型
    """
    models: List[ModelEntry] = []

    # 远程 Ollama (权重1)
    for name, cfg in OLLAMA_MODELS.items():
        models.append(ModelEntry(
            id=cfg["name"], name=cfg["name"], provider="remote_ollama",
            weight=1,
            endpoint=f"http://{REMOTE_HOST}:{REMOTE_OLLAMA_PORT}",
            model_ref=cfg["name"],
        ))

    # 远程自定义模型 (权重2)
    for name, cfg in REMOTE_MODELS.items():
        if cfg.get("type") == "remote_custom":
            models.append(ModelEntry(
                id=name, name=name, provider="remote_custom",
                weight=2,
                endpoint=f"http://{REMOTE_HOST}:{REMOTE_API_PORT}",
                model_ref=name,
            ))

    # 云端模型 (权重2)
    for name, cfg in CLOUD_MODELS.items():
        key = get_cloud_api_key(name)
        models.append(ModelEntry(
            id=name, name=name, provider="cloud",
            weight=2,
            endpoint=cfg["api_base"],
            api_key=key,
            model_ref=name,
        ))

    # SOLO 内置模型 (权重2，模拟)
    for name, cfg in SOLO_MODELS.items():
        if not any(m.id == name for m in models):
            models.append(ModelEntry(
                id=name, name=name, provider="solo",
                weight=2, endpoint="",
                model_ref=name,
            ))

    return models


# 全局模型注册表
ALL_MODELS: List[ModelEntry] = build_model_registry()
ALL_MODELS_DICT: Dict[str, ModelEntry] = {m.id: m for m in ALL_MODELS}


# ================================================================
# 模型查询工具
# ================================================================
def get_model(model_id: str) -> Optional[ModelEntry]:
    """按 ID 查询模型"""
    return ALL_MODELS_DICT.get(model_id)


def get_models_by_provider(provider: str) -> List[ModelEntry]:
    """按 provider 筛选模型"""
    return [m for m in ALL_MODELS if m.provider == provider]


def get_models_by_weight(min_weight: int = 1) -> List[ModelEntry]:
    """按权重筛选模型"""
    return [m for m in ALL_MODELS if m.weight >= min_weight]


def get_best_models(count: int = 3) -> List[ModelEntry]:
    """获取权重最高的前 N 个模型"""
    sorted_models = sorted(ALL_MODELS, key=lambda m: m.weight, reverse=True)
    return sorted_models[:count]


def _dynamic_weight_for(model_id: str) -> Optional[float]:
    """读取 AgentWeightConfig 中的动态权重（避免循环导入，延迟导入）"""
    try:
        from agent_core.weight_manager import get_weight_manager
        return get_weight_manager().get_weight(model_id)
    except Exception:
        return None


def get_best_models_by_dynamic_weight(count: int = 3,
                                      prefer_dynamic: bool = True) -> List[ModelEntry]:
    """
    动态权重感知的模型选择（P1-7）。

    综合分数 = 静态权重 × 动态权重（若无动态权重记录则视为 1.0），
    即运行表现（成功率 × 延迟因子）会实时影响模型选优顺序。

    参数：
        count: 返回数量
        prefer_dynamic: 为 True 时使用 静态×动态 综合分排序；
                        为 False 时回退纯静态权重（与 get_best_models 一致）。
    """
    if not prefer_dynamic:
        return get_best_models(count)

    def _score(m: ModelEntry) -> float:
        dyn = _dynamic_weight_for(m.id) or 1.0
        # 兜底：solo 模拟模型权重固定，避免长期霸榜
        base = m.weight
        return base * dyn

    ranked = sorted(ALL_MODELS, key=_score, reverse=True)
    return ranked[:count]


def get_best_model_by_dynamic_weight(exclude_providers: Optional[List[str]] = None,
                                     count: int = 1) -> List[ModelEntry]:
    """按动态权重挑选最优模型（可排除指定 provider，如 solo 模拟）"""
    exclude = set(exclude_providers or [])
    ranked = sorted(
        (m for m in ALL_MODELS if m.provider not in exclude),
        key=lambda m: m.weight * (_dynamic_weight_for(m.id) or 1.0),
        reverse=True,
    )
    return ranked[:count]


def get_model_summary() -> Dict:
    """获取模型注册表摘要"""
    by_provider: Dict[str, List[str]] = {}
    for m in ALL_MODELS:
        by_provider.setdefault(m.provider, []).append(m.name)

    return {
        "total": len(ALL_MODELS),
        "by_provider": by_provider,
        "total_weight": sum(m.weight for m in ALL_MODELS),
        "models": [
            {"id": m.id, "name": m.name, "provider": m.provider, "weight": m.weight}
            for m in ALL_MODELS
        ],
    }


if __name__ == "__main__":
    summary = get_model_summary()
    print(f"模型注册表摘要: {summary['total']} 个模型")
    for provider, names in summary["by_provider"].items():
        print(f"  {provider}: {names}")
