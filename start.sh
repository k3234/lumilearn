#!/bin/bash
# ============================================================
# LumiLearn Framework - Linux 启动脚本（远程服务器服务器）
# 启动三端口服务：终端HTML / REST API / 模型管理
#
# 用法：
#   bash start.sh             以三端口模式启动
#   bash start.sh --debug      调试模式启动
#   bash start.sh --port 8080  单端口模式启动
#
# 作者：lumilearn AI自动化专家
# 版本：1.0.0
# 日期：2026-06-02
# ============================================================

set -e

LUMILEARN_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$LUMILEARN_DIR"

echo ""
echo "============================================================"
echo "  🚀 LumiLearn Framework 启动中..."
echo "============================================================"
echo ""
echo "  📡 终端HTML:   http://localhost:18080"
echo "  🔌 REST API:   http://localhost:18081"
echo "  🤖 模型管理:   http://localhost:18082"
echo ""
echo "  💻 健康检查:   http://localhost:18080/health"
echo "  📊 API状态:    http://localhost:18080/api/status"
echo ""
echo "  本机访问:      http://localhost:18080"
echo "============================================================"
echo ""

# Ollama连接测试
echo "[检查] Ollama 服务连接..."
OLLAMA_RUNNING=false
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "  ✓ Ollama 服务运行中"
    OLLAMA_RUNNING=true
else
    echo "  ⚠ Ollama 未响应，尝试自动启动..."
    if command -v ollama &> /dev/null; then
        ollama serve &> /dev/null &
        sleep 3
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo "  ✓ Ollama 启动成功"
            OLLAMA_RUNNING=true
        else
            echo "  ⚠ Ollama 启动失败，请手动启动: ollama serve &"
        fi
    else
        echo "  ⚠ 未找到 ollama 命令，请先安装 Ollama"
    fi
fi
echo ""

# 端口冲突检测
echo "[检查] 端口占用情况..."
PORTS_TO_CHECK=(18080 18081 18082)
PORT_CONFLICT=false
CONFLICT_PORTS=()

detect_port_process() {
    local port=$1
    if command -v lsof &> /dev/null; then
        lsof -ti:$port 2>/dev/null
    elif command -v ss &> /dev/null; then
        ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K\d+'
    elif command -v netstat &> /dev/null; then
        netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $NF}' | grep -oP '\d+'
    fi
}

for PORT in "${PORTS_TO_CHECK[@]}"; do
    PID=$(detect_port_process "$PORT")
    if [ -n "$PID" ]; then
        PROCESS_NAME=$(ps -p "$PID" -o comm= 2>/dev/null || echo "unknown")
        echo "  ⚠ 端口 $PORT 被占用 (PID: $PID, 进程: $PROCESS_NAME)"
        PORT_CONFLICT=true
        CONFLICT_PORTS+=("$PORT")
    else
        echo "  ✓ 端口 $PORT 空闲"
    fi
done
echo ""

if [ "$PORT_CONFLICT" = true ]; then
    echo "[冲突] 检测到端口冲突，请选择处理方式："
    echo "  1) 自动终止占用进程"
    echo "  2) 使用其他端口（跳过端口检查，可能导致启动失败）"
    echo "  3) 退出启动"
    echo ""
    read -p "请输入选项 (1/2/3): " PORT_CHOICE
    case $PORT_CHOICE in
        1)
            echo "[处理] 正在终止占用进程..."
            for PORT in "${CONFLICT_PORTS[@]}"; do
                PID=$(detect_port_process "$PORT")
                if [ -n "$PID" ]; then
                    kill "$PID" 2>/dev/null && echo "  ✓ 已终止端口 $PORT 的进程 (PID: $PID)"
                fi
            done
            sleep 1
            echo ""
            ;;
        2)
            echo "[跳过] 忽略端口冲突，继续启动..."
            echo ""
            ;;
        3)
            echo "[退出] 用户取消启动"
            exit 0
            ;;
        *)
            echo "[警告] 无效输入，默认忽略端口冲突继续启动..."
            echo ""
            ;;
    esac
fi

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "[错误] Python3 未安装"
    exit 1
fi

# 检查必要的依赖
python3 -c "import flask, requests" 2>/dev/null || {
    echo "[提示] 缺少依赖，正在安装..."
    pip3 install flask requests -q
}

# 停止已有服务（避免端口冲突）
if pgrep -f "framework.api.server" > /dev/null 2>&1; then
    echo "[提示] 检测到已有服务运行，正在停止..."
    pkill -f "framework.api.server" 2>/dev/null || true
    sleep 2
fi

# 依赖完整性检查
echo "[检查] Python 依赖完整性..."
if command -v pip3 &> /dev/null; then
    BROKEN_DEPS=$(pip check 2>&1) || true
    if echo "$BROKEN_DEPS" | grep -q "No broken requirements"; then
        echo "  ✓ 所有依赖完整"
    else
        echo "  ⚠ 检测到依赖问题:"
        echo "$BROKEN_DEPS" | sed 's/^/    /'
        echo "  建议运行: pip3 install -r requirements.txt"
    fi
elif command -v pip &> /dev/null; then
    BROKEN_DEPS=$(pip check 2>&1) || true
    if echo "$BROKEN_DEPS" | grep -q "No broken requirements"; then
        echo "  ✓ 所有依赖完整"
    else
        echo "  ⚠ 检测到依赖问题:"
        echo "$BROKEN_DEPS" | sed 's/^/    /'
        echo "  建议运行: pip install -r requirements.txt"
    fi
else
    echo "  ⚠ 未找到 pip，跳过依赖检查"
fi
echo ""

# 启动耗时统计
START_TIME=$(date +%s)
echo "[启动] 开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 启动服务
ARGS="${@:---multi-port}"
echo "[启动] LumiLearn Framework Server"
echo ""

python3 -m framework.api.server $ARGS

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED / 60))
ELAPSED_SEC=$((ELAPSED % 60))
echo ""
echo "  ⏱ 服务运行时长: ${ELAPSED_MIN}分${ELAPSED_SEC}秒"
echo "============================================================"
echo "  LumiLearn Framework 已停止"
echo "============================================================"