# -*- coding: utf-8 -*-
"""
LumiLearn 兼容性 shim — 提供模型调用与任务解析能力

提供 LumiLearnAgent / ToolCaller / FlowOrchestrator / TaskUnderstanding
以便 student_portal.py 和旧测试脚本无缝运行。
"""
import os
import requests


# ============================================================
# ToolCaller
# ============================================================
class ToolCaller:
    """
    封装 Ollama / 云端模型调用。
    """

    def __init__(self, ollama_url: str = None):
        self.ollama_url = (ollama_url or os.environ.get("OLLAMA_URL")
                           or os.environ.get("OLLAMA_BASE_URL")
                           or "http://localhost:11434").rstrip("/")
        self._preferred_model = os.environ.get("OLLAMA_MODEL") or "lumilearn-v2:latest"

    @property
    def preferred_model(self) -> str:
        return self._preferred_model

    @property
    def available(self) -> bool:
        try:
            r = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def call(self, prompt: str, task_type: str = "chat", timeout: int = 120) -> dict:
        import json
        payload = {
            "model": self.preferred_model,
            "prompt": prompt,
            "stream": False,
        }
        try:
            r = requests.post(f"{self.ollama_url}/api/generate",
                              json=payload, timeout=timeout, stream=False)
            r.raise_for_status()
            data = r.json()
            return {"success": True, "content": data.get("response", ""),
                    "model_used": self.preferred_model}
        except Exception as e:
            return {"success": False, "error": str(e), "model_used": self.preferred_model}

    def get_call_summary(self) -> dict:
        return {"model": self.preferred_model,
                "ollama_url": self.ollama_url,
                "available": self.available}


# ============================================================
# TaskUnderstanding
# ============================================================
class TaskUnderstanding:
    """
    识别学习主题的学科与类型。
    """

    SUBJECT_KEYWORDS = {
        "数学": ["数学", "代数", "几何", "函数", "方程", "概率", "数列", "三角",
                 "向量", "矩阵", "导数", "积分", "不等式", "勾股", "正余弦",
                 "多项式", "微积分", "极限", "定理", "函数", "单调", "导数",
                 "积分", "矩阵", "向量", "集合", "逻辑", "数列"],
        "物理": ["物理", "力学", "力学", "牛顿", "能量", "动量", "电路",
                 "电磁", "光学", "波动", "热学", "动量", "惯性", "加速度",
                 "质量", "力", "速度", "加速度"],
        "化学": ["化学", "化学", "元素", "原子", "分子", "化合", "反应",
                 "氧化", "还原", "酸碱", "盐", "电子", "共价", "离子",
                 "化学平衡", "催化剂", "摩尔", "溶液", "电解质"],
        "生物": ["生物", "细胞", "基因", "遗传", "进化", "生态", "光合作用",
                 "呼吸", "蛋白质", "DNA", "RNA", "酶", "孟德尔", "染色体"],
    }

    def understand(self, topic: str) -> dict:
        topic_lower = (topic or "").lower()
        subject = "综合"
        best_score = 0
        for subj, keywords in self.SUBJECT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in topic_lower)
            if score > best_score:
                best_score = score
                subject = subj
        return {"subject": subject, "topic": topic, "topic_type": "general"}


# ============================================================
# FlowOrchestrator
# ============================================================
class FlowOrchestrator:
    """
    编排费曼五步学习流程。
    """

    STEPS = [
        {"step": 1, "name": "现象引入",
         "purpose": "从生活场景出发，建立直观认知"},
        {"step": 2, "name": "认知冲突",
         "purpose": "抛出反直觉问题，激发求知欲"},
        {"step": 3, "name": "思维模型",
         "purpose": "用比喻/画面让抽象概念可操作"},
        {"step": 4, "name": "自主推导",
         "purpose": "苏格拉底式追问，引导学生自己得出结论"},
        {"step": 5, "name": "费曼测试",
         "purpose": "30秒极简讲解，检验真正理解"},
    ]

    def orchestrate(self, task: dict) -> list:
        return self.STEPS


# ============================================================
# LumiLearnAgent（顶层兼容包装）
# ============================================================
class LumiLearnAgent:
    """
    面向 student_portal.py 的 Agent 包装。
    """

    def __init__(self, ollama_url: str = None):
        self.tool_caller = ToolCaller(ollama_url=ollama_url)

    def get_status(self) -> dict:
        return {
            "ollama_available": self.tool_caller.available,
            "model": self.tool_caller.preferred_model,
            "ollama_url": self.tool_caller.ollama_url,
        }
