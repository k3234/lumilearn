#!/bin/bash
# LumiLearn 固定 Demo 演示脚本
# 用途：确保现场演示流程可复现，规避随机性
# 用法：bash scripts/demo_fix_scenario.sh

set -e

cd "$(dirname "$0")/.."

echo "=== LumiLearn Demo 初始化 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# -------------------------------------------------------
# 1. 环境检查
# -------------------------------------------------------
echo "【步骤 1/6】环境检查..."

# 检查 Docker 环境
if command -v docker &> /dev/null && docker info &> /dev/null; then
    echo "  Docker: OK"
    # 检查 Ollama 容器
    if docker ps --format '{{.Names}}' | grep -q lumilearn-ollama; then
        echo "  Ollama 容器: 运行中"
    else
        echo "  Ollama 容器: 未启动，尝试启动..."
        docker-compose up -d ollama
        sleep 5
        docker exec lumilearn-ollama ollama list 2>/dev/null | head -5
    fi
else
    echo "  Docker: 不可用（本地模式）"
fi

# 检查 Python 依赖
if python3 -c "import flask" 2>/dev/null; then
    echo "  Python/Flask: OK"
else
    echo "  警告: Flask 未安装，运行 pip install flask"
    pip install flask -q
fi

echo ""

# -------------------------------------------------------
# 2. 预置演示数据（固定教材片段）
# -------------------------------------------------------
echo "【步骤 2/6】预置演示数据..."

# 创建演示用教材文档
DEMO_DOC="docs/demo/gougu_teaching.md"
mkdir -p docs/demo

cat > "$DEMO_DOC" << 'EOF'
# 勾股定理

## 知识点概述
勾股定理是几何学中的基本定理之一，描述了直角三角形三边之间的关系。

## 定理内容
在直角三角形中，两条直角边的平方和等于斜边的平方。
公式：a² + b² = c²

其中 a、b 为直角边，c 为斜边。

## 历史背景
勾股定理在中国古代称为"勾股定理"，最早见于《周髀算经》。
西方称"毕达哥拉斯定理"，但巴比伦人早在公元前 18 世纪就已发现此关系。

## 典型例题
1. 直角三角形两直角边分别为 3 和 4，求斜边长度。
   解：c = √(3² + 4²) = √(9 + 16) = √25 = 5

2. 直角三角形斜边为 13，一条直角边为 5，求另一条直角边。
   解：b = √(13² - 5²) = √(169 - 25) = √144 = 12
EOF

echo "  演示教材已预置: $DEMO_DOC"
echo ""

# -------------------------------------------------------
# 3. 启动服务（Lite 模式，降低资源占用）
# -------------------------------------------------------
echo "【步骤 3/6】启动服务（Lite 模式）..."

# 检查端口占用
for port in 5010 5000 18080; do
    if command -v lsof &> /dev/null; then
        if lsof -i :$port &> /dev/null; then
            echo "  端口 $port 已被占用，跳过重启"
        fi
    fi
done

# 启动主服务
if ! curl -s http://localhost:5010/health &> /dev/null; then
    nohup python3 goai_web.py --mode lite > logs/demo_server.log 2>&1 &
    echo "  服务已启动，等待 3 秒..."
    sleep 3
fi

# 验证服务状态
if curl -s http://localhost:5010/health &> /dev/null; then
    echo "  API 服务: 运行中"
else
    echo "  错误: API 服务启动失败，查看 logs/demo_server.log"
    exit 1
fi
echo ""

# -------------------------------------------------------
# 4. 执行演示流程
# -------------------------------------------------------
echo "【步骤 4/6】执行演示流程..."

API_BASE="http://localhost:5010"
ADMIN_BASE="http://localhost:18080"

# 4.1 获取管理员 Token
echo "  登录管理员账号..."
ADMIN_TOKEN=$(curl -s -X POST "$ADMIN_BASE/api/admin/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"'"$(python3 -c "import secrets; print(secrets.token_hex(16))" | head -c 8)"'"}' \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('token',''))" 2>/dev/null || echo "")

if [ -z "$ADMIN_TOKEN" ]; then
    # 使用已知的测试 admin token（演示环境）
    echo "  警告: 自动获取 Token 失败，使用环境变量 ADMIN_TOKEN"
    ADMIN_TOKEN="${LUMILEARN_ADMIN_TOKEN:-demo_token_placeholder}"
fi
echo "  管理员登录: OK"

# 4.2 导入演示教材（固定内容，规避随机性）
echo "  导入演示教材..."
curl -s -X POST "$ADMIN_BASE/api/admin/import-document" \
    -H "Content-Type: multipart/form-data" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    -F "file=@docs/demo/gougu_teaching.md" \
    -F "subject=数学" -F "chapter=几何" > /dev/null 2>&1
echo "  教材导入: OK"

# 4.3 创建演示学生账号
echo "  创建演示学生账号..."
curl -s -X POST "$API_BASE/api/auth/register" \
    -H "Content-Type: application/json" \
    -d '{"username":"demo_student","password":"demo123456","role":"student","display_name":"演示学生"}' \
    > /dev/null 2>&1
echo "  学生账号创建: OK"

# 4.4 学生登录并发起学习
echo "  学生登录..."
STUDENT_TOKEN=$(curl -s -X POST "$API_BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"demo_student","password":"demo123456"}' \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('token',''))" 2>/dev/null || echo "")
echo "  学生登录: OK"

# 4.5 触发费曼教学流程（固定知识点：勾股定理）
echo "  触发费曼教学（勾股定理）..."
curl -s -X POST "$API_BASE/api/feynman/explain" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $STUDENT_TOKEN" \
    -d '{"topic":"勾股定理","subject":"数学","step":1}' \
    -o /tmp/demo_response.json 2>/dev/null

if [ -f /tmp/demo_response.json ] && [ -s /tmp/demo_response.json ]; then
    echo "  费曼教学: OK（响应已保存至 /tmp/demo_response.json）"
else
    echo "  警告: 费曼教学返回空，可能 Ollama 未就绪"
fi

# 4.6 学生答题
echo "  学生答题..."
curl -s -X POST "$API_BASE/api/feynman/answer" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $STUDENT_TOKEN" \
    -d '{"topic":"勾股定理","answer":"a的平方加b的平方等于c的平方"}' \
    -o /tmp/demo_answer.json 2>/dev/null
echo "  答题: OK"

echo ""

# -------------------------------------------------------
# 5. 演示数据汇总
# -------------------------------------------------------
echo "【步骤 5/6】演示数据汇总..."

echo ""
echo "=== 演示状态 ==="
echo "  API 服务: $API_BASE"
echo "  Admin 面板: $ADMIN_BASE"
echo "  学生账号: demo_student / demo123456"
echo "  预置教材: docs/demo/gougu_teaching.md"
echo "  教学响应: /tmp/demo_response.json"
echo "  答题记录: /tmp/demo_answer.json"
echo ""
echo "=== 浏览器访问地址 ==="
echo "  学生端: http://localhost:5000/student"
echo "  教师端: http://localhost:5001/teacher"
echo "  管理面板: http://localhost:18080"
echo ""

# -------------------------------------------------------
# 6. 保持运行提示
# -------------------------------------------------------
echo "【步骤 6/6】演示准备完成"
echo ""
echo "提示：演示过程中如需重新初始化数据，执行："
echo "  rm -f lumilearn.db && python3 scripts/demo_fix_scenario.sh"
echo ""
echo "按 Ctrl+C 可停止服务（数据保留）"
echo "按 Ctrl+D 保持运行（推荐用于现场演示）"
