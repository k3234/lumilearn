# -*- coding: utf-8 -*-
"""
灵学 lumilearn - API 路由包
统一管理所有API蓝图的注册和导出

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-02
"""

from .admin import admin_bp  # 管理员管理
from .animation import animation_bp  # Manim 动画生成
from .auth import auth_bp  # 账号登录（users 表）
from .chat import chat_bp
from .feynman import feynman_bp
from .learning import learn_bp  # L4 学习路径 + BKT 知识追踪
from .mindmap import mindmap_bp  # 思维导图生成
from .models import models_bp
from .ocr import ocr_bp
from .payment import payment_bp  # 支付宝支付
from .providers import providers_bp  # API Key 管理
from .review import review_bp
from .security import security_bp  # 安全网关
from .slides import slides_bp  # 幻灯片生成
from .speech import speech_bp
from .voicebox import voicebox_bp  # Voicebox语音合成

# 端口整合：抽为 Blueprint 工厂（统一管理门户 server.py 注册）
from .analytics import create_analytics_bp  # 学习分析仪表盘
from .student_learn import create_student_learn_bp  # 学生费曼学习 API
from .student_platform import create_student_platform_bp  # 学生端前端静态服务
from .teacher import create_teacher_portal_bp  # 教师端 API

__all__ = [
    "chat_bp",
    "speech_bp",
    "ocr_bp",
    "review_bp",
    "models_bp",
    "feynman_bp",
    "payment_bp",
    "voicebox_bp",
    "animation_bp",
    "providers_bp",
    "slides_bp",
    "mindmap_bp",
    "security_bp",
    "admin_bp",
    "auth_bp",
    "learn_bp",
    # Blueprint 工厂（端口整合）
    "create_analytics_bp",
    "create_student_learn_bp",
    "create_student_platform_bp",
    "create_teacher_portal_bp",
]
