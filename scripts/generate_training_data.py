#!/usr/bin/env python3
"""
LumiLearn 训练数据生成器
从内置模板生成教育领域语料，支持多学科、多难度
"""
import json
import os
import random
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SUBJECTS = {
    "数学": {
        "topics": [
            "集合与逻辑", "函数与映射", "三角函数", "数列与极限",
            "导数与微分", "积分基础", "向量与几何", "概率与统计",
            "复数", "排列组合", "不等式", "解析几何",
        ],
        "templates": [
            "{topic}是数学中的重要概念。理解{topic}的核心在于掌握其定义和基本性质。",
            "在{topic}中，我们首先需要明确基本概念，然后通过例题来加深理解。",
            "{topic}的解题方法通常包括：分析已知条件、建立数学模型、求解并验证。",
            "学习{topic}时，建议从简单题目入手，逐步过渡到综合题。",
            "{topic}的常见题型有：基础概念题、计算题、证明题和应用题。",
            "要学好{topic}，关键是掌握其推导过程，而不是死记硬背公式。",
            "{topic}与其他知识点有密切联系，例如与函数、方程等概念相互关联。",
            "解决{topic}问题的策略：第一步，仔细审题；第二步，列出已知条件；第三步，选择合适的方法。",
        ],
    },
    "物理": {
        "topics": [
            "运动学", "牛顿定律", "功与能量", "动量守恒",
            "电场与磁场", "电路分析", "电磁感应", "热力学",
            "光学", "原子物理", "波动", "力学综合",
        ],
        "templates": [
            "{topic}是物理学的基础内容。理解{topic}需要建立清晰的物理图像。",
            "在{topic}中，核心公式是解题的关键，但更重要的是理解公式的物理意义。",
            "{topic}的实验是验证理论的重要手段，通过实验可以加深对概念的理解。",
            "学习{topic}时，要注意区分容易混淆的概念，如速度和速率、质量和重量。",
            "{topic}的解题思路：分析受力/运动状态 → 建立方程 → 求解 → 检验合理性。",
            "{topic}中的守恒定律是最强有力的工具，学会识别守恒条件是关键。",
            "在{topic}中，单位换算和量纲分析是避免错误的有效方法。",
        ],
    },
    "化学": {
        "topics": [
            "物质的量", "化学反应", "化学平衡", "溶液与电离",
            "有机化学", "元素周期律", "化学键", "氧化还原反应",
            "电解质", "化学实验", "物质结构", "化学反应速率",
        ],
        "templates": [
            "{topic}是化学学科的核心内容。掌握{topic}需要理解微观与宏观的联系。",
            "在{topic}中，化学方程式的书写和配平是基本技能。",
            "{topic}的实验操作需要规范，注意安全，同时要仔细观察实验现象。",
            "学习{topic}时，要学会从结构决定性质、性质决定用途的角度思考。",
            "{topic}的常见考点：概念辨析、方程式书写、计算题和实验题。",
            "{topic}中，理解反应机理比记忆反应方程式更重要。",
        ],
    },
    "生物": {
        "topics": [
            "细胞结构", "光合作用", "呼吸作用", "遗传与变异",
            "进化论", "生态系统", "植物激素", "动物生理",
            "免疫系统", "基因工程", "种群生态", "生物技术",
        ],
        "templates": [
            "{topic}是生物学的重要知识点。在{topic}中，结构与功能相适应是核心思想。",
            "学习{topic}时，可以通过绘制概念图来梳理知识体系。",
            "{topic}的实验设计要遵循对照原则、单一变量原则和重复原则。",
            "在{topic}中，理解生命活动的调节机制是掌握该知识点的关键。",
            "{topic}的常见题型包括：选择题、填空题、简答题和实验设计题。",
        ],
    },
}

DIFFICULTY_LEVELS = {
    "基础": "这是{topic}的基础内容，需要牢固掌握。",
    "进阶": "这是{topic}的进阶内容，需要对基础有较好理解。",
    "综合": "这是{topic}的综合应用，需要融会贯通多个知识点。",
}

FEYNMAN_TEMPLATES = [
    "用最简单的话说，{topic}就是{simple_explain}。",
    "如果你要给一个完全不懂的人讲{topic}，你会怎么说？{simple_explain}。",
    "让我们用类比来理解{topic}：{simple_explain}。",
    "{topic}的本质是什么？{simple_explain}。",
]

SIMPLE_EXPLAINS = [
    "把一个复杂的问题拆成一个个简单的小问题，然后逐个解决。",
    "找到事物的规律，然后用这个规律去预测和解决问题。",
    "观察现象，提出假设，实验验证，得出结论。",
    "从已知条件出发，一步步推导出未知答案的过程。",
    "理解事物之间的关系，然后利用这些关系来解决问题。",
]


def generate_feynman_content(subject, topic):
    template = random.choice(FEYNMAN_TEMPLATES)
    explain = random.choice(SIMPLE_EXPLAINS)
    return template.format(topic=topic, simple_explain=explain)


def generate_teaching_content(subject, topic, difficulty):
    templates = SUBJECTS[subject]["templates"]
    base = random.choice(templates).format(topic=topic)
    diff_desc = DIFFICULTY_LEVELS[difficulty].format(topic=topic)
    feynman = generate_feynman_content(subject, topic)
    return f"{base} {diff_desc} {feynman}"


def generate_qa_pairs(subject, topic, difficulty):
    qa_templates = [
        ("请解释{topic}的核心概念。", "{topic}的核心概念是..."),
        ("{topic}有哪些常见题型？", "{topic}的常见题型包括..."),
        ("如何高效学习{topic}？", "高效学习{topic}的方法有..."),
        ("{topic}和其他知识点有什么联系？", "{topic}与其他知识点的联系包括..."),
        ("{topic}在实际生活中有什么应用？", "{topic}在实际生活中的应用包括..."),
    ]
    pairs = []
    for q_tpl, a_tpl in qa_templates:
        q = q_tpl.format(topic=topic)
        a = a_tpl.format(topic=topic)
        pairs.append({"question": q, "answer": a})
    return pairs


def main():
    random.seed(42)
    records = []

    for subject, info in SUBJECTS.items():
        for topic in info["topics"]:
            for difficulty in DIFFICULTY_LEVELS:
                for _ in range(3):
                    content = generate_teaching_content(subject, topic, difficulty)
                    records.append({
                        "subject": subject,
                        "chapter": topic,
                        "difficulty": difficulty,
                        "type": "teaching",
                        "content": content,
                    })
                qa_pairs = generate_qa_pairs(subject, topic, difficulty)
                for qa in qa_pairs:
                    records.append({
                        "subject": subject,
                        "chapter": topic,
                        "difficulty": difficulty,
                        "type": "qa",
                        "content": f"问：{qa['question']}\n答：{qa['answer']}",
                    })

    random.shuffle(records)

    output_path = DATA_DIR / "training_corpus.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"生成 {len(records)} 条训练数据")
    print(f"保存到: {output_path}")
    print(f"文件大小: {output_path.stat().st_size / 1024:.1f} KB")

    subjects_count = {}
    for rec in records:
        subjects_count[rec["subject"]] = subjects_count.get(rec["subject"], 0) + 1
    print(f"\n各学科数据量:")
    for subj, count in subjects_count.items():
        print(f"  {subj}: {count} 条")


if __name__ == "__main__":
    main()