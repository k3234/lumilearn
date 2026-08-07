# -*- coding: utf-8 -*-
"""
LumiLearn 管理员系统
- 认证：密码哈希 + 会话令牌
- Agent 注册表：内置 Agent 生命周期管理
- 管理服务：用户/模型/系统管理
"""
from .auth import AdminAuth, get_admin_auth, require_admin
try:
    from .agents import AgentRegistry, get_agent_registry
except ImportError:
    # agents 模块尚未创建（由后续任务补充），在此之前保持轻量导出
    AgentRegistry = None
    get_agent_registry = None

__all__ = [
    "AdminAuth",
    "get_admin_auth",
    "require_admin",
    "AgentRegistry",
    "get_agent_registry",
]
