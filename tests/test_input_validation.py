# -*- coding: utf-8 -*-
"""Task 6：API 输入校验测试（Flask test client）

覆盖 6.3 新增的输入校验：
- POST /api/learn/start      topic 必填且长度 ≤ 200
- GET/POST /api/knowledge/search  query 必填且长度 ≤ 100
- POST /api/documents/import 文件类型白名单（md/txt/pdf/docx/obsidian）

依赖 tests/conftest.py 的 autouse isolated_db fixture（每测试独立临时库）。
"""
import os
import sys
import tempfile
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.services.conversation_store import conversation_store as conv_store

MAX_TOPIC = 200
MAX_QUERY = 100


@pytest.fixture(autouse=True)
def _reset_conv_store():
    """每个测试前关闭 conversation_store 惰性连接，使其跟随 isolated_db 的库路径。"""
    conv_store.close()
    yield
    conv_store.close()


@pytest.fixture(scope="module")
def goai_client():
    """goai_web 应用 test client。

    - 导入前把 DB 指向临时目录，避免在项目根创建 lumilearn.db
    - 阻断 requests.get（LumiLearnAgent 构造时会探测 Ollama 可用性）
    """
    tmp_dir = tempfile.mkdtemp(prefix="lumilearn_goai_test_")
    os.environ["LUMILEARN_DB_PATH"] = os.path.join(tmp_dir, "lumilearn.db")
    try:
        with mock.patch("requests.get", side_effect=ConnectionError("offline")):
            import goai_web
            goai_web.app.config["TESTING"] = True
        yield goai_web.app.test_client()
    finally:
        os.environ.pop("LUMILEARN_DB_PATH", None)


def _login_goai(client):
    """创建测试学生并登录（session 认证，供 learn/search 接口使用）。"""
    db.add_user("接口测试学生", role="student", username="stu_api", password="Test1234")
    resp = client.post("/api/auth/login",
                       json={"username": "stu_api", "password": "Test1234"})
    assert resp.status_code == 200, resp.get_data(as_text=True)


class TestLearnStartValidation:
    """POST /api/learn/start：topic 必填且长度 ≤ 200"""

    def test_topic_too_long(self, goai_client):
        _login_goai(goai_client)
        resp = goai_client.post("/api/learn/start", json={"topic": "学" * (MAX_TOPIC + 1)})
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["code"] == 400
        assert "200" in body["message"]

    def test_topic_missing(self, goai_client):
        _login_goai(goai_client)
        resp = goai_client.post("/api/learn/start", json={})
        assert resp.status_code == 400

    def test_valid_topic_passes(self, goai_client):
        _login_goai(goai_client)
        resp = goai_client.post("/api/learn/start", json={"topic": "函数的单调性"})
        assert resp.status_code == 200
        assert resp.get_json()["code"] == 0


class TestKnowledgeSearchValidation:
    """GET/POST /api/knowledge/search：query 必填且长度 ≤ 100"""

    def test_query_too_long(self, goai_client):
        _login_goai(goai_client)
        resp = goai_client.post("/api/knowledge/search",
                                json={"query": "查" * (MAX_QUERY + 1)})
        assert resp.status_code == 400
        assert resp.get_json()["success"] is False

    def test_query_missing(self, goai_client):
        _login_goai(goai_client)
        resp = goai_client.post("/api/knowledge/search", json={})
        assert resp.status_code == 400

    def test_valid_query_passes(self, goai_client):
        _login_goai(goai_client)
        resp = goai_client.post("/api/knowledge/search", json={"query": "函数的单调性"})
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True


@pytest.fixture()
def admin_client():
    """framework API Server test client + 管理员令牌（X-Admin-Token）。"""
    from framework.api.server import create_app
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    resp = client.post("/api/admin/login",
                       json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    token = resp.get_json()["token"]
    return client, token


class TestDocumentImportValidation:
    """POST /api/documents/import：文件类型白名单（md/txt/pdf/docx/obsidian）"""

    def test_bad_file_type(self, admin_client):
        client, token = admin_client
        resp = client.post("/api/documents/import",
                           json={"filename": "evil.exe", "content": "hello"},
                           headers={"X-Admin-Token": token})
        assert resp.status_code == 400
        assert "不支持的文件类型" in resp.get_json()["message"]

    def test_valid_import_passes(self, admin_client):
        client, token = admin_client
        content = ("# 三角学\n"
                   "## 正弦定理\n正弦定理是三角学中的核心公式。\n"
                   "## 余弦定理\n余弦定理用于求解任意三角形。")
        resp = client.post("/api/documents/import",
                           json={"filename": "三角学笔记.md", "content": content},
                           headers={"X-Admin-Token": token})
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"


class TestUnifiedErrorPage:
    """6.2 统一异常页面：API 404 返回友好 JSON"""

    def test_api_404_friendly_json(self, goai_client):
        resp = goai_client.get("/api/does-not-exist-xyz")
        assert resp.status_code == 404
        body = resp.get_json()
        assert body["error"] == "资源不存在"
        assert body["code"] == 404

    def test_api_404_json_not_html(self, goai_client):
        resp = goai_client.get("/api/does-not-exist-xyz")
        assert "text/html" not in resp.content_type
