#!/usr/bin/env python3
"""远程服务器服务器 SSH 连接配置 — 敏感信息从环境变量读取，不硬编码在仓库中

环境变量:
    REMOTE_HOST      服务器 IP（必填）
    REMOTE_USER      SSH 用户名（必填）
    REMOTE_PASSWORD  SSH 密码（必填，未设置时给出提示并退出）

用法（任选）:
    from _remote_config import get_config
    cfg = get_config()
    ssh.connect(cfg["host"], username=cfg["user"], password=cfg["password"], timeout=15)
"""
import os
import sys


def get_config(host: str = "", user: str = "") -> dict:
    """返回 SSH 连接配置；host/user 可显式覆盖默认值"""
    cfg_host = host or os.environ.get("REMOTE_HOST", "")
    cfg_user = user or os.environ.get("REMOTE_USER", "")
    password = os.environ.get("REMOTE_PASSWORD", "")

    if not (cfg_host and cfg_user and password):
        print(
            "错误: 缺少 SSH 连接配置环境变量。\n"
            "  PowerShell: $env:REMOTE_HOST='服务器IP'; $env:REMOTE_USER='用户名'; $env:REMOTE_PASSWORD='密码'\n"
            "  CMD:        set REMOTE_HOST=服务器IP\n"
            "  Linux:      export REMOTE_HOST='服务器IP'",
            file=sys.stderr,
        )
        sys.exit(1)

    return {"host": cfg_host, "user": cfg_user, "password": password}
