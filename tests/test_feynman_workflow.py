#!/usr/bin/env python3
"""费曼五步教学流程完整性测试"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(r"e:\学习LLM\lumilearn")

import requests
import json

print("=" * 70)
print("  费曼五步教学流程完整性测试")
print("=" * 70)

# 测试主题
test_cases = [
    {
        "name": "数学-勾股定理",
        "topic": "用费曼五步法讲解勾股定理"
    },
    {
        "name": "化学-共价键",
        "topic": "解释化学键中的共价键"
    },
    {
        "name": "物理-牛顿定律",
        "topic": "牛顿第二定律 F=ma 怎么用"
    },
    {
        "name": "生物-光合作用",
        "topic": "光合作用的过程是怎样的"
    },
]

steps_required = ["现象引入", "认知冲突", "思维模型", "自主推导", "费曼测试"]
results = []

print(f"\n测试 {len(test_cases)} 个主题的教学流程...")
print("-" * 70)

for case in test_cases:
    print(f"\n[{case['name']}]")
    try:
        r = requests.post(
            "http://localhost:5000/api/learn",
            json={"topic": case["topic"]},
            timeout=300
        )
        
        if r.status_code == 200:
            data = r.json()
            steps = data.get("teaching_flow", {}).get("steps_detail", [])
            
            # 检查步骤完整性
            all_steps_ok = True
            steps_found = []
            
            for step in steps:
                step_name = step.get("name", "")
                content = step.get("content", "")
                success = step.get("success", False)
                
                if step_name:
                    steps_found.append(step_name)
                
                if not success or not content:
                    all_steps_ok = False
                    print(f"   ❌ {step_name}: 步骤失败或内容为空")
            
            # 检查是否包含所有 5 步
            missing_steps = [s for s in steps_required if s not in steps_found]
            
            if missing_steps:
                print(f"   ❌ 缺少步骤: {missing_steps}")
                all_steps_ok = False
            
            # 检查内容质量
            total_chars = sum(len(s.get("content", "")) for s in steps)
            avg_chars = total_chars / len(steps) if steps else 0
            
            # 检查掌握度
            mastery = data.get("mastery_assessment", {}).get("level", "N/A")
            mastery_score = data.get("mastery_assessment", {}).get("score", 0)
            
            # 检查工具调用
            tool_usage = data.get("tool_usage", {})
            total_calls = tool_usage.get("total_calls", 0)
            success_rate = tool_usage.get("success_rate", 0)
            
            status = "✅" if all_steps_ok else "❌"
            print(f"   {status} 完成: {len(steps)}/5 步")
            print(f"      步骤: {', '.join(steps_found)}")
            print(f"      掌握度: {mastery} ({mastery_score}分)")
            print(f"      平均内容长度: {avg_chars:.0f} 字/步")
            print(f"      工具调用: {total_calls} 次, 成功率 {success_rate:.0%}")
            
            results.append({
                "name": case["name"],
                "success": all_steps_ok and len(steps) == 5,
                "steps": len(steps),
                "mastery": mastery,
                "avg_chars": avg_chars,
            })
        else:
            print(f"   ❌ HTTP {r.status_code}")
            results.append({"name": case["name"], "success": False, "error": f"HTTP {r.status_code}"})
            
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        results.append({"name": case["name"], "success": False, "error": str(e)})

# 汇总
print("\n" + "=" * 70)
print("  教学流程完整性测试汇总")
print("=" * 70)
passed = sum(1 for r in results if r.get("success"))
print(f"   总测试: {len(results)}")
print(f"   通过: {passed}")
print(f"   失败: {len(results) - passed}")
print(f"   通过率: {passed / len(results) * 100:.0f}%")

if passed == len(results):
    print("\n   🎉 费曼五步教学流程完整性测试通过")
else:
    print("\n   ⚠️ 部分测试失败")
    
    print("\n失败详情:")
    for r in results:
        if not r.get("success"):
            print(f"   - {r['name']}: {r.get('error', '步骤不完整')}")
