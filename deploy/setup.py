#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 部署配置引导脚本
========================================
交互式完成：
  1. 环境检测（Python >= 3.9、pip）
  2. 依赖安装（可选，pip install -r requirements.txt）
  3. 端口配置（config/framework.yaml 的 port_settings）
  4. 模型配置（Ollama 本地/远程 + 云端 API Key，写入 .env）

用法：
  python deploy/setup.py              # 交互式引导
  python deploy/setup.py --skip-deps  # 跳过依赖安装
  python deploy/setup.py --quick      # 全部使用默认值（自动化，无交互）

隐私说明：
  本脚本不硬编码、不保存任何真实 IP / 密码；Ollama 地址默认本机 localhost。
  填写的内容仅写入本仓库的 .env（已被 .gitignore 忽略）与 config/framework.yaml。
"""

import argparse
import os
import shutil
import subprocess
import sys

try:
    import yaml
except ImportError:
    yaml = None

try:
    import requests
except ImportError:
    requests = None

try:
    from dotenv import set_key as _dotenv_set_key
except ImportError:
    _dotenv_set_key = None

# Windows 控制台中文输出兼容（chcp 65001 之外的兜底）
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMEWORK_YAML = os.path.join(ROOT, "config", "framework.yaml")
ENV_FILE = os.path.join(ROOT, ".env")
ENV_EXAMPLE = os.path.join(ROOT, ".env.example")
REQUIREMENTS = os.path.join(ROOT, "requirements.txt")

MIN_PYTHON = (3, 9)

# 端口服务清单：(port_settings 键, 显示名, 未配置时的默认端口)
PORT_SERVICES = [
    ("terminal", "框架终端 (Terminal)", 18080),
    ("api", "REST API", 18081),
    ("models", "模型管理 (Models)", 18082),
    ("goai_web", "GOAI 学习 Web", 5000),
    ("teacher_portal", "教师门户 (Teacher Portal)", 5001),
]

# 云端提供者清单：(环境变量名, 显示名)
CLOUD_PROVIDERS = [
    ("DOUBAO_API_KEY", "豆包 (Doubao)"),
    ("ZHIPU_API_KEY", "智谱 (Zhipu)"),
    ("MOONSHOT_API_KEY", "Kimi (Moonshot)"),
    ("MINIMAX_API_KEY", "MiniMax"),
]

OLLAMA_BASE_URL_DEFAULT = "http://localhost:11434"
OLLAMA_MODEL_DEFAULT = "lumilearn-v2:latest"

# 本地 OpenAI 兼容容器（除 Ollama 外，支持 vLLM / LM Studio / LocalAI / llama.cpp 等）
# 它们均提供 /v1/models 与 /v1/chat/completions 的 OpenAI 兼容接口
LOCAL_CONTAINER_EXAMPLES = [
    ("vLLM", "http://localhost:8000/v1"),
    ("LM Studio", "http://localhost:1234/v1"),
    ("LocalAI", "http://localhost:8080/v1"),
    ("llama.cpp server", "http://localhost:8080/v1"),
]
PROVIDERS_YAML = os.path.join(ROOT, "config", "providers.yaml")


# ============================================================
# 交互工具
# ============================================================
def ask(question, default=None, quick=False):
    """交互提问；--quick 模式下直接返回 default。留空输入返回 default（若给定）。"""
    if quick:
        return default
    if default not in (None, ""):
        prompt = "{}（默认: {}）: ".format(question, default)
    else:
        prompt = "{}: ".format(question)
    try:
        value = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        value = ""
    if value == "" and default not in (None, ""):
        return default
    return value


def ask_yes_no(question, default, quick):
    """是否类提问，返回 bool。"""
    ans = ask(question, default="y" if default else "n", quick=quick)
    return str(ans).strip().lower() in ("y", "yes", "是", "1", "true")


def ask_int(question, default, quick):
    """端口号提问（1-65535 整数校验），返回 int。"""
    while True:
        value = ask(question, default=default, quick=quick)
        try:
            port = int(value)
        except (TypeError, ValueError):
            print("  ✗ 请输入 1-65535 之间的整数")
            if quick:
                return default
            continue
        if 1 <= port <= 65535:
            return port
        print("  ✗ 端口号必须在 1-65535 之间")
        if quick:
            return default


# ============================================================
# [1/4] 环境检测 + 依赖安装
# ============================================================
def check_python():
    """检测 Python 版本，返回是否满足要求。"""
    print("  ✓ Python {}".format(sys.version.split()[0]))
    if sys.version_info < MIN_PYTHON:
        print("  ✗ 需要 Python 3.9 及以上版本，当前版本过旧，请升级后重试")
        return False
    return True


def check_pip():
    """检测 pip 是否可用。"""
    try:
        code = subprocess.call(
            [sys.executable, "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return code == 0


def install_dependencies(skip_deps, quick):
    """按需安装 requirements.txt 依赖。"""
    if skip_deps:
        print("  ⏭ 已通过 --skip-deps 跳过依赖安装")
        return
    if quick:
        print("  ⏭ --quick 模式跳过依赖安装（如需安装请执行: pip install -r requirements.txt）")
        return
    if not os.path.exists(REQUIREMENTS):
        print("  ⚠ 未找到 requirements.txt，跳过依赖安装")
        return
    if not ask_yes_no("  是否安装依赖（pip install -r requirements.txt）?", True, quick):
        print("  ⏭ 跳过依赖安装")
        return
    print("  ⏳ 正在安装依赖，请稍候...")
    code = subprocess.call([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS])
    if code == 0:
        print("  ✓ 依赖安装完成")
    else:
        print("  ⚠ 依赖安装失败（退出码 {}），请稍后手动执行: pip install -r requirements.txt".format(code))


# ============================================================
# [2/4] 端口配置（config/framework.yaml）
# ============================================================
def load_framework_yaml():
    if not os.path.exists(FRAMEWORK_YAML):
        print("  ✗ 未找到 {}".format(FRAMEWORK_YAML))
        sys.exit(1)
    with open(FRAMEWORK_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def configure_ports(quick):
    """逐服务引导启用状态与端口号，写回 port_settings（保留其他配置字段）。"""
    print("\n[2/4] 端口配置")
    print("  （写入 config/framework.yaml 的 port_settings，每个服务可独立启用/修改）")
    data = load_framework_yaml()
    settings = data.setdefault("port_settings", {})
    if not isinstance(settings, dict):
        settings = {}
        data["port_settings"] = settings

    for key, label, fallback_port in PORT_SERVICES:
        cur = settings.get(key)
        if not isinstance(cur, dict):
            cur = {}
        cur_enabled = bool(cur.get("enabled", True))
        try:
            cur_port = int(cur.get("port") or fallback_port)
        except (TypeError, ValueError):
            cur_port = fallback_port
        enabled = ask_yes_no("  是否启用「{}」服务?".format(label), cur_enabled, quick)
        port = ask_int("  请输入「{}」端口号".format(label), cur_port, quick) if enabled else cur_port
        settings[key] = {"enabled": enabled, "port": port}
        print("     → {}: enabled={}, port={}".format(label, enabled, port))

    with open(FRAMEWORK_YAML, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print("  ✓ config/framework.yaml 已更新")


# ============================================================
# .env 读写
# ============================================================
def ensure_env_file():
    """确保 .env 存在：不存在时从 .env.example 复制生成。"""
    if os.path.exists(ENV_FILE):
        return
    if os.path.exists(ENV_EXAMPLE):
        shutil.copy2(ENV_EXAMPLE, ENV_FILE)
        print("  ✓ .env 不存在，已从 .env.example 复制生成")
    else:
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write("# LumiLearn 环境配置文件\n")
        print("  ✓ .env 不存在，已创建空文件")


def _set_env_key_manual(key, value):
    """手动读写 .env：仅更新/追加指定键，保留其他行与注释结构。"""
    ensure_env_file()
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(key + "="):
            lines[i] = "{}={}\n".format(key, value)
            found = True
            break
    if not found:
        lines.append("{}={}\n".format(key, value))
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)


def write_env_key(key, value):
    """写入 .env（保留已有内容）：优先用 python-dotenv，失败回退手动读写。"""
    ensure_env_file()
    if _dotenv_set_key is not None:
        try:
            _dotenv_set_key(ENV_FILE, key, value, quote_mode="never")
            return
        except TypeError:
            pass  # 旧版 python-dotenv 无 quote_mode 参数
        except Exception:
            pass  # 其他异常，回退手动读写
    _set_env_key_manual(key, value)


# ============================================================
# [3/4] 模型配置
# ============================================================
def probe_ollama(base_url, timeout=5):
    """探测 Ollama 的 /api/tags 接口，成功返回模型名列表，失败返回 None。"""
    if requests is None:
        print("  ⚠ 未安装 requests，跳过 Ollama 连通性探测")
        return None
    try:
        resp = requests.get("{}/api/tags".format(base_url), timeout=timeout)
        if resp.status_code != 200:
            print("  ⚠ Ollama 返回状态码 {}（{}），跳过模型列表".format(resp.status_code, base_url))
            return None
        data = resp.json()
        models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        return models or None
    except Exception as exc:
        print("  ⚠ 无法连接 Ollama（{}），跳过模型列表".format(exc))
        return None


def configure_ollama(quick):
    """引导 Ollama 地址与默认模型，写入 .env。"""
    print("\n[3/4] 模型配置")
    print("  ── Ollama（本地/远程，默认本机 localhost）──")
    url = ask("  Ollama 服务地址", OLLAMA_BASE_URL_DEFAULT, quick)
    url = str(url).strip().rstrip("/") or OLLAMA_BASE_URL_DEFAULT
    write_env_key("OLLAMA_BASE_URL", url)
    write_env_key("OLLAMA_URL", url)  # goai_web 使用 OLLAMA_URL 读取
    print("  ✓ OLLAMA_BASE_URL / OLLAMA_URL 已写入 .env: {}".format(url))

    models = probe_ollama(url)
    if not models:
        write_env_key("OLLAMA_MODEL", OLLAMA_MODEL_DEFAULT)
        print("  ⏭ 跳过默认模型选择（已保留默认 OLLAMA_MODEL={}，可稍后修改 .env）".format(OLLAMA_MODEL_DEFAULT))
        return

    print("  ✓ 连接成功，可用模型 {} 个：".format(len(models)))
    for i, m in enumerate(models, 1):
        print("     [{}] {}".format(i, m))

    if quick:
        model = OLLAMA_MODEL_DEFAULT if OLLAMA_MODEL_DEFAULT in models else models[0]
    else:
        model = OLLAMA_MODEL_DEFAULT
        while True:
            choice = ask(
                "  选择默认模型（输入编号或完整模型名，回车用默认 {}".format(OLLAMA_MODEL_DEFAULT),
                "",
                quick,
            )
            if choice == "":
                break
            if choice.isdigit() and 1 <= int(choice) <= len(models):
                model = models[int(choice) - 1]
                break
            if choice in models:
                model = choice
                break
            print("  ✗ 输入无效（请输入编号或列表中的模型名），请重新选择")
    write_env_key("OLLAMA_MODEL", model)
    print("  ✓ OLLAMA_MODEL 已写入 .env: {}".format(model))


def configure_cloud_providers(quick):
    """引导云端提供者（OpenAI 兼容接口）API Key，默认跳过。"""
    print("\n  ── 云端大模型 API（可选，OpenAI 兼容接口，默认跳过）──")
    for env_key, label in CLOUD_PROVIDERS:
        if quick:
            continue  # --quick 模式默认跳过云端 API
        if not ask_yes_no("  是否配置「{}」的 API Key?".format(label), False, quick):
            continue
        key = ask("  请输入 {} API Key（留空跳过）".format(label))
        if key:
            write_env_key(env_key, key.strip())
            print("  ✓ {} API Key 已写入 .env".format(label))
        else:
            print("  ⏭ 未输入，跳过 {}".format(label))


def probe_openai_compatible(base_url, timeout=5):
    """探测 OpenAI 兼容容器的 /models 接口，成功返回模型 id 列表，失败返回 None。"""
    if requests is None:
        print("  ⚠ 未安装 requests，跳过容器探测")
        return None
    url = base_url.rstrip("/") + "/models"
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            print("  ⚠ 容器返回状态码 {}（{}），跳过模型列表".format(resp.status_code, url))
            return None
        data = resp.json()
        models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
        return models or None
    except Exception as exc:
        print("  ⚠ 无法连接容器（{}），跳过模型列表".format(exc))
        return None


def _write_provider_to_yaml(key, name, base_url, api_key, models):
    """把本地 OpenAI 兼容容器注册到 config/providers.yaml（追加/覆盖指定 key）。"""
    try:
        with open(PROVIDERS_YAML, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        data = {}
    providers = data.setdefault("providers", {})
    providers[key] = {
        "name": name,
        "base_url": base_url,
        "api_key": api_key,
        "enabled": True,
        "local": True,   # 本地 OpenAI 兼容容器标记：无需 API Key 即可在模型列表/端口配置中使用
        "models": [{"id": m, "name": m} for m in models],
    }
    with open(PROVIDERS_YAML, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print("  ✓ 已注册到 config/providers.yaml: {}（{} 个模型）".format(name, len(models)))


def configure_openai_local(quick):
    """引导接入本地 OpenAI 兼容容器（vLLM / LM Studio / LocalAI / llama.cpp 等）。

    容器地址形如 http://localhost:8000/v1，脚本会调用 /models 自动发现其全部模型，
    并注册到 config/providers.yaml，之后可在 Admin 面板「端口模型配置」中选用。
    """
    print("\n  ── 其他本地模型容器（可选，OpenAI 兼容：vLLM / LM Studio / LocalAI / llama.cpp）──")
    if not ask_yes_no("  是否接入其他本地模型容器（推荐：继续使用上面的 Ollama 即可）?", False, quick):
        return
    print("  常见容器地址示例：")
    for name, url in LOCAL_CONTAINER_EXAMPLES:
        print("    {}  →  {}".format(name, url))
    base_url = ask("  容器服务地址（形如 http://localhost:8000/v1，留空跳过）")
    base_url = str(base_url).strip().rstrip("/")
    if not base_url:
        print("  ⏭ 未输入地址，跳过本地容器接入")
        return
    # 兼容用户只填主机名（无 /v1）
    if not base_url.endswith("/v1"):
        base_url = base_url + "/v1"
    models = probe_openai_compatible(base_url)
    if not models:
        print("  ⏭ 容器不可达或未返回模型，跳过（可稍后在 Admin 面板手动添加）")
        return
    print("  ✓ 连接成功，发现模型 {} 个：".format(len(models)))
    for i, m in enumerate(models, 1):
        print("     [{}] {}".format(i, m))
    default_key = "local_container"
    key = ask("  为该容器设置标识 key（默认 {}，用于 Admin 面板区分）".format(default_key), default_key, quick)
    key = str(key).strip() or default_key
    api_key = ask("  容器若需要 API Key 请填写（本地容器通常留空）", "", quick)
    _write_provider_to_yaml(key, key, base_url, str(api_key).strip(), models)
    print("  提示：可在 Admin 面板「模型管理 → 端口模型配置」中把某个端口切换到此容器模型")


# ============================================================
# 主流程
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="LumiLearn 部署配置引导")
    parser.add_argument("--skip-deps", action="store_true", help="跳过依赖安装")
    parser.add_argument("--quick", action="store_true", help="全部使用默认值，不交互（自动化场景）")
    args = parser.parse_args()

    # 管道/非交互场景根因修复（P2 收尾 spec）：
    # `curl | bash` / `irm | iex` 等管道执行时 stdin 非终端，
    # 若仍走 input() 会抢读管道中脚本残留字节（污染 .env / 打断流程），
    # 因此自动切换 --quick 全默认值，保证整个流程绝不读取 stdin。
    if not args.quick and not sys.stdin.isatty():
        print("  [提示] 检测到非交互输入（管道/重定向），自动使用 --quick 全部默认值")
        args.quick = True

    print("=" * 60)
    print("  🚀 LumiLearn 部署配置引导")
    print("  （环境检测 / 依赖安装 / 端口配置 / 模型配置）")
    print("=" * 60)

    # [1/4] 环境检测 + 依赖安装
    print("\n[1/4] 环境检测")
    if not check_python():
        sys.exit(1)
    if check_pip():
        print("  ✓ pip 可用")
        install_dependencies(args.skip_deps, args.quick)
    else:
        print("  ⚠ 未检测到 pip，跳过依赖安装")

    if yaml is None:
        print("\n  ✗ 缺少 PyYAML 库，无法读写 config/framework.yaml")
        print("    请先执行: pip install -r requirements.txt 或 pip install pyyaml")
        sys.exit(1)
    if _dotenv_set_key is None:
        print("  ⚠ 缺少 python-dotenv，将使用内置的 .env 读写逻辑")

    # [2/4] 端口配置
    configure_ports(args.quick)

    # [3/4] 模型配置
    configure_ollama(args.quick)
    configure_openai_local(args.quick)
    configure_cloud_providers(args.quick)

    # [4/4] 完成
    print("\n[4/4] 配置完成")
    print("  ✓ 端口配置已保存到 config/framework.yaml")
    print("  ✓ 模型配置已保存到 .env")
    print("\n  下一步：")
    print("    Windows: 运行 start_services.bat")
    print("    Linux:   运行 deploy/start.sh")
    print("  （详细说明见 deploy/README.md）")


if __name__ == "__main__":
    main()
