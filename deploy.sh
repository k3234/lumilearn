#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# LumiLearn 一键部署脚本 (Linux / macOS)
# 支持：Ubuntu / Debian / CentOS / Fedora / macOS
# 配置：YAML配置文件 + 多用户端 + 多模型兼容
#
# 使用方法：
#   chmod +x deploy.sh
#   ./deploy.sh                  # 使用默认配置启动
#   ./deploy.sh --config custom  # 使用自定义配置文件
#   ./deploy.sh --summary        # 显示当前配置摘要
#   ./deploy.sh --validate       # 验证配置文件
#   ./deploy.sh --quickstart     # 生成快速启动指南
#   ./deploy.sh --docker         # Docker容器部署
#

set -euo pipefail

# ============================================================
# 颜色定义
# ============================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'
BOLD='\033[1m'

# ============================================================
# 日志函数
# ============================================================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# ============================================================
# 配置变量
# ============================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/.venv"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/deploy_$(date '+%Y%m%d_%H%M%S').log"
CONFIG_FILE="$PROJECT_DIR/deploy_config.yaml"
PYTHON_CMD=""

# ============================================================
# 解析命令行参数
# ============================================================
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --summary)
                python3 "$PROJECT_DIR/scripts/config_manager.py" --summary
                exit 0
                ;;
            --validate)
                python3 "$PROJECT_DIR/scripts/config_manager.py" --validate
                exit 0
                ;;
            --quickstart)
                python3 "$PROJECT_DIR/scripts/config_manager.py" --quickstart
                exit 0
                ;;
            --docker)
                run_docker
                exit 0
                ;;
            --model)
                python3 "$PROJECT_DIR/scripts/config_manager.py" --set-model "$2"
                shift 2
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

show_help() {
    cat << EOF
${BOLD}LumiLearn 一键部署脚本${NC}

${BOLD}用法:${NC}
    ./deploy.sh [选项]

${BOLD}选项:${NC}
    --config FILE       使用指定配置文件 (默认: deploy_config.yaml)
    --summary           显示当前配置摘要
    --validate          验证配置文件
    --quickstart        生成快速启动指南
    --model MODEL       设置默认模型
    --docker            Docker容器部署
    -h, --help         显示帮助信息

${BOLD}访问入口:${NC}
    课堂/终端     - http://localhost:18080/classroom
    管理面板      - http://localhost:18082/admin
    GOAI 学习     - http://localhost:5000
    学生端        - http://localhost:5010
    教师端        - http://localhost:5001
    分析仪表盘    - http://localhost:18090

${BOLD}示例:${NC}
    ./deploy.sh                           # 默认启动
    ./deploy.sh --summary                 # 查看配置
    ./deploy.sh --model deepseek-r1:7b   # 切换模型
    ./deploy.sh --docker                  # Docker部署

${BOLD}支持的系统:${NC}
    - Ubuntu 20.04+
    - Debian 11+
    - CentOS 8+
    - Fedora 35+
    - macOS 12+ (Intel/Apple Silicon)

EOF
}

# ============================================================
# 系统检测
# ============================================================
detect_os() {
    log_step "🔍 检测系统环境"

    local os_name=""
    local os_version=""
    local arch=""

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            os_name="${ID:-linux}"
            os_version="${VERSION_ID:-unknown}"
        else
            os_name="linux"
            os_version="unknown"
        fi
        arch=$(uname -m)
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        os_name="macos"
        os_version=$(sw_vers -productVersion 2>/dev/null || echo "unknown")
        arch=$(uname -m)
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi

    log_info "操作系统: ${BOLD}$os_name $os_version${NC}"
    log_info "系统架构: ${BOLD}$arch${NC}"

    # 检测内存
    local mem_total=""
    if [[ "$os_name" == "macos" ]]; then
        mem_total=$(($(sysctl -n hw.memsize) / 1024 / 1024))
    else
        mem_total=$(($(grep MemTotal /proc/meminfo | awk '{print $2}') / 1024))
    fi
    log_info "系统内存: ${BOLD}${mem_total}MB${NC}"

    if [[ $mem_total -lt 4000 ]]; then
        log_warn "内存不足4GB，建议8GB+"
    fi

    # 检测磁盘空间
    local disk_free=$(df -BG "$PROJECT_DIR" 2>/dev/null | awk 'NR==2 {print $4}' | tr -d 'G' || echo "0")
    log_info "可用磁盘空间: ${BOLD}${disk_free}GB${NC}"

    if [[ $disk_free -lt 10 ]]; then
        log_warn "磁盘空间不足10GB"
    fi

    # 检测 Python
    for python_cmd in python3 python; do
        if command -v "$python_cmd" &>/dev/null; then
            PYTHON_CMD="$python_cmd"
            break
        fi
    done

    if [[ -z "$PYTHON_CMD" ]]; then
        log_error "未找到 Python"
        log_info "请安装 Python 3.10+"
        exit 1
    fi

    local python_version=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    log_info "Python版本: ${BOLD}$python_version${NC}"

    local major=$(echo "$python_version" | cut -d. -f1)
    local minor=$(echo "$python_version" | cut -d. -f2)
    if [[ $major -lt 3 ]] || [[ $major -eq 3 && $minor -lt 10 ]]; then
        log_error "Python 版本过低 ($python_version)，需要 3.10+"
        exit 1
    fi
}

# ============================================================
# 检查配置文件
# ============================================================
check_config() {
    log_step "📋 检查配置文件"

    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_warn "配置文件不存在: $CONFIG_FILE"
        log_info "将使用默认配置..."
        # 创建默认配置文件
        python3 "$PROJECT_DIR/scripts/config_manager.py" --quickstart > "$CONFIG_FILE" 2>/dev/null || true
    fi

    log_info "配置文件: ${BOLD}$CONFIG_FILE${NC}"

    # 验证配置
    log_info "验证配置..."
    python3 "$PROJECT_DIR/scripts/config_manager.py" --validate

    # 显示配置摘要
    python3 "$PROJECT_DIR/scripts/config_manager.py" --summary

    log_success "配置检查完成"
}

# ============================================================
# 安装系统依赖
# ============================================================
install_system_deps() {
    log_step "📦 安装系统依赖"

    local os_name=""
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        os_name="$ID"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        os_name="macos"
    fi

    case "$os_name" in
        ubuntu|debian)
            log_info "Ubuntu/Debian: 安装依赖..."
            sudo apt update -qq
            sudo apt install -y -qq python3-venv python3-pip python3-dev build-essential ffmpeg git curl wget
            ;;
        centos|fedora)
            log_info "CentOS/Fedora: 安装依赖..."
            sudo dnf install -y python3-virtualenv python3-devel gcc gcc-c++ make ffmpeg git curl wget
            ;;
        macos)
            log_info "macOS: 检查依赖..."
            if ! command -v brew &>/dev/null; then
                log_warn "未检测到 Homebrew，建议安装：https://brew.sh"
            fi
            brew install ffmpeg git curl wget 2>/dev/null || true
            ;;
        *)
            log_warn "未知系统，跳过系统依赖安装"
            ;;
    esac

    log_success "系统依赖检查完成"
}

# ============================================================
# 创建虚拟环境
# ============================================================
setup_venv() {
    log_step "🐍 创建 Python 虚拟环境"

    if [ ! -d "$VENV_DIR" ]; then
        log_info "创建虚拟环境..."
        $PYTHON_CMD -m venv "$VENV_DIR"
    else
        log_info "虚拟环境已存在"
    fi

    source "$VENV_DIR/bin/activate"
    log_info "虚拟环境已激活"

    # 升级 pip
    log_info "升级 pip..."
    pip install --upgrade pip setuptools wheel -q

    log_success "虚拟环境准备完成"
}

# ============================================================
# 安装 Python 依赖
# ============================================================
install_python_deps() {
    log_step "📚 安装 Python 依赖"

    source "$VENV_DIR/bin/activate"

    log_info "安装依赖包..."
    pip install -r "$PROJECT_DIR/requirements.txt" -q
    pip install pyyaml -q  # 配置管理器需要

    log_success "Python 依赖安装完成"
}

# ============================================================
# 配置模型
# ============================================================
setup_model() {
    log_step "🧠 配置 AI 模型"

    source "$VENV_DIR/bin/activate"

    # 检查配置文件中的模型配置
    local ollama_enabled=$(python3 -c "
import yaml
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)
print(config.get('models', {}).get('local', {}).get('enabled', True))
" 2>/dev/null || echo "true")

    if [[ "$ollama_enabled" == "True" ]]; then
        # 检查 Ollama
        if ! command -v ollama &>/dev/null; then
            log_info "安装 Ollama..."
            if [[ "$OSTYPE" == "darwin"* ]]; then
                brew install ollama 2>/dev/null || log_warn "请手动安装: https://ollama.com/download"
            else
                curl -fsSL https://ollama.com/install.sh | sh
            fi
        fi

        # 启动 Ollama
        if ! pgrep -x "ollama" > /dev/null 2>&1; then
            log_info "启动 Ollama 服务..."
            ollama serve &
            sleep 3
        fi

        # 获取默认模型
        local default_model=$(python3 -c "
import yaml
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)
print(config.get('models', {}).get('local', {}).get('ollama', {}).get('default_model', 'qwen2.5:7b'))
" 2>/dev/null || echo "qwen2.5:7b")

        log_info "配置默认模型: ${BOLD}$default_model${NC}"
        ollama pull "$default_model" || log_warn "模型下载可能需要时间"

    else
        log_info "使用云端API模型"
        log_warn "请确保已设置相应的API密钥环境变量"
        log_warn "例如: export OPENAI_API_KEY=xxx"
    fi

    log_success "模型配置完成"
}

# ============================================================
# 创建必要目录
# ============================================================
create_directories() {
    log_step "📁 创建必要目录"

    mkdir -p "$LOG_DIR"
    mkdir -p "$PROJECT_DIR/data"
    mkdir -p "$PROJECT_DIR/output"
    mkdir -p "$PROJECT_DIR/checkpoints"

    log_success "目录创建完成"
}

# ============================================================
# 启动服务
# ============================================================
start_server() {
    log_step "🚀 启动 LumiLearn 服务"

    source "$VENV_DIR/bin/activate"

    log_info "端口由 config/framework.yaml 的 port_settings 配置控制（默认 18080/18081/18082）"
    log_info "日志文件: $LOG_FILE"

    cd "$PROJECT_DIR"

    # 启动服务（后台运行）
    nohup python -m framework.api.server \
        --multi-port \
        --host 0.0.0.0 \
        2>&1 | tee -a "$LOG_FILE" &

    SERVER_PID=$!
    echo "$SERVER_PID" > "$LOG_DIR/server.pid"

    log_info "服务启动中 (PID: $SERVER_PID)"
}

# ============================================================
# 健康检查
# ============================================================
health_check() {
    log_step "🏥 服务健康检查"

    local health_port=$(CONFIG_FILE="$CONFIG_FILE" python3 -c "
import os, yaml
with open(os.environ['CONFIG_FILE'], 'r') as f:
    config = yaml.safe_load(f)
server = config.get('server', {})
multi_port = server.get('multi_port', {})
if multi_port.get('enabled', True):
    print(multi_port.get('terminal', 18080))
else:
    print(server.get('single_port', {}).get('port', 18080))
" 2>/dev/null || echo "18080")

    local max_retries=10
    local retry=0

    while [[ $retry -lt $max_retries ]]; do
        if curl -s "http://localhost:$health_port/health" > /dev/null 2>&1; then
            log_success "服务启动成功！"

            echo ""
            echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${PURPLE}  🎓 LumiLearn 已成功启动！${NC}"
            echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo ""
            echo -e "  ${BOLD}课堂/终端:${NC}  http://localhost:$health_port/classroom"
            echo -e "  ${BOLD}管理面板:${NC}   http://localhost:18082/admin"
            echo -e "  ${BOLD}学生端:${NC}     http://localhost:5010"
            echo -e "  ${BOLD}教师端:${NC}     http://localhost:5001"
            echo -e "  ${BOLD}分析仪表盘:${NC} http://localhost:18090"
            echo ""
            echo -e "  ${BOLD}API状态:${NC}   http://localhost:$health_port/api/status"
            echo -e "  ${BOLD}健康检查:${NC}  http://localhost:$health_port/health"
            echo ""
            echo -e "  ${BOLD}按 Ctrl+C 停止服务${NC}"
            echo ""
            return 0
        fi

        retry=$((retry + 1))
        log_info "等待服务启动... ($retry/$max_retries)"
        sleep 2
    done

    log_error "服务启动失败，请检查日志: $LOG_FILE"
    return 1
}

# ============================================================
# Docker 部署
# ============================================================
run_docker() {
    log_step "🐳 Docker 容器部署"

    if ! command -v docker &>/dev/null; then
        log_error "未检测到 Docker，请先安装 Docker"
        log_info "https://docs.docker.com/get-docker/"
        exit 1
    fi

    log_info "构建Docker镜像..."
    docker build -t lumilearn/lumilearn:latest "$PROJECT_DIR"

    log_info "启动容器..."
    docker run -d \
        --name lumilearn \
        -p 18080:18080 \
        -p 18081:18081 \
        -p 18082:18082 \
        -v "$PROJECT_DIR/data:/app/data" \
        -v "$PROJECT_DIR/logs:/app/logs" \
        -v "$PROJECT_DIR/output:/app/output" \
        -v "$PROJECT_DIR/checkpoints:/app/checkpoints" \
        --restart unless-stopped \
        lumilearn/lumilearn:latest

    log_success "Docker容器已启动！"
    echo ""
    echo -e "  ${BOLD}访问地址:${NC}"
    echo -e "  课堂/终端: http://localhost:18080/classroom"
    echo -e "  管理面板:  http://localhost:18082/admin"
    echo ""
    echo -e "  ${BOLD}管理命令:${NC}"
    echo -e "  docker ps              # 查看容器状态"
    echo -e "  docker logs lumilearn  # 查看日志"
    echo -e "  docker stop lumilearn  # 停止容器"
    echo -e "  docker start lumilearn # 启动容器"
}

# ============================================================
# 主函数
# ============================================================
main() {
    echo ""
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}  🎓 LumiLearn - 一键部署脚本${NC}"
    echo -e "${PURPLE}  全球首个本地部署、隐私安全、L1-L5全生态AI学习系统${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # 解析参数
    parse_args "$@"

    # 检测系统
    detect_os

    # 检查配置
    check_config

    # 安装系统依赖
    install_system_deps

    # 创建虚拟环境
    setup_venv

    # 安装 Python 依赖
    install_python_deps

    # 配置模型
    setup_model

    # 创建目录
    create_directories

    # 启动服务
    start_server

    # 健康检查
    health_check
}

# 运行主函数
main "$@"
