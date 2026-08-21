# -*- coding: utf-8 -*-
"""
Task 3: Trace 持久化 + 可视化面板 测试

覆盖：
  - save_agent_trace / get_agent_traces 存取
  - 按 trace_id 过滤
  - telemetry.record_call / end_trace 落库
  - 落库失败不阻塞主流程
"""
import pytest

from agent_core.observability import get_telemetry, reset_telemetry


@pytest.fixture(autouse=True)
def _clean_telemetry():
    """每个用例使用独立 telemetry 单例"""
    reset_telemetry()
    yield
    reset_telemetry()


def test_save_and_query_trace(isolated_db):
    """save_agent_trace 后 get_agent_traces 能查到"""
    from framework.database import db
    row_id = db.save_agent_trace(
        trace_id="trace_test1", user_id="user1", topic="函数的单调性",
        agent_id="feynman", model="qwen2.5:7b", latency_ms=1200,
        input_tokens=300, output_tokens=900, success=True)
    assert row_id > 0
    traces = db.get_agent_traces(limit=100)
    assert len(traces) == 1
    assert traces[0]["trace_id"] == "trace_test1"
    assert traces[0]["topic"] == "函数的单调性"
    assert traces[0]["latency_ms"] == 1200
    assert traces[0]["success"] == 1


def test_trace_filter_by_id(isolated_db):
    """get_agent_traces 支持按 trace_id 过滤"""
    from framework.database import db
    db.save_agent_trace(trace_id="trace_a", user_id="u1", topic="t1")
    db.save_agent_trace(trace_id="trace_a", user_id="u1", topic="t2")
    db.save_agent_trace(trace_id="trace_b", user_id="u2", topic="t3")
    filtered = db.get_agent_traces(trace_id="trace_a")
    assert len(filtered) == 2
    assert all(t["trace_id"] == "trace_a" for t in filtered)
    # 详情：同一 trace 的全部记录
    detail = db.get_agent_trace_detail("trace_a")
    assert len(detail) == 2
    # 不存在的 trace 返回空
    assert db.get_agent_trace_detail("trace_none") == []


def test_record_call_persists(isolated_db):
    """telemetry.record_call / end_trace 后数据库 agent_traces 表有记录"""
    from framework.database import db
    tele = get_telemetry()
    tid = tele.start_trace("user1", "函数的单调性")
    tele.record_call(tid, agent_id="feynman", model="qwen2.5:7b",
                     latency_ms=1200, input_tokens=300, output_tokens=900,
                     success=True)
    tele.record_call(tid, agent_id="verifier", model="qwen2.5:7b",
                     latency_ms=200, input_tokens=100, output_tokens=50,
                     success=True)
    rows = db.get_agent_traces(limit=100)
    assert len(rows) == 2  # 两次调用各一条
    assert all(r["trace_id"] == tid for r in rows)
    # end_trace 落库一条汇总记录（detail_json 存 summary）
    tele.end_trace(tid)
    detail = db.get_agent_trace_detail(tid)
    assert len(detail) == 3
    summary = detail[-1]
    assert summary["agent_id"] == "__trace_summary__"
    assert summary["status"] == "completed"
    assert summary["success"] == 1
    assert summary["topic"] == "函数的单调性"
    assert '"summary"' in (summary["detail_json"] or "")


def test_db_failure_does_not_block(isolated_db, monkeypatch):
    """db.save_agent_trace 抛异常时 record_call / end_trace 不崩溃"""
    from framework.database import db
    tele = get_telemetry()
    tid = tele.start_trace("user1", "函数单调性")

    def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(db, "save_agent_trace", boom)
    rec = tele.record_call(tid, agent_id="feynman", model="qwen2.5:7b",
                           latency_ms=100, input_tokens=10, output_tokens=20,
                           success=True)
    assert rec["agent_id"] == "feynman"
    # end_trace 同样不抛异常且正常返回汇总
    summary = tele.end_trace(tid)
    assert summary is not None
    assert summary["summary"]["call_count"] == 1
