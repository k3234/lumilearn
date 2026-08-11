#!/usr/bin/env python3
"""真实学习场景模拟测试 - 修正路径"""
import json, time, sys, os
# 切换到 lumilearn 目录（环境变量 LUMILEARN_DIR 可覆盖，默认自动探测）
_PROJECT_ROOT = os.environ.get("LUMILEARN_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, _PROJECT_ROOT)

from goai_agent import LumiLearnAgent

print("=" * 70)
print("  🎓 LumiLearn 真实学习场景模拟测试")
print("=" * 70)

# 初始化 agent（连远程服务器 Ollama）
agent = LumiLearnAgent()
print(f"\n📊 Agent 状态:")
print(f"   模型: {agent.tool_caller.preferred_model}")
print(f"   Ollama: {'✅ 可用' if agent.tool_caller.available else '❌ 不可用'}")
print(f"   API: {agent.tool_caller.ollama_url}")

# 测试用例
test_scenarios = [
    {"name": "数学-勾股定理", "topic": "用费曼五步法讲解勾股定理"},
    {"name": "化学-共价键", "topic": "什么是共价键？水分子中氢和氧是怎么结合的？"},
    {"name": "物理-牛顿定律", "topic": "牛顿第二定律 F=ma 怎么用？举几个例子"},
    {"name": "生物-光合作用", "topic": "光合作用分为几个阶段？详细讲解每个阶段"},
]

results = []
total_time = 0.0

for i, scenario in enumerate(test_scenarios, 1):
    print(f"\n{'=' * 70}")
    print(f"  场景 {i}: {scenario['name']}")
    print(f"  问题: {scenario['topic']}")
    print(f"{'=' * 70}")
    
    t0 = time.time()
    report = agent.run(scenario["topic"], interactive=False)
    elapsed = time.time() - t0
    total_time += elapsed
    
    steps = report["teaching_flow"]
    completed = steps["completed_steps"]
    total = steps["total_steps"]
    
    print(f"\n  ✅ 完成 ({elapsed:.1f}s)")
    print(f"     步骤: {completed}/{total}")
    print(f"     掌握度: {report['mastery_assessment']['level']} ({report['mastery_assessment']['score']}分)")
    
    # 保存报告
    ts = int(time.time())
    report_file = f"goai_output/test_{ts}_{scenario['name'][:8]}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    results.append({
        "scenario": scenario["name"],
        "success": completed == total,
        "steps": f"{completed}/{total}",
        "mastery": report["mastery_assessment"]["level"],
        "time_s": elapsed,
        "file": report_file,
    })

# 汇总
print(f"\n{'=' * 70}")
print("  📊 测试汇总")
print(f"{'=' * 70}")
print(f"  总场景: {len(results)}")
print(f"  成功: {sum(1 for r in results if r['success'])}/{len(results)}")
print(f"  总耗时: {total_time:.1f}s (平均 {total_time/len(results):.1f}s/场景)")
print(f"\n  详细结果:")
for r in results:
    status = "✅" if r["success"] else "❌"
    print(f"     {status} {r['scenario'][:15]:<15} | 步骤 {r['steps']} | 掌握 {r['mastery']} | {r['time_s']:.1f}s")

summary = agent.tool_caller.get_call_summary()
print(f"\n  工具调用: {summary['total_calls']} 次 | 成功率 {summary['success_rate']:.0%} | 平均 {summary['avg_elapsed']:.1f}s/次")

all_success = all(r["success"] for r in results)
print(f"\n{'=' * 70}")
print(f"  {'🎉 全部通过！' if all_success else '⚠️ 部分失败'}")
print(f"{'=' * 70}")
