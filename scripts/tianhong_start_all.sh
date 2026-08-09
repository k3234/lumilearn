#!/usr/bin/env bash
# LumiLearn 天虹主机全服务启动脚本
# 启动：Ollama(11434) + Framework API(18080/18081/18082) + GOAI Web(5000)
set -e
cd ~/lumilearn

export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="lumilearn-v2:latest"
export TIANHONG_HOST="192.168.2.xx"
export TIANHONG_USER="kai"

mkdir -p logs

# 0. 初始化数据库（首次建表 + 默认管理员）
echo "[初始化] 数据库建表 ..."
python3 -c "
from framework.database import db
path = db.init()
print(f'[OK] 数据库已初始化: {path}')
from framework.admin.auth import get_admin_auth
get_admin_auth()
print('[OK] 默认管理员已就绪')
" 2>&1 | tail -3

# 1. 确认 Ollama 服务运行
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
  echo "[OK] Ollama 服务已运行"
else
  echo "[启动] Ollama ..."
  nohup /bin/ollama serve > logs/ollama.log 2>&1 &
  sleep 3
fi

# 2. 启动 Framework API 三端口服务
if curl -s http://localhost:18080/health > /dev/null 2>&1; then
  echo "[OK] Framework API 已在 18080 运行"
else
  echo "[启动] Framework API (18080/18081/18082) ..."
  nohup python3 framework/api/server.py --multi-port --host 0.0.0.0 > logs/framework_api.log 2>&1 &
  echo $! > logs/framework_api.pid
  sleep 4
fi

# 3. 启动 GOAI Web (5000)
if curl -s http://localhost:5000/api/status > /dev/null 2>&1; then
  echo "[OK] GOAI Web 已在 5000 运行"
else
  echo "[启动] GOAI Web (5000) ..."
  nohup python3 goai_web.py > logs/goai_web.log 2>&1 &
  echo $! > logs/goai_web.pid
  sleep 3
fi

echo ""
echo "========== 服务状态 =========="
echo "Ollama:     http://localhost:11434"
echo "Terminal:   http://localhost:18080"
echo "API:        http://localhost:18081"
echo "Models:     http://localhost:18082"
echo "GOAI Web:   http://localhost:5000"
echo "=============================="

for port in 11434 18080 18081 18082 5000; do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:$port/health 2>/dev/null || echo "N/A")
  if [ "$port" = "11434" ]; then
    code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:$port/api/tags 2>/dev/null || echo "N/A")
  fi
  echo "  端口 $port: HTTP $code"
done