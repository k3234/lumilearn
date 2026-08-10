# -*- coding: utf-8 -*-
"""
灵学 lumilearn - Chat API 路由
提供对话端点：支持流式响应（SSE）、费曼模式、多模型调用

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-02
"""

import json
import logging
import requests
from flask import Blueprint, request, jsonify, Response, stream_with_context

from framework.services.chat_service import get_chat_service
from framework.services.provider_service import get_provider_service, ProviderService

logger = logging.getLogger("lumilearn.routes.chat")

chat_bp = Blueprint("chat", __name__)

CLOUD_TIMEOUT = 300


@chat_bp.route("/api/port-config", methods=["GET", "OPTIONS"])
def port_config():
    """获取当前请求端口配置的模型（供前端终端显示/默认选择）"""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    provider, model = _resolve_port_config()
    return jsonify({
        "success": True,
        "provider": provider,
        "model": model,
    })


def _get_provider_service():
    """获取 ProviderService 单例（与 Admin 面板共享配置，热更新）"""
    return get_provider_service()


def _resolve_port_config():
    """
    根据请求来源端口解析该端口配置的 provider/model。
    返回 (provider, model) 或 (None, None)。
    """
    try:
        from flask import request as req
        host = req.host  # 形如 localhost:18080
        port = host.rsplit(":", 1)[-1]
        if not port.isdigit():
            return None, None
        port_int = int(port)
        ps = _get_provider_service()
        port_map = ps.get_port_model_map()
        for key, cfg in port_map.items():
            if int(cfg.get("port", 0)) == port_int:
                return cfg.get("provider", "ollama"), cfg.get("model", "")
        return None, None
    except Exception:
        return None, None


def _resolve_cloud_model(model: str):
    """
    检查 model 是否属于云端提供商，如果是则返回 (provider_key, api_key, base_url)。
    如果 model 是本地模型，返回 None。
    """
    ps = _get_provider_service()
    providers = ps._providers
    for key, cfg in providers.items():
        if not cfg.get("enabled", True):
            continue
        for m in cfg.get("models", []):
            if m.get("id") == model:
                api_key = cfg.get("api_key")
                base_url = cfg.get("base_url")
                if api_key:
                    return (key, api_key, base_url)
    return None


def _cloud_chat_stream(model, messages, api_key, base_url, temperature, max_tokens):
    """调用云端 OpenAI 兼容 API 进行流式对话"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=CLOUD_TIMEOUT,
            stream=True,
        )

        if resp.status_code != 200:
            error_body = resp.text[:500]
            yield json.dumps({
                "error": f"cloud API returned {resp.status_code}: {error_body}"
            }, ensure_ascii=False)
            return

        for line in resp.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            yield json.dumps({
                                "message": {"content": content},
                                "done": False,
                            }, ensure_ascii=False)
                    except json.JSONDecodeError:
                        continue

    except requests.exceptions.Timeout:
        yield json.dumps({"error": "cloud API request timed out"}, ensure_ascii=False)
    except requests.exceptions.ConnectionError:
        yield json.dumps({"error": "unable to connect to cloud API"}, ensure_ascii=False)
    except Exception as e:
        yield json.dumps({"error": str(e)}, ensure_ascii=False)


def _cloud_chat_sync(model, messages, api_key, base_url, temperature, max_tokens):
    """调用云端 OpenAI 兼容 API 进行同步对话"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    resp = requests.post(
        f"{base_url}/chat/completions",
        json=payload,
        headers=headers,
        timeout=CLOUD_TIMEOUT,
    )

    if resp.status_code != 200:
        return {"error": f"cloud API returned {resp.status_code}: {resp.text[:500]}"}

    data = resp.json()
    choices = data.get("choices", [])
    if choices:
        message = choices[0].get("message", {})
        return {
            "message": message,
            "model": model,
            "done": True,
        }
    return {"error": "no response from cloud API"}


@chat_bp.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    """
    对话API端点

    请求体（JSON）：
        {
            "model": "模型名称",
            "messages": [{"role": "user", "content": "..."}],
            "mode": "chat" | "reasoning" | "creative" | "feynman",
            "temperature": 0.7,
            "max_tokens": 2048,
            "stream": true
        }

    流式响应（NDJSON）：
        每行一个JSON对象，包含 message.content 或 error 字段
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json(force=True)
    messages = list(data.get("messages", []))
    model = data.get("model", None)
    mode = data.get("mode", "chat")
    role = data.get("role", None)  # 多智能体角色: teacher/assistant/student
    temperature = data.get("temperature", 0.7)
    max_tokens = data.get("max_tokens", 2048)
    stream = data.get("stream", True)

    if not messages:
        return jsonify({"error": "缺少 messages 字段"}), 400

    # 端口模型配置解析：未指定 model 时，根据请求端口自动选择该端口配置的模型
    if not model:
        port_provider, port_model = _resolve_port_config()
        if port_model:
            model = port_model
            logger.info(f"端口配置自动选择模型: {port_provider}/{port_model}")

    # 多智能体角色 System Prompt
    ROLE_PROMPTS = {
        "teacher": "你是一位经验丰富的AI教师。请用结构化方式讲解知识：先给出核心概念，再逐步推导，最后总结要点。使用板书式语言，适当使用\"我们来看\"、\"请注意\"等教师用语。",
        "assistant": "你是一位耐心的AI助教。请用简洁直接的方式回答问题，补充细节，给出具体例子。当学生困惑时，用不同角度重新解释。",
        "student": "你是一位好奇的AI同学。请以学习者视角提出疑问、分享不同理解角度，偶尔提出有深度的追问。你的目标是促进讨论和思考，而非直接给出答案。",
    }

    if role and role in ROLE_PROMPTS:
        # 在消息列表开头插入角色 system prompt
        system_msg = {"role": "system", "content": ROLE_PROMPTS[role]}
        # 避免重复添加
        if not messages or messages[0].get("role") != "system":
            messages = [system_msg] + messages

    # 检查是否为云端模型
    cloud_info = _resolve_cloud_model(model) if model else None

    if cloud_info:
        provider_key, api_key, base_url = cloud_info

        if not stream:
            result = _cloud_chat_sync(model, messages, api_key, base_url,
                                      temperature, max_tokens)
            return jsonify(result)

        def generate_cloud():
            try:
                for chunk in _cloud_chat_stream(model, messages, api_key, base_url,
                                                temperature, max_tokens):
                    yield chunk.encode("utf-8") + b"\n"
            except Exception as e:
                logger.error(f"云端流式对话异常: {e}")
                yield json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8") + b"\n"

        return Response(
            stream_with_context(generate_cloud()),
            content_type="application/x-ndjson; charset=utf-8",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )

    # 本地模型：使用现有 Ollama 调用逻辑
    chat_service = get_chat_service()

    if not stream:
        result = chat_service.chat_sync(messages, mode=mode, model=model,
                                        temperature=temperature,
                                        max_tokens=max_tokens)
        return jsonify(result)

    def generate():
        try:
            for chunk in chat_service.chat(
                messages, mode=mode, model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            ):
                yield chunk.encode("utf-8") + b"\n"
        except Exception as e:
            logger.error(f"流式对话异常: {e}")
            yield json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8") + b"\n"

    return Response(
        stream_with_context(generate()),
        content_type="application/x-ndjson; charset=utf-8",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )