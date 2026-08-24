#!/usr/bin/env bash
# ============================================================
# LumiLearn 一键部署脚本（Linux / macOS / WSL）
# 用法:  bash scripts/quick_deploy.sh
# 说明:  安装依赖 → 初始化数据库 → 确认/拉取模型 → 启动全部服务
# ============================================================
set -e
cd "$(dirname "$0")/.."

echo "==> [1/4] 检查 Python 环境"
python3 --version || { echo "需要 Python 3.10+"; exit 1; }

echo "==> [2/4] 安装依赖"
pip install -r requirements.txt

echo "==> [3/4] 确认模型（优先使用本地 Ollama 已有模型）"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
  if curl -s http://localhost:11434/api/tags | grep -q lumilearn-v2; then
    echo "    [OK] 模型 lumilearn-v2 已就绪"
  else
    echo "    [提示] 未找到 lumilearn-v2，请参考 docs/MODEL_DOWNLOAD.md 获取模型后执行:"
    echo "           ollama create lumilearn-v2 -f Modelfile"
  fi
else
  echo "    [提示] 未检测到 Ollama。请先安装 Ollama 并导入模型（见 docs/MODEL_DOWNLOAD.md）"
fi

echo "==> [4/4] 初始化数据库并启动服务"
python3 -c "from framework.database import db; print('[OK] 数据库: ' + db.init())"
if [ -f scripts/remote_start_all.sh ]; then
  bash scripts/remote_start_all.sh
else
  echo "    未找到 remote_start_all.sh，请手动启动各服务"
fi

echo ""
echo "部署完成。访问入口："
echo "  课堂模式     http://localhost:18080/classroom"
echo "  对话终端     http://localhost:18080/chat"
echo "  管理面板     http://localhost:18082/admin  (默认账号 admin / 登录后请立即改密)"
echo "  学习平台    http://localhost:5000"
echo "  学生端       http://localhost:5010"
echo "  教师端       http://localhost:5001"
echo "  分析仪表盘   http://localhost:18090"
echo ""
echo "健康检查: python3 scripts/health_check.py"
