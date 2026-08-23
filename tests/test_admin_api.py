# -*- coding: utf-8 -*-
"""管理员 API 测试（用 Flask test client）"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.api.server import create_app


class TestAdminAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init()
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def _login(self):
        resp = self.client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(resp.status_code, 200)
        return resp.get_json()["token"]

    def test_login_endpoint(self):
        resp = self.client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("token", data)

    def test_login_wrong_password(self):
        resp = self.client.post("/api/admin/login", json={"username": "admin", "password": "bad"})
        self.assertEqual(resp.status_code, 401)

    def test_me_requires_auth(self):
        resp = self.client.get("/api/admin/me")
        self.assertEqual(resp.status_code, 401)

    def test_me_with_token(self):
        token = self._login()
        resp = self.client.get("/api/admin/me", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["admin"]["username"], "admin")

    def test_overview(self):
        token = self._login()
        resp = self.client.get("/api/admin/overview", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("stats", data)
        self.assertIn("model_status", data)

    def test_list_users(self):
        token = self._login()
        resp = self.client.get("/api/admin/users", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("users", resp.get_json())

    def test_create_and_delete_user(self):
        token = self._login()
        resp = self.client.post("/api/admin/users",
                                json={"name": "API测试用户", "role": "student", "password": "test123"},
                                headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        user_id = resp.get_json()["user"]["id"]

        resp = self.client.delete(f"/api/admin/users/{user_id}", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)

    def test_list_agents(self):
        token = self._login()
        resp = self.client.get("/api/admin/agents", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        agents = resp.get_json()["agents"]
        self.assertGreaterEqual(len(agents), 4)

    def test_start_stop_agent(self):
        token = self._login()
        resp = self.client.post("/api/admin/agents/chat_assistant/start", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post("/api/admin/agents/chat_assistant/stop", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)

    def test_run_agent_feynman(self):
        token = self._login()
        resp = self.client.post("/api/admin/agents/feynman_teacher/run",
                                json={"topic": "勾股定理", "level": "junior"},
                                headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)

    def test_logs(self):
        token = self._login()
        resp = self.client.get("/api/admin/logs?limit=5", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("logs", resp.get_json())

    def test_api_keys_crud(self):
        token = self._login()
        resp = self.client.post("/api/admin/api-keys",
                                json={"key_name": "测试密钥", "scope": "read"},
                                headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        api_key = resp.get_json()["api_key"]

        resp = self.client.delete(f"/api/admin/api-keys/{api_key}", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)

    def test_admin_page_served(self):
        resp = self.client.get("/admin")
        self.assertEqual(resp.status_code, 200)

    # ---------- 三层记忆可视化端点 ----------

    def test_memories_requires_auth(self):
        resp = self.client.get("/api/admin/memories")
        self.assertEqual(resp.status_code, 401)

    def test_memories_list_and_stats(self):
        """记忆列表端点：返回 items/total/stats 且结构完整"""
        token = self._login()
        resp = self.client.get("/api/admin/memories", headers={"X-Admin-Token": token})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["items"], list)
        self.assertIn("total", data)
        stats = data["stats"]
        self.assertEqual(set(stats.keys()), {"short", "mid", "long", "wrong", "total"})

    def test_memories_type_filter(self):
        """按 memory_type 筛选生效"""
        token = self._login()
        # 预置三条不同类型的记忆
        from framework.storage.layered_memory import LayeredMemory
        mem = LayeredMemory()
        mem.save_short_term("7", session_id="s7", content="短期记忆内容", topic="函数")
        mem.save_mid_term("7", chapter="第1章", content="中期记忆内容", topic="函数")
        mem.save_long_term("7", content="长期记忆内容", topic="函数", is_wrong_answer=1)

        resp = self.client.get("/api/admin/memories?memory_type=long&user_id=7",
                               headers={"X-Admin-Token": token})
        data = resp.get_json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["memory_type"], "long")
        self.assertEqual(data["items"][0]["is_wrong_answer"], 1)

    def test_memories_wrong_only_filter(self):
        """wrong_only=1 仅返回错题记忆"""
        token = self._login()
        from framework.storage.layered_memory import LayeredMemory
        mem = LayeredMemory()
        mem.save_long_term("8", content="普通长期记忆", topic="几何")
        mem.save_long_term("8", content="错题记忆", topic="几何", is_wrong_answer=1)

        resp = self.client.get("/api/admin/memories?wrong_only=1&user_id=8",
                               headers={"X-Admin-Token": token})
        data = resp.get_json()
        self.assertEqual(data["total"], 1)
        self.assertTrue(all(it["is_wrong_answer"] == 1 for it in data["items"]))

    def test_memories_users_distribution(self):
        """记忆用户分布端点结构正确"""
        token = self._login()
        from framework.storage.layered_memory import LayeredMemory
        mem = LayeredMemory()
        mem.save_long_term("9", content="记忆A", topic="t")
        resp = self.client.get("/api/admin/memories/users", headers={"X-Admin-Token": token})
        data = resp.get_json()
        self.assertTrue(data["success"])
        user9 = next((u for u in data["users"] if str(u["user_id"]) == "9"), None)
        self.assertIsNotNone(user9)
        self.assertGreaterEqual(user9["long"], 1)
        self.assertIn("total", user9)


if __name__ == "__main__":
    unittest.main()
