#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn GOAI Demo — 演示素材生成助手
============================================
自动生成演示用的CLI截图内容和Web演示说明

运行方式：
  python goai_demo_helper.py
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from goai_agent import LumiLearnAgent, TaskUnderstanding, FlowOrchestrator


def generate_cli_demo_output():
    """生成CLI演示的标准输出"""
    print("\n" + "=" * 70)
    print("  📸 CLI演示标准输出（用于截图）")
    print("=" * 70)

    agent = LumiLearnAgent()

    demo_topics = [
        "我想理解函数的单调性",
        "帮我复习牛顿第二定律",
        "化学平衡移动原理",
    ]

    for topic in demo_topics:
        print(f"\n\n{'─' * 70}")
        print(f"  示例输入: {topic}")
        print(f"{'─' * 70}")
        report = agent.run(topic, interactive=True)

    return True


def generate_web_demo_guide():
    """生成Web演示操作指南"""
    guide = """
╔══════════════════════════════════════════════════════════════════════╗
║                   📸 Web演示操作指南                                  ║
╚══════════════════════════════════════════════════════════════════════╝

【演示流程】（预计2-3分钟）

1. 启动服务
   $ python goai_web.py
   → 显示 "浏览器访问: http://localhost:5000"

2. 打开浏览器
   → 访问 http://localhost:5000
   → 展示输入界面 + 快捷示例标签

3. 输入学习目标
   → 点击"函数的单调性"快捷标签
   → 或手动输入"我想理解函数的单调性"

4. 点击"开始学习"
   → 展示四阶段进度动画
   → 任务理解 → 流程编排 → 工具调用 → 结果交付

5. 查看学习报告
   → 任务理解卡片（学科/类型/难度/置信度）
   → 教学流程（费曼五步法）
   → 掌握度评估
   → 薄弱点分析
   → 下一步建议

【截图点位】（建议截图3-5张）

□ 截图1: 初始界面（输入框+快捷标签）
□ 截图2: 进度动画（四阶段执行中）
□ 截图3: 完整学习报告（任务理解+教学流程）
□ 截图4: 评估与建议（掌握度+薄弱点+下一步）
□ 截图5: CLI终端输出（可选，展示技术细节）

【演示话术】

"LumiLearn是一个教育智能体，它不只是回答问题，而是能完成
'任务理解→流程编排→工具调用→结果交付'的完整闭环。

比如学生说'我想理解函数的单调性'，系统会自动：
1. 识别这是数学-函数-高中难度的概念理解任务
2. 生成费曼五步教学流程
3. 调用AI模型执行每个教学步骤
4. 交付一份结构化的学习报告，包含掌握度评估和下一步建议

这正是一个教育智能体应该具备的核心能力。"
"""
    print(guide)
    return True


def generate_submission_checklist():
    """生成提交材料清单"""
    checklist = """
╔══════════════════════════════════════════════════════════════════════╗
║                   📋 GOAI提交材料清单                                 ║
╚══════════════════════════════════════════════════════════════════════╝

【必须提交】
□ 1. 项目报名帖（GitHub Issues/GOAI官网）
□ 2. 技术方案文档（GOAI_TECH_DOC.md）
□ 3. 可运行Demo（CLI + Web）
□ 4. GitHub仓库（公开可访问）

【加分项】
□ 5. 演示视频（2-3分钟，展示完整闭环）
□ 6. 演示截图（3-5张关键界面）
□ 7. 技术博客（架构解析/开发心得）
□ 8. 演进路线图（L3→L4→L5规划）

【仓库文件清单】
□ README.md（已更新，含GOAI信息）
□ goai_agent.py（核心引擎）
□ goai_web.py（Web Demo）
□ goai_requirements.txt（依赖文件）
□ GOAI_TECH_DOC.md（技术方案）
□ goai_demo_helper.py（本文件）
□ goai_output/（学习报告输出目录）

【提交前检查】
□ 所有文件已commit并push到GitHub
□ README.md能正确显示GOAI信息
□ goai_requirements.txt依赖可正确安装
□ CLI Demo可正常运行
□ Web Demo可正常访问
□ 无敏感信息/密钥泄露
"""
    print(checklist)
    return True


def main():
    print("\n" + "=" * 70)
    print("  🎯 LumiLearn GOAI Demo — 演示素材生成助手")
    print("=" * 70)

    print("\n  选择要生成的内容：")
    print("  1. CLI演示标准输出")
    print("  2. Web演示操作指南")
    print("  3. 提交材料清单")
    print("  4. 全部生成")

    choice = input("\n  请输入选项 (1-4): ").strip()

    if choice == "1":
        generate_cli_demo_output()
    elif choice == "2":
        generate_web_demo_guide()
    elif choice == "3":
        generate_submission_checklist()
    elif choice == "4":
        generate_cli_demo_output()
        generate_web_demo_guide()
        generate_submission_checklist()
    else:
        print("  无效选项")


if __name__ == "__main__":
    main()
