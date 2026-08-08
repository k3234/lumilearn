#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn GOAI 演示脚本
========================
演示完整流程：启动服务 → API调用 → 生成报告

运行方式：
  python goai_demo.py
"""

import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from goai_agent import LumiLearnAgent


def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step, text):
    """打印步骤"""
    print(f"\n  [{step}] {text}")


def demo_cli():
    """CLI模式演示"""
    print_header("🎓 LumiLearn AI 教官 — CLI Demo")

    agent = LumiLearnAgent()
    status = agent.get_status()
    print(f"\n  模型状态: {'✅ Ollama可用' if status['ollama_available'] else '⚠️ 兜底模式'}")
    print(f"  使用模型: {status['model']}")

    demo_topics = [
        "我想理解函数的单调性",
        "牛顿第二定律",
        "化学平衡移动",
    ]

    for topic in demo_topics:
        print_step(1, f"用户输入: {topic}")
        report = agent.run(topic, interactive=True)

    return report


def demo_api():
    """API模式演示"""
    print_header("🌐 LumiLearn AI 教官 — API Demo")

    print("""
  运行以下命令测试API:

  curl -X POST http://localhost:5000/api/learn \\
    -H "Content-Type: application/json" \\
    -d '{"topic":"函数的单调性"}'
""")

    print("  Web服务已启动: http://localhost:5000")
    print("  在浏览器中打开，输入学习目标即可体验完整流程")


def main():
    print("\n" + "=" * 60)
    print("  🎓 LumiLearn AI 教官 — GOAI 演示脚本")
    print("  教育智能体核心引擎")
    print("=" * 60)

    print("\n  选择演示模式：")
    print("  1. CLI模式（终端演示）")
    print("  2. API模式（查看Web服务）")
    print("  3. 完整流程（CLI + API）")

    choice = input("\n  请输入选项 (1-3): ").strip()

    if choice == "1":
        demo_cli()
    elif choice == "2":
        demo_api()
    elif choice == "3":
        demo_cli()
        demo_api()
    else:
        print("  无效选项")


if __name__ == "__main__":
    main()
