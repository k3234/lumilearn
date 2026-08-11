# -*- coding: utf-8 -*-
"""
chat_history 多轮对话持久化 — 轻量测试
核心设备压力约束：仅标准库 sqlite3 + 临时库文件，不触网、不加载任何模型。
"""
import pytest

from framework.services.conversation_store import ConversationStore


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMILEARN_DB_PATH", str(tmp_path / "conv_test.db"))
    s = ConversationStore()
    yield s
    s.close()


class TestSessions:
    def test_create_and_list(self, store):
        sid = store.create_session("函数的单调性", user_id=1)
        assert sid > 0
        sessions = store.list_sessions(user_id=1)
        assert len(sessions) == 1
        assert sessions[0]["title"] == "函数的单调性"
        assert sessions[0]["msg_count"] == 0
        assert sessions[0]["last_message"] is None

    def test_user_isolation(self, store):
        store.create_session("物理题", user_id=1)
        store.create_session("化学题", user_id=2)
        assert len(store.list_sessions(user_id=1)) == 1
        assert len(store.list_sessions(user_id=2)) == 1

    def test_get_and_delete(self, store):
        sid = store.create_session("会话A", user_id=1)
        assert store.get_session(sid)["title"] == "会话A"
        assert store.delete_session(sid) is True
        assert store.get_session(sid) is None
        assert store.delete_session(9999) is False


class TestMessages:
    def test_add_and_get_ordered(self, store):
        sid = store.create_session("多轮对话", user_id=1)
        store.add_message(sid, "user", "什么是函数？")
        store.add_message(sid, "assistant", "函数是一种对应关系……", model="qwen2.5:7b")
        store.add_message(sid, "user", "再讲个例子")
        msgs = store.get_messages(sid)
        assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
        assert msgs[1]["model"] == "qwen2.5:7b"
        assert msgs[2]["content"] == "再讲个例子"

    def test_limit_takes_tail(self, store):
        sid = store.create_session("限长", user_id=1)
        for i in range(5):
            store.add_message(sid, "user", f"第{i + 1}句")
        tail = store.get_messages(sid, limit=2)
        assert [m["content"] for m in tail] == ["第4句", "第5句"]

    def test_clear_session(self, store):
        sid = store.create_session("清空", user_id=1)
        store.add_message(sid, "user", "1")
        store.add_message(sid, "assistant", "2")
        assert store.clear_session(sid) == 2
        assert store.get_messages(sid) == []

    def test_delete_cascades_messages(self, store):
        sid = store.create_session("级联", user_id=1)
        store.add_message(sid, "user", "hi")
        store.delete_session(sid)
        assert store.get_messages(sid) == []
