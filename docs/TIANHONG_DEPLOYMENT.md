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
#   bash scripts/tianhong_start_all.sh
# ============================================================