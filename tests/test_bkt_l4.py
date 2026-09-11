# -*- coding: utf-8 -*-
"""L4 BKT 知识追踪系统 E2E 验证（pytest 化）

修复要点（v0.2.0）：
1. 原实现把所有网络请求与 shutil.rmtree 放在模块导入期执行，导致 pytest 收集阶段
   直接发请求 / 删数据，整套测试无法收集。现改为函数内执行。
2. BKT 的 /student/<sid>/* 接口已加登录与越权守卫，故本测试自行创建临时学生账号、
   登录后带会话访问，结束后清理，不污染业务库。
3. 目标服务不可达时自动 skip（不再报错中断整个测试套件）。

环境变量：
  LUMILEARN_E2E_URL  目标地址，默认 http://localhost:18080
"""
import os
import shutil
import sqlite3
import time

import pytest
import requests

BASE = os.environ.get("LUMILEARN_E2E_URL", "http://localhost:18080").rstrip("/")
TEST_PASS = "LumiE2E1"  # 满足：长度>=8 + 大写 + 数字
# 服务端真实库（绕过 conftest 的临时库重定向）
_PROJECT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lumilearn.db")

PASS = 0
FAIL = 0


def _check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


def _server_alive():
    """探活用轻量静态页（/health 在网关离线时较慢，不适合做存活探测）。"""
    try:
        requests.get(f"{BASE}/", timeout=5)
        return True
    except requests.RequestException:
        return False


def _delete_user(uid):
    """独立 sqlite 连接清理临时账号。"""
    try:
        conn = sqlite3.connect(_PROJECT_DB, timeout=10)
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.commit()
        conn.close()
    except Exception as e:  # pragma: no cover
        print(f"  [清理警告] 删除用户 {uid} 失败: {e}")


def _create_remote_user(uname, password):
    """直接在「服务端真实库」创建临时学生。

    注意：tests/conftest.py 的 autouse fixture 会把 framework.database 的
    LUMILEARN_DB_PATH 重定向到临时库，因此不能用 db.add_user 建号——那样建的
    用户不在运行中的服务端库里，HTTP 登录必然 401。这里用独立 sqlite 连接写真实库。
    """
    from werkzeug.security import generate_password_hash
    conn = sqlite3.connect(_PROJECT_DB, timeout=10)
    try:
        cur = conn.execute(
            "INSERT INTO users (name, role, username, password_hash, is_active) VALUES (?, ?, ?, ?, 1)",
            (uname, "student", uname, generate_password_hash(password)),
        )
        uid = cur.lastrowid
        conn.commit()
        return uid
    finally:
        conn.close()


def test_bkt_l4_e2e():
    global PASS, FAIL
    PASS = FAIL = 0

    if not _server_alive():
        pytest.skip(f"目标服务不可达（{BASE}），跳过 BKT E2E")

    _BKT_DIR = os.environ.get(
        "LUMILEARN_PROGRESS_DIR",
        os.path.join(os.path.dirname(__file__), "..", "data", "bkt_progress"),
    )
    if os.path.isdir(_BKT_DIR):
        shutil.rmtree(_BKT_DIR, ignore_errors=True)
    os.makedirs(_BKT_DIR, exist_ok=True)

    # ---- 准备临时学生账号并登录（须写入服务端真实库）----
    uname = "e2e_bkt_%d" % int(time.time())
    uid = _create_remote_user(uname, TEST_PASS)
    sid = str(uid)
    S = requests.Session()
    try:
        r = S.post(f"{BASE}/api/auth/login", json={"username": uname, "password": TEST_PASS}, timeout=10)
        assert r.status_code == 200 and r.json().get("code") == 0, "临时学生登录失败"

        print("=" * 60)
        print("L4 BKT 知识追踪系统 E2E 验证")
        print("=" * 60)

        # ---- 0. 清除本学生追踪 ----
        print("\n[0] 清除测试追踪")
        r0 = S.post(f"{BASE}/api/learn/student/{sid}/reset", json={}, timeout=10)
        _check("重置请求成功", r0.status_code == 200, f"status={r0.status_code}")
        _check("重置返回成功", r0.json().get("code") == 0, str(r0.json()))
        time.sleep(0.3)

        r0b = S.get(f"{BASE}/api/learn/student/{sid}/status", timeout=10)
        s0 = r0b.json().get("data", {})
        _check("清除后确认状态码200", r0b.status_code == 200)
        _check("清除后总尝试=0", s0.get("total_attempts", -1) == 0, f"attempts={s0.get('total_attempts')}")

        # ---- 1. 知识图谱 ----
        print("\n[1] 知识图谱")
        r = S.get(f"{BASE}/api/learn/knowledge-graph", timeout=10)
        d = r.json()
        _check("状态码 200", r.status_code == 200)
        nodes = d.get("data", {}).get("nodes", [])
        edges = d.get("data", {}).get("edges", [])
        cats = d.get("data", {}).get("categories", [])
        _check("节点数 > 0", len(nodes) > 0, f"nodes={len(nodes)}")
        _check("边数 > 0", len(edges) > 0, f"edges={len(edges)}")
        _check("有分类", len(cats) > 0, f"cats={cats}")

        node_map = {n["id"]: n for n in nodes}
        _check("triangle_basics 存在", "triangle_basics" in node_map)
        if "triangle_basics" in node_map:
            _check("triangle_basics 无前置", len(node_map["triangle_basics"].get("prerequisites", [])) == 0)
        _check("pythagorean 前置有 triangle_basics",
               any(e["from"] == "triangle_basics" and e["to"] == "pythagorean" for e in edges))

        # ---- 2. 知识点详情 ----
        print("\n[2] 知识点详情")
        r2 = S.get(f"{BASE}/api/learn/node/pythagorean", timeout=10)
        d2 = r2.json()
        _check("状态码 200", r2.status_code == 200)
        node = d2.get("data", {})
        _check("有节点名称", node.get("name") == "勾股定理", str(node.get("name")))
        _check("有前置依赖", len(node.get("prerequisites", [])) > 0)
        _check("有后继依赖", len(node.get("dependents", [])) > 0)

        # ---- 3. 学生初始状态 ----
        print("\n[3] 学生初始状态（新用户）")
        r3 = S.get(f"{BASE}/api/learn/student/{sid}/status", timeout=10)
        s = r3.json().get("data", {})
        _check("状态码 200", r3.status_code == 200)
        _check("学生ID正确", s.get("student_id") == sid, str(s.get("student_id")))
        _check("总尝试 = 0", s.get("total_attempts", 0) == 0, f"attempts={s.get('total_attempts')}")
        _check("掌握度 = 0", s.get("overall_mastery", -1) == 0, f"mastery={s.get('overall_mastery')}")
        _check("认知状态未知或novice",
               s.get("cognitive_state", {}).get("state") in ("unknown", "novice"), str(s.get("cognitive_state")))

        # ---- 4. BKT 答题追踪 ----
        print("\n[4] BKT 答题追踪")
        d4a = S.post(f"{BASE}/api/learn/student/{sid}/attempt",
                     json={"node_id": "triangle_basics", "correct": True, "time_spent": 30}, timeout=10).json()
        p1 = d4a["data"]["p"]
        _check("答题1正确=true", d4a.get("data", {}).get("correct") is True)
        _check("答题1后 p > 0.35", p1 > 0.35, f"p={p1}")
        _check("答题1后 p < 1.0", p1 < 1.0, f"p={p1}")

        d4b = S.post(f"{BASE}/api/learn/student/{sid}/attempt",
                     json={"node_id": "triangle_basics", "correct": True, "time_spent": 25}, timeout=10).json()
        p2 = d4b["data"]["p"]
        _check("答题2后 p >= 答题1后 p", p2 >= p1 - 0.001, f"p: {p1} -> {p2}")

        d4c = S.post(f"{BASE}/api/learn/student/{sid}/attempt",
                     json={"node_id": "triangle_basics", "correct": False, "time_spent": 60}, timeout=10).json()
        p3 = d4c["data"]["p"]
        _check("答题3（答错）后 p < 答题2后 p", p3 < p2, f"p: {p2} -> {p3}")
        _check("答题3后预测准确率合理", 0 < d4c["data"].get("predicted_accuracy", 0) < 1)
        cog = d4c["data"].get("cognitive_state", {})
        _check("认知状态有值", cog.get("state") in ("fluent", "confused", "novice", "confident"), str(cog))

        r4d = S.get(f"{BASE}/api/learn/student/{sid}/node/triangle_basics", timeout=10)
        nd = r4d.json().get("data", {})
        _check("单知识点状态200", r4d.status_code == 200)
        _check("总尝试 >= 3", nd.get("total_attempts", 0) >= 3, f"attempts={nd.get('total_attempts')}")
        _check("掌握度在合理区间", 0.5 <= nd.get("p", 0) <= 1.0, f"p={nd.get('p')}")
        _check("预测准确率在合理区间", 0.5 <= nd.get("predicted_accuracy", 0) <= 1.0, f"pa={nd.get('predicted_accuracy')}")

        # ---- 5. 学习路径 ----
        print("\n[5] 学习路径生成")
        r5 = S.get(f"{BASE}/api/learn/student/{sid}/path?max_steps=5", timeout=10)
        path = r5.json().get("data", {}).get("path", [])
        _check("路径状态码200", r5.status_code == 200)
        _check("路径非空", len(path) > 0, f"path_len={len(path)}")
        if path:
            step = path[0]
            _check("路径步骤有 node_id", "node_id" in step)
            _check("路径步骤有 mastery", "mastery" in step)
            _check("路径步骤有 reason", "reason" in step)
            _check("路径步骤有 action", step.get("action") in ("explain", "practice", "test", "review"))

        # ---- 6. 批量答题 ----
        print("\n[6] 批量答题")
        d6 = S.post(f"{BASE}/api/learn/student/{sid}/batch", json={
            "attempts": [
                {"node_id": "triangle_basics", "correct": True, "time_spent": 20},
                {"node_id": "pythagorean", "correct": False, "time_spent": 90},
                {"node_id": "quadratic_formula", "correct": True, "time_spent": 40},
            ]
        }, timeout=10).json()
        sm = d6.get("data", {}).get("summary", {})
        _check("批量总数=3", sm.get("total") == 3)
        _check("批量有效=3", sm.get("valid") == 3)
        _check("批量正确=2", sm.get("correct_count") == 2)
        _check("整体掌握度 > 0", sm.get("overall_mastery", 0) > 0, f"mastery={sm.get('overall_mastery')}")

        # ---- 7. 最终学生状态 ----
        print("\n[7] 最终学生状态")
        s7 = S.get(f"{BASE}/api/learn/student/{sid}/status", timeout=10).json().get("data", {})
        _check("总知识点 > 0", s7.get("total_knowledge_nodes", 0) > 0, f"nodes={s7.get('total_knowledge_nodes')}")
        _check("总尝试 > 0", s7.get("total_attempts", 0) > 0, f"attempts={s7.get('total_attempts')}")
        _check("有认知状态", s7.get("cognitive_state", {}).get("state") != "unknown")

        # ---- 8. 练习题集 ----
        print("\n[8] 练习题集生成")
        d8 = S.post(f"{BASE}/api/learn/student/{sid}/path/practice",
                    json={"node_id": "pythagorean", "count": 3}, timeout=10).json()
        qs = d8.get("data", {}).get("questions", [])
        _check("练习集非空", len(qs) > 0, f"questions={len(qs)}")
        if qs:
            _check("题目有难度", "difficulty" in qs[0])
            _check("题目有提示模式", "hint_mode" in qs[0])

        # ---- 9. 越权守卫（安全） ----
        print("\n[9] 越权守卫")
        other = S.get(f"{BASE}/api/learn/student/999999/status", timeout=10)
        _check("学生访问他人数据 -> 403", other.status_code == 403, f"status={other.status_code}")
        anon = requests.post(f"{BASE}/api/learn/student/{sid}/attempt",
                             json={"node_id": "pythagorean", "correct": True}, timeout=10)
        _check("未登录写入 -> 401", anon.status_code == 401, f"status={anon.status_code}")

        # ---- 10. 重置 ----
        print("\n[10] 重置")
        d9 = S.post(f"{BASE}/api/learn/student/{sid}/reset", json={"node_id": "pythagorean"}, timeout=10).json()
        _check("重置成功", d9.get("data", {}).get("reset") == "pythagorean")

        print("\n" + "=" * 60)
        print(f"结果: {PASS} 通过, {FAIL} 失败")
        print("=" * 60)
        assert FAIL == 0, f"BKT E2E 失败 {FAIL} 项"
    finally:
        _delete_user(uid)
