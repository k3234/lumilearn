# -*- coding: utf-8 -*-
"""
LumiLearn Agent 管理系统
- Agent 基类：统一生命周期（start/stop/status/run）
- 内置 Agent：feynman / detector / adaptive / chat
- Agent 注册表：注册、获取、启停、持久化到数据库
"""
import json
import logging
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable

from framework.database import db

logger = logging.getLogger("lumilearn.admin.agents")

# 全局运行状态（内存）
_agent_runners: Dict[str, Dict] = {}
_agents_lock = threading.Lock()


class BaseAgent(ABC):
    """Agent 基类"""

    def __init__(self, agent_id: str, name: str, agent_type: str, description: str = ""):
        self.agent_id = agent_id
        self.name = name
        self.agent_type = agent_type
        self.description = description

    @abstractmethod
    def run(self, payload: Dict) -> Dict:
        """执行 Agent 任务，返回结果"""
        raise NotImplementedError

    def health(self) -> Dict:
        """Agent 健康状态"""
        return {"agent_id": self.agent_id, "status": "healthy", "type": self.agent_type}

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "type": self.agent_type,
            "description": self.description,
        }


class FeynmanAgent(BaseAgent):
    """费曼五步教学 Agent"""

    def __init__(self):
        super().__init__(
            agent_id="feynman_teacher",
            name="费曼教学Agent",
            agent_type="feynman",
            description="基于费曼五步学习法讲解知识点",
        )

    def run(self, payload: Dict) -> Dict:
        from framework.engines.feynman_engine import FeynmanEngine
        topic = payload.get("topic", "")
        level = payload.get("level", "junior")
        dialogue = payload.get("dialogue")  # 提供对话历史则走交互式单步引导
        if not topic:
            return {"success": False, "error": "缺少 topic 参数"}
        # 优先使用配置的 feynman_model（上下文利用更强）
        model_name = None
        try:
            from framework.core.config import get_config
            cfg = get_config() or {}
            model_name = (cfg or {}).get("ollama", {}).get("feynman_model")
        except Exception:
            model_name = None
        engine = FeynmanEngine(model_name=model_name) if model_name else FeynmanEngine()
        if dialogue:
            step = engine.explain_step(topic=topic, level=level, dialogue=dialogue)
            return {"success": True, "topic": topic, "level": level, "step": step,
                    "mode": "interactive"}
        steps = engine.explain(topic=topic, level=level)
        return {"success": True, "topic": topic, "level": level, "steps": steps,
                "mode": "full"}


class DetectionAgent(BaseAgent):
    """学习输出检测 Agent"""

    def __init__(self):
        super().__init__(
            agent_id="output_detector",
            name="输出检测Agent",
            agent_type="detector",
            description="检测学生学习输出质量并给出改进建议",
        )

    def run(self, payload: Dict) -> Dict:
        from framework.output_detector import OutputDetector
        concept = payload.get("concept", "")
        output = payload.get("student_output", "")
        user_id = payload.get("user_id", 0)
        if not concept or not output:
            return {"success": False, "error": "缺少 concept 或 student_output 参数"}
        detector = OutputDetector(user_id=user_id)
        result = detector.run_detection(concept, output)
        return {
            "success": True,
            "concept": concept,
            "score": result.total_score,
            "is_mastered": result.is_mastered,
            "feedback": result.feedback,
        }


class AdaptiveAgent(BaseAgent):
    """自适应学习 Agent"""

    def __init__(self):
        super().__init__(
            agent_id="adaptive_path",
            name="自适应学习Agent",
            agent_type="adaptive",
            description="根据学生学习进度推荐学习路径",
        )

    def run(self, payload: Dict) -> Dict:
        from framework.services.adaptive_learning import get_adaptive_engine
        user_id = payload.get("user_id", 0)
        if not user_id:
            return {"success": False, "error": "缺少 user_id 参数"}
        service = get_adaptive_engine()
        recommendation = service.recommend_next(user_id=str(user_id), count=5)
        return {"success": True, "user_id": user_id, "recommendation": recommendation}


class ChatAgent(BaseAgent):
    """通用对话 Agent"""

    def __init__(self):
        super().__init__(
            agent_id="chat_assistant",
            name="对话助手Agent",
            agent_type="chat",
            description="通用多轮对话助手",
        )

    def run(self, payload: Dict) -> Dict:
        from framework.services.chat_service import get_chat_service
        message = payload.get("message", "")
        if not message:
            return {"success": False, "error": "缺少 message 参数"}
        service = get_chat_service()
        result = service.chat_sync([{"role": "user", "content": message}])
        if isinstance(result, dict):
            reply = result.get("content") or result.get("reply") or ""
        else:
            reply = str(result)
        return {"success": True, "message": message, "reply": reply}

    def health(self) -> Dict:
        from framework.services.chat_service import get_chat_service
        status = get_chat_service().health_check()
        return {"agent_id": self.agent_id, "status": status.get("status", "unknown"), "type": self.agent_type}


# ================================================================
# agent_core 统一编排 Agent（Phase 1 新增）
# ================================================================
class RouterTaskAgent(BaseAgent):
    """Router Agent — 任务路由与复杂度评估"""

    def __init__(self):
        super().__init__(
            agent_id="router_task",
            name="任务路由Agent",
            agent_type="router",
            description="分析任务复杂度并路由到最优执行路径",
        )

    def run(self, payload: Dict) -> Dict:
        from agent_core.router import get_router_agent
        topic = payload.get("topic", "")
        context = payload.get("context", "")
        if not topic:
            return {"success": False, "error": "缺少 topic 参数"}
        router = get_router_agent()
        result = router.route(topic, context)
        return {"success": True, "route_result": result}

    def health(self) -> Dict:
        return {"agent_id": self.agent_id, "status": "healthy", "type": self.agent_type}


class UnifiedOrchestratorAgent(BaseAgent):
    """统一编排 Agent — 整合 Router + LangGraph + 多 Agent 系统"""

    def __init__(self):
        super().__init__(
            agent_id="unified_orchestrator",
            name="统一编排Agent",
            agent_type="unified_orchestrator",
            description="统一编排：Router智能路由 + LangGraph并行 + 多Agent串行",
        )

    def run(self, payload: Dict) -> Dict:
        from agent_core.orchestrator import get_unified_orchestrator
        orch = get_unified_orchestrator()
        return orch.run(payload)

    def health(self) -> Dict:
        from agent_core.orchestrator import get_unified_orchestrator
        status = get_unified_orchestrator().get_status()
        return {
            "agent_id": self.agent_id,
            "status": "healthy",
            "type": self.agent_type,
            "registered_models": status.get("models", {}).get("total", 0),
        }


class FactCheckAgent(BaseAgent):
    """事实核查 Agent（P0-2）— 教学内容与 RAG 知识库来源二次核对，防语义幻觉"""

    def __init__(self):
        super().__init__(
            agent_id="fact_checker",
            name="事实核查Agent",
            agent_type="fact_checker",
            description="对教学内容做二次事实校验（与RAG来源核对），降低语义级幻觉风险",
        )

    def run(self, payload: Dict) -> Dict:
        from agent_core.fact_checker import get_fact_checker_agent
        topic = payload.get("topic", "")
        if not topic:
            return {"success": False, "error": "缺少 topic 参数"}
        result = get_fact_checker_agent().run(payload)
        # 统一 Agent 契约：失败以 success=False 表达（与编排层状态机兼容）
        result["success"] = bool(result.get("passed", False))
        return result

    def health(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "status": "healthy",
            "type": self.agent_type,
            "sources_checked": 0,
        }


# 内置 Agent 工厂
BUILTIN_AGENTS: List[Callable[[], BaseAgent]] = [
    FeynmanAgent,
    DetectionAgent,
    AdaptiveAgent,
    ChatAgent,
    # Phase 1 新增：统一编排体系
    RouterTaskAgent,
    UnifiedOrchestratorAgent,
    # P0-2 新增：事实核查
    FactCheckAgent,
]


class AgentRegistry:
    """Agent 注册表：管理 Agent 生命周期并持久化状态"""

    def __init__(self):
        self._ensure_builtins()

    def _ensure_builtins(self):
        """将内置 Agent 注册到数据库（幂等）"""
        try:
            for factory in BUILTIN_AGENTS:
                agent = factory()
                existing = db.get_agent(agent.agent_id)
                if not existing:
                    db.register_agent(
                        agent_id=agent.agent_id,
                        name=agent.name,
                        agent_type=agent.agent_type,
                        description=agent.description,
                    )
                    logger.info(f"Registered builtin agent: {agent.agent_id}")
        except Exception as e:
            logger.error(f"Failed to register builtins: {e}")

    def list_agents(self, agent_type: Optional[str] = None) -> List[Dict]:
        agents = db.get_agents(agent_type)
        for agent in agents:
            runner = _agent_runners.get(agent["agent_id"])
            agent["running"] = runner is not None
            agent["is_builtin"] = agent["agent_id"] in {a.agent_id for a in self._get_builtin_instances()}
        return agents

    def _get_builtin_instances(self) -> List[BaseAgent]:
        return [factory() for factory in BUILTIN_AGENTS]

    def get_agent(self, agent_id: str) -> Dict:
        agent = db.get_agent(agent_id)
        if not agent:
            raise KeyError(f"Agent not found: {agent_id}")
        agent["running"] = agent["agent_id"] in _agent_runners
        return agent

    def register(self, agent_id: str, name: str, agent_type: str,
                 description: str = "", config: Dict = None) -> Dict:
        result = db.register_agent(
            agent_id=agent_id,
            name=name,
            agent_type=agent_type,
            description=description,
            config=json.dumps(config or {}, ensure_ascii=False),
        )
        db.add_system_log("info", "agents", f"注册新Agent: {name} ({agent_id})")
        return result

    def _create_instance(self, agent: Dict) -> BaseAgent:
        """根据数据库记录创建 Agent 实例（支持自定义注册）"""
        for factory in BUILTIN_AGENTS:
            builtin = factory()
            if builtin.agent_id == agent["agent_id"]:
                return builtin
        # 自定义 Agent：动态创建通用实例
        return self._create_custom(agent)

    def _create_custom(self, agent: Dict) -> BaseAgent:
        config = json.loads(agent["config"] or "{}")
        runner = config.get("runner")  # 可选：可调用对象的模块路径（预留扩展）

        class _CustomAgent(BaseAgent):
            def run(self, payload: Dict) -> Dict:
                return {"success": True, "message": "自定义Agent已注册，执行器待配置", "payload": payload}

        return _CustomAgent(agent_id=agent["agent_id"], name=agent["name"],
                            agent_type=agent["agent_type"], description=agent["description"])

    def start(self, agent_id: str) -> Dict:
        agent = db.get_agent(agent_id)
        if not agent:
            raise KeyError(f"Agent not found: {agent_id}")
        with _agents_lock:
            if agent_id in _agent_runners:
                return {"success": True, "message": f"Agent {agent_id} 已在运行中"}
            instance = self._create_instance(agent)
            _agent_runners[agent_id] = {"instance": instance}
        db.update_agent_status(agent_id, "running")
        db.add_system_log("info", "agents", f"启动Agent: {agent['name']} ({agent_id})")
        return {"success": True, "message": f"Agent {agent_id} 已启动"}

    def stop(self, agent_id: str) -> Dict:
        with _agents_lock:
            if agent_id not in _agent_runners:
                return {"success": False, "message": f"Agent {agent_id} 未在运行"}
            _agent_runners.pop(agent_id, None)
        db.update_agent_status(agent_id, "stopped")
        db.add_system_log("info", "agents", f"停止Agent: {agent_id}")
        return {"success": True, "message": f"Agent {agent_id} 已停止"}

    def run_agent(self, agent_id: str, payload: Dict) -> Dict:
        """执行 Agent 任务（自动启动未运行实例）"""
        if agent_id not in _agent_runners:
            self.start(agent_id)
        runner = _agent_runners.get(agent_id)
        if not runner:
            return {"success": False, "error": f"Agent {agent_id} 启动失败"}
        try:
            instance = runner["instance"]
            result = instance.run(payload)
            result["agent_id"] = agent_id
            return result
        except Exception as e:
            logger.exception(f"Agent {agent_id} run error")
            db.update_agent_status(agent_id, "error")
            return {"success": False, "error": str(e)}

    def delete(self, agent_id: str) -> Dict:
        if agent_id in _agent_runners:
            self.stop(agent_id)
        db.delete_agent(agent_id)
        return {"success": True, "message": f"Agent {agent_id} 已删除"}

    def health(self, agent_id: Optional[str] = None) -> Dict:
        """Agent 健康检查"""
        if agent_id:
            agent = db.get_agent(agent_id)
            if not agent:
                return {"success": False, "error": f"Agent not found: {agent_id}"}
            runner = _agent_runners.get(agent_id)
            if runner:
                return runner["instance"].health()
            return {"agent_id": agent_id, "status": "stopped", "type": agent["agent_type"]}
        results = {}
        for agent in db.get_agents():
            runner = _agent_runners.get(agent["agent_id"])
            if runner:
                results[agent["agent_id"]] = runner["instance"].health()
            else:
                results[agent["agent_id"]] = {"agent_id": agent["agent_id"], "status": "stopped", "type": agent["agent_type"]}
        return {"agents": results, "total": len(results)}


# 单例
_registry_instance: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AgentRegistry()
    return _registry_instance
