#!/usr/bin/env python3
"""
LumiLearn 五步学习法工作流引擎

将费曼教学法五步（现象引入 → 认知冲突 → 思维模型 → 自主推导 → 费曼测试）
封装为可追踪、可存档、可复现的学习工作流，并集成数据库持久化与输出检测。

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-08-07
"""

import json
import time
import uuid
import os
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

# 导入依赖模块（均已有或为计划模块，输出检测模块可能不存在则降级）
from framework.database import db
from framework.engines.feynman_engine import FeynmanEngine


# ============================================================
# 常量定义
# ============================================================

STEP_NAMES: List[str] = [
    "现象引入",
    "认知冲突",
    "思维模型",
    "自主推导",
    "费曼测试",
]

STEP_KEYS: List[str] = [
    "phenomenon",
    "conflict",
    "model",
    "derive",
    "test",
]

STEP_DESCRIPTIONS: Dict[str, str] = {
    "phenomenon": "从生活场景切入，不使用术语，让学生觉得亲切自然",
    "conflict": "抛出看似简单但让学生愣住的问题，激发思考欲望",
    "model": "给学生一个脑中可操作的画面或比喻，让抽象变具体",
    "derive": "苏格拉底式追问，让学生自己得出结论，不直接给答案",
    "test": "让学生用30秒讲给完全不懂的人听，检验是否真懂",
}


# ============================================================
# LearningWorkflowEngine 类
# ============================================================

class LearningWorkflowEngine:
    """
    五步学习法工作流引擎

    核心流程：
      1. start_workflow(topic, user_id, level)  → 创建工作流，启动费曼五步讲解
      2. submit_step_output(step, user_output)  → 学生提交每步的输出/回答
      3. complete_workflow()                    → 完成全部步骤，归档结果
      4. get_workflow_status()                  → 查询当前工作流进度与得分
      5. _save_learning_archive()              → 将完整档案写入数据库
    """

    def __init__(
        self,
        topic: str,
        user_id: int = 1,
        level: str = "junior",
        model_name: str = "qwen2.5:7b",
        workflow_id: Optional[str] = None,
    ):
        """
        参数：
            topic:       学习主题，如 "勾股定理"
            user_id:     用户ID（用于持久化到数据库）
            level:       学生水平 (junior/senior/college/general)
            model_name:  Ollama 模型名称
            workflow_id: 外部传入的工作流ID（用于续接），随机生成则省略
        """
        self.topic = topic
        self.user_id = user_id
        self.level = level
        self.model_name = model_name
        self.workflow_id = workflow_id or str(uuid.uuid4())[:8]

        self._feynman: Optional[FeynmanEngine] = None
        self._steps: List[Dict[str, Any]] = []
        self._step_outputs: List[Dict[str, Any]] = []
        self._workflow_row_id: Optional[int] = None
        self._started_at: float = 0.0
        self._completed_at: Optional[float] = None
        self._total_score: float = 0.0

    # ------------------------------------------------------------
    # 内部：获取 FeynmanEngine 单例
    # ------------------------------------------------------------

    def _get_feynman(self) -> FeynmanEngine:
        if self._feynman is None:
            self._feynman = FeynmanEngine(model_name=self.model_name)
        return self._feynman

    # ------------------------------------------------------------
    # start_workflow
    # ------------------------------------------------------------

    def start_workflow(self) -> Dict[str, Any]:
        """
        启动五步学习工作流：创建数据库记录，并驱动 FeynmanEngine 执行全部五步。

        返回：
            {
                "workflow_id": str,
                "topic": str,
                "user_id": int,
                "status": "active",
                "current_step": int,
                "total_steps": 5,
                "row_id": int,       # 数据库 learning_workflows 主键
                "steps_summary": [...]
            }
        """
        self._started_at = time.time()

        # 1. 在数据库中创建学习工作流记录
        wf = db.create_learning_workflow(self.user_id, self.workflow_id, self.topic)
        self._workflow_row_id = wf["id"]

        # 2. 驱动费曼引擎逐 step 生成讲解内容
        engine = self._get_feynman()
        steps_detail = engine.explain(self.topic, self.level)

        self._steps = []
        for i, step_data in enumerate(steps_detail["steps"]):
            self._steps.append({
                "step_order": i + 1,
                "step_key": STEP_KEYS[i],
                "step_name": STEP_NAMES[i],
                "step_desc": STEP_DESCRIPTIONS[STEP_KEYS[i]],
                "content": step_data["content"],
                "key_points": step_data.get("key_points", []),
                "animation_hint": step_data.get("animation_hint", ""),
                "user_output": "",
                "output_score": 0.0,
                "step_completed": False,
            })

        # 3. 保存首次进度到数据库
        self._persist_step_progress(0)

        return {
            "workflow_id": self.workflow_id,
            "topic": self.topic,
            "user_id": self.user_id,
            "level": self.level,
            "status": "active",
            "current_step": 0,
            "total_steps": len(self._steps),
            "row_id": self._workflow_row_id,
            "started_at": datetime.fromtimestamp(self._started_at).strftime("%Y-%m-%d %H:%M:%S"),
            "steps_summary": [
                {"step_order": s["step_order"], "step_name": s["step_name"],
                 "content_preview": s["content"][:80]}
                for s in self._steps
            ],
        }

    # ------------------------------------------------------------
    # submit_step_output
    # ------------------------------------------------------------

    def submit_step_output(
        self,
        step_order: int,
        user_output: str,
        score_callback: Optional[Callable[[str, str], Dict]] = None,
    ) -> Dict[str, Any]:
        """
        提交某一步的学习输出（学生回答/思考记录）。

        参数：
            step_order:     步骤序号（1-5）
            user_output:    学生的输出文本
            score_callback: 可选的自定义评分回调，签名 (step_name, output) -> Dict
                            若为 None，则对第5步（费曼测试）自动调用 FeynmanEngine 评分

        返回：
            {
                "step_order": int,
                "step_name": str,
                "output_length": int,
                "score": float,       # 0-100
                "feedback": str,
                "step_completed": bool
            }
        """
        if step_order < 1 or step_order > len(self._steps):
            raise ValueError(f"步骤序号 {step_order} 无效，有效范围 1-{len(self._steps)}")

        step = self._steps[step_order - 1]
        step["user_output"] = user_output

        # 评分
        step_name = step["step_name"]
        if score_callback:
            rating = score_callback(step_name, user_output)
        elif step["step_key"] == "test":
            engine = self._get_feynman()
            rating = engine.thirty_second_test(self.topic, user_output)
        else:
            # 非测试步：基于长度和关键词做简单评分
            rating = self._rule_score(step_name, user_output)

        score = rating.get("score", 0.0)
        feedback = rating.get("feedback", "")
        step["output_score"] = float(score)
        step["step_completed"] = True

        # 累加总分
        self._total_score = sum(s["output_score"] for s in self._steps) / len(self._steps)

        # 持久化到 output_detections 表
        self._save_detection(step_order, user_output, score, feedback)

        # 更新数据库工作流当前步骤
        self._persist_step_progress(step_order)

        return {
            "step_order": step_order,
            "step_name": step_name,
            "output_length": len(user_output),
            "score": round(score, 2),
            "feedback": feedback,
            "step_completed": True,
            "total_score": round(self._total_score, 2),
        }

    def _rule_score(self, step_name: str, output: str) -> Dict[str, Any]:
        """基于规则的非费曼测试步评分（0-100）"""
        char_len = len(output)
        if char_len >= 50:
            length_score = 80
        elif char_len >= 20:
            length_score = 60
        else:
            length_score = 30

        has_keywords = sum(1 for kw in ["因为", "所以", "如果", "就像", "例如", "比如"]
                           if kw in output)
        keyword_score = min(20, has_keywords * 5)

        total = length_score + keyword_score
        return {
            "score": total,
            "feedback": "输出内容充实，继续保持！" if total >= 80 else "可以再展开讲讲你的想法～",
        }

    # ------------------------------------------------------------
    # complete_workflow
    # ------------------------------------------------------------

    def complete_workflow(self) -> Dict[str, Any]:
        """
        标记工作流完成，保存学习档案，更新数据库记录。

        返回：
            {
                "workflow_id": str,
                "topic": str,
                "status": "completed",
                "total_score": float,
                "duration_seconds": float,
                "step_results": [...],
                "archive_id": int
            }
        """
        if self._workflow_row_id is None:
            raise RuntimeError("工作流尚未启动，请先调用 start_workflow()")

        # 检查是否所有步骤已完成
        incomplete = [s["step_name"] for s in self._steps if not s["step_completed"]]
        if incomplete:
            raise RuntimeError(f"尚有步骤未完成，无法完结工作流：{incomplete}")

        self._completed_at = time.time()
        duration = self._completed_at - self._started_at

        # 保存学习档案（数据库 + 可选文件）
        archive_id = self._save_learning_archive()

        # 更新数据库工作流状态
        db.complete_workflow(self._workflow_row_id, score=self._total_score)

        return {
            "workflow_id": self.workflow_id,
            "topic": self.topic,
            "status": "completed",
            "total_score": round(self._total_score, 2),
            "duration_seconds": round(duration, 1),
            "step_results": [
                {
                    "step_name": s["step_name"],
                    "score": s["output_score"],
                    "output_length": len(s["user_output"]),
                }
                for s in self._steps
            ],
            "archive_id": archive_id,
        }

    # ------------------------------------------------------------
    # _save_learning_archive
    # ------------------------------------------------------------

    def _save_learning_archive(self) -> int:
        """
        将完整学习档案写入数据库和可选 JSON 文件。

        写入：
          - output_detections 表（步骤5的费曼测试评分为主记录）
          - learning_workflows 表（由 complete_workflow 调用）
          - 可选：项目根目录下的 archives/ 子目录（JSON 文件）

        返回：
            新插入的 output_detections 记录主键 ID
        """
        # 构建档案数据
        archive_data = {
            "workflow_id": self.workflow_id,
            "topic": self.topic,
            "user_id": self.user_id,
            "level": self.level,
            "model_used": self.model_name,
            "started_at": datetime.fromtimestamp(self._started_at).strftime("%Y-%m-%d %H:%M:%S"),
            "completed_at": datetime.fromtimestamp(self._completed_at or time.time()).strftime("%Y-%m-%d %H:%M:%S"),
            "total_score": round(self._total_score, 2),
            "steps": [
                {
                    "step_order": s["step_order"],
                    "step_name": s["step_name"],
                    "step_key": s["step_key"],
                    "content": s["content"],
                    "key_points": s["key_points"],
                    "animation_hint": s["animation_hint"],
                    "user_output": s["user_output"],
                    "output_score": s["output_score"],
                }
                for s in self._steps
            ],
        }

        # 写入 output_detections（以完整档案为一条记录）
        detection = db.create_output_detection(
            user_id=self.user_id,
            detection_type="essay",
            prompt=f"费曼五步法学习：{self.topic}",
            workflow_id=self.workflow_id,
        )
        detection_id = detection["id"]

        # 回填 user_output 和 feedback
        db.update_detection_result(
            detection_id=detection_id,
            score=self._total_score,
            feedback=json.dumps(archive_data, ensure_ascii=False),
            user_output=json.dumps(
                [s["user_output"] for s in self._steps], ensure_ascii=False
            ),
        )

        # 尝试写入 JSON 文件存档
        try:
            archive_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "archives"
            )
            os.makedirs(archive_dir, exist_ok=True)
            archive_path = os.path.join(archive_dir, f"{self.workflow_id}_archive.json")
            with open(archive_path, "w", encoding="utf-8") as f:
                json.dump(archive_data, f, ensure_ascii=False, indent=2)
            archive_data["_archive_path"] = archive_path
        except Exception:
            pass  # 文件写入失败不影响主流程

        return detection_id

    # ------------------------------------------------------------
    # get_workflow_status
    # ------------------------------------------------------------

    def get_workflow_status(self) -> Dict[str, Any]:
        """
        查询当前工作流的进度状态。

        优先从数据库读取（支持跨进程续接），否则返回内存状态。

        返回：
            {
                "workflow_id": str,
                "topic": str,
                "status": "active"/"completed",
                "current_step": int,     # 已完成的步骤数（0-5）
                "total_steps": int,
                "total_score": float,
                "step_details": [...],
                "started_at": str,
                "completed_at": str or null
            }
        """
        # 尝试从数据库续接
        db_workflow = db.get_workflow(self._workflow_row_id) if self._workflow_row_id else None
        if db_workflow and db_workflow.get("status") == "completed" and self._completed_at is None:
            self._total_score = float(db_workflow.get("score_earned", 0))
            self._completed_at = db_workflow.get("completed_at")

        step_details = []
        for s in self._steps:
            step_details.append({
                "step_order": s["step_order"],
                "step_name": s["step_name"],
                "step_key": s["step_key"],
                "content": s["content"][:100] if s["content"] else "",
                "user_output": s.get("user_output", "")[:100],
                "output_score": s.get("output_score", 0.0),
                "completed": s.get("step_completed", False),
            })

        current_step = sum(1 for s in self._steps if s.get("step_completed"))

        return {
            "workflow_id": self.workflow_id,
            "topic": self.topic,
            "user_id": self.user_id,
            "status": "completed" if self._completed_at else "active",
            "current_step": current_step,
            "total_steps": len(self._steps),
            "total_score": round(self._total_score, 2),
            "step_details": step_details,
            "started_at": datetime.fromtimestamp(self._started_at).strftime("%Y-%m-%d %H:%M:%S")
                if self._started_at else None,
            "completed_at": datetime.fromtimestamp(self._completed_at).strftime("%Y-%m-%d %H:%M:%S")
                if self._completed_at else None,
            "duration_seconds": round(self._completed_at - self._started_at, 1)
                if self._completed_at and self._started_at else None,
        }

    # ------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------

    def _persist_step_progress(self, step_order: int):
        """将当前步骤序号持久化到 learning_workflows 表"""
        if self._workflow_row_id is not None:
            db.update_workflow_step(self._workflow_row_id, step_order)

    def _save_detection(self, step_order: int, output: str, score: float, feedback: str):
        """将单步输出记录到 output_detections 表（以 test 类型区分不同步骤）"""
        step_key = STEP_KEYS[step_order - 1]
        db.create_output_detection(
            user_id=self.user_id,
            detection_type=step_key,
            prompt=f"{STEP_NAMES[step_order - 1]}：{self.topic}",
            workflow_id=self.workflow_id,
        )
        # 回填该条记录
        # 由于 create_output_detection 返回的是 id，这里简化为在档案中保存


# ============================================================
# 便捷函数
# ============================================================

def run_learning_workflow(
    topic: str,
    user_id: int = 1,
    level: str = "junior",
    model_name: str = "qwen2.5:7b",
    auto_submit_outputs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    一键运行完整五步学习工作流。

    参数：
        topic:                  学习主题
        user_id:                用户ID
        level:                  学生水平
        model_name:             Ollama 模型名称
        auto_submit_outputs:    可选，预先准备的各步骤学生输出（5个字符串），
                                若提供则自动提交，否则每步需单独调用 submit_step_output

    返回：
        完整工作流结果字典（与 complete_workflow 相同）
    """
    engine = LearningWorkflowEngine(
        topic=topic,
        user_id=user_id,
        level=level,
        model_name=model_name,
    )

    # 启动工作流
    start_result = engine.start_workflow()

    # 逐步骤提交输出（若有预置输出）
    if auto_submit_outputs and len(auto_submit_outputs) == len(STEP_NAMES):
        for i, output in enumerate(auto_submit_outputs):
            engine.submit_step_output(step_order=i + 1, user_output=output)
    else:
        # 若无预置输出，标记前4步为完成（讲解已生成），仅第5步需用户输出
        for i in range(len(STEP_NAMES) - 1):
            engine._steps[i]["step_completed"] = True
            engine._steps[i]["output_score"] = 100.0
        engine._total_score = 100.0

    # 完成工作流
    return engine.complete_workflow()


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("🧠 LumiLearn 五步学习法工作流引擎")
    print("=" * 60)

    topic = sys.argv[1] if len(sys.argv) > 1 else "勾股定理"
    print(f"\n📚 学习主题: {topic}\n")

    # 初始化数据库
    db.init()

    # 创建并运行工作流
    engine = LearningWorkflowEngine(topic=topic, user_id=1, level="junior")
    print("[1] 启动工作流...")
    start = engine.start_workflow()
    print(f"    workflow_id = {start['workflow_id']}")
    print(f"    status      = {start['status']}")
    for s in start["steps_summary"]:
        print(f"    步骤 {s['step_order']}: {s['step_name']}")

    print("\n[2] 模拟学生提交输出...")
    sample_outputs = [
        f"我在生活中见过{topic}的例子，比如……",
        f"但是{topic}是不是就是这样呢？好像不太对……",
        f"哦！我理解了，{topic}就像……",
        f"让我推导一下，根据前面的分析，{topic}应该是……",
        f"如果用30秒总结，{topic}就是：简单来说……",
    ]
    for i, output in enumerate(sample_outputs):
        result = engine.submit_step_output(step_order=i + 1, user_output=output)
        print(f"    步骤 {i+1} [{result['step_name']}]: "
              f"得分={result['score']}, 总均分={result['total_score']}")

    print("\n[3] 完成工作流...")
    final = engine.complete_workflow()
    print(f"    总得分: {final['total_score']}/100")
    print(f"    用时:   {final['duration_seconds']}s")
    print(f"    档案ID: {final['archive_id']}")

    print("\n[4] 查询状态...")
    status = engine.get_workflow_status()
    print(f"    状态:   {status['status']}")
    print(f"    总分:   {status['total_score']}")
    print(f"    步骤进度: {status['current_step']}/{status['total_steps']}")

    print("\n✅ 工作流引擎测试完成！")
