"""
Base Agent Abstract Class for Autonomous Multi-Agent Runtime
"""
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentEvent(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    agent_name: str
    stage: str
    message: str
    level: str = "info"  # "info", "success", "warning", "error"
    data: Optional[Dict[str, Any]] = None


class AgentContext(BaseModel):
    project_id: str
    incident_id: str
    job_id: str
    workspace_path: Optional[str] = None
    model_name: str = "llama-3.1-70b-versatile"
    state: Dict[str, Any] = Field(default_factory=dict)
    events: List[AgentEvent] = Field(default_factory=list)

    def log(self, agent_name: str, stage: str, message: str, level: str = "info", data: Optional[Dict[str, Any]] = None):
        event = AgentEvent(
            timestamp=time.time(),
            agent_name=agent_name,
            stage=stage,
            message=message,
            level=level,
            data=data
        )
        self.events.append(event)


class BaseAgent(ABC):
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    @abstractmethod
    async def run(self, context: AgentContext, db_session: Any) -> Dict[str, Any]:
        """Execute agent task and return results to be updated into context."""
        pass
