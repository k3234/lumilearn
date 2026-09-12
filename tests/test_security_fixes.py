# -*- coding: utf-8 -*-
"""安全修复回归测试

覆盖本轮修复的 4 项缺陷，防止回退：
- S1：/api/security/* 敏感读接口（及无鉴权 DELETE）必须要求管理员
- S3：用户登录暴力破解锁定 + 用户 Token 过期生效
- F3：管理员可经统一入口 /api/auth/login 登录（原浏览器登录死锁）
- S4：must_change_password 未改密前拦截管理接口，但放行改密/登出/身份查询

依赖 conftest 的 isolated_db 夹具（每用例独立临时库）。
夹具管理员：admin / TestAdmin2026（must_change_password=0）。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash  # noqa: E402

from framework.admin import auth as admin_auth  # noqa: E402
from framework.api.server import create_app  # noqa: E402
from framework.database import db  # noqa: E402


class TestSecurityFixes(unittest.TestCase):
    def setUp(self):
        # 隔离库由 conftest 的 autouse 夹具准备好了，此处确保单例指向它
        admin_auth._auth_instance = None
        self.app = create_app()
        self.app.config["TESTING"] = True

    # ---------------- S1：安全接口鉴权 ----------------
    def test_s1_security_read_endpoints_require_admin(self):
        """/api/security/* 敏感读接口未登录必须 401（此前裸奔）"""
        with self.app.test_client() as c:
            for path in (
                "/api/security/status",
                "/api/security/gateway/stats",
                "/api/security/gateway/logs",
                "/api/security/firewall/rules",
                "/api/security/recommendations",
            ):
                self.assertEqual(c.get(path).status_code, 401, f"{path} 应 401")

    def test_s1_firewall_delete_requires_admin(self):
        """DELETE 防火墙规则是写操作，未登录必须 401（此前无鉴权）"""
        with self.app.test_client() as c:
            r = c.delete("/api/security/firewall/rules/any-rule-id")
            self.assertEqual(r.status_code, 401)

    def test_s1_firewall_check_requires_admin(self):
        with self.app.test_client() as c:
            r = c.post("/api/security/firewall/check", json={"ip": "127.0.0.1", "port": 18080})
            self.assertEqual(r.status_code, 401)

    # ---------------- S3：暴力破解锁定 + Token TTL ----------------
    def test_s3_login_lockout_after_repeated_failures(self):
        """同一 IP+用户名 连续 5 次失败后锁定，第 6 次返回 429"""
        with self.app.test_client() as c:
            uname = "regress_lockout_user"
            for _ in range(5):
                self.assertEqual(
                    c.post("/api/auth/login", json={"username": uname, "password": "bad"}).status_code,
                    401,
                )
            r6 = c.post("/api/auth/login", json={"username": uname, "password": "bad"})
            self.assertEqual(r6.status_code, 429)

    def test_s3_expired_token_rejected(self):
        """Token 定义了 12h TTL，过期后必须失效并被清理"""
        from framework.api.routes import auth as auth_mod

        # 预置对应 user 记录（get_user_by_token 会回查 users 表）
        db.conn.execute(
            "INSERT OR IGNORE INTO users (id, name, role) VALUES (987654, 'ttl_user', 'student')"
        )
        db.conn.commit()

        tok = auth_mod._issue_token(
            {"id": 987654, "name": "ttl_user", "username": "ttl_user", "role": "user"}
        )
        self.assertIsNotNone(auth_mod.get_user_by_token(tok))
        # 强制过期
        with auth_mod._TOKENS_LOCK:
            auth_mod._TOKENS[tok]["expires_at"] = 1
        self.assertIsNone(auth_mod.get_user_by_token(tok))
        self.assertNotIn(tok, auth_mod._TOKENS)

    # ---------------- F3：管理员统一入口登录 ----------------
    def test_f3_admin_can_login_through_unified_entry(self):
        """管理员可经 /api/auth/login 登录并拿到后台令牌（原死锁点）"""
        with self.app.test_client() as c:
            r = c.post("/api/auth/login", json={"username": "admin", "password": "TestAdmin2026"})
            self.assertEqual(r.status_code, 200)
            j = r.get_json()
            self.assertTrue(j.get("success"))
            self.assertTrue(j.get("admin_token"))
            self.assertEqual((j.get("user") or {}).get("role"), "super_admin")

    def test_f3_admin_session_passes_page_guard(self):
        """登录后访问 /admin 不应被 302 弹回首页，且 /api/auth/me 能识别"""
        with self.app.test_client() as c:
            c.post("/api/auth/login", json={"username": "admin", "password": "TestAdmin2026"})
            self.assertEqual(c.get("/admin").status_code, 200)
            rm = c.get("/api/auth/me")
            self.assertEqual(rm.status_code, 200)
            self.assertEqual((rm.get_json().get("user") or {}).get("role"), "super_admin")

    # ---------------- S4：强制改密拦截 ----------------
    def _add_pending_admin(self):
        """创建一个 must_change_password=1 的管理员，模拟首次登录"""
        if not db.get_admin_by_username("pending_admin"):
            db.add_admin(
                "pending_admin",
                generate_password_hash("PendingInit2026"),
                display_name="待改密管理员",
                role="super_admin",
                must_change_password=1,
            )
            db.conn.commit()

    def test_s4_blocks_business_endpoints_until_password_changed(self):
        self._add_pending_admin()
        with self.app.test_client() as c:
            r = c.post("/api/admin/login",
                       json={"username": "pending_admin", "password": "PendingInit2026"})
            self.assertEqual(r.status_code, 200)
            token = r.get_json()["token"]
            h = {"X-Admin-Token": token}

            # 未改密：业务接口 403，并带回 must_change_password 标志
            blocked = c.get("/api/admin/overview", headers=h)
            self.assertEqual(blocked.status_code, 403)
            self.assertTrue((blocked.get_json() or {}).get("must_change_password"))

            # 身份查询与改密端点必须放行，否则形成新死锁
            self.assertEqual(c.get("/api/admin/me", headers=h).status_code, 200)
            rp = c.post("/api/admin/password", headers=h,
                        json={"old_password": "PendingInit2026",
                              "new_password": "PendingNew2026"})
            self.assertEqual(rp.status_code, 200)
            self.assertTrue((rp.get_json() or {}).get("success"))

            # 改密后恢复访问
            self.assertEqual(c.get("/api/admin/overview", headers=h).status_code, 200)


if __name__ == "__main__":
    unittest.main()
