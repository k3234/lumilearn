# -*- coding: utf-8 -*-
"""
费曼教学 → 动画联动桥接层
检测费曼五步法教学 → 提取主题 → 异步触发动画生成

核心功能：
- detect_feynman(): 检测响应是否包含费曼五步法结构
- extract_topic(): 从用户问题中提取教学主题和动画类型
- trigger_animation(): 异步触发动画生成，返回 task_id
- get_animation_for_feynman(): 一键集成接口

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-06
"""

import re
import uuid
import threading
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================
# 费曼五步法关键词检测
# ============================================================

FEYNMAN_STEP_KEYWORDS = {
    "观察与提问": [
        "观察", "提出问题", "现象", "看到", "发现", "注意到",
        "生活中", "日常", "为什么", "注意到",
    ],
    "设想与假设": [
        "设想", "假设", "猜测", "推测", "可能", "也许",
        "为了进一步理解", "可以假设", "定义一个",
    ],
    "推理与实验": [
        "推理", "实验", "推导", "证明", "验证", "测试",
        "设计实验", "动手", "计算", "演示",
    ],
    "分析与数据": [
        "分析", "数据", "计算", "统计", "测量",
        "整理", "对比", "比较", "总结",
    ],
    "结论与总结": [
        "结论", "总结", "得出", "因此", "所以",
        "根据上述", "可以得出", "综上所述", "揭示了",
    ],
}

# 费曼标题模式（如 **观察与提出问题**、### 设想和假设 等）
FEYNMAN_HEADER_PATTERNS = [
    r"\*\*观察[与和]提[出问].*?\*\*",
    r"\*\*设想[与和]假设.*?\*\*",
    r"\*\*推理[与和]实验.*?\*\*",
    r"\*\*分析[与和]数据.*?\*\*",
    r"\*\*结论[与和]总结.*?\*\*",
    r"#{1,3}\s*观察[与和]提[出问]",
    r"#{1,3}\s*设想[与和]假设",
    r"#{1,3}\s*推理[与和]实验",
    r"#{1,3}\s*分析[与和]数据",
    r"#{1,3}\s*结论[与和]总结",
]

# ============================================================
# 主题关键词 → 动画类型映射
# ============================================================

TOPIC_ANIMATION_MAP = {
    # 几何
    "geometry": {
        "keywords": [
            "勾股定理", "毕达哥拉斯", "pythagorean",
            "三角形", "三角", "锐角", "钝角", "直角",
            "圆", "圆周", "圆面积", "圆形", "半径", "直径",
            "余弦定理", "cosine", "正弦定理", "sine",
            "角度", "夹角", "几何", "多边形",
            "内角和", "外角", "相似", "全等",
        ],
        "templates": ["勾股定理", "余弦定理", "圆面积"],
    },
    # 公式/代数
    "formula": {
        "keywords": [
            "求根公式", "二次方程", "一元二次", "quadratic",
            "配方", "配方法", "completing square",
            "代数", "方程", "多项式", "因式分解",
            "函数", "一次函数", "二次函数",
        ],
        "templates": ["求根公式", "配方法"],
    },
    # 物理
    "physics": {
        "keywords": [
            "牛顿", "力学", "运动", "力", "加速度",
            "自由落体", "落体", "重力",
            "折射", "反射", "光学", "光",
            "斯涅尔", "snell",
            "速度", "位移", "动量", "能量",
            "物理", "定律",
        ],
        "templates": ["自由落体", "光的折射"],
    },
    # 函数
    "functions": {
        "keywords": [
            "一次函数", "二次函数", "函数图像", "函数图",
            "抛物线", "直线", "图像", "坐标系",
        ],
        "templates": [],
    },
    # 统计
    "statistics": {
        "keywords": [
            "均值", "中位数", "平均数", "方差", "标准差",
            "正态分布", "概率", "统计",
        ],
        "templates": [],
    },
}


def detect_feynman(response_text: str) -> Tuple[bool, int]:
    """
    检测响应是否包含费曼五步法教学结构

    Args:
        response_text: 模型生成的回复文本

    Returns:
        (是否检测到, 检测到的步骤数)
    """
    found_steps = 0
    for step_name, keywords in FEYNMAN_STEP_KEYWORDS.items():
        for kw in keywords:
            if kw in response_text:
                found_steps += 1
                break

    # 也检查标题模式（更精确的检测）
    if found_steps < 3:
        for pattern in FEYNMAN_HEADER_PATTERNS:
            if re.search(pattern, response_text):
                found_steps += 1
                if found_steps >= 3:
                    break

    return found_steps >= 3, found_steps


def extract_topic(user_input: str, response_text: str = "") -> Dict:
    """
    从用户输入中提取教学主题和动画类型

    Args:
        user_input: 用户提问
        response_text: 模型回复（可选，用于额外关键词匹配）

    Returns:
        {
            "topic": "勾股定理",        # 提取的主题名
            "scene_type": "geometry",   # 动画类型
            "template": "勾股定理",     # 匹配到的模板名
            "confidence": 0.9          # 置信度
        }
    """
    text = (user_input + " " + response_text[:300]).lower()
    best_match = None
    best_score = 0

    for scene_type, info in TOPIC_ANIMATION_MAP.items():
        for kw in info["keywords"]:
            score = 0
            if kw.lower() in text:
                # 精确匹配得分高
                if kw in user_input:
                    score = len(kw) * 2  # 用户直接提到的关键词
                else:
                    score = len(kw)  # 只在回复中出现

                if score > best_score:
                    # 找到匹配的模板
                    template = kw if kw in info["templates"] else (
                        info["templates"][0] if info["templates"] else kw
                    )
                    best_score = score
                    best_match = {
                        "topic": kw,
                        "scene_type": scene_type,
                        "template": template,
                        "confidence": min(score / 20.0, 1.0),
                    }

    if best_match:
        return best_match

    # 没有匹配到，返回通用信息
    return {
        "topic": user_input[:30],
        "scene_type": "auto",
        "template": None,
        "confidence": 0.0,
    }


def trigger_animation(topic: str, scene_type: str,
                      user_id: str = "default") -> Optional[str]:
    """
    触发异步动画生成

    Args:
        topic: 教学主题
        scene_type: 动画类型 (geometry/formula/physics/functions)
        user_id: 用户标识

    Returns:
        task_id 或 None（如果无法触发）
    """
    try:
        # 延迟导入，避免循环依赖
        from animation.pipeline import AnimationPipeline
        from framework.services.manim_service import ManimService

        task_id = str(uuid.uuid4())[:8]

        def _run():
            import asyncio
            try:
                pipeline = AnimationPipeline(
                    manim_service=ManimService(),
                    output_dir="output/animations"
                )
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        pipeline.generate(topic, scene_type)
                    )
                finally:
                    loop.close()

                # 记录到自适应学习引擎
                try:
                    from framework.services.adaptive_learning import get_adaptive_engine
                    engine = get_adaptive_engine()
                    engine.record_learning(
                        user_id=user_id,
                        node_id=topic,
                        score=0.8,
                        time_spent=result.get("duration", 0),
                    )
                except Exception:
                    pass

            except Exception as e:
                logger.error(f"费曼动画后台任务失败: topic={topic}, error={e}", exc_info=True)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        return task_id

    except Exception as e:
        logger.error(f"费曼动画触发失败: topic={topic}, scene_type={scene_type}, error={e}", exc_info=True)
        return None


def get_animation_for_feynman(user_input: str, response_text: str,
                              user_id: str = "default") -> Optional[Dict]:
    """
    一键接口：检测费曼教学 → 提取主题 → 触发动画

    Args:
        user_input: 用户提问
        response_text: 模型回复
        user_id: 用户标识

    Returns:
        None 或 {
            "detected": True,
            "feynman_steps": 4,
            "topic": "勾股定理",
            "scene_type": "geometry",
            "template": "勾股定理",
            "task_id": "abc12345",
            "progress_url": "/api/animation/progress/abc12345"
        }
    """
    # 1. 检测费曼教学
    is_feynman, steps = detect_feynman(response_text)
    if not is_feynman:
        return None

    # 2. 提取主题
    topic_info = extract_topic(user_input, response_text)

    # 3. 触发动画
    task_id = trigger_animation(
        topic_info["topic"],
        topic_info["scene_type"],
        user_id,
    )

    return {
        "detected": True,
        "feynman_steps": steps,
        "topic": topic_info["topic"],
        "scene_type": topic_info["scene_type"],
        "template": topic_info["template"],
        "confidence": topic_info["confidence"],
        "task_id": task_id,
        "progress_url": f"/api/animation/progress/{task_id}" if task_id else None,
    }