# -*- coding: utf-8 -*-
"""
LumiLearn Framework Core — 异常降级通用机制（FallbackHandler）

为模型调用 / JSON 解析等高风险环节提供统一降级能力：
  - safe_json_parse:    带解析策略切换的 JSON 解析（失败不抛异常，返回 (None, error)）
  - run_with_fallback:  通用函数执行包裹（异常时按 fallback_action 降级）
  - friendly_message:   用户可见的中文友好提示（绝不暴露原始堆栈）

完全离线可用：仅依赖标准库。
"""

import json
from typing import Any, Callable, Dict, Optional, Tuple

# 友好错误提示映射（用户可见，不含任何堆栈/内部细节）
FRIENDLY_MESSAGES: Dict[str, str] = {
    "JSONDecodeError": "模型返回的内容格式异常，暂时无法解析，请稍后重试或换个说法再问。",
    "TimeoutError": "请求超时，模型响应过慢，请稍后重试。",
    "ConnectionError": "网络连接异常，暂时无法连接模型服务，请检查网络后重试。",
    "RateLimitError": "请求过于频繁已被限流，请稍等片刻再试。",
    "KeyError": "模型返回的数据缺少必要字段，请稍后重试。",
    "ValueError": "模型返回的数据内容不合法，请稍后重试。",
    "TypeError": "模型返回的数据类型异常，请稍后重试。",
    "ImportError": "依赖组件加载失败，请检查部署环境。",
    "FileNotFoundError": "所需文件不存在，请检查资源配置。",
    "Exception": "系统繁忙，请稍后重试。",
}


class FallbackHandler:
    """异常降级通用处理器。

    用法示例::

        handler = FallbackHandler()

        # 1) 安全解析 JSON（失败返回 (None, error)，不会抛异常）
        data, err = handler.safe_json_parse(raw_text)
        if err is None:
            use(data)

        # 2) 包裹模型调用（异常时自动降级为友好提示）
        result, err = handler.run_with_fallback(call_model, topic=topic)
        if err is None:
            use(result)
    """

    # ------------------------------------------------------------
    # JSON 安全解析
    # ------------------------------------------------------------
    def safe_json_parse(self, raw: str, retries: int = 2) -> Tuple[Any, Optional[str]]:
        """解析 JSON 字符串，失败时返回 ``(None, error_msg)`` 而非抛异常。

        每次重试切换解析策略（提示词模板切换的轻量实现，作用于输出解析层）：
          - 第 0 次：直接 ``json.loads``
          - 第 1 次：去掉 markdown 代码块包裹（`````json ... `````）后解析
          - 第 2 次及以后：提取首个 ``{`` 到最后一个 ``}`` 之间的内容后解析

        Args:
            raw: 待解析的原始字符串（可为 ``None`` / 空串）
            retries: 额外重试次数，总尝试次数 = ``retries + 1``（默认 2）

        Returns:
            ``(解析结果, None)`` 表示成功；
            ``(None, 错误信息)`` 表示失败（错误信息为可读文本，不含堆栈）。
        """
        if not isinstance(raw, str) or not raw.strip():
            return None, "输入为空或不是字符串，无法解析 JSON"

        # 解析策略表：下标即重试档位
        strategies: Tuple[Callable[[str], str], ...] = (
            lambda r: r,                    # 0: 直接解析
            self._strip_markdown_block,     # 1: 去掉 markdown 代码块包裹
            self._extract_json_object,      # 2: 提取首个 { 到最后一个 } 之间的内容
        )

        last_error: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                text = strategies[min(attempt, len(strategies) - 1)](raw)
                return json.loads(text), None
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                last_error = exc

        return None, f"JSON 解析失败（已尝试 {retries + 1} 种策略）: {last_error}"

    # ------------------------------------------------------------
    # 通用函数降级执行
    # ------------------------------------------------------------
    def run_with_fallback(
        self,
        fn: Callable,
        fallback_action: str = "friendly_message",
        max_retries: int = 2,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[Any, Optional[str]]:
        """执行函数并按 fallback_action 降级，返回 ``(result, error)``。

        - 成功：``(函数返回值, None)``
        - ``JSONDecodeError``（模型输出解析失败）：可重试，每次重试前调用
          ``on_retry(attempt, error)``，调用方可借此切换提示词模板；
          重试耗尽后降级
        - ``TimeoutError`` / ``ConnectionError``（API 限流/超时）：直接降级
        - 其他异常：直接降级

        Args:
            fn: 目标函数（可通过 *args / **kwargs 传参）
            fallback_action: 降级行为，默认 ``"friendly_message"`` 返回中文友好提示；
                其他取值返回 ``"[ErrorType] error"`` 形式的可读错误信息
            max_retries: JSONDecodeError 的最大重试次数（默认 2）
            on_retry: 可选回调 ``on_retry(attempt, error)``，每次重试前调用

        Returns:
            ``(result, None)`` 或 ``(None, 降级提示文本)``
        """
        if not callable(fn):
            return None, "fn 不可调用，无法执行"

        last_error: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                result = fn(*args, **kwargs)
                return result, None
            except json.JSONDecodeError as exc:
                # 模型输出 JSON 解析失败：切换提示词模板后重试
                last_error = exc
                if attempt >= max_retries:
                    break
                if on_retry is not None:
                    try:
                        on_retry(attempt + 1, exc)
                    except Exception:
                        pass  # 回调失败不应阻断降级流程
            except (TimeoutError, ConnectionError) as exc:
                # API 限流 / 超时：直接降级为友好提示
                last_error = exc
                break
            except Exception as exc:
                last_error = exc
                break

        return None, self._fallback_result(fallback_action, last_error)

    def _fallback_result(self, fallback_action: str,
                         error: Optional[Exception]) -> str:
        """根据 fallback_action 组装降级结果文本（不含堆栈）"""
        if error is None:
            return "执行失败，请稍后重试。"
        if fallback_action == "friendly_message":
            return self.friendly_message(type(error).__name__)
        return f"[{type(error).__name__}] {error}"

    # ------------------------------------------------------------
    # 友好提示
    # ------------------------------------------------------------
    def friendly_message(self, error_type: str) -> str:
        """返回用户可见的中文友好错误提示，不暴露任何堆栈/内部细节。

        Args:
            error_type: 异常类型名，如 ``"JSONDecodeError"``；未知类型回退通用提示
        """
        key = error_type or "Exception"
        return FRIENDLY_MESSAGES.get(key, FRIENDLY_MESSAGES["Exception"])

    # ------------------------------------------------------------
    # JSON 解析策略
    # ------------------------------------------------------------
    @staticmethod
    def _strip_markdown_block(raw: str) -> str:
        """去掉 markdown 代码块包裹（`````json ... `````）"""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return text.strip()

    @staticmethod
    def _extract_json_object(raw: str) -> str:
        """提取首个 ``{`` 到最后一个 ``}`` 之间的内容（容忍前后杂质文本）"""
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]
        return text
