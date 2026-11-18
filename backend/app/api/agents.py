"""
PHOENIX Autonomous Multi-Agent API Router
Exposes multi-agent execution orchestrator, timeline telemetry, and agent definitions.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.core.security import get_current_user
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.services.agents.orchestrator import agent_orchestrator
from sqlalchemy.orm import Session

router = APIRouter(prefix="/agents", tags=["Autonomous Multi-Agent Runtime"])


class AgentRunRequest(BaseModel):
    project_id: str
    incident_id: str
    model_name: Optional[str] = "llama-3.1-70b-versatile"


@router.get("/list")
def list_available_agents():
    """List all specialized autonomous agents operating within PHOENIX runtime."""
    return [
        {
            "id": "intelligence",
            "name": "ProjectIntelligenceAgent",
            "role": "Repository Architecture, AST Topology & Test Suite Discovery",
            "capabilities": ["AST Module Graphing", "Entrypoint Detection", "Framework Profiling"]
        },
        {
            "id": "diagnosis",
            "name": "DiagnosisAgent",
            "role": "Root Cause Reasoner & Crash Telemetry Analyst",
            "capabilities": ["Stack Trace Dissection", "Groq LLM Reasoning", "Reproduction Hypothesis"]
        },
        {
            "id": "repair",
            "name": "RepairAgent",
            "role": "Code Synthesis & Minimal Unified Diff Specialist",
            "capabilities": ["AST-Preserving Unified Diff", "Targeted Line Patching", "Context Matching"]
        },
        {
            "id": "testing",
            "name": "TestingAgent",
            "role": "Deterministic Sandbox Execution & Regression Validator",
            "capabilities": ["Process Isolation", "Test Output Stream Capture", "Regression Detection"]
        },
        {
            "id": "security",
            "name": "SecurityAgent",
            "role": "AST Vulnerability & Static Injection Auditor",
            "capabilities": ["Forbidden Token Veto", "SSRF / Eval Detection", "Risk Tier Scoring"]
        },
        {
            "id": "review",
            "name": "ReviewAgent",
            "role": "Synthesis, Cryptographic Governance & Human Gatekeeper",
            "capabilities": ["SHA-256 Fingerprinting", "Executive Risk Summary", "Approval Request Binding"]
        }
    ]


@router.post("/run")
async def run_multi_agent_recovery(
    request: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Launch the autonomous multi-agent state machine across the project & incident.
    """
    result = await agent_orchestrator.execute_repair_workflow(
        project_id=request.project_id,
        incident_id=request.incident_id,
        model_name=request.model_name or "llama-3.1-70b-versatile",
        db_override=db
    )
    return result


@router.get("/timeline/{job_id}")
def get_job_timeline(job_id: str):
    """Retrieve chronological event logs from multi-agent execution."""
    timeline = agent_orchestrator.get_timeline(job_id)
    return {"job_id": job_id, "events": timeline}
