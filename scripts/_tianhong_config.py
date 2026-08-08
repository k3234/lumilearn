#!/usr/bin/env python3
"""天虹服务器 SSH 连接配置 — 敏感信息从环境变量读取，不硬编码在仓库中

环境变量:
    TIANHONG_HOST      服务器 IP（默认 192.168.2.68）
    TIANHONG_USER      SSH 用户名（默认 kai）
    TIANHONG_PASSWORD  SSH 密码（必填，未设置时给出提示并退出）

用法（任选）:
    from _tianhong_config import get_config
    cfg = get_config()
    ssh.connect(cfg["host"], username=cfg["user"], password=cfg["password"], timeout=15)
"""
import os
import sys


def get_config(host: str = "", user: str = "") -> dict:
    """返回 SSH 连接配置；host/user 可显式覆盖默认值"""
    cfg_host = host or os.environ.get("TIANHONG_HOST", "192.168.2.68")
    cfg_user = user or os.environ.get("TIANHONG_USER", "kai")
    password = os.environ.get("TIANHONG_PASSWORD", "")

    if not password:
        print(
            "错误: 未设置 TIANHONG_PASSWORD 环境变量。\n"
            "  PowerShell: $env:TIANHONG_PASSWORD='你的密码'\n"
            "  CMD:        set TIANHONG_PASSWORD=你的密码\n"
            "  Linux:      export TIANHONG_PASSWORD='你的密码'",
            file=sys.stderr,
        )
        sys.exit(1)

    return {"host": cfg_host, "user": cfg_user, "password": password}
