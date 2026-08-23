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

import os
import sys
import logging
from typing import Dict, Any

# --mode 参数帮助文本（各入口脚本共用）
MODE_HELP_TEXT = """--mode {lite,full}  运行模式（默认 full）：
  lite  - 精简模式：仅核心服务，隐藏扩展功能入口，适合低配机器/演示
  full  - 完整模式：全部功能可用（默认）
--log-level {debug,info,warning,error}  日志级别（默认随模式）：
  lite  - 默认 warning（仅错误与警告，静默访问日志，降低 CPU 负载）
  full  - 默认 info
  也可通过环境变量 LUMILEARN_LOG_LEVEL 指定
用法：python <入口脚本> [--mode lite|full] [--log-level debug|info|warning|error]"""

# 合法模式值（"" 表示未指定，等同默认 full）
VALID_MODES = ("", "lite", "full")

# 日志级别映射（供 --log-level 与 LUMILEARN_LOG_LEVEL 共用）
_LOG_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "warn": logging.WARNING,
    "error": logging.ERROR,
}

# lite 模式下默认日志级别：WARNING，仅输出错误与警告，降低 IO 与 CPU 负载
LITE_DEFAULT_LOG_LEVEL = "warning"
# full 模式下默认日志级别：INFO
FULL_DEFAULT_LOG_LEVEL = "info"

# 非必要日志器：lite 模式下静默（werkzeug 访问日志 / 仪表盘轮询噪音）
LITE_QUIET_LOGGERS = ("werkzeug", "flask.app")


class LiteModeManager:
    """lite 模式管理器：控制轻量自学模式的启用与各服务开关。"""

    # lite 模式下保留的核心学习服务
    CORE_SERVICES = ("terminal", "api", "student_portal")

    def __init__(self, mode: str = ""):
        """mode="lite" 时启用 lite 模式"""
        self.mode = mode or ""
        # 日志开关：--log-level 解析结果（如未指定则为空串）
        self.log_level = ""

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
        log_level = ""
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
            elif arg == "--log-level":
                if i + 1 >= len(args):
                    print("[LiteMode] --log-level 需要一个参数（debug/info/warning/error）", file=sys.stderr)
                    raise SystemExit(2)
                log_level = args[i + 1]
                i += 2
            elif arg.startswith("--log-level="):
                log_level = arg.split("=", 1)[1]
                i += 1
            else:
                i += 1
        if mode not in VALID_MODES:
            print(f"[LiteMode] 无效的运行模式: {mode!r}（仅支持 lite / full）", file=sys.stderr)
            self.print_help(sys.stderr)
            raise SystemExit(2)
        if log_level and log_level.strip().lower() not in _LOG_LEVEL_MAP:
            print(f"[LiteMode] 无效的日志级别: {log_level!r}（仅支持 debug/info/warning/error）", file=sys.stderr)
            raise SystemExit(2)
        self.log_level = log_level.strip().lower()
        return mode

    # ------------------------------------------------------------
    # 日志开关
    # ------------------------------------------------------------
    def configure_logging(self, log_level: str = "") -> str:
        """配置日志级别与静默规则（日志开关）。

        优先级：
          1. `--log-level <level>` 命令行参数 / 环境变量 LUMILEARN_LOG_LEVEL（显式指定）
          2. lite 模式 → WARNING（仅错误与警告）；full 模式 → INFO

        lite 模式下额外静默 werkzeug / flask.app 等非必要日志器，
        显著降低请求访问日志的 IO 与 CPU 开销。

        返回：最终生效的日志级别（字符串，如 "warning"/"info"）。
        """
        # 1. 显式优先级：环境变量 > 命令行默认值
        env_level = os.environ.get("LUMILEARN_LOG_LEVEL", "").strip().lower()
        if env_level and env_level not in _LOG_LEVEL_MAP:
            print(f"[LiteMode] 无效的日志级别 {env_level!r}，忽略（可选：debug/info/warning/error）",
                  file=sys.stderr)
            env_level = ""

        # 2. 命令行参数 --log-level（如已解析到）
        arg_level = (log_level or "").strip().lower()

        effective = ""
        for candidate in (arg_level, env_level):
            if candidate and candidate in _LOG_LEVEL_MAP:
                effective = candidate
                break
        if not effective:
            effective = LITE_DEFAULT_LOG_LEVEL if self.is_lite() else FULL_DEFAULT_LOG_LEVEL

        level = _LOG_LEVEL_MAP[effective]
        logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

        # lite 模式：静默非必要日志器
        if self.is_lite():
            for name in LITE_QUIET_LOGGERS:
                logging.getLogger(name).setLevel(logging.ERROR)
        else:
            # full 模式：恢复 werkzeug 默认级别（仅当未被显式配置时）
            if not log_level and not env_level:
                logging.getLogger("werkzeug").setLevel(logging.WARNING)

        return effective

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
