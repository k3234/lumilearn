#!/usr/bin/env bash
# LumiLearn 部署配置引导（Linux/macOS）
set -e

# 切换到仓库根目录（脚本所在目录的上一级）
cd "$(dirname "$0")/.."

# 检查 python3
if ! command -v python3 >/dev/null 2>&1; then
    echo "[错误] 未检测到 python3，请先安装 Python 3.9+"
    exit 1
fi

exec python3 deploy/setup.py "$@"
