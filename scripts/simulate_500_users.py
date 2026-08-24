#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 500用户模拟测试脚本
使用CookieJar保持登录会话，模拟真实用户访问各服务
"""

import json
import time
import random
import statistics
import http.cookiejar
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 目标服务主机地址：通过环境变量 LUMILEARN_BASE_URL 指定，默认本机回环地址
# （切勿将真实内网/公网 IP 或服务器地址硬编码提交到公开仓库）
BASE_URL = os.environ.get("LUMILEARN_BASE_URL", "http://localhost")

TOPICS = {
    "数学": [
        "函数的单调性与奇偶性", "导数的几何意义", "数列的通项公式",
        "三角函数的图像与性质", "向量的数量积", "椭圆的标准方程",
        "复数的四则运算", "二项式定理", "排列组合应用题",
        "空间向量与立体几何", "概率分布与期望", "极限与连续",
        "定积分的应用", "微分方程入门", "矩阵与线性方程组"
    ],
    "物理": [
        "牛顿第二定律的推导", "动能定理的应用", "动量守恒定律",
        "电场强度的计算", "电磁感应现象", "光的折射与全反射",
        "简谐运动的周期", "理想气体状态方程", "热力学第二定律",
        "波的干涉与衍射", "相对论基础概念", "量子化能量概念"
    ],
    "化学": [
        "酸碱中和反应原理", "氧化还原反应配平", "化学平衡移动",
        "原电池工作原理", "有机物的同分异构体", "元素周期律应用",
        "化学反应速率影响因素", "盐类的水解", "金属的冶炼方法",
        "酯化反应机理", "高分子化合物合成", "电化学腐蚀防护"
    ],
    "生物": [
        "光合作用的过程", "细胞呼吸的类型", "遗传规律的运用",
        "DNA双螺旋结构", "基因突变与进化", "生态系统的能量流动",
        "免疫系统的功能", "神经调节机制", "植物激素调节",
        "种群的数量特征", "群落演替过程", "生物多样性保护"
    ],
    "语文": [
        "古诗词鉴赏方法", "议论文论证技巧", "现代文阅读理解",
        "文言文实词虚词", "作文立意与结构", "修辞手法的运用",
        "文学常识积累", "名著阅读心得", "语言表达连贯",
        "诗歌意象分析", "散文赏析要点", "应用文写作规范"
    ],
    "英语": [
        "时态语态的综合运用", "定语从句的引导词", "非谓语动词用法",
        "阅读理解技巧", "完形填空解题方法", "书面表达模板",
        "听力理解策略", "词汇记忆方法", "句型转换练习",
        "虚拟语气用法", "宾语从句顺序", "情景对话应答"
    ]
}

GRADES = ["高一", "高二", "高三"]
CLASSES = ["(1)班", "(2)班", "(3)班", "(4)班", "(5)班"]
GENDERS = ["男", "女"]
SURNAMES = ["张", "李", "王", "刘", "陈", "杨", "赵", "黄", "周", "吴",
            "孙", "马", "朱", "胡", "郭", "何", "林", "罗", "梁", "宋",
            "唐", "许", "韩", "冯", "邓", "曹", "彭", "曾", "萧", "田"]
FIRST_NAMES = ["伟", "芳", "娜", "秀英", "敏", "静", "丽", "强", "磊", "洋",
               "勇", "艳", "杰", "涛", "明", "超", "秀兰", "霞", "平", "辉",
               "鹏", "芬", "玲", "欣", "宇", "轩", "浩", "然", "晨", "鑫"]


def make_opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPHandler
    )


def post_json(opener, url, data, headers=None, timeout=15):
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=hdrs)
    try:
        resp = opener.open(req, timeout=timeout)
        return resp, json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
        except Exception:
            err_body = {}
        return e, err_body, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return None, None, str(e)


def get_json(opener, url, timeout=10):
    try:
        resp = opener.open(url, timeout=timeout)
        return resp, json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        return e, {}, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return None, {}, str(e)


def main():
    print("=" * 60)
    print("LumiLearn 500用户模拟测试")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ── 1. 获取admin token ──────────────────────────────────────
    print("\n[1/5] 获取管理员token...")
    admin_opener = make_opener()
    admin_user = os.environ.get("LUMILEARN_ADMIN_USER", "admin")
    admin_pass = os.environ.get("LUMILEARN_ADMIN_PASS", "admin123")
    _, token_body, err = post_json(admin_opener, f"{BASE_URL}:18081/api/admin/login",
                                    {"username": admin_user, "password": admin_pass})
    if err:
        print(f"  ERROR: {err}")
        return
    admin_token = token_body.get("token", "")
    print(f"  token获取成功，长度={len(admin_token)}")

    # ── 2. 获取现有用户 ─────────────────────────────────────────
    print("\n[2/5] 获取已有用户列表...")
    _, users_body, err = get_json(admin_opener, f"{BASE_URL}:18081/api/admin/users")
    if err:
        print(f"  ERROR: {err}")
        return
    all_existing = users_body.get("users", [])
    student_users = [u for u in all_existing if u.get("role") == "student"]
    print(f"  现有用户: {len(all_existing)}，学生: {len(student_users)}")

    # ── 3. 补齐到500用户 ────────────────────────────────────────
    needed = 500 - len(student_users)
    if needed > 0:
        print(f"\n[2b/5] 创建 {needed} 个测试用户...")
        t0 = time.time()
        created_opener = make_opener()
        created = []
        for i in range(1, needed + 1):
            sn = random.choice(SURNAMES)
            fn = random.choice(FIRST_NAMES)
            uname = f"user{i:04d}"
            pwd = f"pass{i:04d}"
            subj = random.choice(list(TOPICS.keys()))
            _, body, err = post_json(created_opener, f"{BASE_URL}:18081/api/admin/users", {
                "username": uname, "password": pwd, "name": sn + fn,
                "role": "student", "subject": subj,
                "grade": random.choice(GRADES),
                "class": random.choice(CLASSES),
                "gender": random.choice(GENDERS)
            }, headers={"X-Admin-Token": admin_token})
            if err:
                created.append({"user_id": None, "username": uname, "error": err})
            else:
                uid = (body.get("user") or {}).get("id")
                created.append({"user_id": uid, "username": uname, "password": pwd, "subject": subj})
        ct = time.time() - t0
        ok_cnt = sum(1 for u in created if u.get("user_id"))
        print(f"  创建成功: {ok_cnt}/{needed}，耗时: {ct:.1f}s")
    else:
        created = []
        ct = 0

    # 组装最终用户列表（统一结构）
    final_users = []
    for u in student_users:
        final_users.append({
            "user_id": u.get("id"),
            "username": u.get("username") or u.get("name"),
            "name": u.get("name"),
            "password": "",  # 后续批量重置
            "subject": u.get("subject", random.choice(list(TOPICS.keys()))),
            "grade": u.get("grade", random.choice(GRADES)),
        })
    for u in created:
        if u.get("user_id"):
            final_users.append({
                "user_id": u["user_id"],
                "username": u["username"],
                "name": u.get("name", u["username"]),
                "password": u.get("password", ""),
                "subject": u.get("subject", "数学"),
                "grade": u.get("grade", "高二"),
            })

    final_users = final_users[:500]
    print(f"  用户总数: {len(final_users)}")

    # ── 4. 批量重置密码 ─────────────────────────────────────────
    print("\n[3/5] 批量重置用户密码...")
    t0 = time.time()
    reset_ok = 0
    for idx, u in enumerate(final_users):
        if not u["password"]:
            pwd = f"test{idx+1:04d}pass"
            url = f"{BASE_URL}:18081/api/admin/users/{u['user_id']}/password"
            body_data = json.dumps({"password": pwd}).encode()
            req = urllib.request.Request(url, data=body_data,
                                          headers={"Content-Type": "application/json",
                                                   "X-Admin-Token": admin_token},
                                          method="POST")
            try:
                resp = admin_opener.open(req, timeout=10)
                result = json.loads(resp.read().decode())
                if result.get("success"):
                    u["password"] = pwd
                    reset_ok += 1
            except Exception:
                pass
    rt = time.time() - t0
    print(f"  密码重置: {reset_ok}/{len(final_users)}，耗时: {rt:.1f}s")

    # ── 5. 并发模拟用户访问 ─────────────────────────────────────
    print(f"\n[4/5] 并发模拟 {len(final_users)} 用户访问各服务...")
    results = []
    lock = None  # 线程安全由results.append保证（CPython GIL）

    def simulate_one(user, idx):
        sess = {
            "user_idx": idx, "username": user["username"],
            "name": user["name"],
            "subject": user.get("subject", "数学"),
            "grade": user.get("grade", "高二"), "steps": []
        }
        op = make_opener()
        subj = sess["subject"]
        topics = TOPICS.get(subj, TOPICS["数学"])
        uname = user["username"]
        pwd = user["password"]

        # Step 1: 健康检查
        t0 = time.time()
        _, _, err = get_json(op, f"{BASE_URL}:18081/api/health")
        sess["steps"].append({"step": "health_check", "latency_ms": round((time.time()-t0)*1000,1), "error": err})

        # Step 2: 框架状态
        t0 = time.time()
        _, _, err = get_json(op, f"{BASE_URL}:18081/api/framework")
        sess["steps"].append({"step": "framework_status", "latency_ms": round((time.time()-t0)*1000,1), "error": err})

        # Step 3: 模型列表
        t0 = time.time()
        _, mbody, err = get_json(op, f"{BASE_URL}:11434/api/tags")
        mc = len((mbody or {}).get("models", [])) if not err else 0
        sess["steps"].append({"step": "model_list", "model_count": mc,
                               "latency_ms": round((time.time()-t0)*1000,1), "error": err})

        # Step 4: 用户登录（学习平台端口5000）
        t0 = time.time()
        _, lbody, err = post_json(op, f"{BASE_URL}:5000/api/login",
                                   {"username": uname, "password": pwd})
        login_ok = (err is None and (lbody or {}).get("success"))
        sess["steps"].append({"step": "login", "success": login_ok,
                               "latency_ms": round((time.time()-t0)*1000,1), "error": err})
        if err or not login_ok:
            results.append(sess)
            return sess

        # Step 5: 获取当前用户
        t0 = time.time()
        _, _, err = get_json(op, f"{BASE_URL}:5000/api/me")
        sess["steps"].append({"step": "get_user_info", "latency_ms": round((time.time()-t0)*1000,1), "error": err})

        # Step 6: 学习请求
        learn_topic = random.choice(topics)
        difficulty = random.choice(["基础", "中等", "进阶"])
        t0 = time.time()
        _, lbody, err = post_json(op, f"{BASE_URL}:5000/api/learn",
                                   {"topic": learn_topic, "subject": subj, "level": difficulty},
                                   timeout=30)
        mastery = 0
        scount = 0
        if err is None:
            mastery = ((lbody or {}).get("mastery_assessment") or {}).get("score", 0)
            scount = len((lbody or {}).get("flow", []))
        sess["steps"].append({"step": "learn_request", "topic": learn_topic,
                               "difficulty": difficulty, "mastery_score": mastery,
                               "steps_count": scount,
                               "latency_ms": round((time.time()-t0)*1000,1), "error": err})

        # Step 7: 多Agent协作（50%概率）
        if random.random() < 0.5:
            ma_topic = random.choice(topics)
            t0 = time.time()
            _, ma_body, err = post_json(op, f"{BASE_URL}:5000/api/multi-agent",
                                         {"topic": ma_topic, "subject": subj}, timeout=30)
            ma_steps = len((ma_body or {}).get("flow", [])) if err is None else 0
            sess["steps"].append({"step": "multi_agent", "topic": ma_topic,
                                   "steps_count": ma_steps,
                                   "latency_ms": round((time.time()-t0)*1000,1), "error": err})

        # Step 8: 学习历史
        t0 = time.time()
        _, hbody, err = get_json(op, f"{BASE_URL}:5000/api/history")
        hcnt = len((hbody or {}).get("reports", [])) if err is None else 0
        sess["steps"].append({"step": "history", "record_count": hcnt,
                               "latency_ms": round((time.time()-t0)*1000,1), "error": err})

        # Step 9: 学习状态
        t0 = time.time()
        _, sbody, err = get_json(op, f"{BASE_URL}:5000/api/status")
        ollama_ok = (sbody or {}).get("ollama_available", False) if err is None else False
        sess["steps"].append({"step": "learn_status", "ollama_available": ollama_ok,
                               "latency_ms": round((time.time()-t0)*1000,1), "error": err})

        # Step 10: 聊天
        chat_msg = f"请帮我学习{learn_topic}"
        t0 = time.time()
        _, cbody, err = post_json(op, f"{BASE_URL}:5000/api/chat",
                                   {"message": chat_msg}, timeout=15)
        rlen = len((cbody or {}).get("reply", "")) if err is None else 0
        sess["steps"].append({"step": "chat", "reply_length": rlen,
                               "latency_ms": round((time.time()-t0)*1000,1), "error": err})

        # 退出登录
        post_json(op, f"{BASE_URL}:5000/api/logout", {})
        results.append(sess)
        return sess

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(simulate_one, u, i+1) for i, u in enumerate(final_users)]
        for f in as_completed(futures):
            pass
    sim_time = time.time() - t0
    print(f"  模拟完成，耗时: {sim_time:.1f}s，吞吐: {len(final_users)/sim_time:.1f} 用户/秒")

    # ── 6. 统计分析 ─────────────────────────────────────────────
    print("\n[5/5] 统计分析...")
    all_lat = []
    cnt = {"health":0, "login":0, "learn":0, "multi_agent":0,
           "history":0, "chat":0, "learn_status":0}
    mastery_scores = []
    subj_dist = {}
    topic_dist = {}
    err_sum = {}
    multi_total = 0

    for r in results:
        for s in r["steps"]:
            lat = s.get("latency_ms")
            if lat is not None:
                all_lat.append(lat)
            sn = s["step"]
            err = s.get("error")
            if err:
                ek = err[:80]
                err_sum[ek] = err_sum.get(ek, 0) + 1
            if sn == "health_check" and not err:
                cnt["health"] += 1
            if sn == "login" and s.get("success"):
                cnt["login"] += 1
            if sn == "learn_request" and not err:
                cnt["learn"] += 1
                mastery_scores.append(s.get("mastery_score", 0))
            if sn == "multi_agent":
                multi_total += 1
                if not err:
                    cnt["multi_agent"] += 1
            if sn == "history" and not err:
                cnt["history"] += 1
            if sn == "chat" and not err:
                cnt["chat"] += 1
            if sn == "learn_status" and not err:
                cnt["learn_status"] += 1
        subj = r.get("subject", "未知")
        subj_dist[subj] = subj_dist.get(subj, 0) + 1
        for s in r["steps"]:
            if s["step"] == "learn_request" and s.get("topic") and not s.get("error"):
                topic_dist[s["topic"]] = topic_dist.get(s["topic"], 0) + 1

    n = len(all_lat)
    if n:
        all_lat.sort()
        p50 = all_lat[int(n*0.5)]; p90 = all_lat[int(n*0.9)]
        p95 = all_lat[int(n*0.95)]; p99 = all_lat[int(n*0.99)]
        avg_lat = statistics.mean(all_lat)
        max_lat = max(all_lat); min_lat = min(all_lat)
    else:
        p50=p90=p95=p99=avg_lat=max_lat=min_lat=0

    avg_m = statistics.mean(mastery_scores) if mastery_scores else 0
    min_m = min(mastery_scores) if mastery_scores else 0
    max_m = max(mastery_scores) if mastery_scores else 0

    # ── 7. 生成报告 ─────────────────────────────────────────────
    report = {
        "test_info": {
            "test_name": "500用户并发模拟测试",
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_users": len(final_users),
            "simulation_time_s": round(sim_time, 1),
            "throughput_users_per_sec": round(len(final_users)/sim_time, 1)
        },
        "api_success_rates": {
            "health_check":   {"total": len(final_users), "ok": cnt["health"],
                                "rate": f"{cnt['health']/len(final_users)*100:.1f}%"},
            "login":          {"total": len(final_users), "ok": cnt["login"],
                                "rate": f"{cnt['login']/len(final_users)*100:.1f}%"},
            "learn":          {"total": len(final_users), "ok": cnt["learn"],
                                "rate": f"{cnt['learn']/len(final_users)*100:.1f}%"},
            "multi_agent":    {"total": multi_total, "ok": cnt["multi_agent"],
                                "rate": f"{cnt['multi_agent']/max(1,multi_total)*100:.1f}%" if multi_total else "N/A"},
            "history":        {"total": len(final_users), "ok": cnt["history"],
                                "rate": f"{cnt['history']/len(final_users)*100:.1f}%"},
            "chat":           {"total": len(final_users), "ok": cnt["chat"],
                                "rate": f"{cnt['chat']/len(final_users)*100:.1f}%"},
            "learn_status":    {"total": len(final_users), "ok": cnt["learn_status"],
                                "rate": f"{cnt['learn_status']/len(final_users)*100:.1f}%"}
        },
        "latency_stats": {
            "avg_ms": round(avg_lat,1), "p50_ms": round(p50,1),
            "p90_ms": round(p90,1), "p95_ms": round(p95,1),
            "p99_ms": round(p99,1), "max_ms": round(max_lat,1), "min_ms": round(min_lat,1)
        },
        "mastery_stats": {
            "avg": round(avg_m,1), "min": min_m, "max": max_m,
            "sample_count": len(mastery_scores)
        },
        "subject_distribution": subj_dist,
        "top_10_topics": dict(sorted(topic_dist.items(), key=lambda x: -x[1])[:10]),
        "error_summary": dict(sorted(err_sum.items(), key=lambda x: -x[1])[:10]),
        "sample_users": results[:5],
        "all_results": results
    }

    out_path = "docs/test-500users-report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n测试报告已保存: {out_path}")

    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    print(f"用户总数: {len(final_users)}")
    print(f"登录成功率: {cnt['login']}/{len(final_users)} ({cnt['login']/len(final_users)*100:.1f}%)")
    print(f"学习请求成功率: {cnt['learn']}/{len(final_users)} ({cnt['learn']/len(final_users)*100:.1f}%)")
    print(f"多Agent成功率: {cnt['multi_agent']}/{multi_total} ({cnt['multi_agent']/max(1,multi_total)*100:.1f}%)")
    print(f"历史查询成功率: {cnt['history']}/{len(final_users)} ({cnt['history']/len(final_users)*100:.1f}%)")
    print(f"平均响应时间: {avg_lat:.1f}ms")
    print(f"P50={p50:.1f}ms P90={p90:.1f}ms P95={p95:.1f}ms P99={p99:.1f}ms Max={max_lat:.1f}ms")
    print(f"平均掌握度: {avg_m:.1f} (样本{len(mastery_scores)})")
    print(f"学科分布: {subj_dist}")
    print(f"错误类型: {len(err_sum)} 种")
    for e, c in list(err_sum.items())[:5]:
        print(f"  - {e} ({c}次)")
    print("=" * 60)


if __name__ == "__main__":
    main()
