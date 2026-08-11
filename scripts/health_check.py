# -*- coding: utf-8 -*-
"""LumiLearn 服务健康检查脚本

用法: python3 scripts/health_check.py [--host 127.0.0.1]
检查所有服务端口 + 核心 API + 数据库状态。
"""
import argparse
import json
import os
import sys
import urllib.request

DEFAULT_HOST = "127.0.0.1"

SERVICES = [
    # (名称, 端口, 探活路径)
    ("课堂/终端/管理 (Framework API)", 18080, "/health"),
    ("REST API", 18081, "/health"),
    ("管理面板 API", 18082, "/api/admin/me"),
    ("GOAI 学习 Web", 5000, "/api/status"),
    ("教师端", 5001, "/api/me"),
    ("学生端学习平台", 5010, "/api/status"),
    ("学习分析仪表盘", 18090, "/api/dashboard/overview"),
]


def check(host: str, port: int, path: str, timeout: int = 8) -> str:
    url = f"http://{host}:{port}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            # 部分接口需要登录返回 401，说明服务在线
            ok = r.status in (200, 302) or r.status in (401,)
            return "OK" if ok else f"HTTP {r.status}"
    except Exception as e:
        return f"DOWN ({e.__class__.__name__})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=DEFAULT_HOST)
    args = ap.parse_args()

    print(f"LumiLearn 健康检查 (host={args.host})\n" + "=" * 56)
    all_ok = True
    for name, port, path in SERVICES:
        status = check(args.host, port, path)
        mark = "✅" if status == "OK" else "❌"
        print(f"  {mark} 端口 {port:<6} {name:<22} {status}")
        if status != "OK":
            all_ok = False

    # 数据库
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from framework.database import db
        db.init()
        users = db.get_users()
        print(f"  ✅ 数据库 lumilearn.db  用户 {len(users)} 人")
    except Exception as e:
        print(f"  ❌ 数据库异常: {e}")
        all_ok = False

    print("=" * 56)
    print("全部服务正常 🎉" if all_ok else "存在异常服务，请查看上方 ❌ 项")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
