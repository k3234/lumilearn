#!/usr/bin/env bash
# ============================================================
# LumiLearn 天虹主机部署说明
# ============================================================
# 天虹主机: 192.168.2.xx (Ubuntu, 用户 kai)
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
#   终端:   http://192.168.2.xx:18080/
#   课堂:   http://192.168.2.xx:18080/classroom
#   聊天:   http://192.168.2.xx:18080/chat
#   管理:   http://192.168.2.xx:18080/admin  (admin / admin123)
#   API:    http://192.168.2.xx:18081/health
#   GOAI:   http://192.168.2.xx:5000/
#
# 一键启动 (非 systemd 环境):
#   bash scripts/tianhong_start_all.sh
# ============================================================