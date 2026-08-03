#!/usr/bin/env python3
"""
灵学 lumilearn - 费曼教学模板
预定义的费曼五步法教学模板库
"""
from typing import Dict, Optional

# 费曼五步法教学模板
FEYNMAN_TEMPLATES: Dict[str, Dict[str, Dict[str, str]]] = {
    "math": {
        "geometry": {
            "phenomenon": "想象你正在帮家里装修，需要知道地板要买多少。这时候你就需要计算房间的面积。几何就是从生活中这样的实际问题开始的。",
            "conflict": "你可能觉得面积就是长乘以宽，但如果是奇怪形状的房间呢？比如三角形、圆形的房间？",
            "model": "把几何图形想象成拼图。每个图形都有自己固定的'公式密码'，就像拼图的边缘决定了它能放在哪里。",
            "derive": "让我们从最简单的正方形开始。如果边长是3，面积就是3×3=9。那长方形呢？长4宽2，就是4×2=8。你发现了什么规律？",
            "test": "现在请你用自己的话，向一个完全不懂的人解释什么是面积。记住，要用最简单的话！"
        },
        "algebra": {
            "phenomenon": "你有10块钱，想买一些2块钱的铅笔。你能买几支？这就是方程——用数学方式表示现实问题。",
            "conflict": "如果铅笔涨价了，变成3块钱一支，你的10块钱还能买几支？为什么结果不是整数？",
            "model": "把方程想象成一个天平。左边是已知数，右边是未知数。天平平衡时，两边相等。",
            "derive": "如果 x + 3 = 10，怎么求 x？提示：天平两边同时减去相同的数，还平衡吗？",
            "test": "用自己的话解释什么是方程，以及为什么要学方程。"
        },
        "default": {
            "phenomenon": "数学无处不在——从购物找零到规划时间，我们每天都在用数学。",
            "conflict": "你觉得数学只是计算吗？其实数学是一种思考方式，帮助我们理解世界。",
            "model": "把数学想象成一种语言，就像英语表达思想一样，数学表达逻辑关系。",
            "derive": "让我们从一个简单的问题开始，看看数学怎么帮我们解决它。",
            "test": "用自己的话解释这个数学概念，就像教一个完全不懂的朋友。"
        }
    },
    "physics": {
        "mechanics": {
            "phenomenon": "你推一个箱子，它会动；你松手，它慢慢停下来。为什么？这就是力学研究的问题。",
            "conflict": "亚里士多德认为'力是维持运动的原因'，但牛顿说不对。到底谁对？",
            "model": "把力想象成推或拉。没有推或拉，物体会保持原来的状态——静止或匀速运动。",
            "derive": "如果物体不受力，它会怎样运动？提示：想象一个完全光滑的平面。",
            "test": "用自己的话解释什么是力，以及力和运动的关系。"
        },
        "electromagnetism": {
            "phenomenon": "冬天脱毛衣时会有火花，下雨天会打雷。这些都是电的现象。",
            "conflict": "电是什么？它像水一样流动吗？还是像小球一样是一个个粒子？",
            "model": "把电想象成水流。电压是水压，电流是水流，电阻是水管的粗细。",
            "derive": "如果电压增大，电流会怎样变化？提示：想象水压变大，水流会怎样？",
            "test": "用自己的话解释什么是电流、电压和电阻。"
        },
        "default": {
            "phenomenon": "物理研究的是自然界的基本规律——从苹果落地到星星运动。",
            "conflict": "物理只是公式和计算吗？其实物理是理解宇宙的语言。",
            "model": "把物理规律想象成游戏规则。宇宙按照这些规则运行，物理就是发现这些规则。",
            "derive": "让我们观察一个现象，看看能不能发现背后的规律。",
            "test": "用自己的话解释这个物理概念，就像给完全不懂的人讲。"
        }
    },
    "chemistry": {
        "reaction": {
            "phenomenon": "铁生锈、木材燃烧，这些都是化学变化。物质变成了新的物质。",
            "conflict": "化学变化和物理变化有什么区别？水结冰是化学变化吗？",
            "model": "把化学反应想象成重新排列积木。原子还是那些原子，但组合方式变了。",
            "derive": "如果反应前后原子种类不变，质量会变吗？提示：想想积木重组前后总重量。",
            "test": "用自己的话解释什么是化学变化，以及它和物理变化的区别。"
        },
        "default": {
            "phenomenon": "化学研究的是物质的组成、结构和变化。从烹饪到制药，化学无处不在。",
            "conflict": "化学只是元素周期表吗？其实化学是理解物质世界的钥匙。",
            "model": "把物质想象成由积木（原子）搭成的不同结构。不同的搭法就是不同的物质。",
            "derive": "让我们观察一种物质，看看它是由什么组成的。",
            "test": "用自己的话解释这个化学概念。"
        }
    },
    "english": {
        "grammar": {
            "phenomenon": "我们每天说很多话，但为什么有些话听起来很顺，有些很别扭？这就是语法在起作用。",
            "conflict": "语法只是规则吗？但为什么很多外国人也不遵守这些规则？",
            "model": "把语法想象成交通规则。它让语言'交通'有序，避免'撞车'（误解）。",
            "derive": "如果一句话没有语法，会怎样？提示：想象没有红绿灯的十字路口。",
            "test": "用自己的话解释为什么需要语法。"
        },
        "default": {
            "phenomenon": "英语是一种语言，用来交流思想、表达情感。",
            "conflict": "学英语只是背单词吗？其实英语是一种思维方式。",
            "model": "把英语想象成另一种'操作系统'。学会它，你就能访问另一个世界。",
            "derive": "让我们从简单的表达开始，看看英语怎么组织思想。",
            "test": "用自己的话解释这个英语概念。"
        }
    },
    "general": {
        "default": {
            "phenomenon": "让我们从生活中的现象开始，看看背后有什么知识。",
            "conflict": "你可能觉得这个概念很简单，但真的是这样吗？",
            "model": "把这个概念想象成你熟悉的东西，让抽象变具体。",
            "derive": "让我们一步步推导，看看你能自己得出结论吗？",
            "test": "用自己的话解释这个概念，就像教一个完全不懂的朋友。"
        }
    }
}


def get_template(subject: str, topic_type: str, step: str, topic: str = "") -> str:
    """
    获取费曼教学模板
    
    参数:
        subject: 学科 (math/physics/chemistry/english/general)
        topic_type: 主题类型 (geometry/algebra/mechanics/...)
        step: 步骤 (phenomenon/conflict/model/derive/test)
        topic: 教学主题（可选，用于未来扩展）
        
    返回:
        模板字符串
    """
    subject_templates = FEYNMAN_TEMPLATES.get(subject, FEYNMAN_TEMPLATES["general"])
    type_templates = subject_templates.get(topic_type, subject_templates.get("default", {}))
    template = type_templates.get(step, "")
    
    if not template:
        # 返回通用模板
        general = FEYNMAN_TEMPLATES["general"]["default"]
        template = general.get(step, f"请用简单的语言解释这个概念。")
    
    return template


def get_all_templates() -> Dict:
    """获取所有模板"""
    return FEYNMAN_TEMPLATES


def add_template(subject: str, topic_type: str, step: str, template: str):
    """
    添加自定义模板
    
    参数:
        subject: 学科
        topic_type: 主题类型
        step: 步骤
        template: 模板内容
    """
    if subject not in FEYNMAN_TEMPLATES:
        FEYNMAN_TEMPLATES[subject] = {}
    if topic_type not in FEYNMAN_TEMPLATES[subject]:
        FEYNMAN_TEMPLATES[subject][topic_type] = {}
    
    FEYNMAN_TEMPLATES[subject][topic_type][step] = template
