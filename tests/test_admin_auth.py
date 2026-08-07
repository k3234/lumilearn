# -*- coding: utf-8 -*-
"""管理员认证测试"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.admin.auth import get_admin_auth


class TestAdminAuth(unittest.TestCase):
    def setUp(self):
        db.init()
        self.auth = get_admin_auth()

    def test_default_admin_exists(self):
        admin = db.get_admin_by_username("admin")
        self.assertIsNotNone(admin)
        self.assertEqual(admin["role"], "super_admin")
        self.assertTrue(admin["is_active"])

    def test_login_success(self):
        result = self.auth.login("admin", "admin123")
        self.assertTrue(result["success"])
        self.assertIn("token", result)
        self.assertEqual(result["admin"]["username"], "admin")

    def test_login_wrong_password(self):
        result = self.auth.login("admin", "wrongpass")
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_login_unknown_user(self):
        result = self.auth.login("nobody", "admin123")
        self.assertFalse(result["success"])

    def test_verify_valid_token(self):
        login = self.auth.login("admin", "admin123")
        admin = self.auth.verify(login["token"])
        self.assertIsNotNone(admin)
        self.assertEqual(admin["username"], "admin")

    def test_verify_invalid_token(self):
        self.assertIsNone(self.auth.verify("invalid_token_xyz"))

    def test_logout_invalidates_token(self):
        login = self.auth.login("admin", "admin123")
        self.auth.logout(login["token"])
        self.assertIsNone(self.auth.verify(login["token"]))

    def test_change_password_and_login(self):
        admin = db.get_admin_by_username("admin")
        result = self.auth.change_password(admin["id"], "admin123", "newpass456")
        self.assertTrue(result["success"])

        # 新密码可登录
        login = self.auth.login("admin", "newpass456")
        self.assertTrue(login["success"])

        # 旧密码失效
        failed = self.auth.login("admin", "admin123")
        self.assertFalse(failed["success"])

        # 还原密码
        self.auth.change_password(admin["id"], "newpass456", "admin123")


if __name__ == "__main__":
    unittest.main()
