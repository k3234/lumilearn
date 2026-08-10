# -*- coding: utf-8 -*-
"""
LumiLearn 统一配置中心（脱敏版）
================================
langgraph_engine 等模型编排模块的配置来源。

隐私约定：
  - 所有远程服务地址一律从环境变量读取（REMOTE_HOST / OLLAMA_URL 等），
    不硬编码任何真实 IP；未设置时回退到 localhost 占位。
  - 云端 API Key 一律从环境变量读取（对应 .env，已被 .gitignore 忽略），
    本文件不含任何真实 Key。
"""

import os

# 尝试加载 .env（缺失时静默跳过，不影响 import）
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ==================== 项目根路径 ====================
DISK_DATA = os.path.dirname(os.path.abspath(__file__))

# ==================== 远程服务（占位/环境变量，禁止硬编码真实 IP） ====================
REMOTE_HOST = os.environ.get("REMOTE_HOST", "localhost")
REMOTE_OLLAMA_PORT = int(os.environ.get(
    "REMOTE_OLLAMA_PORT", os.environ.get("OLLAMA_PORT", "11434")))
REMOTE_API_PORT = int(os.environ.get("REMOTE_API_PORT", "18000"))

# ==================== 云端模型 API（端点均为公开地址，Key 走环境变量） ====================
CLOUD_MODELS = {
    "Doubao-Seed-2.0-Code": {
        "provider":    "doubao",
        "api_base":    "https://ark.cn-beijing.volces.com/api/v3",
        "api_key_env": "DOUBAO_API_KEY",
        "type":        "cloud",
    },
    "GLM-5": {
        "provider":    "zhipu",
        "api_base":    "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPU_API_KEY",
        "type":        "cloud",
    },
    "Kimi-K2.5": {
        "provider":    "moonshot",
        "api_base":    "https://api.moonshot.cn/v1",
        "api_key_env": "MOONSHOT_API_KEY",
        "type":        "cloud",
    },
    "MiniMax-M2.5": {
        "provider":    "minimax",
        "api_base":    "https://api.minimax.chat/v1",
        "api_key_env": "MINIMAX_API_KEY",
        "type":        "cloud",
    },
}

# ==================== 远程自研模型（地址由 REMOTE_HOST 占位） ====================
REMOTE_MODELS = {
    "lumilearn-remote": {
        "name": "lumilearn-remote",
        "api_base": f"http://{REMOTE_HOST}:{REMOTE_API_PORT}",
        "type":     "remote_custom",
    },
}


def get_cloud_api_key(model_id: str) -> str:
    """按模型 ID 从环境变量读取 API Key（未配置返回空串）。"""
    cfg = CLOUD_MODELS.get(model_id, {})
    env_name = cfg.get("api_key_env", "")
    if not env_name:
        return ""
    return os.environ.get(env_name, "")


if __name__ == "__main__":
    print(f"DISK_DATA           = {DISK_DATA}")
    print(f"REMOTE_HOST         = {REMOTE_HOST}")
    print(f"REMOTE_OLLAMA_PORT  = {REMOTE_OLLAMA_PORT}")
    print(f"REMOTE_API_PORT     = {REMOTE_API_PORT}")
    print(f"云端模型: {list(CLOUD_MODELS)}")
    print(f"远程模型: {list(REMOTE_MODELS)}")
