# -*- coding: utf-8 -*-
"""
LumiLearn 集中日志脱敏工具
=========================
统一在日志写入前清洗敏感信息，防止密码 / Token / API Key / 手机号 /
身份证 / 内网 IP 等进入日志文件或审计记录。

用法：
    from framework.security.sanitize import sanitize_text, sanitize_payload

    logger.info(sanitize_text(f"登录失败 user={user} body={body}"))
    log_payload = sanitize_payload(request.get_json() or {})
"""
import re
from typing import Any

#: 需要整值打码的敏感字段名（递归生效）
_SENSITIVE_KEYS = {
    "password", "passwd", "pwd", "secret", "api_key", "apikey", "access_key",
    "secret_key", "authorization", "token", "access_token", "refresh_token",
    "private_key", "app_secret", "alipay_private_key", "cookie", "set-cookie",
    "x-admin-token", "x-auth-token", "creds", "credentials",
}

#: 敏感值替换掩码
_MASK = "[REDACTED]"

#: 文本级敏感模式（输出/日志字符串）
_TEXT_PATTERNS = [
    # 密码/密钥/Token 赋值（key=value 或 key: value）
    re.compile(r"(?i)(api[_-]?key|secret|password|passwd|pwd|token|access_token)"
               r"[\"']?\s*[=:]\s*[\"'][^\"']{4,}[\"']"),
    re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/=-]{8,}"),
    # API Key 风格（sk-xxx / AKIA / ghp_ / AIza）
    re.compile(r"\bsk-[a-zA-Z0-9]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[a-zA-Z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}\b"),
    # 私钥头
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]*?-----END (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    # 手机号 / 身份证号
    re.compile(r"\b1[3-9]\d{9}\b"),
    re.compile(r"\b\d{17}[\dXx]\b"),
    # 内网 IPv4（192.168/10.x/172.16-31）
    re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"),
    re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    re.compile(r"\b172\.(1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3}\b"),
]


def sanitize_text(text: str) -> str:
    """清洗字符串日志中的敏感信息，返回脱敏后的文本。"""
    if not text:
        return text
    result = str(text)
    for pat in _TEXT_PATTERNS:
        result = pat.sub(_MASK, result)
    return result


def _sanitize_value(value: Any, key: str = "") -> Any:
    """递归清洗单个值；敏感键名的值整值打码。"""
    if key.strip().lower() in _SENSITIVE_KEYS:
        if isinstance(value, (str, int, float)):
            return _MASK
        if isinstance(value, (dict, list)):
            return _MASK
        return _MASK
    return sanitize_payload(value)


def sanitize_payload(payload: Any) -> Any:
    """递归清洗结构化数据（dict/list），敏感键打码、字符串内联脱敏。"""
    if isinstance(payload, dict):
        return {k: _sanitize_value(v, k) for k, v in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [_sanitize_value(v) for v in payload]
    if isinstance(payload, str):
        return sanitize_text(payload)
    return payload


def mask_query_string(path: str) -> str:
    """清洗 URL 查询字符串中的敏感参数（token/password/key 等）。"""
    if not path or "?" not in path:
        return path
    base, _, query = path.partition("?")
    parts = []
    for kv in query.split("&"):
        if not kv:
            continue
        if "=" in kv:
            k, _, v = kv.partition("=")
            if k.strip().lower() in _SENSITIVE_KEYS:
                parts.append(f"{k}={_MASK}")
                continue
        parts.append(kv)
    return f"{base}?{'&'.join(parts)}" if parts else base
