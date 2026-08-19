#!/usr/bin/env bash
# ============================================================
# LumiLearn 服务器部署说明
# ============================================================
# 服务器: <server-ip> (Ubuntu, 用户 <username>)
#
# 已部署服务 (systemd user 服务，开机自启):
#   11434  Ollama (lumilearn-v2:latest 主模型, qwen2.5:7b 备用)
#   18080  Framework Terminal (HTML 终端 + 全部 API)
#   18081  Framework REST API
#   18082  Framework 模型管理
#   5000   GOAI Web (费曼五步教学 Demo)
#
# 启动/停止/查看状态:
#   systemctl --user status lumilearn-api    # 18080/18081/18082
#   systemctl --user status lumilearn-goai   # 5000
#   systemctl --user restart lumilearn-api
#   journalctl --user -u lumilearn-api -f
#
# 访问入口:
#   终端:   http://<server-ip>:18080/
#   课堂:   http://<server-ip>:18080/classroom
#   聊天:   http://<server-ip>:18080/chat
#   管理:   http://<server-ip>:18080/admin  (admin / <your-password>)
#   API:    http://<server-ip>:18081/health
#   GOAI:   http://<server-ip>:5000/
#
# 一键启动 (非 systemd 环境):
#   bash scripts/remote_start_all.sh
# ============================================================

# ============================================================
# 2026-08-20 增量实操记录（P2 收尾 spec，已脱敏）
# ============================================================
# 目标: 天虹主机（Ubuntu，Python 3.10.12，用户 <user>）
# 方式: 本地 `python scripts/deploy_remote.py`（paramiko SSH/SFTP）
# 凭据: 仅通过环境变量 REMOTE_HOST / REMOTE_USER / REMOTE_PASSWORD 传入，
#        不写入任何仓库文件；报告以 <host> 占位，不显示真实地址。
#
# 执行摘要:
#   1. 上传: 3131 个文件到 <remote-dir>（默认 ~/lumilearn），跳过 .git/.env/
#      pid/缓存/虚拟环境/大文件（>5MB，67 个）
#   2. 配置: `python3 deploy/setup.py --quick --skip-deps` 成功
#      - 端口: terminal 18080 / api 18081 / models 18082 / goai 5000 /
#              teacher 5001 全部 enabled
#      - 模型: Ollama http://localhost:11434 探测成功（8 个模型，
#              默认 lumilearn-v2:latest），OLLAMA_MODEL 已写入 .env
#   3. 启动: `python3 deploy/start.py --no-open`
#      - 默认端口 18080-18082/5000/5001 被既有 systemd 部署占用 → 跳过启动
#      - 既有服务健康检查: 18081/health=200, 18080/=200, 18082/=302, /admin=200
#   4. 新实例独立验证（临时端口 28080-28082，验证后已停止并恢复配置）:
#      28080=200, 28081=200, 28082=302, /admin=200（Flask 实际响应）
#   5. 发现并修复真实缺陷: framework/api/routes/admin.py 的 _task_to_api 使用
#      Dict 注解但未导入（本机 Python 3.14 延迟注解掩盖；主机 3.10 急切注解
#      启动即崩）→ 已补 `from typing import Dict`，主机导入与启动验证通过
#
# 运维提示:
#   - 新代码已部署在 <remote-dir>（本机源同步）；若需切换正式服务，请在主机
#     停止旧 systemd 服务后于 <remote-dir> 运行 `python3 deploy/start.py`
#   - 零文件重装: 主机上执行
#     curl -fsSL https://raw.githubusercontent.com/k3234/lumilearn/master/deploy/install.sh | bash
# ============================================================
