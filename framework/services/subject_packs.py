# -*- coding: utf-8 -*-
"""物化生学科深度包（先做物理）。

以结构化常量提供高中理科核心章节的「教学先验」：权威要点、前置依赖、
易错点、适配年级。供幻灯片/讲义生成链路在命中对应章节时注入，使生成
内容从「自由发挥」变为「有教材依据」，同时向下兼容未命中的自由生成。

定位：轻量、离线、低配置可跑，与 KNOWLEDGE_GRAPH 内存节点的产品风格一致。
规模化为全学科入库留到 P3。
"""

from typing import Dict, List, Optional

# 章节知识节点结构：
#   id/name/category/grade       — 标识与学段
#   difficulty(1-5)/prerequisites — 学习路径与前置
#   key_points[权威要点]          — 生成时作为教材先验注入
#   misconceptions[易错点]        — 供生成侧规避常见错误
#   aliases[命中词]               — 用于按 topic 自动匹配章节
PHYSICS_PACK: List[Dict] = [
    {
        "id": "motion",
        "name": "匀变速直线运动",
        "category": "physics/mechanics",
        "grade": "高一",
        "difficulty": 2,
        "prerequisites": ["位移/速度/加速度的基本概念"],
        "aliases": ["匀变速", "直线运动", "自由落体", "运动学", "v-t 图像", "vt图像"],
        "key_points": [
            "匀变速直线运动：加速度 a 恒定，速度均匀变化，v-t 图像为一条直线。",
            "三个核心公式：v = v0 + at；s = v0t + ½at²；v² − v0² = 2as。",
            "自由落体是 v0 = 0、a = g（约 9.8 m/s²）的匀加速直线运动特例。",
            "解题先定正方向，再统一符号；v-t 图线下方面积 = 位移。",
        ],
        "misconceptions": [
            "误把速度大小当平均速度；速度为零并不代表静止加速度为零。",
            "自由落体忽略空气阻力，是理想化模型；物体下落快慢不由质量决定。",
        ],
    },
    {
        "id": "newton",
        "name": "牛顿运动定律",
        "category": "physics/mechanics",
        "grade": "高一",
        "difficulty": 3,
        "prerequisites": ["力的合成与分解", "运动学基本公式"],
        "aliases": ["牛顿", "牛顿定律", "牛顿三定律", "惯性", "作用力反作用力", "受力分析"],
        "key_points": [
            "牛顿第一定律：物体保持静止或匀速直线运动状态，除非受外力迫使改变（惯性定律）。",
            "牛顿第二定律：F = ma，力是物体产生加速度的原因，加速度方向与合力方向一致。",
            "牛顿第三定律：作用力与反作用力大小相等、方向相反、作用在不同物体上。",
            "受力分析顺序：重力→弹力→摩擦力→其他力；沿运动方向和垂直方向正交分解。",
        ],
        "misconceptions": [
            "作用力与反作用力不能相互抵消，因作用对象不同；f = μN 中的 N 不一定等于重力。",
            "合力为零时物体可能匀速运动而非静止；不要遗漏摩擦力的有无与方向判断。",
        ],
    },
    {
        "id": "momentum",
        "name": "动量守恒定律",
        "category": "physics/mechanics",
        "grade": "高二",
        "difficulty": 3,
        "prerequisites": ["牛顿定律", "冲量与动量概念"],
        "aliases": ["动量", "动量守恒", "碰撞", "弹性碰撞", "反冲", "火箭"],
        "key_points": [
            "动量 p = mv；冲量 I = Ft；动量定理：合外力的冲量等于动量变化。",
            "动量守恒条件：系统所受合外力为零（近似：内力>>外力，如碰撞、爆炸）。",
            "碰撞分类：弹性碰撞（动量+动能都守恒）、非弹性碰撞（仅动量守恒）、完全非弹性碰撞（碰后同速）。",
            "应用：反冲运动（火箭推进）、子弹打木块、两球相撞。",
        ],
        "misconceptions": [
            "动量守恒的前提是系统合外力为零，不是单个物体；不是所有碰撞都动能守恒。",
            "动量是矢量，列方程须先定正方向；完全非弹性碰撞动能损失最大但不违反动量守恒。",
        ],
    },
    {
        "id": "em_induction",
        "name": "电磁感应",
        "category": "physics/electromagnetism",
        "grade": "高二",
        "difficulty": 4,
        "prerequisites": ["磁通量概念", "闭合电路欧姆定律", "楞次定律"],
        "aliases": ["电磁感应", "楞次定律", "法拉第", "感生电动", "动生电动", "磁通量"],
        "key_points": [
            "产生感应电流的条件：穿过闭合回路的磁通量发生变化。",
            "法拉第电磁感应定律：感应电动势 E = n·ΔΦ/Δt。",
            "楞次定律：感应电流的磁场总要阻碍引起感应电流的磁通量的变化（增反减同）。",
            "动生电动势：导体垂直切割磁感线时 E = B·l·v。",
        ],
        "misconceptions": [
            "磁通量大不等于变化率大，感应电动势由 ΔΦ/Δt 决定而非 Φ 本身。",
            "楞次定律判断的是「阻碍变化」而非「阻碍磁场」；区分感应电流方向与感应电动势方向。",
        ],
    },
    {
        "id": "bohr_atom",
        "name": "玻尔原子模型",
        "category": "physics/atomic",
        "grade": "高二",
        "difficulty": 3,
        "prerequisites": ["原子的核式结构", "能量守恒与频率概念"],
        "aliases": ["玻尔", "原子模型", "能级", "跃迁", "光谱", "氢原子"],
        "key_points": [
            "三条假设：定态（轨道能量量子化）、跃迁（吸收/辐射光子 hν = E₂ − E₁）、轨道半径量子化。",
            "氢原子能级：Eₙ = −13.6/n² eV；基态 −13.6 eV。",
            "能级跃迁吸收/放出光子，光子频率由两能级能量差决定；辐射光谱为线状。",
            "极限：玻尔模型只对氢原子及类氢离子精确成立，解释了氢原子光谱。",
        ],
        "misconceptions": [
            "能级跃迁吸收/放出的是两能级差对应的特定频率光子，不是任意频率。",
            "电子在不同轨道能量不同，但基态能量最低最稳定；电离需要吸收 ≥ 电离能。",
        ],
    },
]

# 命中顺序即优先级（先定义的章节优先匹配）
_PACK_INDEX = {b["id"]: b for b in PHYSICS_PACK}


def resolve_pack(topic: str) -> Optional[Dict]:
    """按主题名关键词匹配物理深度包章节；未命中返回 None。

    匹配规则：对 topic 小写化后，若「关键字出现在主题中」或「主题短词与关键字
    重叠」即命中。用于生成链路判断是否需要注入教学先验。
    """
    if not topic:
        return None
    t = topic.lower().strip()
    for node in PHYSICS_PACK:
        for alias in node["aliases"]:
            a = alias.lower().strip()
            if not a:
                continue
            # 别名是主题的一部分，或主题是单个关键词的精确命中
            if a in t or (len(t) <= 8 and t in node["name"].lower()):
                return node
    return None


def pack_prior(node: Dict) -> str:
    """把章节先验渲染为可注入生成 prompt 的教材依据文本。"""
    keys = "\n".join(f"· {k}" for k in node.get("key_points", []))
    slow = "\n".join(f"· {m}" for m in node.get("misconceptions", []))
    prereq = "、".join(node.get("prerequisites", [])) or "无"
    return (
        f"【教材先验 · {node['name']}（{node.get('grade', '')}·难度{node.get('difficulty', 2)}）】\n"
        f"重要知识点（生成时必须准确体现，不得与之矛盾）：\n{keys}\n"
        f"常见易错点（应规避或辨析）：\n{slow}\n"
        f"前置知识：{prereq}"
    )


def list_packs() -> List[Dict]:
    """返回深度包章节清单（简要，供管理端/前端展示）。"""
    return [
        {"id": b["id"], "name": b["name"], "category": b["category"],
         "grade": b["grade"], "difficulty": b["difficulty"],
         "prerequisites": b["prerequisites"]}
        for b in PHYSICS_PACK
    ]