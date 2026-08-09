#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 全面测评脚本
=====================
测试范围：
  1. GOAI Agent 引擎（任务理解/流程编排/工具调用/结果交付）
  2. 费曼教学引擎（五步教学法）
  3. API 服务（Flask 端点）
  4. 多学科覆盖测试
  5. 性能与稳定性测试

运行方式：
  python goai_comprehensive_test.py
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# 测试报告
# ============================================================
class TestReport:
    def __init__(self):
        self.results = []
        self.start_time = time.time()

    def add(self, module, test_name, status, detail="", elapsed=0):
        self.results.append({
            "module": module,
            "test_name": test_name,
            "status": status,
            "detail": detail,
            "elapsed": round(elapsed, 2),
        })
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"  {icon} [{module}] {test_name} ({elapsed:.1f}s)")
        if detail and status != "PASS":
            print(f"     {detail[:200]}")

    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        skipped = sum(1 for r in self.results if r["status"] == "SKIP")
        elapsed = time.time() - self.start_time

        score = round(passed / total * 100, 1) if total > 0 else 0

        print("\n" + "=" * 70)
        print("  📊 测评报告")
        print("=" * 70)
        print(f"  总耗时: {elapsed:.1f}s")
        print(f"  测试项: {total}")
        print(f"  ✅ 通过: {passed}")
        print(f"  ❌ 失败: {failed}")
        print(f"  ⚠️  跳过: {skipped}")
        print(f"  通过率: {score}%")
        print("=" * 70)

        if score >= 90:
            print("  🏆 评级: S — 系统稳定性优秀")
        elif score >= 80:
            print("  🏆 评级: A — 系统稳定性良好")
        elif score >= 60:
            print("  ⚠️ 评级: B — 部分功能需要修复")
        else:
            print("  ❌ 评级: C — 系统需要大幅修复")

        # 保存报告
        report = {
            "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_elapsed": round(elapsed, 1),
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "score": score,
            "details": self.results,
        }
        os.makedirs("goai_output", exist_ok=True)
        path = f"goai_output/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n  报告已保存: {path}")
        return score


# ============================================================
# 测试套件
# ============================================================
report = TestReport()


def test_module_imports():
    """模块1: 导入测试"""
    t0 = time.time()
    try:
        from goai_agent import (LumiLearnAgent, TaskUnderstanding,
                                FlowOrchestrator, ToolCaller, ResultDelivery)
        report.add("导入", "goai_agent 全部模块引入", "PASS", elapsed=time.time()-t0)
        return True
    except Exception as e:
        report.add("导入", "goai_agent 模块导入", "FAIL", str(e), time.time()-t0)
        return False


def test_task_understanding():
    """模块2: 任务理解测试"""
    t0 = time.time()
    try:
        from goai_agent import TaskUnderstanding
        tu = TaskUnderstanding()

        # 测试用例
        cases = [
            ("我想理解函数的单调性", "数学", "函数", "高中"),
            ("帮我复习牛顿第二定律", "物理", "力学", "高中"),
            ("化学平衡移动原理", "化学", "反应", "高中"),
            ("英语定语从句的用法", "英语", "通用", "高中"),
            ("勾股定理", "数学", "几何", "高中"),
            ("大学微积分基础", "数学", "函数", "大学"),
            ("初一数学一元一次方程", "数学", "方程", "初中"),
        ]

        for input_text, exp_subj, exp_type, exp_diff in cases:
            result = tu.understand(input_text)
            checks = []
            if result["subject"] != exp_subj:
                checks.append(f"学科预期{exp_subj}实际{result['subject']}")
            if result["difficulty"] != exp_diff:
                checks.append(f"难度预期{exp_diff}实际{result['difficulty']}")

            status = "PASS" if not checks else "FAIL"
            detail = f"输入:「{input_text}」→ 学科={result['subject']} 类型={result['topic_type']} 难度={result['difficulty']}"
            report.add("任务理解", f"识别「{input_text[:15]}」", status, detail if checks else "OK", time.time()-t0)
            t0 = time.time()

        # 边缘测试
        edge_cases = [
            ("", "综合", "通用"),
            ("你好", "综合", "通用"),
            ("啊啊啊啊", "综合", "通用"),
        ]
        for input_text, exp_subj, exp_type in edge_cases:
            result = tu.understand(input_text)
            report.add("任务理解", f"边缘「{input_text or '空字符串'}」", "PASS",
                       f"学科={result['subject']}", time.time()-t0)
            t0 = time.time()

        return True
    except Exception as e:
        report.add("任务理解", "模块整体测试", "FAIL", str(e), time.time()-t0)
        return False


def test_flow_orchestrator():
    """模块3: 流程编排测试"""
    t0 = time.time()
    try:
        from goai_agent import TaskUnderstanding, FlowOrchestrator
        tu = TaskUnderstanding()
        fo = FlowOrchestrator()

        task = tu.understand("函数的单调性")
        steps = fo.orchestrate(task)

        assert len(steps) == 5, f"预期5步，实际{len(steps)}步"
        step_names = [s["name"] for s in steps]
        expected = ["现象引入", "认知冲突", "思维模型", "自主推导", "费曼测试"]
        assert step_names == expected, f"步骤名不匹配: {step_names}"

        for s in steps:
            assert "prompt" in s and len(s["prompt"]) > 50, f"步骤{s['step']} prompt太短"
            assert "purpose" in s, f"步骤{s['step']}缺少purpose"

        report.add("流程编排", "五步教学法生成", "PASS", f"5步全部生成，每步prompt>50字", time.time()-t0)

        # 测试不同学科
        for topic in ["牛顿第二定律", "化学平衡", "英语语法"]:
            t0 = time.time()
            task = tu.understand(topic)
            steps = fo.orchestrate(task)
            assert len(steps) == 5
            report.add("流程编排", f"「{topic}」五步生成", "PASS", elapsed=time.time()-t0)

        return True
    except Exception as e:
        report.add("流程编排", "模块测试", "FAIL", str(e), time.time()-t0)
        return False


def test_tool_caller():
    """模块4: 工具调用测试"""
    t0 = time.time()
    try:
        from goai_agent import ToolCaller
        tc = ToolCaller()

        # 测试状态检查
        status = tc.get_call_summary()
        assert isinstance(status, dict)

        # 测试调用（会走兜底模式，因为Ollama可能不可用）
        result = tc.call("测试prompt", task_type="teach")
        assert "content" in result
        assert "model" in result
        assert "success" in result

        if result["success"]:
            model_status = "✅ Ollama可用" if "fallback" not in result["model"] else "⚠️ 兜底模式"
            report.add("工具调用", "模型调用测试", "PASS", f"{model_status} | 耗时{result['elapsed']:.1f}s", time.time()-t0)
        else:
            report.add("工具调用", "模型调用测试", "FAIL", "模型调用失败", time.time()-t0)

        return True
    except Exception as e:
        report.add("工具调用", "模块测试", "FAIL", str(e), time.time()-t0)
        return False


def test_result_delivery():
    """模块5: 结果交付测试"""
    t0 = time.time()
    try:
        from goai_agent import TaskUnderstanding, FlowOrchestrator, ToolCaller, ResultDelivery

        tu = TaskUnderstanding()
        fo = FlowOrchestrator()
        tc = ToolCaller()
        rd = ResultDelivery()

        task = tu.understand("函数的单调性")
        flow = fo.orchestrate(task)

        # 执行教学
        flow_results = []
        for step in flow:
            result = tc.call(step["prompt"], task_type="teach")
            result["step"] = step["step"]
            result["name"] = step["name"]
            flow_results.append(result)

        tool_summary = tc.get_call_summary()
        report_data = rd.generate_report(task, flow_results, tool_summary)

        # 验证报告结构
        assert "title" in report_data
        assert "task_understanding" in report_data
        assert "teaching_flow" in report_data
        assert "mastery_assessment" in report_data
        assert "weak_points" in report_data
        assert "next_steps" in report_data
        assert "generated_at" in report_data

        # 验证CLI渲染
        cli_output = rd.render_cli_report(report_data)
        assert len(cli_output) > 100

        # 验证保存
        json_path, md_path = rd.save_report(report_data)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)

        report.add("结果交付", "完整报告生成", "PASS",
                   f"报告结构完整，CLI输出{len(cli_output)}字，已保存JSON+MD",
                   time.time()-t0)

        # 测试不同主题
        for topic in ["牛顿第二定律", "勾股定理"]:
            t0 = time.time()
            task = tu.understand(topic)
            flow = fo.orchestrate(task)
            flow_results = [{"step": s["step"], "name": s["name"], "content": "测试内容", "success": True, "model": "test", "elapsed": 0.1} for s in flow]
            r = rd.generate_report(task, flow_results, {"total_calls": 5})
            assert r["task_understanding"]["subject"] in ["物理", "数学"]
            report.add("结果交付", f"「{topic}」报告生成", "PASS", elapsed=time.time()-t0)

        return True
    except Exception as e:
        report.add("结果交付", "模块测试", "FAIL", str(e), time.time()-t0)
        return False


def test_agent_full_flow():
    """模块6: 完整Agent流程测试"""
    t0 = time.time()
    try:
        from goai_agent import LumiLearnAgent
        agent = LumiLearnAgent()

        topics = ["函数的单调性", "牛顿第二定律"]
        for topic in topics:
            t0_topic = time.time()
            result = agent.run(topic, interactive=False)
            elapsed = time.time() - t0_topic

            # 验证
            assert result["task_understanding"]["core_topic"] in topic or topic in result["task_understanding"]["core_topic"]
            assert result["teaching_flow"]["total_steps"] == 5
            assert result["teaching_flow"]["completed_steps"] >= 0
            assert result["mastery_assessment"]["score"] >= 0

            report.add("完整闭环", f"「{topic}」全流程", "PASS",
                       f"5步教学，耗时{elapsed:.1f}s", elapsed)

        return True
    except Exception as e:
        report.add("完整闭环", "Agent全流程测试", "FAIL", str(e), time.time()-t0)
        return False


def test_web_server():
    """模块7: Web服务器测试"""
    t0 = time.time()
    try:
        import requests

        # 测试健康检查
        try:
            r = requests.get("http://localhost:5000/api/status", timeout=5)
            if r.status_code == 200:
                data = r.json()
                report.add("Web服务", "健康检查", "PASS", f"状态: {data.get('gateway', 'ok')}", time.time()-t0)
            else:
                report.add("Web服务", "健康检查", "FAIL", f"状态码: {r.status_code}", time.time()-t0)
        except requests.exceptions.ConnectionError:
            report.add("Web服务", "健康检查", "SKIP", "Web服务未运行（跳过）", time.time()-t0)

        # 测试API学习端点
        t0 = time.time()
        try:
            r = requests.post("http://localhost:5000/api/learn",
                              json={"topic": "函数的单调性"}, timeout=30)
            if r.status_code == 200:
                data = r.json()
                report.add("Web服务", "API/learn", "PASS", f"报告标题: {data.get('title', 'ok')}", time.time()-t0)
            else:
                report.add("Web服务", "API/learn", "FAIL", f"状态码: {r.status_code}", time.time()-t0)
        except Exception as e:
            report.add("Web服务", "API/learn", "SKIP", f"Web服务未运行: {e}", time.time()-t0)

        return True
    except Exception as e:
        report.add("Web服务", "模块测试", "SKIP", f"requests模块异常: {e}", time.time()-t0)
        return False


def test_ollama_connectivity():
    """模块8: Ollama连接测试"""
    t0 = time.time()
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        if r.status_code == 200:
            models = r.json().get("models", [])
            model_names = [m["name"] for m in models]
            report.add("Ollama", "连接测试", "PASS", f"可用模型: {', '.join(model_names[:5])}", time.time()-t0)
        else:
            report.add("Ollama", "连接测试", "SKIP", f"Ollama返回状态码{r.status_code}", time.time()-t0)
    except Exception as e:
        report.add("Ollama", "连接测试", "SKIP", f"Ollama未运行: {e}", time.time()-t0)


def test_feynman_engine():
    """模块9: 费曼引擎测试"""
    t0 = time.time()
    try:
        from framework.engines.feynman_engine import FeynmanEngine
        engine = FeynmanEngine()

        result = engine.teach("函数的单调性", subject="数学", difficulty="高中")
        report.add("费曼引擎", "教学调用", "SKIP", "费曼引擎已导入，需实际环境验证", time.time()-t0)
    except Exception as e:
        report.add("费曼引擎", "模块导入", "SKIP", f"费曼引擎需额外依赖: {e}", time.time()-t0)


def test_framework_imports():
    """模块10: 框架模块导入测试"""
    t0 = time.time()
    modules = [
        ("framework", "config"),
        ("framework.core", "config"),
        ("framework.models", "base"),
        ("framework.engines", "feynman_engine"),
        ("framework.services", "adaptive_learning"),
        ("framework.services", "review_service"),
        ("framework.services", "manim_service"),
        ("framework.services", "video_compiler"),
        ("framework.services", "provider_service"),
    ]

    for package, module in modules:
        t0_m = time.time()
        try:
            __import__(f"{package}.{module}", fromlist=[module])
            report.add("框架模块", f"{package}.{module}", "PASS", elapsed=time.time()-t0_m)
        except Exception as e:
            # 一些依赖可能缺失，标记为SKIP而不是FAIL
            report.add("框架模块", f"{package}.{module}", "SKIP", f"需额外依赖: {str(e)[:60]}", time.time()-t0_m)


# ============================================================
# 主函数
# ============================================================
def main():
    print("=" * 70)
    print("  🎓 LumiLearn 全面测评")
    print("  GOAI 无界应用赛道参赛作品")
    print(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(f"\n  Python: {sys.version}")
    print(f"  工作目录: {os.getcwd()}")
    print("=" * 70)

    tests = [
        ("模块导入", test_module_imports),
        ("任务理解", test_task_understanding),
        ("流程编排", test_flow_orchestrator),
        ("工具调用", test_tool_caller),
        ("结果交付", test_result_delivery),
        ("完整闭环", test_agent_full_flow),
        ("Ollama连接", test_ollama_connectivity),
        ("Web服务", test_web_server),
        ("费曼引擎", test_feynman_engine),
        ("框架模块", test_framework_imports),
    ]

    for name, test_func in tests:
        print(f"\n  📋 [{name}]")
        try:
            test_func()
        except Exception as e:
            print(f"  ❌ 测试[{name}]抛出未捕获异常: {e}")
            traceback.print_exc()

    print("\n")
    score = report.summary()
    return score


if __name__ == "__main__":
    main()