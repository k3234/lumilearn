# -*- coding: utf-8 -*-
"""
LumiLearn 兼容性 shim — 替代已删除的 goai_web.py

提供 Flask app 实例以便 test_learning_dashboard.py 和 test_input_validation.py 导入。
"""
import os
import tempfile
from pathlib import Path

from flask import Flask
from framework.core.config import get_app_secret_key, register_csrf_guard
from framework.database import db

db.init()

app = Flask(__name__)
app.secret_key = get_app_secret_key("STUDENT_SECRET_KEY", "学生端学习平台")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("LUMILEARN_COOKIE_SECURE", "").lower() == "true",
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,
)
register_csrf_guard(app)


def check_port(port: int) -> bool:
    """检查端口是否被占用（返回 True 表示可用）"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


# 占位函数：保持 test_learning_dashboard.py 的 _match_knowledge_node 调用
def _match_knowledge_node(query: str):
    """简单知识节点匹配（兼容旧接口）"""
    keywords = {
        "function_monotonicity": ["单调", "函数", "增函数", "减函数", "区间"],
        "newton_second_law": ["牛顿", "力", "加速度", "F=ma", "质量"],
        "chemical_equilibrium": ["化学平衡", "勒夏特列", "平衡常数", "压强", "浓度"],
        "pythagorean": ["勾股", "直角三角形", "斜边", "平方"],
        "derivative": ["导数", "微分", "斜率", "变化率"],
        "normal_distribution": ["正态分布", "高斯", "钟形曲线", "标准差"],
    }
    query_lower = (query or "").lower()
    for key, kws in keywords.items():
        if any(kw in query_lower for kw in kws):
            return key
    return None


# 占位函数：保持 test_learning_dashboard.py 的 _get_adaptive_engine 调用
def _get_adaptive_engine():
    return None
