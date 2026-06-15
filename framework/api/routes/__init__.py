# -*- coding: utf-8 -*-
"""
灵学 lumilearn - API 路由包
统一管理所有API蓝图的注册和导出

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-02
"""

from .chat import chat_bp
from .speech import speech_bp
from .ocr import ocr_bp
from .review import review_bp
from .resources import resources_bp
from .models import models_bp
from .feynman import feynman_bp
from .payment import payment_bp  # 支付宝支付
from .voicebox import voicebox_bp  # Voicebox语音合成
from .animation import animation_bp  # Manim 动画生成
from .providers import providers_bp  # API Key 管理
from .slides import slides_bp  # 幻灯片生成
from .mindmap import mindmap_bp  # 思维导图生成

__all__ = [
    "chat_bp",
    "speech_bp",
    "ocr_bp",
    "review_bp",
    "resources_bp",
    "models_bp",
    "feynman_bp",
    "payment_bp",
    "voicebox_bp",
    "animation_bp",
    "providers_bp",
    "slides_bp",
    "mindmap_bp",
]