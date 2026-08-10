#!/bin/bash
# 启动 LumiLearn 教师端（端口 5001）
cd ~/lumilearn || exit 1
mkdir -p logs

# 停止旧进程
pkill -f "teacher_portal.py" 2>/dev/null
sleep 1

# 语法检查
python3 -m py_compile teacher_portal.py framework/database.py || { echo "COMPILE_FAIL"; exit 1; }

# 后台启动（setsid 脱离 SSH 会话）
setsid nohup python3 teacher_portal.py > logs/teacher_portal.log 2>&1 < /dev/null &
echo "STARTED"
