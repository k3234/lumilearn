#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 一键停止脚本（跨平台统一入口）
============================================
1. 读取 deploy/.pids.json，逐个终止对应 PID 进程；
2. 残留进程兜底：按命令行含 goai_web / teacher_portal / framework.api.server
   的 python 进程清理（优先 psutil；缺省 Windows 用 PowerShell 枚举 + taskkill，
   Linux/macOS 用 pgrep + SIGTERM）；
3. 删除 deploy/.pids.json。

用法：
  python deploy/stop.py
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Windows 控制台中文输出兼容（chcp 65001 之外的兜底）
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DEPLOY_DIR = Path(__file__).resolve().parent
PIDS_FILE = DEPLOY_DIR / ".pids.json"

try:
    import psutil
except ImportError:
    psutil = None

# 残留进程识别关键字（与进程命令行匹配）
MARKERS = ("goai_web", "teacher_portal", "framework.api.server")

# 各服务显示名
SERVICE_NAMES = {
    "goai_web": "GOAI 学习 Web",
    "teacher_portal": "教师门户",
    "framework": "Framework API",
}


def load_pids():
    """读取 PID 记录，返回 {服务key: pid}。"""
    if not PIDS_FILE.exists():
        return {}
    try:
        data = json.loads(PIDS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    result = {}
    for key, pid in data.items():
        try:
            result[key] = int(pid)
        except (TypeError, ValueError):
            continue
    return result


def kill_pid(pid):
    """按 PID 终止进程；进程已不存在返回 False，成功返回 True。"""
    if psutil is not None:
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                proc.kill()
            return True
        except psutil.NoSuchProcess:
            return False
        except Exception:
            return False

    if os.name == "nt":
        r = subprocess.run(["taskkill", "/pid", str(pid), "/f", "/t"],
                           capture_output=True, text=True)
        return r.returncode == 0

    # POSIX 兜底：SIGTERM，最多等 5 秒后 SIGKILL
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(50):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            time.sleep(0.1)
        os.kill(pid, signal.SIGKILL)
        return True
    except ProcessLookupError:
        return False
    except OSError:
        return False


def find_leftover_pids():
    """按命令行关键字查找残留 python 进程 PID 列表（跨平台）。"""
    if psutil is not None:
        pids = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = (proc.info.get("name") or "").lower()
                cmdline = " ".join(proc.info.get("cmdline") or [])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if "python" not in name:
                continue
            if any(m in cmdline for m in MARKERS):
                pids.append(int(proc.info["pid"]))
        return pids

    if os.name == "nt":
        # PowerShell 枚举 python 进程命令行（wmic 已弃用）
        script = (
            "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | "
            "Where-Object { $_.CommandLine -match 'goai_web|teacher_portal|framework\\.api\\.server' } | "
            "ForEach-Object { $_.ProcessId }"
        )
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=60)
            return [int(line) for line in out.stdout.split() if line.strip().isdigit()]
        except Exception:
            return []

    # Linux/macOS 兜底
    try:
        out = subprocess.run(["pgrep", "-f", "goai_web|teacher_portal|framework.api.server"],
                             capture_output=True, text=True, timeout=30)
        return [int(line) for line in out.stdout.split() if line.strip().isdigit()]
    except Exception:
        return []


def main():
    print("=" * 60)
    print("  ⏹  LumiLearn 服务停止中...")
    print("=" * 60)
    print()

    stopped = 0

    # [1/2] 按 PID 记录停止
    pids = load_pids()
    if pids:
        print("  [1/2] 按 PID 记录停止服务...")
        for key, pid in pids.items():
            name = SERVICE_NAMES.get(key, key)
            if kill_pid(pid):
                print("    ✓ {} 已停止 (PID {})".format(name, pid))
                stopped += 1
            else:
                print("    ⏭ {} 已不在运行 (PID {})".format(name, pid))
    else:
        print("  [1/2] 未找到 PID 记录（{}），改为按进程名清理".format(PIDS_FILE))

    # [2/2] 残留进程兜底
    print("  [2/2] 扫描残留进程...")
    leftovers = find_leftover_pids()
    if leftovers:
        for pid in leftovers:
            if kill_pid(pid):
                print("    ✓ 残留进程已清理 (PID {})".format(pid))
                stopped += 1
    else:
        print("    ✓ 未发现残留进程")

    # 删除 PID 记录
    if PIDS_FILE.exists():
        try:
            PIDS_FILE.unlink()
            print("  🗑  已删除 PID 记录: {}".format(PIDS_FILE))
        except OSError:
            pass

    print()
    if stopped:
        print("  ✅ 共停止 {} 个进程，LumiLearn 服务已停止".format(stopped))
    else:
        print("  ✅ 未发现需要停止的 LumiLearn 服务进程")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
