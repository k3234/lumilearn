# -*- coding: utf-8 -*-
"""
LumiLearn Agent Core — 分布式任务队列（P2-12）

轻量级异步任务队列，基于 SQLite（broker + 结果后端）+ 线程工作池，
无外部依赖（不引入 Celery/RQ/Redis），与现有 SQLite 技术栈一致，
适配 Windows / 低资源部署 / 单机多进程 worker 场景。

架构：
  - Broker / Result Backend：SQLite task_queue 表（持久化、重启不丢）
  - Worker：后台线程池消费任务（可多实例/多进程并行领取，DB 锁保证原子领取）
  - 注册表：按 task_type 注册执行函数（默认注册 unified_orchestrator）

特性：
  - 优先级（priority 越小越优先）
  - 延迟执行（delay 秒后到期）
  - 失败重试（指数退避：1s, 2s, 4s…）
  - 单次执行超时（timeout 秒，超时标记失败）
  - 取消（仅 pending 可取消）
  - 宕机恢复（running 超租约 → 重置 pending）
  - 结果持久化（completed 后可按 task_id 查询结果）

状态机：
  pending → running → completed / failed / canceled
  running ──(失败重试)──→ pending（退避后再次执行）
"""

from __future__ import annotations

import os
import sys
import time
import logging
import threading
import uuid
from typing import Callable, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("lumilearn.agent.task_queue")

# 任务执行函数签名：fn(payload: Dict) -> Dict
TASK_REGISTRY: Dict[str, Callable[[Dict], Dict]] = {}

# 终态集合（wait / 判断用）
_TERMINAL = {"completed", "failed", "canceled"}


def register_task(task_type: str, fn: Callable[[Dict], Dict]) -> None:
    """注册任务类型对应的执行函数"""
    if not task_type or not callable(fn):
        raise ValueError("task_type 与可调用 fn 均必填")
    TASK_REGISTRY[task_type] = fn
    logger.info("已注册任务类型: %s", task_type)


def _default_orchestrator_handler(payload: Dict) -> Dict:
    """默认任务：统一编排器完整链路（Router → Feynman → Verifier → FactChecker → KnowledgeCache）"""
    from agent_core.orchestrator import run_agent
    return run_agent(payload)


register_task("unified_orchestrator", _default_orchestrator_handler)


class TaskQueue:
    """分布式任务队列（SQLite broker + 线程工作池）"""

    def __init__(self, worker_count: int = 2, poll_interval: float = 0.5,
                 lease_timeout: float = 300.0, backoff_base: float = 1.0):
        self.worker_count = max(1, int(worker_count))
        self.poll_interval = max(0.05, float(poll_interval))
        self.lease_timeout = float(lease_timeout)   # running 超租约秒数（worker 崩溃恢复）
        self.backoff_base = float(backoff_base)     # 重试退避基数（秒）
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._threads: List[threading.Thread] = []
        self._workers_started = False

    # ------------------------------------------------------------
    # 提交 / 查询 / 取消
    # ------------------------------------------------------------
    def submit(self, task_type: str, payload: Optional[Dict] = None,
               priority: int = 5, max_retries: int = 1,
               delay: float = 0.0, timeout: int = 300) -> Dict:
        """提交任务到队列，返回 {task_id, status, task_type}"""
        if task_type not in TASK_REGISTRY:
            return {
                "success": False,
                "error": f"未注册的任务类型: {task_type}（可用: {sorted(TASK_REGISTRY)}）",
            }
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        next_run_at = time.time() + max(0.0, float(delay))
        from framework.database import db
        ok = db.submit_task(
            task_id=task_id, task_type=task_type,
            payload=payload or {}, priority=priority,
            max_retries=max_retries, next_run_at=next_run_at,
            timeout=max(1, int(timeout)))
        if not ok:
            return {"success": False, "error": "任务提交失败"}
        return {"success": True, "task_id": task_id,
                "task_type": task_type, "status": "pending"}

    def get(self, task_id: str) -> Optional[Dict]:
        """查询任务详情（含反序列化后的 payload/result）"""
        from framework.database import db
        return db.get_task(task_id)

    def status(self, task_id: str) -> str:
        task = self.get(task_id)
        return task["status"] if task else "not_found"

    def list(self, status: str = "", task_type: str = "",
             limit: int = 50) -> List[Dict]:
        from framework.database import db
        return db.list_tasks(status=status, task_type=task_type, limit=limit)

    def stats(self) -> Dict:
        """队列统计：各状态计数 + worker 状态"""
        from framework.database import db
        counts = db.count_tasks()
        return {
            "counts": counts,
            "total": sum(counts.values()) if isinstance(counts, dict) else 0,
            "workers_started": self._workers_started,
            "worker_count": self.worker_count,
            "registered_types": sorted(TASK_REGISTRY),
        }

    def cancel(self, task_id: str) -> Dict:
        from framework.database import db
        if not db.get_task(task_id):
            return {"success": False, "error": "任务不存在"}
        if db.cancel_task(task_id):
            return {"success": True, "task_id": task_id, "status": "canceled"}
        task = db.get_task(task_id)
        return {"success": False,
                "error": f"仅 pending 状态可取消（当前: {task['status']}）"}

    def wait(self, task_id: str, timeout: float = 60.0, poll: float = 0.2) -> Dict:
        """阻塞等待任务进入终态，返回任务详情；超时抛 TimeoutError"""
        deadline = time.time() + max(0.0, float(timeout))
        while True:
            task = self.get(task_id)
            if task is None:
                raise RuntimeError(f"任务不存在: {task_id}")
            if task["status"] in _TERMINAL:
                return task
            if time.time() >= deadline:
                raise TimeoutError(
                    f"任务 {task_id} 等待超时（{timeout}s，状态: {task['status']}）")
            time.sleep(poll)

    # ------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------
    def _execute_task(self, task: Dict) -> Dict:
        """执行单个任务（含超时），返回执行后的任务记录"""
        task_id = task["task_id"]
        fn = TASK_REGISTRY.get(task["task_type"])
        if fn is None:
            from framework.database import db
            db.fail_task(task_id, f"未注册的任务类型: {task['task_type']}")
            return self.get(task_id) or task

        result_box: Dict = {"result": None, "error": None}
        timeout = max(1, int(task.get("timeout") or 300))

        def _run():
            try:
                result_box["result"] = fn(task.get("payload") or {})
            except Exception as e:  # noqa: BLE001 — 任务异常写入队列，由上层判定
                result_box["error"] = f"{type(e).__name__}: {e}"

        worker = threading.Thread(target=_run, daemon=True)
        worker.start()
        worker.join(timeout=timeout)
        alive = worker.is_alive()

        from framework.database import db
        if alive:
            db.fail_task(task_id, f"执行超时（>{timeout}s）")
            return self.get(task_id) or task
        if result_box["error"] is not None:
            error = result_box["error"]
            retries = int(task.get("retries") or 0)
            max_retries = int(task.get("max_retries") or 0)
            if retries < max_retries:
                # 指数退避：1s, 2s, 4s…
                backoff = self.backoff_base * (2 ** retries)
                db.mark_task_retry(task_id, retries + 1,
                                   time.time() + backoff, error)
            else:
                db.fail_task(task_id, error)
            return self.get(task_id) or task
        db.complete_task(task_id, result_box["result"] or {})
        return self.get(task_id) or task

    def process_one(self) -> Optional[Dict]:
        """领取并执行一个到期任务；无任务返回 None（同步执行，测试/嵌入用）"""
        from framework.database import db
        task = db.claim_next_task("worker_sync", time.time())
        if not task:
            return None
        return self._execute_task(task)

    def run_pending_now(self, limit: int = 0) -> int:
        """同步执行当前所有到期任务（常用于测试 / 无后台 worker 的嵌入场景）"""
        done = 0
        while True:
            if limit and done >= limit:
                break
            if self.process_one() is None:
                break
            done += 1
        return done

    # ------------------------------------------------------------
    # 后台工作池
    # ------------------------------------------------------------
    def start(self) -> None:
        """启动后台工作线程（幂等）；启动前先做宕机恢复"""
        with self._lock:
            if self._workers_started:
                return
            self._stop.clear()
            self.recover_stale_tasks()
            for i in range(self.worker_count):
                t = threading.Thread(
                    target=self._worker_loop, args=(f"worker-{i + 1}",),
                    daemon=True, name=f"task-queue-{i + 1}")
                t.start()
                self._threads.append(t)
            self._workers_started = True
            logger.info("任务队列 worker 池已启动（%d 个）", self.worker_count)

    def stop(self, timeout: float = 5.0) -> None:
        """停止后台工作线程（幂等）"""
        with self._lock:
            if not self._workers_started:
                return
            self._stop.set()
            for t in self._threads:
                t.join(timeout=timeout)
            self._threads.clear()
            self._workers_started = False
            logger.info("任务队列 worker 池已停止")

    def _worker_loop(self, worker_id: str) -> None:
        from framework.database import db
        while not self._stop.is_set():
            try:
                task = db.claim_next_task(worker_id, time.time())
                if task is None:
                    time.sleep(self.poll_interval)
                    continue
                self._execute_task(task)
            except Exception as e:  # noqa: BLE001
                logger.warning("worker %s 异常: %s", worker_id, e)
                time.sleep(self.poll_interval)

    def recover_stale_tasks(self) -> int:
        """宕机恢复：running 超租约 → 重置 pending（worker 崩溃后任务可重新执行）"""
        from framework.database import db
        return db.reset_stale_tasks(time.time(), self.lease_timeout)


# 单例
_task_queue: Optional[TaskQueue] = None


def get_task_queue(**kwargs) -> TaskQueue:
    """获取任务队列单例"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue(**kwargs)
    return _task_queue


def reset_task_queue() -> None:
    """重置队列单例（测试用：先停止 worker 再重建）"""
    global _task_queue
    if _task_queue is not None:
        _task_queue.stop()
        _task_queue = None


def submit_task(task_type: str, payload: Optional[Dict] = None, **kwargs) -> Dict:
    """便捷入口：一行提交任务"""
    return get_task_queue().submit(task_type, payload, **kwargs)


if __name__ == "__main__":
    print("=" * 60)
    print("  LumiLearn 分布式任务队列 — 自检")
    print("=" * 60)

    q = TaskQueue(worker_count=1, poll_interval=0.1)

    def _demo(payload: dict) -> dict:
        return {"echo": payload}

    register_task("tq.demo", _demo)

    r = q.submit("tq.demo", {"msg": "hello"})
    print(f"  提交: {r}")
    q.run_pending_now()
    task = q.get(r["task_id"])
    print(f"  状态: {task['status']} | 结果: {task['result']}")

    r2 = q.submit("tq.demo", {"msg": "later"}, delay=100)
    print(f"  延迟任务未到期: {q.process_one() is None}")
    print(f"  统计: {q.stats()}")
    print("=" * 60)
