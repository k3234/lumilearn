# -*- coding: utf-8 -*-
"""
安全相关API路由
"""
import logging
from flask import Blueprint, jsonify, request

from framework.security import (
    get_gateway, get_sandbox, get_firewall,
    reset_gateway, reset_sandbox, reset_firewall,
    SecurityConfig,
)

logger = logging.getLogger(__name__)

security_bp = Blueprint('security', __name__, url_prefix='/api/security')


@security_bp.route('/status', methods=['GET'])
def get_status():
    """获取安全系统状态"""
    gateway = get_gateway()
    sandbox = get_sandbox()
    firewall = get_firewall()

    return jsonify({
        "gateway": gateway.get_stats(),
        "sandbox": sandbox.get_stats(),
        "firewall": firewall.get_status(),
        "local_ip": firewall.get_local_ip(),
        "internal_ip": firewall.get_internal_ip()
    })


@security_bp.route('/gateway/stats', methods=['GET'])
def get_gateway_stats():
    """获取网关统计"""
    gateway = get_gateway()
    return jsonify(gateway.get_stats())


@security_bp.route('/gateway/block', methods=['POST'])
def block_ip():
    """封禁IP"""
    data = request.get_json()
    ip = data.get('ip')
    reason = data.get('reason', '手动封禁')
    duration = data.get('duration', 3600)

    if not ip:
        return jsonify({"error": "缺少IP地址"}), 400

    gateway = get_gateway()
    gateway.block_ip(ip, reason, duration)

    return jsonify({
        "message": f"IP {ip} 已封禁",
        "ip": ip,
        "reason": reason,
        "duration": duration
    })


@security_bp.route('/gateway/unblock', methods=['POST'])
def unblock_ip():
    """解封IP"""
    data = request.get_json()
    ip = data.get('ip')

    if not ip:
        return jsonify({"error": "缺少IP地址"}), 400

    gateway = get_gateway()
    gateway.unblock_ip(ip)

    return jsonify({
        "message": f"IP {ip} 已解封",
        "ip": ip
    })


@security_bp.route('/gateway/logs', methods=['GET'])
def get_gateway_logs():
    """获取网关日志"""
    limit = request.args.get('limit', 100, type=int)
    gateway = get_gateway()
    return jsonify({
        "logs": gateway.get_request_log(limit),
        "total": len(gateway.get_request_log())
    })


@security_bp.route('/firewall/rules', methods=['GET'])
def get_firewall_rules():
    """获取防火墙规则"""
    firewall = get_firewall()
    return jsonify({
        "rules": firewall.get_rules(),
        "status": firewall.get_status()
    })


@security_bp.route('/firewall/rules', methods=['POST'])
def add_firewall_rule():
    """添加防火墙规则"""
    data = request.get_json()
    action = data.get('action', 'allow')
    source = data.get('source')
    port = data.get('port')
    description = data.get('description', '')

    if not source:
        return jsonify({"error": "缺少源IP/CIDR"}), 400

    if action not in ['allow', 'deny']:
        return jsonify({"error": "action必须是allow或deny"}), 400

    firewall = get_firewall()
    rule_id = firewall.add_rule(
        action=action,
        source=source,
        port=port,
        description=description
    )

    return jsonify({
        "message": "规则已添加",
        "rule_id": rule_id,
        "action": action,
        "source": source,
        "port": port,
        "description": description
    })


@security_bp.route('/firewall/rules/<rule_id>', methods=['DELETE'])
def remove_firewall_rule(rule_id):
    """删除防火墙规则"""
    firewall = get_firewall()
    success = firewall.remove_rule(rule_id)

    if not success:
        return jsonify({"error": "规则不存在"}), 404

    return jsonify({"message": f"规则 {rule_id} 已删除"})


@security_bp.route('/firewall/check', methods=['POST'])
def check_access():
    """检查访问权限"""
    data = request.get_json()
    source_ip = data.get('ip', request.remote_addr)
    dest_port = data.get('port', 18080)

    firewall = get_firewall()
    result = firewall.check_access(source_ip, dest_port)

    return jsonify(result)


@security_bp.route('/sandbox/stats', methods=['GET'])
def get_sandbox_stats():
    """获取沙箱统计"""
    sandbox = get_sandbox()
    return jsonify(sandbox.get_stats())


@security_bp.route('/sandbox/execute', methods=['POST'])
def execute_code():
    """在沙箱中执行代码"""
    data = request.get_json()
    code = data.get('code', '')
    user_id = data.get('user_id', 'anonymous')

    if not code:
        return jsonify({"error": "缺少代码"}), 400

    sandbox = get_sandbox()
    result = sandbox.execute(code, user_id)

    return jsonify({
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "execution_time": result.execution_time,
        "return_value": result.return_value
    })


@security_bp.route('/firewall/apply', methods=['POST'])
def apply_system_firewall():
    """应用系统级防火墙规则（需要管理员权限）"""
    firewall = get_firewall()

    # 检查是否有管理员权限
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return jsonify({"error": "需要API密钥"}), 401

    firewall.apply_system_firewall()

    return jsonify({"message": "系统防火墙规则已应用"})


@security_bp.route('/reset', methods=['POST'])
def reset_security_system():
    """重置安全系统（仅用于测试）"""
    reset_gateway()
    reset_sandbox()
    reset_firewall()

    return jsonify({"message": "安全系统已重置"})


@security_bp.route('/recommendations', methods=['GET'])
def get_security_recommendations():
    """获取安全建议"""
    firewall = get_firewall()
    gateway = get_gateway()
    sandbox = get_sandbox()

    recommendations = []

    # 防火墙建议
    status = firewall.get_status()
    if status["rules_count"] < 5:
        recommendations.append({
            "type": "firewall",
            "level": "warning",
            "message": "防火墙规则较少，建议添加更多规则"
        })

    # 网关建议
    stats = gateway.get_stats()
    if stats["blocked_ips"] > 0:
        recommendations.append({
            "type": "gateway",
            "level": "info",
            "message": f"已封禁 {stats['blocked_ips']} 个IP地址"
        })

    # 沙箱建议
    sandbox_stats = sandbox.get_stats()
    if sandbox_stats["total_executions"] > 1000:
        recommendations.append({
            "type": "sandbox",
            "level": "info",
            "message": "沙箱已执行多次，建议定期检查执行日志"
        })

    return jsonify({
        "local_ip": firewall.get_local_ip(),
        "internal_ip": firewall.get_internal_ip(),
        "recommendations": recommendations
    })
