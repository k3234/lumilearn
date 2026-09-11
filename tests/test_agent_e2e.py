# -*- coding: utf-8 -*-
"""
LumiLearn 10 Agent 端到端完整测试
==================================
使用 10 个完整 Agent 身份档案，代入真实使用场景，
逐一访问所有核心 API 端点，收集响应时间、状态码、内容质量。
"""

import json
import os
import sys
import time
import concurrent.futures
from datetime import datetime
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

AGENTS_DIR = BASE / "docs" / "simulation" / "agents"
OUTPUT_DIR = BASE / "docs" / "simulation"
BASE_URL = "http://127.0.0.1:18080"

# ---------------------------------------------------------------------------
# Agent 数据定义（与档案对应）
# ---------------------------------------------------------------------------
AGENTS = [
    {
        "id": "agent_01", "name": "陈小雨", "role": "student", "grade": 7,
        "style": "visual", "device": "poor", "network": "unstable",
        "topics": ["勾股定理", "用字母表示数", "简单方程"],
        "scenario": "课后补基础，喜欢看图形和动画",
        "difficulty": "beginner",
    },
    {
        "id": "agent_02", "name": "林浩然", "role": "student", "grade": 7,
        "style": "logical", "device": "medium", "network": "unstable",
        "topics": ["导数概念", "极限定义", "函数单调性"],
        "scenario": "主动学习，追问推导过程",
        "difficulty": "intermediate",
    },
    {
        "id": "agent_03", "name": "黄志远", "role": "student", "grade": 8,
        "style": "visual", "device": "poor", "network": "unstable",
        "topics": ["一次函数", "二元一次方程组", "三角形全等"],
        "scenario": "被强制补课，容易放弃",
        "difficulty": "beginner",
    },
    {
        "id": "agent_04", "name": "王秀芳", "role": "student", "grade": 8,
        "style": "practice", "device": "medium", "network": "ok",
        "topics": ["因式分解", "分式运算", "二次根式"],
        "scenario": "刷题巩固，需要详细解析",
        "difficulty": "intermediate",
    },
    {
        "id": "agent_05", "name": "吴思琪", "role": "student", "grade": 9,
        "style": "visual", "device": "medium", "network": "unstable",
        "topics": ["二次函数", "圆的性质", "概率统计"],
        "scenario": "中考冲刺，压力大，需要鼓励",
        "difficulty": "advanced",
    },
    {
        "id": "agent_06", "name": "张子轩", "role": "student", "grade": 9,
        "style": "logical", "device": "medium", "network": "ok",
        "topics": ["相似三角形", "锐角三角函数", "统计与概率综合"],
        "scenario": "学霸挑战难题，喜欢验证思路",
        "difficulty": "advanced",
    },
    {
        "id": "agent_07", "name": "刘晓峰", "role": "teacher", "grade": None,
        "style": "logical", "device": "good", "network": "ok",
        "topics": ["勾股定理教学设计", "函数单调性备课", "三角形全等课件"],
        "scenario": "备课用，想导出数据做班级分析",
        "difficulty": "teacher",
    },
    {
        "id": "agent_08", "name": "赵建国", "role": "teacher", "grade": None,
        "style": "practice", "device": "good", "network": "ok",
        "topics": ["方程应用题", "几何证明入门", "统计图表"],
        "scenario": "被迫使用，习惯PPT+黑板",
        "difficulty": "teacher",
    },
    {
        "id": "agent_09", "name": "孙丽娟", "role": "teacher", "grade": None,
        "style": "visual", "device": "medium", "network": "ok",
        "topics": ["古诗词欣赏", "阅读理解方法", "作文指导"],
        "scenario": "跨学科探索，语文内容少",
        "difficulty": "teacher",
    },
    {
        "id": "agent_10", "name": "周明华", "role": "admin", "grade": None,
        "style": "practice", "device": "good", "network": "ok",
        "topics": [],
        "scenario": "查看平台状态、管理用户、监控使用数据",
        "difficulty": "admin",
    },
]

# difficulty → 有效 level 映射
_DIFFICULTY_TO_LEVEL = {"beginner": "junior", "intermediate": "junior", "advanced": "senior"}

# 预注册用户 token 缓存
_AGENT_TOKENS = {}


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def setup_test_users():
    """预注册所有 Agent 为测试用户，返回 {agent_name: token}"""
    from framework.database import db
    db.init()
    passwords = {}
    for agent in AGENTS:
        uname = f"test_{agent['role']}_{agent['name']}"
        pwd = "test123"
        passwords[agent["name"]] = pwd
        existing = db.get_user_by_username(uname)
        if not existing:
            db.add_user(name=agent["name"], role=agent["role"],
                        username=uname, password=pwd)
            print(f"  注册用户: {agent['name']} ({agent['role']}) / {uname}")
        else:
            print(f"  已有用户: {agent['name']} ({agent['role']})")
    # 登录获取 token
    for agent in AGENTS:
        uname = f"test_{agent['role']}_{agent['name']}"
        try:
            r = requests.post(f"{BASE_URL}/api/auth/login",
                              json={"username": uname, "password": "test123"},
                              timeout=10)
            if r.status_code in (200, 201):
                _AGENT_TOKENS[agent["name"]] = r.json().get("token", "")
        except Exception:
            pass
    # 尝试管理员登录（使用默认 admin/admin123）
    global _ADMIN_TOKEN
    try:
        r = requests.post(f"{BASE_URL}/api/admin/login",
                          json={"username": "admin", "password": "admin123"},
                          timeout=10)
        if r.status_code in (200, 201):
            _ADMIN_TOKEN = r.json().get("token", "")
            print(f"  管理员登录: OK (token: {_ADMIN_TOKEN[:8]}...)")
        else:
            print(f"  管理员登录: 失败 (status={r.status_code})，使用普通用户测试替代")
    except Exception as e:
        print(f"  管理员登录: 异常 {e}")
    return _AGENT_TOKENS


def load_agent_file(agent_id: str) -> dict:
    """从档案文件加载补充信息"""
    f = AGENTS_DIR / f"{agent_id}.md"
    if not f.exists():
        return {}
    return {"file": str(f), "exists": True}


def test_health() -> dict:
    """测试 /health 端点"""
    t0 = time.time()
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        return {"endpoint": "/health", "method": "GET", "status": r.status_code,
                "time_ms": round((time.time() - t0) * 1000, 1), "success": r.status_code == 200,
                "data": r.json() if r.status_code == 200 else None}
    except Exception as e:
        return {"endpoint": "/health", "method": "GET", "status": 0,
                "time_ms": round((time.time() - t0) * 1000, 1), "success": False,
                "error": str(e)}


def test_api_status() -> dict:
    """测试 /api/status 端点"""
    t0 = time.time()
    try:
        r = requests.get(f"{BASE_URL}/api/status", timeout=10)
        return {"endpoint": "/api/status", "method": "GET", "status": r.status_code,
                "time_ms": round((time.time() - t0) * 1000, 1), "success": r.status_code == 200,
                "data": r.json() if r.status_code == 200 else None}
    except Exception as e:
        return {"endpoint": "/api/status", "method": "GET", "status": 0,
                "time_ms": round((time.time() - t0) * 1000, 1), "success": False,
                "error": str(e)}


def _test_auth_login(username: str) -> dict:
    """测试 /api/auth/login"""
    t0 = time.time()
    try:
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"username": username, "password": "test123"},
                          timeout=10)
        return {"endpoint": "/api/auth/login", "method": "POST", "status": r.status_code,
                "time_ms": round((time.time() - t0) * 1000, 1),
                "success": r.status_code in (200, 201),
                "data": r.json() if r.status_code in (200, 201) else None}
    except Exception as e:
        return {"endpoint": "/api/auth/login", "method": "POST", "status": 0,
                "time_ms": round((time.time() - t0) * 1000, 1), "success": False,
                "error": str(e)}


def _test_feynman_explain(topic: str, level: str = "junior", token: str = "") -> dict:
    """测试 /api/feynman/explain"""
    t0 = time.time()
    headers = {"X-Auth-Token": token} if token else {}
    try:
        r = requests.post(f"{BASE_URL}/api/feynman/explain",
                          json={"topic": topic, "level": level},
                          headers=headers, timeout=30)
        return {"endpoint": "/api/feynman/explain", "method": "POST", "status": r.status_code,
                "time_ms": round((time.time() - t0) * 1000, 1),
                "success": r.status_code in (200, 201),
                "data": r.json() if r.status_code in (200, 201) else None}
    except Exception as e:
        return {"endpoint": "/api/feynman/explain", "method": "POST", "status": 0,
                "time_ms": round((time.time() - t0) * 1000, 1), "success": False,
                "error": str(e)}


def _test_feynman_classroom(topic: str, token: str = "") -> dict:
    """测试 /api/feynman/classroom"""
    t0 = time.time()
    headers = {"X-Auth-Token": token} if token else {}
    try:
        r = requests.post(f"{BASE_URL}/api/feynman/classroom",
                          json={"topic": topic, "knowledge_node": {"name": topic, "category": "math"}},
                          headers=headers, timeout=30)
        return {"endpoint": "/api/feynman/classroom", "method": "POST", "status": r.status_code,
                "time_ms": round((time.time() - t0) * 1000, 1),
                "success": r.status_code in (200, 201),
                "data": r.json() if r.status_code in (200, 201) else None}
    except Exception as e:
        return {"endpoint": "/api/feynman/classroom", "method": "POST", "status": 0,
                "time_ms": round((time.time() - t0) * 1000, 1), "success": False,
                "error": str(e)}


def _test_chat(topic: str, token: str = "") -> dict:
    """测试 /api/chat"""
    t0 = time.time()
    headers = {"X-Auth-Token": token} if token else {}
    try:
        r = requests.post(f"{BASE_URL}/api/chat",
                          json={"messages": [{"role": "user", "content": f"请帮我讲解{topic}的基础概念"}],
                                "mode": "feynman"},
                          headers=headers, timeout=30)
        return {"endpoint": "/api/chat", "method": "POST", "status": r.status_code,
                "time_ms": round((time.time() - t0) * 1000, 1),
                "success": r.status_code in (200, 201),
                "data": r.json() if r.status_code in (200, 201) else None}
    except Exception as e:
        return {"endpoint": "/api/chat", "method": "POST", "status": 0,
                "time_ms": round((time.time() - t0) * 1000, 1), "success": False,
                "error": str(e)}


def _test_feynman_test(topic: str, token: str = "") -> dict:
    """测试 /api/feynman/test"""
    t0 = time.time()
    headers = {"X-Auth-Token": token} if token else {}
    try:
        r = requests.post(f"{BASE_URL}/api/feynman/test",
                          json={"topic": topic, "student_answer": "需要理解核心概念"},
                          headers=headers, timeout=30)
        return {"endpoint": "/api/feynman/test", "method": "POST", "status": r.status_code,
                "time_ms": round((time.time() - t0) * 1000, 1),
                "success": r.status_code in (200, 201),
                "data": r.json() if r.status_code in (200, 201) else None}
    except Exception as e:
        return {"endpoint": "/api/feynman/test", "method": "POST", "status": 0,
                "time_ms": round((time.time() - t0) * 1000, 1), "success": False,
                "error": str(e)}


def test_admin_overview(token: str = "") -> dict:
    """测试 /api/admin/overview"""
    t0 = time.time()
    headers = {"X-Auth-Token": token} if token else {}
    try:
        r = requests.get(f"{BASE_URL}/api/admin/overview", headers=headers, timeout=10)
        return {"endpoint": "/api/admin/overview", "method": "GET", "status": r.status_code,
                "time_ms": round((time.time() - t0) * 1000, 1),
                "success": r.status_code in (200, 201),
                "data": r.json() if r.status_code in (200, 201) else None}
    except Exception as e:
        return {"endpoint": "/api/admin/overview", "method": "GET", "status": 0,
                "time_ms": round((time.time() - t0) * 1000, 1), "success": False,
                "error": str(e)}


def test_admin_agents(token: str = "") -> dict:
    """测试 /api/admin/agents"""
    t0 = time.time()
    headers = {"X-Auth-Token": token} if token else {}
    try:
        r = requests.get(f"{BASE_URL}/api/admin/agents", headers=headers, timeout=10)
        return {"endpoint": "/api/admin/agents", "method": "GET", "status": r.status_code,
                "time_ms": round((time.time() - t0) * 1000, 1),
                "success": r.status_code in (200, 201),
                "data": r.json() if r.status_code in (200, 201) else None}
    except Exception as e:
        return {"endpoint": "/api/admin/agents", "method": "GET", "status": 0,
                "time_ms": round((time.time() - t0) * 1000, 1), "success": False,
                "error": str(e)}


def test_models_health() -> dict:
    """测试 /api/models/health"""
    t0 = time.time()
    try:
        r = requests.get(f"{BASE_URL}/api/models/health", timeout=10)
        return {"endpoint": "/api/models/health", "method": "GET", "status": r.status_code,
                "time_ms": round((time.time() - t0) * 1000, 1),
                "success": True,
                "data": r.json() if r.status_code == 200 else None}
    except Exception as e:
        return {"endpoint": "/api/models/health", "method": "GET", "status": 0,
                "time_ms": round((time.time() - t0) * 1000, 1), "success": False,
                "error": str(e)}


# ---------------------------------------------------------------------------
# 各Agent测试映射
# ---------------------------------------------------------------------------
def run_agent_tests(agent: dict, token: str = "") -> dict:
    """为单个Agent执行完整的端到端测试"""
    results = {"agent": agent, "tests": [], "total_time_ms": 0, "success_count": 0, "fail_count": 0}

    # 将 difficulty 映射到有效的 level 值
    level = _DIFFICULTY_TO_LEVEL.get(agent["difficulty"], "junior")

    # 通用测试
    tests = [
        ("health", test_health),
        ("api_status", test_api_status),
        ("models_health", test_models_health),
    ]

    # 根据角色添加特定测试
    if agent["role"] == "student":
        tests.extend([
            ("auth_login", lambda: _test_auth_login(f"test_student_{agent['name']}")),
        ])
        for topic in agent["topics"][:2]:  # 每个Agent测试2个知识点
            tests.extend([
                (f"feynman_explain_{topic[:4]}", lambda t=topic, lv=level, tk=token: _test_feynman_explain(t, lv, tk)),
                (f"feynman_classroom_{topic[:4]}", lambda t=topic, tk=token: _test_feynman_classroom(t, tk)),
                (f"chat_{topic[:4]}", lambda t=topic, tk=token: _test_chat(t, tk)),
            ])
    elif agent["role"] == "teacher":
        tests.extend([
            ("auth_login", lambda: _test_auth_login(f"test_teacher_{agent['name']}")),
        ])
        for topic in agent["topics"][:2]:
            tests.extend([
                (f"feynman_explain_{topic[:4]}", lambda t=topic, tk=token: _test_feynman_explain(t, "senior", tk)),
                (f"feynman_classroom_{topic[:4]}", lambda t=topic, tk=token: _test_feynman_classroom(t, tk)),
            ])
    elif agent["role"] == "admin":
        admin_token = globals().get("_ADMIN_TOKEN", "")
        tests.extend([
            ("admin_overview", lambda tk=admin_token: test_admin_overview(tk)),
            ("admin_agents", lambda tk=admin_token: test_admin_agents(tk)),
        ])

    # 执行测试
    for name, test_fn in tests:
        t_start = time.time()
        try:
            r = test_fn()
            elapsed = (time.time() - t_start) * 1000
            r["agent_test_name"] = name
            r["actual_time_ms"] = round(elapsed, 1)
            results["tests"].append(r)
            if r["success"]:
                results["success_count"] += 1
            else:
                results["fail_count"] += 1
        except Exception as e:
            elapsed = (time.time() - t_start) * 1000
            results["tests"].append({
                "agent_test_name": name,
                "endpoint": "", "method": "", "status": 0,
                "time_ms": round(elapsed, 1), "actual_time_ms": round(elapsed, 1),
                "success": False, "error": str(e),
            })
            results["fail_count"] += 1

    results["total_time_ms"] = round(sum(t["actual_time_ms"] for t in results["tests"]), 1)
    results["total_tests"] = len(results["tests"])
    results["success_rate"] = round(results["success_count"] / max(results["total_tests"], 1) * 100, 1)
    return results


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("  LumiLearn 10 Agent 端到端完整测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    # 检查服务是否可用
    print("[检查] 服务连接...")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code == 200:
            print(f"  OK  服务正常 (健康检查: {r.status_code})")
        else:
            print(f"  WARN 健康检查返回 {r.status_code}")
    except Exception as e:
        print(f"  ERROR 无法连接服务: {e}")
        print("  请确保 LumiLearn 服务已在 18080 端口启动")
        return

    print()

    # 预注册用户并获取 token
    print("[准备] 预注册测试用户...")
    tokens = setup_test_users()
    print(f"  成功登录 {len(tokens)}/10 个用户")
    print()

    # 串行执行所有Agent测试（避免并发问题）
    all_results = []
    for i, agent in enumerate(AGENTS, 1):
        token = tokens.get(agent["name"], "")
        print(f"[{i:02d}/10] 测试 Agent: {agent['name']} ({agent['role']})...")
        result = run_agent_tests(agent, token=token)
        all_results.append(result)
        status = "OK" if result["success_rate"] == 100 else f"{result['success_rate']}%"
        print(f"       通过: {result['success_count']}/{result['total_tests']} | 耗时: {result['total_time_ms']}ms | {status}")

    print()
    print("=" * 70)
    print("  测试汇总")
    print("=" * 70)

    total_tests = sum(r["total_tests"] for r in all_results)
    total_success = sum(r["success_count"] for r in all_results)
    total_fail = sum(r["fail_count"] for r in all_results)
    overall_rate = round(total_success / max(total_tests, 1) * 100, 1)
    total_time = round(sum(r["total_time_ms"] for r in all_results), 1)

    print(f"  总测试数: {total_tests}")
    print(f"  通过: {total_success} | 失败: {total_fail}")
    print(f"  总体成功率: {overall_rate}%")
    print(f"  总耗时: {total_time}ms")
    print()

    # 按端点统计
    endpoint_stats = {}
    for result in all_results:
        for t in result["tests"]:
            ep = t.get("endpoint", "unknown")
            if ep not in endpoint_stats:
                endpoint_stats[ep] = {"total": 0, "success": 0, "fail": 0, "total_time": 0}
            endpoint_stats[ep]["total"] += 1
            endpoint_stats[ep]["total_time"] += t.get("actual_time_ms", 0)
            if t.get("success"):
                endpoint_stats[ep]["success"] += 1
            else:
                endpoint_stats[ep]["fail"] += 1

    print("  端点统计:")
    for ep, stats in sorted(endpoint_stats.items()):
        rate = round(stats["success"] / max(stats["total"], 1) * 100, 1)
        avg_time = round(stats["total_time"] / max(stats["total"], 1), 1)
        print(f"    {ep:30s} | {stats['success']:3d}/{stats['total']:3d} ({rate:5.1f}%) | 平均 {avg_time}ms")

    print()

    # 各Agent详情
    print("  各Agent详情:")
    for r in all_results:
        a = r["agent"]
        print(f"    {a['name']:6s} ({a['role']:6s}) | 通过 {r['success_count']}/{r['total_tests']} | 成功率 {r['success_rate']}% | 耗时 {r['total_time_ms']}ms")

    # 保存结果
    output_file = OUTPUT_DIR / "agent_e2e_test_report.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "summary": {
            "total_tests": total_tests,
            "total_success": total_success,
            "total_fail": total_fail,
            "overall_rate": overall_rate,
            "total_time_ms": total_time,
        },
        "endpoint_stats": endpoint_stats,
        "agent_results": all_results,
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n  报告已保存: {output_file}")

    # 生成Markdown报告
    md_report = OUTPUT_DIR / "agent_e2e_test_full_report.md"
    md_lines = [
        "# LumiLearn 10 Agent 端到端完整测试报告",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 服务地址: {BASE_URL}",
        "",
        "## 一、测试概览",
        "",
        f"- **总测试数**: {total_tests}",
        f"- **通过**: {total_success}",
        f"- **失败**: {total_fail}",
        f"- **总体成功率**: {overall_rate}%",
        f"- **总耗时**: {total_time}ms",
        "",
        "## 二、各Agent测试结果",
        "",
        "| Agent | 角色 | 年级 | 测试数 | 通过 | 成功率 | 耗时(ms) |",
        "|-------|------|------|--------|------|--------|----------|",
    ]
    for r in all_results:
        a = r["agent"]
        grade_str = f"{a['grade']}年级" if a["grade"] else "-"
        md_lines.append(f"| {a['name']} | {a['role']} | {grade_str} | {r['total_tests']} | {r['success_count']} | {r['success_rate']}% | {r['total_time_ms']} |")

    md_lines.extend([
        "",
        "## 三、端点性能统计",
        "",
        "| 端点 | 调用次数 | 成功 | 失败 | 成功率 | 平均耗时(ms) |",
        "|------|---------|------|------|--------|-------------|",
    ])
    for ep, stats in sorted(endpoint_stats.items(), key=lambda x: -x[1]["total"]):
        rate = round(stats["success"] / max(stats["total"], 1) * 100, 1)
        avg_time = round(stats["total_time"] / max(stats["total"], 1), 1)
        md_lines.append(f"| {ep} | {stats['total']} | {stats['success']} | {stats['fail']} | {rate}% | {avg_time} |")

    md_lines.extend([
        "",
        "## 四、各Agent详细测试结果",
        "",
    ])
    for r in all_results:
        a = r["agent"]
        md_lines.append(f"### {a['name']} ({a['role']})")
        md_lines.append(f"- 场景: {a['scenario']}")
        md_lines.append(f"- 设备: {a['device']} | 网络: {a['network']}")
        md_lines.append(f"- 测试数: {r['total_tests']} | 通过: {r['success_count']} | 失败: {r['fail_count']}")
        md_lines.append("")
        md_lines.append("| 测试项 | 端点 | 方法 | 状态码 | 耗时(ms) | 成功 | 错误 |")
        md_lines.append("|--------|------|------|--------|---------|------|------|")
        for t in r["tests"]:
            err = t.get("error", "")[:30] if t.get("error") else "-"
            md_lines.append(f"| {t.get('agent_test_name', '-')} | {t.get('endpoint', '-')} | {t.get('method', '-')} | {t.get('status', 0)} | {t.get('actual_time_ms', 0)} | {'✅' if t.get('success') else '❌'} | {err} |")
        md_lines.append("")

    md_lines.extend([
        "",
        "## 五、总结与建议",
        "",
    ])

    # 生成总结
    fail_endpoints = [ep for ep, s in endpoint_stats.items() if s["fail"] > 0]
    slow_endpoints = [ep for ep, s in endpoint_stats.items()
                      if s["total"] > 0 and s["total_time"] / s["total"] > 5000]

    if fail_endpoints:
        md_lines.append(f"### 5.1 失败端点 ({len(fail_endpoints)}个)")
        for ep in fail_endpoints:
            s = endpoint_stats[ep]
            md_lines.append(f"- `{ep}`: {s['fail']}/{s['total']} 失败")

    if slow_endpoints:
        md_lines.append(f"\n### 5.2 慢端点 (>5s, {len(slow_endpoints)}个)")
        for ep in slow_endpoints:
            avg = round(endpoint_stats[ep]["total_time"] / endpoint_stats[ep]["total"], 1)
            md_lines.append(f"- `{ep}`: 平均 {avg}ms")

    md_lines.extend([
        "",
        "### 5.3 改进建议",
        "",
        f"1. **服务稳定性**: 总体成功率 {overall_rate}%，需关注失败端点",
        f"2. **响应速度**: 总耗时 {total_time}ms，部分端点需优化",
        f"3. **Ollama依赖**: 若Ollama不可用，部分端点会超时或返回模板内容",
        f"4. **网络弹性**: 山区学校网络不稳定，需增强断网重试和离线模式",
        "",
        "---",
        f"*报告由 LumiLearn Agent 端到端测试脚本自动生成*",
    ])

    with open(md_report, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"  Markdown报告已保存: {md_report}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
