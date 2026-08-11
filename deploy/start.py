#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 一键启动脚本（跨平台统一入口）
============================================
从 config/framework.yaml（port_settings / server）读取端口配置，
从 .env 读取 OLLAMA_BASE_URL / OLLAMA_URL 等环境变量，按 enabled 状态
启动各服务，并将 PID 记录到 deploy/.pids.json 供 deploy/stop.py 使用。

用法：
  python deploy/start.py             # 启动全部启用的服务并打开浏览器
  python deploy/start.py --no-open   # 不自动打开浏览器
  python deploy/start.py --dry-run   # 仅打印将启动的服务列表，不实际启动

说明：
  本脚本不硬编码任何真实 IP / 密码；Ollama 地址优先取 .env 中的
  OLLAMA_URL / OLLAMA_BASE_URL，缺省回退 http://localhost:11434。
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# Windows 控制台中文输出兼容（chcp 65001 之外的兜底）
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DEPLOY_DIR = Path(__file__).resolve().parent
ROOT = DEPLOY_DIR.parent
FRAMEWORK_YAML = ROOT / "config" / "framework.yaml"
ENV_FILE = ROOT / ".env"
PIDS_FILE = DEPLOY_DIR / ".pids.json"

try:
    import yaml
except ImportError:
    yaml = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# 兜底默认端口：仅在配置文件缺失对应字段时使用，正常端口一律来自 framework.yaml
DEFAULT_PORTS = {
    "goai_web": 5000,
    "teacher_portal": 5001,
    "student_portal": 5010,
    "analytics_dashboard": 18090,
    "terminal": 18080,
    "api": 18081,
    "models": 18082,
}


def load_env():
    """加载 .env 到进程环境（不覆盖已有环境变量）。"""
    if not ENV_FILE.exists():
        return
    if load_dotenv is not None:
        load_dotenv(ENV_FILE, override=False)
        return
    # 无 python-dotenv 时手动解析
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


def load_config():
    """读取 config/framework.yaml，返回 dict。"""
    if yaml is None:
        print("  ✗ 缺少 PyYAML，无法读取 config/framework.yaml")
        print("    请先执行: pip install pyyaml 或 pip install -r requirements.txt")
        sys.exit(1)
    if not FRAMEWORK_YAML.exists():
        print("  ✗ 未找到配置文件: {}".format(FRAMEWORK_YAML))
        print("    请先执行: python deploy/setup.py 生成配置")
        sys.exit(1)
    with open(FRAMEWORK_YAML, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def port_in_use(port):
    """探测端口是否被占用（能连上 127.0.0.1 即视为占用）。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except OSError:
        return False


def get_ollama_urls():
    """取 Ollama 地址（.env 已加载进环境），缺省回退 localhost。"""
    base = (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434").strip().rstrip("/")
    url = (os.environ.get("OLLAMA_URL") or "").strip().rstrip("/") or base
    return {"OLLAMA_URL": url, "OLLAMA_BASE_URL": base}


def _port_settings(config):
    ps = config.get("port_settings")
    return ps if isinstance(ps, dict) else {}


def _enabled_port(settings, key):
    """读取某服务的 enabled + port（缺省 enabled=True，port 用兜底默认值）。"""
    item = settings.get(key)
    item = item if isinstance(item, dict) else {}
    enabled = item.get("enabled", True)
    try:
        port = int(item.get("port") or DEFAULT_PORTS[key])
    except (TypeError, ValueError):
        port = DEFAULT_PORTS[key]
    return bool(enabled), port


def build_services(config):
    """按 port_settings 的 enabled 状态组装服务列表。"""
    settings = _port_settings(config)
    services = []

    # --- GOAI 学习 Web（goai_web.py 支持 GOAI_PORT 环境变量覆盖端口）---
    enabled, port = _enabled_port(settings, "goai_web")
    if enabled:
        services.append({
            "key": "goai_web",
            "name": "GOAI 学习 Web",
            "cmd": [sys.executable, "goai_web.py"],
            "ports": [port],
            "env": {"GOAI_PORT": str(port)},
            "url": "http://localhost:{}".format(port),
            "desc": "AI 教官问答 + 费曼教学法",
        })

    # --- 教师门户（teacher_portal.py 支持 TEACHER_PORT 环境变量覆盖端口）---
    enabled, port = _enabled_port(settings, "teacher_portal")
    if enabled:
        services.append({
            "key": "teacher_portal",
            "name": "教师门户",
            "cmd": [sys.executable, "teacher_portal.py"],
            "ports": [port],
            "env": {"TEACHER_PORT": str(port)},
            "url": "http://localhost:{}".format(port),
            "desc": "班级 / 任务 / 学情管理",
        })

    # --- 学生端学习平台（student_portal.py 支持 STUDENT_PORT 环境变量覆盖端口）---
    enabled, port = _enabled_port(settings, "student_portal")
    if enabled:
        services.append({
            "key": "student_portal",
            "name": "学生端学习平台",
            "cmd": [sys.executable, "student_portal.py"],
            "ports": [port],
            "env": {"STUDENT_PORT": str(port)},
            "url": "http://localhost:{}".format(port),
            "desc": "费曼学习 + 真实后端 + 对话持久化",
        })

    # --- 学习分析仪表盘（analytics_dashboard.py 支持 ANALYTICS_PORT 环境变量覆盖端口）---
    enabled, port = _enabled_port(settings, "analytics_dashboard")
    if enabled:
        services.append({
            "key": "analytics_dashboard",
            "name": "学习分析仪表盘",
            "cmd": [sys.executable, "analytics_dashboard.py"],
            "ports": [port],
            "env": {"ANALYTICS_PORT": str(port)},
            "url": "http://localhost:{}".format(port),
            "desc": "掌握度趋势 / 学科对比 / 薄弱点",
        })

    # --- 框架三端口（框架自己从 framework.yaml 读取端口，--multi-port 一次启动）---
    triples = []
    for key, label in (("terminal", "框架终端"), ("api", "REST API"), ("models", "模型管理")):
        enabled, port = _enabled_port(settings, key)
        if enabled:
            triples.append((label, port))
    if triples:
        ports = [p for _, p in triples]
        services.append({
            "key": "framework",
            "name": "Framework API",
            "cmd": [sys.executable, "-m", "framework.api.server", "--multi-port"],
            "ports": ports,
            "env": {},
            "url": "http://localhost:{}".format(ports[0]),
            "desc": "三端口: " + " / ".join("{}:{}".format(label, p) for label, p in triples),
        })

    return services


def make_child_env(service_env, ollama):
    """子进程环境 = 当前环境 + Ollama 地址 + 服务特定变量。"""
    env = os.environ.copy()
    env.update(ollama)
    env.update(service_env or {})
    return env


def start_service(svc, ollama, wait_seconds=20):
    """启动单个服务；端口被占用则跳过。返回 PID，未启动返回 None。"""
    port_text = "/".join(str(p) for p in svc["ports"])
    busy = [p for p in svc["ports"] if port_in_use(p)]
    if busy:
        print("  ⚠ {} 端口被占用（{}），跳过启动；如为残留进程请先运行 stop_services.bat".format(
            svc["name"], ", ".join(str(p) for p in busy)))
        return None

    print("  ▶ 启动 {} (端口 {}): {}".format(svc["name"], port_text, " ".join(svc["cmd"])))
    kwargs = {"cwd": str(ROOT), "env": make_child_env(svc.get("env"), ollama)}
    if os.name == "nt":
        # Windows 下每个服务独立控制台窗口，便于查看日志
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    proc = subprocess.Popen(svc["cmd"], **kwargs)
    pid = proc.pid

    # 等待端口进入监听状态
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if all(port_in_use(p) for p in svc["ports"]):
            break
        time.sleep(0.5)
    if all(port_in_use(p) for p in svc["ports"]):
        print("      ✓ {} 已就绪 (PID {})".format(svc["name"], pid))
    else:
        print("      ⚠ {} 进程已启动 (PID {})，端口暂未监听，请查看服务窗口日志".format(svc["name"], pid))
    return pid


def main():
    parser = argparse.ArgumentParser(
        description="LumiLearn 一键启动（端口与 Ollama 地址取自 config/framework.yaml 与 .env）")
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--dry-run", action="store_true", help="仅打印将启动的服务列表，不实际启动")
    args = parser.parse_args()

    print("=" * 60)
    print("  🚀 LumiLearn 服务启动中（配置驱动）")
    print("=" * 60)
    print()

    load_env()
    config = load_config()
    ollama = get_ollama_urls()
    print("  🔗 Ollama 地址: {}（OLLAMA_BASE_URL）".format(ollama["OLLAMA_BASE_URL"]))
    print("  📄 配置文件: {}".format(FRAMEWORK_YAML))
    print()

    services = build_services(config)
    if not services:
        print("  ⚠ config/framework.yaml 的 port_settings 中所有服务均未启用，无服务可启动")
        return 0

    if args.dry_run:
        print("  📋 将启动以下服务（--dry-run，未实际启动）：")
        print("  ─────────────────────────────────────────────")
        for svc in services:
            print("  • {} (端口 {}): {}".format(
                svc["name"], "/".join(str(p) for p in svc["ports"]), svc["desc"]))
        return 0

    pids = {}
    for svc in services:
        pid = start_service(svc, ollama)
        if pid:
            pids[svc["key"]] = pid

    if pids:
        PIDS_FILE.write_text(json.dumps(pids, ensure_ascii=False, indent=2), encoding="utf-8")
        print()
        print("  💾 PID 记录已写入: {}".format(PIDS_FILE))
    else:
        print()
        print("  ⚠ 没有服务成功启动（端口可能被占用，或依赖缺失）")

    print()
    print("  📌 服务访问地址")
    print("  ─────────────────────────────────────────────")
    for svc in services:
        if svc["key"] in pids:
            print("  • {}: {}".format(svc["name"], svc["url"]))
    print("  ─────────────────────────────────────────────")
    print()
    print("  ⏹  停止服务请运行: stop_services.bat 或 python deploy/stop.py")
    print()

    if not args.no_open and pids:
        first_url = next((s["url"] for s in services if s["key"] in pids), None)
        if first_url:
            try:
                webbrowser.open(first_url)
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
