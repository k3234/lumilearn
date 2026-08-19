# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — Agent API 级安全控制（Phase 3）

在代码沙箱（framework/security/sandbox.py）之上扩展 Agent 调用级安全：

  代码沙箱（已有）          Agent API 沙箱（本模块）        结果验证沙箱（本模块）
  ┌──────────────┐         ┌──────────────────┐          ┌──────────────────┐
  │ AST 验证     │         │ 调用频率限制      │          │ 敏感信息检测      │
  │ 模块黑名单   │  ────►  │ 预算控制          │  ────►  │ 幻觉/错误占位检测 │
  │ 执行超时     │         │ 模型白名单        │          │ 输出内容过滤      │
  └──────────────┘         └──────────────────┘          └──────────────────┘

核心能力：
  - AgentSafetyGuard.check_call()  : 统一调用前检查（频率+预算+白名单）
  - AgentSafetyGuard.validate_output() : 输出过滤（敏感信息/错误占位符）
  - 与现有 sandbox 协同：Agent 执行代码前先过沙箱，再调用模型
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("lumilearn.agent.safety")


class AgentSafetyGuard:
    """
    Agent API 调用安全控制。

    三层防护：
      1. 调用前检查（check_call）：频率限制 + 预算控制 + 模型白名单
      2. 输出验证（validate_output）：敏感信息 + 错误占位符 + 长度控制
      3. 审计记录（audit）：每次调用留痕，支持人工中断标记
    """

    def __init__(
        self,
        default_rate_limit: int = 30,
        default_window_sec: int = 60,
        default_budget_per_day: int = 100000,   # 估算 token 数
        max_output_len: int = 8000,
        model_whitelist: Optional[Dict[str, List[str]]] = None,
    ):
        self._lock = threading.Lock()
        # 频率限制：{agent_id: {"user": user_id, "count": n, "window_start": ts}}
        self._rate_window: Dict[str, Dict] = {}
        self.default_rate_limit = default_rate_limit
        self.default_window_sec = default_window_sec
        # 预算：{user_id: {"date": "2026-08-17", "tokens": n}}
        self._budgets: Dict[str, Dict] = {}
        # per-user 每日限额覆盖：{user_id: tokens_per_day}
        self._user_budgets: Dict[str, int] = {}
        self.default_budget_per_day = default_budget_per_day
        self.max_output_len = max_output_len
        # 模型白名单：{agent_id: [model_id, ...]}，None 表示全部放行
        self.model_whitelist = model_whitelist or {}
        # 统计
        self.stats = {
            "total_checks": 0,
            "denied_rate": 0,
            "denied_budget": 0,
            "denied_model": 0,
            "output_rejected": 0,
        }
        # 敏感信息模式（输出过滤）
        self.sensitive_patterns = [
            (re.compile(r"(?i)(api[_-]?key|secret|password|passwd|token)\s*[=:]\s*\S+"),
             "凭据泄露"),
            (re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/=-]{8,}", re.IGNORECASE),
             "认证令牌"),
            (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "内网IP"),
            (re.compile(r"(?i)BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY"), "私钥"),
            (re.compile(r"1[3-9]\d{9}"), "手机号"),
            (re.compile(r"\b\d{17}[\dXx]\b"), "身份证号"),
        ]

    # ============================================================
    # 1. 调用前检查
    # ============================================================
    def check_call(
        self,
        agent_id: str,
        user_id: str = "anonymous",
        model_id: str = "",
        budget_tokens: int = 0,
    ) -> Dict:
        """
        统一调用前检查：频率 + 模型白名单 + 预算。

        参数：
            agent_id: Agent 标识
            user_id: 用户标识
            model_id: 将要调用的模型 ID
            budget_tokens: 本次预估消耗 token（用于预算预扣）

        返回：
            {"allowed": bool, "reason": str, "retry_after": int}
        """
        with self._lock:
            self.stats["total_checks"] += 1

            # A. 频率限制（per-agent + per-user）
            rate_ok, retry_after, rate_reason = self._check_rate(agent_id, user_id)
            if not rate_ok:
                self.stats["denied_rate"] += 1
                return {"allowed": False, "reason": rate_reason,
                        "retry_after": retry_after}

            # B. 模型白名单
            if self._check_model_whitelist(agent_id, model_id) is False:
                self.stats["denied_model"] += 1
                return {"allowed": False,
                        "reason": f"模型 {model_id} 不在 Agent {agent_id} 的白名单中",
                        "retry_after": 0}

            # C. 预算控制
            budget_ok, budget_reason = self._check_budget(user_id, budget_tokens)
            if not budget_ok:
                self.stats["denied_budget"] += 1
                return {"allowed": False, "reason": budget_reason,
                        "retry_after": 0}

            # 预算预扣
            self._consume_budget(user_id, budget_tokens)

            return {"allowed": True, "reason": "ok", "retry_after": 0}

    def _check_rate(self, agent_id: str, user_id: str) -> Tuple[bool, int, str]:
        """滑动窗口频率限制"""
        now = time.time()
        key = f"{agent_id}:{user_id}"
        entry = self._rate_window.get(key)
        window = self.default_window_sec

        if entry is None or (now - entry["window_start"]) >= window:
            # 新窗口
            self._rate_window[key] = {
                "user": user_id, "count": 1, "window_start": now}
            return True, 0, "ok"

        entry["count"] += 1
        if entry["count"] > self.default_rate_limit:
            retry_after = int(window - (now - entry["window_start"])) + 1
            return False, retry_after, (
                f"调用频率超限（{self.default_rate_limit}次/{window}秒）")

        return True, 0, "ok"

    def _check_model_whitelist(self, agent_id: str, model_id: str) -> Optional[bool]:
        """模型白名单检查：None 表示未配置（放行），True 允许，False 拒绝"""
        allowed = self.model_whitelist.get(agent_id)
        if allowed is None:
            return None  # 未配置白名单 → 放行
        if not model_id:
            return True
        return model_id in allowed

    def _check_budget(self, user_id: str, tokens: int) -> Tuple[bool, str]:
        """预算控制（按日，per-user 限额覆盖全局默认）"""
        today = datetime.now().strftime("%Y-%m-%d")
        budget = self._budgets.setdefault(
            user_id, {"date": today, "tokens": 0})
        limit = self._user_budgets.get(user_id, self.default_budget_per_day)

        if budget["date"] != today:
            budget["date"] = today
            budget["tokens"] = 0

        if budget["tokens"] + tokens > limit:
            return False, (
                f"预算超限（今日已用 {budget['tokens']} tokens，"
                f"上限 {limit}）")

        return True, "ok"

    def _consume_budget(self, user_id: str, tokens: int):
        today = datetime.now().strftime("%Y-%m-%d")
        budget = self._budgets.setdefault(
            user_id, {"date": today, "tokens": 0})
        if budget["date"] != today:
            budget["date"] = today
            budget["tokens"] = 0
        budget["tokens"] += max(0, tokens)

    def reset_rate(self, agent_id: str = "", user_id: str = ""):
        """重置频率限制（测试/管理用）"""
        with self._lock:
            if agent_id and user_id:
                self._rate_window.pop(f"{agent_id}:{user_id}", None)
            elif agent_id:
                for k in list(self._rate_window):
                    if k.startswith(agent_id + ":"):
                        self._rate_window.pop(k, None)
            else:
                self._rate_window.clear()

    # ============================================================
    # 2. 输出验证
    # ============================================================
    def validate_output(self, content: str, agent_id: str = "") -> Dict:
        """
        输出内容验证与过滤。

        返回：
            {"safe": bool, "issues": [str, ...], "content": 过滤后内容}
        """
        if not content:
            return {"safe": True, "issues": [], "content": content}

        issues = []
        filtered = content

        # A. 长度控制
        if len(content) > self.max_output_len:
            issues.append(f"输出超长（{len(content)}字 > {self.max_output_len}），已截断")
            filtered = content[:self.max_output_len]

        # B. 敏感信息检测
        for pattern, label in self.sensitive_patterns:
            if pattern.search(filtered):
                issues.append(f"检测到{label}，已脱敏")
                filtered = pattern.sub("[已脱敏]", filtered)

        # C. 错误占位符检测（幻觉/不可用信号）
        for bad in ("[不可用]", "[无API Key]", "调用失败", "HTTP4", "HTTP5"):
            if bad in filtered:
                issues.append(f"内容含错误占位符: {bad}")
                # 不直接判定失败，交由 Verifier 处理

        # D. 幻觉警示词检测（无法确认的绝对化表述）
        hallucination_words = ["绝对正确", "百分百准确", "唯一标准答案", "所有教材都这样说"]
        for w in hallucination_words:
            if w in filtered:
                issues.append(f"检测到可能幻觉表述: 「{w}」")

        if issues:
            self.stats["output_rejected"] += 1

        return {"safe": len(issues) == 0, "issues": issues, "content": filtered}

    # ============================================================
    # 3. 工具函数
    # ============================================================
    def estimate_tokens(self, text: str) -> int:
        """粗略估算 token 数（中文按字，英文按词）"""
        if not text:
            return 0
        # 中文字符计 1 token，英文单词按 3 字符/词估算
        cn = len(re.findall(r"[\u4e00-\u9fff]", text))
        en_words = len(re.findall(r"[a-zA-Z0-9]+", text))
        return cn + en_words

    def get_stats(self) -> Dict:
        """获取安全控制统计"""
        with self._lock:
            return dict(self.stats)

    def set_model_whitelist(self, agent_id: str, model_ids: List[str]):
        """设置 Agent 的模型白名单"""
        self.model_whitelist[agent_id] = list(model_ids)

    def set_budget(self, user_id: str, tokens_per_day: int):
        """设置用户每日预算（覆盖全局默认，仅对该用户生效）"""
        self._user_budgets[user_id] = tokens_per_day


# ================================================================
# 单例
# ================================================================
_safety_guard: Optional[AgentSafetyGuard] = None


def get_safety_guard(**kwargs) -> AgentSafetyGuard:
    """获取安全守卫单例"""
    global _safety_guard
    if _safety_guard is None:
        _safety_guard = AgentSafetyGuard(**kwargs)
    return _safety_guard


def reset_safety_guard():
    """重置安全守卫（测试用）"""
    global _safety_guard
    _safety_guard = None


def check_agent_call(agent_id: str, user_id: str = "anonymous",
                     model_id: str = "", budget_tokens: int = 0) -> Dict:
    """一行调用调用前检查"""
    return get_safety_guard().check_call(
        agent_id, user_id, model_id, budget_tokens)


if __name__ == "__main__":
    guard = get_safety_guard()
    print("=== Agent API 安全控制测试 ===")

    # 1. 正常调用
    r = guard.check_call("feynman_teacher", "user1", "qwen2.5:7b", 500)
    print(f"正常调用: allowed={r['allowed']}")

    # 2. 模型白名单
    guard.set_model_whitelist("feynman_teacher", ["qwen2.5:7b"])
    r = guard.check_call("feynman_teacher", "user1", "hack-model", 500)
    print(f"白名单拒绝: allowed={r['allowed']} reason={r['reason']}")

    # 3. 输出过滤
    out = guard.validate_output("我的API_KEY=sk-abc1234567，服务器IP是192.168.1.1")
    print(f"输出过滤: safe={out['safe']} issues={out['issues']}")

    # 4. 频率限制
    guard.reset_rate()
    for i in range(35):
        r = guard.check_call("test_agent", "user_x", "", 0)
    print(f"频率限制: allowed={r['allowed']} reason={r['reason']}")

    # 5. 预算
    guard.set_budget("user_b", 100)
    r = guard.check_call("test_agent", "user_b", "", 100)
    r2 = guard.check_call("test_agent", "user_b", "", 50)
    print(f"预算限制: 第一次allowed={r['allowed']} 第二次allowed={r2['allowed']} reason={r2['reason']}")

    print(f"统计: {guard.get_stats()}")
