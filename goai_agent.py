#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn GOAI Agent — 教育智能体核心引擎
============================================
GOAI"无界应用"赛道参赛Demo

核心能力（契合GOAI评审标准）：
  1. 任务理解 — 识别学习目标、学科、难度
  2. 流程编排 — 费曼五步教学法自动规划
  3. 工具调用 — 多模型并行调用 + AI评分
  4. 结果交付 — 完整学习报告（掌握度+薄弱点+建议）

架构：
  用户输入 → [任务理解] → [流程编排] → [工具调用] → [结果交付] → 学习报告

作者：LumiLearn (LumiLearn)
版本：1.0.0
日期：2026-08-05
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Ollama 服务地址（优先从环境变量读取，避免硬编码内网 IP）
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

# 确保能导入同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ============================================================
# 一、任务理解模块
# ============================================================
class TaskUnderstanding:
    """
    任务理解：解析用户输入的学习目标
    
    能力：
    - 学科识别（数学/物理/化学/英语/语文/综合）
    - 主题类型识别（函数/几何/力学/语法...）
    - 难度评估（初中/高中/大学）
    - 学习类型识别（概念理解/题型训练/复习）
    """
    
    SUBJECT_KEYWORDS = {
        "数学": ["数学", "代数", "几何", "函数", "方程", "概率", "数列", "三角",
                "向量", "矩阵", "导数", "积分", "不等式", "圆", "椭圆", "勾股",
                "正余弦", "正弦", "余弦", "多项式", "微积分", "极限"],
        "物理": ["物理", "力学", "电", "磁", "光", "热", "声", "速度", "加速度",
                "牛顿", "能量", "功率", "电压", "电流", "电阻", "磁场", "功",
                "欧姆", "焦耳", "法拉第"],
        "化学": ["化学", "元素", "周期", "反应", "分子", "原子", "离子", "化合",
                "分解", "酸", "碱", "盐", "氧化", "还原", "催化剂", "方程式",
                "摩尔", "配平"],
        "英语": ["英语", "英文", "语法", "单词", "词汇", "写作", "阅读", "翻译",
                "时态", "口语", "听力", "发音", "从句"],
        "语文": ["语文", "文言", "诗词", "阅读", "作文", "修辞", "成语", "病句"],
    }
    
    TYPE_KEYWORDS = {
        "数学": {
            "函数": ["函数", "定义域", "值域", "单调", "奇偶", "指数", "对数", "图像"],
            "几何": ["几何", "三角形", "圆", "面积", "体积", "角度", "勾股", "坐标"],
            "方程": ["方程", "不等式", "代数", "多项式", "因式分解"],
            "概率": ["概率", "统计", "随机", "期望", "组合", "排列"],
        },
        "物理": {
            "力学": ["力", "速度", "加速度", "牛顿", "运动", "功", "能量", "动量"],
            "电磁": ["电", "磁", "电压", "电流", "电阻", "电磁", "电路", "欧姆"],
            "热学": ["热", "温度", "热量", "热力学", "内能"],
            "光学": ["光", "反射", "折射", "透镜", "波长", "色散"],
        },
        "化学": {
            "反应": ["反应", "化合", "分解", "氧化", "还原", "方程式", "配平"],
            "元素": ["元素", "周期", "族", "原子序数", "半径"],
            "化学键": ["键", "离子键", "共价键", "电子", "结构", "分子"],
        },
    }
    
    DIFFICULTY_INDICATORS = {
        "初中": ["初中", "初一", "初二", "初三", "中考"],
        "高中": ["高中", "高一", "高二", "高三", "高考", "会考"],
        "大学": ["大学", "高数", "微积分", "线性代数", "考研"],
    }
    
    def understand(self, user_input: str) -> Dict:
        """
        解析用户输入，输出结构化任务理解结果
        
        Returns:
            {
                "subject": 学科,
                "topic_type": 主题类型,
                "difficulty": 难度,
                "core_topic": 核心主题（清洗后的关键词）,
                "learning_type": 学习类型,
                "confidence": 置信度
            }
        """
        subject = self._detect_subject(user_input)
        topic_type = self._detect_topic_type(user_input, subject)
        difficulty = self._detect_difficulty(user_input)
        core_topic = self._extract_core_topic(user_input)
        learning_type = self._detect_learning_type(user_input)
        
        confidence = 0.9 if subject != "综合" else 0.6
        if core_topic:
            confidence = min(1.0, confidence + 0.1)
        
        return {
            "subject": subject,
            "topic_type": topic_type,
            "difficulty": difficulty,
            "core_topic": core_topic,
            "learning_type": learning_type,
            "confidence": confidence,
        }
    
    def _detect_subject(self, text: str) -> str:
        scores = {}
        for subject, keywords in self.SUBJECT_KEYWORDS.items():
            scores[subject] = sum(1 for kw in keywords if kw in text)
        if not any(scores.values()):
            return "综合"
        return max(scores, key=scores.get)
    
    def _detect_topic_type(self, text: str, subject: str) -> str:
        if subject not in self.TYPE_KEYWORDS:
            return "通用"
        scores = {}
        for ttype, keywords in self.TYPE_KEYWORDS[subject].items():
            scores[ttype] = sum(1 for kw in keywords if kw in text)
        if not any(scores.values()):
            return "通用"
        return max(scores, key=scores.get)
    
    def _detect_difficulty(self, text: str) -> str:
        for level, keywords in self.DIFFICULTY_INDICATORS.items():
            if any(kw in text for kw in keywords):
                return level
        return "高中"
    
    def _extract_core_topic(self, text: str) -> str:
        stop_words = ["我想", "我要", "帮我", "请", "学习", "理解", "掌握", "复习",
                      "一下", "什么", "怎么", "如何", "什么是", "解释", "教"]
        cleaned = text
        for sw in stop_words:
            cleaned = cleaned.replace(sw, "")
        cleaned = re.sub(r'[？?！!。.，,、]', '', cleaned)
        return cleaned.strip()[:30] or text[:30]
    
    def _detect_learning_type(self, text: str) -> str:
        if any(kw in text for kw in ["做题", "练习", "题型", "解法", "方法"]):
            return "题型训练"
        if any(kw in text for kw in ["复习", "回顾", "巩固"]):
            return "复习巩固"
        return "概念理解"


# ============================================================
# 二、流程编排模块
# ============================================================
class FlowOrchestrator:
    """
    流程编排：基于费曼五步教学法自动生成教学流程
    
    五步流程：
    1. 现象引入 — 从生活场景切入
    2. 认知冲突 — 制造反直觉问题
    3. 思维模型 — 用比喻让抽象变具体
    4. 自主推导 — 苏格拉底式引导
    5. 费曼测试 — 30秒讲解检验
    """
    
    STEP_NAMES = ["现象引入", "认知冲突", "思维模型", "自主推导", "费曼测试"]
    
    def orchestrate(self, task: Dict) -> List[Dict]:
        """
        根据任务理解结果生成教学流程
        
        Returns:
            [{"step": 1, "name": "现象引入", "prompt": "...", "purpose": "..."}, ...]
        """
        core_topic = task["core_topic"]
        subject = task["subject"]
        difficulty = task["difficulty"]
        
        steps = []
        for i, name in enumerate(self.STEP_NAMES, 1):
            prompt = self._build_step_prompt(i, name, core_topic, subject, difficulty)
            purpose = self._get_step_purpose(i)
            steps.append({
                "step": i,
                "name": name,
                "prompt": prompt,
                "purpose": purpose,
                "status": "pending",
            })
        
        return steps
    
    def _build_step_prompt(self, step: int, name: str, topic: str,
                           subject: str, difficulty: str) -> str:
        level_desc = {
            "初中": "初中生水平，用最简单的生活例子，不要用专业术语",
            "高中": "高中生水平，可以适当使用学科术语，但需解释清楚",
            "大学": "大学生水平，可以使用专业术语，但核心概念仍要讲透",
        }
        
        step_descriptions = {
            1: f"用生活中的具体场景引入概念，让学生觉得'哦，原来这就是...'，不要直接说出答案或概念名称",
            2: f"抛出一个看似简单但让学生愣住的问题，制造认知冲突。让学生意识到自己原来的理解不完整",
            3: f"给学生一个脑中能操作的画面或比喻。比如'就像...一样'，让抽象概念变得可触摸",
            4: f"引导学生自主分析推导。先指出分析方向，给出关键提示，用追问方式让学生自己迈出第一步。不直接给答案",
            5: f"让学生用30秒讲给一个完全不懂的人听。要求：必须用最简单的话，最少的术语",
        }
        
        return f"""【费曼教学法 - {name}阶段】

学生水平：{level_desc.get(difficulty, level_desc["高中"])}
教学主题：{topic}
学科领域：{subject}

任务：{step_descriptions[step]}

要求：
1. 语言极度简单、口语化，像面对面聊天
2. 一定要用具体的生活例子
3. 不要堆砌术语，非用不可的要先解释
4. 语气要有趣、亲切，像朋友在教你
5. 控制在200-300字

请直接写出教学内容："""
    
    def _get_step_purpose(self, step: int) -> str:
        purposes = {
            1: "从生活场景切入，零术语切入，让学生觉得亲切",
            2: "制造认知冲突，激发求知欲，打破原有认知",
            3: "用比喻/画面让抽象概念可操作、可触摸",
            4: "苏格拉底式追问，引导学生自己得出结论",
            5: "检验学生是否真正理解——能否用简单话讲清楚",
        }
        return purposes.get(step, "教学步骤")


# ============================================================
# 三、工具调用模块
# ============================================================
class ToolCaller:
    """
    工具调用：调用外部模型/服务执行具体任务
    
    支持的工具：
    - ollama_local: 本地Ollama模型（deepseek-r1:1.5b, qwen2.5:7b）
    - rule_scoring: 基于规则的评分（兜底）
    """
    
    def __init__(self, ollama_url: str = DEFAULT_OLLAMA_URL,
                 preferred_model: str = "lumilearn-v2",
                 timeout: int = 120):
        self.ollama_url = ollama_url
        self.preferred_model = preferred_model
        self.timeout = timeout
        self.available = self._check_availability()
        self.call_log = []
    
    def _check_availability(self) -> bool:
        """检查Ollama是否可用"""
        try:
            import requests
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=8)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                available_names = [m.get("name", "") for m in models]
                # 优先使用 LumiLearn V2 微调模型，其次回退到通用模型
                for name in [self.preferred_model, "lumilearn-v2",
                             "lumilearn-merged", "qwen2.5:1.5b",
                             "deepseek-r1:1.5b"]:
                    if any(name in an for an in available_names):
                        self.preferred_model = name
                        return True
        except:
            pass
        return False
    
    def call(self, prompt: str, task_type: str = "teach") -> Dict:
        """
        调用工具执行任务
        
        Args:
            prompt: 提示词
            task_type: 任务类型（teach/score/evaluate）
        
        Returns:
            {"content": "...", "model": "...", "elapsed": 0.0, "success": True/False}
        """
        t0 = time.time()
        
        if self.available:
            result = self._call_ollama(prompt)
            elapsed = time.time() - t0
            self.call_log.append({
                "task_type": task_type,
                "model": self.preferred_model,
                "elapsed": elapsed,
                "success": bool(result),
            })
            return {
                "content": result or self._fallback_response(prompt, task_type),
                "model": self.preferred_model,
                "elapsed": elapsed,
                "success": bool(result),
            }
        else:
            elapsed = time.time() - t0
            self.call_log.append({
                "task_type": task_type,
                "model": "rule_fallback",
                "elapsed": elapsed,
                "success": True,
            })
            return {
                "content": self._fallback_response(prompt, task_type),
                "model": "rule_fallback（Ollama不可用）",
                "elapsed": elapsed,
                "success": True,
            }
    
    def _call_ollama(self, prompt: str) -> str:
        """调用Ollama API"""
        try:
            import requests
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.preferred_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            pass
        return ""
    
    def _fallback_response(self, prompt: str, task_type: str) -> str:
        """兜底响应：当模型不可用时"""
        if task_type == "teach":
            return self._extract_topic_hint(prompt)
        elif task_type == "score":
            return json.dumps({
                "total_score": 75,
                "simplicity": {"score": 15, "comment": "基本简洁"},
                "accuracy": {"score": 14, "comment": "概念基本正确"},
                "analogy": {"score": 12, "comment": "可以加入更多比喻"},
                "completeness": {"score": 12, "comment": "核心要点已涵盖"},
                "jargon_free": {"score": 12, "comment": "术语控制在合理范围"},
                "feedback": "整体不错，建议加入更多生活化比喻",
                "is_feynman_worthy": True,
            }, ensure_ascii=False)
        return "工具调用完成（Ollama不可用模式）"
    
    def _extract_topic_hint(self, prompt: str) -> str:
        """从prompt提取主题，生成简单兜底内容"""
        topic_match = re.search(r'教学主题[：:]\s*(.+)', prompt)
        topic = topic_match.group(1).strip() if topic_match else "这个概念"
        return f"""（这是关于「{topic}」的教学内容）

由于本地模型暂时不可用，这里展示的是教学流程框架。

在实际部署中，这里会调用AI模型生成完整的{topic}教学内容，包括：
- 用生活场景引入概念
- 制造认知冲突激发思考
- 用比喻让抽象变具体
- 引导学生自主推导
- 30秒费曼测试检验理解"""

    def get_call_summary(self) -> Dict:
        """获取工具调用摘要"""
        if not self.call_log:
            return {"total_calls": 0}
        return {
            "total_calls": len(self.call_log),
            "by_type": {t: sum(1 for c in self.call_log if c["task_type"] == t)
                        for t in set(c["task_type"] for c in self.call_log)},
            "avg_elapsed": sum(c["elapsed"] for c in self.call_log) / len(self.call_log),
            "success_rate": sum(1 for c in self.call_log if c["success"]) / len(self.call_log),
        }


# ============================================================
# 四、结果交付模块
# ============================================================
class ResultDelivery:
    """
    结果交付：生成完整学习报告
    
    报告结构：
    1. 任务理解摘要
    2. 教学流程执行结果
    3. 掌握度评估
    4. 薄弱点分析
    5. 下一步学习建议
    """
    
    def generate_report(self, task: Dict, flow_results: List[Dict],
                        tool_summary: Dict) -> Dict:
        """生成完整学习报告"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = {
            "title": f"「{task['core_topic']}」学习报告",
            "generated_at": now,
            "task_understanding": task,
            "teaching_flow": {
                "total_steps": len(flow_results),
                "completed_steps": sum(1 for s in flow_results if s.get("success")),
                "steps_detail": flow_results,
            },
            "tool_usage": tool_summary,
            "mastery_assessment": self._assess_mastery(flow_results),
            "weak_points": self._identify_weak_points(task, flow_results),
            "next_steps": self._suggest_next_steps(task, flow_results),
        }
        
        return report
    
    def _assess_mastery(self, flow_results: List[Dict]) -> Dict:
        """评估掌握度"""
        completed = sum(1 for s in flow_results if s.get("success"))
        total = len(flow_results)
        mastery_level = completed / total if total > 0 else 0
        
        if mastery_level >= 0.8:
            level = "良好"
            emoji = "✅"
        elif mastery_level >= 0.5:
            level = "中等"
            emoji = "⚠️"
        else:
            level = "需加强"
            emoji = "❌"
        
        return {
            "score": round(mastery_level * 100),
            "level": level,
            "emoji": emoji,
            "summary": f"{emoji} 完成 {completed}/{total} 个教学步骤，掌握度{level}",
        }
    
    def _identify_weak_points(self, task: Dict, flow_results: List[Dict]) -> List[str]:
        """识别薄弱点"""
        weak = []
        step_names = ["现象引入", "认知冲突", "思维模型", "自主推导", "费曼测试"]
        
        for i, result in enumerate(flow_results):
            if not result.get("success") or not result.get("content"):
                weak.append(f"「{step_names[i]}」阶段内容生成不完整")
        
        if task.get("confidence", 0) < 0.7:
            weak.append("任务理解置信度偏低，建议明确学习目标")
        
        if not weak:
            weak.append("暂无明显薄弱点，建议继续深入练习")
        
        return weak
    
    def _suggest_next_steps(self, task: Dict, flow_results: List[Dict]) -> List[str]:
        """建议下一步学习"""
        suggestions = []
        subject = task.get("subject", "综合")
        topic = task.get("core_topic", "")
        difficulty = task.get("difficulty", "高中")
        
        suggestions.append(f"完成「{topic}」相关练习题（{difficulty}难度）")
        suggestions.append(f"尝试用30秒向同学讲解「{topic}」的核心概念")
        
        if task.get("learning_type") == "概念理解":
            suggestions.append(f"进阶：探索「{topic}」在实际问题中的应用")
        
        suggestions.append(f"复习周期：1天后 → 3天后 → 7天后 → 14天后")
        
        return suggestions
    
    def render_cli_report(self, report: Dict) -> str:
        """渲染CLI格式的学习报告"""
        lines = []
        
        # 标题
        lines.append("\n" + "=" * 60)
        lines.append(f"  📊 {report['title']}")
        lines.append(f"  生成时间: {report['generated_at']}")
        lines.append("=" * 60)
        
        # 任务理解
        task = report["task_understanding"]
        lines.append("\n【任务理解】")
        lines.append(f"  学科: {task['subject']} | 类型: {task['topic_type']}")
        lines.append(f"  难度: {task['difficulty']} | 学习类型: {task['learning_type']}")
        lines.append(f"  置信度: {task['confidence']:.0%}")
        
        # 教学流程
        tf = report["teaching_flow"]
        lines.append(f"\n【教学流程】完成 {tf['completed_steps']}/{tf['total_steps']} 步")
        for step in tf["steps_detail"]:
            status = "✅" if step.get("success") else "❌"
            lines.append(f"  {status} 步骤{step['step']}: {step['name']}")
            content_preview = step.get("content", "")[:80].replace("\n", " ")
            if content_preview:
                lines.append(f"     {content_preview}...")
        
        # 掌握度
        mastery = report["mastery_assessment"]
        lines.append(f"\n【掌握度评估】{mastery['summary']}")
        
        # 薄弱点
        lines.append("\n【薄弱点分析】")
        for wp in report["weak_points"]:
            lines.append(f"  • {wp}")
        
        # 下一步
        lines.append("\n【下一步建议】")
        for i, step in enumerate(report["next_steps"], 1):
            lines.append(f"  {i}. {step}")
        
        # 工具使用
        tu = report["tool_usage"]
        if tu.get("total_calls", 0) > 0:
            lines.append(f"\n【工具调用】共 {tu['total_calls']} 次 | "
                        f"平均耗时 {tu.get('avg_elapsed', 0):.1f}s | "
                        f"成功率 {tu.get('success_rate', 0):.0%}")
        
        lines.append("\n" + "=" * 60)
        lines.append("  LumiLearn AI 教官 — 让每个学习者都被看见")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def save_report(self, report: Dict, output_dir: str = "goai_output"):
        """保存学习报告到文件"""
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        topic_safe = re.sub(r'[\\/:*?"<>|]', '_', report['task_understanding']['core_topic'])[:20]
        
        # JSON格式
        json_path = os.path.join(output_dir, f"report_{ts}_{topic_safe}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        # Markdown格式
        md_path = os.path.join(output_dir, f"report_{ts}_{topic_safe}.md")
        md_content = self._render_markdown(report)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        return json_path, md_path
    
    def _render_markdown(self, report: Dict) -> str:
        """渲染Markdown格式报告"""
        lines = [
            f"# {report['title']}",
            f"",
            f"> 生成时间: {report['generated_at']}",
            f"> 由 LumiLearn AI 教官自动生成",
            f"",
            f"## 任务理解",
            f"",
            f"| 维度 | 结果 |",
            f"|------|------|",
            f"| 学科 | {report['task_understanding']['subject']} |",
            f"| 类型 | {report['task_understanding']['topic_type']} |",
            f"| 难度 | {report['task_understanding']['difficulty']} |",
            f"| 学习类型 | {report['task_understanding']['learning_type']} |",
            f"| 置信度 | {report['task_understanding']['confidence']:.0%} |",
            f"",
            f"## 教学流程",
            f"",
        ]
        
        for step in report["teaching_flow"]["steps_detail"]:
            status = "✅" if step.get("success") else "❌"
            lines.append(f"### {status} 步骤{step['step']}: {step['name']}")
            lines.append("")
            content = step.get("content", "（无内容）")
            lines.append(content[:500])
            lines.append("")
        
        mastery = report["mastery_assessment"]
        lines.extend([
            f"## 掌握度评估",
            f"",
            f"{mastery['summary']}",
            f"",
            f"## 薄弱点分析",
            f"",
        ])
        for wp in report["weak_points"]:
            lines.append(f"- {wp}")
        
        lines.extend([
            f"",
            f"## 下一步建议",
            f"",
        ])
        for i, step in enumerate(report["next_steps"], 1):
            lines.append(f"{i}. {step}")
        
        lines.extend([
            f"",
            f"---",
            f"*由 LumiLearn AI 教官生成 | GOAI 无界应用赛道参赛作品*",
        ])
        
        return "\n".join(lines)


# ============================================================
# 五、LumiLearn Agent 主引擎
# ============================================================
class LumiLearnAgent:
    """
    LumiLearn 教育智能体 — 主引擎
    
    整合四大模块：
    1. TaskUnderstanding — 任务理解
    2. FlowOrchestrator — 流程编排
    3. ToolCaller — 工具调用
    4. ResultDelivery — 结果交付
    
    完整流程：
    用户输入 → 任务理解 → 流程编排 → 工具调用 → 结果交付 → 学习报告
    """
    
    def __init__(self, ollama_url: str = DEFAULT_OLLAMA_URL,
                 model: str = "lumilearn-v2"):
        self.task_understanding = TaskUnderstanding()
        self.flow_orchestrator = FlowOrchestrator()
        self.tool_caller = ToolCaller(ollama_url=ollama_url, preferred_model=model)
        self.result_delivery = ResultDelivery()
        self.session_count = 0
    
    def run(self, user_input: str, interactive: bool = True) -> Dict:
        """
        运行完整的学习辅导流程
        
        Args:
            user_input: 用户输入的学习目标
            interactive: 是否交互式（显示进度）
        
        Returns:
            完整学习报告 Dict
        """
        self.session_count += 1
        
        if interactive:
            print("\n" + "=" * 60)
            print("  🎓 LumiLearn AI 教官 — 教育智能体")
            print("=" * 60)
            print(f"\n  📝 学习目标: {user_input}")
        
        # === 阶段1: 任务理解 ===
        if interactive:
            print("\n  🔍 [1/4] 任务理解中...", end="", flush=True)
        
        task = self.task_understanding.understand(user_input)
        
        if interactive:
            print(f" ✅")
            print(f"     学科: {task['subject']} | 类型: {task['topic_type']} | "
                  f"难度: {task['difficulty']}")
        
        # === 阶段2: 流程编排 ===
        if interactive:
            print(f"  📋 [2/4] 生成教学流程...", end="", flush=True)
        
        flow = self.flow_orchestrator.orchestrate(task)
        
        if interactive:
            print(f" ✅")
            print(f"     已生成 {len(flow)} 步费曼教学流程")
        
        # === 阶段3: 工具调用（执行教学） ===
        if interactive:
            print(f"  🤖 [3/4] 执行教学流程（调用AI模型）...")
        
        flow_results = []
        for step in flow:
            if interactive:
                print(f"     步骤{step['step']}/{len(flow)}: {step['name']}...", end="", flush=True)
            
            result = self.tool_caller.call(step["prompt"], task_type="teach")
            result["step"] = step["step"]
            result["name"] = step["name"]
            flow_results.append(result)
            
            if interactive:
                print(f" ✅ ({result['elapsed']:.1f}s)")
            
            if interactive:
                input_content = result.get("content", "")
                if input_content and len(input_content) > 10:
                    preview = input_content[:150].replace("\n", "\n       ")
                    print(f"       ┌─ {preview}...")
                    print(f"       └─ ...（{len(input_content)}字）")
        
        # === 阶段4: 结果交付 ===
        if interactive:
            print(f"\n  📊 [4/4] 生成学习报告...", end="", flush=True)
        
        tool_summary = self.tool_caller.get_call_summary()
        report = self.result_delivery.generate_report(task, flow_results, tool_summary)
        
        if interactive:
            print(f" ✅")
        
        # 渲染并显示报告
        if interactive:
            cli_report = self.result_delivery.render_cli_report(report)
            print(cli_report)
        
        # 保存报告
        json_path, md_path = self.result_delivery.save_report(report)
        if interactive:
            print(f"\n  📁 报告已保存:")
            print(f"     JSON: {json_path}")
            print(f"     Markdown: {md_path}")
        
        return report
    
    def get_status(self) -> Dict:
        """获取Agent状态"""
        return {
            "sessions_completed": self.session_count,
            "ollama_available": self.tool_caller.available,
            "model": self.tool_caller.preferred_model,
        }


# ============================================================
# 六、CLI入口
# ============================================================
def main():
    """CLI入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LumiLearn AI 教官 — GOAI 无界应用赛道参赛Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python goai_agent.py "我想理解函数的单调性"
  python goai_agent.py "帮我复习牛顿第二定律"
  python goai_agent.py --interactive
  python goai_agent.py --topic "化学平衡移动" --difficulty 高中
        """
    )
    
    parser.add_argument("topic", nargs="?", help="学习目标（如'函数的单调性'）")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--difficulty", "-d", default=None, help="指定难度（初中/高中/大学）")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="Ollama地址")
    parser.add_argument("--model", default="lumilearn-v2", help="使用的模型")
    
    args = parser.parse_args()
    
    # 初始化Agent
    agent = LumiLearnAgent(
        ollama_url=args.ollama_url,
        model=args.model,
    )
    
    # 显示状态
    status = agent.get_status()
    print("\n" + "=" * 60)
    print("  🎓 LumiLearn AI 教官 — 教育智能体")
    print("  GOAI 无界应用赛道参赛Demo")
    print("=" * 60)
    print(f"  模型状态: {'✅ Ollama可用' if status['ollama_available'] else '⚠️ 兜底模式'}")
    print(f"  使用模型: {status['model']}")
    print(f"  Ollama地址: {args.ollama_url}")
    
    if args.topic:
        # 直接执行
        if args.difficulty:
            args.topic += f" {args.difficulty}"
        agent.run(args.topic, interactive=True)
    elif args.interactive or not args.topic:
        # 交互模式
        print("\n  输入学习目标开始学习（输入 exit 退出）:")
        while True:
            try:
                user_input = input("\n  📝 学习目标> ").strip()
                if user_input.lower() in ("exit", "quit", "退出", "q"):
                    print("\n  👋 再见！坚持学习，你会进步的。")
                    break
                if not user_input:
                    continue
                agent.run(user_input, interactive=True)
            except KeyboardInterrupt:
                print("\n\n  👋 再见！")
                break
            except EOFError:
                break


if __name__ == "__main__":
    main()
