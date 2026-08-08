#!/usr/bin/env python3
"""
鲁棒性测试 + 管理员功能测试
- 随机提问含错别字、语法错误、不完整问题
- 测试管理员 API（登录、用户管理、模型管理、Agent 管理）
"""
import sys, os, time, json, requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.api.server import create_app

print("=" * 70)
print("  LumiLearn 鲁棒性 + 管理员功能测试")
print("=" * 70)

# ─── 1. 鲁棒性测试 ──────────────────────────────────────────────────────────
print("\n【1/2】鲁棒性测试（含错别字、语法错误、不完整问题）")
print("-" * 70)

robustness_tests = [
    ("错别字 - 勾股定理", "帮偶讲讲勾股定理，a方加b方等c方是啥意思"),
    ("错别字 - 化学键", "离子键和共价键有啥区别？能举几个例字吗"),
    ("语法错误", "牛顿第二定律F等于ma怎么用举例说明"),
    ("不完整问题", "光合作用"),
    ("口语化表达", "老师那个啥就是化学键那个东西是咋回事儿啊"),
    ("中英文混杂", "Explain the function of mitochondria in simple terms"),
    ("超长问题", "请用费曼五步法详细讲解勾股定理的定义历史证明方法应用场景以及在中考高考中的出题方式和解题技巧"),
    ("特殊字符", "勾股定理a²+b²=c²中，如果a=3,b=4那么c等于多少？"),
    ("重复提问", "勾股定理勾股定理勾股定理"),
    ("模糊表达", "就是那个三角形的东西"),
]

results_robust = []
for desc, question in robustness_tests:
    try:
        t0 = time.time()
        r = requests.post(
            "http://localhost:5000/api/learn",
            json={"topic": question, "user_id": 99},
            timeout=300
        )
        elapsed = time.time() - t0
        if r.status_code == 200:
            data = r.json()
            steps = data.get("teaching_flow", {})
            completed = steps.get("completed_steps", 0)
            total = steps.get("total_steps", 0)
            mastery = data.get("mastery_assessment", {}).get("level", "N/A")
            results_robust.append({
                "desc": desc,
                "success": completed == total,
                "steps": f"{completed}/{total}",
                "mastery": mastery,
                "elapsed": elapsed,
            })
            status = "✅" if completed == total else "⚠️"
            print(f"   {status} {desc[:20]:<20} → {completed}/{total} 步, {mastery}, {elapsed:.1f}s")
        else:
            results_robust.append({"desc": desc, "success": False, "error": f"HTTP {r.status_code}"})
            print(f"   ❌ {desc[:20]:<20} → HTTP {r.status_code}")
    except Exception as e:
        results_robust.append({"desc": desc, "success": False, "error": str(e)[:50]})
        print(f"   ❌ {desc[:20]:<20} → {str(e)[:50]}")

robust_passed = sum(1 for r in results_robust if r.get("success"))
print(f"\n   鲁棒性通过率: {robust_passed}/{len(results_robust)} ({robust_passed/len(results_robust)*100:.0f}%)")

# ─── 2. 管理员功能测试 ──────────────────────────────────────────────────────
print("\n【2/2】管理员功能测试")
print("-" * 70)

app = create_app()
app.config["TESTING"] = True
client = app.test_client()

admin_results = []

def admin_request(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Admin-Token"] = token
    if method == "GET":
        return client.get(path, headers=headers)
    elif method == "POST":
        return client.post(path, json=data, headers=headers)
    elif method == "DELETE":
        return client.delete(path, headers=headers)

# 2.1 登录测试
print("\n  [2.1] 管理员登录")
resp = admin_request("POST", "/api/admin/login", {"username": "admin", "password": "admin123"})
login_ok = resp.status_code == 200
token = resp.get_json().get("token", "") if login_ok else ""
print(f"     正常登录: {'✅' if login_ok else '❌'} (HTTP {resp.status_code})")

resp = admin_request("POST", "/api/admin/login", {"username": "admin", "password": "wrong"})
print(f"     错误密码: {'✅ 返回401' if resp.status_code == 401 else '❌'} (HTTP {resp.status_code})")

resp = admin_request("POST", "/api/admin/login", {"username": "nobody", "password": "x"})
print(f"     不存在用户: {'✅ 返回401' if resp.status_code == 401 else '❌'} (HTTP {resp.status_code})")

admin_results.append(("管理员登录", login_ok))

# 2.2 权限检查
print("\n  [2.2] 权限检查")
resp = client.get("/api/admin/me")
no_auth = resp.status_code == 401
print(f"     无token访问: {'✅ 返回401' if no_auth else '❌'} (HTTP {resp.status_code})")
admin_results.append(("权限检查", no_auth))

# 2.3 获取当前管理员信息
print("\n  [2.3] 管理员信息")
resp = admin_request("GET", "/api/admin/me", token=token)
me_ok = resp.status_code == 200 and resp.get_json().get("admin", {}).get("username") == "admin"
print(f"     获取当前用户: {'✅' if me_ok else '❌'} (HTTP {resp.status_code})")
admin_results.append(("获取管理员信息", me_ok))

# 2.4 系统总览
print("\n  [2.4] 系统总览")
resp = admin_request("GET", "/api/admin/overview", token=token)
overview_ok = resp.status_code == 200
data = resp.get_json() if resp.status_code == 200 else {}
stats = data.get("stats", {})
print(f"     HTTP: {'✅' if overview_ok else '❌'} (HTTP {resp.status_code})")
if overview_ok:
    print(f"     统计: users={stats.get('total_users',0)}, sessions={stats.get('total_sessions',0)}")
admin_results.append(("系统总览", overview_ok))

# 2.5 用户管理
print("\n  [2.5] 用户管理")
resp = admin_request("GET", "/api/admin/users", token=token)
list_users_ok = resp.status_code == 200
users = resp.get_json().get("users", []) if resp.status_code == 200 else []
print(f"     用户列表: {'✅' if list_users_ok else '❌'} ({len(users)} 个用户)")

resp = admin_request("POST", "/api/admin/users", {"name": "测试用户", "role": "student"}, token=token)
create_user_ok = resp.status_code == 200
new_user = resp.get_json().get("user", {}) if create_user_ok else {}
new_user_id = new_user.get("id") if create_user_ok else None
print(f"     创建用户: {'✅' if create_user_ok else '❌'} (id={new_user_id})")

if new_user_id:
    resp = admin_request("DELETE", f"/api/admin/users/{new_user_id}", token=token)
    delete_user_ok = resp.status_code == 200
    print(f"     删除用户: {'✅' if delete_user_ok else '❌'} (HTTP {resp.status_code})")
else:
    delete_user_ok = False
admin_results.append(("用户管理", list_users_ok and create_user_ok and delete_user_ok))

# 2.6 模型管理
print("\n  [2.6] 模型管理")
resp = admin_request("GET", "/api/admin/models", token=token)
list_models_ok = resp.status_code == 200
models = resp.get_json().get("models", []) if resp.status_code == 200 else []
print(f"     模型列表: {'✅' if list_models_ok else '❌'} ({len(models)} 个模型)")
admin_results.append(("模型管理", list_models_ok))

# 2.7 Agent 管理
print("\n  [2.7] Agent 管理")
resp = admin_request("GET", "/api/admin/agents", token=token)
list_agents_ok = resp.status_code == 200
agents = resp.get_json().get("agents", []) if resp.status_code == 200 else []
print(f"     Agent列表: {'✅' if list_agents_ok else '❌'} ({len(agents)} 个Agent)")

resp = admin_request("GET", "/api/admin/agents/health", token=token)
health_ok = resp.status_code == 200
print(f"     Agent健康: {'✅' if health_ok else '❌'} (HTTP {resp.status_code})")
admin_results.append(("Agent管理", list_agents_ok and health_ok))

# 2.8 API Key 管理（修复：api_key 是顶层字段）
print("\n  [2.8] API Key 管理")
resp = admin_request("GET", "/api/admin/api-keys", token=token)
list_keys_ok = resp.status_code == 200
keys = resp.get_json().get("api_keys", []) if resp.status_code == 200 else []
print(f"     API Key列表: {'✅' if list_keys_ok else '❌'} ({len(keys)} 个Key)")

# 修复：API 返回 {"success": True, "id": ..., "key_name": ..., "api_key": ..., "scope": ...}
resp = admin_request("POST", "/api/admin/api-keys", {"key_name": "测试Key", "scope": "read"}, token=token)
create_key_ok = resp.status_code == 200
new_key_data = resp.get_json() if create_key_ok else {}
new_api_key = new_key_data.get("api_key") if create_key_ok else None
print(f"     创建API Key: {'✅' if create_key_ok else '❌'} (key={new_api_key[:8] if new_api_key else 'None'}...)")

if new_api_key:
    resp = admin_request("DELETE", f"/api/admin/api-keys/{new_api_key}", token=token)
    delete_key_ok = resp.status_code == 200
    print(f"     删除API Key: {'✅' if delete_key_ok else '❌'} (HTTP {resp.status_code})")
else:
    delete_key_ok = False
admin_results.append(("API Key管理", list_keys_ok and create_key_ok and delete_key_ok))

# 2.9 日志管理
print("\n  [2.9] 日志管理")
resp = admin_request("GET", "/api/admin/logs", token=token)
logs_ok = resp.status_code == 200
print(f"     日志列表: {'✅' if logs_ok else '❌'} (HTTP {resp.status_code})")
admin_results.append(("日志管理", logs_ok))

# 2.10 修改密码
print("\n  [2.10] 修改密码")
resp = admin_request("POST", "/api/admin/password",
                     {"old_password": "admin123", "new_password": "admin123"}, token=token)
change_pwd_ok = resp.status_code == 200
print(f"     修改密码: {'✅' if change_pwd_ok else '❌'} (HTTP {resp.status_code})")
admin_results.append(("修改密码", change_pwd_ok))

# ─── 汇总 ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  📊 测试汇总")
print("=" * 70)

print("\n  【鲁棒性测试】")
print(f"     通过率: {robust_passed}/{len(results_robust)} ({robust_passed/len(results_robust)*100:.0f}%)")
for r in results_robust:
    status = "✅" if r.get("success") else "❌"
    print(f"     {status} {r['desc'][:25]}")

print("\n  【管理员功能测试】")
admin_passed = sum(1 for _, ok in admin_results if ok)
print(f"     通过率: {admin_passed}/{len(admin_results)} ({admin_passed/len(admin_results)*100:.0f}%)")
for name, ok in admin_results:
    print(f"     {'✅' if ok else '❌'} {name}")

total_passed = robust_passed + admin_passed
total_all = len(results_robust) + len(admin_results)
print(f"\n     总通过率: {total_passed}/{total_all} ({total_passed/total_all*100:.0f}%)")

print(f"\n{'=' * 70}")
if robust_passed == len(results_robust) and admin_passed == len(admin_results):
    print("  🎉 全部测试通过！系统鲁棒性和管理员功能正常")
else:
    print("  ⚠️ 部分测试失败，请检查上述结果")
print(f"{'=' * 70}")
