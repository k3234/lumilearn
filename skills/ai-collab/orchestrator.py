"""
AI-Collab 多智能体协调器
实现多个AI Agent的协作执行
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from queue import PriorityQueue
import hashlib
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AgentCapability:
    """Agent能力定义"""
    skills: List[str]
    subjects: List[str] = field(default_factory=list)
    max_length: int = 5000
    languages: List[str] = field(default_factory=lambda: ["zh"])
    animation_types: List[str] = field(default_factory=list)
    question_types: List[str] = field(default_factory=list)
    difficulty_range: List[float] = field(default_factory=lambda: [0.3, 0.9])
    metrics: List[str] = field(default_factory=list)


@dataclass
class SubTask:
    """子任务定义"""
    id: str
    agent_type: str
    action: str
    input_data: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    estimated_time: int = 30
    priority: int = 5
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class TaskResult:
    """任务结果"""
    subtask_id: str
    agent_type: str
    status: str  # success, failed, retrying
    output: Any
    execution_time: float
    quality_score: float = 0.0
    error_message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class BaseAgent:
    """Agent基类"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.capability = self._define_capability()
        self.stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "avg_execution_time": 0.0
        }
    
    def _define_capability(self) -> AgentCapability:
        """定义Agent能力，子类重写"""
        return AgentCapability(skills=[])
    
    async def execute(self, subtask: SubTask, dependencies: Dict[str, TaskResult]) -> TaskResult:
        """执行子任务，子类重写"""
        raise NotImplementedError
    
    def can_handle(self, task_type: str, requirements: List[str]) -> bool:
        """检查是否能处理任务类型"""
        return task_type in self.capability.skills
    
    def update_stats(self, execution_time: float, success: bool):
        """更新统计信息"""
        self.stats["total_tasks"] += 1
        if success:
            self.stats["successful_tasks"] += 1
        else:
            self.stats["failed_tasks"] += 1
        
        # 更新平均执行时间
        total = self.stats["total_tasks"]
        old_avg = self.stats["avg_execution_time"]
        self.stats["avg_execution_time"] = (old_avg * (total - 1) + execution_time) / total


class ContentAgent(BaseAgent):
    """内容生成Agent"""
    
    def _define_capability(self) -> AgentCapability:
        return AgentCapability(
            skills=["content_generation", "latex", "markdown"],
            subjects=["math", "physics", "chemistry", "english", "chinese"],
            max_length=5000,
            languages=["zh", "en"]
        )
    
    async def execute(self, subtask: SubTask, dependencies: Dict[str, TaskResult]) -> TaskResult:
        """生成教学内容"""
        start_time = time.time()
        
        try:
            # 模拟内容生成（实际实现中调用AI模型）
            topic = subtask.input_data.get("topic", "")
            subject = subtask.input_data.get("subject", "")
            
            content = f"""
# {topic}

## 概念定义
{topic}是{subject}中的重要概念...

## 核心公式
$$E = mc^2$$

## 示例
例如：当m=1kg, c=3×10⁸m/s时...

## 应用场景
{topic}在实际生活中有广泛应用...
"""
            
            execution_time = time.time() - start_time
            self.update_stats(execution_time, True)
            
            return TaskResult(
                subtask_id=subtask.id,
                agent_type=self.name,
                status="success",
                output={"content": content, "word_count": len(content)},
                execution_time=execution_time,
                quality_score=0.9
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.update_stats(execution_time, False)
            
            return TaskResult(
                subtask_id=subtask.id,
                agent_type=self.name,
                status="failed",
                output=None,
                execution_time=execution_time,
                error_message=str(e)
            )


class AnimationAgent(BaseAgent):
    """动画生成Agent"""
    
    def _define_capability(self) -> AgentCapability:
        return AgentCapability(
            skills=["manim", "hyperframes", "animation_design"],
            animation_types=["formula", "concept", "process", "comparison"],
            max_length=3000
        )
    
    async def execute(self, subtask: SubTask, dependencies: Dict[str, TaskResult]) -> TaskResult:
        """生成动画脚本"""
        start_time = time.time()
        
        try:
            # 获取依赖的内容
            content = ""
            for dep_id, dep_result in dependencies.items():
                if isinstance(dep_result.output, dict) and "content" in dep_result.output:
                    content = dep_result.output["content"]
                    break
            
            # 模拟动画代码生成
            animation_code = f'''
from manim import *

class {subtask.input_data.get("topic", "Topic").replace(" ", "")}Scene(Scene):
    def construct(self):
        # 标题
        title = Text("{subtask.input_data.get("topic", "")}")
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))
        
        # 内容展示
        content = Text("概念讲解...")
        self.play(Write(content))
        self.wait(2)
'''
            
            execution_time = time.time() - start_time
            self.update_stats(execution_time, True)
            
            return TaskResult(
                subtask_id=subtask.id,
                agent_type=self.name,
                status="success",
                output={"animation_code": animation_code, "format": "manim"},
                execution_time=execution_time,
                quality_score=0.88
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.update_stats(execution_time, False)
            
            return TaskResult(
                subtask_id=subtask.id,
                agent_type=self.name,
                status="failed",
                output=None,
                execution_time=execution_time,
                error_message=str(e)
            )


class QuestionAgent(BaseAgent):
    """问答生成Agent"""
    
    def _define_capability(self) -> AgentCapability:
        return AgentCapability(
            skills=["question_generation", "answer_validation"],
            question_types=["choice", "fill_blank", "essay", "calculation"],
            difficulty_range=[0.3, 0.9]
        )
    
    async def execute(self, subtask: SubTask, dependencies: Dict[str, TaskResult]) -> TaskResult:
        """生成问答对"""
        start_time = time.time()
        
        try:
            topic = subtask.input_data.get("topic", "")
            
            questions = [
                {
                    "type": "choice",
                    "question": f"关于{topic}，以下说法正确的是？",
                    "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
                    "answer": "B",
                    "difficulty": 0.5
                },
                {
                    "type": "calculation",
                    "question": f"计算{topic}相关的数值...",
                    "answer": "42",
                    "difficulty": 0.7
                }
            ]
            
            execution_time = time.time() - start_time
            self.update_stats(execution_time, True)
            
            return TaskResult(
                subtask_id=subtask.id,
                agent_type=self.name,
                status="success",
                output={"questions": questions, "count": len(questions)},
                execution_time=execution_time,
                quality_score=0.92
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.update_stats(execution_time, False)
            
            return TaskResult(
                subtask_id=subtask.id,
                agent_type=self.name,
                status="failed",
                output=None,
                execution_time=execution_time,
                error_message=str(e)
            )


class EvaluationAgent(BaseAgent):
    """评估Agent"""
    
    def _define_capability(self) -> AgentCapability:
        return AgentCapability(
            skills=["content_evaluation", "quality_scoring", "error_detection"],
            metrics=["accuracy", "completeness", "clarity", "difficulty"]
        )
    
    async def execute(self, subtask: SubTask, dependencies: Dict[str, TaskResult]) -> TaskResult:
        """评估内容质量"""
        start_time = time.time()
        
        try:
            # 收集所有依赖结果
            scores = {}
            for dep_id, dep_result in dependencies.items():
                scores[dep_result.agent_type] = dep_result.quality_score
            
            # 计算整体质量分
            overall_score = sum(scores.values()) / len(scores) if scores else 0.0
            
            evaluation = {
                "overall_score": round(overall_score, 2),
                "individual_scores": scores,
                "metrics": {
                    "accuracy": 0.95,
                    "completeness": 0.88,
                    "clarity": 0.92,
                    "difficulty_appropriate": 0.85
                },
                "suggestions": [
                    "内容准确性高",
                    "可以增加更多示例",
                    "动画时长可适当缩短"
                ]
            }
            
            execution_time = time.time() - start_time
            self.update_stats(execution_time, True)
            
            return TaskResult(
                subtask_id=subtask.id,
                agent_type=self.name,
                status="success",
                output=evaluation,
                execution_time=execution_time,
                quality_score=overall_score
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.update_stats(execution_time, False)
            
            return TaskResult(
                subtask_id=subtask.id,
                agent_type=self.name,
                status="failed",
                output=None,
                execution_time=execution_time,
                error_message=str(e)
            )


class AICollabOrchestrator:
    """
    AI-Collab 协调器
    管理多个AI Agent的协作执行
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.agents: Dict[str, BaseAgent] = {}
        self.results: Dict[str, TaskResult] = {}
        self.task_history: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 初始化默认Agent
        self._init_default_agents()
    
    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "max_concurrent_tasks": 10,
            "task_timeout": 300,
            "retry_attempts": 3,
            "quality_threshold": 0.85,
            "parallel_execution": True
        }
    
    def _init_default_agents(self):
        """初始化默认Agent"""
        self.register_agent("ContentAgent", ContentAgent("ContentAgent", {}))
        self.register_agent("AnimationAgent", AnimationAgent("AnimationAgent", {}))
        self.register_agent("QuestionAgent", QuestionAgent("QuestionAgent", {}))
        self.register_agent("EvaluationAgent", EvaluationAgent("EvaluationAgent", {}))
    
    def register_agent(self, agent_type: str, agent_instance: BaseAgent):
        """注册Agent"""
        self.agents[agent_type] = agent_instance
        self.logger.info(f"Registered agent: {agent_type}")
    
    def create_task_plan(self, workflow_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建任务计划"""
        
        if workflow_name == "完整知识点生成":
            return self._create_complete_knowledge_plan(input_data)
        elif workflow_name == "批量内容生产":
            return self._create_batch_production_plan(input_data)
        else:
            # 默认简单计划
            return {
                "task_id": self._generate_task_id(),
                "task_type": workflow_name,
                "input": input_data,
                "subtasks": [
                    SubTask(
                        id="subtask_1",
                        agent_type="ContentAgent",
                        action="生成内容",
                        input_data=input_data,
                        dependencies=[],
                        estimated_time=30
                    )
                ],
                "parallel_groups": [["subtask_1"]]
            }
    
    def _create_complete_knowledge_plan(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建完整知识点生成计划"""
        task_id = self._generate_task_id()
        
        subtasks = [
            SubTask(
                id="subtask_1",
                agent_type="ContentAgent",
                action="生成知识点讲解",
                input_data=input_data,
                dependencies=[],
                estimated_time=30,
                priority=1
            ),
            SubTask(
                id="subtask_2",
                agent_type="AnimationAgent",
                action="创建证明动画",
                input_data=input_data,
                dependencies=["subtask_1"],
                estimated_time=60,
                priority=2
            ),
            SubTask(
                id="subtask_3",
                agent_type="QuestionAgent",
                action="生成练习题",
                input_data=input_data,
                dependencies=["subtask_1"],
                estimated_time=20,
                priority=2
            ),
            SubTask(
                id="subtask_4",
                agent_type="EvaluationAgent",
                action="质量评估",
                input_data=input_data,
                dependencies=["subtask_1", "subtask_2", "subtask_3"],
                estimated_time=15,
                priority=3
            )
        ]
        
        return {
            "task_id": task_id,
            "task_type": "完整知识点生成",
            "input": input_data,
            "subtasks": subtasks,
            "parallel_groups": [
                ["subtask_1"],
                ["subtask_2", "subtask_3"],
                ["subtask_4"]
            ]
        }
    
    def _create_batch_production_plan(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建批量生产计划"""
        task_id = self._generate_task_id()
        topics = input_data.get("topics", [])
        
        subtasks = []
        for i, topic in enumerate(topics):
            subtask = SubTask(
                id=f"batch_subtask_{i}",
                agent_type="ContentAgent",
                action=f"生成{topic}的内容",
                input_data={"topic": topic, **input_data},
                dependencies=[],
                estimated_time=30,
                priority=1
            )
            subtasks.append(subtask)
        
        return {
            "task_id": task_id,
            "task_type": "批量内容生产",
            "input": input_data,
            "subtasks": subtasks,
            "parallel_groups": [[s.id for s in subtasks]]  # 全部并行
        }
    
    def _generate_task_id(self) -> str:
        """生成任务ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_str = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
        return f"task_{timestamp}_{hash_str}"
    
    async def execute_task(self, task_plan: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务计划"""
        task_id = task_plan["task_id"]
        start_time = time.time()
        
        self.logger.info(f"Starting task execution: {task_id}")
        
        # 重置结果
        self.results = {}
        
        # 按并行组执行
        for group_idx, group in enumerate(task_plan["parallel_groups"]):
            self.logger.info(f"Executing parallel group {group_idx + 1}: {group}")
            
            if self.config.get("parallel_execution", True):
                # 并行执行
                tasks = [self._execute_subtask_by_id(task_plan, subtask_id) for subtask_id in group]
                await asyncio.gather(*tasks)
            else:
                # 串行执行
                for subtask_id in group:
                    await self._execute_subtask_by_id(task_plan, subtask_id)
        
        # 计算总耗时
        total_time = time.time() - start_time
        
        # 整合结果
        final_result = self._integrate_results(task_plan, total_time)
        
        # 记录历史
        self.task_history.append({
            "task_id": task_id,
            "task_type": task_plan["task_type"],
            "execution_time": total_time,
            "result": final_result,
            "timestamp": datetime.now()
        })
        
        self.logger.info(f"Task completed: {task_id}, time: {total_time:.2f}s")
        
        return final_result
    
    async def _execute_subtask_by_id(self, task_plan: Dict[str, Any], subtask_id: str):
        """根据ID执行子任务"""
        # 查找子任务
        subtask = None
        for st in task_plan["subtasks"]:
            if isinstance(st, SubTask) and st.id == subtask_id:
                subtask = st
                break
            elif isinstance(st, dict) and st.get("id") == subtask_id:
                subtask = SubTask(**st)
                break
        
        if not subtask:
            self.logger.error(f"Subtask not found: {subtask_id}")
            return
        
        await self._execute_subtask(subtask)
    
    async def _execute_subtask(self, subtask: SubTask):
        """执行子任务"""
        agent_type = subtask.agent_type
        
        if agent_type not in self.agents:
            self.logger.error(f"Agent not found: {agent_type}")
            self.results[subtask.id] = TaskResult(
                subtask_id=subtask.id,
                agent_type=agent_type,
                status="failed",
                output=None,
                execution_time=0,
                error_message=f"Agent {agent_type} not found"
            )
            return
        
        agent = self.agents[agent_type]
        
        # 获取依赖结果
        dependencies = {}
        for dep_id in subtask.dependencies:
            if dep_id in self.results:
                dependencies[dep_id] = self.results[dep_id]
        
        self.logger.info(f"Executing subtask: {subtask.id} with agent: {agent_type}")
        
        # 执行（带重试）
        result = None
        for attempt in range(subtask.max_retries):
            try:
                result = await asyncio.wait_for(
                    agent.execute(subtask, dependencies),
                    timeout=self.config.get("task_timeout", 300)
                )
                
                if result.status == "success":
                    break
                elif attempt < subtask.max_retries - 1:
                    self.logger.warning(f"Subtask {subtask.id} failed, retrying...")
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                    
            except asyncio.TimeoutError:
                self.logger.error(f"Subtask {subtask.id} timed out")
                result = TaskResult(
                    subtask_id=subtask.id,
                    agent_type=agent_type,
                    status="failed",
                    output=None,
                    execution_time=self.config.get("task_timeout", 300),
                    error_message="Task timeout"
                )
            except Exception as e:
                self.logger.error(f"Subtask {subtask.id} error: {e}")
                result = TaskResult(
                    subtask_id=subtask.id,
                    agent_type=agent_type,
                    status="failed",
                    output=None,
                    execution_time=0,
                    error_message=str(e)
                )
        
        self.results[subtask.id] = result
    
    def _integrate_results(self, task_plan: Dict[str, Any], total_time: float) -> Dict[str, Any]:
        """整合结果"""
        # 收集所有结果
        content_results = []
        animation_results = []
        question_results = []
        evaluation_results = []
        
        agents_involved = []
        
        for subtask_id, result in self.results.items():
            agents_involved.append({
                "type": result.agent_type,
                "time": result.execution_time
            })
            
            if result.status == "success" and result.output:
                if result.agent_type == "ContentAgent":
                    content_results.append(result.output)
                elif result.agent_type == "AnimationAgent":
                    animation_results.append(result.output)
                elif result.agent_type == "QuestionAgent":
                    question_results.append(result.output)
                elif result.agent_type == "EvaluationAgent":
                    evaluation_results.append(result.output)
        
        # 获取质量评分
        quality_score = 0.0
        if evaluation_results:
            quality_score = evaluation_results[0].get("overall_score", 0.0)
        
        return {
            "task_id": task_plan["task_id"],
            "status": "completed",
            "execution_time": total_time,
            "agents_involved": agents_involved,
            "results": {
                "content": content_results[0] if content_results else None,
                "animation": animation_results[0] if animation_results else None,
                "questions": question_results[0] if question_results else None,
                "evaluation": evaluation_results[0] if evaluation_results else None
            },
            "quality": {
                "overall_score": quality_score,
                "passed": quality_score >= self.config.get("quality_threshold", 0.85)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """获取Agent统计信息"""
        stats = {}
        for agent_type, agent in self.agents.items():
            stats[agent_type] = agent.stats
        return stats
    
    def get_task_history(self) -> List[Dict[str, Any]]:
        """获取任务历史"""
        return self.task_history


# 便捷函数
async def orchestrate_workflow(workflow_name: str, input_data: Dict[str, Any], 
                                config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    便捷函数：执行工作流
    
    示例:
        result = await orchestrate_workflow(
            "完整知识点生成",
            {"subject": "数学", "topic": "勾股定理", "grade": "初二"}
        )
    """
    orchestrator = AICollabOrchestrator(config)
    task_plan = orchestrator.create_task_plan(workflow_name, input_data)
    return await orchestrator.execute_task(task_plan)


if __name__ == "__main__":
    # 测试
    async def test():
        orchestrator = AICollabOrchestrator()
        
        # 测试完整知识点生成
        task_plan = orchestrator.create_task_plan("完整知识点生成", {
            "subject": "数学",
            "topic": "勾股定理",
            "grade": "初二"
        })
        
        print("Task Plan:")
        print(json.dumps({
            "task_id": task_plan["task_id"],
            "task_type": task_plan["task_type"],
            "parallel_groups": task_plan["parallel_groups"]
        }, indent=2, ensure_ascii=False))
        
        result = await orchestrator.execute_task(task_plan)
        
        print("\nExecution Result:")
        print(json.dumps({
            "task_id": result["task_id"],
            "status": result["status"],
            "execution_time": result["execution_time"],
            "quality": result["quality"],
            "agents_involved": result["agents_involved"]
        }, indent=2, ensure_ascii=False))
    
    asyncio.run(test())
