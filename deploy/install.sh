#!/usr/bin/env bash
set -e
# ============================================================
# LumiLearn 零文件一键部署（Linux / macOS，管道安全）
#
# 用法（不下载文件，直接执行远程脚本）：
#   curl -fsSL https://raw.githubusercontent.com/k3234/lumilearn/master/deploy/install.sh | bash
#   带参数：
#   curl -fsSL https://raw.githubusercontent.com/k3234/lumilearn/master/deploy/install.sh | bash -s -- --quick
#
# 支持参数（--dir / --branch 支持 = 与空格两种写法）：
#   --quick        全默认值，无人值守
#   --skip-deps    跳过依赖安装
#   --no-start     只克隆+配置，不启动服务
#   --dir=<路径>   克隆到指定目录（默认 $(pwd)/lumilearn）
#   --branch=<名>  指定分支（默认 master）
#
# 环境变量可覆盖（方便 fork 用户）：
#   LUMILEARN_REPO_URL   仓库地址（默认 https://github.com/k3234/lumilearn.git）
#   LUMILEARN_BRANCH     分支（默认 master）
#
# 隐私说明：本脚本仅访问公开仓库地址，不含任何真实 IP / 密码 / API Key。
# ============================================================

REPO_URL="${LUMILEARN_REPO_URL:-https://github.com/k3234/lumilearn.git}"
BRANCH="${LUMILEARN_BRANCH:-master}"
DEST=""
SKIP_DEPS=""
QUICK=""
NO_START=0

while [ $# -gt 0 ]; do
    case "$1" in
        --quick) QUICK="--quick" ;;
        --skip-deps) SKIP_DEPS="--skip-deps" ;;
        --no-start) NO_START=1 ;;
        --dir=*) DEST="${1#*=}" ;;
        --dir) shift; DEST="$1" ;;
        --branch=*) BRANCH="${1#*=}" ;;
        --branch) shift; BRANCH="$1" ;;
    esac
    shift
done

echo "============================================================"
echo "  🚀 LumiLearn 零文件一键部署"
echo "  仓库: $REPO_URL (分支: $BRANCH)"
echo "============================================================"

# [1/5] 检测 git
if ! command -v git >/dev/null 2>&1; then
    echo "[错误] 未检测到 git，请先安装 Git："
    echo "  Debian/Ubuntu: sudo apt install git"
    echo "  CentOS/Fedora: sudo dnf install git"
    echo "  macOS:         brew install git"
    exit 1
fi

# [2/5] 定位 / 克隆仓库
# 管道安全：curl | bash 执行时 $0=bash，无法用 $0 定位脚本；
# 「已在仓库内」仅靠 cwd 特征（deploy/setup.py + .git）判断。
if [ -z "$DEST" ]; then
    if [ -f "deploy/setup.py" ] && [ -d ".git" ]; then
        DEST="$(pwd)"                       # 已在仓库内：复用当前目录
    else
        DEST="$(pwd)/lumilearn"             # 克隆到当前目录
    fi
fi
mkdir -p "$(dirname "$DEST")" 2>/dev/null || true

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

# [3/5] 检测 python（python3 优先，兼容仅安装 python 的环境）
PY=""
for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" --version >/dev/null 2>&1; then
        PY="$c"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "[错误] 未检测到可用的 python3 / python，请先安装 Python 3.9+："
    echo "  Debian/Ubuntu: sudo apt install python3 python3-pip"
    echo "  CentOS/Fedora: sudo dnf install python3 python3-pip"
    echo "  macOS:         brew install python"
    exit 1
fi
echo "  ✓ $($PY --version)"

# [4/5] 部署配置（依赖安装 / 端口 / 模型）
echo ""
echo "[4/5] 运行部署配置引导（依赖 / 端口 / 模型）..."
if [ -t 0 ]; then
    # 交互模式：stdin 为终端，正常提问
    "$PY" deploy/setup.py $SKIP_DEPS $QUICK
else
    # 管道模式（curl | bash）：stdin 非终端 → 强制 --quick 并隔离 stdin，
    # 防止子进程抢读管道中脚本残留字节（setup.py 亦内置非交互自动 quick 兜底）。
    echo "  [提示] 检测到管道执行（非终端），自动使用 --quick 全部默认值"
    "$PY" deploy/setup.py $SKIP_DEPS --quick < /dev/null
fi

# [5/5] 启动服务
echo ""
if [ "$NO_START" = "0" ]; then
    echo "[5/5] 启动全部服务..."
    "$PY" deploy/start.py
else
    echo "[5/5] 已跳过服务启动（--no-start），手动启动命令："
    echo "  $PY deploy/start.py"
fi

echo ""
echo "============================================================"
echo "  ✅ LumiLearn 部署完成"
echo "  终端页面:   http://localhost:18080"
echo "  管理面板:   http://localhost:18080/admin"
echo "  REST API:   http://localhost:18081"
echo "  模型管理:   http://localhost:18082"
echo "============================================================"
