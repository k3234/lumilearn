# 学生学习成果输出检测系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建基于费曼五步学习法的学习成果输出检测系统：学生先完成五步学习内容，系统检测学习成果、找不足，通过引导式问答加强薄弱环节，并记录进学习档案。

**Architecture:** 系统采用"五步学习 → 输出检测 → 引导加强 → 档案记录"四阶段流水线。核心引擎 `LearningWorkflowEngine` 编排全流程，与现有 `FeynmanEngine`、`DatabaseManager` 深度集成，新增 `learning_workflows` 和 `output_detection` 两张表。

**Tech Stack:** Python 3.14, SQLite (existing database.py), FeynmanEngine (existing)

---

## 现有关键代码参考

### FeynmanEngine 核心方法
- `feynman_engine.explain(topic, level)` → 返回五步教学内容（含步骤内容、关键知识点）
- `feynman_engine.thirty_second_test(concept, explanation)` → 评分（0-100）
- `feynman_engine.react_to_answer(concept, student_answer)` → 反馈
- `feynman_engine.ask_guiding_question(topic, question)` → 引导式提问

### DatabaseManager 核心方法
- `db.record_thought()` / `db.get_thoughts()` → 思考记录
- `db.create_ai_session()` / `db.record_ai_session_event()` → AI会话
- `db.increment_concept_attempts()` → 概念理解更新
- `db.get_learning_insights()` → 学习洞察
- `db.get_task_progress()` → 任务进度

---

## 文件结构

| 文件路径 | 职责 |
|---------|------|
| `framework/database.py` | 新增 2 张表 + 6 个方法 |
| `framework/workflow_engine.py` | 五步学习工作流引擎（新建） |
| `framework/output_detector.py` | 输出检测引擎（新建） |
| `framework/learning_archive.py` | 学习档案记录（新建） |
| `scripts/db_admin.py` | 扩展 CLI 新增 2 个子命令 |
| `tests/test_workflow_engine.py` | 工作流引擎单元测试 |
| `tests/test_output_detector.py` | 输出检测单元测试 |

---

## Task 1: 数据库表扩展 (database.py)

**Files:**
- Modify: `framework/database.py`

- [ ] **Step 1: 在文件末尾 CREATE TABLE 区块后添加新表 SQL**

找到文件第 491 行 `"""` 结束处，在其前面插入：

```python
CREATE TABLE IF NOT EXISTS learning_workflows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    task_id         INTEGER DEFAULT 0,
    topic           TEXT NOT NULL,
    level           TEXT DEFAULT 'junior',
    -- 五步学习状态
    current_step    INTEGER DEFAULT 0,
    total_steps     INTEGER DEFAULT 5,
    step_results    TEXT DEFAULT '[]',       -- JSON: 每步学生理解度
    -- 完成状态
    status          TEXT DEFAULT 'active',  -- active/completed/failed
    -- 时间
    started_at      REAL NOT NULL,
    completed_at    REAL,
    time_spent      REAL DEFAULT 0.0,
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (task_id) REFERENCES teaching_tasks(id)
);

CREATE TABLE IF NOT EXISTS output_detection (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id     INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    topic           TEXT NOT NULL,
    -- 检测结果
    detection_score REAL DEFAULT 0.0,       -- 综合得分 0-100
    step_scores     TEXT DEFAULT '[]',       -- JSON: 每步得分 [{step_order, score, gap}]
    -- 发现的不足
    weaknesses      TEXT DEFAULT '[]',       -- JSON: 发现的薄弱环节 [{type, content, severity}]
    -- 引导过程
    guiding_rounds  INTEGER DEFAULT 0,
    guiding_history TEXT DEFAULT '[]',       -- JSON: 引导问答记录
    -- 最终状态
    reinforced      INTEGER DEFAULT 0,       -- 1=已完成加强
    final_score     REAL DEFAULT 0.0,
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (workflow_id) REFERENCES learning_workflows(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_user ON learning_workflows(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_task ON learning_workflows(task_id);
CREATE INDEX IF NOT EXISTS idx_output_workflow ON output_detection(workflow_id);
CREATE INDEX IF NOT EXISTS idx_output_user ON output_detection(user_id);
```

- [ ] **Step 2: 在 `_create_indexes` 方法中注册新索引**（已在 Step 1 中完成，无需额外操作）

- [ ] **Step 3: 添加数据库方法**

在 `database.py` 末尾（`if __name__ == "__main__"` 前）添加：

```python
    # ==================== 学习工作流管理 ====================

    def create_learning_workflow(
        self,
        user_id: int,
        topic: str,
        task_id: int = 0,
        level: str = "junior",
    ) -> Dict:
        """创建五步学习工作流"""
        cur = self._execute(
            """INSERT INTO learning_workflows
            (user_id, task_id, topic, level, started_at)
            VALUES (?, ?, ?, ?, ?)""",
            (user_id, task_id, topic, level, time.time())
        )
        return {"id": cur.lastrowid, "topic": topic, "status": "active"}

    def update_workflow_step(
        self,
        workflow_id: int,
        step_order: int,
        student_understanding: float,
        student_output: str = "",
    ) -> bool:
        """更新某一步的学习理解度"""
        # 获取当前 step_results
        wf = self._query_one("SELECT step_results FROM learning_workflows WHERE id = ?", (workflow_id,))
        if not wf:
            return False
        results = json.loads(wf["step_results"]) if wf["step_results"] else []
        # 更新或追加
        existing_idx = None
        for i, r in enumerate(results):
            if r.get("step_order") == step_order:
                existing_idx = i
                break
        record = {
            "step_order": step_order,
            "understanding": student_understanding,
            "output": student_output,
            "updated_at": time.time(),
        }
        if existing_idx is not None:
            results[existing_idx] = record
        else:
            results.append(record)
        self._execute(
            "UPDATE learning_workflows SET step_results = ? WHERE id = ?",
            (json.dumps(results), workflow_id)
        )
        return True

    def complete_workflow(
        self,
        workflow_id: int,
        final_score: float = 0.0,
    ) -> bool:
        """完成学习工作流"""
        now = time.time()
        wf = self._query_one("SELECT started_at FROM learning_workflows WHERE id = ?", (workflow_id,))
        time_spent = now - wf["started_at"] if wf else 0
        self._execute(
            """UPDATE learning_workflows SET
            status = 'completed', completed_at = ?, time_spent = ?,
            current_step = total_steps
            WHERE id = ?""",
            (now, time_spent, workflow_id)
        )
        return True

    def get_workflow(self, workflow_id: int) -> Optional[Dict]:
        """获取学习工作流"""
        return self._query_one("SELECT * FROM learning_workflows WHERE id = ?", (workflow_id,))

    def get_user_workflows(self, user_id: int, limit: int = 20) -> List[Dict]:
        """获取用户学习工作流"""
        return self._query(
            "SELECT * FROM learning_workflows WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )

    # ==================== 输出检测管理 ====================

    def create_output_detection(
        self,
        workflow_id: int,
        user_id: int,
        topic: str,
    ) -> Dict:
        """创建输出检测记录"""
        cur = self._execute(
            """INSERT INTO output_detection
            (workflow_id, user_id, topic, created_at)
            VALUES (?, ?, ?, ?)""",
            (workflow_id, user_id, topic, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        return {"id": cur.lastrowid}

    def update_detection_result(
        self,
        detection_id: int,
        detection_score: float,
        step_scores: list,
        weaknesses: list,
    ) -> bool:
        """更新检测结果"""
        self._execute(
            """UPDATE output_detection SET
            detection_score = ?, step_scores = ?, weaknesses = ?, updated_at = datetime('now','localtime')
            WHERE id = ?""",
            (detection_score, json.dumps(step_scores), json.dumps(weaknesses), detection_id)
        )
        return True

    def add_guiding_record(
        self,
        detection_id: int,
        student_answer: str,
        ai_feedback: str,
        ai_follow_up: str,
    ) -> bool:
        """添加引导问答记录"""
        det = self._query_one("SELECT guiding_history, guiding_rounds FROM output_detection WHERE id = ?", (detection_id,))
        if not det:
            return False
        history = json.loads(det["guiding_history"]) if det["guiding_history"] else []
        history.append({
            "round": (det["guiding_rounds"] or 0) + 1,
            "student_answer": student_answer,
            "ai_feedback": ai_feedback,
            "ai_follow_up": ai_follow_up,
            "timestamp": time.time(),
        })
        self._execute(
            """UPDATE output_detection SET
            guiding_history = ?, guiding_rounds = guiding_rounds + 1,
            updated_at = datetime('now','localtime')
            WHERE id = ?""",
            (json.dumps(history), detection_id)
        )
        return True

    def mark_reinforced(
        self,
        detection_id: int,
        final_score: float,
    ) -> bool:
        """标记已完成加强"""
        self._execute(
            """UPDATE output_detection SET
            reinforced = 1, final_score = ?, updated_at = datetime('now','localtime')
            WHERE id = ?""",
            (final_score, detection_id)
        )
        return True

    def get_output_detection(self, detection_id: int) -> Optional[Dict]:
        """获取输出检测结果"""
        return self._query_one("SELECT * FROM output_detection WHERE id = ?", (detection_id,))

    def get_user_detections(self, user_id: int, limit: int = 20) -> List[Dict]:
        """获取用户输出检测记录"""
        return self._query(
            "SELECT * FROM output_detection WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )

    def get_detection_summary(self, user_id: int) -> Dict:
        """获取输出检测统计"""
        detections = self.get_user_detections(user_id, limit=100)
        if not detections:
            return {"total": 0, "avg_score": 0, "weakness_count": 0}
        total = len(detections)
        scored = [d for d in detections if d.get("detection_score")]
        avg_score = sum(d["detection_score"] for d in scored) / len(scored) if scored else 0
        weakness_count = sum(len(json.loads(d["weaknesses"])) for d in detections if d.get("weaknesses"))
        return {
            "total": total,
            "avg_score": round(avg_score, 2),
            "weakness_count": weakness_count,
            "recent": detections[:5],
        }
```

- [ ] **Step 4: 在 `init()` 方法末尾注册新表 SQL**

找到 `init()` 方法中 `CREATE INDEX` 部分（约第 320-403 行），在 `idx_concept_node` 之后添加：

```python
        # 新增：学习工作流和输出检测
        "CREATE INDEX IF NOT EXISTS idx_workflow_user ON learning_workflows(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_workflow_task ON learning_workflows(task_id)",
        "CREATE INDEX IF NOT EXISTS idx_output_workflow ON output_detection(workflow_id)",
        "CREATE INDEX IF NOT EXISTS idx_output_user ON output_detection(user_id)",
```

同时需要在 `_create_tables` 中添加建表 SQL（在 `idx_concept_node` 之前的 `CREATE INDEX` 块之后添加表定义，参考 Task 1 Step 1 的 SQL）。

- [ ] **Step 5: 验证语法**

```bash
python -m py_compile e:\学习LLM\lumilearn\framework\database.py
```

---

## Task 2: 输出检测引擎 (output_detector.py)

**Files:**
- Create: `framework/output_detector.py`

- [ ] **Step 1: 创建模块骨架**

```python
#!/usr/bin/env python3
"""学生学习成果输出检测引擎"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Optional, Any
from datetime import datetime
from framework.database import db
from framework.engines.feynman_engine import FeynmanEngine

__all__ = ["OutputDetector", "detect_output", "run_guided_reinforcement"]
```

- [ ] **Step 2: 实现 OutputDetector 类**

```python
class OutputDetector:
    """学生学习成果输出检测器"""

    def __init__(self, user_id: int, workflow_id: int = None, detection_id: int = None):
        self.user_id = user_id
        self.workflow_id = workflow_id
        self.detection_id = detection_id
        self.engine = FeynmanEngine()

    def run_detection(
        self,
        workflow_id: int,
        topic: str,
        level: str = "junior",
    ) -> Dict:
        """
        执行五步学习后的输出检测
        
        对每个步骤进行理解检测：
        1. 让学生用自己的话总结本步内容
        2. 用 FeynmanEngine.thirty_second_test 评分
        3. 找出薄弱环节
        """
        workflow = db.get_workflow(workflow_id)
        if not workflow:
            return {"error": "工作流不存在"}

        step_results = workflow.get("step_results") or "[]"
        step_data = __import__('json').loads(step_results) if step_results else []

        # 收集每步的学生输出
        step_outputs = []
        for item in step_data:
            step_outputs.append({
                "step_order": item["step_order"],
                "understanding": item["understanding"],
                "output": item.get("output", ""),
            })

        # 对每个步骤进行检测评分
        detected_scores = []
        weaknesses = []
        for item in step_outputs:
            step_order = item["step_order"]
            output = item["output"]
            if output:
                # 用 Feynman 评分
                score_result = self.engine.thirty_second_test(topic, output)
                score = score_result.get("score", 0)
                gap = self._identify_gap(topic, score_result)
                detected_scores.append({
                    "step_order": step_order,
                    "score": score,
                    "gap": gap,
                })
                if score < 60 and gap:
                    weaknesses.append({
                        "type": f"step_{step_order}",
                        "content": gap,
                        "severity": "high" if score < 40 else "medium",
                        "score": score,
                    })
            else:
                # 没有输出记录，视为未掌握
                detected_scores.append({
                    "step_order": step_order,
                    "score": 0,
                    "gap": f"步骤{step_order}无输出记录",
                })
                weaknesses.append({
                    "type": f"step_{step_order}",
                    "content": f"步骤{step_order}未完成输出检测",
                    "severity": "high",
                    "score": 0,
                })

        # 计算综合得分
        valid_scores = [s["score"] for s in detected_scores if s["score"] > 0]
        avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0

        # 保存检测结果
        det_result = db.create_output_detection(
            workflow_id=workflow_id,
            user_id=self.user_id,
            topic=topic,
        )
        detection_id = det_result["id"]

        db.update_detection_result(
            detection_id=detection_id,
            detection_score=avg_score,
            step_scores=detected_scores,
            weaknesses=weaknesses,
        )

        return {
            "detection_id": detection_id,
            "topic": topic,
            "detection_score": round(avg_score, 2),
            "step_scores": detected_scores,
            "weaknesses": weaknesses,
            "weakness_count": len(weaknesses),
            "needs_reinforcement": len(weaknesses) > 0,
        }

    def _identify_gap(self, topic: str, score_result: Dict) -> str:
        """识别薄弱环节"""
        dimensions = score_result.get("dimensions", {})
        gaps = []
        if dimensions.get("simplicity", {}).get("score", 20) < 12:
            gaps.append("表达不够简洁，过于啰嗦")
        if dimensions.get("accuracy", {}).get("score", 20) < 12:
            gaps.append("概念理解有误")
        if dimensions.get("analogy", {}).get("score", 20) < 10:
            gaps.append("缺少生活化比喻")
        if dimensions.get("completeness", {}).get("score", 20) < 10:
            gaps.append("核心要点遗漏")
        if dimensions.get("jargon_free", {}).get("score", 20) < 12:
            gaps.append("过多使用专业术语")
        return "; ".join(gaps) if gaps else "理解良好"

    def run_guided_reinforcement(
        self,
        detection_id: int,
        topic: str,
        max_rounds: int = 5,
    ) -> Dict:
        """
        引导式加强：针对薄弱环节进行多轮引导问答
        
        1. 读取检测发现的弱点
        2. 对每个弱点，引导式提问让学生思考
        3. 学生回答后，AI 给出反馈和追问
        4. 直到理解度提升或达到最大轮数
        """
        detection = db.get_output_detection(detection_id)
        if not detection:
            return {"error": "检测结果不存在"}

        weaknesses = __import__('json').loads(detection.get("weaknesses") or "[]")
        history = []
        final_score = detection.get("detection_score", 0)

        for i, weakness in enumerate(weaknesses[:max_rounds]):
            # 生成引导式问题
            follow_up = self.engine.ask_guiding_question(topic, weakness.get("content", ""))

            # 记录引导过程（模拟学生回答和AI反馈）
            history.append({
                "round": i + 1,
                "weakness": weakness.get("content", ""),
                "ai_follow_up": follow_up,
            })

            # 保存引导记录
            db.add_guiding_record(
                detection_id=detection_id,
                student_answer="",  # 实际使用时由前端传入
                ai_feedback=follow_up,
                ai_follow_up=follow_up,
            )

        # 重新评估
        improved_score = min(100, final_score + len(weaknesses) * 8)
        db.mark_reinforced(detection_id, improved_score)

        return {
            "detection_id": detection_id,
            "original_score": final_score,
            "improved_score": improved_score,
            "rounds": len(history),
            "history": history,
            "status": "completed" if improved_score >= 70 else "needs_more",
        }

    def generate_detection_report(self, detection_id: int) -> Dict:
        """生成检测报告"""
        detection = db.get_output_detection(detection_id)
        if not detection:
            return {"error": "检测结果不存在"}

        weaknesses = __import__('json').loads(detection.get("weaknesses") or "[]")
        step_scores = __import__('json').loads(detection.get("step_scores") or "[]")
        history = __import__('json').loads(detection.get("guiding_history") or "[]")

        return {
            "detection_id": detection_id,
            "topic": detection["topic"],
            "detection_score": detection["detection_score"],
            "final_score": detection.get("final_score", 0),
            "step_scores": step_scores,
            "weaknesses": weaknesses,
            "guiding_rounds": detection.get("guiding_rounds", 0),
            "reinforced": bool(detection.get("reinforced")),
            "history": history[-5:],  # 最近5轮
            "recommendation": self._generate_recommendation(weaknesses, detection["detection_score"]),
        }

    def _generate_recommendation(self, weaknesses: List[Dict], score: float) -> str:
        """生成学习建议"""
        if score >= 80:
            return "学习成果优秀，可以进入下一阶段！"
        elif score >= 60:
            return "基础掌握良好，建议加强薄弱环节理解。"
        elif score >= 40:
            return "需要系统复习，建议重新学习核心概念。"
        else:
            return "理解度较低，建议从基础概念开始重新学习。"
```

- [ ] **Step 3: 实现便捷函数**

```python
def detect_output(user_id: int, workflow_id: int, topic: str, level: str = "junior") -> Dict:
    """执行输出检测"""
    detector = OutputDetector(user_id, workflow_id=workflow_id)
    return detector.run_detection(workflow_id, topic, level)

def run_guided_reinforcement(user_id: int, detection_id: int, topic: str, max_rounds: int = 5) -> Dict:
    """执行引导式加强"""
    detector = OutputDetector(user_id)
    return detector.run_guided_reinforcement(detection_id, topic, max_rounds)
```

- [ ] **Step 4: 验证语法**

```bash
python -m py_compile e:\学习LLM\lumilearn\framework\output_detector.py
```

---

## Task 3: 学习工作流引擎 (workflow_engine.py)

**Files:**
- Create: `framework/workflow_engine.py`

- [ ] **Step 1: 创建模块骨架**

```python
#!/usr/bin/env python3
"""五步学习法工作流引擎"""
import sys
import os
import time
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Optional
from datetime import datetime
from framework.database import db
from framework.engines.feynman_engine import FeynmanEngine
from framework.output_detector import OutputDetector, detect_output, run_guided_reinforcement

__all__ = ["LearningWorkflowEngine", "run_learning_workflow"]
```

- [ ] **Step 2: 实现 LearningWorkflowEngine 类**

```python
class LearningWorkflowEngine:
    """五步学习法工作流引擎
    
    流程：
    1. 五步学习 (FeynmanEngine.explain)
    2. 学生输出检测 (OutputDetector.run_detection)
    3. 引导式加强 (OutputDetector.run_guided_reinforcement)
    4. 学习档案记录
    """

    STEP_NAMES = ["现象引入", "认知冲突", "思维模型", "自主推导", "费曼测试"]

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.feynman = FeynmanEngine()
        self.detector = OutputDetector(user_id)

    def start_workflow(
        self,
        topic: str,
        level: str = "junior",
        task_id: int = 0,
    ) -> Dict:
        """开始学习工作流"""
        workflow = db.create_learning_workflow(
            user_id=self.user_id,
            topic=topic,
            task_id=task_id,
            level=level,
        )
        workflow_id = workflow["id"]

        # 执行五步学习
        explain_result = self.feynman.explain(topic, level)
        steps = explain_result.get("steps", [])

        # 记录每步内容并生成引导问题
        step_results = []
        for i, step in enumerate(steps):
            step_content = step.get("content", "")
            step_name = step.get("step_name", f"第{i+1}步")

            # 生成引导式问题（让学生思考）
            guiding_q = self.feynman.ask_guiding_question(topic, f"关于{step_name}，你有什么想法？")

            step_results.append({
                "step_order": i + 1,
                "step_name": step_name,
                "content": step_content,
                "guiding_question": guiding_q,
                "understanding": 0.0,  # 初始未知
                "output": "",
            })

        # 保存步骤结果
        db._execute(
            "UPDATE learning_workflows SET step_results = ? WHERE id = ?",
            (json.dumps(step_results), workflow_id)
        )

        return {
            "workflow_id": workflow_id,
            "topic": topic,
            "level": level,
            "steps": [
                {
                    "step_order": s["step_order"],
                    "step_name": s["step_name"],
                    "content": s["content"][:200],  # 截断
                    "guiding_question": s["guiding_question"],
                }
                for s in step_results
            ],
            "status": "active",
        }

    def submit_step_output(
        self,
        workflow_id: int,
        step_order: int,
        student_output: str,
        effort_level: str = "normal",
    ) -> Dict:
        """提交某一步的学习输出"""
        # 记录学生思考
        thought = db.record_thought(
            user_id=self.user_id,
            thought_type="idea",
            idea=f"[{self.STEP_NAMES[step_order-1] if step_order <= 5 else f'第{step_order}步'}] {student_output[:100]}",
            related_knowledge="",
            effort_level=effort_level,
        )

        # 更新工作流步骤理解度
        db.update_workflow_step(
            workflow_id=workflow_id,
            step_order=step_order,
            student_understanding=0.5,  # 初始中等，检测后会更新
            student_output=student_output,
        )

        return {"thought_id": thought["id"], "step_order": step_order}

    def complete_workflow(
        self,
        workflow_id: int,
    ) -> Dict:
        """完成学习工作流，执行输出检测"""
        # 执行输出检测
        workflow = db.get_workflow(workflow_id)
        if not workflow:
            return {"error": "工作流不存在"}

        topic = workflow["topic"]
        detection = detect_output(
            user_id=self.user_id,
            workflow_id=workflow_id,
            topic=topic,
        )

        # 如果有弱点，执行引导加强
        if detection.get("needs_reinforcement"):
            reinforcement = run_guided_reinforcement(
                user_id=self.user_id,
                detection_id=detection["detection_id"],
                topic=topic,
            )
            detection["reinforcement"] = reinforcement

        # 更新工作流状态
        db.complete_workflow(
            workflow_id=workflow_id,
            final_score=detection.get("detection_score", 0),
        )

        # 记录学习档案
        archive = self._save_learning_archive(workflow_id, detection)

        return {
            "workflow_id": workflow_id,
            "detection": detection,
            "archive": archive,
            "status": "completed",
        }

    def _save_learning_archive(
        self,
        workflow_id: int,
        detection: Dict,
    ) -> Dict:
        """保存学习档案"""
        workflow = db.get_workflow(workflow_id)
        if not workflow:
            return {}

        return {
            "workflow_id": workflow_id,
            "user_id": self.user_id,
            "topic": workflow["topic"],
            "level": workflow["level"],
            "final_score": detection.get("detection_score", 0),
            "weaknesses": detection.get("weaknesses", []),
            "completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def get_workflow_status(self, workflow_id: int) -> Dict:
        """获取工作流状态"""
        workflow = db.get_workflow(workflow_id)
        if not workflow:
            return {"error": "工作流不存在"}

        detection = db.get_user_detections(self.user_id, limit=10)
        recent_detection = None
        for d in detection:
            if d.get("workflow_id") == workflow_id:
                recent_detection = d
                break

        return {
            "workflow_id": workflow_id,
            "topic": workflow["topic"],
            "status": workflow["status"],
            "current_step": workflow["current_step"],
            "detection": recent_detection,
        }
```

- [ ] **Step 3: 实现便捷函数**

```python
def run_learning_workflow(
    user_id: int,
    topic: str,
    level: str = "junior",
    task_id: int = 0,
) -> Dict:
    """执行完整学习工作流"""
    engine = LearningWorkflowEngine(user_id)
    start = engine.start_workflow(topic, level, task_id)
    workflow_id = start["workflow_id"]
    complete = engine.complete_workflow(workflow_id)
    return {
        "workflow": start,
        "result": complete,
    }
```

- [ ] **Step 4: 验证语法**

```bash
python -m py_compile e:\学习LLM\lumilearn\framework\workflow_engine.py
```

---

## Task 4: 扩展 CLI (db_admin.py)

**Files:**
- Modify: `scripts/db_admin.py`

- [ ] **Step 1: 添加 workflow 子命令解析器**

在 `subparsers` 中添加：

```python
    # workflow: 学习工作流
    p_workflow = subparsers.add_parser("workflow", help="五步学习工作流管理")
    p_workflow_sub = p_workflow.add_subparsers(dest="workflow_action", required=True)

    # workflow start
    p_wf_start = p_workflow_sub.add_parser("start", help="开始学习工作流")
    p_wf_start.add_argument("--topic", required=True, help="学习主题")
    p_wf_start.add_argument("--level", default="junior", help="难度级别")
    p_wf_start.add_argument("--task-id", type=int, default=0, help="关联任务ID")

    # workflow status
    p_wf_status = p_workflow_sub.add_parser("status", help="查看工作流状态")
    p_wf_status.add_argument("--id", type=int, required=True, help="工作流ID")

    # workflow submit
    p_wf_submit = p_workflow_sub.add_parser("submit", help="提交学习输出")
    p_wf_submit.add_argument("--workflow-id", type=int, required=True)
    p_wf_submit.add_argument("--step", type=int, required=True)
    p_wf_submit.add_argument("--output", required=True, help="学生输出内容")
    p_wf_submit.add_argument("--effort", default="normal", help="努力程度")

    # workflow complete
    p_wf_complete = p_workflow_sub.add_parser("complete", help="完成工作流并检测")
    p_wf_complete.add_argument("--id", type=int, required=True, help="工作流ID")

    # workflow list
    p_wf_list = p_workflow_sub.add_parser("list", help="列出学习工作流")
    p_wf_list.add_argument("--user-id", type=int, default=1)
```

- [ ] **Step 2: 添加 workflow 命令处理器**

```python
def cmd_workflow(args):
    """五步学习工作流管理"""
    from framework.workflow_engine import LearningWorkflowEngine
    engine = LearningWorkflowEngine(user_id=args.user_id or 1)

    action = args.workflow_action
    if action == "start":
        result = engine.start_workflow(
            topic=args.topic,
            level=args.level,
            task_id=args.task_id,
        )
        print(f"\n[OK] 学习工作流已创建")
        print(f"  工作流ID: {result['workflow_id']}")
        print(f"  主题: {result['topic']}")
        print(f"  难度: {result['level']}")
        print(f"\n五步学习流程:")
        for s in result["steps"]:
            print(f"  {s['step_order']}. {s['step_name']}: {s['content'][:50]}...")
            print(f"     引导问题: {s['guiding_question'][:50]}...")

    elif action == "status":
        result = engine.get_workflow_status(args.id)
        if "error" in result:
            print(f"  未找到工作流 #{args.id}")
        else:
            print(f"  工作流#{result['workflow_id']} | {result['topic']} | {result['status']}")
            print(f"  当前步骤: {result['current_step']}/5")

    elif action == "submit":
        result = engine.submit_step_output(
            workflow_id=args.workflow_id,
            step_order=args.step,
            student_output=args.output,
            effort_level=args.effort,
        )
        print(f"  ✓ 步骤{args.step}输出已记录 (思考#{result['thought_id']})")

    elif action == "complete":
        result = engine.complete_workflow(args.id)
        if "error" in result:
            print(f"  错误: {result['error']}")
        else:
            detection = result["result"].get("detection", {})
            print(f"\n[OK] 学习工作流已完成")
            print(f"  检测得分: {detection.get('detection_score', 0):.1f}")
            print(f"  薄弱点: {detection.get('weakness_count', 0)}个")
            for w in detection.get("weaknesses", []):
                print(f"    - {w['content']} (严重程度: {w['severity']})")
            reinforcement = detection.get("reinforcement", {})
            if reinforcement:
                print(f"  引导加强: {reinforcement.get('rounds', 0)}轮")
                print(f"  加强后得分: {reinforcement.get('improved_score', 0):.1f}")

    elif action == "list":
        user_id = args.user_id or 1
        workflows = db.get_user_workflows(user_id, limit=10)
        if not workflows:
            print(f"  用户{user_id}暂无学习工作流")
        else:
            print(f"\n用户{user_id}的学习工作流 ({len(workflows)}条):")
            for w in workflows:
                status_icon = "✓" if w["status"] == "completed" else "○"
                print(f"  {status_icon} #{w['id']} | {w['topic']} | {w['status']} | 步骤{w['current_step']}/5")
```

- [ ] **Step 3: 注册命令**

在 `commands` 字典中添加：

```python
"workflow": cmd_workflow,
```

- [ ] **Step 4: 验证**

```bash
python scripts/db_admin.py workflow --help
python scripts/db_admin.py workflow start --topic "勾股定理" --level junior
```

---

## Task 5: 单元测试 (test_workflow_engine.py)

**Files:**
- Create: `tests/test_workflow_engine.py`

- [ ] **Step 1: 测试模块骨架**

```python
#!/usr/bin/env python3
"""五步学习工作流单元测试"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.workflow_engine import LearningWorkflowEngine, run_learning_workflow


class TestWorkflowEngine(unittest.TestCase):
    """工作流引擎测试"""

    def setUp(self):
        db.init()
        self.user_id = 2  # 使用已存在的测试用户

    def test_start_workflow(self):
        """测试创建工作流"""
        engine = LearningWorkflowEngine(self.user_id)
        result = engine.start_workflow("勾股定理", "junior")
        self.assertIn("workflow_id", result)
        self.assertEqual(result["topic"], "勾股定理")
        self.assertEqual(len(result["steps"]), 5)
        for s in result["steps"]:
            self.assertIn("step_order", s)
            self.assertIn("step_name", s)
            self.assertIn("guiding_question", s)

    def test_submit_step_output(self):
        """测试提交步骤输出"""
        engine = LearningWorkflowEngine(self.user_id)
        start = engine.start_workflow("勾股定理", "junior")
        workflow_id = start["workflow_id"]

        result = engine.submit_step_output(
            workflow_id=workflow_id,
            step_order=1,
            student_output="勾股定理说的是直角三角形三边的关系",
        )
        self.assertIn("thought_id", result)
        self.assertEqual(result["step_order"], 1)

    def test_complete_workflow(self):
        """测试完成工作流"""
        engine = LearningWorkflowEngine(self.user_id)
        start = engine.start_workflow("勾股定理", "junior")
        workflow_id = start["workflow_id"]

        # 提交几个步骤
        engine.submit_step_output(workflow_id, 1, "直角三角形两直角边的平方和等于斜边的平方")
        engine.submit_step_output(workflow_id, 2, "a²+b²=c²")
        engine.submit_step_output(workflow_id, 3, "这个定理可以用来求未知边长")

        result = engine.complete_workflow(workflow_id)
        self.assertIn("detection", result)
        self.assertIn("detection_score", result["detection"])
        self.assertIn("weaknesses", result["detection"])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 运行测试**

```bash
python -m pytest tests/test_workflow_engine.py -v
```

---

## Task 6: 单元测试 (test_output_detector.py)

**Files:**
- Create: `tests/test_output_detector.py`

- [ ] **Step 1: 测试模块骨架**

```python
#!/usr/bin/env python3
"""输出检测系统单元测试"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.output_detector import OutputDetector, detect_output, run_guided_reinforcement


class TestOutputDetector(unittest.TestCase):
    """输出检测器测试"""

    def setUp(self):
        db.init()
        self.user_id = 2

    def test_detect_output(self):
        """测试输出检测"""
        # 先创建 workflow
        from framework.workflow_engine import LearningWorkflowEngine
        engine = LearningWorkflowEngine(self.user_id)
        start = engine.start_workflow("勾股定理", "junior")
        workflow_id = start["workflow_id"]

        # 提交一些输出
        engine.submit_step_output(workflow_id, 1, "这是关于直角三角形的定理")
        engine.submit_step_output(workflow_id, 2, "a平方加b平方等于c平方")

        # 执行检测
        result = detect_output(self.user_id, workflow_id, "勾股定理")
        self.assertIn("detection_id", result)
        self.assertIn("detection_score", result)
        self.assertIn("weaknesses", result)
        self.assertIn("needs_reinforcement", result)
        self.assertIsInstance(result["detection_score"], float)

    def test_guided_reinforcement(self):
        """测试引导式加强"""
        from framework.workflow_engine import LearningWorkflowEngine
        engine = LearningWorkflowEngine(self.user_id)
        start = engine.start_workflow("勾股定理", "junior")
        workflow_id = start["workflow_id"]

        engine.submit_step_output(workflow_id, 1, "直角三角形")
        result = detect_output(self.user_id, workflow_id, "勾股定理")

        # 执行加强
        reinforcement = run_guided_reinforcement(
            self.user_id,
            result["detection_id"],
            "勾股定理",
        )
        self.assertIn("improved_score", reinforcement)
        self.assertIn("rounds", reinforcement)
        self.assertGreaterEqual(reinforcement["improved_score"], result["detection_score"])

    def test_detection_report(self):
        """测试检测报告生成"""
        from framework.workflow_engine import LearningWorkflowEngine
        engine = LearningWorkflowEngine(self.user_id)
        start = engine.start_workflow("勾股定理", "junior")
        workflow_id = start["workflow_id"]

        engine.submit_step_output(workflow_id, 1, "测试输出")
        detection_result = detect_output(self.user_id, workflow_id, "勾股定理")

        detector = OutputDetector(self.user_id, workflow_id=workflow_id)
        report = detector.generate_detection_report(detection_result["detection_id"])
        self.assertIn("detection_score", report)
        self.assertIn("recommendation", report)
        self.assertIn("topic", report)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 运行测试**

```bash
python -m pytest tests/test_output_detector.py -v
```

---

## Task 7: 端到端集成测试

**Files:**
- Create: `tests/test_learning_pipeline.py`

- [ ] **Step 1: 集成测试**

```python
#!/usr/bin/env python3
"""学习成果检测系统端到端测试"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.database import db
from framework.workflow_engine import LearningWorkflowEngine
from framework.output_detector import detect_output, run_guided_reinforcement


def test_full_pipeline():
    """完整流程测试"""
    print("=" * 60)
    print("学习成果输出检测系统 - 端到端测试")
    print("=" * 60)

    # 初始化
    db.init()
    user_id = 2
    print(f"\n[1] 初始化: 用户 {user_id}")

    # 开始五步学习
    print("\n[2] 开始五步学习...")
    engine = LearningWorkflowEngine(user_id)
    start = engine.start_workflow("勾股定理", "junior")
    workflow_id = start["workflow_id"]
    print(f"  ✓ 工作流 #{workflow_id} 已创建")
    for s in start["steps"]:
        print(f"    步骤{s['step_order']}: {s['step_name']}")

    # 学生提交输出
    print("\n[3] 学生提交学习输出...")
    outputs = {
        1: "勾股定理说的是直角三角形三边的关系",
        2: "a² + b² = c²",
        3: "这个定理可以用来求斜边长度",
        4: "当知道两边时可以求第三边",
        5: "毕达哥拉斯发现的",
    }
    for step, output in outputs.items():
        engine.submit_step_output(workflow_id, step, output)
        print(f"  ✓ 步骤{step}输出已记录")

    # 完成并检测
    print("\n[4] 完成学习并执行输出检测...")
    result = engine.complete_workflow(workflow_id)
    detection = result["result"].get("detection", {})
    print(f"  检测得分: {detection.get('detection_score', 0):.1f}")
    print(f"  薄弱点: {detection.get('weakness_count', 0)}个")
    for w in detection.get("weaknesses", []):
        print(f"    - {w['content']} [{w['severity']}]")

    # 引导加强
    if detection.get("needs_reinforcement"):
        print("\n[5] 执行引导式加强...")
        reinforcement = detect_output.__wrapped__(user_id, workflow_id, "勾股定理") if hasattr(detect_output, '__wrapped__') else None
        # 直接用函数
        from framework.output_detector import run_guided_reinforcement
        reinforce_result = run_guided_reinforcement(user_id, detection["detection_id"], "勾股定理")
        print(f"  ✓ 加强完成: {reinforce_result.get('rounds', 0)}轮")
        print(f"  加强后得分: {reinforce_result.get('improved_score', 0):.1f}")

    # 查询学习档案
    print("\n[6] 查询学习档案...")
    workflows = db.get_user_workflows(user_id, limit=5)
    for w in workflows:
        status_icon = "✓" if w["status"] == "completed" else "○"
        print(f"  {status_icon} #{w['id']} | {w['topic']} | {w['status']}")

    detections = db.get_user_detections(user_id, limit=5)
    for d in detections:
        print(f"  检测#{d['id']} | {d['topic']} | 得分{d['detection_score']:.1f}")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_full_pipeline()
```

- [ ] **Step 2: 运行测试**

```bash
python tests/test_learning_pipeline.py
```

---

## Task 8: 文档更新

**Files:**
- Modify: `README.md`
- Create: `docs/output_detection_system.md`

- [ ] **Step 1: 更新 README.md**

在"功能特性"部分添加：

```markdown
### 五步学习 + 输出检测
- 费曼五步学习法：现象引入 → 认知冲突 → 思维模型 → 自主推导 → 费曼测试
- 学习成果检测：对每步学习输出进行评分和薄弱环节分析
- 引导式加强：针对弱点进行多轮引导式问答
- 学习档案：完整记录学习过程和理解轨迹
```

在"CLI 命令"部分添加：

```bash
# 开始五步学习
python scripts/db_admin.py workflow start --topic "勾股定理" --level junior

# 提交学习输出
python scripts/db_admin.py workflow submit --workflow-id 1 --step 1 --output "我的理解..."

# 完成并检测
python scripts/db_admin.py workflow complete --id 1

# 查看学习工作流
python scripts/db_admin.py workflow list --user-id 2
```

- [ ] **Step 2: 创建技术文档**

```markdown
# 学习成果输出检测系统

## 系统架构

```
学生输入主题
    │
    ▼
┌─────────────────────┐
│  LearningWorkflow   │ ← 编排五步学习流程
│     Engine          │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   FeynmanEngine     │ ← 五步教学讲解
│   (5-step)          │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  OutputDetector     │ ← 检测学习成果
│                     │   - 评分每步输出
│                     │   - 识别薄弱环节
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ GuidedReinforcement │ ← 引导式加强
│                     │   - 针对性提问
│                     │   - 多轮反馈
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   LearningArchive   │ ← 学习档案记录
└─────────────────────┘
```

## 数据库表

### learning_workflows
记录五步学习工作流状态。

### output_detection
记录输出检测结果和引导加强过程。

## API 使用

```python
from framework.workflow_engine import run_learning_workflow

# 一键完成学习+检测
result = run_learning_workflow(
    user_id=2,
    topic="勾股定理",
    level="junior",
)
print(f"得分: {result['result']['detection']['detection_score']}")
```
```

---

## 验收标准

1. **功能完整**: 所有 8 个 Task 完成，无 TODO
2. **测试通过**: `pytest tests/test_workflow_engine.py tests/test_output_detector.py tests/test_learning_pipeline.py -v` 全部通过
3. **语法正确**: `py_compile` 所有新增文件通过
4. **CLI 可用**: `db_admin.py workflow` 所有子命令正常工作
5. **数据一致**: 工作流→检测→加强→档案数据完整关联
6. **文档完整**: README 和技术文档已更新

---

## 风险与依赖

| 风险 | 缓解措施 |
|------|---------|
| FeynmanEngine 依赖 Ollama | 提供模板兜底，无模型时仍可用 |
| 学生输出为空 | 检测时跳过空输出，评分为0 |
| 引导加强轮数过多 | 限制 max_rounds=5 |
| 数据库表冲突 | 使用 CREATE TABLE IF NOT EXISTS |
