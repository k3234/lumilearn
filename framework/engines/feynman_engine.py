# -*- coding: utf-8 -*-
"""
灵学 lumilearn - 费曼教学引擎
费曼学习法五步教学：现象引入 → 认知冲突 → 思维模型 → 自主推导 → 30秒测试

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-01
"""

import re
import json
import time
import random
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field

# 导入共享模块
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lumilearn_shared import call_ollama
from framework.engines.feynman_templates import get_template, FEYNMAN_TEMPLATES

# ==================== 数据模型 ====================
@dataclass
class FeynmanStep:
    """费曼教学单步结果"""
    step_name: str           # 步骤名称
    step_order: int           # 步骤顺序 (1-5)
    content: str              # 步骤内容
    key_points: list = field(default_factory=list)  # 关键知识点
    animation_hint: str = ""  # 动画提示，用于匹配相关动画

@dataclass
class FeynmanResult:
    """费曼教学完整结果"""
    topic: str                # 教学主题
    level: str                # 学生水平
    steps: list = field(default_factory=list)       # 五个步骤
    model_used: str = ""      # 使用的模型
    total_time: float = 0.0   # 总耗时(秒)
    timestamp: str = ""       # 创建时间

# ==================== 学科判断 ====================
SUBJECT_KEYWORDS = {
    "math": ["数学", "代数", "几何", "函数", "概率", "方程", "公式", "计算", "面积", "体积",
             "三角形", "圆", "数", "加减乘除", "勾股", "坐标", "数列", "向量", "矩阵"],
    "physics": ["物理", "力学", "电", "磁", "光", "热", "声", "力", "速度", "加速度",
                "牛顿", "欧姆", "焦耳", "能量", "功率", "电压", "电流", "电阻", "磁场"],
    "english": ["英语", "英文", "语法", "单词", "词汇", "写作", "阅读", "翻译", "时态",
                "口语", "听力", "发音", "从句", "短语"],
    "chemistry": ["化学", "元素", "周期", "反应", "分子", "原子", "离子", "化合", "分解",
                  "酸", "碱", "盐", "氧化", "还原", "催化剂"],
}

TOPIC_TYPE_KEYWORDS = {
    "math": {
        "algebra": ["方程", "不等式", "代数", "多项式", "因式分解", "未知数", "移项", "解"],
        "geometry": ["几何", "三角形", "圆", "面积", "体积", "角度", "勾股", "坐标系", "相似", "全等"],
        "function": ["函数", "图像", "定义域", "值域", "单调", "奇偶", "指数", "对数", "映射"],
        "probability": ["概率", "统计", "可能性", "频率", "随机", "期望", "组合", "排列"],
    },
    "physics": {
        "mechanics": ["力", "速度", "加速度", "牛顿", "运动", "功", "能量", "动量", "摩擦", "杠杆"],
        "electromagnetism": ["电", "磁", "电压", "电流", "电阻", "电磁", "电路", "欧姆", "安培"],
        "thermodynamics": ["热", "温度", "热量", "熵", "热力学", "内能", "卡诺", "传导"],
        "optics": ["光", "反射", "折射", "透镜", "镜", "光谱", "波长", "色散", "成像"],
    },
    "english": {
        "grammar": ["语法", "时态", "主谓", "从句", "语态", "句型", "固定搭配"],
        "vocabulary": ["单词", "词汇", "词根", "词缀", "同义词", "搭配", "短语"],
        "writing": ["写作", "作文", "开头", "结尾", "段落", "结构", "模板"],
        "reading": ["阅读", "理解", "精读", "泛读", "文章", "作者", "主题"],
    },
    "chemistry": {
        "reaction": ["反应", "化合", "分解", "氧化", "还原", "方程式", "配平"],
        "periodic_table": ["元素", "周期", "族", "原子序数", "半径", "金属性", "非金属"],
        "chemical_bond": ["键", "离子键", "共价键", "电子", "结构", "分子"],
    },
}

# ==================== FeynmanEngine ====================
class FeynmanEngine:
    """
    费曼教学引擎
    核心：用最朴素的语言，让任何水平的学生都能真正理解
    
    教学方法：
    1. 现象引入：从生活场景出发，零术语切入
    2. 认知冲突：抛出反直觉问题，激发求知欲
    3. 思维模型：用比喻/画面让抽象概念可操作
    4. 自主推导：苏格拉底式追问，引导学生自己得出结论
    5. 30秒测试：必须能用极简语言讲给完全不懂的人听
    """

    def __init__(self, model_name: str = "lumilearn-v2:latest", timeout: int = 60):
        """
        初始化费曼引擎
        
        参数：
            model_name: Ollama模型名称
            timeout: 调用超时(秒)
        """
        self.model_name = model_name
        self.timeout = timeout
        self.history = []  # 对话历史

    def _detect_subject_and_type(self, topic: str) -> Tuple[str, str]:
        """自动识别学科和主题类型"""
        topic_lower = topic.lower()
        
        # 识别学科
        best_subject = "general"
        best_score = 0
        for subject, keywords in SUBJECT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in topic_lower)
            if score > best_score:
                best_score = score
                best_subject = subject
        
        # 识别主题类型
        topic_type = "general"
        if best_subject in TOPIC_TYPE_KEYWORDS:
            best_ttype_score = 0
            for ttype, keywords in TOPIC_TYPE_KEYWORDS[best_subject].items():
                score = sum(1 for kw in keywords if kw in topic_lower)
                if score > best_ttype_score:
                    best_ttype_score = score
                    topic_type = ttype
        
        return best_subject, topic_type

    def _generate_animation_hint(self, step_name: str, topic: str, 
                                  subject: str, topic_type: str) -> str:
        """
        根据步骤和主题生成动画提示
        
        参数：
            step_name: 步骤名称
            topic: 教学主题
            subject: 学科类型
            topic_type: 主题类型
        
        返回：
            动画提示字符串，用于匹配相关动画
        """
        # 基于主题类型生成动画提示
        animation_hints = {
            "math": {
                "geometry": {
                    "现象引入": "math_geometry_scene",
                    "认知冲突": "math_puzzle",
                    "思维模型": "math_visualization",
                    "自主推导": "math_proof",
                    "费曼测试": "math_summary"
                },
                "algebra": {
                    "现象引入": "math_algebra_scene",
                    "认知冲突": "math_equation_puzzle",
                    "思维模型": "math_graph",
                    "自主推导": "math_solve",
                    "费曼测试": "math_summary"
                },
                "function": {
                    "现象引入": "math_function_scene",
                    "认知冲突": "math_function_puzzle",
                    "思维模型": "math_graph_2d",
                    "自主推导": "math_derive",
                    "费曼测试": "math_summary"
                },
                "default": {
                    "现象引入": "math_scene",
                    "认知冲突": "math_puzzle",
                    "思维模型": "math_visualization",
                    "自主推导": "math_calculation",
                    "费曼测试": "math_summary"
                }
            },
            "physics": {
                "mechanics": {
                    "现象引入": "physics_mechanics_scene",
                    "认知冲突": "physics_puzzle",
                    "思维模型": "physics_diagram",
                    "自主推导": "physics_formula",
                    "费曼测试": "physics_summary"
                },
                "electromagnetism": {
                    "现象引入": "physics_electric_scene",
                    "认知冲突": "physics_circuit_puzzle",
                    "思维模型": "physics_circuit",
                    "自主推导": "physics_law",
                    "费曼测试": "physics_summary"
                },
                "default": {
                    "现象引入": "physics_scene",
                    "认知冲突": "physics_puzzle",
                    "思维模型": "physics_diagram",
                    "自主推导": "physics_simulation",
                    "费曼测试": "physics_summary"
                }
            },
            "chemistry": {
                "reaction": {
                    "现象引入": "chemistry_reaction_scene",
                    "认知冲突": "chemistry_puzzle",
                    "思维模型": "chemistry_molecule",
                    "自主推导": "chemistry_equation",
                    "费曼测试": "chemistry_summary"
                },
                "default": {
                    "现象引入": "chemistry_scene",
                    "认知冲突": "chemistry_puzzle",
                    "思维模型": "chemistry_diagram",
                    "自主推导": "chemistry_process",
                    "费曼测试": "chemistry_summary"
                }
            },
            "english": {
                "grammar": {
                    "现象引入": "english_conversation",
                    "认知冲突": "english_puzzle",
                    "思维模型": "english_structure",
                    "自主推导": "english_example",
                    "费曼测试": "english_summary"
                },
                "default": {
                    "现象引入": "english_scene",
                    "认知冲突": "english_puzzle",
                    "思维模型": "english_diagram",
                    "自主推导": "english_practice",
                    "费曼测试": "english_summary"
                }
            },
            "general": {
                "default": {
                    "现象引入": "general_scene",
                    "认知冲突": "general_puzzle",
                    "思维模型": "general_diagram",
                    "自主推导": "general_example",
                    "费曼测试": "general_summary"
                }
            }
        }
        
        # 获取对应学科的动画提示字典
        subject_hints = animation_hints.get(subject, animation_hints["general"])
        type_hints = subject_hints.get(topic_type, subject_hints.get("default", 
                                                                      subject_hints.get("default", {})))
        
        # 获取对应步骤的动画提示
        hint = type_hints.get(step_name, "general_animation")
        
        # 添加主题相关后缀
        if subject in ["math", "physics", "chemistry"]:
            hint = f"{subject}_{topic_type}_{hint}" if topic_type != "default" else hint
        
        return hint

    def _build_feynman_prompt(self, step: str, topic: str, level: str, 
                               context: list = None) -> str:
        """
        构建费曼风格的Prompt
        
        参数：
            step: 步骤名 (phenomenon/conflict/model/derive/test)
            topic: 教学主题
            level: 学生水平 (junior/senior/college/general)
            context: 前几步的内容作为上下文
        
        返回：
            构建好的Prompt字符串
        """
        # 获取模板
        subject, topic_type = self._detect_subject_and_type(topic)
        template = get_template(subject, topic_type, step, topic)
        
        # 水平描述
        level_descriptions = {
            "junior": "初中生水平，用最简单的生活例子，不要用专业术语",
            "senior": "高中生水平，可以适当使用学科术语，但需要解释清楚",
            "college": "大学生水平，可以使用专业术语，但核心概念仍需要讲透",
            "general": "通用水平，像给12岁孩子讲解一样清晰易懂",
        }
        level_desc = level_descriptions.get(level, level_descriptions["general"])
        
        # 步骤描述
        step_descriptions = {
            "phenomenon": "用生活中的具体场景引入概念，让学生觉得'哦，原来这就是...'，不要直接说出答案或概念名称",
            "conflict": "抛出一个看似简单但让学生愣住的问题，制造认知冲突。让学生意识到自己原来理解得不对或不完整",
            "model": "给学生一个脑中能操作的画面或比喻。比如'就像...一样'。让抽象概念变得可触摸",
            "derive": "引导学生自主分析推导。分三步：(1)先指出分析方向，说'我们可以从...角度思考'；(2)给出一个关键提示或线索；(3)用追问方式让学生自己迈出第一步。不直接给答案，要像教练一样给方向、给线索、给鼓励",
            "test": "让学生用30秒讲给一个完全不懂的人听。要求：必须用最简单的话，最少的术语",
        }
        step_desc = step_descriptions.get(step, "")
        
        # 组装上下文
        context_str = ""
        if context:
            context_str = "前面已经讨论过的内容：\n"
            for i, ctx in enumerate(context):
                context_str += f"第{i+1}步：{ctx[:200]}\n\n"
        
        # 构建最终Prompt
        prompt = f"""【费曼教学法 - {step}阶段】

学生水平：{level_desc}
教学主题：{topic}

任务：{step_desc}

参考引导语：{template}

{context_str}
请按照费曼教学法的要求，为 "{topic}" 这个主题写出{step}阶段的教学内容。

要求：
1. 语言极度简单、口语化，像面对面聊天
2. 一定要用具体的生活例子
3. 不要堆砌术语，非用不可的要先解释
4. 语气要有趣、亲切，像朋友在教你
5. 控制在300字以内，精炼！

请直接写出教学内容："""
        
        return prompt

    # ==================== 五步教学 ====================
    
    def _step1_phenomenon(self, topic: str, level: str = "junior") -> FeynmanStep:
        """
        第一步：现象引入
        从生活场景切入，不使用术语，让学生觉得亲切自然
        """
        subject, topic_type = self._detect_subject_and_type(topic)
        prompt = self._build_feynman_prompt("phenomenon", topic, level)
        response = call_ollama(self.model_name, prompt, timeout=self.timeout)
        
        if not response:
            # 模型调用失败，使用模板兜底
            response = get_template(subject, topic_type, "phenomenon", topic)
        
        return FeynmanStep(
            step_name="现象引入",
            step_order=1,
            content=response.strip(),
            key_points=[f"用生活场景引入{topic}"],
            animation_hint=self._generate_animation_hint("现象引入", topic, subject, topic_type)
        )

    def _step2_conflict(self, topic: str, level: str = "junior",
                         context: list = None) -> FeynmanStep:
        """
        第二步：认知冲突
        抛出看似简单但让学生愣住的问题，激发思考欲望
        """
        subject, topic_type = self._detect_subject_and_type(topic)
        prompt = self._build_feynman_prompt("conflict", topic, level, context)
        response = call_ollama(self.model_name, prompt, timeout=self.timeout)
        
        if not response:
            response = get_template(subject, topic_type, "conflict", topic)
        
        return FeynmanStep(
            step_name="认知冲突",
            step_order=2,
            content=response.strip(),
            key_points=[f"挑战对{topic}的直觉理解"],
            animation_hint=self._generate_animation_hint("认知冲突", topic, subject, topic_type)
        )

    def _step3_model(self, topic: str, level: str = "junior",
                      context: list = None) -> FeynmanStep:
        """
        第三步：思维模型
        给学生一个脑中可操作的画面/比喻，让抽象变具体
        """
        subject, topic_type = self._detect_subject_and_type(topic)
        prompt = self._build_feynman_prompt("model", topic, level, context)
        response = call_ollama(self.model_name, prompt, timeout=self.timeout)
        
        if not response:
            response = get_template(subject, topic_type, "model", topic)
        
        return FeynmanStep(
            step_name="思维模型",
            step_order=3,
            content=response.strip(),
            key_points=[f"用比喻/图像理解{topic}"],
            animation_hint=self._generate_animation_hint("思维模型", topic, subject, topic_type)
        )

    def _step4_derive(self, topic: str, level: str = "junior",
                       context: list = None) -> FeynmanStep:
        """
        第四步：自主推导
        苏格拉底式追问，让学生自己得出结论，不直接给答案
        """
        subject, topic_type = self._detect_subject_and_type(topic)
        prompt = self._build_feynman_prompt("derive", topic, level, context)
        response = call_ollama(self.model_name, prompt, timeout=self.timeout)
        
        if not response:
            response = get_template(subject, topic_type, "derive", topic)
        
        return FeynmanStep(
            step_name="自主推导",
            step_order=4,
            content=response.strip(),
            key_points=[f"引导式推导{topic}的关键原理"],
            animation_hint=self._generate_animation_hint("自主推导", topic, subject, topic_type)
        )

    def _step5_test(self, topic: str, level: str = "junior",
                     context: list = None) -> FeynmanStep:
        """
        第五步：30秒费曼测试
        让学生用30秒讲给完全不懂的人听，检验是否真懂
        """
        subject, topic_type = self._detect_subject_and_type(topic)
        prompt = self._build_feynman_prompt("test", topic, level, context)
        response = call_ollama(self.model_name, prompt, timeout=self.timeout)
        
        if not response:
            response = get_template(subject, topic_type, "test", topic)
        
        return FeynmanStep(
            step_name="费曼测试",
            step_order=5,
            content=response.strip(),
            key_points=[f"用最朴素的语言概括{topic}"],
            animation_hint=self._generate_animation_hint("费曼测试", topic, subject, topic_type)
        )

    # ==================== 主教学方法 ====================
    
    def explain(self, topic: str, level: str = "junior") -> Dict:
        """
        五步费曼讲解流程 - 主入口
        
        参数：
            topic: 教学主题，如 "勾股定理"、"英语过去式"、"化学反应"
            level: 学生水平 (junior/senior/college/general)
        
        返回：
            {
                "topic": 主题,
                "level": 水平,
                "subject": 识别出的学科,
                "topic_type": 识别出的主题类型,
                "steps": [
                    {"step_name": "现象引入", "step_order": 1, "content": "...", "key_points": [...]},
                    ...
                ],
                "full_content": "合并后的完整讲解内容",
                "model_used": 模型名称,
                "total_time": 耗时,
                "timestamp": 时间戳
            }
        """
        t0 = time.time()
        from datetime import datetime
        
        # 识别学科和主题类型
        subject, topic_type = self._detect_subject_and_type(topic)
        
        # 执行五步教学
        context = []
        steps = []
        
        # 第一步：现象引入
        step1 = self._step1_phenomenon(topic, level)
        steps.append(step1)
        context.append(step1.content)
        
        # 第二步：认知冲突
        step2 = self._step2_conflict(topic, level, context)
        steps.append(step2)
        context.append(step2.content)
        
        # 第三步：思维模型
        step3 = self._step3_model(topic, level, context)
        steps.append(step3)
        context.append(step3.content)
        
        # 第四步：自主推导
        step4 = self._step4_derive(topic, level, context)
        steps.append(step4)
        context.append(step4.content)
        
        # 第五步：30秒费曼测试
        step5 = self._step5_test(topic, level, context)
        steps.append(step5)
        context.append(step5.content)
        
        # 组装结果
        total_time = round(time.time() - t0, 2)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 合并内容
        full_content = "\n\n".join([
            f"【第一步：{steps[0].step_name}】\n{steps[0].content}",
            f"【第二步：{steps[1].step_name}】\n{steps[1].content}",
            f"【第三步：{steps[2].step_name}】\n{steps[2].content}",
            f"【第四步：{steps[3].step_name}】\n{steps[3].content}",
            f"【第五步：{steps[4].step_name}】\n{steps[4].content}",
        ])
        
        result = {
            "topic": topic,
            "level": level,
            "subject": subject,
            "topic_type": topic_type,
            "steps": [
                {"step_name": s.step_name, "step_order": s.step_order,
                 "content": s.content, "key_points": s.key_points,
                 "animation_hint": s.animation_hint}
                for s in steps
            ],
            "full_content": full_content,
            "model_used": self.model_name,
            "total_time": total_time,
            "timestamp": timestamp,
        }
        
        # 记录历史
        self.history.append({
            "topic": topic,
            "level": level,
            "subject": subject,
            "timestamp": timestamp,
        })
        
        return result

    def explain_stream(self, topic: str, level: str = "junior"):
        """
        流式费曼讲解 - 生成器模式
        每完成一步就yield，适合前端逐条展示
        
        参数：
            topic: 教学主题
            level: 学生水平
        
        Yields:
            {"step": 步骤号, "step_name": 步骤名, "content": 内容, "is_last": 是否最后一步}
        """
        subject, topic_type = self._detect_subject_and_type(topic)
        context = []
        
        steps_config = [
            ("phenomenon", "现象引入", self._step1_phenomenon),
            ("conflict", "认知冲突", self._step2_conflict),
            ("model", "思维模型", self._step3_model),
            ("derive", "自主推导", self._step4_derive),
            ("test", "费曼测试", self._step5_test),
        ]
        
        for i, (step_key, step_name, step_func) in enumerate(steps_config):
            if i == 0:
                step_result = step_func(topic, level)
            else:
                step_result = step_func(topic, level, context)
            
            context.append(step_result.content)
            
            yield {
                "step": i + 1,
                "step_name": step_name,
                "content": step_result.content,
                "animation_hint": step_result.animation_hint,
                "is_last": (i == len(steps_config) - 1),
            }

    # ==================== AI评分系统 ====================
    
    def thirty_second_test(self, concept: str, 
                            student_explanation: str) -> Dict:
        """
        评估学生理解程度的AI评分
        
        费曼测试的核心：学生能否用最简单的话讲清楚一个概念
        
        参数：
            concept: 评估的概念
            student_explanation: 学生的解释内容
        
        返回：
            {
                "score": 总分(0-100),
                "dimensions": {
                    "simplicity": {"score": 简洁度, "comment": "..."},
                    "accuracy": {"score": 准确度, "comment": "..."},
                    "analogy": {"score": 比喻运用, "comment": "..."},
                    "completeness": {"score": 完整度, "comment": "..."},
                    "jargon_free": {"score": 术语规避, "comment": "..."},
                },
                "feedback": "综合评语",
                "is_feynman_worthy": 是否达到费曼标准,
                "model_used": 模型名称
            }
        """
        prompt = f"""【费曼测试评分】

概念：{concept}
学生解释：{student_explanation}

请从以下五个维度评分（每项0-20分，总分0-100）：

1. 简洁度（simplicity）：解释是否足够简单？能用8岁孩子听懂的话说吗？
2. 准确度（accuracy）：解释在概念上是否正确？
3. 比喻运用（analogy）：是否用了生活中可理解的比喻？
4. 完整度（completeness）：是否抓住了核心要点而非面面俱到？
5. 术语规避（jargon_free）：是否避免使用专业术语？如果用了，解释了吗？

请用JSON格式回复：
{{
  "simplicity": {{"score": 数值, "comment": "评语"}},
  "accuracy": {{"score": 数值, "comment": "评语"}},
  "analogy": {{"score": 数值, "comment": "评语"}},
  "completeness": {{"score": 数值, "comment": "评语"}},
  "jargon_free": {{"score": 数值, "comment": "评语"}},
  "total_score": 数值,
  "feedback": "综合评语",
  "is_feynman_worthy": true/false
}}

只输出JSON，不要其他内容："""
        
        response = call_ollama(self.model_name, prompt, timeout=self.timeout)
        
        # 解析JSON响应
        try:
            # 尝试从响应中提取JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "score": data.get("total_score", 0),
                    "dimensions": {
                        "simplicity": data.get("simplicity", {"score": 0, "comment": ""}),
                        "accuracy": data.get("accuracy", {"score": 0, "comment": ""}),
                        "analogy": data.get("analogy", {"score": 0, "comment": ""}),
                        "completeness": data.get("completeness", {"score": 0, "comment": ""}),
                        "jargon_free": data.get("jargon_free", {"score": 0, "comment": ""}),
                    },
                    "feedback": data.get("feedback", ""),
                    "is_feynman_worthy": data.get("is_feynman_worthy", False),
                    "model_used": self.model_name,
                }
        except:
            pass
        
        # 解析失败，使用规则兜底
        return self._fallback_rating(student_explanation)

    def _fallback_rating(self, explanation: str) -> Dict:
        """评分兜底方案：基于规则的评分"""
        # 简洁度：字数越少越好（理想60-150字）
        char_count = len(explanation)
        if char_count <= 80:
            simplicity = 18
        elif char_count <= 150:
            simplicity = 16
        elif char_count <= 250:
            simplicity = 12
        else:
            simplicity = 8
        
        # 比喻：检查是否包含比喻性表达
        analogy_keywords = ["像", "好像", "比如", "例如", "就像", "好比", "类似",
                           "想象", "可以看作", "可以理解成"]
        analogy_count = sum(1 for kw in analogy_keywords if kw in explanation)
        analogy = min(20, analogy_count * 5 + 5)
        
        # 术语规避：检查专业术语数量
        jargon_chars = set("^±×÷∑∫√π∞αβγθλμΔΩ∇∂∈∉∪∩⊂⊃⊆⊇∧∨¬→⇒↔∀∃∄≡≈≠≤≥")
        jargon_count = sum(1 for c in explanation if c in jargon_chars)
        if jargon_count == 0:
            jargon_free = 18
        elif jargon_count <= 2:
            jargon_free = 14
        elif jargon_count <= 5:
            jargon_free = 10
        else:
            jargon_free = 5
        
        # 准确度和完整度给基准分
        accuracy = 14
        completeness = 12
        
        total = simplicity + accuracy + analogy + completeness + jargon_free
        
        return {
            "score": total,
            "dimensions": {
                "simplicity": {"score": simplicity, "comment": "字数越精炼越好" if simplicity >= 14 else "可以更简洁些"},
                "accuracy": {"score": accuracy, "comment": "AI评分：基本正确"},
                "analogy": {"score": analogy, "comment": "比喻让理解更容易" if analogy >= 12 else "建议加入生活比喻"},
                "completeness": {"score": completeness, "comment": "核心要点基本涵盖"},
                "jargon_free": {"score": jargon_free, "comment": "术语使用控制在合理范围" if jargon_free >= 14 else "建议减少专业术语"},
            },
            "feedback": "评分基于规则（AI模型不可用时的兜底方案）。建议加入更多生活化比喻，减少术语使用。" if total < 70 else "整体不错，继续保持费曼风格！",
            "is_feynman_worthy": total >= 70,
            "model_used": "rule_fallback",
        }

    # ==================== 快捷回复 ====================
    
    def ask_guiding_question(self, topic: str, 
                              question: str = "") -> str:
        """
        生成引导式提问（费曼风格）
        不直接给答案，而是引导学生思考
        
        参数：
            topic: 当前话题
            question: 学生的具体问题（可选）
        
        返回：
            引导式回复文本
        """
        if question:
            prompt = f"""你是费曼教学法的老师。学生的问题关于"{topic}"，具体问："{question}"。

你的任务：不要直接给答案！用苏格拉底式追问引导学生自己思考。
先肯定问题，然后抛出一个引向答案的引导性问题。

要求：
- 语气亲切，像朋友聊天
- 不直接给出答案
- 引导学生自己找到答案
- 控制在60字以内

请直接回复："""
        else:
            prompt = f"""你是费曼教学法的老师。学生想学"{topic}"。

你的任务：用生活中的例子引入这个话题，让学生觉得有趣。不要直接讲定义！
问一个有趣的生活问题，让学生自己开始思考。

要求：
- 语气亲切，像朋友聊天
- 用生活场景开头
- 控制在60字以内

请直接回复："""
        
        response = call_ollama(self.model_name, prompt, timeout=self.timeout)
        
        if not response:
            # 兜底
            subject, topic_type = self._detect_subject_and_type(topic)
            response = get_template(subject, topic_type, "phenomenon", topic)
        
        return response.strip()

    def react_to_answer(self, concept: str, student_answer: str,
                         expected: str = "") -> Dict:
        """
        对学生回答的费曼式反馈
        不直接说对错，而是评价解释道不道地
        
        参数：
            concept: 概念名
            student_answer: 学生回答
            expected: 参考答案（可选）
        
        返回：
            {"status": "good/partial/needs_work", "feedback": "...", "hint": "..."}
        """
        # 先用AI评分
        rating = self.thirty_second_test(concept, student_answer)
        score = rating.get("score", 0)
        
        if score >= 80:
            return {
                "status": "good",
                "feedback": f"讲得真好！你已经理解了{concept}的核心。",
                "hint": f"如果能再举个生活中的例子就更棒了～",
            }
        elif score >= 60:
            return {
                "status": "partial",
                "feedback": f"大概意思对了！但还有一点可以更清楚。",
                "hint": rating.get("feedback", "试着用一个更简单的比喻再讲一次？"),
            }
        else:
            return {
                "status": "needs_work",
                "feedback": f"你对{concept}的理解还需要加深。没关系，学习就是这样！",
                "hint": "先别管具体细节，想想它最核心的东西是什么？",
            }

    def suggest_correction(self, concept: str,
                            wrong_explanation: str) -> str:
        """
        纠错引导：学生讲错了，怎么引导正确的理解
        
        参数：
            concept: 概念名
            wrong_explanation: 学生的错误解释
        
        返回：
            引导式纠正文本
        """
        prompt = f"""你是费曼教学法的老师。学生对"{concept}"的理解出了偏差，他说：
"{wrong_explanation}"

你的任务：
1. 第一句肯定学生的努力
2. 不直接说"你错了"
3. 用一个简单的比喻/例子让学生自己发现问题
4. 最后给一个正确的简单解释

要求：
- 语气温暖，像朋友聊天
- 用最简单的话解释
- 控制在100字以内

请直接回复："""
        
        response = call_ollama(self.model_name, prompt, timeout=self.timeout)
        
        if not response:
            response = f"你的理解很有意思！关于{concept}，让我们换个角度想想...你能不能先用自己的话说说，{concept}最核心的东西是什么？"
        
        return response.strip()

    # ==================== 工具方法 ====================
    
    def get_history(self) -> list:
        """获取教学历史记录"""
        return self.history

    def clear_history(self):
        """清空教学历史"""
        self.history = []

    def set_model(self, model_name: str):
        """切换模型"""
        self.model_name = model_name

    def get_model_info(self) -> Dict:
        """获取引擎信息"""
        return {
            "engine": "FeynmanEngine",
            "version": "1.0.0",
            "model": self.model_name,
            "timeout": self.timeout,
            "total_sessions": len(self.history),
        }


# ==================== 便捷函数 ====================
def quick_explain(topic: str, level: str = "junior",
                   model: str = "qwen2.5:7b") -> Dict:
    """
    快速费曼讲解 - 一行调用
    
    参数：
        topic: 教学主题
        level: 学生水平
        model: 模型名称
    
    返回：
        讲解结果Dict
    """
    engine = FeynmanEngine(model_name=model)
    return engine.explain(topic, level)


def quick_test(concept: str, explanation: str,
                model: str = "qwen2.5:7b") -> Dict:
    """
    快速费曼测试 - 一行评分
    
    参数：
        concept: 概念名
        explanation: 学生解释
        model: 模型名称
    
    返回：
        评分结果Dict
    """
    engine = FeynmanEngine(model_name=model)
    return engine.thirty_second_test(concept, explanation)


# ==================== 测试入口 ====================
if __name__ == "__main__":
    print("=" * 60)
    print("🧠 费曼教学引擎 - 测试")
    print("=" * 60)
    
    # 测试主题
    test_topics = [
        ("勾股定理", "junior"),
        ("英语过去式", "junior"),
        ("牛顿第一定律", "senior"),
    ]
    
    engine = FeynmanEngine(model_name="qwen2.5:7b")
    
    for topic, level in test_topics:
        print(f"\n{'=' * 40}")
        print(f"📚 主题: {topic} | 水平: {level}")
        print("=" * 40)
        
        subject, ttype = engine._detect_subject_and_type(topic)
        print(f"   识别: 学科={subject}, 主题类型={ttype}")
        
        result = engine.explain(topic, level)
        print(f"   模型: {result['model_used']}, 耗时: {result['total_time']}s")
        
        for step in result["steps"]:
            print(f"\n   [{step['step_name']}]")
            content_preview = step["content"][:100].replace("\n", " ")
            print(f"   {content_preview}...")
    
    print(f"\n{'=' * 40}")
    print("📊 费曼测试评分")
    print("=" * 40)
    
    test_concept = "勾股定理"
    test_explanation = ("勾股定理就是说，直角三角形两个短边的平方加起来，"
                       "等于最长边的平方。就好像你盖房子，对角线就是最长的，"
                       "两个墙的长度决定了对角线。")
    
    rating = engine.thirty_second_test(test_concept, test_explanation)
    print(f"   学生解释: {test_explanation}")
    print(f"   评分: {rating['score']}/100")
    print(f"   费曼认证: {'✅ 通过' if rating['is_feynman_worthy'] else '❌ 需要改进'}")
    for dim, data in rating.get("dimensions", {}).items():
        print(f"   {dim}: {data['score']}/20 - {data['comment']}")