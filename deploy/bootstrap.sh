#!/usr/bin/env bash
# ============================================================
# LumiLearn 一键部署引导（Linux / macOS）
# 从任意目录运行，自动完成：克隆/更新仓库 → 配置 → 启动服务
#
# 完整流程：
#   1. 检测 git / python
#   2. 克隆仓库（已存在则 git pull 更新）
#   3. 运行 deploy/setup.py（依赖安装 / 端口 / 模型配置）
#   4. 运行 deploy/start.py 启动全部启用服务
#
# 用法：
#   bash bootstrap.sh                # 完整一键部署（克隆→配置→启动）
#   bash bootstrap.sh --quick        # 全默认值，无人值守
#   bash bootstrap.sh --skip-deps    # 跳过依赖安装
#   bash bootstrap.sh --no-start     # 只克隆+配置，不启动服务
#   bash bootstrap.sh --dir /path    # 克隆到指定目录
#   bash bootstrap.sh --branch dev   # 指定分支（默认 master）
#
# 环境变量可覆盖（方便 fork 用户）：
#   LUMILEARN_REPO_URL   仓库地址（默认 https://github.com/k3234/lumilearn.git）
#   LUMILEARN_BRANCH     分支（默认 master）
#
# 隐私说明：本脚本仅使用公开仓库地址，不含任何真实 IP / 密码 / API Key。
# ============================================================
set -e

REPO_URL="${LUMILEARN_REPO_URL:-https://github.com/k3234/lumilearn.git}"
BRANCH="${LUMILEARN_BRANCH:-master}"
DEST=""
SKIP_DEPS=""
QUICK=""
NO_START=0

for arg in "$@"; do
    case "$arg" in
        --skip-deps) SKIP_DEPS="--skip-deps" ;;
        --quick) QUICK="--quick" ;;
        --no-start) NO_START=1 ;;
        --dir=*) DEST="${arg#*=}" ;;
        --branch=*) BRANCH="${arg#*=}" ;;
    esac
done

echo "============================================================"
echo "  🚀 LumiLearn 一键部署引导"
echo "  仓库: $REPO_URL (分支: $BRANCH)"
echo "============================================================"

# [1/5] 检测 git
if ! command -v git >/dev/null 2>&1; then
    echo "[错误] 未检测到 git，请先安装 Git："
    echo "  Debian/Ubuntu: sudo apt install git"
    echo "  macOS:         brew install git"
    exit 1
fi

# [2/5] 确定目标目录
SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
if [ -z "$DEST" ]; then
    if [ -f "deploy/setup.py" ] && [ -d ".git" ]; then
        DEST="$(pwd)"                                  # 已在仓库内
    elif [ -f "$SCRIPT_DIR/../deploy/setup.py" ] && [ -d "$SCRIPT_DIR/../.git" ]; then
        DEST="$(cd "$SCRIPT_DIR/.." && pwd)"           # 通过 deploy/bootstrap.sh 调用
    else
        DEST="$(pwd)/lumilearn"                        # 克隆到当前目录
    fi
fi
mkdir -p "$(dirname "$DEST")" 2>/dev/null || true

# 克隆或更新仓库
if [ -d "$DEST/.git" ]; then
    echo "[2/5] 检测到已有仓库: $DEST，正在更新..."
    cd "$DEST"
    git fetch origin 2>/dev/null || true
    if git pull --ff-only origin "$BRANCH" 2>/dev/null; then
        echo "  ✓ 仓库已更新"
    else
        echo "  ⚠ 快进更新失败（可能本地有未提交改动），继续使用现有代码"
    fi
else
    echo "[2/5] 正在克隆仓库..."
    git clone -b "$BRANCH" --depth 1 "$REPO_URL" "$DEST"
    cd "$DEST"
    echo "  ✓ 仓库克隆完成"
fi
echo "  目录: $DEST"
echo ""

# [3/5] 检测 python
if ! command -v python3 >/dev/null 2>&1; then
    echo "[错误] 未检测到 python3，请先安装 Python 3.9+"
    exit 1
fi
echo "  ✓ $(python3 --version)"

# [4/5] 部署配置（依赖安装 / 端口 / 模型）
echo ""
echo "[4/5] 运行部署配置引导（依赖 / 端口 / 模型）..."
python3 deploy/setup.py $SKIP_DEPS $QUICK

# [5/5] 启动服务
echo ""
if [ "$NO_START" = "0" ]; then
    echo "[5/5] 启动全部服务..."
    python3 deploy/start.py
else
    echo "[5/5] 已跳过服务启动（--no-start），手动启动命令："
    echo "  python3 deploy/start.py"
fi

echo ""
echo "============================================================"
echo "  ✅ LumiLearn 部署完成"
echo "  终端页面:   http://localhost:18080"
echo "  管理面板:   http://localhost:18080/admin"
echo "  REST API:   http://localhost:18081"
echo "  模型管理:   http://localhost:18082"
echo "============================================================"
