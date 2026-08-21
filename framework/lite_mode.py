#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn lite 模式（轻量自学模式）
====================================
轻量自学模式管理器：通过 `--mode lite` 启动参数或配置启用，
仅保留核心学习服务（terminal / api / student_portal），
关闭教师端、分析仪表盘等非核心服务，降低资源占用，适合自学场景。

用法：
    from framework.lite_mode import LiteModeManager
    manager = LiteModeManager()
    if manager.parse_args() == "lite":
        manager = LiteModeManager("lite")
        app.config["LITE_MODE"] = True
"""

import sys
from typing import Dict, Any


class LiteModeManager:
    """lite 模式管理器：控制轻量自学模式的启用与各服务开关。"""

    # lite 模式下保留的核心学习服务
    CORE_SERVICES = ("terminal", "api", "student_portal")

    def __init__(self, mode: str = ""):
        """mode="lite" 时启用 lite 模式"""
        self.mode = mode or ""

    def is_lite(self) -> bool:
        """当前是否为 lite 模式"""
        return self.mode == "lite"

    def parse_args(self, argv=None) -> str:
        """解析 --mode lite 参数，返回模式值（默认 ""）。

        支持两种写法：
          --mode lite
          --mode=lite
        """
        args = list(sys.argv[1:] if argv is None else argv)
        mode = ""
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--mode" and i + 1 < len(args):
                mode = args[i + 1]
                i += 2
            elif arg.startswith("--mode="):
                mode = arg.split("=", 1)[1]
                i += 1
            else:
                i += 1
        return mode

    def get_enabled_services(self, port_settings: dict) -> dict:
        """返回各服务的启用状态。

        - lite 模式：仅保留核心学习服务（terminal/api/student_portal）enabled=True，
          其他服务 enabled=False
        - 默认模式：保留配置中的 enabled 设置（缺省视为 True，即全部启用）
        """
        result: Dict[str, Any] = {}
        for name, cfg in port_settings.items():
            service = dict(cfg) if isinstance(cfg, dict) else {"enabled": True, "port": cfg}
            if self.is_lite():
                service["enabled"] = name in self.CORE_SERVICES
            else:
                service["enabled"] = bool(service.get("enabled", True))
            result[name] = service
        return result
