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

支持 `--mode lite|full`（默认 full），`-h/--help` 打印帮助。
"""

import sys
from typing import Dict, Any

# --mode 参数帮助文本（各入口脚本共用）
MODE_HELP_TEXT = """--mode {lite,full}  运行模式（默认 full）：
  lite  - 精简模式：仅核心服务，隐藏扩展功能入口，适合低配机器/演示
  full  - 完整模式：全部功能可用（默认）
用法：python <入口脚本> [--mode lite|full]"""

# 合法模式值（"" 表示未指定，等同默认 full）
VALID_MODES = ("", "lite", "full")


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

    def print_help(self, stream=None) -> None:
        """打印 --mode 参数帮助信息（默认输出到 stdout）。"""
        (stream or sys.stdout).write(MODE_HELP_TEXT + "\n")

    def parse_args(self, argv=None) -> str:
        """解析 --mode 参数，返回模式值（默认 ""，等同 full）。

        支持两种写法：
          --mode lite / --mode full
          --mode=lite / --mode=full
        - `-h` / `--help`：打印帮助后退出（exit 0）
        - 非法模式值：打印错误与帮助后退出（exit 2）
        """
        args = list(sys.argv[1:] if argv is None else argv)
        mode = ""
        i = 0
        while i < len(args):
            arg = args[i]
            if arg in ("-h", "--help"):
                self.print_help()
                raise SystemExit(0)
            if arg == "--mode":
                if i + 1 >= len(args):
                    print("[LiteMode] --mode 需要一个参数（lite 或 full）", file=sys.stderr)
                    self.print_help(sys.stderr)
                    raise SystemExit(2)
                mode = args[i + 1]
                i += 2
            elif arg.startswith("--mode="):
                mode = arg.split("=", 1)[1]
                i += 1
            else:
                i += 1
        if mode not in VALID_MODES:
            print(f"[LiteMode] 无效的运行模式: {mode!r}（仅支持 lite / full）", file=sys.stderr)
            self.print_help(sys.stderr)
            raise SystemExit(2)
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
