#!/usr/bin/env bash
# LumiLearn 天虹主机全服务启动脚本（按端口配置选择性启动）
# 端口启停由 Admin 面板「端口管理」配置（config/framework.yaml 的 port_settings）
set -e
cd $HOME/lumilearn

export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="lumilearn-v2:latest"
export TIANHONG_HOST="${TIANHONG_HOST:-}"
export TIANHONG_USER="${TIANHONG_USER:-}"

mkdir -p logs

# 读取端口配置，输出 "key|enabled|port"（无配置时回退默认全启用）
read_ports() {
  python3 -c "
import yaml
cfg = yaml.safe_load(open('config/framework.yaml')) or {}
ps = cfg.get('port_settings', {})
defaults = {
    'terminal': (1, 18080), 'api': (1, 18081), 'models': (1, 18082),
    'goai_web': (1, 5000), 'teacher_portal': (1, 5001),
}
for k, (de, dp) in defaults.items():
    v = ps.get(k, {})
    en = 1 if v.get('enabled', de == 1) else 0
    port = v.get('port', dp)
    print('{}|{}|{}'.format(k, en, port))
" 2>/dev/null || true
}

# 服务是否启用
is_enabled() { read_ports | grep -q "^$1|1|"; }
# 读取端口号
get_port() { read_ports | grep "^$1|" | cut -d'|' -f3; }

# 0. 初始化数据库（首次建表）
echo "[初始化] 数据库建表 ..."
python3 -c "
from framework.database import db
path = db.init()
print('[OK] 数据库已初始化: ' + path)
" 2>&1 | tail -2

# 1. Ollama（核心服务，始终启动）
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
  echo "[OK] Ollama 服务已运行"
else
  echo "[启动] Ollama ..."
  nohup /bin/ollama serve > logs/ollama.log 2>&1 &
  sleep 3
fi

# 2. Framework API（terminal/api/models 任一启用则启动）
if is_enabled terminal || is_enabled api || is_enabled models; then
  TP=$(get_port terminal)
  [ -z "$TP" ] && TP=18080
  if curl -s http://localhost:$TP/health > /dev/null 2>&1; then
    echo "[OK] Framework API 已在 $TP 运行"
  else
    echo "[启动] Framework API (terminal=$TP) ..."
    nohup python3 framework/api/server.py --multi-port --host 0.0.0.0 > logs/framework_api.log 2>&1 &
    echo $! > logs/framework_api.pid
    sleep 4
  fi
else
  echo "[跳过] Framework API（端口未启用）"
  pkill -f "framework/api/server.py" 2>/dev/null || true
fi

# 3. GOAI Web（学生端）
if is_enabled goai_web; then
  GP=$(get_port goai_web)
  [ -z "$GP" ] && GP=5000
  if curl -s http://localhost:$GP/api/status > /dev/null 2>&1; then
    echo "[OK] GOAI Web 已在 $GP 运行"
  else
    echo "[启动] GOAI Web ($GP) ..."
    nohup python3 goai_web.py > logs/goai_web.log 2>&1 &
    echo $! > logs/goai_web.pid
    sleep 3
  fi
else
  echo "[跳过] GOAI Web（端口未启用）"
  pkill -f "goai_web.py" 2>/dev/null || true
fi

# 4. 教师端（Teacher Portal）
if is_enabled teacher_portal; then
  TCP=$(get_port teacher_portal)
  [ -z "$TCP" ] && TCP=5001
  if curl -s -o /dev/null http://localhost:$TCP/api/me 2>/dev/null; then
    echo "[OK] 教师端已在 $TCP 运行"
  else
    echo "[启动] 教师端 ($TCP) ..."
    nohup python3 teacher_portal.py > logs/teacher_portal.log 2>&1 &
    echo $! > logs/teacher_portal.pid
    sleep 3
  fi
else
  echo "[跳过] 教师端（端口未启用）"
  pkill -f "teacher_portal.py" 2>/dev/null || true
fi

echo ""
echo "========== 服务状态 =========="
echo "Ollama: http://localhost:11434"
for entry in $(read_ports); do
  key=$(echo $entry | cut -d'|' -f1)
  en=$(echo $entry | cut -d'|' -f2)
  p=$(echo $entry | cut -d'|' -f3)
  if [ "$en" = "1" ] && [ -n "$p" ]; then
    code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:$p/health 2>/dev/null || echo "N/A")
    echo "  $key: 端口 $p HTTP $code"
  else
    echo "  $key: 已禁用"
  fi
done
echo "=============================="
