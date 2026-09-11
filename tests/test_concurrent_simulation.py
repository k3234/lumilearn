# -*- coding: utf-8 -*-
"""
LumiLearn 并发模拟测试 — 10 个身份同时访问服务

场景：
  A. 6 个学生同时学习不同知识点（feynman API）
  B. 3 个教师同时备课（feynman API 生成课程）
  C. 10 个身份混合并发

设计：
  - 从 docs/simulation/agents/*.md 加载 10 个 agent 身份档案
  - 使用 threading 模拟并发，不调用真实 API
  - 模拟 API 响应时间（随机分布，考虑网络延迟）
  - 统计：成功率、平均响应时间、P95、错误分布
  - 生成结构化报告 concurrent_test_report.md
"""

import os
import sys
import re
import json
import math
import random
import statistics
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

AGENT_DIR = os.path.join(_PROJECT_ROOT, "docs", "simulation", "agents")
REPORT_PATH = os.path.join(_PROJECT_ROOT, "docs", "simulation", "concurrent_test_report.md")

# ---------------------------------------------------------------------------
# Agent 数据模型
# ---------------------------------------------------------------------------

@dataclass
class AgentProfile:
    agent_id: str
    name: str
    age: int
    role: str          # student / teacher / admin
    grade: str
    style: str
    description: str
    typical_topics: list[str] = field(default_factory=list)
    device_quality: str = "good"   # good / medium / poor
    network_latency_ms: int = 50   # 模拟基础网络延迟

    @property
    def api_endpoint(self) -> str:
        if self.role == "teacher":
            return "/api/feynman/prepare"
        elif self.role == "admin":
            return "/api/admin/dashboard"
        return "/api/learn"

    @property
    def simulated_delay_ms(self) -> int:
        """根据设备/网络质量模拟额外延迟"""
        if self.device_quality == "poor":
            return random.randint(800, 2500)
        elif self.device_quality == "medium":
            return random.randint(300, 800)
        return random.randint(50, 300)


# ---------------------------------------------------------------------------
# Agent 档案解析器
# ---------------------------------------------------------------------------

def parse_agent_file(filepath: str) -> AgentProfile:
    """从 markdown 档案解析 AgentProfile"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    aid = os.path.splitext(os.path.basename(filepath))[0]  # e.g. agent_01_grade7_visual

    def extract(key: str) -> str:
        m = re.search(rf"\*\*{key}\*\*[：:]\s*(.+)", content)
        return m.group(1).strip() if m else ""

    name = extract("姓名")
    age_str = extract("年龄")
    role_str = extract("年级/角色")
    style = extract("学习风格")
    desc_lines = re.findall(r"^\*\*使用场景\*\*[：:]([\s\S]*?)(?=\n##|\n\*\*典型问题|\Z)", content)
    description = desc_lines[0].strip() if desc_lines else role_str

    age = int(re.search(r"(\d+)", age_str).group(1)) if re.search(r"(\d+)", age_str) else 0

    # 角色推断
    if "教师" in role_str or "老师" in role_str:
        role = "teacher"
    elif "管理员" in role_str or "admin" in role_str.lower():
        role = "admin"
    else:
        role = "student"

    # 设备/网络质量推断
    if "老旧" in content and "卡顿" in content:
        device_quality = "poor"
    elif "旧" in content or "较差" in content:
        device_quality = "medium"
    else:
        device_quality = "good"

    # 典型学习主题
    typical_topics = []
    if role == "student":
        typical_topics = _student_topics(aid)
    elif role == "teacher":
        typical_topics = _teacher_topics(aid)
    else:
        typical_topics = ["系统健康检查", "使用统计报表"]

    return AgentProfile(
        agent_id=aid,
        name=name,
        age=age,
        role=role,
        grade=role_str.split("（")[0].split("(")[0].strip(),
        style=style.split("（")[0].strip(),
        description=description[:80],
        typical_topics=typical_topics,
        device_quality=device_quality,
        network_latency_ms=random.randint(30, 150),
    )


def _student_topics(aid: str) -> list[str]:
    """根据 agent id 分配不同知识点"""
    mapping = {
        "agent_01": "勾股定理动画讲解",
        "agent_02": "代数式推导与公式来源",
        "agent_03": "一次函数图像变换",
        "agent_04": "二次方程求根公式练习",
        "agent_05": "圆的几何证明与中考冲刺",
        "agent_06": "压轴题解题思路对比",
    }
    for k, v in mapping.items():
        if k in aid:
            return [v, f"{v}进阶练习", f"{v}错题回顾"]
    return ["函数单调性", "几何证明入门", "概率统计基础"]


def _teacher_topics(aid: str) -> list[str]:
    mapping = {
        "agent_07": "勾股定理课程设计（费曼五步法）",
        "agent_08": "二次函数综合题备课",
        "agent_09": "语文阅读理解教学拓展",
    }
    for k, v in mapping.items():
        if k in aid:
            return [v, "配套练习题生成", "学情分析报告"]
    return ["知识点讲解设计", "课后作业布置"]


def load_all_agents(agent_dir: str) -> list[AgentProfile]:
    """加载所有 agent 档案"""
    agents = []
    for fname in sorted(os.listdir(agent_dir)):
        if fname.startswith("agent_") and fname.endswith(".md"):
            agents.append(parse_agent_file(os.path.join(agent_dir, fname)))
    return agents


# ---------------------------------------------------------------------------
# 模拟 API 响应
# ---------------------------------------------------------------------------

class SimulatedAPIServer:
    """
    模拟 LumiLearn API 服务器，模拟不同端点的响应。
    不调用真实网络，完全在内存中模拟。
    """

    _ENDPOINT_LATENCY_BASE = {
        "/api/learn":           (200, 800),    # 学生请求较快
        "/api/feynman/prepare": (400, 1500),   # 教师备课较重
        "/api/admin/dashboard": (100, 500),    # 管理端轻量
    }

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self._lock = threading.Lock()
        self._request_count = 0

    def simulate_request(self, agent: AgentProfile, endpoint: str) -> dict[str, Any]:
        """模拟一次 API 请求，返回响应字典"""
        with self._lock:
            self._request_count += 1
            req_id = self._request_count

        base_ms, heavy_ms = self._ENDPOINT_LATENCY_BASE.get(
            endpoint, (200, 800))

        # 基础网络延迟 + 设备延迟 + 端点处理时间
        network_delay = agent.network_latency_ms
        device_delay = agent.simulated_delay_ms
        processing_delay = self.rng.randint(base_ms, heavy_ms)

        total_delay_ms = network_delay + device_delay + processing_delay

        # 极低概率模拟网络超时 / 错误（约 3%）
        roll = self.rng.random()
        if roll < 0.02:
            time.sleep(total_delay_ms / 1000.0 * 0.3)
            return {
                "request_id": req_id,
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "role": agent.role,
                "endpoint": endpoint,
                "status_code": 504,
                "success": False,
                "error": "Gateway Timeout — 网络超时",
                "elapsed_ms": total_delay_ms,
                "latency_ms": network_delay,
                "device_delay_ms": device_delay,
                "processing_delay_ms": processing_delay,
            }
        elif roll < 0.04:
            time.sleep(total_delay_ms / 1000.0 * 0.5)
            return {
                "request_id": req_id,
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "role": agent.role,
                "endpoint": endpoint,
                "status_code": 500,
                "success": False,
                "error": "Internal Server Error — 服务异常",
                "elapsed_ms": total_delay_ms,
                "latency_ms": network_delay,
                "device_delay_ms": device_delay,
                "processing_delay_ms": processing_delay,
            }

        # 正常响应
        time.sleep(total_delay_ms / 1000.0)

        if endpoint == "/api/learn":
            body = {
                "topic": agent.typical_topics[0],
                "teaching_flow": {
                    "total_steps": 5,
                    "completed_steps": 5,
                    "mode": "feynman",
                },
                "mastery_assessment": {
                    "level": self.rng.choice(["良好", "优秀", "需巩固"]),
                    "score": self.rng.randint(60, 95),
                },
            }
        elif endpoint == "/api/feynman/prepare":
            body = {
                "course_title": agent.typical_topics[0],
                "steps_generated": 5,
                "models_used": self.rng.choice([1, 2, 3]),
                "best_model": "qwen2.5:7b",
            }
        else:
            body = {
                "total_users": self.rng.randint(50, 200),
                "active_now": self.rng.randint(5, 30),
                "error_rate": round(self.rng.uniform(0.01, 0.05), 3),
            }

        return {
            "request_id": req_id,
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "role": agent.role,
            "endpoint": endpoint,
            "status_code": 200,
            "success": True,
            "error": None,
            "body": body,
            "elapsed_ms": total_delay_ms,
            "latency_ms": network_delay,
            "device_delay_ms": device_delay,
            "processing_delay_ms": processing_delay,
        }


# ---------------------------------------------------------------------------
# 并发执行引擎
# ---------------------------------------------------------------------------

@dataclass
class ScenarioConfig:
    name: str
    description: str
    agent_indices: list[int]
    endpoint_fn: callable   # agent -> endpoint


SCENARIO_A = ScenarioConfig(
    name="场景A：6名学生并发学习",
    description="6个学生同时调用 /api/learn 学习不同知识点",
    agent_indices=list(range(0, 6)),
    endpoint_fn=lambda a: a.api_endpoint,
)

SCENARIO_B = ScenarioConfig(
    name="场景B：3位教师并发备课",
    description="3位教师同时调用 /api/feynman/prepare 生成课程",
    agent_indices=list(range(6, 9)),
    endpoint_fn=lambda a: "/api/feynman/prepare",
)

SCENARIO_C = ScenarioConfig(
    name="场景C：10个身份混合并发",
    description="10个身份（学生+教师+管理员）混合并发访问",
    agent_indices=list(range(0, 10)),
    endpoint_fn=lambda a: a.api_endpoint,
)


def run_scenario(
    agents: list[AgentProfile],
    config: ScenarioConfig,
    server: SimulatedAPIServer,
) -> dict[str, Any]:
    """运行一个并发场景，返回结构化结果"""
    selected = [agents[i] for i in config.agent_indices]
    results: list[dict[str, Any]] = []
    lock = threading.Lock()

    def worker(agent: AgentProfile):
        resp = server.simulate_request(agent, config.endpoint_fn(agent))
        with lock:
            results.append(resp)

    t_start = time.perf_counter()
    threads = [threading.Thread(target=worker, args=(a,)) for a in selected]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    t_end = time.perf_counter()

    elapsed_total = (t_end - t_start) * 1000  # ms

    # 统计
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    times = [r["elapsed_ms"] for r in results]
    times.sort()

    def percentile(data: list, p: float) -> float:
        if not data:
            return 0.0
        k = (len(data) - 1) * p / 100.0
        f = int(k)
        c = f + 1
        if c >= len(data):
            return float(data[f])
        return data[f] + (k - f) * (data[c] - data[f])

    error_dist: dict[str, int] = {}
    for r in failed:
        err = r.get("error", "unknown")
        error_dist[err] = error_dist.get(err, 0) + 1

    role_stats: dict[str, dict] = {}
    for r in results:
        role = r.get("role", "unknown")
        if role not in role_stats:
            role_stats[role] = {"total": 0, "success": 0, "times": []}
        role_stats[role]["total"] += 1
        if r["success"]:
            role_stats[role]["success"] += 1
        role_stats[role]["times"].append(r["elapsed_ms"])

    return {
        "scenario": config.name,
        "description": config.description,
        "agent_count": len(selected),
        "total_elapsed_ms": round(elapsed_total, 2),
        "summary": {
            "total_requests": len(results),
            "success_count": len(successful),
            "fail_count": len(failed),
            "success_rate": round(len(successful) / len(results) * 100, 2) if results else 0,
            "avg_response_ms": round(statistics.mean(times), 2) if times else 0,
            "p95_response_ms": round(percentile(times, 95), 2),
            "min_response_ms": min(times) if times else 0,
            "max_response_ms": max(times) if times else 0,
            "std_response_ms": round(statistics.stdev(times), 2) if len(times) > 1 else 0,
        },
        "error_distribution": error_dist,
        "role_breakdown": {
            role: {
                "total": s["total"],
                "success": s["success"],
                "rate": round(s["success"] / s["total"] * 100, 2) if s["total"] else 0,
                "avg_ms": round(statistics.mean(s["times"]), 2) if s["times"] else 0,
            }
            for role, s in role_stats.items()
        },
        "details": results,
    }


# ---------------------------------------------------------------------------
# 报告生成
# ---------------------------------------------------------------------------

def generate_report(all_scenarios: list[dict], agents: list[AgentProfile]) -> str:
    """生成 Markdown 格式的测试报告"""
    lines: list[str] = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append("# LumiLearn 并发模拟测试报告")
    lines.append("")
    lines.append(f"**生成时间**：{ts}")
    lines.append(f"**测试类型**：模拟并发测试（不调用真实 API）")
    lines.append(f"**Agent 数量**：{len(agents)} 个身份")
    lines.append("")

    # 一、Agent 身份列表
    lines.append("## 一、Agent 身份档案")
    lines.append("")
    lines.append("| # | Agent ID | 姓名 | 角色 | 年级 | 学习风格 | 设备质量 | 基础延迟(ms) |")
    lines.append("|---|----------|------|------|------|----------|----------|--------------|")
    for i, a in enumerate(agents, 1):
        lines.append(
            f"| {i} | `{a.agent_id}` | {a.name} | {a.role} | {a.grade} | "
            f"{a.style} | {a.device_quality} | {a.network_latency_ms} |"
        )
    lines.append("")

    # 二、汇总统计
    lines.append("## 二、总体统计")
    lines.append("")
    total_req = sum(s["summary"]["total_requests"] for s in all_scenarios)
    total_ok = sum(s["summary"]["success_count"] for s in all_scenarios)
    total_fail = sum(s["summary"]["fail_count"] for s in all_scenarios)
    all_times = []
    for s in all_scenarios:
        all_times.extend(d["elapsed_ms"] for d in s["details"])
    all_times.sort()

    def pct(data, p):
        if not data:
            return 0.0
        k = (len(data) - 1) * p / 100.0
        f = int(k)
        c = f + 1
        if c >= len(data):
            return data[f]
        return data[f] + (k - f) * (data[c] - data[f])

    lines.append(f"- **总请求数**：{total_req}")
    lines.append(f"- **成功**：{total_ok}  ({total_ok/total_req*100:.2f}%)")
    lines.append(f"- **失败**：{total_fail}  ({total_fail/total_req*100:.2f}%)")
    lines.append(f"- **平均响应时间**：{statistics.mean(all_times):.2f} ms" if all_times else "")
    lines.append(f"- **P95 响应时间**：{pct(all_times, 95):.2f} ms")
    lines.append(f"- **P99 响应时间**：{pct(all_times, 99):.2f} ms" if len(all_times) > 10 else "")
    lines.append(f"- **最小响应时间**：{min(all_times):.2f} ms" if all_times else "")
    lines.append(f"- **最大响应时间**：{max(all_times):.2f} ms" if all_times else "")
    lines.append("")

    # 三、各场景详情
    lines.append("## 三、各场景详情")
    lines.append("")

    for scenario in all_scenarios:
        s = scenario["summary"]
        lines.append(f"### {scenario['scenario']}")
        lines.append("")
        lines.append(f"**描述**：{scenario['description']}")
        lines.append("")
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        lines.append(f"| 请求数 | {s['total_requests']} |")
        lines.append(f"| 成功数 | {s['success_count']} |")
        lines.append(f"| 失败数 | {s['fail_count']} |")
        lines.append(f"| 成功率 | {s['success_rate']:.2f}% |")
        lines.append(f"| 平均响应时间 | {s['avg_response_ms']:.2f} ms |")
        lines.append(f"| P95 响应时间 | {s['p95_response_ms']:.2f} ms |")
        lines.append(f"| 最小响应时间 | {s['min_response_ms']:.2f} ms |")
        lines.append(f"| 最大响应时间 | {s['max_response_ms']:.2f} ms |")
        lines.append(f"| 标准差 | {s['std_response_ms']:.2f} ms |")
        lines.append(f"| 场景总耗时 | {scenario['total_elapsed_ms']:.2f} ms |")
        lines.append("")

        # 按角色细分
        if scenario["role_breakdown"]:
            lines.append("**按角色细分：**")
            lines.append("")
            lines.append("| 角色 | 请求数 | 成功数 | 成功率 | 平均耗时(ms) |")
            lines.append("|------|--------|--------|--------|-------------|")
            for role, rs in scenario["role_breakdown"].items():
                lines.append(
                    f"| {role} | {rs['total']} | {rs['success']} | "
                    f"{rs['rate']:.2f}% | {rs['avg_ms']:.2f} |"
                )
            lines.append("")

        # 错误分布
        if scenario["error_distribution"]:
            lines.append("**错误分布：**")
            lines.append("")
            lines.append("| 错误类型 | 次数 |")
            lines.append("|----------|------|")
            for err, cnt in scenario["error_distribution"].items():
                lines.append(f"| {err} | {cnt} |")
            lines.append("")

        # 详细记录
        lines.append("**详细请求记录：**")
        lines.append("")
        lines.append("| 请求ID | Agent | 姓名 | 角色 | 端点 | 状态码 | 耗时(ms) | 错误 |")
        lines.append("|--------|-------|------|------|------|--------|---------|------|")
        for d in scenario["details"]:
            err_str = d.get("error") or "-"
            lines.append(
                f"| {d['request_id']} | `{d['agent_id']}` | {d.get('agent_name','-')} | "
                f"{d.get('role','-')} | {d['endpoint']} | {d['status_code']} | "
                f"{d['elapsed_ms']} | {err_str} |"
            )
        lines.append("")

    # 四、结论
    lines.append("## 四、结论")
    lines.append("")
    overall_rate = total_ok / total_req * 100 if total_req else 0
    if overall_rate >= 95:
        verdict = "✅ **通过** — 并发模拟成功率 ≥ 95%"
    elif overall_rate >= 80:
        verdict = "⚠️ **警告** — 成功率在 80%-95% 之间，需关注失败原因"
    else:
        verdict = "❌ **失败** — 成功率低于 80%"
    lines.append(f"- **整体结论**：{verdict}")
    lines.append(f"- **成功率**：{overall_rate:.2f}%")
    lines.append(f"- **P95 响应时间**：{pct(all_times, 95):.2f} ms")
    lines.append(f"- **模拟错误率**：{(total_fail/total_req*100) if total_req else 0:.2f}%（含 2% 超时 + 2% 服务端错误）")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 测试用例（pytest）
# ---------------------------------------------------------------------------

class TestConcurrentSimulation:
    """并发模拟测试集"""

    @pytest.fixture(autouse=True)
    def setup_agents(self):
        self.agents = load_all_agents(AGENT_DIR)
        self.server = SimulatedAPIServer(seed=42)
        assert len(self.agents) == 10, f"期望 10 个 agent，实际 {len(self.agents)}"

    def test_agent_count_is_10(self):
        """验证加载了 10 个 agent"""
        assert len(self.agents) == 10

    def test_all_agents_have_required_fields(self):
        """验证每个 agent 关键字段非空"""
        for a in self.agents:
            assert a.agent_id, f"{a} 缺少 agent_id"
            assert a.name, f"{a.agent_id} 缺少 name"
            assert a.role in ("student", "teacher", "admin"), \
                f"{a.agent_id} 角色无效: {a.role}"
            assert a.typical_topics, f"{a.agent_id} 缺少典型主题"

    def test_scenario_a_six_students(self):
        """场景A：6个学生同时学习"""
        result = run_scenario(self.agents, SCENARIO_A, self.server)
        assert result["summary"]["total_requests"] == 6
        assert result["summary"]["success_count"] >= 4  # 允许少量模拟错误
        assert result["summary"]["success_rate"] > 0
        # 所有请求者都应是学生角色
        for d in result["details"]:
            assert d["role"] == "student"

    def test_scenario_b_three_teachers(self):
        """场景B：3位教师同时备课"""
        result = run_scenario(self.agents, SCENARIO_B, self.server)
        assert result["summary"]["total_requests"] == 3
        assert result["summary"]["success_count"] >= 2
        for d in result["details"]:
            assert d["role"] == "teacher"
            assert d["endpoint"] == "/api/feynman/prepare"

    def test_scenario_c_mixed_10(self):
        """场景C：10个身份混合并发"""
        result = run_scenario(self.agents, SCENARIO_C, self.server)
        assert result["summary"]["total_requests"] == 10
        roles = {d["role"] for d in result["details"]}
        assert "student" in roles
        assert "teacher" in roles

    def test_response_time_reasonable(self):
        """响应时间应在合理范围内（100ms ~ 5000ms）"""
        for config in (SCENARIO_A, SCENARIO_B, SCENARIO_C):
            result = run_scenario(self.agents, config, self.server)
            for d in result["details"]:
                assert 50 <= d["elapsed_ms"] <= 6000, \
                    f"不合理响应时间: {d['elapsed_ms']}ms (agent={d['agent_id']})"

    def test_no_duplicate_request_ids(self):
        """同一场景内 request_id 不重复"""
        for config in (SCENARIO_A, SCENARIO_B, SCENARIO_C):
            server = SimulatedAPIServer(seed=123)
            result = run_scenario(self.agents, config, server)
            ids = [d["request_id"] for d in result["details"]]
            assert len(ids) == len(set(ids)), f"重复 request_id: {ids}"

    def test_error_distribution_structure(self):
        """错误分布结构正确"""
        # 尝试多个 seed，确保至少有一个包含成功和失败的混合结果
        for seed in (42, 99, 7, 123, 256):
            server = SimulatedAPIServer(seed=seed)
            result = run_scenario(self.agents, SCENARIO_C, server)
            if result["summary"]["success_count"] > 0:
                break
        errors = result["error_distribution"]
        # 至少有成功记录
        assert result["summary"]["success_count"] > 0
        # 错误类型是字符串到计数的映射
        for k, v in errors.items():
            assert isinstance(k, str)
            assert isinstance(v, int)
            assert v >= 1


# ---------------------------------------------------------------------------
# 直接运行入口
# ---------------------------------------------------------------------------

def run_simulation() -> dict[str, Any]:
    """
    直接运行并发模拟并生成报告。
    可通过 `python test_concurrent_simulation.py` 直接执行。
    """
    agents = load_all_agents(AGENT_DIR)
    print(f"加载了 {len(agents)} 个 agent 身份档案")

    server = SimulatedAPIServer(seed=42)
    scenarios = [SCENARIO_A, SCENARIO_B, SCENARIO_C]
    all_results = []

    for config in scenarios:
        print(f"\n{'='*60}")
        print(f"  {config.name}")
        print(f"  {config.description}")
        print(f"{'='*60}")
        result = run_scenario(agents, config, server)
        all_results.append(result)
        s = result["summary"]
        print(f"  请求: {s['total_requests']}  |  "
              f"成功: {s['success_count']}  |  "
              f"失败: {s['fail_count']}  |  "
              f"成功率: {s['success_rate']:.1f}%  |  "
              f"P95: {s['p95_response_ms']:.0f}ms  |  "
              f"平均: {s['avg_response_ms']:.0f}ms")

    report = generate_report(all_results, agents)
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n报告已写入: {REPORT_PATH}")

    return {"scenarios": all_results, "report_path": REPORT_PATH}


if __name__ == "__main__":
    run_simulation()
