#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 远程部署脚本（天虹主机）
============================================
通过 SSH/SFTP 将本地仓库上传到远端服务器并完成部署：
  1. SFTP 递归上传（自动排除敏感/缓存/虚拟环境/大文件等）
  2. 远端执行依赖安装与 deploy/setup.py --quick 配置
  3. 可选启动服务（deploy/start.py --no-open）并做 HTTP 健康检查

隐私约定（重要）:
  - 本脚本不硬编码、不打印任何真实 IP / 主机名 / 密码 / API Key；
    凭据一律从环境变量读取，报告中主机地址以 <host> 占位显示。
  - 仓库中的 .env 等敏感文件会被自动排除，不会上传到远端。

用法示例:
  PowerShell:
    $env:REMOTE_HOST='<主机IP>'; $env:REMOTE_USER='<用户名>'; $env:REMOTE_PASSWORD='<密码>'; python scripts\\deploy_remote.py [--skip-deps] [--no-start] [--remote-dir ~/lumilearn]
  Linux:
    REMOTE_HOST=... REMOTE_USER=... REMOTE_PASSWORD=... python3 scripts/deploy_remote.py

环境变量:
    REMOTE_HOST      目标主机 IP（必填）
    REMOTE_USER      SSH 用户名（必填）
    REMOTE_PASSWORD  SSH 密码（必填）
"""

import argparse
import os
import posixpath
import shlex
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("[错误] 缺少 paramiko，请先执行 pip install paramiko")
    sys.exit(1)

# Windows 控制台中文输出兼容（chcp 65001 之外的兜底）
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REMOTE_DIR = "~/lumilearn"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 单文件 >5MB 跳过

# 上传排除清单：目录名
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "node_modules",
    ".trae",
    ".github",
}
# 上传排除清单：文件名（精确）
EXCLUDE_FILES = {".env", ".DS_Store"}
# 上传排除清单：文件名后缀
EXCLUDE_FILES_SUFFIX = (".pyc", ".pids.json")

# 健康检查端点（远端本机回环地址，不涉及真实公网信息）
HEALTH_ENDPOINTS = [
    ("REST API 健康检查 (/health)", "http://127.0.0.1:18081/health"),
    ("框架终端 + Admin 入口", "http://127.0.0.1:18080/"),
    ("模型管理", "http://127.0.0.1:18082/"),
    ("Admin 面板", "http://127.0.0.1:18080/admin"),
]


def read_credentials():
    """从环境变量读取 SSH 凭据；任一缺失则打印设置示例并退出。"""
    host = os.environ.get("REMOTE_HOST", "").strip()
    user = os.environ.get("REMOTE_USER", "").strip()
    password = os.environ.get("REMOTE_PASSWORD", "")
    missing = [k for k, v in (
        ("REMOTE_HOST", host),
        ("REMOTE_USER", user),
        ("REMOTE_PASSWORD", password),
    ) if not v]
    if missing:
        print("[错误] 缺少 SSH 连接凭据环境变量: {}".format(", ".join(missing)))
        print("  请在运行前设置以下环境变量（示例，请替换为真实值）：")
        print("    PowerShell: $env:REMOTE_HOST='<主机IP>'; $env:REMOTE_USER='<用户名>'; $env:REMOTE_PASSWORD='<密码>'")
        print("    CMD:        set REMOTE_HOST=<主机IP> && set REMOTE_USER=<用户名> && set REMOTE_PASSWORD=<密码>")
        print("    Linux:      REMOTE_HOST=<主机IP> REMOTE_USER=<用户名> REMOTE_PASSWORD=<密码> python3 scripts/deploy_remote.py")
        sys.exit(1)
    return host, user, password


def connect_ssh(host, user, password):
    """建立 SSH 连接；失败打印错误并以非 0 退出码结束。"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("  ⏳ 正在连接目标主机 <host>（隐私约定：不显示真实地址）...")
    try:
        client.connect(host, username=user, password=password, timeout=15)
    except Exception as exc:
        print("[错误] SSH 连接失败，请检查 REMOTE_HOST / REMOTE_USER / REMOTE_PASSWORD 是否正确: {}".format(exc))
        client.close()
        sys.exit(1)
    print("  ✓ SSH 连接成功")
    return client


def sftp_mkdir_p(sftp, remote_dir):
    """逐级创建远端目录；已存在则忽略异常（支持绝对路径与相对路径）。"""
    parts = remote_dir.replace("\\", "/").split("/")
    is_abs = remote_dir.startswith("/")
    current = ""
    for part in parts:
        if part in ("", "."):
            continue
        if is_abs and not current.startswith("/"):
            current = "/" + part
        elif current:
            current = current + "/" + part
        else:
            current = part
        try:
            sftp.stat(current)
        except IOError:
            try:
                sftp.mkdir(current)
            except IOError:
                pass  # 目录已存在或并发创建，忽略


def upload_repo(sftp, abs_remote_dir):
    """递归上传仓库全部文件到远端目录；返回 (成功上传数, 跳过大文件数)。"""
    uploaded, skipped_large = 0, 0
    sftp_mkdir_p(sftp, abs_remote_dir)
    for root, dirs, files in os.walk(str(REPO_ROOT)):
        # 剪枝排除目录，避免无谓遍历
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        rel = os.path.relpath(root, str(REPO_ROOT))
        remote_dir = abs_remote_dir if rel == "." else posixpath.join(
            abs_remote_dir, rel.replace(os.sep, "/"))
        sftp_mkdir_p(sftp, remote_dir)
        for name in files:
            if name in EXCLUDE_FILES or name.endswith(EXCLUDE_FILES_SUFFIX):
                continue
            local_path = os.path.join(root, name)
            try:
                size = os.path.getsize(local_path)
            except OSError:
                continue
            if size > MAX_FILE_SIZE:
                skipped_large += 1
                continue
            remote_path = posixpath.join(remote_dir, name)
            try:
                sftp.put(local_path, remote_path)
                uploaded += 1
            except Exception as exc:
                print("  ⚠ 上传失败 {} → {}: {}".format(local_path, remote_path, exc))
    return uploaded, skipped_large


def run_remote(client, command, label, timeout=600):
    """执行远端命令，逐条打印 stdout/stderr；退出码非 0 打印警告但继续。"""
    print("\n  ▶ [{}] {}".format(label, command))
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()
        if out.strip():
            print(out.rstrip())
        if err.strip():
            print("[stderr] {}".format(err.rstrip()))
        if exit_code != 0:
            print("  ⚠ 命令执行退出码非 0: {}".format(exit_code))
        return exit_code
    except Exception as exc:
        print("  ⚠ 命令执行异常: {}".format(exc))
        return -1


def deploy_remote(client, args, remote_dir):
    """在远端依次执行：cd → 依赖安装 → setup 配置 → 启动 → 健康检查。
    remote_dir 为已解析的绝对路径（与 SFTP 上传目录一致）。"""
    # 每次 exec_command 均为新 shell，后续命令统一前置 cd（绝对路径，无 ~ 歧义）
    base = "cd {} && ".format(shlex.quote(remote_dir))

    # 1) 切换目录
    run_remote(client, "cd {}".format(shlex.quote(remote_dir)), "切换目录", timeout=30)

    # 2) 依赖安装（--skip-deps 时跳过）
    if not args.skip_deps:
        run_remote(client, base + "python3 -m pip install -r requirements.txt", "安装依赖")

    # 3) 配置（--quick 自动化；--skip-deps 时同时传递）
    setup_cmd = "python3 deploy/setup.py --quick"
    if args.skip_deps:
        setup_cmd += " --skip-deps"
    run_remote(client, base + setup_cmd, "运行 deploy/setup.py --quick 配置")

    # 4) 启动服务（--no-start 时跳过）
    if not args.no_start:
        run_remote(client, base + "python3 deploy/start.py --no-open", "启动服务", timeout=120)

    # 5) 健康检查：curl 各端点，收集 HTTP 状态码
    health_results = []
    for name, url in HEALTH_ENDPOINTS:
        cmd = '{} curl -s -o /dev/null -w "%{{http_code}}" --max-time 5 {}'.format(base, url)
        print("\n  ▶ [健康检查] {} → {}".format(name, url))
        try:
            stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
            out = stdout.read().decode("utf-8", errors="replace").strip()
            err = stderr.read().decode("utf-8", errors="replace").strip()
            exit_code = stdout.channel.recv_exit_status()
            if err.strip():
                print("[stderr] {}".format(err.strip()))
            code = out if (exit_code == 0 and out) else "000（连接失败）"
        except Exception as exc:
            code = "异常（{}）".format(exc)
        print("    → HTTP {}".format(code))
        health_results.append((name, code))
    return health_results


def main():
    parser = argparse.ArgumentParser(
        description="LumiLearn 远程部署脚本（天虹主机：SFTP 上传 + 远端部署 + 健康检查）")
    parser.add_argument("--skip-deps", action="store_true", help="跳过依赖安装")
    parser.add_argument("--no-start", action="store_true", help="只上传+配置，不启动服务")
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR,
                        help="远端部署目录（默认 %(default)s）")
    args = parser.parse_args()

    print("=" * 60)
    print("  🚀 LumiLearn 远程部署（天虹主机）")
    print("  （隐私约定：凭据仅从环境变量读取，报告不显示真实地址）")
    print("=" * 60)

    # 凭据缺失或 SSH 连接失败均以非 0 退出
    host, user, password = read_credentials()
    client = connect_ssh(host, user, password)

    # ---- SFTP 上传 ----
    try:
        sftp = client.open_sftp()
    except Exception as exc:
        print("[错误] SFTP 通道打开失败: {}".format(exc))
        client.close()
        sys.exit(1)

    try:
        # 解析远端目录为绝对路径，供 SFTP 上传与 shell 命令共用，避免 ~ 解析不一致：
        # OpenSSH sftp-server 的 realpath 不展开 "~"（会被当作字面目录名），
        # 因此先取 SFTP 默认工作目录（即用户家目录）作为基准再拼接。
        try:
            home_dir = sftp.normalize(".") or ""
        except IOError:
            home_dir = ""
        if not home_dir or home_dir == ".":
            try:
                _in, _out, _err = client.exec_command("echo $HOME", timeout=10)
                home_dir = _out.read().decode("utf-8", errors="replace").strip()
            except Exception:
                home_dir = ""
        if home_dir and home_dir != "." and args.remote_dir.startswith("~"):
            abs_remote_dir = posixpath.join(home_dir, args.remote_dir.lstrip("~/"))
        else:
            abs_remote_dir = sftp.normalize(args.remote_dir) or args.remote_dir
        print("\n── 开始上传（远端目录: {}）──".format(abs_remote_dir))
        uploaded, skipped_large = upload_repo(sftp, abs_remote_dir)
        print("  ✓ 上传完成")
    except Exception as exc:
        print("[错误] 上传过程异常: {}".format(exc))
        sftp.close()
        client.close()
        sys.exit(1)
    finally:
        sftp.close()

    # ---- 远端执行与健康检查（使用与上传一致的绝对路径） ----
    health_results = deploy_remote(client, args, abs_remote_dir)

    # ---- 脱敏报告 ----
    print("\n" + "=" * 60)
    print("  📋 部署报告")
    print("  ── 目标主机: <host>（隐私约定，不显示真实地址）")
    print("  ── 远端目录: {}".format(args.remote_dir))
    print("  ── 上传文件数: {}".format(uploaded))
    print("  ── 跳过大文件数（>5MB）: {}".format(skipped_large))
    print("  ── 健康检查:")
    for name, code in health_results:
        print("      {} → HTTP {}".format(name, code))
    print("  " + "=" * 56)
    if args.no_start:
        print("  ⏭ 已跳过启动（--no-start），请登录远端手动执行: python3 deploy/start.py --no-open")
    print()

    client.close()


if __name__ == "__main__":
    main()
