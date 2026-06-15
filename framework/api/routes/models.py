# -*- coding: utf-8 -*-
"""
灵学 lumilearn - 模型管理 API 路由
模型列表、切换、健康检查、训练、对比端点

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-02
"""

import logging
import subprocess
import threading
import time
import uuid
from pathlib import Path
from datetime import datetime
from flask import Blueprint, request, jsonify

from framework.services.chat_service import get_chat_service
from framework.core.config import get_config

logger = logging.getLogger("lumilearn.routes.models")

models_bp = Blueprint("models", __name__)

# ---------------------------------------------------------------------------
# 后台训练任务管理
# ---------------------------------------------------------------------------

training_tasks: dict = {}  # {task_id: {status, progress, log, start_time, model_name, process}}

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


def start_training_task(model_name: str, base_model: str,
                        subjects: list, sample_count: int) -> str:
    """
    启动异步训练任务

    参数：
        model_name: 自定义模型名称
        base_model: 基础模型
        subjects: 训练主题列表
        sample_count: 样本数量

    返回：
        task_id: 训练任务ID
    """
    task_id = f"train_{uuid.uuid4().hex[:8]}"
    training_tasks[task_id] = {
        "status": "running",
        "progress": "Step 1/7: 初始化训练",
        "log": [],
        "start_time": time.time(),
        "model_name": model_name,
    }

    def run():
        script_path = BASE_DIR / "train_lumilearn.sh"
        cmd = [
            "bash", str(script_path),
            "--model-name", model_name,
            "--base", base_model,
            "--subjects", ",".join(subjects),
            "--sample-count", str(sample_count),
        ]
        try:
            training_tasks[task_id]["log"].append(f"[CMD] {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(BASE_DIR)
            )
            training_tasks[task_id]["process"] = process
            step_num = 1
            for line in process.stdout:
                training_tasks[task_id]["log"].append(line.strip())
                if "Step" in line:
                    step_num += 1
                    training_tasks[task_id]["progress"] = f"Step {min(step_num, 7)}/7: {line.strip()}"
                # 限制日志数量，防止内存溢出
                if len(training_tasks[task_id]["log"]) > 500:
                    training_tasks[task_id]["log"] = training_tasks[task_id]["log"][-200:]
            process.wait()
            if process.returncode == 0:
                training_tasks[task_id]["status"] = "completed"
                training_tasks[task_id]["progress"] = "Step 7/7: 训练完成"
            else:
                training_tasks[task_id]["status"] = "failed"
                training_tasks[task_id]["progress"] = f"训练失败，返回码: {process.returncode}"
            training_tasks[task_id]["log"].append(
                f"[EXIT] 进程退出，返回码: {process.returncode}"
            )
        except Exception as e:
            training_tasks[task_id]["status"] = "failed"
            training_tasks[task_id]["progress"] = f"训练异常: {str(e)}"
            training_tasks[task_id]["log"].append(f"[ERROR] {e}")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return task_id


@models_bp.route("/api/models", methods=["GET", "OPTIONS"])
def list_models():
    """
    获取所有可用模型列表

    返回：
        {
            "models": [
                {"name": "qwen2.5:7b", "size": "4.7GB", "provider": "ollama", "status": "healthy"},
                ...
            ],
            "active_model": "qwen2.5:7b",
            "total": 5
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    try:
        chat_service = get_chat_service()
        models = chat_service.get_models()
        health = chat_service.health_check()

        models_with_status = []
        for m in models:
            name = m.get("name", "unknown")
            models_with_status.append({
                "name": name,
                "size": m.get("size", "?"),
                "modified": m.get("modified", ""),
                "provider": "ollama",
                "status": "healthy" if health.get("status") == "healthy" else "unknown"
            })

        return jsonify({
            "models": models_with_status,
            "active_model": health.get("default_model", ""),
            "total": len(models_with_status),
            "gateway": health.get("gateway", "offline")
        })

    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        return jsonify({"error": str(e)}), 500


@models_bp.route("/api/models/switch", methods=["POST", "OPTIONS"])
def switch_model():
    """
    切换当前使用的模型

    请求体（JSON）：
        {
            "model": "qwen2.5:7b"
        }

    返回：
        {
            "success": true,
            "previous_model": "lumilearn-v5:real",
            "current_model": "qwen2.5:7b",
            "message": "模型已切换"
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "请求体为空"}), 400

    model_name = data.get("model", "")
    if not model_name:
        return jsonify({"error": "缺少 model 字段"}), 400

    try:
        chat_service = get_chat_service()
        previous_model = chat_service._default_model
        chat_service._default_model = model_name

        logger.info(f"模型切换: {previous_model} → {model_name}")

        return jsonify({
            "success": True,
            "previous_model": previous_model,
            "current_model": model_name,
            "message": f"模型已从 {previous_model} 切换到 {model_name}"
        })

    except Exception as e:
        logger.error(f"模型切换失败: {e}")
        return jsonify({"error": str(e)}), 500


@models_bp.route("/api/models/health", methods=["GET", "OPTIONS"])
def models_health():
    """
    模型健康检查

    返回：
        {
            "status": "healthy" | "degraded" | "offline",
            "gateway": "online" | "offline",
            "models_count": 5,
            "latency_ms": 42,
            "timestamp": "2026-06-02 12:00:00"
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    try:
        chat_service = get_chat_service()
        health = chat_service.health_check()

        from datetime import datetime
        return jsonify({
            "status": health.get("status", "unknown"),
            "gateway": health.get("gateway", "offline"),
            "models_count": health.get("models", 0),
            "latency_ms": health.get("latency_ms", 0),
            "default_model": health.get("default_model", ""),
            "feynman_available": health.get("feynman_available", False),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# 6.2 新增端点：训练、对比、自定义模型
# ---------------------------------------------------------------------------


@models_bp.route("/api/models/train", methods=["POST", "OPTIONS"])
def trigger_training():
    """
    触发异步训练任务

    请求体（JSON）：
        {
            "model_name": "lumilearn-custom-v1",
            "base_model": "qwen2.5:7b",
            "subjects": ["math", "physics"],
            "sample_count": 100
        }

    响应（JSON）：
        {
            "task_id": "train_abc12345",
            "status": "started",
            "message": "Training started in background"
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "请求体为空"}), 400

        model_name = data.get("model_name", "")
        if not model_name:
            return jsonify({"error": "缺少 model_name 字段"}), 400

        base_model = data.get("base_model", "qwen2.5:7b")
        subjects = data.get("subjects", ["general"])
        sample_count = int(data.get("sample_count", 100))

        if not isinstance(subjects, list) or len(subjects) == 0:
            return jsonify({"error": "subjects 必须是非空列表"}), 400

        task_id = start_training_task(model_name, base_model, subjects, sample_count)

        logger.info(f"训练任务已启动: {task_id} (模型: {model_name})")

        return jsonify({
            "task_id": task_id,
            "status": "started",
            "message": f"模型 {model_name} 训练已在后台启动"
        })

    except Exception as e:
        logger.error(f"启动训练任务失败: {e}")
        return jsonify({"error": f"启动训练失败: {str(e)}"}), 500


@models_bp.route("/api/models/train/status/<task_id>", methods=["GET", "OPTIONS"])
def training_status(task_id):
    """
    查询训练任务状态

    路径参数：
        task_id: 训练任务ID

    响应（JSON）：
        {
            "task_id": "train_abc12345",
            "status": "running",
            "progress": "Step 3/7",
            "elapsed": "5m30s",
            "log": [...]
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    try:
        task = training_tasks.get(task_id)
        if task is None:
            return jsonify({"error": f"任务不存在: {task_id}"}), 404

        elapsed_seconds = int(time.time() - task["start_time"])
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        elapsed_str = f"{minutes}m{seconds}s" if minutes > 0 else f"{seconds}s"

        # 返回最近的部分日志（避免响应过大）
        recent_logs = task["log"][-50:] if len(task["log"]) > 50 else task["log"]

        return jsonify({
            "task_id": task_id,
            "status": task["status"],
            "progress": task["progress"],
            "elapsed": elapsed_str,
            "model_name": task.get("model_name", ""),
            "log": recent_logs,
        })

    except Exception as e:
        logger.error(f"查询训练状态失败: {e}")
        return jsonify({"error": str(e)}), 500


@models_bp.route("/api/models/compare", methods=["POST", "OPTIONS"])
def compare_models():
    """
    A/B 模型对比

    请求体（JSON）：
        {
            "model_a": "qwen2.5:7b",
            "model_b": "lumilearn-custom-v1",
            "prompt": "解释什么是勾股定理（可选，默认使用测试提示词）"
        }

    响应（JSON）：
        {
            "model_a": "qwen2.5:7b",
            "model_b": "lumilearn-custom-v1",
            "prompt": "...",
            "results": {
                "model_a": {"response": "...", "latency_ms": 1200, "tokens": 150},
                "model_b": {"response": "...", "latency_ms": 800, "tokens": 180}
            },
            "comparison": {
                "latency_diff_ms": 400,
                "faster_model": "lumilearn-custom-v1",
                "tokens_diff": 30,
                "longer_response": "lumilearn-custom-v1"
            }
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "请求体为空"}), 400

        model_a = data.get("model_a", "")
        model_b = data.get("model_b", "")
        if not model_a or not model_b:
            return jsonify({"error": "缺少 model_a 或 model_b 字段"}), 400

        prompt = data.get("prompt", "请用费曼教学法解释什么是机器学习，用简单易懂的语言。")

        chat_service = get_chat_service()

        messages = [{"role": "user", "content": prompt}]

        # 调用模型 A
        t0 = time.time()
        try:
            result_a = chat_service.chat_sync(messages, mode="chat", temperature=0.7, max_tokens=512)
            latency_a = round((time.time() - t0) * 1000)
            content_a = result_a.get("message", {}).get("content", "") if isinstance(result_a.get("message"), dict) else result_a.get("content", str(result_a))
            tokens_a = len(content_a)
        except Exception as e:
            result_a = {"error": str(e)}
            latency_a = None
            content_a = f"[错误] {e}"
            tokens_a = 0

        # 调用模型 B
        t1 = time.time()
        try:
            result_b = chat_service.chat_sync(messages, mode="chat", temperature=0.7, max_tokens=512)
            latency_b = round((time.time() - t1) * 1000)
            content_b = result_b.get("message", {}).get("content", "") if isinstance(result_b.get("message"), dict) else result_b.get("content", str(result_b))
            tokens_b = len(content_b)
        except Exception as e:
            result_b = {"error": str(e)}
            latency_b = None
            content_b = f"[错误] {e}"
            tokens_b = 0

        comparison = {}
        if latency_a is not None and latency_b is not None:
            comparison["latency_diff_ms"] = latency_a - latency_b
            comparison["faster_model"] = model_a if latency_a < latency_b else model_b
        if tokens_a > 0 or tokens_b > 0:
            comparison["tokens_diff"] = tokens_b - tokens_a
            comparison["longer_response"] = model_b if tokens_b > tokens_a else model_a

        return jsonify({
            "model_a": model_a,
            "model_b": model_b,
            "prompt": prompt,
            "results": {
                "model_a": {"response": content_a[:1000], "latency_ms": latency_a, "tokens": tokens_a},
                "model_b": {"response": content_b[:1000], "latency_ms": latency_b, "tokens": tokens_b},
            },
            "comparison": comparison,
        })

    except Exception as e:
        logger.error(f"模型对比失败: {e}")
        return jsonify({"error": f"模型对比失败: {str(e)}"}), 500


@models_bp.route("/api/models/custom", methods=["GET", "OPTIONS"])
def list_custom_models():
    """
    获取自定义训练模型列表

    返回：
        {
            "models": [
                {
                    "name": "lumilearn-teacher-v1",
                    "model_id": "lumilearn-teacher-v1:latest",
                    "provider": "ollama",
                    "custom": true,
                    "tags": ["local", "custom", "fine-tuned"]
                }
            ],
            "total": 1
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    try:
        chat_service = get_chat_service()
        custom_models = chat_service.list_custom_models()

        return jsonify({
            "models": custom_models,
            "total": len(custom_models),
        })

    except Exception as e:
        logger.error(f"获取自定义模型列表失败: {e}")
        return jsonify({"error": str(e)}), 500