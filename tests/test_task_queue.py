# -*- coding: utf-8 -*-
"""
LumiLearn P2-12 — 分布式任务队列测试

覆盖：
  - 提交 / 查询 / 取消（pending 可取消，终态不可取消）
  - 优先级排序（priority 越小越先执行）
  - 执行成功 → completed + 结果持久化
  - 失败重试（指数退避）→ 重试后成功 / 重试耗尽 → failed
  - 延迟执行（delay 未到期不领取）
  - 单次执行超时 → failed
  - 宕机恢复（running 超租约 → 重置 pending）
  - 后台工作池端到端（start / submit / wait / stop）
  - 编排器集成（unified_orchestrator 任务在 worker 中异步完成完整链路）
  - Admin API 端点（提交 / 列表 / 详情 / 取消 / 手动消费）
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from agent_core.task_queue import (
    TaskQueue, register_task, TASK_REGISTRY, get_task_queue, reset_task_queue,
)
from agent_core.verifier import VerifierAgent
from framework.database import db

_TERMINAL = {"completed", "failed", "canceled"}


# ================================================================
# 共享任务类型（模块级注册，注册表跨测试复用）
# ================================================================
def _echo(payload: dict) -> dict:
    return {"echo": payload}


def _add(payload: dict) -> dict:
    return {"sum": (payload.get("a") or 0) + (payload.get("b") or 0)}


register_task("tq.echo", _echo)
register_task("tq.add", _add)

# 编排器集成测试数据（与 test_integration.py 一致）
GOOD_TOPIC = "牛顿第二定律"
GOOD_STEPS = [
    {"step_name": "现象引入", "content": "推车加速的体验就是牛顿第二定律的生活原型"},
    {"step_name": "思维模型", "content": "F=ma：合外力等于质量乘以加速度"},
    {"step_name": "自主推导", "content": "由动量定理推导 F=ma，说明力是改变运动状态的原因"},
    {"step_name": "认知冲突", "content": "力不是维持运动的原因，没有力物体仍做匀速直线运动"},
    {"step_name": "费曼测试", "content": "请用自己的话解释为什么用力推车车才加速"},
]
GOOD_CONTENT = (
    "牛顿第二定律是经典力学的核心定律。物体的加速度与所受合外力成正比，"
    "与质量成反比，公式为 F=ma。F 表示合外力，单位牛顿；m 表示质量，单位千克；"
    "a 表示加速度。常见误区：误以为力是维持运动的原因，实际上力是改变运动状态的原因。"
    "应用示例：已知质量与加速度可求合外力，用于分析汽车加速、电梯升降等场景。"
)
GOOD_SOURCES = [
    {"source": "physics_kb", "id": 1, "title": "牛顿第二定律",
     "content": "牛顿第二定律：物体的加速度与合外力成正比，与质量成反比，公式 F=ma。"
                "F 为合外力（单位牛顿），m 为质量（千克），a 为加速度。"
                "力不是维持运动的原因，而是改变运动状态的原因。"},
]


def _good_teach(payload: dict) -> dict:
    return {"success": True, "mode": "full",
            "steps": list(GOOD_STEPS), "full_content": GOOD_CONTENT,
            "rag_sources": list(GOOD_SOURCES),
            "models_used": 2, "best_model": "qwen2.5:7b", "elapsed": 0.4}


@pytest.fixture
def mock_feynman_model(monkeypatch):
    """屏蔽外部模型调用：FeynmanTeacher.run_parallel 返回固定优质教学内容"""
    def _teach(self, payload, model_ids=None, max_workers=4):
        return _good_teach(payload)
    monkeypatch.setattr(
        "agent_core.multi_agent.FeynmanTeacher.run_parallel", _teach)


@pytest.fixture
def rule_verifier(monkeypatch):
    """确保编排器内部 pipeline 使用纯规则 Verifier（不调模型）"""
    monkeypatch.setattr(
        "agent_core.multi_agent.get_verifier_agent",
        lambda **kw: VerifierAgent(use_model=False))


# ================================================================
# 辅助
# ================================================================
def _pump(q: TaskQueue, task_id: str, deadline: float = 10.0) -> dict:
    """手动驱动队列直至任务进入终态（配合 process_one 同步消费）"""
    end = time.time() + deadline
    while time.time() < end:
        task = q.get(task_id)
        if task and task["status"] in _TERMINAL:
            return task
        q.process_one()
        time.sleep(0.05)
    raise AssertionError(f"任务 {task_id} 未在 {deadline}s 内进入终态")


# ================================================================
# 一、基础：提交 / 查询 / 取消
# ================================================================
class TestBasics:

    def test_submit_and_get_roundtrip(self):
        q = TaskQueue()
        r = q.submit("tq.echo", {"x": 42})
        assert r["success"] is True
        assert r["status"] == "pending"
        task = q.get(r["task_id"])
        assert task["status"] == "pending"
        assert task["payload"] == {"x": 42}
        assert task["task_type"] == "tq.echo"
        assert task["max_retries"] == 1
        assert q.status(r["task_id"]) == "pending"

    def test_submit_unknown_type(self):
        q = TaskQueue()
        r = q.submit("no.such.type", {})
        assert r["success"] is False
        assert "未注册" in r["error"]
        assert "unified_orchestrator" in r["error"]  # 提示可用类型

    def test_cancel_pending_only(self):
        q = TaskQueue()
        r1 = q.submit("tq.echo", {"x": 1})
        r2 = q.submit("tq.echo", {"x": 2})
        # pending 可取消
        c = q.cancel(r1["task_id"])
        assert c["success"] is True and c["status"] == "canceled"
        # 已取消任务不会被消费
        q.run_pending_now()
        assert q.status(r1["task_id"]) == "canceled"
        assert q.status(r2["task_id"]) == "completed"
        # 终态不可取消
        c2 = q.cancel(r2["task_id"])
        assert c2["success"] is False
        assert "pending" in c2["error"]
        # 不存在
        assert q.cancel("task_none")["success"] is False

    def test_stats(self):
        q = TaskQueue(worker_count=3)
        q.submit("tq.echo", {"x": 1})
        q.submit("tq.echo", {"x": 2})
        stats = q.stats()
        assert stats["counts"]["pending"] == 2
        assert stats["total"] == 2
        assert stats["worker_count"] == 3
        assert stats["workers_started"] is False
        assert "unified_orchestrator" in stats["registered_types"]


# ================================================================
# 二、调度：优先级 / 延迟 / 结果持久化
# ================================================================
class TestScheduling:

    def test_priority_ordering(self):
        order = []

        def _track(payload: dict) -> dict:
            order.append(payload["mark"])
            return {"mark": payload["mark"]}

        register_task("tq.track", _track)
        q = TaskQueue()
        q.submit("tq.track", {"mark": "low"}, priority=3)
        q.submit("tq.track", {"mark": "mid"}, priority=2)
        q.submit("tq.track", {"mark": "high"}, priority=1)
        q.run_pending_now()
        assert order == ["high", "mid", "low"]

    def test_delay_execution(self):
        q = TaskQueue()
        r = q.submit("tq.echo", {"x": 1}, delay=100)  # 未到期
        assert q.process_one() is None                # 无到期任务
        assert q.status(r["task_id"]) == "pending"
        r2 = q.submit("tq.echo", {"x": 2})
        q.process_one()
        assert q.status(r2["task_id"]) == "completed"
        assert q.status(r["task_id"]) == "pending"    # 延迟任务仍未执行

    def test_result_persistence(self):
        q = TaskQueue()
        r = q.submit("tq.add", {"a": 2, "b": 3})
        q.process_one()
        task = q.get(r["task_id"])
        assert task["status"] == "completed"
        assert task["result"] == {"sum": 5}
        assert task["finished_at"]


# ================================================================
# 三、可靠性：重试 / 超时 / 宕机恢复
# ================================================================
class TestReliability:

    def test_retry_then_success(self):
        attempts = []

        def _flaky(payload: dict) -> dict:
            attempts.append(1)
            if len(attempts) < 3:
                raise RuntimeError("暂时失败")
            return {"ok": True}

        register_task("tq.flaky", _flaky)
        q = TaskQueue(backoff_base=0.05)
        r = q.submit("tq.flaky", {}, max_retries=3)
        task = _pump(q, r["task_id"])
        assert task["status"] == "completed"
        assert task["retries"] == 2          # 失败 2 次后第 3 次成功
        assert task["result"] == {"ok": True}

    def test_fail_after_max_retries(self):
        def _boom(payload: dict) -> dict:
            raise ValueError("boom")

        register_task("tq.boom", _boom)
        q = TaskQueue(backoff_base=0.05)
        r = q.submit("tq.boom", {}, max_retries=2)
        task = _pump(q, r["task_id"])
        assert task["status"] == "failed"
        assert task["retries"] == 2
        assert "boom" in task["error"]

    def test_timeout_fails(self):
        def _slow(payload: dict) -> dict:
            time.sleep(5)
            return {"ok": True}

        register_task("tq.slow", _slow)
        q = TaskQueue()
        r = q.submit("tq.slow", {}, timeout=1)
        t0 = time.time()
        q.process_one()
        assert time.time() - t0 < 3          # 超时后立即返回
        task = q.get(r["task_id"])
        assert task["status"] == "failed"
        assert "超时" in task["error"]

    def test_stale_task_recovery(self):
        q = TaskQueue()
        r = q.submit("tq.echo", {"x": 1})
        # 模拟 worker 领取后崩溃：标记 running 且 started_at 已过期
        claimed = db.claim_next_task("crashed_worker", time.time())
        assert claimed and claimed["task_id"] == r["task_id"]
        db.conn.execute(
            "UPDATE task_queue SET started_at = "
            "datetime('now','localtime','-600 seconds') WHERE task_id = ?",
            (r["task_id"],))
        db.conn.commit()
        # 宕机恢复：running 超租约 → pending
        assert q.recover_stale_tasks() == 1
        task = q.get(r["task_id"])
        assert task["status"] == "pending"
        # 可重新执行
        q.process_one()
        assert q.status(r["task_id"]) == "completed"


# ================================================================
# 四、后台工作池端到端
# ================================================================
class TestWorkerPool:

    def test_worker_pool_end_to_end(self):
        q = TaskQueue(worker_count=2, poll_interval=0.05)
        q.start()
        try:
            r = q.submit("tq.add", {"a": 2, "b": 3})
            task = q.wait(r["task_id"], timeout=5)
            assert task["status"] == "completed"
            assert task["result"] == {"sum": 5}
            assert q.stats()["workers_started"] is True
        finally:
            q.stop()

    def test_start_stop_idempotent(self):
        q = TaskQueue(worker_count=1, poll_interval=0.05)
        q.start()
        q.start()          # 幂等
        assert len(q._threads) == 1
        q.stop()
        q.stop()           # 幂等
        assert q.stats()["workers_started"] is False


# ================================================================
# 五、编排器集成：异步执行完整链路
# ================================================================
class TestOrchestratorIntegration:

    def test_orchestrator_task_in_worker(self, mock_feynman_model, rule_verifier):
        q = TaskQueue(worker_count=1, poll_interval=0.05)
        q.start()
        try:
            r = q.submit("unified_orchestrator", {
                "topic": GOOD_TOPIC, "subject": "物理", "user_id": 1,
            })
            task = q.wait(r["task_id"], timeout=15)
            assert task["status"] == "completed"
            result = task["result"]
            assert result.get("success") is True
            assert result.get("routing_decision") == "standard"
            assert result.get("verified") is True
            assert result.get("fact_check", {}).get("passed") is True
            assert result.get("knowledge_written") is True
        finally:
            q.stop()


# ================================================================
# 六、Admin API 端点
# ================================================================
class TestAdminAPI:

    def test_task_endpoints(self):
        reset_task_queue()  # 确保单例干净
        from framework.api.server import create_app
        app = create_app()
        app.config["TESTING"] = True
        client = app.test_client()

        # 未认证 → 401
        assert client.get("/api/admin/tasks").status_code == 401

        resp = client.post("/api/admin/login",
                           json={"username": "admin", "password": "admin123"})
        token = resp.get_json()["token"]
        h = {"X-Admin-Token": token}

        # 未知类型 → 400
        resp = client.post("/api/admin/tasks",
                           json={"task_type": "nope", "payload": {}}, headers=h)
        assert resp.status_code == 400

        # 提交
        resp = client.post("/api/admin/tasks",
                           json={"task_type": "tq.echo", "payload": {"x": 42}},
                           headers=h)
        assert resp.status_code == 200
        task_id = resp.get_json()["task"]["task_id"]

        # 列表 + 统计
        resp = client.get("/api/admin/tasks", headers=h)
        assert resp.status_code == 200
        data = resp.get_json()
        assert any(t["task_id"] == task_id for t in data["tasks"])
        assert data["stats"]["counts"]["pending"] >= 1

        # 详情（完整 payload）
        resp = client.get(f"/api/admin/tasks/{task_id}", headers=h)
        assert resp.get_json()["task"]["payload"] == {"x": 42}

        # 手动消费
        resp = client.post("/api/admin/tasks/process", headers=h)
        assert resp.get_json()["processed"] >= 1

        # 消费后 completed + 结果持久化
        resp = client.get(f"/api/admin/tasks/{task_id}", headers=h)
        task = resp.get_json()["task"]
        assert task["status"] == "completed"
        assert task["result"] == {"echo": {"x": 42}}

        # 终态不可取消 → 400
        resp = client.post(f"/api/admin/tasks/{task_id}/cancel", headers=h)
        assert resp.status_code == 400

        # 不存在 → 404
        assert client.get("/api/admin/tasks/task_none", headers=h).status_code == 404
